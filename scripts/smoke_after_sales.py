import json

from fastapi.testclient import TestClient

from backend.app.db.session import Database, get_db
from backend.app.main import app
from backend.app.models import Base
from sample_data.seed import AGENT_PASSWORD, DEMO_PASSWORD, seed_demo_data

MESSAGES = (
    "耳机坏了，想退货",
    "订单号 A10086",
    "左耳没有声音",
)


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def main() -> None:
    database = Database("sqlite+pysqlite:///:memory:")
    with database.engine.begin() as connection:
        Base.metadata.create_all(connection)

    def override_get_db():
        with database.session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with database.session_factory() as session:
            seed_demo_data(session)

        with TestClient(app) as client:
            consumer_headers = _login(
                client,
                "consumer_demo",
                DEMO_PASSWORD,
            )
            agent_headers = _login(
                client,
                "agent_demo",
                AGENT_PASSWORD,
            )
            created = client.post("/chat/sessions", headers=consumer_headers)
            created.raise_for_status()
            session_id = created.json()["id"]

            for message in MESSAGES:
                response = client.post(
                    f"/chat/sessions/{session_id}/messages",
                    headers=consumer_headers,
                    json={"content": message},
                )
                response.raise_for_status()
                result = response.json()
                print(
                    json.dumps(
                        {
                            "message": message,
                            "action": result["action"],
                            "workflow_state": result["workflow_state"],
                            "missing_slots": result["missing_slots"],
                            "assistant": (
                                result["assistant_message"]["content"]
                                if result["assistant_message"]
                                else None
                            ),
                        },
                        ensure_ascii=False,
                    )
                )

            handoff_session = client.post(
                "/chat/sessions",
                headers=consumer_headers,
            ).json()
            handoff = client.post(
                f"/chat/sessions/{handoff_session['id']}/handoff",
                headers=consumer_headers,
                json={"reason": "冒烟测试人工申请"},
            )
            handoff.raise_for_status()
            queue = client.get("/agent/handoffs", headers=agent_headers)
            queue.raise_for_status()
            print(
                json.dumps(
                    {
                        "handoff_source": handoff.json()["source"],
                        "handoff_status": handoff.json()["status"],
                        "pending_queue_count": len(queue.json()),
                    },
                    ensure_ascii=False,
                )
            )
    finally:
        app.dependency_overrides.clear()
        database.dispose()


if __name__ == "__main__":
    main()
