"""The dependency rule: a layer never imports an outer layer (or, at the core, a framework)."""

import ast
from pathlib import Path

import pytest

import app

APP_ROOT = Path(app.__file__).parent
FRAMEWORKS = ("fastapi", "starlette", "sqlalchemy", "alembic", "asyncpg", "uvicorn")
OUTER = ("app.interface", "app.infrastructure", "app.config")
FORBIDDEN: dict[str, tuple[str, ...]] = {
    "domain": ("app.usecases", *OUTER, *FRAMEWORKS),
    "usecases": (*OUTER, *FRAMEWORKS),
    "interface": ("app.infrastructure", "app.config"),
    "shared": ("app.domain", "app.usecases", *OUTER, *FRAMEWORKS),
}


def _imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_respects_dependency_rule(layer: str) -> None:
    violations = [
        f"{path.relative_to(APP_ROOT)} imports {module}"
        for path in sorted((APP_ROOT / layer).rglob("*.py"))
        for module in sorted(_imported_modules(path))
        if any(_is_within(module, package) for package in FORBIDDEN[layer])
    ]
    assert violations == []
