from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings


class Database:
    """Own a SQLAlchemy engine and session factory."""

    def __init__(self, url: str, *, echo: bool = False) -> None:
        engine_options: dict[str, object] = {
            "echo": echo,
            "pool_pre_ping": not url.startswith("sqlite"),
        }
        if url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
            if ":memory:" in url:
                engine_options["poolclass"] = StaticPool

        self.engine = create_engine(url, **engine_options)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )

    def dispose(self) -> None:
        self.engine.dispose()

    def get_engine(self) -> Engine:
        return self.engine


settings = get_settings()
database = Database(settings.database_url, echo=settings.database_echo)


def get_db() -> Generator[Session, None, None]:
    """Yield one request-scoped database session."""

    with database.session_factory() as session:
        yield session
