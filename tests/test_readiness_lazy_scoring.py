from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORING_MODULES = (
    "data_sources.modules.content_scorer",
    "data_sources.modules.readability_scorer",
    "textstat",
)


def _imported_scoring_modules(statement: str) -> list[str]:
    script = (
        "import json, sys; "
        f"{statement}; "
        f"print(json.dumps([name for name in {SCORING_MODULES!r} if name in sys.modules]))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_importing_readiness_does_not_load_scoring_stack() -> None:
    imported = _imported_scoring_modules(
        "import data_sources.modules.readiness.api"
    )

    assert imported == []


def test_landing_scorer_factory_loads_no_scoring_stack() -> None:
    imported = _imported_scoring_modules(
        "from data_sources.modules.readiness import common as readiness; "
        "readiness.LandingPageScorer"
    )

    assert imported == []


def test_early_input_blocker_does_not_load_scoring_stack() -> None:
    imported = _imported_scoring_modules(
        "import tempfile; from pathlib import Path; "
        "from data_sources.modules.readiness.api import run_publish_readiness; "
        "root=Path(tempfile.mkdtemp()); "
        "result=run_publish_readiness(root/'missing.md', workspace_root=root); "
        "assert not result['passed']"
    )

    assert imported == []
