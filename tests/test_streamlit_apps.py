from pathlib import Path

from streamlit.testing.v1 import AppTest

from frontend.api_client import ApiClient

ROOT = Path(__file__).resolve().parents[1]


def test_consumer_login_page_renders():
    app = AppTest.from_file(
        str(ROOT / "frontend" / "consumer_app.py"),
        default_timeout=15,
    ).run()

    assert not app.exception
    assert app.title[0].value == "SmartService AI"
    assert len(app.text_input) == 2
    assert len(app.image) == 1
    assert app.button[0].label == "安全登录"


def test_agent_login_page_renders():
    app = AppTest.from_file(
        str(ROOT / "frontend" / "agent_app.py"),
        default_timeout=15,
    ).run()

    assert not app.exception
    assert app.title[0].value == "SmartService AI"
    assert len(app.text_input) == 2
    assert len(app.image) == 1
    assert app.button[0].label == "安全登录"


def test_consumer_authenticated_view_renders_history(monkeypatch):
    monkeypatch.setattr(
        ApiClient,
        "list_sessions",
        lambda self: [
            {
                "id": 7,
                "status": "open",
                "intent": "return_request",
                "slots_json": {"order_no": "A10086"},
                "workflow_state": "resolved",
                "created_at": "2026-10-31T08:00:00",
                "updated_at": "2026-10-31T08:00:01",
            }
        ],
    )
    monkeypatch.setattr(
        ApiClient,
        "get_messages",
        lambda self, session_id: [
            {
                "id": 1,
                "sender_type": "consumer",
                "content": "耳机保修多久？",
                "citations_json": [],
                "created_at": "2026-10-31T08:00:00",
            },
            {
                "id": 2,
                "sender_type": "assistant",
                "content": "降噪耳机提供十二个月质保。[1]",
                "citations_json": [
                    {
                        "document_id": 2,
                        "chunk_id": "[1] 2:1",
                        "filename": "warranty_policy.md",
                        "title": "质保规则",
                        "page": None,
                        "heading": "各品类期限",
                        "excerpt": "降噪耳机提供十二个月质保。",
                        "similarity": 0.9,
                    }
                ],
                "created_at": "2026-10-31T08:00:01",
            },
        ],
    )
    monkeypatch.setattr(
        ApiClient,
        "get_order_by_number",
        lambda self, order_no: {
            "id": 1,
            "order_no": order_no,
            "status": "delivered",
            "product": {
                "id": 1,
                "name": "SmartShop 降噪耳机 Pro",
                "description": "演示商品",
            },
            "created_at": "2026-10-31T08:00:00",
        },
    )
    app = AppTest.from_file(
        str(ROOT / "frontend" / "consumer_app.py"),
        default_timeout=15,
    )
    app.session_state["consumer_token"] = "test-token"
    app.session_state["consumer_user"] = {
        "id": 1,
        "username": "consumer_demo",
        "role": "consumer",
    }
    app.run()

    assert not app.exception
    assert any("当前阶段：已解决" in caption.value for caption in app.caption)
    assert any("3 秒自动同步" in caption.value for caption in app.caption)


def test_agent_pending_view_renders_claim_action(monkeypatch):
    monkeypatch.setattr(
        ApiClient,
        "list_pending_handoffs",
        lambda self: [
            {
                "id": 4,
                "session_id": 9,
                "status": "pending",
                "source": "user",
                "reason": "需要人工核实",
                "agent_id": None,
                "claimed_at": None,
                "closed_at": None,
                "created_at": "2026-10-31T08:00:00",
            }
        ],
    )
    monkeypatch.setattr(
        ApiClient,
        "list_my_handoffs",
        lambda self: [],
    )
    app = AppTest.from_file(
        str(ROOT / "frontend" / "agent_app.py"),
        default_timeout=15,
    )
    app.session_state["agent_token"] = "test-token"
    app.session_state["agent_user"] = {
        "id": 3,
        "username": "agent_demo",
        "role": "agent",
    }
    app.run()

    assert not app.exception
    assert any(button.label == "接管此会话" for button in app.button)
    assert any("3 秒自动同步" in caption.value for caption in app.caption)


def test_agent_claimed_view_renders_context_and_reply_form(monkeypatch):
    handoff = {
        "id": 4,
        "session_id": 9,
        "status": "claimed",
        "source": "user",
        "reason": "需要人工核实",
        "agent_id": 3,
        "claimed_at": "2026-10-31T08:00:00",
        "closed_at": None,
        "created_at": "2026-10-31T08:00:00",
    }
    monkeypatch.setattr(ApiClient, "list_pending_handoffs", lambda self: [])
    monkeypatch.setattr(ApiClient, "list_my_handoffs", lambda self: [handoff])
    monkeypatch.setattr(
        ApiClient,
        "get_agent_session",
        lambda self, session_id: {
            "session": {
                "id": session_id,
                "status": "human_active",
                "intent": "return_request",
                "slots_json": {"order_no": "A10086", "product_id": 1},
                "workflow_state": "need_human",
                "created_at": "2026-10-31T08:00:00",
                "updated_at": "2026-10-31T08:00:01",
            },
            "messages": [
                {
                    "id": 1,
                    "sender_type": "consumer",
                    "content": "左耳没有声音，想退货",
                    "citations_json": [],
                    "created_at": "2026-10-31T08:00:00",
                }
            ],
            "handoff": handoff,
            "order": {
                "id": 1,
                "order_no": "A10086",
                "status": "delivered",
                "product": {
                    "id": 1,
                    "name": "SmartShop 降噪耳机 Pro",
                    "description": "演示商品",
                },
                "created_at": "2026-10-31T08:00:00",
            },
        },
    )
    app = AppTest.from_file(
        str(ROOT / "frontend" / "agent_app.py"),
        default_timeout=15,
    )
    app.session_state["agent_token"] = "test-token"
    app.session_state["agent_user"] = {
        "id": 3,
        "username": "agent_demo",
        "role": "agent",
    }
    app.session_state["agent_view"] = "我的会话"
    app.run()

    assert not app.exception
    assert any(button.label == "发送回复" for button in app.button)
    assert any(button.label == "结束会话" for button in app.button)
