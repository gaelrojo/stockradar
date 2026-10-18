"""Pruebas de la lógica de días de cobertura (sección 6 del brief)."""

import math
from datetime import date, timedelta

import pytest

from app.domain.coverage import aggregate_daily_units, classify, compute_coverage
from app.domain.models import CoverageStatus, CoverageThresholds

AS_OF = date(2026, 10, 14)


class TestClassify:
    @pytest.mark.parametrize(
        ("coverage_days", "expected"),
        [
            (0.0, CoverageStatus.CRITICAL),
            (2.99, CoverageStatus.CRITICAL),
            (3.0, CoverageStatus.WARNING),
            (6.99, CoverageStatus.WARNING),
            (7.0, CoverageStatus.OK),
            (math.inf, CoverageStatus.OK),
        ],
    )
    def test_default_thresholds(self, coverage_days: float, expected: CoverageStatus) -> None:
        assert classify(coverage_days, CoverageThresholds()) is expected

    def test_custom_thresholds_per_store(self) -> None:
        thresholds = CoverageThresholds(critical_days=5, warning_days=10)
        assert classify(4, thresholds) is CoverageStatus.CRITICAL
        assert classify(8, thresholds) is CoverageStatus.WARNING
        assert classify(10, thresholds) is CoverageStatus.OK

    @pytest.mark.parametrize(("critical", "warning"), [(0, 7), (-1, 7), (8, 7)])
    def test_invalid_thresholds_rejected(self, critical: float, warning: float) -> None:
        with pytest.raises(ValueError):
            CoverageThresholds(critical_days=critical, warning_days=warning)


