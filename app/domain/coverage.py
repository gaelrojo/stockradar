"""Cálculo de días de cobertura. Funciones puras; las reglas se explican en docs/adr/0002."""

import math
import statistics
from collections.abc import Iterable, Sequence
from datetime import date, timedelta

from app.domain.models import CoverageResult, CoverageStatus, CoverageThresholds

DEFAULT_WINDOW_DAYS = 14
# Con menos días con venta no hay base estadística para declarar un día atípico.
MIN_SALE_DAYS_FOR_OUTLIERS = 4
IQR_FACTOR = 1.5
# Con ventas muy uniformes el IQR es ~0; exigir también superar N veces la mediana.
MEDIAN_FACTOR = 2.0


def classify(coverage_days: float, thresholds: CoverageThresholds) -> CoverageStatus:
    if coverage_days < thresholds.critical_days:
        return CoverageStatus.CRITICAL
    if coverage_days < thresholds.warning_days:
        return CoverageStatus.WARNING
    return CoverageStatus.OK


def aggregate_daily_units(
    lines: Iterable[tuple[date, float]], *, as_of: date, window_days: int
) -> list[float]:
    """Suma unidades netas por día en la ventana que termina en `as_of` (inclusive).

    Devuelve `window_days` valores, del más antiguo al más reciente, con ceros en días sin venta.
    """
    start = as_of - timedelta(days=window_days - 1)
    daily = [0.0] * window_days
    for day, quantity in lines:
        if start <= day <= as_of:
            daily[(day - start).days] += quantity
    return daily


def _cap_outliers(daily: list[float]) -> tuple[list[float], int]:
    sale_days = [units for units in daily if units > 0]
    if len(sale_days) < MIN_SALE_DAYS_FOR_OUTLIERS:
        return daily, 0
    q1, median, q3 = statistics.quantiles(sale_days, n=4, method="inclusive")
    cap = max(q3 + IQR_FACTOR * (q3 - q1), MEDIAN_FACTOR * median)
    capped = [min(units, cap) for units in daily]
    return capped, sum(1 for units in daily if units > cap)


def compute_coverage(
    stock: float,
    daily_units: Sequence[float],
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    history_days: int | None = None,
    thresholds: CoverageThresholds | None = None,
) -> CoverageResult:
    """Calcula la cobertura de un producto.

    `daily_units` son las unidades netas por día, de la más antigua a la más reciente.
    `history_days` son los días desde que existe el producto; acota la ventana en productos nuevos.
    """
    if window_days < 1:
        raise ValueError("window_days debe ser al menos 1")
    thresholds = thresholds or CoverageThresholds()

    window = window_days if history_days is None else max(1, min(window_days, history_days))
    recent = list(daily_units[-window:])
    padded = [0.0] * (window - len(recent)) + recent
    # Un día con devoluciones mayores que sus ventas no genera demanda negativa.
    daily = [max(units, 0.0) for units in padded]
    daily, outliers = _cap_outliers(daily)

    stock_anomaly = stock < 0
    effective_stock = max(stock, 0.0)
    avg_daily_sales = sum(daily) / window
    coverage_days = effective_stock / avg_daily_sales if avg_daily_sales > 0 else math.inf

    return CoverageResult(
        stock=effective_stock,
        avg_daily_sales=avg_daily_sales,
        coverage_days=coverage_days,
        status=classify(coverage_days, thresholds),
        effective_window_days=window,
        stock_anomaly=stock_anomaly,
        outlier_days_capped=outliers,
    )
