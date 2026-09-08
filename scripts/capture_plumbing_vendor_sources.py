#!/usr/bin/env python3
"""Capture current official vendor pages used by the plumbing recovery article."""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO / "research" / "best-plumbing-job-management-software-remediation-2026-09-03"
RAW_DIR = OUTPUT_DIR / "raw" / "vendor-sources"
NPM_CACHE = Path.home() / "AppData" / "Local" / "npm-cache" / "_npx"
SESSION = "plumbing-serp-recovery"

SOURCES = [
    {"vendor": "BuildOps", "decision": "retain", "source_type": "plumbing_product", "url": "https://buildops.com/industries/plumbing"},
    {"vendor": "BuildOps", "decision": "retain", "source_type": "pricing", "url": "https://buildops.com/pricing"},
    {"vendor": "FieldPulse", "decision": "retain", "source_type": "plumbing_product", "url": "https://www.fieldpulse.com/solutions/plumbing"},
    {"vendor": "FieldPulse", "decision": "retain", "source_type": "pricing", "url": "https://fp-pricing.fieldpulse.com/"},
    {"vendor": "Housecall Pro", "decision": "retain", "source_type": "plumbing_product", "url": "https://www.housecallpro.com/industries/plumbing-software/"},
    {"vendor": "Housecall Pro", "decision": "retain", "source_type": "pricing", "url": "https://www.housecallpro.com/pricing/"},
    {"vendor": "Jobber", "decision": "retain", "source_type": "plumbing_product", "url": "https://www.getjobber.com/industries/plumbing-software/"},
    {"vendor": "Jobber", "decision": "retain", "source_type": "pricing", "url": "https://www.getjobber.com/pricing/"},
    {"vendor": "Service Fusion", "decision": "retain", "source_type": "plumbing_product", "url": "https://www.servicefusion.com/plumbing-software"},
    {"vendor": "Service Fusion", "decision": "retain", "source_type": "pricing_and_product", "url": "https://www.servicefusion.com/field-service-management-software"},
    {"vendor": "ServiceTitan", "decision": "add", "source_type": "plumbing_product", "url": "https://www.servicetitan.com/industries/plumbing-software"},
    {"vendor": "Simpro", "decision": "retain", "source_type": "plumbing_product", "url": "https://www.simprogroup.com/industries/plumbing-software"},
    {"vendor": "Simpro", "decision": "retain", "source_type": "pricing", "url": "https://www.simprogroup.com/pricing"},
    {"vendor": "Workiz", "decision": "retain", "source_type": "plumbing_product", "url": "https://www.workiz.com/industries/plumbing-software/"},
    {"vendor": "Workiz", "decision": "retain", "source_type": "pricing", "url": "https://www.workiz.com/pricing-plans/"},
    {"vendor": "FieldEdge", "decision": "drop", "source_type": "plumbing_product", "url": "https://fieldedge.com/plumbing-software/"},
    {"vendor": "FieldEdge", "decision": "drop", "source_type": "pricing", "url": "https://fieldedge.com/pricing-v1/"},
]

TERM_PATTERNS = {
    "scheduling": ["scheduling", "schedule jobs"],
    "dispatch": ["dispatch", "dispatching"],
    "estimating": ["estimate", "estimating", "quotes"],
    "invoicing": ["invoice", "invoicing"],
    "payments": ["payments", "payment processing", "get paid"],
    "maintenance": ["maintenance", "service agreements", "service plans"],
    "projects": ["project management", "project workflow", "multi-day jobs"],
    "inventory": ["inventory", "stock management"],
    "purchasing": ["purchase orders", "purchasing"],
    "job_costing": ["job costing", "job costs", "cost tracking"],
    "mobile": ["mobile app", "mobile workforce", "field app"],
    "pricing": ["pricing", "price", "request a quote", "get a quote", "free trial"],
}


def cli_path() -> Path:
    candidates = sorted(NPM_CACHE.glob("*/node_modules/@playwright/cli/playwright-cli.js"))
    if not candidates:
        raise FileNotFoundError("@playwright/cli was not found in the npm cache")
    return candidates[0]


