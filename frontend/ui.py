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
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #DCE5F2;
    border-radius: 20px;
    padding: 1rem;
    box-shadow: 0 18px 50px rgba(15, 35, 65, 0.07);
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
    padding: 0.35rem 0 0.8rem;
}
.st-key-brand-block h3 {
    font-size: 1.28rem;
    margin-bottom: 0.15rem;
    white-space: nowrap;
}
.st-key-history-list button,
.st-key-handoff-list button {
    justify-content: flex-start !important;
    text-align: left !important;
}
.st-key-message-scroll {
    border: 1px solid #EDF1F7;
    border-radius: 16px;
    padding: 0.35rem 0.7rem;
}
.st-key-detail-card,
.st-key-order-card,
.st-key-session-meta,
.st-key-consumer-order,
.st-key-consumer-session-meta,
.st-key-consumer-support-card,
.st-key-agent-order,
.st-key-agent-session-meta,
.st-key-agent-task-card,
.st-key-welcome-card {
    background: #F8FAFD;
    border: 1px solid #E3EAF4;
    border-radius: 16px;
    padding: 0.85rem;
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
    role = "user" if sender == "consumer" else "assistant"
    if sender == "agent":
        avatar = ":material/support_agent:"
        label = "人工客服"
    elif sender == "assistant":
        avatar = ":material/auto_awesome:"
        label = "SmartService AI"
    elif sender == "system":
        avatar = ":material/info:"
        label = "系统"
    else:
        avatar = ":material/person:"
        label = "消费者"

    with st.chat_message(role, avatar=avatar):
        header = f"**{label}**"
        timestamp = format_timestamp(message.get("created_at"))
        if timestamp:
            header += f" · {timestamp}"
        st.markdown(header)
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
    *,
    key: str = "order-card",
) -> None:
    with st.container(key=key, border=True):
        st.markdown("#### :material/receipt_long: 订单信息")
        if not order:
            st.caption("会话中还没有关联订单。发送订单号后可自动识别。")
            return
        st.markdown(f"**{order['order_no']}**")
        st.caption(f"状态：{status_label(order['status'])}")
        product = order.get("product") or {}
        st.caption(f"商品：{product.get('name', '未知商品')}")


def render_session_meta(
    session: dict[str, Any],
    *,
    key: str = "session-meta",
) -> None:
    with st.container(key=key, border=True):
        st.markdown("#### :material/info: 会话信息")
        st.caption(f"会话状态：{status_label(session['status'])}")
        workflow = (
            "人工处理中"
            if session["status"] == "human_active"
            else workflow_label(session["workflow_state"])
        )
        st.caption(f"工作流：{workflow}")
        if session.get("intent"):
            st.caption(f"识别意图：{session['intent']}")
        st.caption(f"创建时间：{format_timestamp(session.get('created_at'))}")
