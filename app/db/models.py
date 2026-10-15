"""Modelos SQLAlchemy (sección 5 del brief)."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models import CoverageStatus


def _enum(enum_cls: type[StrEnum], name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"


class SyncStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole, "user_role"), default=UserRole.VIEWER)


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="America/Mexico_City")


class POSConnection(Base):
    __tablename__ = "pos_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    connector_type: Mapped[str] = mapped_column(String(50))
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Credenciales cifradas por la aplicación; nunca se guardan en texto plano.
    encrypted_credentials: Mapped[bytes | None] = mapped_column(LargeBinary)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("connection_id", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("pos_connections.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(100))
    sku: Mapped[str | None] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str | None] = mapped_column(String(150))
    supplier: Mapped[str | None] = mapped_column(String(200))
    unit: Mapped[str | None] = mapped_column(String(30))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockLevel(Base):
    __tablename__ = "stock_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    # Numeric para admitir productos a granel (kg, litros) y stock negativo reportado por el POS.
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    min_threshold: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (UniqueConstraint("connection_id", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("pos_connections.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(100))
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class SaleLine(Base):
    __tablename__ = "sale_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))  # negativa en devoluciones
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        CheckConstraint("coverage_days_critical > 0", name="critical_positive"),
        CheckConstraint("coverage_days_warning >= coverage_days_critical", name="warning_gte"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), unique=True)
    coverage_days_critical: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal(3))
    coverage_days_warning: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal(7))
    channels_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    level: Mapped[CoverageStatus] = mapped_column(_enum(CoverageStatus, "coverage_status"))
    coverage_days: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # NULL = infinita
    message: Mapped[str] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("pos_connections.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[SyncStatus] = mapped_column(
        _enum(SyncStatus, "sync_status"), default=SyncStatus.RUNNING
    )
    records: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
