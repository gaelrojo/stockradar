# ADR 0001 — Stack base y gestor de dependencias `uv`

- Estado: aceptada
- Fecha: 2026-10-14

## Contexto
El brief fija Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, pytest, ruff y mypy. Falta decidir el gestor de dependencias y el driver de base de datos. El equipo de desarrollo solo tenía Python 3.9 instalado.

## Decisión
- **uv** como gestor: instala Python 3.12 sin tocar el sistema, genera `uv.lock` reproducible y es el más rápido en CI (`astral-sh/setup-uv`). Alternativas: Poetry (más lento, no gestiona la versión de Python), pip-tools (sin lock multiplataforma).
- **SQLAlchemy asíncrono + asyncpg**: los conectores serán `async` (contrato `POSConnector`), así que la sesión de base de datos también lo es para no bloquear el event loop.
- **Migración inicial escrita a mano** y verificada por `tests/integration/test_migrations.py`, que compara el esquema migrado con los modelos (`alembic.autogenerate.compare_metadata`); CI falla si divergen.
- Dependencias de Sprint 1, cada una con su motivo:
  - `fastapi`, `uvicorn[standard]`: API y servidor ASGI.
  - `pydantic-settings`: configuración por variables de entorno.
  - `sqlalchemy[asyncio]`, `asyncpg`, `alembic`: ORM, driver y migraciones.
  - dev: `pytest`, `pytest-asyncio`, `coverage`, `ruff`, `mypy`, `httpx` (requerido por `fastapi.testclient`).
  - pandas, respx, JWT y passlib se agregan en el sprint que los usa.

## Consecuencias
- Quien clone el repo solo necesita `uv` (y Docker para la base).
- Starlette emite una advertencia de obsolescencia al usar `httpx` en su `TestClient`; no afecta y se revisará al actualizar FastAPI.
