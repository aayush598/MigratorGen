"""
Async SQLAlchemy database setup for MigratorGen platform.
Provides async session management, connection pooling, and SaaS models.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID, uuid4

try:
    from sqlalchemy import (
        Column,
        DateTime,
        String,
        Integer,
        Text,
        Boolean,
        Float,
        Enum as SQLEnum,
        Index,
        ForeignKey,
        text,
    )
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSON, ARRAY
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
    from sqlalchemy.pool import AsyncAdaptedQueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    DeclarativeBase = None  # type: ignore

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# ── SaaS Models ─────────────────────────────────────────────────


class Tenant(Base):
    """
    Multi-tenant organization.

    Attributes:
        id: UUID primary key
        name: Display name
        slug: URL-safe identifier
        plan: Subscription tier (free, pro, enterprise)
        settings: JSONB for flexible tenant configuration
        is_active: Whether tenant is active
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    settings: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users: Mapped[List["User"]] = relationship("User", back_populates="tenant")
    api_keys: Mapped[List["APIKey"]] = relationship("APIKey", back_populates="tenant")


class User(Base):
    """
    Platform user belonging to a tenant.

    Attributes:
        id: UUID primary key
        tenant_id: Foreign key to tenants
        email: Unique email address
        password_hash: bcrypt hashed password
        name: Display name
        role: RBAC role (owner, admin, member, viewer)
        is_active: Whether user is active
        last_login: Last login timestamp
        created_at: Creation timestamp
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")


class APIKey(Base):
    """
    API key for programmatic access.

    Attributes:
        id: UUID primary key
        tenant_id: Foreign key to tenants
        user_id: Foreign key to users who created the key
        name: Human-readable name
        key_hash: SHA-256 hash of the raw key
        key_prefix: First 12 chars for display
        scopes: Allowed operations (migrate, read, write, admin)
        is_active: Whether key is active
        last_used_at: Last usage timestamp
        created_at: Creation timestamp
    """

    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    scopes: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=["migrate", "read"])
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="api_keys")


# ── Migration Models ────────────────────────────────────────────


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
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
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
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_activity: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    migration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AuditLog(Base):
    """
    Immutable audit trail for all mutations.

    Attributes:
        id: UUID primary key
        tenant_id: Multi-tenant identifier
        user_id: User who performed the action
        action: Action performed (create, update, delete, migrate)
        resource_type: Type of resource affected
        resource_id: ID of the resource affected
        details: JSONB with additional context
        ip_address: Client IP
        user_agent: Client user agent
        created_at: Action timestamp
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_audit_logs_tenant_action", "tenant_id", "action"),
        Index("ix_audit_logs_created", "created_at"),
    )


class BillingSubscription(Base):
    """
    Stripe subscription tracking.

    Attributes:
        id: UUID primary key
        tenant_id: Foreign key to tenants
        plan: Subscription plan (free, pro, enterprise)
        status: Subscription status (active, canceled, past_due)
        stripe_customer_id: Stripe customer ID
        stripe_subscription_id: Stripe subscription ID
        current_period_start: Current billing period start
        current_period_end: Current billing period end
        migration_count_this_period: Migrations used this period
        migration_limit: Max migrations per period
    """

    __tablename__ = "billing_subscriptions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    migration_count_this_period: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    migration_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)


# ── Engine & Session ────────────────────────────────────────────


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
