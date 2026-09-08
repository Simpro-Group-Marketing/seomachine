#!/usr/bin/env python3
"""Capture source-bound desktop and mobile evidence for the live plumbing article."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO / "research" / "best-plumbing-job-management-software-remediation-2026-09-03"
RAW_DIR = OUTPUT_DIR / "raw" / "live-page"
NPM_CACHE = Path.home() / "AppData" / "Local" / "npm-cache" / "_npx"
SESSION = "plumbing-serp-recovery"
URL = "https://www.simprogroup.com/blog/best-plumbing-job-management-software"
HUB_URL = "https://www.simprogroup.com/blog/page:6"
DATE_QUERY = '"8 Best Plumbing Job Management Software Tools for Growing Plumbing Businesses" "May 6, 2026"'


def cli_path() -> Path:
    candidates = sorted(NPM_CACHE.glob("*/node_modules/@playwright/cli/playwright-cli.js"))
    if not candidates:
        raise FileNotFoundError("@playwright/cli was not found in the npm cache")
    return candidates[0]


def run_cli(*args: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def capture() -> dict[str, Any]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    url_json = json.dumps(URL)
    hub_url_json = json.dumps(HUB_URL)
    date_query_json = json.dumps(DATE_QUERY)
    output_dir_json = json.dumps(str(RAW_DIR).replace("\\", "/"))
    javascript = f"""async function run(page) {{
      const url = {url_json};
      const hubUrl = {hub_url_json};
      const dateQuery = {date_query_json};
      const outputDir = {output_dir_json};
      const viewports = [
        {{name: 'desktop', width: 1440, height: 1000}},
        {{name: 'mobile', width: 390, height: 844}}
      ];
      const captures = [];
      for (const viewport of viewports) {{
        await page.setViewportSize({{width: viewport.width, height: viewport.height}});
        const response = await page.goto(url, {{waitUntil: 'networkidle', timeout: 90000}});
        await page.waitForTimeout(1500);
        const data = await page.evaluate(() => {{
          const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
          const visible = element => {{
            const style = window.getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
          }};
          const meta = selector => document.querySelector(selector)?.getAttribute('content') || '';
          const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
            .map((script, index) => {{
              try {{
                return {{index, valid_json: true, value: JSON.parse(script.textContent || '')}};
              }} catch (error) {{
                return {{index, valid_json: false, error: String(error), raw: (script.textContent || '').slice(0, 2000)}};
              }}
            }});
          const bodyText = clean(document.body.innerText);
          const main = document.querySelector('main, article, [role="main"]');
          const mainText = clean(main?.innerText || '');
          const leakPatterns = [
            'original eight tools',
            'same order as the current article',
            'fixes the incorrect electrical',
            'keeps the existing url slug',
            'before cms publish',
            'cms publish',
            'editorial instruction'
          ];
          return {{
            final_url: location.href,
            title: document.title,
            meta_description: meta('meta[name="description"]'),
            meta_robots: meta('meta[name="robots"]'),
            googlebot: meta('meta[name="googlebot"]'),
            canonical: document.querySelector('link[rel="canonical"]')?.href || '',
            h1s: Array.from(document.querySelectorAll('h1')).map(element => clean(element.innerText)),
            headings: Array.from(document.querySelectorAll('h1,h2,h3')).map(element => ({{
              level: element.tagName.toLowerCase(),
              text: clean(element.innerText)
            }})),
            time_elements: Array.from(document.querySelectorAll('time')).map(element => ({{
              text: clean(element.innerText),
              datetime: element.getAttribute('datetime') || ''
            }})),
            publication_meta: {{
              article_published_time: meta('meta[property="article:published_time"]'),
              article_modified_time: meta('meta[property="article:modified_time"]'),
              date: meta('meta[name="date"]'),
              date_published: meta('meta[itemprop="datePublished"]'),
              date_modified: meta('meta[itemprop="dateModified"]')
            }},
            json_ld: scripts,
            table_count: document.querySelectorAll('table').length,
            tables: Array.from(document.querySelectorAll('table')).map((table, index) => ({{
              index,
              visible: visible(table),
              rows: table.rows.length,
              columns: Math.max(0, ...Array.from(table.rows).map(row => row.cells.length)),
              width: Math.round(table.getBoundingClientRect().width),
              viewport_overflow: table.getBoundingClientRect().right > window.innerWidth,
              text_sample: clean(table.innerText).slice(0, 1000)
            }})),
            body_word_count: bodyText ? bodyText.split(/\\s+/).length : 0,
            main_word_count: mainText ? mainText.split(/\\s+/).length : 0,
            leak_matches: leakPatterns.filter(pattern => bodyText.toLowerCase().includes(pattern)),
            main_text: mainText,
            main_html: main?.innerHTML || ''
          }};
        }});
        data.viewport = viewport;
        data.http_status = response ? response.status() : null;
        data.response_headers = response ? await response.allHeaders() : {{}};
        data.captured_at = new Date().toISOString();
        const screenshot = outputDir + '/' + viewport.name + '-live-page.png';
        await page.screenshot({{path: screenshot, fullPage: false}});
        data.screenshot = screenshot;
        captures.push(data);
      }}
      await page.setViewportSize({{width: 1440, height: 1000}});
      const hubResponse = await page.goto(hubUrl, {{waitUntil: 'domcontentloaded', timeout: 90000}});
      await page.waitForTimeout(1000);
      const publicationHistory = await page.evaluate(() => {{
        const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
        const matches = Array.from(document.querySelectorAll('a[href*="/blog/best-plumbing-job-management-software"]'))
          .map(anchor => {{
            let node = anchor;
            let context = clean(anchor.innerText);
            for (let depth = 0; depth < 7 && node.parentElement; depth++) {{
              node = node.parentElement;
              const candidate = clean(node.innerText);
              if (/May\\s+6,\\s+2026/i.test(candidate)) {{
                context = candidate;
                break;
              }}
            }}
            return {{
              href: anchor.href,
              link_text: clean(anchor.innerText),
              context_text: context.slice(0, 1200)
            }};
          }});
        return {{
          final_url: location.href,
          page_title: document.title,
          matches
        }};
      }});
      publicationHistory.http_status = hubResponse ? hubResponse.status() : null;
      publicationHistory.captured_at = new Date().toISOString();
      publicationHistory.screenshot = outputDir + '/publication-history-hub.png';
      await page.screenshot({{path: publicationHistory.screenshot, fullPage: false}});
      const dateSearchUrl = 'https://www.google.com/search?q=' + encodeURIComponent(dateQuery) + '&gl=us&hl=en&pws=0';
      const dateSearchResponse = await page.goto(dateSearchUrl, {{waitUntil: 'domcontentloaded', timeout: 90000}});
      await page.waitForTimeout(2000);
      const publicationSearch = await page.evaluate(() => {{
        const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
        const bodyText = clean(document.body.innerText);
        return {{
          final_url: location.href,
          page_title: document.title,
          signed_in_indicator: !Array.from(document.querySelectorAll('a')).some(anchor => clean(anchor.innerText) === 'Sign in'),
          contains_original_title: /8 Best Plumbing Job Management Software Tools for Growing Plumbing Businesses/i.test(bodyText),
          contains_may_6_2026: /May\\s+6,\\s+2026/i.test(bodyText),
          body_text_sample: bodyText.slice(0, 12000)
        }};
      }});
      publicationSearch.query = dateQuery;
      publicationSearch.http_status = dateSearchResponse ? dateSearchResponse.status() : null;
      publicationSearch.captured_at = new Date().toISOString();
      publicationSearch.screenshot = outputDir + '/publication-history-google.png';
      await page.screenshot({{path: publicationSearch.screenshot, fullPage: false}});
      return {{captures, publication_history: publicationHistory, publication_search: publicationSearch}};
    }}"""
    result = run_cli("--json", "run-code", javascript, timeout=240)
    wrapper = json.loads(result.stdout)
    captured = json.loads(wrapper["result"])
    payload = {
        "schema": "simpro-live-page-render-evidence/v1",
        "captured_at": datetime.now().astimezone().isoformat(),
        "requested_url": URL,
        "browser": "Google Chrome via persistent Playwright profile",
        "captures": captured["captures"],
        "publication_history": captured["publication_history"],
        "publication_search": captured["publication_search"],
    }
    write_json(RAW_DIR / "live-page-captures.json", payload)
    return payload


def main() -> int:
    payload = capture()
    summary = [
        {
            "viewport": item["viewport"]["name"],
            "http_status": item["http_status"],
            "canonical": item["canonical"],
            "h1_count": len(item["h1s"]),
            "table_count": item["table_count"],
            "main_word_count": item["main_word_count"],
            "leak_matches": item["leak_matches"],
            "publication_meta": item["publication_meta"],
        }
        for item in payload["captures"]
    ]
    output = {
        "render_captures": summary,
        "publication_history": payload["publication_history"],
        "publication_search": payload["publication_search"],
    }
    write_json(OUTPUT_DIR / "live-cms-render-summary.json", output)
    print(json.dumps(output, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
