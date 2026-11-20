import streamlit as st

try:
    from frontend.api_client import ApiClient, ApiError
    from frontend.login_ui import render_login_screen
    from frontend.ui import (
        after_sales_ticket_status_label,
        after_sales_ticket_type_label,
        format_timestamp,
        handoff_status_label,
        inject_styles,
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
        after_sales_ticket_status_label,
        after_sales_ticket_type_label,
        format_timestamp,
        handoff_status_label,
        inject_styles,
        render_message,
        render_order_card,
        render_session_meta,
        status_label,
        workflow_label,
    )

SOURCE_LABELS = {
    "user": "消费者申请",
    "ai": "AI 降级",
    "rule": "规则触发",
}

st.set_page_config(
    page_title="SmartShop AfterSales · 售后工作台",
    page_icon=":material/support_agent:",
    layout="wide",
)

st.session_state.setdefault("agent_token", None)
st.session_state.setdefault("agent_user", None)
st.session_state.setdefault("agent_view", "待接管")
st.session_state.setdefault("agent_switch_to_mine", False)


def logout() -> None:
    st.session_state.agent_token = None
    st.session_state.agent_user = None
    st.session_state.pop("agent_handoff_id", None)


def client() -> ApiClient:
    return ApiClient(token=st.session_state.agent_token)


def show_error(error: ApiError) -> None:
    st.error(error.message, title="操作失败")


def render_after_sales_ticket_workspace() -> None:
    try:
        tickets = client().list_pending_after_sales_tickets()
    except ApiError as error:
        show_error(error)
        return

    ticket_by_id = {ticket["id"]: ticket for ticket in tickets}
    if st.session_state.get("agent_ticket_id") not in ticket_by_id:
        st.session_state.agent_ticket_id = tickets[0]["id"] if tickets else None
    selected_id = st.session_state.get("agent_ticket_id")
    selected = ticket_by_id.get(selected_id) if selected_id is not None else None

    left, center, right = st.columns([0.2, 0.3, 0.5], gap="medium")
    with left:
        with st.container(key="agent-nav"):
            st.markdown("### :material:support_agent: 工单审批")
            st.caption("AI 已核验订单和政策，等待人工决定。")
            if st.button(
                "返回客服会话",
                icon=":material/arrow_back:",
                width="stretch",
            ):
                st.session_state.agent_view = "待接管"
                st.rerun()
            st.caption(f"待审批 {len(tickets)} 张")

    with center:
        with st.container(key="agent-list"):
            st.markdown("### 待审批工单")
            if not tickets:
                st.info("当前没有待审批售后工单。", title="审批队列为空")
            else:
                for ticket in tickets:
                    ticket_id = ticket["id"]
                    is_selected = ticket_id == selected_id
                    with st.container(key=f"agent-ticket-{ticket_id}"):
                        if st.button(
                            ticket["ticket_no"],
                            key=f"select-agent-ticket-{ticket_id}",
                            type="primary" if is_selected else "secondary",
                            width="stretch",
                        ):
                            st.session_state.agent_ticket_id = ticket_id
                            st.rerun()
                        st.caption(
                            f"{after_sales_ticket_type_label(ticket['request_type'])}"
                            f" · {after_sales_ticket_status_label(ticket['status'])}"
                        )
                        st.caption(
                            f"会话 #{ticket['session_id']} · "
                            f"{format_timestamp(ticket['created_at'])}"
                        )

    with right:
        with st.container(key="agent-chat"):
            if selected is None:
                st.info("从待审批列表选择一张工单。", title="尚未选择工单")
                return
            st.markdown(f"### {selected['ticket_no']}")
            st.caption(
                f"{after_sales_ticket_type_label(selected['request_type'])}"
                f" · {after_sales_ticket_status_label(selected['status'])}"
            )
            st.markdown(f"**问题描述**  \n{selected['issue_description']}")
            st.caption(
                f"消费者 #{selected['user_id']} · 订单 #{selected['order_id']}"
                f" · 会话 #{selected['session_id']}"
            )
            citations = selected.get("policy_citations") or []
            if citations:
                with st.expander("查看政策依据", icon=":material/menu_book:"):
                    for citation in citations:
                        st.markdown(
                            f"**{citation.get('title', '知识片段')}** "
                            f"· `{citation.get('filename', '')}`"
                        )
                        st.caption(citation.get("excerpt", ""))

            review_note = st.text_area(
                "审批意见",
                max_chars=500,
                placeholder="拒绝时必须填写原因；通过时可选填。",
                key=f"ticket-review-note-{selected['id']}",
            )
            approve_column, reject_column = st.columns(2)
            with approve_column:
                if st.button(
                    "通过工单",
                    icon=":material/task_alt:",
                    type="primary",
                    width="stretch",
                ):
                    try:
                        client().review_after_sales_ticket(
                            selected["id"],
                            decision="approved",
                            review_note=review_note.strip(),
                        )
                        st.rerun()
                    except ApiError as error:
                        show_error(error)
            with reject_column:
                if st.button(
                    "拒绝工单",
                    icon=":material/cancel:",
                    width="stretch",
                ):
                    if not review_note.strip():
                        st.warning("拒绝工单时必须填写审批意见。")
                    else:
                        try:
                            client().review_after_sales_ticket(
                                selected["id"],
                                decision="rejected",
                                review_note=review_note.strip(),
                            )
                            st.rerun()
                        except ApiError as error:
                            show_error(error)


