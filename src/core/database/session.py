"""
Database connection and session management for Agentic CRAG Launchpad
"""

import os
from contextlib import contextmanager
from typing import Optional
from sqlalchemy import create_engine as sa_create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system environment variables

from .models import Base


# ===========================================
# DATABASE CONNECTION & SESSION MANAGEMENT
# ===========================================

def get_database_url(context_id: Optional[str] = None) -> str:
    """Get database URL for specific context or default"""
    base_url = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/knowledge_base')

    if context_id:
        # Per-context database mode
        if base_url.endswith('/'):
            # Pattern: DATABASE_URL ends with /
            return f"{base_url}{context_id}"
        else:
            # Pattern: DATABASE_URL includes database name
            # Extract base and append context_id
            if '/knowledge_base' in base_url:
                base_url = base_url.replace('/knowledge_base', '/')
                return f"{base_url}{context_id}"
            else:
                # Fallback: assume it's a complete URL and can't support per-context
                raise ValueError("DATABASE_URL format incompatible with per-context mode. Use base URL ending with '/'.")
    else:
        # Default mode: use knowledge_base
        if base_url.endswith('/'):
            return f"{base_url}knowledge_base"
        else:
            return base_url


def create_engine(context_id: Optional[str] = None):
    """Create SQLAlchemy engine with PostgreSQL driver"""
    return sa_create_engine(
        get_database_url(context_id),
        echo=False,  # Set to True for debugging
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections every hour
    )


# Session factory cache by database URL
_session_factories = {}


def _get_session_factory(database_url: str):
    """Get or create session factory for specific database URL"""
    if database_url not in _session_factories:
        engine = create_engine_from_url(database_url)
        _session_factories[database_url] = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
    return _session_factories[database_url]


def create_engine_from_url(database_url: str):
    """Create SQLAlchemy engine from database URL"""
    return sa_create_engine(
        database_url,
        echo=False,  # Set to True for debugging
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections every hour
    )


@contextmanager
def get_db_session(context_id: Optional[str] = None):
    """Get database session for specific context with automatic cleanup"""
    database_url = get_database_url(context_id)
    session_factory = _get_session_factory(database_url)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(context_id: Optional[str] = None):
    """Initialize database tables"""
    engine = create_engine(context_id)
    Base.metadata.create_all(bind=engine)


def drop_database(context_id: Optional[str] = None):
    """Drop all database tables (for testing/migrations)"""
    engine = create_engine(context_id)

    # Manually drop tables in correct order to avoid foreign key constraints
    with engine.connect() as conn:
        try:
            # Disable foreign key checks temporarily
            conn.execute(text("SET CONSTRAINTS ALL DEFERRED;"))
            conn.commit()

            # Drop tables in reverse dependency order
            tables_to_drop = [
                'knowledge_chunks',
                'conversations'  # If using conversation history
            ]

            for table_name in tables_to_drop:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))
                    conn.commit()
                except Exception:
                    # Continue if table doesn't exist or can't be dropped
                    pass

        except Exception:
            # If manual dropping fails, fall back to SQLAlchemy's method
            pass

    # Final fallback: use SQLAlchemy's drop_all (may still fail on foreign keys)
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        # If that fails too, just continue - tables might not exist
        pass


def reset_database(context_id: Optional[str] = None):
    """Reset database (drop all tables and recreate)"""
    drop_database(context_id)
    init_database(context_id)

