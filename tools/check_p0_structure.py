"""Enforce the P0 physical-line and cyclomatic-complexity baseline."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "config" / "p0-structure-baseline.json"


def main() -> int:
    try:
        baseline = _load_baseline(BASELINE_PATH)
        errors = [*_line_errors(baseline), *_complexity_errors(baseline)]
    except (OSError, UnicodeError, ValueError) as error:
        print(f"structure check failed: {error}", file=sys.stderr)
        return 2
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


def _load_baseline(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("structure baseline must be a JSON object")
    if value.get("schema") != "simpro-python-structure-baseline/v1":
        raise ValueError("structure baseline schema is invalid")
    maximum = value.get("maximum_lines")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
        raise ValueError("structure baseline maximum_lines is invalid")
    return value


def _line_errors(baseline: Mapping[str, Any]) -> list[str]:
    maximum = int(baseline["maximum_lines"])
    errors: list[str] = []
    for path in _strict_paths(baseline, "strict_files", "strict_directories"):
        count = _physical_lines(path)
        if count > maximum:
            errors.append(f"{_relative(path)} has {count} lines; limit is {maximum}")
    grandfathered = _string_int_mapping(baseline.get("grandfathered_files"))
    for relative, allowed in grandfathered.items():
        path = ROOT / relative
        count = _physical_lines(path)
        if count > allowed:
            errors.append(f"{relative} grew from baseline {allowed} to {count} lines")
    return errors


def _complexity_errors(baseline: Mapping[str, Any]) -> list[str]:
    paths = _strict_paths(
        baseline,
        "complexity_strict_files",
        "complexity_strict_directories",
    )
    ruff = shutil.which("ruff")
    if ruff is None:
        raise ValueError("ruff is required for the P0 complexity check")
    completed = subprocess.run(
        [ruff, "check", *map(str, paths), "--select", "C901", "--output-format", "concise"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise ValueError(completed.stderr.strip() or "ruff complexity check failed")
    if completed.returncode == 0:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _strict_paths(
    baseline: Mapping[str, Any],
    files_key: str,
    directories_key: str,
) -> list[Path]:
    paths = [ROOT / value for value in _string_list(baseline.get(files_key))]
    for directory in _string_list(baseline.get(directories_key)):
        paths.extend(sorted((ROOT / directory).glob("*.py")))
    unique = {path.resolve(): path for path in paths}
    missing = [path for path in unique if not path.is_file()]
    if missing:
        raise ValueError(f"structure baseline path is missing: {_relative(missing[0])}")
    return sorted(unique)


def _physical_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError("structure baseline file lists must contain non-empty strings")
    return value


def _string_int_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("structure baseline grandfathered_files must be an object")
    if not all(
        isinstance(key, str)
        and key
        and isinstance(item, int)
        and not isinstance(item, bool)
        and item > 500
        for key, item in value.items()
    ):
        raise ValueError("structure baseline grandfathered file entries are invalid")
    return dict(value)


if __name__ == "__main__":
    raise SystemExit(main())
