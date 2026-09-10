"""Enforce declining Python size and cyclomatic-complexity baselines."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "config" / "python-structure-baseline.json"
SCHEMA = "simpro-python-structure-baseline/v2"
PRODUCTION_ROOTS = ("data_sources", "scripts", "tools")
C901_PATTERN = re.compile(r"`([^`]+)` is too complex \((\d+) > 10\)")


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


def _production_lines(root: Path) -> dict[str, int]:
    rows: dict[str, int] = {}
    for directory in PRODUCTION_ROOTS:
        base = root / directory
        if not base.is_dir():
            raise ValueError(f"production root is missing: {directory}")
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rows[path.relative_to(root).as_posix()] = _physical_lines(path)
    return rows


def _test_lines(root: Path) -> dict[str, int]:
    return {
        path.relative_to(root).as_posix(): _physical_lines(path)
        for path in sorted((root / "tests").rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def _complexities(root: Path) -> dict[str, dict[str, int]]:
    ruff = shutil.which("ruff")
    if ruff is None:
        raise ValueError("ruff is required for the structure check")
    completed = subprocess.run(
        [
            ruff,
            "check",
            *PRODUCTION_ROOTS,
            "--select",
            "C901",
            "--output-format",
            "json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
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
