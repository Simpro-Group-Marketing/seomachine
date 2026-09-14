"""Enforce declining Python size and cyclomatic-complexity baselines."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "config" / "python-structure-baseline.json"
SCHEMA = "simpro-python-structure-baseline/v2"
PRODUCTION_ROOTS = ("data_sources", "scripts", "tools", "mcp-gsc")
REQUIRED_PRODUCTION_PATHS = (
    "mcp-gsc/gsc_server.py",
    "mcp-gsc/mcp_gsc/__init__.py",
)
EXCLUDED_PRODUCTION_DIRECTORIES = frozenset(
    {
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "venv",
    }
)
C901_PATTERN = re.compile(r"`([^`]+)` is too complex \((\d+) > 10\)")
SUBPROCESS_BOUNDARY = "data_sources/modules/artifact_runtime/subprocesses.py"
SUBPROCESS_CALLS = frozenset({"Popen", "call", "check_call", "check_output", "run"})


def production_line_errors(
    current: Mapping[str, int],
    baseline: Mapping[str, int],
    *,
    maximum: int,
) -> list[str]:
    errors: list[str] = []
    for path, allowed in sorted(baseline.items()):
        count = current.get(path)
        if count is None:
            errors.append(f"{path} is absent; remove its stale line baseline")
        elif count < allowed:
            errors.append(
                f"{path} improved to {count} lines; lower its stale {allowed}-line baseline"
            )
        elif count > allowed:
            errors.append(f"{path} grew from {allowed} to {count} physical lines")
    for path, count in sorted(current.items()):
        if count > maximum and path not in baseline:
            errors.append(
                f"{path} has {count} lines; new production files are limited to {maximum}"
            )
    return sorted(errors)


def complexity_errors(
    current: Mapping[str, Mapping[str, int]],
    baseline: Mapping[str, Mapping[str, int]],
) -> list[str]:
    errors: list[str] = []
    for path, functions in sorted(baseline.items()):
        current_functions = current.get(path, {})
        for name, allowed in sorted(functions.items()):
            value = current_functions.get(name)
            if value is None:
                errors.append(
                    f"{path}:{name} no longer violates C901; remove its stale baseline"
                )
            elif value < allowed:
                errors.append(
                    f"{path}:{name} improved to complexity {value}; "
                    f"lower its stale {allowed} baseline"
                )
            elif value > allowed:
                errors.append(f"{path}:{name} complexity grew from {allowed} to {value}")
    for path, functions in sorted(current.items()):
        known = baseline.get(path, {})
        for name, value in sorted(functions.items()):
            if name not in known:
                errors.append(f"{path}:{name} is a new C901 violation at complexity {value}")
    return sorted(errors)


def forbidden_structure_errors(sources: Mapping[str, str]) -> list[str]:
    """Reject namespace coupling that defeats explicit package ownership."""
    errors: list[str] = []
    for path, source in sorted(sources.items()):
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            continue
        reported: set[tuple[int, str]] = set()
        module_aliases, call_aliases = _subprocess_aliases(tree)
        for node in ast.walk(tree):
            namespace_message = _namespace_structure_message(node)
            if namespace_message is not None:
                reported.add((node.lineno, namespace_message))
            if _is_subprocess_call(node, path, module_aliases, call_aliases):
                reported.add((node.lineno, "bypasses bounded subprocess execution"))
        errors.extend(
            f"{path}:{line} {message}" for line, message in sorted(reported)
        )
    return sorted(errors)


def _namespace_structure_message(node: ast.AST) -> str | None:
    if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
        return "uses a wildcard import"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "globals":
            return "uses globals() for dynamic dispatch"
    if isinstance(node, ast.Assign) and any(
        _contains_sys_modules(target) for target in node.targets
    ):
        return "uses sys.modules for dynamic dispatch"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "get" and _is_sys_modules(node.func.value):
            return "uses sys.modules for dynamic dispatch"
    return None


def _is_subprocess_call(
    node: ast.AST,
    path: str,
    module_aliases: set[str],
    call_aliases: set[str],
) -> bool:
    if path == SUBPROCESS_BOUNDARY or not isinstance(node, ast.Call):
        return False
    return _is_subprocess_attribute_call(node, path, module_aliases) or (
        isinstance(node.func, ast.Name) and node.func.id in call_aliases
    )


def _subprocess_aliases(tree: ast.Module) -> tuple[set[str], set[str]]:
    modules = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "subprocess"
    }
    calls = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "subprocess"
        for alias in node.names
        if alias.name in SUBPROCESS_CALLS
    }
    return modules, calls


def _is_subprocess_attribute_call(
    node: ast.Call,
    path: str,
    module_aliases: set[str],
) -> bool:
    function = node.func
    return (
        path != SUBPROCESS_BOUNDARY
        and isinstance(function, ast.Attribute)
        and function.attr in SUBPROCESS_CALLS
        and isinstance(function.value, ast.Name)
        and function.value.id in module_aliases
    )


def _contains_sys_modules(node: ast.AST) -> bool:
    return any(_is_sys_modules(candidate) for candidate in ast.walk(node))


def _is_sys_modules(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "modules"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _production_lines(root: Path) -> dict[str, int]:
    return {
        path.relative_to(root).as_posix(): _physical_lines(path)
        for path in _production_files(root)
    }


def _production_files(root: Path) -> tuple[Path, ...]:
    files: set[Path] = set()
    for directory in PRODUCTION_ROOTS:
        base = root / directory
        if not base.is_dir():
            raise ValueError(f"production root is missing: {directory}")
        files.update(
            path
            for path in base.rglob("*.py")
            if not _is_excluded_production_path(path.relative_to(root))
        )
    for relative in REQUIRED_PRODUCTION_PATHS:
        if not (root / relative).is_file():
            raise ValueError(f"required production path is missing: {relative}")
    return tuple(sorted(files))


def _is_excluded_production_path(relative: Path) -> bool:
    directories = relative.parts[:-1]
    if "__pycache__" in directories:
        return True
    if not relative.parts or relative.parts[0].casefold() != "mcp-gsc":
        return False
    return any(
        part.casefold() in EXCLUDED_PRODUCTION_DIRECTORIES
        or part.casefold().endswith(".egg-info")
        for part in directories
    )


def _test_lines(root: Path) -> dict[str, int]:
    return {
        path.relative_to(root).as_posix(): _physical_lines(path)
        for path in sorted((root / "tests").rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def _complexities(root: Path) -> dict[str, dict[str, int]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from data_sources.modules.artifact_runtime.subprocesses import (
        run_bounded_text_process,
    )

    ruff = shutil.which("ruff")
    if ruff is None:
        raise ValueError("ruff is required for the structure check")
    targets = list(PRODUCTION_ROOTS[:-1])
    targets.extend(
        path.relative_to(root).as_posix()
        for path in _production_files(root)
        if path.relative_to(root).parts[0] == "mcp-gsc"
    )
    completed = run_bounded_text_process(
        [
            ruff,
            "check",
            *targets,
            "--select",
            "C901",
            "--output-format",
            "json",
        ],
        cwd=root,
        timeout=120,
        max_output_bytes=8 * 1024 * 1024,
    )
    if completed.returncode not in {0, 1}:
        raise ValueError(completed.stderr.strip() or "ruff complexity scan failed")
    rows: dict[str, dict[str, int]] = {}
    for finding in json.loads(completed.stdout or "[]"):
        match = C901_PATTERN.fullmatch(str(finding.get("message", "")))
        if match is None:
            raise ValueError("ruff returned an unrecognized C901 finding")
        path = Path(str(finding["filename"])).resolve().relative_to(root).as_posix()
        name, raw_value = match.groups()
        if name in rows.setdefault(path, {}):
            raise ValueError(f"duplicate C901 function name requires disambiguation: {path}:{name}")
        rows[path][name] = int(raw_value)
    return rows


def _errors(root: Path, baseline: Mapping[str, Any]) -> list[str]:
    maximum = int(baseline["maximum_lines"])
    lines = _production_lines(root)
    oversized = {path: count for path, count in lines.items() if count > maximum}
    errors = production_line_errors(
        oversized,
        _int_map(baseline.get("oversized_production_files")),
        maximum=maximum,
    )
    errors.extend(
        complexity_errors(
            _complexities(root),
            _nested_int_map(baseline.get("complexity_violations")),
        )
    )
    errors.extend(
        forbidden_structure_errors(
            {
                path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
                for path in _production_files(root)
            }
        )
    )
    errors.extend(_test_line_errors(_test_lines(root), baseline, maximum=maximum))
    return sorted(errors)


def _test_line_errors(
    current: Mapping[str, int],
    baseline: Mapping[str, Any],
    *,
    maximum: int,
) -> list[str]:
    allowed = _int_map(baseline.get("test_file_lines"))
    errors: list[str] = []
    for path, count in sorted(current.items()):
        previous = allowed.get(path)
        if previous is not None and count > previous:
            errors.append(f"{path} grew from its {previous}-line test baseline to {count}")
        elif previous is None and count > maximum:
            errors.append(f"{path} has {count} lines; new test files are limited to {maximum}")
    return errors


def _baseline(root: Path, *, test_root: Path | None = None) -> dict[str, Any]:
    maximum = 500
    lines = _production_lines(root)
    return {
        "schema": SCHEMA,
        "maximum_lines": maximum,
        "target_lines": 400,
        "production_roots": list(PRODUCTION_ROOTS),
        "oversized_production_files": {
            path: count for path, count in lines.items() if count > maximum
        },
        "complexity_violations": _complexities(root),
        "test_file_lines": _test_lines(test_root or root),
    }


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError("structure baseline schema is invalid")
    maximum = value.get("maximum_lines")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
        raise ValueError("structure baseline maximum_lines is invalid")
    return value


def _int_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str)
        and key
        and isinstance(item, int)
        and not isinstance(item, bool)
        and item > 0
        for key, item in value.items()
    ):
        raise ValueError("structure baseline line mapping is invalid")
    return dict(value)


def _nested_int_map(value: Any) -> dict[str, dict[str, int]]:
    if not isinstance(value, dict):
        raise ValueError("structure baseline complexity mapping is invalid")
    return {str(path): _int_map(functions) for path, functions in value.items()}


def _physical_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--test-root", type=Path)
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)
    root = args.source_root.resolve()
    try:
        if args.write_baseline:
            test_root = args.test_root.resolve() if args.test_root else root
            _atomic_write(args.baseline, _baseline(root, test_root=test_root))
            return 0
        errors = _errors(root, _load(args.baseline))
    except (OSError, UnicodeError, ValueError) as error:
        print(f"structure check failed: {error}", file=sys.stderr)
        return 2
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
