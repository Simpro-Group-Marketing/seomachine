"""Every guard invocation the repo documents must actually be runnable.

Guards under ``data_sources/modules`` are packages that import across their
parent package. Run as a bare script path the package context is absent, so the
interpreter dies on import before the guard ever sees its arguments. Any command
documented in that form never runs -- it exits non-zero for a reason unrelated
to the article being checked, which reads like a passing gate that simply
produced no findings.

This test extracts the invocations the docs actually prescribe and asserts each
one loads.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

DOC_DIRS = (
    ROOT / ".claude",
    ROOT / ".cursor",
    ROOT / ".agents",
    ROOT / "context",
)

SCRIPT_FORM_RE = re.compile(r"python\s+(data_sources/modules/[a-z0-9_/]+)\.py")
MODULE_FORM_RE = re.compile(r"python\s+-m\s+(data_sources\.modules\.[a-z0-9_.]+)")

IMPORT_FAILURE_MARKERS = (
    "ImportError",
    "ModuleNotFoundError",
    "attempted relative import",
)


def _documented_invocations():
    """Yield (doc-relative-path, line number, argv-prefix) for each documented command."""
    seen = set()
    for doc_dir in DOC_DIRS:
        for path in sorted(doc_dir.rglob("*")):
            if not path.is_file() or path.suffix not in {".md", ".mdc"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), start=1):
                for match in SCRIPT_FORM_RE.finditer(line):
                    argv = (f"{match.group(1)}.py",)
                    key = (argv, path)
                    if key not in seen:
                        seen.add(key)
                        yield path, lineno, argv
                for match in MODULE_FORM_RE.finditer(line):
                    argv = ("-m", match.group(1))
                    key = (argv, path)
                    if key not in seen:
                        seen.add(key)
                        yield path, lineno, argv


INVOCATIONS = list(_documented_invocations())


def _case_id(case):
    path, lineno, argv = case
    return f"{path.relative_to(ROOT).as_posix()}:{lineno}:{' '.join(argv)}"


def test_docs_actually_document_guard_invocations():
    """Guard the parser itself: an empty sweep would make every case below vacuous."""
    assert len(INVOCATIONS) > 10


@pytest.mark.parametrize("case", INVOCATIONS, ids=_case_id)
def test_documented_invocation_loads(case):
    _path, _lineno, argv = case

    result = subprocess.run(
        [sys.executable, *argv, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    combined = f"{result.stdout}\n{result.stderr}"
    failures = [marker for marker in IMPORT_FAILURE_MARKERS if marker in combined]
    assert not failures, (
        f"documented command `python {' '.join(argv)}` cannot load "
        f"({', '.join(failures)}):\n{result.stderr.strip()}"
    )
