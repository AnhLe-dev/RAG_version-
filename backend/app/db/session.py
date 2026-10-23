from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


SessionFactory = sessionmaker[Session]


def create_database_engine(
    settings: Settings,
) -> Engine:
    """Create a SQLAlchemy engine without exposing its URL."""

    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: Engine,
) -> SessionFactory:
    """Create sessions bound to one database engine."""

    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(
    session_factory: SessionFactory,
) -> Generator[Session, None, None]:
    """Commit successful work and roll back failed work."""

    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()