import streamlit as st

try:
    from frontend.api_client import ApiClient, ApiError
    from frontend.login_ui import render_login_screen
    from frontend.ui import (
        derive_session_title,
        format_timestamp,
        inject_styles,
        message_summary,
        render_message,
        render_order_card,
        render_session_meta,
        status_label,
        workflow_label,
    )
except ModuleNotFoundError:
    from api_client import ApiClient, ApiError
    from login_ui import render_login_screen
    from ui import (
        derive_session_title,
        format_timestamp,
        inject_styles,
        message_summary,
        render_message,
        render_order_card,
        render_session_meta,
        status_label,
        workflow_label,
    )

st.set_page_config(
    page_title="SmartShop 售后客服",
    page_icon=":material/support_agent:",
    layout="wide",
)

st.session_state.setdefault("consumer_token", None)
st.session_state.setdefault("consumer_user", None)


def logout() -> None:
    st.session_state.consumer_token = None
    st.session_state.consumer_user = None
    st.session_state.pop("consumer_session_id", None)


def client() -> ApiClient:
    return ApiClient(token=st.session_state.consumer_token)


def show_error(error: ApiError) -> None:
    st.error(error.message, title="操作失败")


if st.session_state.consumer_token is None:
    username, password, submitted = render_login_screen(
        role="消费者",
        brand_title="SmartService AI",
        subtitle="从已有订单开始，把退货、换货、保修和订单问题一次处理好。",
        account_hint="演示账号：consumer_demo / Demo123!",
    )

    if submitted:
        try:
            login = ApiClient().login(username, password)
            if login["user"]["role"] != "consumer":
                st.error("请使用消费者账号登录", title="角色不匹配")
            else:
                st.session_state.consumer_token = login["access_token"]
                st.session_state.consumer_user = login["user"]
                st.rerun()
        except ApiError as error:
            show_error(error)
    st.stop()

inject_styles()


