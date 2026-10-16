from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def is_sqlite_database_url(database_url: str) -> bool:
    return database_url.strip().lower().startswith("sqlite")


def create_sqlalchemy_engine(database_url: str) -> Engine:
    engine_kwargs: dict[str, object] = {"future": True}

    if is_sqlite_database_url(database_url):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_pre_ping"] = True

    return create_engine(database_url, **engine_kwargs)


settings = get_settings()
engine = create_sqlalchemy_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
