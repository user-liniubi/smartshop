from datetime import datetime
from typing import Any

import streamlit as st

APP_CSS = """
<style>
.st-key-sm-nav,
.st-key-sm-chat,
.st-key-sm-detail,
.st-key-agent-nav,
.st-key-agent-list,
.st-key-agent-chat {
    background: #FFFFFF;
    border: 1px solid #E5E9F0;
    border-radius: 16px;
    padding: 1.1rem;
}
.st-key-sm-nav,
.st-key-agent-nav {
    min-height: calc(100vh - 4.5rem);
}
.st-key-sm-chat,
.st-key-agent-chat,
.st-key-agent-list {
    min-height: calc(100vh - 4.5rem);
}
.st-key-brand-block {
    padding: 0.15rem 0 0.9rem;
}
.st-key-brand-block h3 {
    font-size: 1.18rem !important;
    line-height: 1.35 !important;
    margin-bottom: 0.15rem;
    white-space: nowrap;
}
.st-key-history-list button,
.st-key-handoff-list button {
    justify-content: flex-start !important;
    text-align: left !important;
    min-height: 2.125rem !important;
}
.st-key-message-scroll {
    background: #F7F8FA;
    border-radius: 16px;
    padding: 0.75rem;
}
[class*="st-key-message-consumer-"],
[class*="st-key-message-assistant-"],
[class*="st-key-message-agent-"],
[class*="st-key-message-system-"] {
    width: fit-content;
    max-width: 78%;
    padding: 0.65rem 0.85rem;
    margin-bottom: 0.65rem;
}
[class*="st-key-message-consumer-"] {
    margin-left: auto;
    background: #DCF8C6;
    border-radius: 16px 16px 4px 16px;
}
[class*="st-key-message-assistant-"] {
    margin-right: auto;
    background: #FFFFFF;
    border: 1px solid #E5E9F0;
    border-radius: 16px 16px 16px 4px;
}
[class*="st-key-message-agent-"] {
    margin-right: auto;
    background: #EAF2FF;
    border: 1px solid #D7E7FF;
    border-radius: 16px 16px 16px 4px;
}
[class*="st-key-message-system-"] {
    max-width: 100%;
    margin-right: auto;
    margin-left: auto;
    background: #EEF1F5;
    border-radius: 10px;
    text-align: center;
}
.st-key-message-scroll [class*="st-key-message-"] p {
    margin-bottom: 0.45rem;
}
.st-key-message-scroll [class*="st-key-message-"] p:last-child {
    margin-bottom: 0;
}
.stApp {
    font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.stApp h3 {
    font-size: 1.2rem !important;
    line-height: 1.35 !important;
    letter-spacing: -0.015em;
}
.stApp h4 {
    font-size: 0.95rem !important;
    line-height: 1.4 !important;
}
.stApp button,
.stApp input,
.stApp textarea {
    font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
}
@media (max-width: 900px) {
    .st-key-sm-nav,
    .st-key-sm-chat,
    .st-key-sm-detail,
    .st-key-agent-nav,
    .st-key-agent-list,
    .st-key-agent-chat {
        min-height: auto;
        padding: 0.8rem;
        border-radius: 16px;
    }
}
</style>
"""

SESSION_STATUS_LABELS = {
    "open": "AI 处理中",
    "need_human": "等待人工",
    "human_active": "人工处理中",
    "closed": "已结束",
}

WORKFLOW_LABELS = {
    "collecting_info": "收集信息",
    "awaiting_order_selection": "选择订单",
    "checking_order": "核验订单",
    "checking_policy": "检索政策",
    "answer_ready": "生成建议",
    "need_human": "等待人工",
    "resolved": "已解决",
}

HANDOFF_STATUS_LABELS = {
    "pending": "待接管",
    "claimed": "已接管",
    "closed": "已关闭",
}

AFTER_SALES_TICKET_STATUS_LABELS = {
    "pending_approval": "待审批",
    "approved": "已通过",
    "rejected": "已拒绝",
    "cancelled": "已取消",
}

AFTER_SALES_TICKET_TYPE_LABELS = {
    "return": "退货",
    "exchange": "换货",
}

AFTER_SALES_TICKET_EVENT_LABELS = {
    "created": "工单创建",
    "approved": "审批通过",
    "rejected": "审批驳回",
    "cancelled": "工单取消",
    "system_note": "系统记录",
}


def inject_styles() -> None:
    st.html(APP_CSS)


def format_timestamp(value: str | None) -> str:
    if not value:
        return ""
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value[:16]
    return timestamp.strftime("%m-%d %H:%M")