@st.fragment(run_every="3s", key="consumer_live_workspace")
def render_live_workspace() -> None:
    try:
        sessions = client().list_sessions()
    except ApiError as error:
        show_error(error)
        return

    if not sessions:
        left, center, right = st.columns([0.22, 0.54, 0.24], gap="medium")
        with left:
            with st.container(key="sm-nav"):
                st.markdown("### :material/support_agent: SmartService AI")
                st.caption("智能售后客服")
                if st.button("新建会话", icon=":material/add:", width="stretch"):
                    created = client().create_session()
                    st.session_state.consumer_session_id = created["id"]
                    st.rerun()
                st.caption("暂无会话记录")
                if st.button(
                    "退出登录",
                    icon=":material/logout:",
                    width="stretch",
                ):
                    logout()
                    st.rerun(scope="app")
        with center:
            with st.container(key="sm-chat"):
                st.info(
                    "创建第一个售后会话，描述订单和问题后即可开始。",
                    title="欢迎使用 SmartService AI",
                )
        with right:
            with st.container(key="sm-detail"):
                st.markdown("#### :material/health_and_safety: 服务保障")
                st.caption("订单事实来自 MySQL，售后政策来自可引用知识库。")
        return

    session_messages: dict[int, list[dict]] = {}
    for session in sessions:
        try:
            session_messages[session["id"]] = client().get_messages(session["id"])
        except ApiError:
            session_messages[session["id"]] = []

    session_by_id = {session["id"]: session for session in sessions}
    if st.session_state.get("consumer_session_id") not in session_by_id:
        st.session_state.consumer_session_id = sessions[0]["id"]
    selected_id = st.session_state.consumer_session_id
    selected = session_by_id[selected_id]
    messages = session_messages[selected_id]

    left, center, right = st.columns([0.22, 0.54, 0.24], gap="medium")
    with left:
        with st.container(key="sm-nav"):
            with st.container(key="brand-block"):
                st.markdown("### :material/support_agent: SmartService AI")
                st.caption("智能售后客服")
            if st.button(
                "新建会话",
                icon=":material/add:",
                type="primary",
                width="stretch",
            ):
                created = client().create_session()
                st.session_state.consumer_session_id = created["id"]
                st.rerun()

            st.markdown("#### 会话记录")
            with st.container(key="history-list"):
                for session in sessions:
                    session_id = session["id"]
                    is_selected = session_id == selected_id
                    title = derive_session_title(
                        session_messages[session_id],
                        session_id,
                    )
                    with st.container(
                        border=is_selected,
                        key=f"consumer-session-{session_id}",
                    ):
                        if st.button(
                            title,
                            key=f"select-consumer-session-{session_id}",
                            type="primary" if is_selected else "secondary",
                            width="stretch",
                        ):
                            st.session_state.consumer_session_id = session_id
                            st.rerun()
                        st.caption(
                            f"{status_label(session['status'])} · "
                            f"{format_timestamp(session['updated_at'])}"
                        )
                        st.caption(message_summary(session_messages[session_id]))

            st.space("stretch")
            st.caption(f"当前账号：{st.session_state.consumer_user['username']}")
            if st.button(
                "退出登录",
                icon=":material/logout:",
                width="stretch",
            ):
                logout()
                st.rerun(scope="app")

    with center:
        with st.container(key="sm-chat"):
            with st.container(horizontal=True, horizontal_alignment="distribute"):
                st.markdown("### :material/auto_awesome: SmartService AI")
                st.markdown(":green-badge[在线]")
            st.caption("订单查询、售后政策与人工客服协同处理")

            status = selected["status"]
            if status == "need_human":
                st.warning("正在等待人工客服接管。", icon=":material/schedule:")
            elif status == "human_active":
                st.info("当前由人工客服处理，新消息会继续保存。", icon=":material/support_agent:")
            elif status == "closed":
                st.success("本次售后会话已关闭。", icon=":material/task_alt:")

            with st.container(horizontal=True):
                if status != "human_active":
                    st.caption(f":blue-badge[{workflow_label(selected['workflow_state'])}]")
                st.caption(f":gray-badge[{status_label(status)}]")
                st.caption(":material/sync: 3 秒自动同步")

            with st.container(key="message-scroll", height=500):
                if not messages:
                    with st.container(key="welcome-card", border=True):
                        st.markdown("### 你好，我是 SmartService AI")
                        st.write("告诉我订单号和遇到的问题，我会核验订单并检索售后政策。")
                    st.caption("你可以从下面几个问题开始：")
                    suggestions = (
                        ("耳机坏了怎么退货？", "耳机坏了，想退货"),
                        ("查订单 A10086", "查一下订单 A10086 的状态"),
                        ("保修政策是什么？", "降噪耳机保修多久？"),
                    )
                    with st.container(horizontal=True):
                        for label, prompt_text in suggestions:
                            if st.button(
                                label,
                                key=f"consumer-suggestion-{label}",
                            ):
                                with st.spinner("正在处理你的问题..."):
                                    client().send_message(selected_id, prompt_text)
                                st.rerun()
                else:
                    for message in messages:
                        render_message(message)

            if status in {"open", "human_active"}:
                with st.container(
                    horizontal=True,
                    horizontal_alignment="right",
                ):
                    if st.button(
                        "申请人工客服",
                        icon=":material/support_agent:",
                        disabled=status != "open",
                    ):
                        try:
                            client().request_handoff(
                                selected_id,
                                "消费者主动申请人工客服",
                            )
                            st.rerun()
                        except ApiError as error:
                            show_error(error)

            prompt = st.chat_input(
                "输入订单号、故障描述或售后问题",
                disabled=status == "closed",
                submit_mode="disable",
                key="consumer_chat_input",
            )
            if prompt:
                with st.spinner("SmartService AI 正在查询订单和知识库..."):
                    try:
                        result = client().send_message(selected_id, prompt)
                        if result["assistant_message"] is None:
                            st.info(
                                "消息已发送，请等待人工客服回复。",
                                title="等待客服",
                            )
                        st.rerun()
                    except ApiError as error:
                        show_error(error)

    with right:
        with st.container(key="sm-detail"):
            order_no = (selected.get("slots_json") or {}).get("order_no")
            order = None
            if isinstance(order_no, str):
                try:
                    order = client().get_order_by_number(order_no)
                except ApiError:
                    order = None
            render_order_card(order, key="consumer-order")
            render_session_meta(selected, key="consumer-session-meta")
            with st.container(key="consumer-support-card", border=True):
                st.markdown("#### :material/health_and_safety: 售后流程")
                st.markdown(
                    ":material/check_circle: 自动核验本人订单  \n"
                    ":material/menu_book: 政策回答附带来源  \n"
                    ":material/support_agent: 复杂问题可转人工"
                )


render_live_workspace()
