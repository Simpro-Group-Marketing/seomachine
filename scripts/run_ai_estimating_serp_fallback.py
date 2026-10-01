"""Run the repository SERP collector with a readiness check for Playwright CLI."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import research_serp_analysis as serp  # noqa: E402
from data_sources.modules.artifact_runtime.subprocesses import run_bounded_text_process  # noqa: E402


KEYWORD = "ai estimating software"
RUN_ID = "ai-estimating-software-trade-businesses-2026-09-28-task1-playwright"


def run_playwright_cli_serp_capture_ready(
    keyword: str, google_country: str = "us"
) -> str:
    """Capture the SERP after confirming the CLI browser session is responsive."""
    search_url = serp.build_google_search_url(keyword, google_country)
    code = serp.build_playwright_serp_extraction_code(search_url)
    npx_path = serp.find_npx_executable()
    if not npx_path:
        raise RuntimeError(
            "npx unavailable; install Node/npm or provide a SERP/PAA export."
        )
    prefix = [
        npx_path,
        "--yes",
        "--package",
        "@playwright/cli",
        "playwright-cli",
    ]
    run_bounded_text_process(
        prefix + ["close"],
        timeout=serp.PLAYWRIGHT_CLOSE_TIMEOUT_SECONDS,
        errors="replace",
    )
    opened = run_bounded_text_process(
        prefix + ["open", "about:blank"],
        timeout=serp.PLAYWRIGHT_OPEN_TIMEOUT_SECONDS,
        errors="replace",
    )
    if opened.returncode != 0:
        raise RuntimeError((opened.stderr or opened.stdout).strip())

    ready = False
    readiness_error = ""
    for _ in range(5):
        listed = run_bounded_text_process(
            prefix + ["tab-list"],
            timeout=serp.PLAYWRIGHT_OPEN_TIMEOUT_SECONDS,
            errors="replace",
        )
        readiness_error = (listed.stderr or listed.stdout).strip()
        if listed.returncode == 0 and "about:blank" in listed.stdout:
            ready = True
            break
        time.sleep(1)
    if not ready:
        raise RuntimeError(
            "Playwright browser session did not become ready: " + readiness_error
        )

    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".js", delete=False
        ) as temp_file:
            temp_file.write(code)
            code_path = temp_file.name
        try:
            completed = run_bounded_text_process(
                prefix + ["run-code", "--filename", code_path, "--raw"],
                encoding="utf-8",
                errors="replace",
                timeout=serp.PLAYWRIGHT_RUN_TIMEOUT_SECONDS,
            )
            if completed.returncode != 0:
                raise RuntimeError((completed.stderr or completed.stdout).strip())
            return completed.stdout.strip()
        finally:
            try:
                os.unlink(code_path)
            except OSError:
                pass
    finally:
        run_bounded_text_process(
            prefix + ["close"],
            timeout=serp.PLAYWRIGHT_CLOSE_TIMEOUT_SECONDS,
            errors="replace",
        )


def main() -> int:
    serp.run_playwright_cli_serp_capture = run_playwright_cli_serp_capture_ready
    analysis = serp.run_serp_analysis(
        KEYWORD,
        output_dir=ROOT / "research",
        run_id=RUN_ID,
        location_code=2840,
        google_country="us",
    )
    if not analysis.get("top_results"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
