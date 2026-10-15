"""Modelo de dominio normalizado, independiente del POS y de cualquier framework."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class CoverageStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class CoverageThresholds:
    """Umbrales en días de cobertura; configurables por tienda."""

    critical_days: float = 3.0
    warning_days: float = 7.0

    def __post_init__(self) -> None:
        if self.critical_days <= 0:
            raise ValueError("critical_days debe ser mayor que 0")
        if self.warning_days < self.critical_days:
            raise ValueError("warning_days no puede ser menor que critical_days")


@dataclass(frozen=True, slots=True)
class CoverageResult:
    stock: float
    avg_daily_sales: float
    coverage_days: float
    status: CoverageStatus
    effective_window_days: int
    stock_anomaly: bool = False
    outlier_days_capped: int = 0


@dataclass(frozen=True, slots=True)
class Product:
    external_id: str
    name: str
    sku: str | None = None
    category: str | None = None
    supplier: str | None = None
    unit: str | None = None
    cost: Decimal | None = None
    price: Decimal | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class StockLevel:
    product_external_id: str
    quantity: float
    captured_at: datetime
    min_threshold: float | None = None


@dataclass(frozen=True, slots=True)
class SaleLine:
    product_external_id: str
    quantity: float  # negativa en devoluciones
    unit_price: Decimal


@dataclass(frozen=True, slots=True)
class Sale:
    external_id: str
    sold_at: datetime
    total: Decimal
    lines: tuple[SaleLine, ...] = field(default_factory=tuple)
