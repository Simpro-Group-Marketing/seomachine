"""Run the approved AnswerSocrates recorder with a persistent CLI subprocess."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.paa_provenance.cli import _record_main  # noqa: E402
from data_sources.modules.artifact_runtime.subprocesses import (  # noqa: E402
    BoundedTextProcess,
    run_bounded_text_process,
)
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
) -> BoundedTextProcess:
    """Run the approved CLI without terminating its browser service between calls."""
    kwargs = {
        "cwd": ROOT,
        "encoding": encoding,
        "errors": errors,
        "timeout": float(timeout) if timeout is not None else 60.0,
    }
    if max_output_bytes is not None:
        kwargs["max_output_bytes"] = max_output_bytes
    return run_bounded_text_process(
        list(args),
        **kwargs,
    )


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