def run_cli(*args: str, timeout: int = 420) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["node", str(cli_path()), f"-s={SESSION}", *args],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Playwright CLI failed:\n{result.stderr}\n{result.stdout}")
    return result


def capture() -> list[dict[str, Any]]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sources_json = json.dumps(SOURCES)
    javascript = f"""async function run(page) {{
      const sources = {sources_json};
      const captures = [];
      await page.setViewportSize({{width: 1440, height: 1000}});
      for (const source of sources) {{
        let response = null;
        let error = '';
        try {{
          response = await page.goto(source.url, {{waitUntil: 'domcontentloaded', timeout: 60000}});
          await page.waitForTimeout(1000);
        }} catch (caught) {{
          error = String(caught);
        }}
        const pageData = await page.evaluate(() => {{
          const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
          const bodyText = clean(document.body ? document.body.innerText : '');
          return {{
            final_url: location.href,
            title: document.title,
            canonical: document.querySelector('link[rel="canonical"]')?.href || '',
            meta_description: document.querySelector('meta[name="description"]')?.getAttribute('content') || '',
            meta_robots: document.querySelector('meta[name="robots"]')?.getAttribute('content') || '',
            h1s: Array.from(document.querySelectorAll('h1')).map(element => clean(element.innerText)),
            body_word_count: bodyText ? bodyText.split(/\\s+/).length : 0,
            visible_text: bodyText.slice(0, 80000)
          }};
        }}).catch(caught => ({{
          final_url: page.url(), title: '', canonical: '', meta_description: '',
          meta_robots: '', h1s: [], body_word_count: 0, visible_text: '',
          evaluation_error: String(caught)
        }}));
        captures.push({{
          ...source,
          ...pageData,
          http_status: response ? response.status() : null,
          captured_at: new Date().toISOString(),
          capture_error: error
        }});
      }}
      return captures;
    }}"""
    result = run_cli("run-code", javascript)
    marker = "### Result"
    if marker not in result.stdout:
        raise RuntimeError(f"Unexpected Playwright output:\n{result.stdout}")
    payload = result.stdout.split(marker, 1)[1].strip()
    if "### Ran Playwright code" in payload:
        payload = payload.split("### Ran Playwright code", 1)[0].strip()
    return json.loads(payload)


def summarize(captures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for capture in captures:
        body = capture.get("visible_text", "").lower()
        matched_terms = [
            label
            for label, patterns in TERM_PATTERNS.items()
            if any(pattern in body for pattern in patterns)
        ]
        status = capture.get("http_status")
        rows.append(
            {
                "vendor": capture["vendor"],
                "shortlist_decision": capture["decision"],
                "source_type": capture["source_type"],
                "requested_url": capture["url"],
                "final_url": capture.get("final_url", ""),
                "http_status": status,
                "page_title": capture.get("title", ""),
                "canonical": capture.get("canonical", ""),
                "h1": " | ".join(capture.get("h1s", [])),
                "visible_word_count": capture.get("body_word_count", 0),
                "detected_terms_not_feature_validation": ";".join(matched_terms),
                "captured_at": capture.get("captured_at", ""),
                "source_status": "captured" if status and 200 <= status < 400 and body else "capture_incomplete",
                "capture_error": capture.get("capture_error", "") or capture.get("evaluation_error", ""),
            }
        )
    return rows


def main() -> int:
    captures = capture()
    RAW_DIR.joinpath("official-vendor-page-captures.json").write_text(
        json.dumps(
            {
                "schema": "simpro-plumbing-official-vendor-page-evidence/v1",
                "captured_at": datetime.now().astimezone().isoformat(),
                "note": "Term detection is a navigation aid only. Feature claims require review of the captured official page text.",
                "captures": captures,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    rows = summarize(captures)
    output_path = OUTPUT_DIR / "vendor-source-evidence.csv"
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    complete = sum(row["source_status"] == "captured" for row in rows)
    print(json.dumps({"sources": len(rows), "captured": complete, "output": str(output_path)}))
    return 0 if complete == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
