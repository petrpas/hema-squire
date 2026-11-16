"""The floor module's boundary (CLAUDE.md, Floor module; design add-floor-boundary D6).

The checker reads imports with `ast` and reports every one that crosses the
boundary. It takes file paths so its own tests can hand it offenders written to
a temporary tree, which is how each rule is shown to bite.
"""

import ast
import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]

# what `app.floor` may import from the rest of `app`
FLOOR_ALLOWED = ("app.db", "app.auth", "app.errors", "app.i18n", "app.config", "app.floor")
OFFICE_ADAPTER = ("app", "floor", "adapters", "office.py")
ROUTER_MOUNT = ("app", "main.py")


def _within(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def _imports(path: Path, parts: tuple[str, ...]) -> list[tuple[int, str]]:
    """Every module a file imports, as an absolute dotted name with its line.

    A relative import is resolved against the file's own package. A name
    imported from a module that is itself only a package root — `from app
    import x`, `from . import x` — is read as the submodule `x`, since that is
    what a package-level name almost always is here, and an attribute that is
    not a module still crosses the same boundary."""
    package = list(parts[:-1])
    tree = ast.parse(path.read_text(), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - (node.level - 1)]
                module = ".".join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ""
            if node.module is None or module == "app":
                found += [(node.lineno, f"{module}.{alias.name}") for alias in node.names]
            else:
                found.append((node.lineno, module))
    return found


def violations(paths: Iterable[Path], root: Path) -> list[str]:
    """Each import in `paths` that breaks a floor boundary rule, as
    `<file>:<line>: rule <n>: <module>`. `root` is the directory holding the
    `app` package, against which a file's package is read."""
    found: list[str] = []
    for path in paths:
        parts = path.resolve().relative_to(root.resolve()).parts
        if not parts or parts[0] != "app":
            continue
        in_floor = parts[:2] == ("app", "floor")
        in_engine = parts[:3] == ("app", "floor", "engine")
        is_port = parts == ("app", "floor", "roster.py")
        where = "/".join(parts)
        for line, module in _imports(path, parts):
            in_app = _within(module, "app")
            broken: list[int] = []
            if (
                in_floor
                and parts != OFFICE_ADAPTER
                and in_app
                and not any(_within(module, allowed) for allowed in FLOOR_ALLOWED)
            ):
                broken.append(1)
            if not in_floor and parts != ROUTER_MOUNT and _within(module, "app.floor"):
                broken.append(2)
            if in_engine and not (
                _within(module, "app.floor.engine")
                or module.split(".")[0] in sys.stdlib_module_names
            ):
                broken.append(3)
            if is_port and in_app:
                broken.append(4)
            found += [f"{where}:{line}: rule {rule}: {module}" for rule in broken]
    return found


def test_the_real_tree_keeps_the_boundary():
    paths = sorted((BACKEND / "app").rglob("*.py"))
    assert violations(paths, BACKEND) == []


def _tree(tmp_path: Path, files: dict[str, str]) -> list[Path]:
    paths = []
    for name, source in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        paths.append(path)
    return paths


def _rules(tmp_path: Path, files: dict[str, str]) -> set[int]:
    return {
        int(violation.split("rule ")[1].split(":")[0])
        for violation in violations(_tree(tmp_path, files), tmp_path)
    }


@pytest.mark.parametrize(
    "source",
    ["import app.models\n", "from app import models\n", "from .. import models\n"],
)
def test_rule_1_floor_reads_no_office_module(tmp_path, source):
    assert _rules(tmp_path, {"app/floor/api.py": source}) == {1}


@pytest.mark.parametrize(
    "source",
    ["import app.floor.api\n", "from app import floor\n", "from .floor import api\n"],
)
def test_rule_2_office_does_not_import_floor(tmp_path, source):
    assert _rules(tmp_path, {"app/entrants.py": source}) == {2}


@pytest.mark.parametrize(
    "source",
    [
        "import sqlalchemy\n",
        "import app.floor.roster\n",
        "from app.floor import roster\n",
        "from ... import db\n",
        "from .. import roster\n",
    ],
)
def test_rule_3_engine_is_pure(tmp_path, source):
    assert 3 in _rules(tmp_path, {"app/floor/engine/pools.py": source})


@pytest.mark.parametrize(
    "source",
    ["import app.db\n", "from app import config\n", "from . import api\n", "from .. import db\n"],
)
def test_rule_4_the_port_imports_nothing_from_app(tmp_path, source):
    assert 4 in _rules(tmp_path, {"app/floor/roster.py": source})


def test_the_two_exceptions_and_what_is_allowed(tmp_path):
    assert (
        _rules(
            tmp_path,
            {
                "app/floor/adapters/office.py": "from app import entrants, models\n",
                "app/main.py": "from app.floor import api\n",
                "app/floor/api.py": "from app.auth import require_console_access\n"
                "from app.floor.adapters import office\nfrom . import schemas\n",
                "app/floor/engine/pools.py": "import itertools\n"
                "from __future__ import annotations\n"
                "from . import seeding\nfrom app.floor.engine import rounds\n",
                "app/floor/roster.py": "from dataclasses import dataclass\n",
            },
        )
        == set()
    )