class TestComputeCoverage:
    def test_regular_sales(self) -> None:
        # 2 unidades diarias durante 14 días, 10 en stock -> 5 días de cobertura.
        result = compute_coverage(10, [2.0] * 14)
        assert result.avg_daily_sales == pytest.approx(2.0)
        assert result.coverage_days == pytest.approx(5.0)
        assert result.status is CoverageStatus.WARNING
        assert result.effective_window_days == 14
        assert not result.stock_anomaly

    def test_default_window_is_14_days(self) -> None:
        # Las ventas fuera de los últimos 14 días no cuentan.
        daily = [100.0] * 16 + [1.0] * 14
        result = compute_coverage(70, daily)
        assert result.avg_daily_sales == pytest.approx(1.0)
        assert result.coverage_days == pytest.approx(70.0)

    def test_window_30_days(self) -> None:
        result = compute_coverage(30, [1.0] * 30, window_days=30)
        assert result.effective_window_days == 30
        assert result.coverage_days == pytest.approx(30.0)

    def test_shorter_series_is_zero_filled(self) -> None:
        # Solo hay 7 días con datos en una ventana de 14: los faltantes cuentan como 0.
        result = compute_coverage(14, [2.0] * 7)
        assert result.avg_daily_sales == pytest.approx(1.0)
        assert result.coverage_days == pytest.approx(14.0)

    def test_product_without_sales_has_infinite_coverage(self) -> None:
        result = compute_coverage(25, [0.0] * 14)
        assert math.isinf(result.coverage_days)
        assert result.avg_daily_sales == 0
        assert result.status is CoverageStatus.OK

    def test_empty_history_has_infinite_coverage(self) -> None:
        result = compute_coverage(25, [])
        assert math.isinf(result.coverage_days)
        assert result.status is CoverageStatus.OK

    def test_new_product_uses_only_its_history(self) -> None:
        # Producto dado de alta hace 3 días que vende 4 diarias: no se diluye en 14 días.
        result = compute_coverage(8, [0.0] * 11 + [4.0] * 3, history_days=3)
        assert result.effective_window_days == 3
        assert result.avg_daily_sales == pytest.approx(4.0)
        assert result.coverage_days == pytest.approx(2.0)
        assert result.status is CoverageStatus.CRITICAL

    def test_new_product_history_is_at_least_one_day(self) -> None:
        result = compute_coverage(5, [5.0], history_days=0)
        assert result.effective_window_days == 1
        assert result.coverage_days == pytest.approx(1.0)

    def test_history_longer_than_window_is_capped(self) -> None:
        result = compute_coverage(14, [1.0] * 14, history_days=400)
        assert result.effective_window_days == 14

    def test_zero_stock_with_sales_is_critical(self) -> None:
        result = compute_coverage(0, [3.0] * 14)
        assert result.coverage_days == 0
        assert result.status is CoverageStatus.CRITICAL

    def test_returns_are_netted_within_the_day(self) -> None:
        # Último día: vende 5 y le devuelven 2 -> neto 3.
        daily = [2.0] * 13 + [5.0 - 2.0]
        result = compute_coverage(10, daily)
        assert result.avg_daily_sales == pytest.approx((13 * 2 + 3) / 14)

    def test_net_negative_day_counts_as_zero(self) -> None:
        daily = [1.0] * 13 + [-5.0]
        result = compute_coverage(13, daily)
        assert result.avg_daily_sales == pytest.approx(13 / 14)

    def test_only_returns_means_no_demand(self) -> None:
        result = compute_coverage(10, [0.0] * 12 + [-2.0, -1.0])
        assert math.isinf(result.coverage_days)
        assert result.status is CoverageStatus.OK

    def test_outlier_day_is_capped(self) -> None:
        # Un día con venta excepcional (p. ej. un pedido de evento) no debe disparar la media.
        daily = [2.0, 3.0, 2.0, 3.0, 2.0, 3.0, 2.0, 3.0, 2.0, 3.0, 2.0, 3.0, 2.0, 200.0]
        result = compute_coverage(50, daily)
        assert result.outlier_days_capped == 1
        # Días con venta: Q1=2, mediana=2.5, Q3=3 -> tope = max(3 + 1.5, 2 * 2.5) = 5
        assert result.avg_daily_sales == pytest.approx((7 * 2 + 6 * 3 + 5) / 14)
        assert result.status is CoverageStatus.OK

    def test_sparse_sales_are_not_treated_as_outliers(self) -> None:
        # Producto de baja rotación: muchos días en cero no deben anular sus ventas.
        daily = [0.0] * 10 + [5.0, 0.0, 6.0, 0.0]
        result = compute_coverage(11, daily)
        assert result.outlier_days_capped == 0
        assert result.avg_daily_sales == pytest.approx(11 / 14)

    def test_too_few_sale_days_skip_outlier_capping(self) -> None:
        daily = [0.0] * 11 + [1.0, 1.0, 50.0]
        result = compute_coverage(52, daily)
        assert result.outlier_days_capped == 0
        assert result.avg_daily_sales == pytest.approx(52 / 14)

    def test_negative_stock_is_flagged_and_treated_as_zero(self) -> None:
        result = compute_coverage(-4, [1.0] * 14)
        assert result.stock_anomaly
        assert result.stock == 0
        assert result.coverage_days == 0
        assert result.status is CoverageStatus.CRITICAL

    def test_negative_stock_without_sales(self) -> None:
        result = compute_coverage(-1, [0.0] * 14)
        assert result.stock_anomaly
        assert math.isinf(result.coverage_days)

    def test_invalid_window_rejected(self) -> None:
        with pytest.raises(ValueError):
            compute_coverage(1, [1.0], window_days=0)

    def test_uses_given_thresholds(self) -> None:
        result = compute_coverage(
            10, [2.0] * 14, thresholds=CoverageThresholds(critical_days=6, warning_days=9)
        )
        assert result.status is CoverageStatus.CRITICAL


class TestAggregateDailyUnits:
    def test_groups_and_nets_by_day_zero_filled(self) -> None:
        lines = [
            (AS_OF, 2.0),
            (AS_OF, 1.0),
            (AS_OF - timedelta(days=2), 4.0),
            (AS_OF - timedelta(days=2), -1.0),  # devolución
        ]
        assert aggregate_daily_units(lines, as_of=AS_OF, window_days=4) == [0.0, 3.0, 0.0, 3.0]

    def test_ignores_lines_outside_window(self) -> None:
        lines = [
            (AS_OF - timedelta(days=3), 9.0),  # fuera de una ventana de 3 días
            (AS_OF + timedelta(days=1), 9.0),  # futuro
            (AS_OF - timedelta(days=2), 1.0),
        ]
        assert aggregate_daily_units(lines, as_of=AS_OF, window_days=3) == [1.0, 0.0, 0.0]

    def test_end_to_end_with_compute(self) -> None:
        lines = [(AS_OF - timedelta(days=i), 2.0) for i in range(14)]
        daily = aggregate_daily_units(lines, as_of=AS_OF, window_days=14)
        assert compute_coverage(6, daily).status is CoverageStatus.WARNING