if st.session_state.agent_token is None:
    username, password, submitted = render_login_screen(
        role="客服",
        brand_title="SmartShop AfterSales",
        subtitle="统一处理消费电子产品售后任务、会话上下文与人工回复。",
        account_hint="演示账号：agent_demo / Agent123!",
    )

    if submitted:
        try:
            login = ApiClient().login(username, password)
            if login["user"]["role"] != "agent":
                st.error("请使用客服账号登录", title="角色不匹配")
            else:
                st.session_state.agent_token = login["access_token"]
                st.session_state.agent_user = login["user"]
                st.rerun()
        except ApiError as error:
            show_error(error)
    st.stop()

inject_styles()


@st.fragment(run_every="3s", key="agent_live_workspace")
def render_live_workspace() -> None:
    if st.session_state.agent_switch_to_mine:
        st.session_state.agent_view = "我的会话"
        st.session_state.agent_switch_to_mine = False

    try:
        pending_handoffs = client().list_pending_handoffs()
        my_handoffs = client().list_my_handoffs()
    except ApiError as error:
        show_error(error)
        return

    view = st.session_state.agent_view
    if view == "工单审批":
        render_after_sales_ticket_workspace()
        return
    handoffs = pending_handoffs if view == "待接管" else my_handoffs
    handoff_by_id = {handoff["id"]: handoff for handoff in handoffs}
    if st.session_state.get("agent_handoff_id") not in handoff_by_id:
        st.session_state.agent_handoff_id = handoffs[0]["id"] if handoffs else None
    selected_handoff_id = st.session_state.get("agent_handoff_id")
    handoff = handoff_by_id.get(selected_handoff_id) if selected_handoff_id is not None else None

    left, center, right = st.columns([0.2, 0.29, 0.51], gap="medium")

    with left:
        with st.container(key="agent-nav"):
            with st.container(key="brand-block"):
                st.markdown("### :material/support_agent: SmartShop AfterSales")
                st.caption("消费电子客服工作台")

            st.markdown("#### 工作队列")
            if st.button(
                f"待接管  {len(pending_handoffs)}",
                icon=":material/pending_actions:",
                type="primary" if view == "待接管" else "secondary",
                width="stretch",
                key="agent-nav-pending",
            ):
                st.session_state.agent_view = "待接管"
                st.rerun()
            if st.button(
                f"我的会话  {len(my_handoffs)}",
                icon=":material/assignment_ind:",
                type="primary" if view == "我的会话" else "secondary",
                width="stretch",
                key="agent-nav-mine",
            ):
                st.session_state.agent_view = "我的会话"
                st.rerun()
            if st.button(
                "工单审批",
                icon=":material/fact_check:",
                width="stretch",
                key="agent-nav-tickets",
            ):
                st.session_state.agent_view = "工单审批"
                st.rerun()

            st.caption(":material/sync: 3 秒自动同步")
            st.caption("当前接口提供待接管与已接管会话。")
            st.space("stretch")
            st.caption(f"当前客服：{st.session_state.agent_user['username']}")
            if st.button(
                "退出登录",
                icon=":material/logout:",
                width="stretch",
            ):
                logout()
                st.rerun(scope="app")

    with center:
        with st.container(key="agent-list"):
            st.markdown(f"### {view}")
            st.caption(f"共 {len(handoffs)} 个任务")
            search = st.text_input(
                "搜索会话",
                placeholder="搜索会话编号、原因或来源",
                key="agent_search",
            ).strip()
            filtered = [
                item
                for item in handoffs
                if not search
                or search.lower()
                in f"{item['session_id']} {item['reason']} {item['source']}".lower()
            ]

            if not filtered:
                st.info(
                    "没有符合搜索条件的会话。" if search else "当前队列为空。",
                    title="暂无任务",
                )
            else:
                with st.container(key="handoff-list", height=620):
                    for item in filtered:
                        item_id = item["id"]
                        is_selected = item_id == selected_handoff_id
                        with st.container(key=f"agent-handoff-{item_id}"):
                            if st.button(
                                f"会话 #{item['session_id']}",
                                key=f"select-handoff-{item_id}",
                                type="primary" if is_selected else "secondary",
                                width="stretch",
                            ):
                                st.session_state.agent_handoff_id = item_id
                                st.rerun()
                            st.caption(" ".join(item["reason"].split())[:48])
                            st.caption(
                                f"{handoff_status_label(item['status'])} · "
                                f"{format_timestamp(item['created_at'])}"
                            )

    with right:
        with st.container(key="agent-chat"):
            if handoff is None:
                st.info("从中间列表选择一个会话。", title="尚未选择会话")
                return

            if view == "待接管":
                with st.container(key="detail-card"):
                    st.markdown(f"### :material/pending_actions: 会话 #{handoff['session_id']}")
                    st.markdown(f"**转人工原因**  \n{handoff['reason']}")
                    st.caption(
                        f"来源：{SOURCE_LABELS.get(handoff['source'], handoff['source'])}"
                        f" · {format_timestamp(handoff['created_at'])}"
                    )
                    st.caption("接管后可查看完整对话、订单摘要并进行人工回复。")
                    if st.button(
                        "接管此会话",
                        icon=":material/assignment_ind:",
                        type="primary",
                        width="stretch",
                    ):
                        try:
                            client().claim_handoff(handoff["id"])
                            st.session_state.agent_switch_to_mine = True
                            st.rerun()
                        except ApiError as error:
                            show_error(error)
                return

            try:
                context = client().get_agent_session(handoff["session_id"])
            except ApiError as error:
                show_error(error)
                return

            chat_session = context["session"]
            with st.container(horizontal=True, horizontal_alignment="distribute"):
                st.markdown(f"### :material/forum: 会话 #{chat_session['id']}")
                st.markdown(f":green-badge[{status_label(chat_session['status'])}]")
            workflow = (
                "人工处理中"
                if chat_session["status"] == "human_active"
                else workflow_label(chat_session["workflow_state"])
            )
            st.caption(f"会话编号 #{chat_session['id']} · {workflow}")

            message_column, detail_column = st.columns([0.69, 0.31], gap="medium")
            with message_column:
                with st.container(key="message-scroll", height=500):
                    for message in context["messages"]:
                        render_message(message, staff_view=True)

                if chat_session["status"] != "closed":
                    with st.form("agent_reply_form", clear_on_submit=True):
                        reply = st.text_area(
                            "人工回复",
                            max_chars=4000,
                            height=110,
                            placeholder="输入回复内容",
                            key="agent_reply_text",
                        )
                        submitted = st.form_submit_button(
                            "发送回复",
                            icon=":material/send:",
                            type="primary",
                            width="stretch",
                        )
                    if submitted:
                        if not reply.strip():
                            st.warning("回复内容不能为空。")
                        else:
                            with st.spinner("正在发送人工回复..."):
                                try:
                                    client().reply_as_agent(
                                        handoff["session_id"],
                                        reply.strip(),
                                    )
                                    st.rerun()
                                except ApiError as error:
                                    show_error(error)
                else:
                    st.success("会话已关闭。", icon=":material/task_alt:")

            with detail_column:
                render_order_card(context.get("order"))
                st.space("medium")
                render_session_meta(chat_session)
                st.space("medium")
                st.markdown("#### 人工任务")
                st.caption(f"任务状态：{handoff_status_label(context['handoff']['status'])}")
                handoff_source = context["handoff"]["source"]
                st.caption(f"转人工来源：{SOURCE_LABELS.get(handoff_source, handoff_source)}")
                if chat_session["status"] != "closed":
                    if st.button(
                        "结束会话",
                        icon=":material/task_alt:",
                        width="stretch",
                    ):
                        try:
                            client().close_agent_session(handoff["session_id"])
                            st.rerun()
                        except ApiError as error:
                            show_error(error)


render_live_workspace()
