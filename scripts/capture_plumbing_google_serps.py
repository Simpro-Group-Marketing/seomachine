#!/usr/bin/env python3
"""Capture the three US Google SERPs required by the plumbing recovery plan."""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO / "research" / "best-plumbing-job-management-software-remediation-2026-09-03"
NPM_CACHE = Path.home() / "AppData" / "Local" / "npm-cache" / "_npx"
SESSION = "plumbing-serp-recovery"
QUERIES = [
    "plumbing job management software",
    "best plumbing job management software",
    "best plumbing software",
]


def cli_path() -> Path:
    candidates = sorted(NPM_CACHE.glob("*/node_modules/@playwright/cli/playwright-cli.js"))
    if not candidates:
        raise FileNotFoundError("@playwright/cli was not found in the npm cache")
    return candidates[0]


def run_cli(*args: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    command = ["node", str(cli_path()), f"-s={SESSION}", *args]
    return subprocess.run(
        command,
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def capture() -> dict[str, Any]:
    raw_dir = OUTPUT_DIR / "raw" / "google-serp"
    raw_dir.mkdir(parents=True, exist_ok=True)
    query_json = json.dumps(QUERIES)
    screenshot_dir_json = json.dumps(str(raw_dir).replace("\\", "/"))
    javascript = f"""async function run(page) {{
      const queries = {query_json};
      const screenshotDir = {screenshot_dir_json};
      const output = [];
      for (let index = 0; index < queries.length; index++) {{
        const query = queries[index];
        const url = 'https://www.google.com/search?q=' + encodeURIComponent(query) + '&gl=us&hl=en&pws=0';
        const response = await page.goto(url, {{waitUntil:'domcontentloaded', timeout:90000}});
        await page.waitForTimeout(2500);
        const data = await page.evaluate(() => {{
          const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
          const headings = Array.from(document.querySelectorAll('h2,h3')).map(h => clean(h.innerText)).filter(Boolean);
          const exactTextElement = text => Array.from(document.querySelectorAll('body *'))
            .find(element => clean(element.innerText).toLowerCase() === text.toLowerCase());
          const webHeading = exactTextElement('Web results');
          const aiHeading = exactTextElement('AI Overview');
          const follows = (node, reference) => !!reference && !!(reference.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING);
          const precedes = (node, reference) => !!reference && !!(reference.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_PRECEDING);
          const resultData = h => {{
            const anchor = h.closest('a');
            const sourceText = clean(anchor && anchor.parentElement ? anchor.parentElement.innerText : '');
            let block = h.closest('.MjjYud') || h.closest('[data-hveid]') || (anchor ? anchor.parentElement : h.parentElement);
            let blockText = clean(block ? block.innerText : sourceText);
            if (blockText.length < 80 && block && block.parentElement) blockText = clean(block.parentElement.innerText);
            const displayedUrl = (sourceText.match(/https?:\\/\\/[^ ]+/) || [''])[0];
            const sourceLines = (anchor && anchor.parentElement ? anchor.parentElement.innerText : '').split(/\\n+/).map(clean).filter(Boolean);
            const dateMatch = blockText.match(/(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]* \\d{{1,2}}, 20\\d{{2}}/i);
            return {{
              title: clean(h.innerText),
              displayed_source: sourceLines.length > 1 ? sourceLines[1] : '',
              displayed_url: displayedUrl,
              google_href: anchor ? anchor.href : '',
              visible_date: dateMatch ? dateMatch[0] : '',
              block_text: blockText.slice(0, 1200)
            }};
          }};
          const organic = Array.from(document.querySelectorAll('h3'))
            .filter(h => h.closest('a') && follows(h, webHeading))
            .filter(h => !h.closest('[aria-label="Ads"], [data-text-ad]'))
            .map(resultData)
            .filter((row, idx, rows) => row.title && rows.findIndex(other => other.title === row.title && other.displayed_source === row.displayed_source) === idx)
            .slice(0, 10);
          const aiSources = Array.from(document.querySelectorAll('h3'))
            .filter(h => h.closest('a') && follows(h, aiHeading) && precedes(h, webHeading))
            .map(resultData)
            .filter((row, idx, rows) => row.title && rows.findIndex(other => other.title === row.title && other.displayed_source === row.displayed_source) === idx)
            .slice(0, 20);
          let aiOverviewText = '';
          let aiLinkLabels = [];
          if (aiHeading) {{
            let container = aiHeading.parentElement;
            while (container && clean(container.innerText).length < 500) container = container.parentElement;
            if (container) {{
              aiOverviewText = clean(container.innerText).slice(0, 5000);
              aiLinkLabels = Array.from(container.querySelectorAll('a'))
                .map(anchor => clean(anchor.innerText || anchor.getAttribute('aria-label') || ''))
                .filter(text => text && text.length <= 300)
                .filter((text, idx, rows) => rows.indexOf(text) === idx)
                .slice(0, 30);
            }}
          }}
          const featureNames = [];
          for (const name of ['AI Overview', 'People also ask', 'Discussions and forums', 'Videos', 'Web results', 'People also search for']) {{
            if (headings.some(value => value.toLowerCase() === name.toLowerCase())) featureNames.push(name);
          }}
          if (aiHeading && !featureNames.includes('AI Overview')) featureNames.unshift('AI Overview');
          if (document.querySelector('[aria-label="Ads"], [data-text-ad]')) featureNames.push('Sponsored results');
          const relatedSearches = Array.from(document.querySelectorAll('a'))
            .map(a => clean(a.innerText))
            .filter(text => text && /plumb|field service|job schedul/i.test(text))
            .filter((text, idx, rows) => rows.indexOf(text) === idx)
            .slice(-20);
          return {{
            page_url: location.href,
            page_title: document.title,
            capture_location_text: clean((document.body.innerText.match(/\\b[A-Z][a-z]+, [A-Z]{{2}} \\d{{5}}\\b/) || [''])[0]),
            signed_in_indicator: !Array.from(document.querySelectorAll('a')).some(a => clean(a.innerText) === 'Sign in'),
            feature_names: featureNames,
            ai_overview_present: !!aiHeading,
            ai_overview_text: aiOverviewText,
            ai_overview_link_labels: aiLinkLabels,
            ai_sources: aiSources,
            organic_results: organic,
            related_searches: relatedSearches,
            body_text_sample: clean(document.body.innerText).slice(0, 8000)
          }};
        }});
        data.query = query;
        data.requested_url = url;
        data.http_status = response ? response.status() : null;
        data.capture_index = index + 1;
        const filename = screenshotDir + '/' + String(index + 1).padStart(2, '0') + '-' + query.replace(/[^a-z0-9]+/gi, '-').toLowerCase() + '.png';
        await page.screenshot({{path: filename, fullPage: true}});
        data.screenshot = filename;
        output.push(data);
      }}
      return output;
    }}"""
    result = run_cli("--json", "run-code", javascript, timeout=360)
    wrapper = json.loads(result.stdout)
    captures = json.loads(wrapper["result"])
    payload = {
        "schema": "simpro-browser-google-serp-evidence/v1",
        "captured_at": datetime.now().astimezone().isoformat(),
        "browser": "Google Chrome via persistent Playwright profile; signed-in state is reported per capture",
        "market_parameters": {"gl": "us", "hl": "en", "pws": "0"},
        "ranking_scope": "Rendered result order in this captured US SERP; not a universal rank claim.",
        "captures": captures,
    }
    write_json(raw_dir / "google-serp-captures.json", payload)
    return payload


def flatten(payload: dict[str, Any]) -> None:
    rows = []
    feature_rows = []
    for capture in payload["captures"]:
        for rank, result in enumerate(capture.get("organic_results") or [], start=1):
            rows.append(
                {
                    "query": capture["query"],
                    "result_type": "organic",
                    "rendered_rank": rank,
                    "title": result.get("title"),
                    "displayed_source": result.get("displayed_source"),
                    "displayed_url": result.get("displayed_url"),
                    "visible_date": result.get("visible_date"),
                    "result_text": result.get("block_text"),
                    "capture_http_status": capture.get("http_status"),
                    "capture_location": capture.get("capture_location_text"),
                    "screenshot": capture.get("screenshot"),
                    "source_status": "captured",
                }
            )
        for result in capture.get("ai_sources") or []:
            rows.append(
                {
                    "query": capture["query"],
                    "result_type": "ai_overview_source",
                    "rendered_rank": "",
                    "title": result.get("title"),
                    "displayed_source": result.get("displayed_source"),
                    "displayed_url": result.get("displayed_url"),
                    "visible_date": result.get("visible_date"),
                    "result_text": result.get("block_text"),
                    "capture_http_status": capture.get("http_status"),
                    "capture_location": capture.get("capture_location_text"),
                    "screenshot": capture.get("screenshot"),
                    "source_status": "captured",
                }
            )
        feature_rows.append(
            {
                "query": capture["query"],
                "http_status": capture.get("http_status"),
                "page_title": capture.get("page_title"),
                "capture_location": capture.get("capture_location_text"),
                "signed_in_indicator": capture.get("signed_in_indicator"),
                "features": ";".join(capture.get("feature_names") or []),
                "ai_overview_present": capture.get("ai_overview_present"),
                "ai_overview_text": capture.get("ai_overview_text"),
                "ai_overview_link_labels": ";".join(capture.get("ai_overview_link_labels") or []),
                "related_searches": ";".join(capture.get("related_searches") or []),
                "screenshot": capture.get("screenshot"),
                "source_status": "captured",
            }
        )
    fields = [
        "query",
        "result_type",
        "rendered_rank",
        "title",
        "displayed_source",
        "displayed_url",
        "visible_date",
        "result_text",
        "capture_http_status",
        "capture_location",
        "screenshot",
        "source_status",
    ]
    write_csv(OUTPUT_DIR / "google-serp-results.csv", rows, fields)
    write_csv(
        OUTPUT_DIR / "google-serp-features.csv",
        feature_rows,
        [
            "query",
            "http_status",
            "page_title",
            "capture_location",
            "signed_in_indicator",
            "features",
            "ai_overview_present",
            "ai_overview_text",
            "ai_overview_link_labels",
            "related_searches",
            "screenshot",
            "source_status",
        ],
    )


def main() -> int:
    payload = capture()
    flatten(payload)
    print(json.dumps({
        "captures": len(payload["captures"]),
        "organic_results": sum(len(item.get("organic_results") or []) for item in payload["captures"]),
        "ai_overview_captures": sum(bool(item.get("ai_overview_present")) for item in payload["captures"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
