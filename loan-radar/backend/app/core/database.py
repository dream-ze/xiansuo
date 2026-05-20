import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}
if settings.is_production:
    _engine_kwargs.update(pool_size=20, max_overflow=30, pool_timeout=30)
else:
    _engine_kwargs.update(pool_size=5, max_overflow=10)

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
