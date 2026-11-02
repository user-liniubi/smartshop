import streamlit as st

from frontend.api_client import ApiClient, ApiError

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


st.title("SmartShop 售后服务")
st.caption("从已有订单开始处理退货、换货、保修和订单问题")

if st.session_state.consumer_token is None:
    with st.form("consumer_login", border=False):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button(
            "登录",
            icon=":material/login:",
        )

    if submitted:
        try:
            login = ApiClient().login(username.strip(), password)
            if login["user"]["role"] != "consumer":
                st.error("请使用消费者账号登录", title="角色不匹配")
            else:
                st.session_state.consumer_token = login["access_token"]
                st.session_state.consumer_user = login["user"]
                st.rerun()
        except ApiError as error:
            show_error(error)
    st.stop()

with st.sidebar:
    st.subheader(st.session_state.consumer_user["username"])
    st.caption("消费者账号")
    if st.button("新建会话", icon=":material/add:", width="stretch"):
        try:
            created = client().create_session()
            st.session_state.consumer_session_id = created["id"]
            st.rerun()
        except ApiError as error:
            show_error(error)
    if st.button("退出登录", icon=":material/logout:", width="stretch"):
        logout()
        st.rerun()

try:
    sessions = client().list_sessions()
except ApiError as error:
    show_error(error)
    st.stop()

if not sessions:
    st.info("还没有售后会话，请点击左侧“新建会话”。", title="暂无会话")
    st.stop()

session_by_id = {session["id"]: session for session in sessions}
if st.session_state.get("consumer_session_id") not in session_by_id:
    st.session_state.consumer_session_id = sessions[0]["id"]
selected_id = st.selectbox(
    "选择会话",
    options=list(session_by_id),
    format_func=lambda session_id: (
        f"会话 #{session_id} · {session_by_id[session_id]['workflow_state']}"
    ),
    key="consumer_session_id",
)
selected = session_by_id[selected_id]

status = selected["status"]
if status == "need_human":
    st.warning("已提交人工申请，正在等待客服接管。", title="等待人工客服")
elif status == "human_active":
    st.info("当前由人工客服处理，你的消息仍会保存。", title="人工处理中")
elif status == "closed":
    st.success("本次售后会话已关闭。", title="会话已关闭")

with st.container(horizontal=True):
    st.caption(f"工作流：{selected['workflow_state']}")
    st.caption(f"会话状态：{status}")

try:
    messages = client().get_messages(selected_id)
except ApiError as error:
    show_error(error)
    st.stop()

for message in messages:
    sender = message["sender_type"]
    role = "assistant" if sender in {"assistant", "agent", "system"} else "user"
    avatar = ":material/support_agent:" if sender == "agent" else None
    with st.chat_message(role, avatar=avatar):
        if sender == "agent":
            st.caption("人工客服")
        st.write(message["content"])
        citations = message.get("citations_json") or []
        if citations:
            with st.expander("查看来源", icon=":material/menu_book:"):
                for citation in citations:
                    st.markdown(f"**{citation['title']}** · `{citation['filename']}`")
                    st.caption(citation["excerpt"])

if status in {"open", "human_active"}:
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button(
            "申请人工客服",
            icon=":material/support_agent:",
            disabled=status != "open",
        ):
            try:
                client().request_handoff(selected_id, "消费者主动申请人工客服")
                st.rerun()
            except ApiError as error:
                show_error(error)

prompt = st.chat_input(
    "描述你的售后问题",
    disabled=status == "closed",
    submit_mode="disable",
    key="consumer_chat_input",
)
if prompt:
    try:
        result = client().send_message(selected_id, prompt)
        if result["assistant_message"] is None:
            st.info("消息已发送，请等待人工客服回复。", title="等待客服")
        st.rerun()
    except ApiError as error:
        show_error(error)
