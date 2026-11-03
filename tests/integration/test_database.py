from sqlalchemy import text

from backend.app.db.session import Database


def test_database_session_can_connect():
    test_database = Database("sqlite+pysqlite:///:memory:")

    with test_database.engine.connect() as connection:
        result = connection.scalar(text("SELECT 1"))

    test_database.dispose()
    assert result == 1
