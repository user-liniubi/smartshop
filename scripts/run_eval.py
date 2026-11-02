import argparse
import asyncio
import json
import math
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

from backend.app.agent.intent import IntentService
from backend.app.agent.orchestrator import AfterSalesOrchestrator
from backend.app.agent.tools import GET_MY_ORDER, ToolContext, ToolRegistry
from backend.app.core.config import get_settings
from backend.app.core.exceptions import AppError
from backend.app.db.session import Database
from backend.app.models import ChatSession, Order, User
from backend.app.rag.embeddings import BgeEmbeddingProvider
from backend.app.rag.vector_store import ChromaVectorStore
from backend.app.services.llm import DeepSeekClient
from backend.app.services.rag import RAGService


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    category: str
    intent_correct: bool
    order_no_correct: bool
    action_correct: bool
    tool_correct: bool
    hit_at_3: bool | None
    hit_at_5: bool | None
    refusal_correct: bool | None
    task_correct: bool
    latency_ms: float
    actual_intent: str
    actual_order_no: str | None
    actual_action: str


def _load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                cases.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
    return cases


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(percentile * len(ordered)) - 1))
    return round(ordered[index], 2)


def _rate(values: list[bool | None]) -> float | None:
    applicable = [value for value in values if value is not None]
    if not applicable:
        return None
    return round(sum(applicable) / len(applicable), 4)


def _tool_case_correct(
    *,
    registry: ToolRegistry,
    context: ToolContext,
    case: dict[str, Any],
    actual_order_no: str | None,
) -> tuple[bool, int | None]:
    if case["expected_tool"] == "none":
        if case["category"] == "prompt_injection":
            try:
                registry.execute(
                    context=context,
                    tool_name="execute_sql",
                    arguments={"sql": "SELECT * FROM users"},
                )
            except AppError as exc:
                return exc.code == "tool_not_allowed", None
        return True, None

    if actual_order_no is None:
        return False, None

    try:
        result = registry.execute(
            context=context,
            tool_name=GET_MY_ORDER,
            arguments={"order_no": actual_order_no},
        )
    except AppError as exc:
        return (case["expect_denied"] and exc.code == "order_not_found"), None

    if case["expect_denied"]:
        return False, None
    return result.result.get("order_no") == actual_order_no, result.result.get("product_id")


def _rag_metrics(
    *,
    rag_service: RAGService,
    message: str,
    product_id: int | None,
    gold_files: list[str],
) -> tuple[bool | None, bool | None, bool | None]:
    if not gold_files:
        return None, None, None
    context = rag_service.retrieve_sync(
        question=message,
        product_id=product_id,
        top_k=5,
    )
    files = [citation.filename for citation in context.citations]
    gold = set(gold_files)
    return (
        bool(gold.intersection(files[:3])),
        bool(gold.intersection(files[:5])),
        context.grounded,
    )


def _refusal_correct(
    *,
    category: str,
    case_id: str,
    rag_service: RAGService,
    message: str,
) -> bool | None:
    if category != "unrelated" and case_id != "injection-003":
        return None
    context = rag_service.retrieve_sync(question=message, top_k=5)
    return not context.grounded


