from __future__ import annotations

from pathlib import Path

import pytest

from tools.check_python_structure import (
    _production_files,
    complexity_errors,
    production_line_errors,
)


def test_production_line_baseline_rejects_growth_and_stale_debt() -> None:
    baseline = {"legacy.py": 700}

    assert production_line_errors({"legacy.py": 700}, baseline, maximum=500) == []
    assert production_line_errors({"legacy.py": 701}, baseline, maximum=500) == [
        "legacy.py grew from 700 to 701 physical lines"
    ]
    assert production_line_errors({"legacy.py": 699}, baseline, maximum=500) == [
        "legacy.py improved to 699 lines; lower its stale 700-line baseline"
    ]
    assert production_line_errors({"new.py": 501}, baseline, maximum=500) == [
        "legacy.py is absent; remove its stale line baseline",
        "new.py has 501 lines; new production files are limited to 500",
    ]


def test_complexity_baseline_rejects_new_growth_and_stale_debt() -> None:
    baseline = {"legacy.py": {"old": 14}}

    assert complexity_errors({"legacy.py": {"old": 14}}, baseline) == []
    assert complexity_errors({"legacy.py": {"old": 15}}, baseline) == [
        "legacy.py:old complexity grew from 14 to 15"
    ]
    assert complexity_errors({"legacy.py": {"old": 13}}, baseline) == [
        "legacy.py:old improved to complexity 13; lower its stale 14 baseline"
    ]
    assert complexity_errors({"new.py": {"new": 11}}, baseline) == [
        "legacy.py:old no longer violates C901; remove its stale baseline",
        "new.py:new is a new C901 violation at complexity 11",
    ]


def test_mcp_gsc_is_a_required_production_root(tmp_path: Path) -> None:
    for directory in ("data_sources", "scripts", "tools"):
        (tmp_path / directory).mkdir()

    with pytest.raises(ValueError, match="production root is missing: mcp-gsc"):
        _production_files(tmp_path)


def test_mcp_gsc_scan_requires_facade_and_package_and_excludes_build_artifacts(
    tmp_path: Path,
) -> None:
    for directory in ("data_sources", "scripts", "tools"):
        (tmp_path / directory).mkdir()
    package_root = tmp_path / "mcp-gsc"
    package = package_root / "mcp_gsc"
    package.mkdir(parents=True)
    (package_root / "gsc_server.py").write_text("FACADE = True\n", encoding="utf-8")
    (package / "__init__.py").write_text("PACKAGE = True\n", encoding="utf-8")
    (package_root / "extra.py").write_text("EXTRA = True\n", encoding="utf-8")
    for excluded in ("venv", ".venv", "build", "dist", "pkg.egg-info", "__pycache__"):
        path = package_root / excluded
        path.mkdir()
        (path / "ignored.py").write_text("IGNORED = True\n", encoding="utf-8")

    files = {
        path.relative_to(tmp_path).as_posix() for path in _production_files(tmp_path)
    }

    assert files == {
        "mcp-gsc/extra.py",
        "mcp-gsc/gsc_server.py",
        "mcp-gsc/mcp_gsc/__init__.py",
    }

    (package_root / "gsc_server.py").unlink()
    with pytest.raises(ValueError, match="required production path is missing"):
        _production_files(tmp_path)
