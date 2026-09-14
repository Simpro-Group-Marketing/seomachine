"""AST import-architecture checks for production Python packages."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Mapping, Sequence


TERMINAL_FACADE_PATHS = frozenset(
    {
        "data_sources/modules/aeo_geo_rater.py",
        "data_sources/modules/blog_assembly_bom.py",
        "data_sources/modules/blog_assembly_bom_guard.py",
        "data_sources/modules/blog_assembly_bom_preflight_session.py",
        "data_sources/modules/blog_assembly_bom_reviews.py",
        "data_sources/modules/blog_assembly_bom_session.py",
        "data_sources/modules/blog_assembly_bom_snapshot.py",
        "data_sources/modules/blog_release.py",
        "data_sources/modules/content_scorer.py",
        "data_sources/modules/customer_proof_diversity_guard.py",
        "data_sources/modules/customer_proof_evidence.py",
        "data_sources/modules/customer_proof_selector.py",
        "data_sources/modules/editorial_plan_guard.py",
        "data_sources/modules/editorial_plan_snapshot.py",
        "data_sources/modules/nonvault_customer_proof_selector.py",
        "data_sources/modules/paa_provenance_guard.py",
        "data_sources/modules/publish_readiness.py",
        "data_sources/modules/publish_readiness_core.py",
        "data_sources/modules/seo_quality_rater.py",
        "mcp-gsc/gsc_server.py",
    }
)


def import_architecture_errors(
    files: Sequence[Path],
    *,
    root: Path,
) -> list[str]:
    modules = _module_paths(files, root=root)
    facades = {
        module
        for module, path in modules.items()
        if path in TERMINAL_FACADE_PATHS
    }
    edges: dict[str, set[str]] = {module: set() for module in modules}
    errors: list[str] = []
    for module, relative_path in sorted(modules.items(), key=lambda item: item[1]):
        path = root / relative_path
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative_path)
        except SyntaxError:
            continue
        for target, line in _import_targets(
            tree,
            module=module,
            is_package=path.name == "__init__.py",
        ):
            resolved = _resolve_module(target, modules)
            if resolved is None or resolved == module:
                continue
            edges[module].add(resolved)
            if resolved in facades and module not in facades:
                errors.append(
                    f"{relative_path}:{line} imports terminal facade "
                    f"{modules[resolved]}"
                )
    for component in _strong_components(edges):
        labels = " -> ".join(modules[module] for module in sorted(component))
        errors.append(f"production import cycle: {labels}")
    return sorted(errors)


def _module_paths(files: Sequence[Path], *, root: Path) -> dict[str, str]:
    modules: dict[str, str] = {}
    for path in files:
        relative = path.resolve().relative_to(root).as_posix()
        module = _module_name(relative)
        if module is not None:
            modules[module] = relative
    return modules


def _module_name(relative: str) -> str | None:
    if relative.startswith("data_sources/modules/"):
        module = "data_sources.modules." + relative[
            len("data_sources/modules/"):-3
        ].replace("/", ".")
    elif relative.startswith("mcp-gsc/mcp_gsc/"):
        module = "mcp_gsc." + relative[len("mcp-gsc/mcp_gsc/"):-3].replace("/", ".")
    elif relative == "mcp-gsc/gsc_server.py":
        module = "gsc_server"
    elif relative.startswith("scripts/"):
        module = "scripts." + relative[len("scripts/"):-3].replace("/", ".")
    elif relative.startswith("tools/"):
        module = "tools." + relative[len("tools/"):-3].replace("/", ".")
    else:
        return None
    return module[:-9] if module.endswith(".__init__") else module


def _import_targets(
    tree: ast.Module,
    *,
    module: str,
    is_package: bool,
) -> tuple[tuple[str, int], ...]:
    targets: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from_import(
                module,
                level=node.level,
                imported_module=node.module,
                is_package=is_package,
            )
            targets.append((base, node.lineno))
            targets.extend(
                (
                    f"{base}.{alias.name}" if base else alias.name,
                    node.lineno,
                )
                for alias in node.names
                if alias.name != "*"
            )
    return tuple(targets)


def _resolve_from_import(
    module: str,
    *,
    level: int,
    imported_module: str | None,
    is_package: bool,
) -> str:
    if level == 0:
        return imported_module or ""
    package_parts = module.split(".") if is_package else module.split(".")[:-1]
    base_parts = package_parts[: max(0, len(package_parts) - level + 1)]
    if imported_module:
        base_parts.extend(imported_module.split("."))
    return ".".join(base_parts)


def _resolve_module(target: str, modules: Mapping[str, str]) -> str | None:
    parts = target.split(".")
    while parts:
        candidate = ".".join(parts)
        if candidate in modules:
            return candidate
        parts.pop()
    return None


def _strong_components(graph: Mapping[str, set[str]]) -> list[set[str]]:
    return _Tarjan(graph).components()


class _Tarjan:
    def __init__(self, graph: Mapping[str, set[str]]) -> None:
        self.graph = graph
        self.indexes: dict[str, int] = {}
        self.lowlinks: dict[str, int] = {}
        self.stack: list[str] = []
        self.on_stack: set[str] = set()
        self.result: list[set[str]] = []

    def components(self) -> list[set[str]]:
        for node in sorted(self.graph):
            if node not in self.indexes:
                self._visit(node)
        return self.result

    def _visit(self, node: str) -> None:
        self.indexes[node] = len(self.indexes)
        self.lowlinks[node] = self.indexes[node]
        self.stack.append(node)
        self.on_stack.add(node)
        for target in self.graph[node]:
            self._follow_edge(node, target)
        if self.lowlinks[node] == self.indexes[node]:
            self._close_component(node)

    def _follow_edge(self, node: str, target: str) -> None:
        if target not in self.indexes:
            self._visit(target)
            self.lowlinks[node] = min(self.lowlinks[node], self.lowlinks[target])
        elif target in self.on_stack:
            self.lowlinks[node] = min(self.lowlinks[node], self.indexes[target])

    def _close_component(self, node: str) -> None:
        component: set[str] = set()
        while True:
            target = self.stack.pop()
            self.on_stack.remove(target)
            component.add(target)
            if target == node:
                break
        if len(component) > 1:
            self.result.append(component)


__all__ = ["TERMINAL_FACADE_PATHS", "import_architecture_errors"]
