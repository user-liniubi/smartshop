import streamlit as st

try:
    from frontend.api_client import ApiClient, ApiError
except ModuleNotFoundError:
    from api_client import ApiClient, ApiError

st.set_page_config(
    page_title="SmartShop 客服工作台",
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


st.title("SmartShop 客服工作台")
st.caption("查看待接管会话、接管、回复并关闭售后任务")

if st.session_state.agent_token is None:
    with st.form("agent_login", border=False):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button(
            "登录",
            icon=":material/login:",
        )

    if submitted:
        try:
            login = ApiClient().login(username.strip(), password)
            if login["user"]["role"] != "agent":
                st.error("请使用客服账号登录", title="角色不匹配")
            else:
                st.session_state.agent_token = login["access_token"]
                st.session_state.agent_user = login["user"]
                st.rerun()
        except ApiError as error:
            show_error(error)
    st.stop()

with st.sidebar:
    st.subheader(st.session_state.agent_user["username"])
    st.caption("客服账号")
    if st.button("刷新队列", icon=":material/refresh:", width="stretch"):
        st.rerun()
    if st.button("退出登录", icon=":material/logout:", width="stretch"):
        logout()
        st.rerun()

if st.session_state.agent_switch_to_mine:
    st.session_state.agent_view = "我的会话"
    st.session_state.agent_switch_to_mine = False

view = st.segmented_control(
    "工作视图",
    options=["待接管", "我的会话"],
    default="待接管",
    key="agent_view",
    required=True,
)

try:
    handoffs = client().list_pending_handoffs() if view == "待接管" else client().list_my_handoffs()
except ApiError as error:
    show_error(error)
    st.stop()

if not handoffs:
    if view == "待接管":
        st.info("当前没有待接管会话。", title="队列为空")
    else:
        st.info("当前没有你已接管的会话。", title="暂无会话")
    st.stop()

handoff_by_id = {handoff["id"]: handoff for handoff in handoffs}
if st.session_state.get("agent_handoff_id") not in handoff_by_id:
    st.session_state.agent_handoff_id = handoffs[0]["id"]
selected_handoff_id = st.selectbox(
    "选择人工任务",
    options=list(handoff_by_id),
    format_func=lambda handoff_id: (
        f"任务 #{handoff_id} · 会话 #{handoff_by_id[handoff_id]['session_id']} "
        f"· {handoff_by_id[handoff_id]['reason']}"
    ),
    key="agent_handoff_id",
)
handoff = handoff_by_id[selected_handoff_id]

if view == "待接管":
    if st.button("接管会话", icon=":material/assignment_ind:", type="primary"):
        try:
            client().claim_handoff(selected_handoff_id)
            st.session_state.agent_switch_to_mine = True
            st.rerun()
        except ApiError as error:
            show_error(error)
    st.stop()

try:
    context = client().get_agent_session(handoff["session_id"])
except ApiError as error:
    show_error(error)
    st.stop()

chat_session = context["session"]
with st.container(horizontal=True):
    st.metric("会话状态", chat_session["status"], border=True)
    st.metric("工作流", chat_session["workflow_state"], border=True)
    st.metric("人工任务", context["handoff"]["status"], border=True)

with st.container(border=True):
    st.subheader("任务上下文")
    st.write(f"转人工原因：{context['handoff']['reason']}")
    st.write(f"转人工来源：{context['handoff']['source']}")
    order = context.get("order")
    if order:
        st.write(f"订单：{order['order_no']} · {order['status']} · {order['product']['name']}")
    else:
        st.caption("当前会话还没有可展示的订单摘要。")

for message in context["messages"]:
    sender = message["sender_type"]
    role = "assistant" if sender in {"assistant", "agent", "system"} else "user"
    avatar = ":material/support_agent:" if sender == "agent" else None
    with st.chat_message(role, avatar=avatar):
        if sender == "agent":
            st.caption("人工客服")
        st.write(message["content"])

if chat_session["status"] != "closed":
    with st.form("agent_reply_form", clear_on_submit=True):
        reply = st.text_area(
            "人工回复",
            max_chars=4000,
            height=120,
            placeholder="输入回复内容",
        )
        submitted = st.form_submit_button(
            "发送回复",
            icon=":material/send:",
        )
    if submitted:
        if not reply.strip():
            st.warning("回复内容不能为空。")
        else:
            try:
                client().reply_as_agent(handoff["session_id"], reply.strip())
                st.rerun()
            except ApiError as error:
                show_error(error)

    if st.button("关闭会话", icon=":material/task_alt:"):
        try:
            client().close_agent_session(handoff["session_id"])
            st.rerun()
        except ApiError as error:
            show_error(error)
else:
    st.success("人工会话已关闭。", title="已完成")
