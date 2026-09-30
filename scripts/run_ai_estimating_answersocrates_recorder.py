"""Run the approved AnswerSocrates recorder with a persistent CLI subprocess."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.paa_provenance.cli import _record_main  # noqa: E402
from data_sources.modules.paa_provenance.collection import (  # noqa: E402
    find_npx_executable,
)
from data_sources.modules.paa_provenance.dependencies import PaaDependencies  # noqa: E402


QUERY = "AI software for generating estimates and quotes for trade businesses"
RUN_ID = "ai-estimating-software-trade-businesses-2026-09-28-semrush-primary"
RAW = ROOT / "research" / (
    "answersocrates-raw-ai-estimating-software-trade-businesses-2026-09-28.json"
)
OUTPUT = ROOT / "research" / (
    "paa-questions-ai-estimating-software-trade-businesses-2026-09-28.json"
)


def persistent_subprocess_runner(
    args: Sequence[str],
    *,
    encoding: str = "utf-8",
    errors: str = "replace",
    timeout: int | float | None = None,
    max_output_bytes: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the approved CLI without terminating its browser service between calls."""
    completed = subprocess.run(
        list(args),
        capture_output=True,
        encoding=encoding,
        errors=errors,
        timeout=timeout,
        check=False,
    )
    if max_output_bytes is not None:
        stdout_bytes = completed.stdout.encode(encoding, errors=errors)
        stderr_bytes = completed.stderr.encode(encoding, errors=errors)
        if len(stdout_bytes) > max_output_bytes or len(stderr_bytes) > max_output_bytes:
            raise subprocess.SubprocessError(
                "AnswerSocrates collector output exceeded the repository bound"
            )
    return completed


def main() -> int:
    dependencies = PaaDependencies(
        executable_resolver=find_npx_executable,
        subprocess_runner=persistent_subprocess_runner,
    )
    return _record_main(
        [
            "--query",
            QUERY,
            "--collection-date",
            "2026-09-28",
            "--run-id",
            RUN_ID,
            "--raw-capture-output",
            str(RAW),
            "--workspace-root",
            str(ROOT),
            "--output",
            str(OUTPUT),
        ],
        dependencies=dependencies,
    )


if __name__ == "__main__":
    raise SystemExit(main())
