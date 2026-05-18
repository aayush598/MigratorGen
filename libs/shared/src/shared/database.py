"""
Async SQLAlchemy database setup for MigratorGen platform.
Provides async session management, connection pooling, and core models.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import UUID, uuid4

try:
    from sqlalchemy import (
        Column,
        DateTime,
        String,
        Integer,
        Text,
        Boolean,
        Enum as SQLEnum,
        Index,
        text,
    )
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSON
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from sqlalchemy.pool import AsyncAdaptedQueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    DeclarativeBase = None  # type: ignore

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


class MigrationJob(Base):
    """
    Tracks migration job history and status.

    Attributes:
        id: UUID primary key
        tenant_id: Multi-tenant identifier
        user_id: User who initiated the migration
        status: Job status (pending, running, completed, failed, cancelled)
        source_version: Source library version
        target_version: Target library version
        input_path: Path to input file/directory
        output_path: Path to output
        rules_applied: JSON list of applied rule IDs
        bytes_processed: Total bytes processed
        duration_ms: Migration duration in milliseconds
        error_message: Error message if failed
        confidence_score: Average confidence score
        ip_address: Client IP address
        user_agent: Client user agent
        created_at: Job creation timestamp
        completed_at: Job completion timestamp
    """

    __tablename__ = "migration_jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_version: Mapped[str] = mapped_column(String(32), nullable=False)
    target_version: Mapped[str] = mapped_column(String(32), nullable=False)
    input_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rules_applied: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    bytes_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_migration_jobs_status_created", "status", "created_at"),
        Index("ix_migration_jobs_tenant_created", "tenant_id", "created_at"),
    )


class MigrationSession(Base):
    """
    Tracks migration session for analytics.

    Attributes:
        id: UUID primary key
        tenant_id: Multi-tenant identifier
        user_id: User identifier
        ip_address: Client IP
        created_at: Session creation
        last_activity: Last activity timestamp
        migration_count: Number of migrations in session
        total_bytes: Total bytes processed
    """

    __tablename__ = "migration_sessions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    migration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def create_engine(url: str, pool_size: int = 20, max_overflow: int = 10) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine.

    Args:
        url: Database URL (e.g., postgresql+asyncpg://...)
        pool_size: Base pool size
        max_overflow: Max pool overflow connections

    Returns:
        AsyncEngine instance
    """
    global _engine

    if not SQLALCHEMY_AVAILABLE:
        raise ImportError("SQLAlchemy with async support is required")

    _engine = create_async_engine(
        url,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )
    return _engine


def get_engine() -> Optional[AsyncEngine]:
    """Get the current engine instance."""
    return _engine


async def init_db(url: Optional[str] = None, create_tables: bool = True) -> AsyncEngine:
    """
    Initialize the database connection.

    Args:
        url: Database URL (uses DATABASE_URL env var if not provided)
        create_tables: If True, create all tables

    Returns:
        AsyncEngine instance
    """
    import os

    if url is None:
        url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://migrator_user:change-me@localhost:5432/migrator_platform",
        )

    engine = create_engine(url)

    if create_tables and SQLALCHEMY_AVAILABLE:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    global _session_maker
    _session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    logger.info("Database initialized", pool_size=20)
    return engine


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session as a context manager.

    Usage:
        async with get_session() as session:
            result = await session.execute(select(MigrationJob))
    """
    if _session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_maker
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_maker = None
        logger.info("Database connections closed")