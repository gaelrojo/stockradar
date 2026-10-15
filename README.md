# StockRadar

API de inventario que se conecta al punto de venta (POS) que ya usa un negocio, sincroniza productos, existencias y ventas, y avisa cuando un producto **está por agotarse** según sus **días de cobertura** (stock ÷ venta diaria promedio), no según un mínimo fijo.

El POS sigue siendo la fuente de verdad: StockRadar solo lee, analiza y notifica.

> Estado: **Sprint 1 — base y dominio**. Conectores, autenticación y alertas llegan en los sprints 2 a 4 (ver [`docs/roadmap.md`](docs/roadmap.md)).

## Arranque rápido (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- API: <http://localhost:8000/health>
- Documentación interactiva: <http://localhost:8000/docs>

Al arrancar, el contenedor aplica las migraciones (`alembic upgrade head`).

## Desarrollo local

Requiere [uv](https://docs.astral.sh/uv/) (instala Python 3.12 por ti).

```bash
uv sync                          # dependencias + entorno virtual
docker compose up -d db          # solo PostgreSQL
uv run alembic upgrade head      # migraciones
uv run uvicorn app.main:app --reload
```

Calidad y pruebas (lo mismo que corre CI):

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run coverage run -m pytest && uv run coverage report   # falla bajo 80 %
```

Las pruebas de `tests/integration` necesitan `DATABASE_URL` apuntando a PostgreSQL; sin ella se omiten.

## Cómo se calcula la cobertura

```
venta_diaria_promedio = unidades_netas_en_ventana / días_de_la_ventana
días_de_cobertura     = stock_actual / venta_diaria_promedio
```

| Estado | Por defecto |
|---|---|
| crítico | < 3 días |
| atención | < 7 días |
| ok | resto, o sin ventas |

Ventana por defecto de 14 días. Los casos borde (productos nuevos, devoluciones, días atípicos, stock negativo) se explican en [ADR 0002](docs/adr/0002-reglas-de-cobertura.md).

## Estructura

```
app/
├── api/         routers FastAPI
├── core/        configuración
├── domain/      modelo normalizado y reglas de cobertura (sin dependencias de framework)
├── connectors/  conectores POS (Sprint 2)
├── services/    sincronización, alertas, notificaciones (Sprint 2-4)
├── db/          modelos SQLAlchemy y sesión
└── main.py
migrations/      Alembic
tests/           unit · api · integration · connectors
docs/            ADRs, roadmap y retrospectivas
```

La capa `domain` no importa FastAPI, SQLAlchemy ni httpx; una prueba (`tests/unit/test_architecture.py`) lo garantiza.
