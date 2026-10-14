"""Tests for the keep-list reachability walk used to retire unreachable modules."""

from __future__ import annotations

from pathlib import Path

from tools.reachable_modules import doc_references, reachable, unreachable


def _write(root: Path, rel: str, text: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _package(root: Path) -> Path:
    mods = root / "data_sources" / "modules"
    _write(root, "data_sources/__init__.py")
    _write(root, "data_sources/modules/__init__.py")
    _write(root, "data_sources/modules/entry.py", "from data_sources.modules.absolute import x\nfrom . import relative\n")
    _write(root, "data_sources/modules/absolute.py", "x = 1\n")
    _write(root, "data_sources/modules/relative.py", "try:\n    from .fallback import y\nexcept ImportError:\n    from bare import y\n")
    _write(root, "data_sources/modules/fallback.py", "y = 2\n")
    _write(root, "data_sources/modules/bare.py", "y = 3\n")
    _write(root, "data_sources/modules/pkg/__init__.py", "")
    _write(root, "data_sources/modules/pkg/inner.py", "from ..absolute import x\n")
    _write(root, "data_sources/modules/dynamic.py", "NAME = 'data_sources.modules.stringly'\n")
    _write(root, "data_sources/modules/stringly.py", "")
    _write(root, "data_sources/modules/orphan.py", "import os\n")
    _write(root, "data_sources/modules/orphan_pkg/__init__.py", "")
    _write(root, "data_sources/modules/orphan_pkg/leaf.py", "from data_sources.modules import absolute\n")
    return mods


def test_closure_follows_absolute_relative_fallback_and_bare_imports(tmp_path):
    _package(tmp_path)
    found = reachable(tmp_path, ["data_sources/modules/entry.py"])
    names = {path.relative_to(tmp_path).as_posix() for path in found}
    assert {
        "data_sources/modules/entry.py",
        "data_sources/modules/absolute.py",
        "data_sources/modules/relative.py",
        "data_sources/modules/fallback.py",
        "data_sources/modules/bare.py",
        "data_sources/modules/__init__.py",
    } <= names
    assert "data_sources/modules/orphan.py" not in names


def test_package_entry_and_parent_init_and_string_reference(tmp_path):
    _package(tmp_path)
    found = reachable(tmp_path, ["data_sources/modules/pkg/inner.py", "data_sources/modules/dynamic.py"])
    names = {path.relative_to(tmp_path).as_posix() for path in found}
    assert "data_sources/modules/pkg/__init__.py" in names
    assert "data_sources/modules/absolute.py" in names
    assert "data_sources/modules/stringly.py" in names


def test_unreachable_lists_only_unreferenced_module_files(tmp_path):
    _package(tmp_path)
    left = unreachable(tmp_path, ["data_sources/modules/entry.py"])
    names = {path.relative_to(tmp_path).as_posix() for path in left}
    assert "data_sources/modules/orphan.py" in names
    assert "data_sources/modules/orphan_pkg/leaf.py" in names
    assert "data_sources/modules/entry.py" not in names


def test_doc_references_find_paths_and_dotted_names(tmp_path):
    _package(tmp_path)
    _write(tmp_path, ".claude/commands/x.md", "run `python data_sources/modules/orphan.py` and `python -m data_sources.modules.pkg.inner`\n")
    _write(tmp_path, ".github/workflows/ci.yml", "paths:\n  - data_sources/modules/orphan_pkg\n")
    refs = {path.relative_to(tmp_path).as_posix() for path in doc_references(tmp_path)}
    assert "data_sources/modules/orphan.py" in refs
    assert "data_sources/modules/pkg/inner.py" in refs
    assert "data_sources/modules/orphan_pkg/leaf.py" in refs


def test_scripts_importing_modules_via_data_sources_on_sys_path(tmp_path):
    _package(tmp_path)
    _write(tmp_path, "scripts/run.py", "import sys\nsys.path.insert(0, 'data_sources')\nfrom modules.orphan import x\nimport modules.orphan_pkg.leaf\n")
    names = {path.relative_to(tmp_path).as_posix() for path in reachable(tmp_path, ["scripts/run.py"])}
    assert "data_sources/modules/orphan.py" in names
    assert "data_sources/modules/orphan_pkg/leaf.py" in names
