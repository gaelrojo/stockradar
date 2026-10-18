# Roadmap

## Sprints del MVP
- [x] **Sprint 1 — Base y dominio**: estructura, herramientas, Docker, CI, cálculo de cobertura, modelo de datos y migración inicial.
- [ ] **Sprint 2 — Conectores**: `POSConnector`, registro, DTOs, CSV/Excel, REST genérico por YAML/JSON, sincronización incremental e idempotente.
- [ ] **Sprint 3 — API, alertas y conector real**: JWT y roles, endpoints, motor de alertas, conector dedicado.
- [ ] **Sprint 4 — Notificaciones, reportes y entrega**: correo y webhook, reportes y pedido sugerido, despliegue, documentación final.

## Preguntas abiertas
1. ¿Con qué POS se hace el conector dedicado (Loyverse, Epos Now…) y hay cuenta de pruebas? — se decide al iniciar el Sprint 3.
2. ¿Cuántos productos y sucursales maneja el cliente de ejemplo?
3. ¿Quién recibe las alertas y por qué canal?
4. ¿Dónde se despliega la primera versión (AWS EC2 + Nginx o Render)?

Resueltas: base de datos → PostgreSQL 16.

## Trabajo futuro (fuera del MVP, no se implementa)
- App móvil y notificaciones push (FCM), Telegram.
- Predicción de demanda con machine learning y estacionalidad.
- Pedidos automáticos a proveedores.
- Facturación.
- Webhooks del POS como disparador de sincronización (el sondeo periódico siempre queda como respaldo).
