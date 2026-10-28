from sqlalchemy import func, select

from backend.app.core.security import hash_password, verify_password
from backend.app.db.session import Database
from backend.app.models import ChatSession, Handoff, Order, Product, User
from sample_data.seed import AGENT_PASSWORD, DEMO_PASSWORD, seed_demo_data


def test_seed_creates_complete_demo_dataset_idempotently():
    test_database = Database("sqlite+pysqlite:///:memory:")
    with test_database.engine.begin() as connection:
        from backend.app.models import Base

        Base.metadata.create_all(connection)

    with test_database.session_factory() as session:
        first_counts = seed_demo_data(session)
        second_counts = seed_demo_data(session)

        order = session.scalar(select(Order).where(Order.order_no == "A10086"))
        consumer = session.scalar(select(User).where(User.username == "consumer_demo"))
        agent = session.scalar(select(User).where(User.username == "agent_demo"))

        assert first_counts == {"users": 3, "products": 5, "orders": 5}
        assert second_counts == first_counts
        assert order is not None
        assert consumer is not None
        assert agent is not None
        assert order.user_id == consumer.id
        assert verify_password(DEMO_PASSWORD, consumer.password_hash)
        assert verify_password(AGENT_PASSWORD, agent.password_hash)
        assert DEMO_PASSWORD not in consumer.password_hash
        assert session.scalar(select(func.count()).select_from(ChatSession)) == 0
        assert session.scalar(select(func.count()).select_from(Handoff)) == 0
        assert session.scalar(select(func.count()).select_from(Product)) == 5

    test_database.dispose()


def test_password_hash_uses_unique_salts_and_rejects_wrong_password():
    first_hash = hash_password("correct-password")
    second_hash = hash_password("correct-password")

    assert first_hash != second_hash
    assert verify_password("correct-password", first_hash)
    assert not verify_password("wrong-password", first_hash)
    assert not verify_password("correct-password", "invalid-hash")
