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
    assert app.title[0].value == "SmartShop 售后服务"
    assert len(app.text_input) == 2
    assert app.button[0].label == "登录"


def test_agent_login_page_renders():
    app = AppTest.from_file(
        str(ROOT / "frontend" / "agent_app.py"),
        default_timeout=15,
    ).run()

    assert not app.exception
    assert app.title[0].value == "SmartShop 客服工作台"
    assert len(app.text_input) == 2
    assert app.button[0].label == "登录"


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
    assert any("工作流：resolved" in caption.value for caption in app.caption)


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
    assert any(button.label == "接管会话" for button in app.button)
