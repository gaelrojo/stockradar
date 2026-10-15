# Retrospectiva — Sprint 1 (Base y dominio)

## Qué salió bien
- Las pruebas de cobertura se escribieron antes que la implementación y detectaron un fallo real: con ventas uniformes el IQR es 0 y cualquier día un poco más alto se marcaba como atípico. Se corrigió con el término de la mediana (ADR 0002).
- La migración inicial se valida automáticamente contra los modelos, así que escribirla a mano no deja huecos.

## Qué mejorar
- Docker no estaba instalado al empezar; Dockerfile y compose quedaron pendientes de probar en local hasta instalarlo; la migración se validó con un PostgreSQL temporal.

## Acuerdos
- _(completar en la revisión del sprint)_
