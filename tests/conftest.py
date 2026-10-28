import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import Database, get_db
from backend.app.main import app
from backend.app.models import Base
from sample_data.seed import seed_demo_data


@pytest.fixture
def test_database():
    test_db = Database("sqlite+pysqlite:///:memory:")
    with test_db.engine.begin() as connection:
        Base.metadata.create_all(connection)
    yield test_db
    test_db.dispose()


@pytest.fixture
def client(test_database):
    def override_get_db():
        with test_database.session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(client, test_database):
    with test_database.session_factory() as session:
        seed_demo_data(session)
    return client
