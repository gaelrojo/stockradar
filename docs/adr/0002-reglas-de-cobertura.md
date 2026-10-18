# ADR 0002 — Reglas del cálculo de días de cobertura

- Estado: aceptada
- Fecha: 2026-10-14
- Código: `app/domain/coverage.py` · Pruebas: `tests/unit/test_coverage.py`

## Contexto
La sección 6 del brief define la fórmula y exige pruebas para varios casos borde, pero no dice cómo tratarlos.

## Decisión

| Caso | Regla |
|---|---|
| Ventana | 14 días por defecto (configurable, p. ej. 30). Días sin ventas cuentan como 0. |
| Sin ventas en la ventana | Cobertura infinita → **ok**. |
| Producto nuevo | Ventana efectiva = `min(ventana, días de historial)`, mínimo 1, para no diluir la demanda real. |
| Stock 0 con ventas | Cobertura 0 → **crítico**. |
| Devoluciones | Se netean por día. Un día con neto negativo cuenta como 0: una devolución no "crea" stock futuro ni cancela la demanda de otros días. |
| Días atípicos | Si hay al menos 4 días con venta, cada día se recorta a `max(Q3 + 1.5·IQR, 2 × mediana)` de los días con venta. Los días en cero no entran al cálculo para no castigar productos de baja rotación; el término de la mediana evita recortar variaciones normales cuando las ventas son muy uniformes (IQR ≈ 0). |
| Stock negativo del POS | Se trata como 0 y se marca `stock_anomaly=True` para revisarlo. |
| Umbrales | crítico < 3 días, atención < 7 días; configurables por tienda (`alert_rules`). Se valida que `0 < crítico ≤ atención`. |

El cálculo es una función pura sin dependencias externas (solo `statistics` de la librería estándar); la agregación por día recibe pares `(fecha, cantidad)` ya convertidos a la zona horaria de la tienda.

## Consecuencias
- Un evento puntual (pedido grande) no dispara alertas falsas, pero una tendencia sostenida sí se refleja.
- Con menos de 4 días con venta no se recorta nada; es preferible una alerta de más a ocultar demanda real.
- Las constantes (`MIN_SALE_DAYS_FOR_OUTLIERS`, `IQR_FACTOR`, `MEDIAN_FACTOR`) pueden volverse configurables si un cliente lo necesita.
