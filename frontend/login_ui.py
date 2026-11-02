from pathlib import Path

import streamlit as st

_ASSET_PATH = Path(__file__).resolve().parent / "assets" / "login_illustration.svg"


def render_login_screen(
    *,
    role: str,
    brand_title: str,
    subtitle: str,
    account_hint: str,
) -> tuple[str, str, bool]:
    """Render the shared split-screen login layout."""

    left, right = st.columns([1.12, 0.88], gap="large", vertical_alignment="center")

    with left:
        st.image(
            str(_ASSET_PATH),
            width=380,
            alt="智能客服通过对话、订单和政策知识协同处理售后问题",
        )
        st.badge(
            "AI 售后协同",
            icon=":material/auto_awesome:",
            color="blue",
        )
        st.title(brand_title)
        st.caption(subtitle)
        st.markdown(
            ":material/verified: **订单事实与知识库分离**  \n"
            ":material/security: **身份与订单归属由后端校验**  \n"
            ":material/support_agent: **AI 与人工客服连续协同**"
        )

    with right:
        with st.container(border=True):
            st.badge(
                role,
                icon=":material/account_circle:",
                color="gray",
            )
            st.header("登录你的账户", icon=":material/login:")
            st.caption(f"使用{role}账号继续。")
            with st.form(f"{role}_login_form"):
                username = st.text_input(
                    "用户名",
                    placeholder="请输入用户名",
                    key=f"{role}_username",
                )
                password = st.text_input(
                    "密码",
                    type="password",
                    placeholder="请输入密码",
                    key=f"{role}_password",
                )
                submitted = st.form_submit_button(
                    "安全登录",
                    icon=":material/arrow_forward:",
                    type="primary",
                    width="stretch",
                )
            st.caption(account_hint)

    return username.strip(), password, submitted
