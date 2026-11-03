import json

import pytest
from sqlalchemy import select

from backend.app.agent.schemas import GetMyOrderArguments
from backend.app.agent.tools import (
    GET_MY_ORDER,
    SEARCH_AFTER_SALES_POLICY,
    ToolContext,
    ToolRegistry,
)
from backend.app.core.exceptions import AppError
from backend.app.models import ChatSession, ToolInvocation, User
from backend.app.schemas.rag import CitationResponse
from backend.app.services.rag import RAGContext


def create_owned_chat_session(test_database, username: str) -> tuple[int, int]:
    with test_database.session_factory() as session:
        user = session.scalar(select(User).where(User.username == username))
        assert user is not None
        chat_session = ChatSession(user_id=user.id)
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return user.id, chat_session.id


def test_get_my_order_returns_safe_owned_order_facts(
    seeded_client,
    test_database,
):
    user_id, session_id = create_owned_chat_session(test_database, "consumer_demo")
    with test_database.session_factory() as session:
        result = ToolRegistry().execute(
            context=ToolContext(session=session, session_id=session_id, user_id=user_id),
            tool_name=GET_MY_ORDER,
            arguments={"order_no": "A10086"},
        )
        invocation = session.scalar(select(ToolInvocation))

    assert result.result == {
        "order_no": "A10086",
        "status": "delivered",
        "product_id": 1,
        "product_name": "SmartShop 降噪耳机 Pro",
    }
    assert invocation is not None
    assert invocation.status == "success"
    assert invocation.error_code is None
    assert invocation.arguments_json == {"order_no": "A10086"}
    assert "user_id" not in json.dumps(invocation.arguments_json)
    assert "password" not in json.dumps(invocation.arguments_json).lower()


def test_get_my_order_does_not_expose_another_users_order(
    seeded_client,
    test_database,
):
    user_id, session_id = create_owned_chat_session(test_database, "consumer_demo")
    with test_database.session_factory() as session:
        with pytest.raises(AppError) as error:
            ToolRegistry().execute(
                context=ToolContext(session=session, session_id=session_id, user_id=user_id),
                tool_name=GET_MY_ORDER,
                arguments={"order_no": "A10088"},
            )
        invocation = session.scalar(select(ToolInvocation))

    assert error.value.code == "order_not_found"
    assert invocation is not None
    assert invocation.status == "error"
    assert invocation.error_code == "order_not_found"
    assert invocation.result_json == {"error": "order_not_found"}


def test_unknown_tool_is_blocked_and_audited(seeded_client, test_database):
    user_id, session_id = create_owned_chat_session(test_database, "consumer_demo")
    with test_database.session_factory() as session:
        with pytest.raises(AppError) as error:
            ToolRegistry().execute(
                context=ToolContext(session=session, session_id=session_id, user_id=user_id),
                tool_name="execute_sql",
                arguments={"sql": "DROP TABLE users"},
            )
        invocation = session.scalar(select(ToolInvocation))

    assert error.value.code == "tool_not_allowed"
    assert invocation is not None
    assert invocation.status == "blocked"
    assert invocation.arguments_json == {"redacted": True}
    assert "DROP TABLE" not in json.dumps(invocation.arguments_json)


def test_tool_arguments_reject_model_supplied_identity(
    seeded_client,
    test_database,
):
    user_id, session_id = create_owned_chat_session(test_database, "consumer_demo")
    with test_database.session_factory() as session:
        with pytest.raises(AppError) as error:
            ToolRegistry().execute(
                context=ToolContext(session=session, session_id=session_id, user_id=user_id),
                tool_name=GET_MY_ORDER,
                arguments={"order_no": "A10088", "user_id": 3},
            )
        invocation = session.scalar(select(ToolInvocation))

    assert error.value.code == "tool_arguments_invalid"
    assert invocation is not None
    assert invocation.status == "blocked"
    assert invocation.arguments_json == {"redacted": True}


def test_tool_requires_owned_chat_session(seeded_client, test_database):
    consumer_id, _ = create_owned_chat_session(test_database, "consumer_demo")
    _, other_users_session_id = create_owned_chat_session(
        test_database,
        "consumer_other",
    )

    with test_database.session_factory() as session:
        with pytest.raises(AppError) as error:
            ToolRegistry().execute(
                context=ToolContext(
                    session=session,
                    session_id=other_users_session_id,
                    user_id=consumer_id,
                ),
                tool_name=GET_MY_ORDER,
                arguments={"order_no": "A10086"},
            )

    assert error.value.code == "chat_session_not_found"


def test_get_my_order_arguments_forbid_extra_fields():
    with pytest.raises(ValueError):
        GetMyOrderArguments.model_validate(
            {"order_no": "A10086", "user_id": 1},
        )


def test_tool_schemas_only_expose_allowlisted_business_parameters():
    schemas = ToolRegistry().model_schemas()
    by_name = {schema["function"]["name"]: schema for schema in schemas}

    order_parameters = by_name[GET_MY_ORDER]["function"]["parameters"]
    assert order_parameters["additionalProperties"] is False
    assert set(order_parameters["properties"]) == {"order_no"}
    assert "user_id" not in order_parameters["properties"]
    assert "search_after_sales_policy" in by_name


def test_policy_tool_returns_grounded_citations(
    seeded_client,
    test_database,
):
    class FakeRagService:
        def retrieve_sync(
            self,
            *,
            question: str,
            product_id: int | None = None,
            top_k: int | None = None,
        ) -> RAGContext:
            citation = CitationResponse(
                document_id=2,
                chunk_id="[1] 2:1",
                filename="warranty_policy.md",
                title="质保规则",
                excerpt="降噪耳机提供十二个月质保。",
                similarity=0.9,
            )
            return RAGContext(
                evidence="[1] 降噪耳机提供十二个月质保。",
                citations=[citation],
                chunks=(),
                grounded=True,
            )

    user_id, session_id = create_owned_chat_session(test_database, "consumer_demo")
    with test_database.session_factory() as session:
        result = ToolRegistry().execute(
            context=ToolContext(
                session=session,
                session_id=session_id,
                user_id=user_id,
                rag_service=FakeRagService(),
            ),
            tool_name=SEARCH_AFTER_SALES_POLICY,
            arguments={"query": "耳机保修多久", "product_id": 1},
        )
        invocation = session.scalar(
            select(ToolInvocation).where(ToolInvocation.tool_name == SEARCH_AFTER_SALES_POLICY)
        )

    assert result.result["grounded"] is True
    assert result.result["citations"][0]["filename"] == "warranty_policy.md"
    assert invocation is not None
    assert invocation.status == "success"
