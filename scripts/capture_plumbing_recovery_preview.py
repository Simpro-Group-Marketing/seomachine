"""Capture browser evidence for the local plumbing remediation preview."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = (
    "http://127.0.0.1:8876/research/"
    "best-plumbing-job-management-software-remediation-2026-09-03/"
    "replacement-preview.html"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "research"
    / "best-plumbing-job-management-software-remediation-2026-09-03"
    / "raw"
    / "replacement-render"
)
PLAYWRIGHT_CLI_VERSION = "0.1.19"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}
LAYOUT_EXPRESSION = " ".join(r"""() => {
  const table = document.querySelector('table');
  const wrapper = document.querySelector('.table-responsive');
  const tableRect = table ? table.getBoundingClientRect() : null;
  const wrapperRect = wrapper ? wrapper.getBoundingClientRect() : null;
  const root = document.documentElement;
  const text = document.body.innerText.toLowerCase();
  const leakPhrases = [
    'original eight tools',
    'same order as the current article',
    'fixes the incorrect electrical',
    'keeps the existing url slug',
    'before cms publish',
    'cms publish'
  ];
  const brokenImages = Array.from(document.images)
    .filter(image => !image.complete || image.naturalWidth === 0)
    .map(image => ({src: image.currentSrc || image.src, alt: image.alt}));
  return {
    url: location.href,
    title: document.title,
    viewport: {width: innerWidth, height: innerHeight},
    documentClientWidth: root.clientWidth,
    documentScrollWidth: root.scrollWidth,
    pageHasHorizontalOverflow: root.scrollWidth > root.clientWidth + 1,
    scrollPosition: {x: Math.round(scrollX), y: Math.round(scrollY)},
    h1Count: document.querySelectorAll('h1').length,
    h1Text: document.querySelector('h1')?.textContent.trim() || null,
    tableCount: document.querySelectorAll('table').length,
    tableVisible: Boolean(tableRect && tableRect.width > 0 && tableRect.height > 0),
    tableWidth: tableRect ? Math.round(tableRect.width) : null,
    tableHeight: tableRect ? Math.round(tableRect.height) : null,
    wrapperWidth: wrapperRect ? Math.round(wrapperRect.width) : null,
    wrapperClientWidth: wrapper ? wrapper.clientWidth : null,
    wrapperScrollWidth: wrapper ? wrapper.scrollWidth : null,
    wrapperOverflowX: wrapper ? getComputedStyle(wrapper).overflowX : null,
    comparisonTableScrollable: Boolean(wrapper && wrapper.scrollWidth > wrapper.clientWidth + 1),
    imageCount: document.images.length,
    brokenImages,
    schemaScriptCount: document.querySelectorAll('script[type="application/ld+json"]').length,
    leakMatches: leakPhrases.filter(phrase => text.includes(phrase))
  };
}""".split())


def _run_cli(
    npx: str,
    session: str,
    *arguments: str,
    raw: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = [
        npx,
        "--yes",
        f"@playwright/cli@{PLAYWRIGHT_CLI_VERSION}",
    ]
    if raw:
        command.append("--raw")
    command.extend([f"-s={session}", *arguments])
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=check,
    )


def _http_status(url: str) -> int:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read(1)
        return int(response.status)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "check": name,
        "passed": passed,
        "actual": actual,
        "expected": expected,
    }


def _viewport_checks(label: str, metrics: dict[str, Any]) -> list[dict[str, Any]]:
    expected = VIEWPORTS[label]
    checks = [
        _check("viewport", metrics["viewport"] == expected, metrics["viewport"], expected),
        _check("single_h1", metrics["h1Count"] == 1, metrics["h1Count"], 1),
        _check("comparison_table_present", metrics["tableCount"] >= 1, metrics["tableCount"], ">=1"),
        _check("comparison_table_visible", metrics["tableVisible"], metrics["tableVisible"], True),
        _check(
            "page_horizontal_overflow_absent",
            not metrics["pageHasHorizontalOverflow"],
            metrics["pageHasHorizontalOverflow"],
            False,
        ),
        _check(
            "viewport_capture_at_document_top",
            metrics["scrollPosition"] == {"x": 0, "y": 0},
            metrics["scrollPosition"],
            {"x": 0, "y": 0},
        ),
        _check("images_loaded", not metrics["brokenImages"], metrics["brokenImages"], []),
        _check("operational_leakage", not metrics["leakMatches"], metrics["leakMatches"], []),
        _check(
            "json_ld_present",
            metrics["schemaScriptCount"] >= 1,
            metrics["schemaScriptCount"],
            ">=1",
        ),
    ]
    if label == "mobile":
        checks.extend(
            [
                _check(
                    "comparison_table_scrollable",
                    metrics["comparisonTableScrollable"],
                    {
                        "clientWidth": metrics["wrapperClientWidth"],
                        "scrollWidth": metrics["wrapperScrollWidth"],
                    },
                    "scrollWidth > clientWidth",
                ),
                _check(
                    "comparison_wrapper_overflow",
                    metrics["wrapperOverflowX"] in {"auto", "scroll"},
                    metrics["wrapperOverflowX"],
                    "auto or scroll",
                ),
            ]
        )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--session", default="plumbing-remediation-capture")
    args = parser.parse_args()

    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        raise RuntimeError("npx is required for Playwright CLI capture.")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    http_status = _http_status(args.url)
    captures: dict[str, Any] = {}
    all_checks = [_check("preview_http_status", http_status == 200, http_status, 200)]

    _run_cli(npx, args.session, "close", check=False)
    try:
        _run_cli(npx, args.session, "open", args.url)
        for label, viewport in VIEWPORTS.items():
            _run_cli(
                npx,
                args.session,
                "resize",
                str(viewport["width"]),
                str(viewport["height"]),
            )
            _run_cli(npx, args.session, "reload")
            _run_cli(
                npx,
                args.session,
                "eval",
                (
                    "async () => { await Promise.all(Array.from(document.images).map("
                    "image => image.complete ? Promise.resolve() : new Promise(resolve => { "
                    "image.addEventListener('load', resolve, {once:true}); "
                    "image.addEventListener('error', resolve, {once:true}); }))); return true; }"
                ),
                raw=True,
            )
            _run_cli(
                npx,
                args.session,
                "eval",
                "() => { window.scrollTo(0, 0); return {x: scrollX, y: scrollY}; }",
                raw=True,
            )
            snapshot = _run_cli(npx, args.session, "snapshot").stdout
            (output_dir / f"{label}-snapshot.txt").write_text(
                snapshot,
                encoding="utf-8",
                newline="\n",
            )
            metrics_output = _run_cli(
                npx,
                args.session,
                "eval",
                LAYOUT_EXPRESSION,
                raw=True,
            ).stdout
            metrics = json.loads(metrics_output)
            checks = _viewport_checks(label, metrics)
            all_checks.extend(
                {
                    **check,
                    "viewport": label,
                }
                for check in checks
            )

            viewport_screenshot = output_dir / f"{label}-preview.png"
            table_screenshot = output_dir / f"{label}-comparison-table.png"
            _run_cli(
                npx,
                args.session,
                "screenshot",
                f"--filename={viewport_screenshot}",
            )
            _run_cli(
                npx,
                args.session,
                "screenshot",
                ".table-responsive",
                f"--filename={table_screenshot}",
            )
            console = _run_cli(
                npx,
                args.session,
                "console",
                "error",
                raw=True,
                check=False,
            ).stdout.strip()
            console_clean = "Total messages: 0" in console or not console
            console_check = _check(
                "console_errors_absent",
                console_clean,
                console,
                "0 errors",
            )
            console_check["viewport"] = label
            all_checks.append(console_check)
            captures[label] = {
                "metrics": metrics,
                "snapshot": str((output_dir / f"{label}-snapshot.txt").relative_to(REPO_ROOT)),
                "viewport_screenshot": str(viewport_screenshot.relative_to(REPO_ROOT)),
                "table_screenshot": str(table_screenshot.relative_to(REPO_ROOT)),
                "console": console,
            }
    finally:
        _run_cli(npx, args.session, "close", check=False)

    result = {
        "schema": "plumbing-remediation-browser-render-evidence/v1",
        "playwright_cli_version": PLAYWRIGHT_CLI_VERSION,
        "url": args.url,
        "http_status": http_status,
        "viewports": VIEWPORTS,
        "captures": captures,
        "checks": all_checks,
        "summary": {
            "passed": sum(1 for check in all_checks if check["passed"]),
            "failed": sum(1 for check in all_checks if not check["passed"]),
            "all_passed": all(check["passed"] for check in all_checks),
        },
    }
    output_path = output_dir / "browser-validation.json"
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result["summary"], indent=2))
    print(f"evidence={output_path}")
    return 0 if result["summary"]["all_passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        raise