def _write_report(
    *,
    output_dir: Path,
    summary: dict[str, Any],
    results: list[EvalResult],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summary,
        "results": [result.__dict__ for result in results],
    }
    (output_dir / "latest_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    category_counts = Counter(result.category for result in results)
    category_success = Counter(result.category for result in results if result.task_correct)
    lines = [
        "# SmartShop Agent 固定评测报告",
        "",
        "## 指标",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
    ]
    for label, value in summary.items():
        lines.append(f"| {label} | {value} |")
    lines.extend(
        [
            "",
            "## 分类结果",
            "",
            "| 分类 | 成功 / 总数 |",
            "|---|---:|",
        ]
    )
    for category, count in sorted(category_counts.items()):
        lines.append(f"| {category} | {category_success[category]} / {count} |")
    lines.extend(
        [
            "",
            "## 口径",
            "",
            "- 意图和订单号使用 DeepSeek 结构化输出实测。",
            "- 工具指标验证订单归属和未知工具拦截，不执行任意 SQL。",
            "- RAG Hit@K 以人工标注的 gold files 是否进入前 K 条来源计算。",
            "- 任务成功率要求意图、订单号、工作流动作、工具行为以及适用的 RAG/拒答均正确。",
            "- 该报告不包含最终回答人工正确率或引用支持度抽检。",
        ]
    )
    (output_dir / "latest_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_evaluation(*, cases_path: Path, output_dir: Path) -> dict[str, Any]:
    cases = _load_cases(cases_path)
    settings = get_settings()
    database = Database(settings.database_url, echo=settings.database_echo)
    vector_store = ChromaVectorStore(settings.chroma_path)
    embedder = BgeEmbeddingProvider(
        settings.embedding_model,
        settings.embedding_device,
        local_files_only=settings.embedding_local_files_only,
    )
    llm = DeepSeekClient(settings)
    intent_service = IntentService(llm)
    registry = ToolRegistry()
    orchestrator = AfterSalesOrchestrator()
    rag_service = RAGService(
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
        llm=llm,
    )
    results: list[EvalResult] = []

    try:
        with database.session_factory() as session:
            consumer = session.scalar(select(User).where(User.username == "consumer_demo"))
            if consumer is None:
                raise RuntimeError("Missing demo consumer; run sample_data.seed first")
            scratch_session = ChatSession(user_id=consumer.id)
            session.add(scratch_session)
            session.commit()
            session.refresh(scratch_session)
            context = ToolContext(
                session=session,
                session_id=scratch_session.id,
                user_id=consumer.id,
                rag_service=rag_service,
            )

            for case in cases:
                started_at = time.perf_counter()
                intent_result = asyncio.run(intent_service.extract(content=case["message"]))
                decision = orchestrator.decide(intent_result)
                actual_order_no = intent_result.slots.order_no
                tool_correct, product_id = _tool_case_correct(
                    registry=registry,
                    context=context,
                    case=case,
                    actual_order_no=actual_order_no,
                )

                if product_id is None and case.get("product_id") is not None:
                    product_id = case["product_id"]
                if product_id is None and case.get("expected_order_no"):
                    order = session.scalar(
                        select(Order).where(Order.order_no == case["expected_order_no"])
                    )
                    product_id = order.product_id if order else None

                hit_at_3, hit_at_5, _ = _rag_metrics(
                    rag_service=rag_service,
                    message=case["message"],
                    product_id=product_id,
                    gold_files=case.get("gold_files", []),
                )
                refusal_correct = _refusal_correct(
                    category=case["category"],
                    case_id=case["id"],
                    rag_service=rag_service,
                    message=case["message"],
                )
                intent_correct = intent_result.intent.value == case["expected_intent"]
                expected_order_no = case.get("expected_order_no")
                order_no_correct = actual_order_no == expected_order_no
                action_correct = decision.action.value == case["expected_action"]
                task_correct = all(
                    [
                        intent_correct,
                        order_no_correct,
                        action_correct,
                        tool_correct,
                        hit_at_5 is not False,
                        refusal_correct is not False,
                    ]
                )
                results.append(
                    EvalResult(
                        case_id=case["id"],
                        category=case["category"],
                        intent_correct=intent_correct,
                        order_no_correct=order_no_correct,
                        action_correct=action_correct,
                        tool_correct=tool_correct,
                        hit_at_3=hit_at_3,
                        hit_at_5=hit_at_5,
                        refusal_correct=refusal_correct,
                        task_correct=task_correct,
                        latency_ms=round(
                            (time.perf_counter() - started_at) * 1000,
                            2,
                        ),
                        actual_intent=intent_result.intent.value,
                        actual_order_no=actual_order_no,
                        actual_action=decision.action.value,
                    )
                )

            session.delete(scratch_session)
            session.commit()
    finally:
        database.dispose()

    latencies = [result.latency_ms for result in results]
    summary = {
        "case_count": len(results),
        "intent_accuracy": _rate([result.intent_correct for result in results]),
        "order_no_extraction_accuracy": _rate(
            [
                result.order_no_correct
                for result, case in zip(results, cases, strict=True)
                if case.get("expected_order_no") is not None
            ]
        ),
        "action_accuracy": _rate([result.action_correct for result in results]),
        "tool_behavior_accuracy": _rate(
            [
                result.tool_correct
                for result, case in zip(results, cases, strict=True)
                if case["expected_tool"] != "none" or case["category"] == "prompt_injection"
            ]
        ),
        "rag_hit_at_3": _rate([result.hit_at_3 for result in results]),
        "rag_hit_at_5": _rate([result.hit_at_5 for result in results]),
        "no_evidence_refusal_rate": _rate([result.refusal_correct for result in results]),
        "task_success_rate": _rate([result.task_correct for result in results]),
        "p50_latency_ms": _percentile(latencies, 0.5),
        "p95_latency_ms": _percentile(latencies, 0.95),
    }
    _write_report(output_dir=output_dir, summary=summary, results=results)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("data/eval/after_sales_questions.jsonl"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/eval"),
    )
    args = parser.parse_args()
    summary = run_evaluation(
        cases_path=args.cases,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