def status_label(value: str) -> str:
    return SESSION_STATUS_LABELS.get(value, value)


def workflow_label(value: str) -> str:
    return WORKFLOW_LABELS.get(value, value)


def handoff_status_label(value: str) -> str:
    return HANDOFF_STATUS_LABELS.get(value, value)


def after_sales_ticket_status_label(value: str) -> str:
    return AFTER_SALES_TICKET_STATUS_LABELS.get(value, value)


def after_sales_ticket_type_label(value: str) -> str:
    return AFTER_SALES_TICKET_TYPE_LABELS.get(value, value)


def derive_session_title(messages: list[dict[str, Any]], session_id: int) -> str:
    for message in messages:
        if message.get("sender_type") == "consumer" and message.get("content"):
            content = " ".join(message["content"].split())
            return content if len(content) <= 28 else f"{content[:28]}..."
    return f"售后会话 #{session_id}"


def message_summary(messages: list[dict[str, Any]]) -> str:
    if not messages:
        return "暂无消息"
    content = " ".join((messages[-1].get("content") or "").split())
    return content if len(content) <= 42 else f"{content[:42]}..."


def render_message(message: dict[str, Any], *, staff_view: bool = False) -> None:
    sender = message.get("sender_type", "assistant")
    bucket = sender if sender in {"consumer", "assistant", "agent", "system"} else "assistant"
    if sender == "agent":
        label = "人工客服"
    elif sender == "assistant":
        label = "SmartService AI"
    elif sender == "system":
        label = "系统"
    else:
        label = "消费者"

    message_id = message.get("id", f"{sender}-{message.get('created_at', '')}")
    with st.container(key=f"message-{bucket}-{message_id}"):
        header = f"**{label}**"
        timestamp = format_timestamp(message.get("created_at"))
        if timestamp:
            header += f" · {timestamp}"
        st.caption(header)
        st.markdown(message.get("content") or "")
        citations = message.get("citations_json") or []
        if citations:
            with st.expander("查看知识来源", icon=":material/menu_book:"):
                for citation in citations:
                    st.markdown(
                        f"**{citation.get('title', '知识片段')}** "
                        f"· `{citation.get('filename', '')}`"
                    )
                    if citation.get("heading"):
                        st.caption(citation["heading"])
                    st.caption(citation.get("excerpt", ""))


def render_order_card(
    order: dict[str, Any] | None,
) -> None:
    st.markdown("#### 订单信息")
    if not order:
        st.caption("尚未关联订单")
        st.caption("发送订单号后可自动识别。")
        return
    st.markdown(f"**{order['order_no']}**")
    st.caption(status_label(order["status"]))
    product = order.get("product") or {}
    st.caption(product.get("name", "未知商品"))


def render_session_meta(
    session: dict[str, Any],
) -> None:
    st.markdown("#### 会话信息")
    st.markdown(f"**{status_label(session['status'])}**")
    workflow = (
        "人工处理中"
        if session["status"] == "human_active"
        else workflow_label(session["workflow_state"])
    )
    st.caption(f"当前阶段：{workflow}")
    if session.get("intent"):
        st.caption(f"识别意图：{session['intent']}")
    st.caption(f"创建时间：{format_timestamp(session.get('created_at'))}")


def render_after_sales_ticket(
    ticket: dict[str, Any] | None,
    events: list[dict[str, Any]] | None = None,
) -> None:
    st.markdown("#### 售后工单")
    if not ticket:
        st.caption("当前会话尚未生成售后工单")
        return
    st.markdown(f"**{ticket['ticket_no']}**")
    st.caption(
        f"{after_sales_ticket_type_label(ticket['request_type'])} · "
        f"{after_sales_ticket_status_label(ticket['status'])}"
    )
    st.caption(ticket.get("issue_description", ""))
    if ticket.get("refund_amount") is not None:
        st.caption(f"参考退款金额：{ticket['refund_amount']} {ticket.get('currency', 'CNY')}")
    if ticket.get("eligibility_reason"):
        st.caption(f"资格规则：{ticket['eligibility_reason']}")
    if ticket.get("review_note"):
        st.caption(f"审批意见：{ticket['review_note']}")
    if events:
        with st.expander("查看处理记录", icon=":material/timeline:"):
            for event in events:
                label = AFTER_SALES_TICKET_EVENT_LABELS.get(
                    event.get("event_type", ""),
                    event.get("event_type", "事件"),
                )
                st.caption(
                    f"{format_timestamp(event.get('created_at'))} · {label}"
                    f"{' · ' + event['note'] if event.get('note') else ''}"
                )
