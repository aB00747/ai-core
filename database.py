import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config import settings

logger = logging.getLogger(__name__)

# Read-only connection to ERP database
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.erp_database_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def execute_read_query(query: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only SQL query against the ERP database."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            columns = list(result.keys())
            return [dict(zip(columns, row)) for row in result.fetchall()]
    except SQLAlchemyError as e:
        logger.error(f"Database query error: {e}")
        return []


def check_db_connection() -> bool:
    """Check if ERP database is reachable."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
