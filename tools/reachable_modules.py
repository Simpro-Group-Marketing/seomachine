"""List data_sources/modules files that no keep-list entrypoint can reach.

The walk follows absolute, relative, and bare sibling imports (the modules also
run as scripts with their own directory on sys.path), including imports inside
try/except ImportError fallbacks, plus string literals that name a module.
Entrypoints are the keep-list globs, repo scripts and tools, and every module a
command, skill, agent, rule, context doc, or CI workflow references.

Usage: python tools/reachable_modules.py [--root DIR] [--exclude PATH ...]
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

MODULE_DIR = Path("data_sources") / "modules"
KEEP_GLOBS = (
    "data_sources/modules/production/**/*.py",
    "data_sources/modules/content_scoring/**/*.py",
    "data_sources/modules/context_build/**/*.py",
    "data_sources/modules/content_scorer.py",
    "data_sources/modules/seo_quality_rater.py",
    "data_sources/modules/aeo_geo_rater.py",
    "data_sources/modules/wordpress_publisher.py",
    "data_sources/modules/grav_publisher.py",
    "data_sources/modules/customer_proof_selector.py",
    "data_sources/modules/nonvault_customer_proof_selector.py",
    "data_sources/modules/fred_authority_selector.py",
    "data_sources/modules/paa_provenance_guard.py",
    "data_sources/modules/content_scrubber.py",
    "data_sources/modules/google_analytics.py",
    "data_sources/modules/google_search_console.py",
    "data_sources/modules/dataforseo.py",
    "data_sources/modules/data_aggregator.py",
    "data_sources/modules/opportunity_scorer.py",
    "scripts/*.py",
    "tools/*.py",
)
DOC_GLOBS = (
    ".claude/commands/*.md",
    ".claude/skills/**/*.md",
    ".claude/agents/*.md",
    ".claude/rules/*.md",
    "context/*.md",
    "README.md",
    ".github/workflows/*.yml",
)
_PATH_REF = re.compile(r"data_sources/modules/[\w/.-]*\w")
_DOTTED_REF = re.compile(r"data_sources\.modules(?:\.\w+)+")


def _module_files(root: Path) -> list[Path]:
    return sorted((root / MODULE_DIR).rglob("*.py"))


def _dotted_to_path(root: Path, dotted: str) -> Path | None:
    base = root.joinpath(*dotted.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def _ref_to_paths(root: Path, ref: str) -> list[Path]:
    """Resolve a slash path or dotted name to module files (a directory means all of it)."""
    ref = ref.removesuffix(".py").replace(".", "/") if "/" not in ref else ref
    target = root / ref
    if target.is_dir():
        return sorted(target.rglob("*.py"))
    for candidate in (target, target.with_suffix(".py") if target.suffix != ".py" else target):
        if candidate.is_file():
            return [candidate]
    path = _dotted_to_path(root, ref.replace("/", "."))
    return [path] if path else []


def _package_of(root: Path, path: Path) -> list[str]:
    parts = list(path.relative_to(root).with_suffix("").parts)
    return parts if path.name == "__init__.py" else parts[:-1]


def _relative_targets(root: Path, path: Path, node: ast.ImportFrom) -> list[str]:
    package = _package_of(root, path)
    if path.name == "__init__.py":
        package = package[:-1]
    base = package[: len(package) - (node.level - 1)] if node.level > 1 else package
    stem = ".".join(base + ([node.module] if node.module else []))
    return [stem] + [f"{stem}.{alias.name}" for alias in node.names]


def _absolute_targets(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    assert isinstance(node, ast.ImportFrom) and node.module
    return [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]


def _bare_paths(root: Path, path: Path, name: str) -> list[Path]:
    first = name.split(".")[0]
    found = []
    for directory in (path.parent, root / MODULE_DIR):
        found += [p for p in (directory / f"{first}.py", directory / first / "__init__.py") if p.is_file()]
    return found


def _import_names(root: Path, path: Path, tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level:
            names += _relative_targets(root, path, node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names += _absolute_targets(node)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names += _DOTTED_REF.findall(node.value)
    return names


def _edges(root: Path, path: Path) -> set[Path]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    targets: set[Path] = set()
    for name in _import_names(root, path, tree):
        if name.startswith("data_sources"):
            resolved = _dotted_to_path(root, name)
            targets |= {resolved} if resolved else set()
        else:
            targets |= set(_bare_paths(root, path, name))
    return targets


def _with_parents(root: Path, path: Path) -> set[Path]:
    found = {path}
    for parent in path.parents:
        if parent == root:
            break
        init = parent / "__init__.py"
        if init.is_file():
            found.add(init)
    return found


def reachable(root: str | Path, entrypoints: Iterable[str | Path]) -> set[Path]:
    """Return every module file transitively imported from the entrypoints."""
    root = Path(root).resolve()
    pending = [(root / p).resolve() for p in entrypoints if (root / p).is_file()]
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        pending.extend(p.resolve() for p in _with_parents(root, path) | _edges(root, path) if p.resolve() not in seen)
    return seen


def doc_references(root: str | Path) -> set[Path]:
    """Module files named by docs, rules, skills, agents, and CI workflows."""
    root = Path(root).resolve()
    found: set[Path] = set()
    for pattern in DOC_GLOBS:
        for doc in root.glob(pattern):
            text = doc.read_text(encoding="utf-8", errors="replace")
            for ref in _PATH_REF.findall(text) + _DOTTED_REF.findall(text):
                found |= {p.resolve() for p in _ref_to_paths(root, ref)}
    return found


def entrypoints(root: str | Path, exclude: Sequence[str] = ()) -> list[Path]:
    root = Path(root).resolve()
    excluded = {(root / item).resolve() for item in exclude}
    paths = {p.resolve() for pattern in KEEP_GLOBS for p in root.glob(pattern)}
    paths |= doc_references(root)
    return sorted(p for p in paths if p not in excluded)


def unreachable(root: str | Path, starts: Iterable[str | Path]) -> list[Path]:
    root = Path(root).resolve()
    kept = reachable(root, starts)
    return [p.resolve() for p in _module_files(root) if p.resolve() not in kept]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    parser.add_argument("--exclude", action="append", default=[], help="Entrypoint path to ignore (repeatable).")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    starts = entrypoints(root, args.exclude)
    for path in unreachable(root, starts):
        print(path.relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
