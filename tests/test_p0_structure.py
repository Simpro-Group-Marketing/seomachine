from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_p0_files_respect_loc_and_complexity_baseline():
    completed = subprocess.run(
        [sys.executable, "tools/check_p0_structure.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
