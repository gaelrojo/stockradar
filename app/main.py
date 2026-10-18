from fastapi import FastAPI

from app.api import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Inventario con alertas por días de cobertura, conectable a cualquier POS.",
    )
    app.include_router(health.router)
    return app


app = create_app()
