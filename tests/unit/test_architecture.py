"""El dominio no debe depender de frameworks ni librerías de infraestructura."""

import ast
from pathlib import Path

import pytest

DOMAIN_DIR = Path(__file__).parents[2] / "app" / "domain"
FORBIDDEN = {"fastapi", "sqlalchemy", "httpx", "pydantic", "alembic", "asyncpg", "pandas"}


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("path", sorted(DOMAIN_DIR.glob("*.py")), ids=lambda p: p.name)
def test_domain_has_no_framework_imports(path: Path) -> None:
    assert not _imported_roots(path) & FORBIDDEN
