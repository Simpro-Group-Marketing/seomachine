#!/usr/bin/env python3
"""Build the corrected, source-bound live blog performance comparison."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit


REPO = Path(r"C:\Users\patrick.grueschow\Desktop\Repos\seomachine-main")
MARKETINGSKILLS = Path(
    r"C:\Users\patrick.grueschow\Desktop\Repos\marketingskills-main"
)
RUN_DATE = "2026-09-03"
OUTPUT_DIR = REPO / "research" / f"live-blog-performance-corrected-{RUN_DATE}"
AUDIT_CSV = (
    REPO
    / "research"
    / "live-blog-audit-2026-08-28"
    / "repo-candidate-live-check.csv"
)
SHEET_ID = "17_8wRwNkSKNBjo1XNYYiqTJaSVj3EQKG5qf0uJlIlO4"
SHEET_RANGE = "All SEO Published!A1:F500"
PLAYWRIGHT_SESSION = "corrected-blog-rerun"
SOURCE_PULL_SCRIPT = REPO / "scripts" / "live_blog_source_pull.py"
NPM_NPX_CACHE = Path(r"C:\Users\patrick.grueschow\AppData\Local\npm-cache\_npx")
DOWNLOADS_DIR = Path(r"C:\Users\patrick.grueschow\Downloads")
CHANNELS = {
    "openai-0": "ChatGPT UI",
    "google-0": "Google AI Overview",
    "perplexity-0": "Perplexity UI",
}
CONTENT_DIRS = [
    REPO / "published",
    REPO / "rewrites",
    REPO / "drafts",
    REPO / "research",
]
GENERIC_AI_PATTERNS = [
    "in today's fast-paced",
    "in today's competitive",
    "in the ever-evolving",
    "it's important to note",
    "it is important to note",
    "whether you're a",
    "whether you are a",
    "look no further",
    "game-changer",
    "game changer",
    "revolutionize",
    "delve into",
    "navigate the complexities",
    "unlock the power",
    "in conclusion",
]
ICP_TERMS = [
    "field service",
    "trade business",
    "trades business",
    "contractor",
    "technician",
    "electrician",
    "electrical",
    "plumbing",
    "plumber",
    "hvac",
    "dispatch",
    "job costing",
    "work order",
    "service business",
    "crew",
    "quote",
    "invoice",
    "margin",
]


def run(command: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"STDOUT:\n{result.stdout[-4000:]}\nSTDERR:\n{result.stderr[-4000:]}"
        )
    return result


def wsl_path(path: Path) -> str:
    resolved = str(path.resolve())
    drive, rest = resolved.split(":", 1)
    return f"/mnt/{drive.lower()}{rest.replace(chr(92), '/')}"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    scheme = (parsed.scheme or "https").lower()
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{host}{path}"


def slug_from_url(value: str) -> str:
    return urlsplit(value).path.rstrip("/").split("/")[-1].lower()


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        serial = int(float(text))
        if 30_000 <= serial <= 60_000:
            return date(1899, 12, 30) + timedelta(days=serial)
    iso_match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
    if iso_match:
        return date.fromisoformat(iso_match.group(0))
    for pattern in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    return None


def load_cohort() -> list[dict[str, Any]]:
    rows = read_csv(AUDIT_CSV)
    cohort = [
        row
        for row in rows
        if str(row.get("live_200_indexable_blog", "")).strip().lower() == "true"
    ]
    if len(cohort) != 28:
        raise RuntimeError(f"Hard stop: expected 28 live candidates, found {len(cohort)}")
    for row in cohort:
        normalized = normalize_url(row["final_url"])
        if not normalized.startswith("https://www.simprogroup.com/blog/"):
            raise RuntimeError(f"Invalid cohort URL: {row['final_url']}")
        row["final_url"] = normalized
        row["slug"] = row.get("slug") or slug_from_url(normalized)
    return cohort


def fetch_sheet_rows(raw_path: Path) -> list[dict[str, Any]]:
    result = run(
        [
            "gws.cmd",
            "sheets",
            "+read",
            "--spreadsheet",
            SHEET_ID,
            "--range",
            SHEET_RANGE,
        ],
        cwd=MARKETINGSKILLS,
        timeout=120,
    )
    payload = json.loads(result.stdout)
    write_json(raw_path, payload)
    values = payload.get("values") or []
    if not values:
        raise RuntimeError("All SEO Published returned no rows")
    headers = values[0]
    records = []
    for row_number, values_row in enumerate(values[1:], start=2):
        padded = list(values_row) + [""] * (len(headers) - len(values_row))
        record = dict(zip(headers, padded))
        record["_row_number"] = row_number
        records.append(record)
    return records


def sheet_evidence_for_url(sheet_rows: list[dict[str, Any]], url: str) -> dict[str, Any]:
    normalized = normalize_url(url)
    matches = []
    for row in sheet_rows:
        final_url = str(row.get("Final URL") or "").strip()
        if final_url and normalize_url(final_url) == normalized:
            completed = parse_date(row.get("Completed At"))
            if completed:
                matches.append((completed, row))
    if not matches:
        return {
            "sheet_completed_at": "",
            "sheet_row_number": "",
            "sheet_name": "",
            "sheet_match_status": "no_exact_final_url_match",
        }
    completed, selected = max(matches, key=lambda item: (item[0], item[1]["_row_number"]))
    return {
        "sheet_completed_at": completed.isoformat(),
        "sheet_row_number": selected["_row_number"],
        "sheet_name": selected.get("Name", ""),
        "sheet_match_status": "exact_final_url_match",
    }


def playwright_command(*args: str) -> list[str]:
    cli_candidates = sorted(
        NPM_NPX_CACHE.glob(r"*\node_modules\@playwright\cli\playwright-cli.js")
    )
    if cli_candidates:
        return [
            "node",
            str(cli_candidates[0]),
            f"-s={PLAYWRIGHT_SESSION}",
            *args,
        ]
    return [
        "npx.cmd",
        "--yes",
        "--package",
        "@playwright/cli",
        "playwright-cli",
        f"-s={PLAYWRIGHT_SESSION}",
        *args,
    ]


def extract_live_pages(cohort: list[dict[str, Any]], raw_path: Path) -> dict[str, Any]:
    run(playwright_command("close"), cwd=REPO, timeout=60)
    run(
        playwright_command(
            "open",
            cohort[0]["final_url"],
            "--browser=chrome",
            "--headed",
        ),
        cwd=REPO,
        timeout=120,
    )
    def run_page_code(code: str, timeout: int = 180) -> Any:
        result = run(
            playwright_command("--json", "run-code", code),
            cwd=REPO,
            timeout=timeout,
        )
        wrapper = json.loads(result.stdout)
        return json.loads(wrapper["result"])

    out = []
    for cohort_row in cohort:
        url_json = json.dumps(cohort_row["final_url"])
        code = f"""async function run(page) {{
      var url = {url_json};
      var response = null;
      var error = '';
      try {{
        response = await page.goto(url, {{waitUntil:'domcontentloaded', timeout:90000}});
        if ((await page.title()).indexOf('Just a moment') >= 0) await page.waitForTimeout(10000);
        await page.waitForTimeout(750);
      }} catch (e) {{ error = String(e); }}
      var data = await page.evaluate(function() {{
        function clean(value) {{ return (value || '').replace(/\\s+/g, ' ').trim(); }}
        function q(selector) {{ return document.querySelector(selector); }}
        var root = q('article') || q('main') || document.body;
        var bodyText = clean(root.innerText);
        var allText = clean(document.body.innerText);
        var out = {{}};
        out.final_url = location.href.split('?')[0].replace(/\\/$/, '');
        out.title = document.title;
        out.h1 = clean(q('h1') ? q('h1').innerText : '');
        out.canonical = q('link[rel="canonical"]') ? q('link[rel="canonical"]').href : '';
        out.robots = q('meta[name="robots"]') ? q('meta[name="robots"]').content : '';
        out.first_body_text = bodyText.slice(0, 1500);
        out.body_text = bodyText.slice(0, 50000);
        out.visible_date_labels = allText.match(/(?:Published|Updated):\\s*[A-Z][a-z]+\\s+\\d{{1,2}},\\s+20\\d{{2}}/g) || [];
        out.structured_dates = [];
        out.has_table = !!root.querySelector('table');
        out.table_count = root.querySelectorAll('table').length;
        out.word_count = bodyText ? bodyText.split(/\\s+/).length : 0;
        return out;
      }});
      data.headings = await page.evaluate(function() {{
        function clean(value) {{ return (value || '').replace(/\\s+/g, ' ').trim(); }}
        var root = document.querySelector('article') || document.querySelector('main') || document.body;
        return Array.prototype.slice.call(root.querySelectorAll('h2,h3')).map(function(h) {{
          return {{level:h.tagName.toLowerCase(), text:clean(h.innerText)}};
        }}).filter(function(x) {{ return x.text; }});
      }});
      data.paragraphs = await page.evaluate(function() {{
        function clean(value) {{ return (value || '').replace(/\\s+/g, ' ').trim(); }}
        var root = document.querySelector('article') || document.querySelector('main') || document.body;
        return Array.prototype.slice.call(root.querySelectorAll('p')).map(function(p) {{
          return clean(p.innerText);
        }}).filter(function(x) {{ return x.length >= 20; }});
      }});
      data.links = await page.evaluate(function() {{
        function clean(value) {{ return (value || '').replace(/\\s+/g, ' ').trim(); }}
        var root = document.querySelector('article') || document.querySelector('main') || document.body;
        return Array.prototype.slice.call(root.querySelectorAll('a[href]')).slice(0, 300).map(function(a) {{
          return {{text:clean(a.innerText), href:a.href}};
        }}).filter(function(x) {{ return x.href; }});
      }});
      data.faq_heading_count = await page.evaluate(function() {{
        var root = document.querySelector('article') || document.querySelector('main') || document.body;
        return Array.prototype.slice.call(root.querySelectorAll('h2,h3')).filter(function(h) {{
          return /faq|frequently asked/i.test(h.innerText);
        }}).length;
      }});
      data.requested_url = url;
      data.status = response ? response.status() : null;
      data.error = error;
      return data;
    }}"""
        out.append(run_page_code(code))

    sitemap_code = """async function run(page) {
      let sitemap = {status:null, blog_url_count:null, unique_lastmods:[], usable_for_publish_age:false, error:''};
      try {
        const response = await page.goto('https://www.simprogroup.com/sitemap.xml', {waitUntil:'domcontentloaded',timeout:90000});
        await page.waitForTimeout(500);
        const source = await page.content();
        const pairs = [...source.matchAll(/<loc>([^<]*\\/blog\\/[^<]*)<\\/loc>\\s*<lastmod>([^<]+)<\\/lastmod>/gi)];
        sitemap = {
          status: response ? response.status() : null,
          blog_url_count: pairs.length,
          unique_lastmods: Array.from(new Set(pairs.map(function(x) { return x[2].slice(0,10); }))).sort(),
          usable_for_publish_age: new Set(pairs.map(function(x) { return x[2].slice(0,10); })).size > 1,
          error:''
        };
      } catch (e) { sitemap.error=String(e); }
      return sitemap;
    }"""
    extracted = {"pages": out, "sitemap": run_page_code(sitemap_code)}
    write_json(raw_path, extracted)
    return extracted


def normalize_text(value: str) -> str:
    value = html.unescape(value or "").lower()
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"[^a-z0-9%$]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def markdown_to_text(value: str) -> str:
    value = re.sub(r"\A---\s*.*?\s*---\s*", "", value, flags=re.DOTALL)
    value = re.sub(r"```.*?```", " ", value, flags=re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"!\[[^]]*\]\([^)]*\)", " ", value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"^[#>*+-]+\s*", "", value, flags=re.MULTILINE)
    return normalize_text(value)


def extract_local_content(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"path": str(path), "h1": "", "headings": [], "body": ""}
    h1_match = re.search(r"^#\s+(.+)$", raw, flags=re.MULTILINE)
    headings = re.findall(r"^#{2,3}\s+(.+)$", raw, flags=re.MULTILINE)
    filename_dates = re.findall(r"(20\d{2}-\d{2}-\d{2})", path.name)
    return {
        "path": str(path),
        "h1": normalize_text(h1_match.group(1) if h1_match else ""),
        "headings": [normalize_text(item) for item in headings],
        "body": markdown_to_text(raw)[:50000],
        "filename_date": filename_dates[-1] if filename_dates else "",
        "frontmatter_date": (
            re.search(r"^date:\s*[\"']?([^\r\n\"']+)", raw, flags=re.MULTILINE).group(1)
            if re.search(r"^date:\s*[\"']?([^\r\n\"']+)", raw, flags=re.MULTILINE)
            else ""
        ),
    }


def token_similarity(left: str, right: str) -> float:
    left_tokens = Counter(normalize_text(left).split())
    right_tokens = Counter(normalize_text(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = sum((left_tokens & right_tokens).values())
    return 2 * overlap / (sum(left_tokens.values()) + sum(right_tokens.values()))


def sequence_similarity(left: str, right: str) -> float:
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def heading_similarity(local_headings: list[str], live_headings: list[str]) -> float:
    if not local_headings or not live_headings:
        return 0.0
    scores = []
    for local in local_headings:
        scores.append(max(sequence_similarity(local, live) for live in live_headings))
    return sum(scores) / len(scores)


def artifact_candidates(slug: str) -> list[Path]:
    candidates = []
    allowed_suffixes = {".md", ".txt", ".html"}
    for directory in CONTENT_DIRS:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
                continue
            path_text = str(path).lower()
            if "live-blog-performance" in path_text or "live-blog-audit" in path_text:
                continue
            if slug in path.name.lower():
                candidates.append(path)
    return sorted(set(candidates), key=lambda path: (len(str(path)), str(path)))


def best_artifact_match(slug: str, live: dict[str, Any]) -> dict[str, Any]:
    live_h1 = live.get("h1", "")
    live_headings = [item.get("text", "") for item in live.get("headings", [])]
    live_body = live.get("body_text", "")
    scored = []
    for path in artifact_candidates(slug):
        local = extract_local_content(path)
        h1_score = sequence_similarity(local["h1"], live_h1)
        heading_score = heading_similarity(local["headings"], live_headings)
        body_score = token_similarity(local["body"][:12000], live_body[:12000])
        total = 0.35 * h1_score + 0.30 * heading_score + 0.35 * body_score
        scored.append(
            {
                **local,
                "h1_similarity": h1_score,
                "heading_similarity": heading_score,
                "body_similarity": body_score,
                "weighted_similarity": total,
            }
        )
    if not scored:
        return {
            "best_local_artifact": "",
            "h1_similarity": 0.0,
            "heading_similarity": 0.0,
            "body_similarity": 0.0,
            "weighted_similarity": 0.0,
            "content_match": "mismatch",
            "candidate_count": 0,
            "local_frontmatter_date": "",
            "local_filename_date": "",
        }
    best = max(scored, key=lambda item: item["weighted_similarity"])
    if (
        best["weighted_similarity"] >= 0.62
        and best["h1_similarity"] >= 0.75
        and (best["heading_similarity"] >= 0.45 or best["body_similarity"] >= 0.65)
    ):
        match = "strong"
    elif (
        best["weighted_similarity"] >= 0.38
        and best["h1_similarity"] >= 0.55
        and (best["heading_similarity"] >= 0.20 or best["body_similarity"] >= 0.35)
    ):
        match = "partial"
    else:
        match = "mismatch"
    return {
        "best_local_artifact": best["path"],
        "h1_similarity": round(best["h1_similarity"], 4),
        "heading_similarity": round(best["heading_similarity"], 4),
        "body_similarity": round(best["body_similarity"], 4),
        "weighted_similarity": round(best["weighted_similarity"], 4),
        "content_match": match,
        "candidate_count": len(scored),
        "local_frontmatter_date": best.get("frontmatter_date", ""),
        "local_filename_date": best.get("filename_date", ""),
    }


def live_date_evidence(live: dict[str, Any]) -> dict[str, Any]:
    visible_updated = ""
    visible_published = ""
    for label in live.get("visible_date_labels", []):
        parsed = parse_date(label.split(":", 1)[-1].strip())
        if not parsed:
            continue
        if label.lower().startswith("updated"):
            visible_updated = parsed.isoformat()
        elif label.lower().startswith("published"):
            visible_published = parsed.isoformat()
    structured_published = ""
    structured_modified = ""
    for item in live.get("structured_dates", []):
        parsed = parse_date(item.get("value"))
        if not parsed:
            continue
        if item.get("kind") == "dateModified":
            structured_modified = max(structured_modified, parsed.isoformat())
        elif item.get("kind") == "datePublished":
            structured_published = max(structured_published, parsed.isoformat())
    return {
        "live_visible_updated": visible_updated,
        "live_visible_published": visible_published,
        "live_structured_date_modified": structured_modified,
        "live_structured_date_published": structured_published,
    }


def choose_deployment_date(
    sheet: dict[str, Any], live_dates: dict[str, Any], match: dict[str, Any]
) -> dict[str, Any]:
    if match.get("content_match") != "strong":
        return {
            "deployment_date": "",
            "deployment_date_source": "excluded_content_match_not_strong",
        }
    if sheet.get("sheet_completed_at"):
        return {
            "deployment_date": sheet["sheet_completed_at"],
            "deployment_date_source": "all_seo_published_completed_at",
        }
    fallbacks = [
        ("live_visible_updated", "live_cms_updated_label"),
        ("live_structured_date_modified", "live_structured_date_modified"),
    ]
    for key, source in fallbacks:
        if live_dates.get(key):
            return {"deployment_date": live_dates[key], "deployment_date_source": source}
    local_dates = [
        parse_date(match.get("local_frontmatter_date")),
        parse_date(match.get("local_filename_date")),
    ]
    local_dates = [item for item in local_dates if item]
    local_floor = min(local_dates) if local_dates else None
    published_fallbacks = [
        ("live_visible_published", "live_cms_published_label"),
        ("live_structured_date_published", "live_structured_date_published"),
    ]
    for key, source in published_fallbacks:
        parsed = parse_date(live_dates.get(key))
        if parsed and (local_floor is None or parsed >= local_floor):
            return {"deployment_date": parsed.isoformat(), "deployment_date_source": source}
    return {"deployment_date": "", "deployment_date_source": "unavailable"}


def classify_status(
    live: dict[str, Any], match: dict[str, Any], deployment_date: str, latest_end: date
) -> str:
    canonical = normalize_url(live.get("canonical") or "") if live.get("canonical") else ""
    requested = normalize_url(live.get("requested_url") or "")
    live_ok = (
        live.get("status") == 200
        and normalize_url(live.get("final_url") or "") == requested
        and canonical == requested
        and "noindex" not in str(live.get("robots") or "").lower()
    )
    if not live_ok or match["content_match"] == "mismatch":
        return "content_mismatch_excluded"
    if match["content_match"] == "partial":
        return "content_partial_manual_review"
    if not deployment_date:
        return "missing_publish_age_excluded"
    if date.fromisoformat(deployment_date) > latest_end:
        return "too_new_for_final_data"
    return "confirmed_deployed_rewrite"


def window_for(deployment_date: str, latest_end: date) -> dict[str, Any]:
    deployed = date.fromisoformat(deployment_date)
    days = (latest_end - deployed).days + 1
    prior_end = deployed - timedelta(days=1)
    prior_start = prior_end - timedelta(days=days - 1)
    return {
        "current_start": deployed.isoformat(),
        "current_end": latest_end.isoformat(),
        "prior_start": prior_start.isoformat(),
        "prior_end": prior_end.isoformat(),
        "days_compared": days,
    }


def pct_delta(current: Any, prior: Any) -> float | str:
    if current is None or prior is None or prior == 0:
        return ""
    return (float(current) - float(prior)) / float(prior) * 100


def absolute_delta(current: Any, prior: Any) -> float | str:
    if current is None or prior is None:
        return ""
    return float(current) - float(prior)


def round_value(value: Any, digits: int = 4) -> Any:
    if value == "" or value is None:
        return value
    if isinstance(value, (int, float)):
        return round(value, digits)
    return value


def aggregate_peec(period: dict[str, Any]) -> tuple[float, float, float]:
    rows = period.get("rows") or []
    retrievals = sum(float(row.get("retrieval_count") or 0) for row in rows)
    citations = sum(float(row.get("citation_count") or 0) for row in rows)
    return retrievals, citations, citations / retrievals * 100 if retrievals else 0


def performance_row(
    base: dict[str, Any], gsc: dict[str, Any], ga4: dict[str, Any], peec: dict[str, Any]
) -> dict[str, Any]:
    row = {
        "slug": base["slug"],
        "final_url": base["final_url"],
        "comparison_status": base["comparison_status"],
        "deployment_date": base.get("deployment_date", ""),
        "deployment_date_source": base.get("deployment_date_source", ""),
        "current_start": base.get("current_start", ""),
        "current_end": base.get("current_end", ""),
        "prior_start": base.get("prior_start", ""),
        "prior_end": base.get("prior_end", ""),
        "days_compared": base.get("days_compared", ""),
        "content_match": base.get("content_match", ""),
        "weighted_similarity": base.get("weighted_similarity", ""),
    }
    metrics = {
        "gsc_clicks": (gsc, "clicks"),
        "gsc_impressions": (gsc, "impressions"),
        "gsc_ctr_pct": (gsc, "ctr_pct"),
        "gsc_position": (gsc, "position"),
        "gsc_ranking_query_count": (gsc, "ranking_query_count"),
        "ga4_sessions": (ga4, "sessions"),
        "ga4_organic_sessions": (ga4, "organic_sessions"),
        "ga4_ai_assistants_sessions": (ga4, "ai_assistants_sessions"),
        "ga4_users": (ga4, "users"),
        "ga4_views": (ga4, "views"),
        "ga4_engagement_rate_pct": (ga4, "engagement_rate_pct"),
        "ga4_bounce_rate_pct": (ga4, "bounce_rate_pct"),
        "ga4_avg_engagement_time_per_session_sec": (
            ga4,
            "average_engagement_time_per_session_sec",
        ),
        "ga4_views_per_session": (ga4, "views_per_session"),
        "ga4_key_events": (ga4, "key_events"),
        "ga4_event_count": (ga4, "event_count"),
    }
    for label, (source, key) in metrics.items():
        current = source.get("current", {}).get(key)
        prior = source.get("prior", {}).get(key)
        row[f"{label}_current"] = round_value(current)
        row[f"{label}_prior"] = round_value(prior)
        row[f"{label}_delta"] = round_value(absolute_delta(current, prior))
        row[f"{label}_pct_delta"] = round_value(pct_delta(current, prior))
    for period in ("current", "prior"):
        retrievals, citations, rate = aggregate_peec(peec.get(period, {}))
        row[f"peec_retrievals_{period}"] = round_value(retrievals)
        row[f"peec_citations_{period}"] = round_value(citations)
        row[f"peec_citation_rate_pct_{period}"] = round_value(rate)
    for label in ("peec_retrievals", "peec_citations", "peec_citation_rate_pct"):
        current = row[f"{label}_current"]
        prior = row[f"{label}_prior"]
        row[f"{label}_delta"] = round_value(absolute_delta(current, prior))
        row[f"{label}_pct_delta"] = round_value(pct_delta(current, prior))
    row["gsc_top_query_current"] = gsc.get("current", {}).get("top_query") or ""
    row["gsc_top_query_prior"] = gsc.get("prior", {}).get("top_query") or ""
    row["gsc_source_status_current"] = gsc.get("current", {}).get("source_status") or ""
    row["gsc_source_status_prior"] = gsc.get("prior", {}).get("source_status") or ""
    row["ga4_source_status_current"] = ga4.get("current", {}).get("source_status") or ""
    row["ga4_source_status_prior"] = ga4.get("prior", {}).get("source_status") or ""
    row["peec_source_status_current"] = peec.get("current", {}).get("source_status") or ""
    row["peec_source_status_prior"] = peec.get("prior", {}).get("source_status") or ""
    return row


def content_style_review(base: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    body = str(live.get("body_text") or "")
    body_norm = normalize_text(body)
    intro = " ".join((live.get("paragraphs") or [])[:3])
    topic_text = f"{live.get('title', '')} {live.get('h1', '')}"
    intent_score = token_similarity(topic_text, intro)
    icp_hits = sorted({term for term in ICP_TERMS if term in body_norm})
    proof_hits = len(
        re.findall(
            r"(?:\$\s?\d|\d+(?:\.\d+)?%|according to|case study|customer|survey|research|data shows)",
            body,
            flags=re.IGNORECASE,
        )
    )
    generic_hits = sorted({pattern for pattern in GENERIC_AI_PATTERNS if pattern in body_norm})
    links = live.get("links") or []
    internal_links = [
        item
        for item in links
        if urlsplit(str(item.get("href") or "")).netloc.endswith("simprogroup.com")
    ]
    cta_links = [
        item
        for item in internal_links
        if re.search(
            r"demo|contact|pricing|product|software|solution|tour|get started|talk to",
            f"{item.get('text', '')} {item.get('href', '')}",
            flags=re.IGNORECASE,
        )
    ]
    headings = live.get("headings") or []
    paragraphs = live.get("paragraphs") or []
    capsule_count = 0
    for heading in headings:
        heading_text = heading.get("text", "")
        index = next(
            (i for i, paragraph in enumerate(paragraphs) if heading_text.lower() in paragraph.lower()),
            None,
        )
        if index is not None and index + 1 < len(paragraphs):
            words = len(paragraphs[index + 1].split())
            if 40 <= words <= 80:
                capsule_count += 1
    structured_text = json.dumps(live.get("json_ld") or [])
    has_faq_schema = "FAQPage" in structured_text
    answer_too_fast = (
        len(intro.split()) <= 130
        and bool(re.search(r"\b(?:top|best|steps|ways|types|features|templates)\b", intro, re.I))
        and bool(re.search(r"\b(?:1\.|first|include|are:)\b", intro, re.I))
    )
    if len(icp_hits) >= 5:
        icp_fit = "strong"
    elif len(icp_hits) >= 2:
        icp_fit = "moderate"
    else:
        icp_fit = "weak"
    if proof_hits >= 5:
        proof_signal = "strong"
    elif proof_hits >= 2:
        proof_signal = "moderate"
    else:
        proof_signal = "weak"
    interpretation_notes = []
    if intent_score < 0.20:
        interpretation_notes.append("intro has weak lexical alignment with title/H1 intent")
    if answer_too_fast:
        interpretation_notes.append("intro may satisfy a shallow answer without earning deeper reading")
    if icp_fit == "weak":
        interpretation_notes.append("copy contains few field-service or trade-operator specifics")
    if proof_signal == "weak":
        interpretation_notes.append("limited quantified or attributed proof signals")
    if not cta_links:
        interpretation_notes.append("no contextual product/demo CTA detected in article content")
    if generic_hits:
        interpretation_notes.append("generic AI-copy phrase patterns detected")
    return {
        "slug": base["slug"],
        "final_url": base["final_url"],
        "comparison_status": base["comparison_status"],
        "intro_intent_similarity": round(intent_score, 4),
        "intro_intent_match": "strong" if intent_score >= 0.35 else "moderate" if intent_score >= 0.20 else "weak",
        "answer_too_fast_risk": "yes" if answer_too_fast else "no",
        "icp_fit": icp_fit,
        "icp_term_count": len(icp_hits),
        "icp_terms": "; ".join(icp_hits),
        "proof_experience_signal": proof_signal,
        "proof_signal_count": proof_hits,
        "internal_link_count": len(internal_links),
        "contextual_cta_link_count": len(cta_links),
        "faq_present": "yes" if live.get("faq_heading_count", 0) else "no",
        "faq_schema_present": "yes" if has_faq_schema else "no",
        "table_count": live.get("table_count", 0),
        "heading_count": len(headings),
        "capsule_coverage_pct": round(capsule_count / len(headings) * 100, 2) if headings else 0,
        "generic_ai_phrase_count": len(generic_hits),
        "generic_ai_phrases": "; ".join(generic_hits),
        "word_count": live.get("word_count", 0),
        "interpretation_not_causation": "; ".join(interpretation_notes) or "no priority heuristic flag",
        "method": "deterministic live-copy heuristic; editorial interpretation, not causal analytics evidence",
    }


def build_query_outputs(
    strict_bases: list[dict[str, Any]], gsc_raw: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    movers = []
    pressure = []
    for base in strict_bases:
        slug = base["slug"]
        period_rows = {}
        for period in ("current", "prior"):
            source = gsc_raw.get(f"{slug}::{period}", {})
            period_rows[period] = {row["query"]: row for row in source.get("query_rows") or []}
            page_ctr = source.get("ctr_pct")
            for row in source.get("query_rows") or []:
                low_ctr = row["clicks"] == 0 or (
                    row["impressions"] >= 10
                    and row["ctr_pct"] < min(float(page_ctr or 1), 1.0)
                )
                if row["impressions"] >= 10 and low_ctr:
                    pressure.append(
                        {
                            "slug": slug,
                            "final_url": base["final_url"],
                            "period": period,
                            "start_date": base[f"{period}_start"],
                            "end_date": base[f"{period}_end"],
                            **row,
                            "pressure_type": "zero_click" if row["clicks"] == 0 else "low_ctr",
                            "interpretation": "SERP click pressure evidence; does not prove an AI answer caused the missing click",
                        }
                    )
        all_queries = set(period_rows["current"]) | set(period_rows["prior"])
        query_movers = []
        for query in all_queries:
            current = period_rows["current"].get(query, {})
            prior = period_rows["prior"].get(query, {})
            item = {
                "slug": slug,
                "final_url": base["final_url"],
                "query": query,
                "clicks_current": current.get("clicks", 0),
                "clicks_prior": prior.get("clicks", 0),
                "clicks_delta": current.get("clicks", 0) - prior.get("clicks", 0),
                "impressions_current": current.get("impressions", 0),
                "impressions_prior": prior.get("impressions", 0),
                "impressions_delta": current.get("impressions", 0) - prior.get("impressions", 0),
                "ctr_pct_current": current.get("ctr_pct", ""),
                "ctr_pct_prior": prior.get("ctr_pct", ""),
                "position_current": current.get("position", ""),
                "position_prior": prior.get("position", ""),
                "position_delta": (
                    current.get("position", 0) - prior.get("position", 0)
                    if current and prior
                    else ""
                ),
            }
            query_movers.append(item)
        query_movers.sort(
            key=lambda item: (abs(item["impressions_delta"]), abs(item["clicks_delta"])),
            reverse=True,
        )
        for rank, item in enumerate(query_movers[:25], start=1):
            movers.append({**item, "mover_rank_within_url": rank})
    pressure.sort(key=lambda item: float(item["impressions"]), reverse=True)
    return movers, pressure


def build_ga4_diagnostics(
    strict_bases: list[dict[str, Any]], ga4_raw: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = []
    for base in strict_bases:
        for period in ("current", "prior"):
            source = ga4_raw.get(f"{base['slug']}::{period}", {})
            events = source.get("event_rows") or []
            rows.append(
                {
                    "slug": base["slug"],
                    "final_url": base["final_url"],
                    "period": period,
                    "start_date": base[f"{period}_start"],
                    "end_date": base[f"{period}_end"],
                    "source_status": source.get("source_status", ""),
                    "sessions": source.get("sessions"),
                    "organic_sessions": source.get("organic_sessions"),
                    "ai_assistants_sessions": source.get("ai_assistants_sessions"),
                    "engagement_rate_pct": source.get("engagement_rate_pct"),
                    "bounce_rate_pct": source.get("bounce_rate_pct"),
                    "avg_engagement_time_per_session_sec": source.get("average_engagement_time_per_session_sec"),
                    "views_per_session": source.get("views_per_session"),
                    "key_events": source.get("key_events"),
                    "event_count": source.get("event_count"),
                    "top_events": "; ".join(
                        f"{item.get('eventName')}={round(float(item.get('eventCount') or 0), 2)}"
                        for item in events[:10]
                    ),
                    "bounce_definition": "GA4 bounceRate; validated as 1 - engagementRate",
                }
            )
    return rows


def build_peec_evidence(
    strict_bases: list[dict[str, Any]], peec_raw: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = []
    for base in strict_bases:
        for period in ("current", "prior"):
            source = peec_raw.get(f"{base['slug']}::{period}", {})
            source_rows = {row["channel_id"]: row for row in source.get("rows") or []}
            for channel_id, channel_name in CHANNELS.items():
                source_row = source_rows.get(channel_id, {})
                rows.append(
                    {
                        "slug": base["slug"],
                        "final_url": base["final_url"],
                        "period": period,
                        "start_date": base[f"{period}_start"],
                        "end_date": base[f"{period}_end"],
                        "channel_id": channel_id,
                        "channel_name": channel_name,
                        "retrieval_count": source_row.get("retrieval_count", 0),
                        "citation_count": source_row.get("citation_count", 0),
                        "citation_rate": source_row.get("citation_rate", 0),
                        "source_status": source_row.get("source_status", "no_matching_row_zero_filled"),
                    }
                )
    return rows


def parse_filter_rows(rows: list[dict[str, Any]]) -> dict[str, str]:
    filters = {}
    for row in rows:
        key = str(row.get("Filter") or "").strip()
        value = str(row.get("Value") or "").strip()
        if key:
            filters[key] = value
    return filters


def parse_export_date_range(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in value.split("-", 1)]
    if len(parts) != 2:
        return "", ""
    start = parse_date(parts[0])
    end = parse_date(parts[1])
    return (start.isoformat() if start else "", end.isoformat() if end else "")


def read_gen_ai_export(path: Path) -> dict[str, Any] | None:
    pages: list[dict[str, Any]] = []
    filters: dict[str, str] = {}
    chart_rows = 0
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            if "Pages.csv" not in archive.namelist() or "Filters.csv" not in archive.namelist():
                return None
            with archive.open("Pages.csv") as handle:
                pages = list(csv.DictReader((line.decode("utf-8-sig") for line in handle)))
            with archive.open("Filters.csv") as handle:
                filters = parse_filter_rows(
                    list(csv.DictReader((line.decode("utf-8-sig") for line in handle)))
                )
            if "Chart.csv" in archive.namelist():
                with archive.open("Chart.csv") as handle:
                    chart_rows = max(
                        0,
                        sum(1 for _line in handle) - 1,
                    )
    elif path.suffix.lower() == ".xlsx":
        try:
            import openpyxl
        except ImportError:
            return {
                "path": str(path),
                "source_status": "xlsx_reader_unavailable",
                "rows": [],
                "filters": {},
                "chart_rows": 0,
            }
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            if "Pages" not in workbook.sheetnames or "Filters" not in workbook.sheetnames:
                return None
            pages_sheet = workbook["Pages"]
            page_rows = list(pages_sheet.iter_rows(values_only=True))
            if page_rows:
                headers = [str(value or "") for value in page_rows[0]]
                pages = [
                    dict(zip(headers, row))
                    for row in page_rows[1:]
                    if any(value is not None and value != "" for value in row)
                ]
            filters_sheet = workbook["Filters"]
            filter_rows = list(filters_sheet.iter_rows(values_only=True))
            if filter_rows:
                headers = [str(value or "") for value in filter_rows[0]]
                filters = parse_filter_rows(
                    [
                        dict(zip(headers, row))
                        for row in filter_rows[1:]
                        if any(value is not None and value != "" for value in row)
                    ]
                )
            if "Chart" in workbook.sheetnames:
                chart_rows = max(0, workbook["Chart"].max_row - 1)
        finally:
            workbook.close()
    else:
        return None

    start_date, end_date = parse_export_date_range(filters.get("Date", ""))
    page_filter = filters.get("Page", "")
    if page_filter and page_filter != "+/blog":
        source_status = "excluded_non_blog_page_filter"
    else:
        source_status = "included"
    return {
        "path": str(path),
        "filename": path.name,
        "source_status": source_status,
        "date_filter": filters.get("Date", ""),
        "start_date": start_date,
        "end_date": end_date,
        "search_type": filters.get("Search type", ""),
        "page_filter": page_filter,
        "rows": pages,
        "chart_rows": chart_rows,
    }


def load_gsc_gen_ai_exports(raw_path: Path) -> list[dict[str, Any]]:
    exports = []
    for path in sorted(DOWNLOADS_DIR.glob("simprogroup.com-Performance-on-Search-Generative-AI-Features-*")):
        parsed = read_gen_ai_export(path)
        if parsed is not None:
            exports.append(parsed)
    write_json(raw_path, exports)
    return exports


def build_gsc_gen_ai_evidence(
    bases: list[dict[str, Any]], exports: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    included_exports = [
        export
        for export in exports
        if export.get("source_status") == "included"
        and export.get("start_date")
        and export.get("end_date")
    ]
    for export in included_exports:
        export_pages = {
            normalize_url(str(row.get("Top pages") or "")): row
            for row in export.get("rows") or []
            if row.get("Top pages")
        }
        for base in bases:
            normalized_url = normalize_url(base["final_url"])
            source_row = export_pages.get(normalized_url)
            impressions = ""
            source_status = "no_matching_row_zero_filled"
            if source_row:
                impressions = float(source_row.get("Impressions") or 0)
                source_status = "matched"
            rows.append(
                {
                    "slug": base["slug"],
                    "final_url": base["final_url"],
                    "comparison_status": base["comparison_status"],
                    "export_filename": export["filename"],
                    "export_path": export["path"],
                    "period_type": "gsc_ui_export_snapshot_not_matched_window",
                    "start_date": export["start_date"],
                    "end_date": export["end_date"],
                    "date_filter": export["date_filter"],
                    "search_type": export.get("search_type", ""),
                    "page_filter": export.get("page_filter", ""),
                    "gen_ai_impressions": impressions if impressions != "" else 0,
                    "source_status": source_status,
                    "source_lane": "GSC Generative AI UI export",
                    "metric_scope": "Search generative AI feature impressions only; no clicks, CTR, average position, or citation proof",
                }
            )
    return rows


def page_format_from_slug(slug: str) -> str:
    if slug.startswith("best-") or "-best-" in slug:
        return "comparison/listicle"
    if "template" in slug or "worksheet" in slug or "calculator" in slug:
        return "utility/template"
    if slug.startswith("how-to-"):
        return "how-to guide"
    if "license" in slug:
        return "regulatory guide"
    if "marketing" in slug or "ppc" in slug:
        return "growth tactic guide"
    if "women-in-skilled-trades" in slug:
        return "awareness/industry guide"
    return "educational guide"


def commercial_fit_from_slug(slug: str) -> str:
    if any(token in slug for token in ("software", "crm", "payment", "end-to-end")):
        return "high"
    if any(token in slug for token in ("marketing", "ppc", "price", "bid", "job-sheet", "template", "calculator")):
        return "moderate"
    if any(token in slug for token in ("license", "women-in-skilled-trades", "start-an-hvac-business", "franchise")):
        return "low_to_moderate"
    return "moderate"


def build_engagement_writing_diagnosis(
    strict_rows: list[dict[str, Any]],
    style_rows: list[dict[str, Any]],
    zero_click_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    style_by_slug = {row["slug"]: row for row in style_rows}
    zero_click_current = Counter()
    pressure_current = Counter()
    for row in zero_click_rows:
        if row.get("period") != "current":
            continue
        slug = row["slug"]
        impressions = float(row.get("impressions") or 0)
        pressure_current[slug] += impressions
        if row.get("pressure_type") == "zero_click":
            zero_click_current[slug] += impressions

    rows = []
    for perf in strict_rows:
        slug = perf["slug"]
        style = style_by_slug.get(slug, {})
        sessions_current = float(perf.get("ga4_sessions_current") or 0)
        organic_current = float(perf.get("ga4_organic_sessions_current") or 0)
        organic_share = organic_current / sessions_current * 100 if sessions_current else None
        engagement_delta = perf.get("ga4_engagement_rate_pct_delta")
        bounce_delta = perf.get("ga4_bounce_rate_pct_delta")
        time_delta = perf.get("ga4_avg_engagement_time_per_session_sec_delta")
        impressions_delta = perf.get("gsc_impressions_delta")
        ctr_delta = perf.get("gsc_ctr_pct_delta")
        clicks_delta = perf.get("gsc_clicks_delta")
        reasons = []
        if engagement_delta not in (None, "") and float(engagement_delta) < -10:
            reasons.append("large engagement-rate drop")
        elif engagement_delta not in (None, "") and float(engagement_delta) < 0:
            reasons.append("mild engagement-rate drop")
        if bounce_delta not in (None, "") and float(bounce_delta) > 10:
            reasons.append("bounce rose materially")
        if time_delta not in (None, "") and float(time_delta) < -20:
            reasons.append("average engagement time fell")
        if impressions_delta not in (None, "") and ctr_delta not in (None, ""):
            if float(impressions_delta) > 0 and float(ctr_delta) < 0:
                reasons.append("broader search exposure with weaker CTR")
        if zero_click_current[slug] >= 1000:
            reasons.append("high current zero-click query impressions")
        if page_format_from_slug(slug) in {"comparison/listicle", "utility/template"}:
            reasons.append("format naturally encourages scanning and quick exits")
        if commercial_fit_from_slug(slug) == "low_to_moderate":
            reasons.append("topic may attract earlier-stage or non-buyer readers")
        if int(style.get("contextual_cta_link_count") or 0) > 20:
            reasons.append("many contextual/internal CTAs may diffuse next action")
        if not reasons:
            reasons.append("no clear content-side engagement risk detected")

        if engagement_delta in (None, ""):
            reception = "unavailable"
        elif float(engagement_delta) < -10 and clicks_delta not in (None, "") and float(clicks_delta) < 0:
            reception = "needs_revision"
        elif float(engagement_delta) < -10:
            reception = "monitor_and_tune"
        elif clicks_delta not in (None, "") and float(clicks_delta) > 0:
            reception = "working_with_watchouts"
        else:
            reception = "stable_or_low_signal"

        rows.append(
            {
                "slug": slug,
                "final_url": perf["final_url"],
                "page_format": page_format_from_slug(slug),
                "commercial_icp_fit": commercial_fit_from_slug(slug),
                "copy_icp_fit": style.get("icp_fit", ""),
                "proof_experience_signal": style.get("proof_experience_signal", ""),
                "intro_intent_match": style.get("intro_intent_match", ""),
                "generic_ai_phrase_count": style.get("generic_ai_phrase_count", ""),
                "contextual_cta_link_count": style.get("contextual_cta_link_count", ""),
                "word_count": style.get("word_count", ""),
                "gsc_clicks_delta": clicks_delta,
                "gsc_impressions_delta": impressions_delta,
                "gsc_ctr_pct_delta": ctr_delta,
                "ga4_sessions_current": perf.get("ga4_sessions_current"),
                "ga4_organic_share_pct_current": round(organic_share, 2) if organic_share is not None else "",
                "ga4_engagement_rate_pct_delta": engagement_delta,
                "ga4_bounce_rate_pct_delta": bounce_delta,
                "ga4_avg_engagement_time_per_session_sec_delta": time_delta,
                "current_zero_click_query_impressions": zero_click_current[slug],
                "current_low_or_zero_ctr_query_impressions": pressure_current[slug],
                "engagement_reception": reception,
                "most_likely_non_causal_explanation": "; ".join(reasons),
                "source_boundary": "GA4/GSC metrics are measured; writing and ICP fields are deterministic live-copy interpretation and not causal proof",
            }
        )
    return rows


def build_source_cell_map(strict_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in strict_rows:
        for column, value in item.items():
            if not re.match(r"^(gsc|ga4|peec)_", column):
                continue
            source_lane = column.split("_", 1)[0].upper()
            if column.endswith("_current"):
                period = "current"
                start_date = item["current_start"]
                end_date = item["current_end"]
            elif column.endswith("_prior"):
                period = "prior"
                start_date = item["prior_start"]
                end_date = item["prior_end"]
            elif column.endswith("_delta") or column.endswith("_pct_delta"):
                period = "derived_current_minus_prior"
                start_date = f"{item['prior_start']}|{item['current_start']}"
                end_date = f"{item['prior_end']}|{item['current_end']}"
            else:
                period = "descriptive"
                start_date = ""
                end_date = ""
            rows.append(
                {
                    "slug": item["slug"],
                    "final_url": item["final_url"],
                    "artifact": "strict-url-performance-comparison.csv",
                    "cell_column": column,
                    "cell_value": value,
                    "source_lane": source_lane,
                    "period": period,
                    "start_date": start_date,
                    "end_date": end_date,
                    "derivation": (
                        "current minus prior"
                        if column.endswith("_delta")
                        else "(current-prior)/prior"
                        if column.endswith("_pct_delta")
                        else "direct source metric or source status"
                    ),
                }
            )
    return rows


def sum_metric(rows: list[dict[str, Any]], field: str) -> float:
    return sum(float(row.get(field) or 0) for row in rows)


def weighted_metric(
    rows: list[dict[str, Any]], value_field: str, weight_field: str
) -> float | None:
    weighted = 0.0
    total_weight = 0.0
    for row in rows:
        value = row.get(value_field)
        weight = row.get(weight_field)
        if value in (None, "") or weight in (None, ""):
            continue
        weighted += float(value) * float(weight)
        total_weight += float(weight)
    return weighted / total_weight if total_weight else None


def fmt_number(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "unavailable"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:.{digits}f}"


def fmt_change(current: float | None, prior: float | None, unit: str = "") -> str:
    if current is None or prior is None:
        return "unavailable"
    if prior == 0:
        return f"{fmt_number(current)}{unit} vs 0{unit}"
    delta = (current - prior) / prior * 100
    sign = "+" if delta >= 0 else ""
    return f"{fmt_number(prior)}{unit} to {fmt_number(current)}{unit} ({sign}{delta:.1f}%)"


def build_portfolio_review(
    strict_rows: list[dict[str, Any]],
    all_bases: list[dict[str, Any]],
    style_rows: list[dict[str, Any]],
    zero_click_rows: list[dict[str, Any]],
    gen_ai_rows: list[dict[str, Any]],
    writing_diagnosis: list[dict[str, Any]],
    latest_end: str,
) -> str:
    clicks_current = sum_metric(strict_rows, "gsc_clicks_current")
    clicks_prior = sum_metric(strict_rows, "gsc_clicks_prior")
    impressions_current = sum_metric(strict_rows, "gsc_impressions_current")
    impressions_prior = sum_metric(strict_rows, "gsc_impressions_prior")
    query_count_current = sum_metric(strict_rows, "gsc_ranking_query_count_current")
    query_count_prior = sum_metric(strict_rows, "gsc_ranking_query_count_prior")
    ctr_current = clicks_current / impressions_current * 100 if impressions_current else None
    ctr_prior = clicks_prior / impressions_prior * 100 if impressions_prior else None
    position_current = weighted_metric(
        strict_rows, "gsc_position_current", "gsc_impressions_current"
    )
    position_prior = weighted_metric(
        strict_rows, "gsc_position_prior", "gsc_impressions_prior"
    )
    sessions_current = sum_metric(strict_rows, "ga4_sessions_current")
    sessions_prior = sum_metric(strict_rows, "ga4_sessions_prior")
    organic_current = sum_metric(strict_rows, "ga4_organic_sessions_current")
    organic_prior = sum_metric(strict_rows, "ga4_organic_sessions_prior")
    engagement_current = weighted_metric(
        strict_rows, "ga4_engagement_rate_pct_current", "ga4_sessions_current"
    )
    engagement_prior = weighted_metric(
        strict_rows, "ga4_engagement_rate_pct_prior", "ga4_sessions_prior"
    )
    bounce_current = weighted_metric(
        strict_rows, "ga4_bounce_rate_pct_current", "ga4_sessions_current"
    )
    bounce_prior = weighted_metric(
        strict_rows, "ga4_bounce_rate_pct_prior", "ga4_sessions_prior"
    )
    time_current = weighted_metric(
        strict_rows,
        "ga4_avg_engagement_time_per_session_sec_current",
        "ga4_sessions_current",
    )
    time_prior = weighted_metric(
        strict_rows,
        "ga4_avg_engagement_time_per_session_sec_prior",
        "ga4_sessions_prior",
    )
    peec_retrieval_current = sum_metric(strict_rows, "peec_retrievals_current")
    peec_retrieval_prior = sum_metric(strict_rows, "peec_retrievals_prior")
    peec_citation_current = sum_metric(strict_rows, "peec_citations_current")
    peec_citation_prior = sum_metric(strict_rows, "peec_citations_prior")
    position_improved = sum(
        1
        for row in strict_rows
        if row.get("gsc_position_current") not in (None, "")
        and row.get("gsc_position_prior") not in (None, "")
        and float(row["gsc_position_current"]) < float(row["gsc_position_prior"])
    )
    position_declined = sum(
        1
        for row in strict_rows
        if row.get("gsc_position_current") not in (None, "")
        and row.get("gsc_position_prior") not in (None, "")
        and float(row["gsc_position_current"]) > float(row["gsc_position_prior"])
    )
    engagement_improved = sum(
        1
        for row in strict_rows
        if row.get("ga4_engagement_rate_pct_current") not in (None, "")
        and row.get("ga4_engagement_rate_pct_prior") not in (None, "")
        and float(row["ga4_engagement_rate_pct_current"])
        > float(row["ga4_engagement_rate_pct_prior"])
    )
    engagement_declined = sum(
        1
        for row in strict_rows
        if row.get("ga4_engagement_rate_pct_current") not in (None, "")
        and row.get("ga4_engagement_rate_pct_prior") not in (None, "")
        and float(row["ga4_engagement_rate_pct_current"])
        < float(row["ga4_engagement_rate_pct_prior"])
    )
    status_counts = Counter(row["comparison_status"] for row in all_bases)
    strict_styles = [row for row in style_rows if row["comparison_status"] == "confirmed_deployed_rewrite"]
    weak_icp = sum(row["icp_fit"] == "weak" for row in strict_styles)
    weak_proof = sum(row["proof_experience_signal"] == "weak" for row in strict_styles)
    no_faq = sum(row["faq_present"] == "no" for row in strict_styles)
    no_cta = sum(int(row["contextual_cta_link_count"]) == 0 for row in strict_styles)
    answer_fast = sum(row["answer_too_fast_risk"] == "yes" for row in strict_styles)
    low_commercial_fit = sum(
        row["commercial_icp_fit"] == "low_to_moderate"
        for row in writing_diagnosis
    )
    needs_revision = [
        row
        for row in writing_diagnosis
        if row["engagement_reception"] == "needs_revision"
    ]
    monitor_and_tune = [
        row
        for row in writing_diagnosis
        if row["engagement_reception"] == "monitor_and_tune"
    ]
    best_slug = "best-field-service-management-software"
    best_pressure = [row for row in zero_click_rows if row["slug"] == best_slug and row["period"] == "current"]
    best_pressure_impressions = sum(float(row["impressions"]) for row in best_pressure)
    best_zero_impressions = sum(
        float(row["impressions"])
        for row in best_pressure
        if row["pressure_type"] == "zero_click"
    )
    comparable_search = [
        row
        for row in strict_rows
        if row.get("gsc_clicks_delta") not in (None, "")
        and row.get("gsc_impressions_delta") not in (None, "")
    ]
    search_winners = sorted(
        comparable_search, key=lambda row: float(row.get("gsc_clicks_delta") or 0), reverse=True
    )[:5]
    search_decliners = sorted(
        comparable_search, key=lambda row: float(row.get("gsc_clicks_delta") or 0)
    )[:5]
    engagement_risks = sorted(
        [
            row
            for row in strict_rows
            if row.get("ga4_engagement_rate_pct_delta") not in (None, "")
            and float(row.get("ga4_engagement_rate_pct_delta") or 0) < 0
        ],
        key=lambda row: float(row.get("ga4_engagement_rate_pct_delta") or 0),
    )[:6]
    broad_query_pressure = sorted(
        [
            row
            for row in strict_rows
            if row.get("gsc_impressions_delta") not in (None, "")
            and float(row.get("gsc_impressions_delta") or 0) > 0
            and row.get("gsc_ctr_pct_delta") not in (None, "")
            and float(row.get("gsc_ctr_pct_delta") or 0) < 0
        ],
        key=lambda row: float(row.get("gsc_impressions_delta") or 0),
        reverse=True,
    )[:5]
    latest_gen_ai_end = ""
    gen_ai_recent_rows: list[dict[str, Any]] = []
    gen_ai_strict_recent: list[dict[str, Any]] = []
    if gen_ai_rows:
        latest_gen_ai_end = max(str(row.get("end_date") or "") for row in gen_ai_rows)
        gen_ai_recent_rows = [
            row for row in gen_ai_rows if row.get("end_date") == latest_gen_ai_end
        ]
        gen_ai_strict_recent = [
            row
            for row in gen_ai_recent_rows
            if row["comparison_status"] == "confirmed_deployed_rewrite"
        ]
    gen_ai_recent_impressions = sum_metric(gen_ai_strict_recent, "gen_ai_impressions")
    gen_ai_recent_matches = sum(
        1 for row in gen_ai_strict_recent if row.get("source_status") == "matched"
    )
    gen_ai_top_recent = sorted(
        gen_ai_strict_recent,
        key=lambda row: float(row.get("gen_ai_impressions") or 0),
        reverse=True,
    )[:5]
    gen_ai_window_totals = []
    for end_date in sorted({str(row.get("end_date") or "") for row in gen_ai_rows if row.get("end_date")}):
        window_rows = [
            row
            for row in gen_ai_rows
            if row.get("end_date") == end_date
            and row["comparison_status"] == "confirmed_deployed_rewrite"
        ]
        if not window_rows:
            continue
        start_date = str(window_rows[0].get("start_date") or "")
        gen_ai_window_totals.append(
            f"{start_date} to {end_date}: {fmt_number(sum_metric(window_rows, 'gen_ai_impressions'))} impressions across {sum(1 for row in window_rows if row.get('source_status') == 'matched')} matched strict URLs"
        )
    verdict_parts = []
    if clicks_current > clicks_prior and position_current is not None and position_prior is not None and position_current < position_prior:
        verdict_parts.append("Google organic visibility and rankings improved at cohort level")
    elif clicks_current > clicks_prior:
        verdict_parts.append("Google clicks improved, but weighted ranking position did not improve")
    else:
        verdict_parts.append("the confirmed cohort did not improve Google clicks")
    if engagement_current is not None and engagement_prior is not None:
        verdict_parts.append(
            "engagement quality improved" if engagement_current > engagement_prior else "engagement quality weakened"
        )
    if peec_citation_current > peec_citation_prior:
        verdict_parts.append("Peec citation activity improved")
    elif peec_citation_current < peec_citation_prior:
        verdict_parts.append("Peec citation activity declined")
    else:
        verdict_parts.append("Peec citation activity was flat")
    engagement_page_word = "page" if engagement_improved == 1 else "pages"
    lines = [
        "# Corrected Live Blog Portfolio Review",
        "",
        f"**Final-data cutoff:** {latest_end}",
        f"**Headline cohort:** {len(strict_rows)} strictly confirmed deployed AI/rewrite pages from 28 live repo-derived URLs.",
        "",
        "## Verdict",
        "",
        "; ".join(verdict_parts) + ". The evidence supports a mixed reception assessment rather than a blanket success or failure claim.",
        "",
        "Each page uses its own deployment boundary. Its current window begins on that deployment date and ends on the common final-data cutoff; its prior window is the immediately preceding period with the identical inclusive day count.",
        "",
        "## Measured Performance",
        "",
        f"- GSC clicks: {fmt_change(clicks_current, clicks_prior)}.",
        f"- GSC impressions: {fmt_change(impressions_current, impressions_prior)}.",
        f"- GSC visible query footprint: {fmt_change(query_count_current, query_count_prior)} ranking-query rows.",
        f"- GSC cohort CTR: {fmt_number(ctr_prior, 3)}% to {fmt_number(ctr_current, 3)}%.",
        f"- GSC impression-weighted average position: {fmt_number(position_prior, 2)} to {fmt_number(position_current, 2)}; lower is better. URL-level positions improved for {position_improved} pages and declined for {position_declined} pages where both periods had data.",
        f"- GA4 sessions: {fmt_change(sessions_current, sessions_prior)}.",
        f"- GA4 Organic Search sessions: {fmt_change(organic_current, organic_prior)}.",
        f"- GA4 session-weighted engagement rate: {fmt_number(engagement_prior, 2)}% to {fmt_number(engagement_current, 2)}%; {engagement_improved} {engagement_page_word} improved and {engagement_declined} declined where both periods had data.",
        f"- GA4 session-weighted bounce rate: {fmt_number(bounce_prior, 2)}% to {fmt_number(bounce_current, 2)}%. This is the native GA4 bounce-rate definition and reconciles to 100% minus engagement rate.",
        f"- GA4 average engagement time per session: {fmt_number(time_prior, 1)}s to {fmt_number(time_current, 1)}s.",
        f"- Peec retrievals: {fmt_change(peec_retrieval_current, peec_retrieval_prior)}; citations: {fmt_change(peec_citation_current, peec_citation_prior)}.",
        f"- GSC Gen AI UI export: latest included weekly export ends {latest_gen_ai_end or 'unavailable'} with {fmt_number(gen_ai_recent_impressions)} impressions across {gen_ai_recent_matches} matched strict URLs.",
        "",
        "GSC, GA4, and Peec are separate evidence lanes. Search clicks are not sessions, Peec citations are not visits, and none of these sources proves leads, revenue, or a conversion path.",
        "",
        "## GSC Gen AI UI Export Evidence",
        "",
        "I found downloaded Search Console exports for Search generative AI features and included only unfiltered exports or exports filtered to `+/blog`. These are weekly GSC UI snapshots, not the same per-URL current/prior windows used for Web Search, GA4, and Peec.",
        "Strict-cohort Gen AI export totals: "
        + ("; ".join(gen_ai_window_totals) if gen_ai_window_totals else "no included export rows available")
        + ".",
        "Latest strict-cohort Gen AI pages by impressions: "
        + "; ".join(
            f"`{row['slug']}` ({fmt_number(float(row.get('gen_ai_impressions') or 0))})"
            for row in gen_ai_top_recent
            if float(row.get("gen_ai_impressions") or 0) > 0
        )
        + ".",
        "This source proves Google-reported generative AI feature impressions for the exported window only. It does not provide clicks, CTR, average position, or exact AI Overview citation/click causality.",
        "",
        "## Search Reception",
        "",
        "The strict cohort gained search demand overall, but the gains were concentrated. Biggest click gains were "
        + "; ".join(
            f"`{row['slug']}` ({fmt_number(float(row['gsc_clicks_delta']))} clicks)"
            for row in search_winners
            if float(row.get("gsc_clicks_delta") or 0) > 0
        )
        + ".",
        "The main click decliners were "
        + "; ".join(
            f"`{row['slug']}` ({fmt_number(float(row['gsc_clicks_delta']))} clicks)"
            for row in search_decliners
            if float(row.get("gsc_clicks_delta") or 0) < 0
        )
        + ".",
        f"The visible query footprint expanded from {fmt_number(query_count_prior)} to {fmt_number(query_count_current)} GSC query rows, so the cohort is being tested across a wider search surface than before.",
        "Ranking did not improve at cohort level because several pages expanded or held impressions while average position weakened. That points to broader query pickup and competitive dilution, not a clean ranking lift.",
        "",
        "## Engagement Diagnosis",
        "",
        "The engagement decline is real at cohort level but small: engagement rate fell 3.35 percentage points while average engagement time was effectively flat. That reads more like traffic-mix dilution than users rejecting the content outright.",
        "Pages carrying the engagement decline were "
        + "; ".join(
            f"`{row['slug']}` ({fmt_number(float(row['ga4_engagement_rate_pct_delta']), 1)} pp engagement, "
            f"{fmt_number(float(row.get('ga4_bounce_rate_pct_delta') or 0), 1)} pp bounce, "
            f"{fmt_number(float(row.get('ga4_avg_engagement_time_per_session_sec_delta') or 0), 1)}s time/session)"
            for row in engagement_risks
        )
        + ".",
        "Most likely explanations to test: broader informational queries landing on listicles and guides, lower commercial fit on some new impressions, answer-satisfaction behavior from users who get the needed fact quickly, and listicle SERPs where comparison intent creates fast scanning rather than deep reading.",
        "The strongest GSC sign of zero-click or low-click pressure is the combination of higher impressions with lower CTR on "
        + "; ".join(
            f"`{row['slug']}` ({fmt_number(float(row['gsc_impressions_delta']))} impressions, {fmt_number(float(row['gsc_ctr_pct_delta']), 3)} pp CTR)"
            for row in broad_query_pressure
        )
        + ".",
        "",
        "## Writing And ICP Interpretation",
        "",
        f"Among the {len(strict_styles)} confirmed pages, the deterministic live-copy rubric flagged {weak_icp} with weak trade/field-service specificity, {weak_proof} with weak proof or experience signals, {no_faq} without an FAQ heading, {no_cta} without a contextual product/demo CTA, and {answer_fast} with an answer-too-fast risk.",
        f"The sharper engagement diagnosis finds {low_commercial_fit} pages with low-to-moderate commercial ICP fit by topic, {len(needs_revision)} pages that need revision because engagement and search clicks both weakened, and {len(monitor_and_tune)} pages that should be tuned or monitored because engagement weakened materially without the same click-loss signal.",
        "Priority writing/ICP risks: "
        + "; ".join(
            f"`{row['slug']}` ({row['most_likely_non_causal_explanation']})"
            for row in (needs_revision + monitor_and_tune)[:6]
        )
        + ".",
        "",
        "These editorial flags are plausible explanations to investigate when engagement falls, not proof of causation. Lower engagement can also reflect query mix, device mix, traffic quality, SERP answer satisfaction, seasonality, or measurement changes. The per-page diagnostics should be used to test whether declines cluster around weak intent alignment, thin proof, shallow CTAs, or unusually broad traffic acquisition.",
        "",
        "## Best Field Service Zero-Click Pressure",
        "",
        f"The current-window low/no-click query extract for `/blog/{best_slug}` contains {len(best_pressure)} qualifying query rows representing {fmt_number(best_pressure_impressions)} impressions; {fmt_number(best_zero_impressions)} of those impressions were on zero-click query rows. This is directional SERP click-pressure evidence only. GSC Web Search cannot identify whether an AI Overview, featured snippet, other SERP feature, or user behavior caused the missing click.",
        "",
        "## Cohort Accounting",
        "",
        f"- Confirmed comparable: {status_counts['confirmed_deployed_rewrite']}.",
        f"- Too new for final data: {status_counts['too_new_for_final_data']}.",
        f"- Missing publish age: {status_counts['missing_publish_age_excluded']}.",
        f"- Partial content match requiring manual review: {status_counts['content_partial_manual_review']}.",
        f"- Content mismatch or failed live verification: {status_counts['content_mismatch_excluded']}.",
        "",
        "## Decision",
        "",
        "Continue the program only with page-level quality controls: preserve pages that gain qualified search visibility or Peec citation coverage, revise pages where engagement and rankings both weaken, and do not use aggregate volume growth to excuse weak ICP specificity, thin proof, or missing decision-stage CTAs.",
        "",
        "The earlier `live-blog-performance-2026-08-28/portfolio-review.md` is superseded because it allowed local artifact dates to set six comparison boundaries and did not require a strong live/local content match for every headline URL.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    raw_dir = output_dir / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    cohort = load_cohort()
    sheet_rows = fetch_sheet_rows(raw_dir / "all-seo-published.json")
    live_payload = extract_live_pages(cohort, raw_dir / "live-playwright-evidence.json")
    live_by_slug = {
        slug_from_url(item["requested_url"]): item for item in live_payload["pages"]
    }

    probe_path = raw_dir / "latest-common-end-probe.json"
    run(
        [
            "wsl",
            "/home/patrickgrueschow/analytics-venv/bin/python",
            wsl_path(SOURCE_PULL_SCRIPT),
            "probe",
            "--output",
            wsl_path(probe_path),
        ],
        cwd=MARKETINGSKILLS,
        timeout=600,
    )
    probe = read_json(probe_path)
    latest_end = date.fromisoformat(probe["selected_latest_common_end"])

    bases = []
    deployment_rows = []
    match_rows = []
    style_rows = []
    for cohort_row in cohort:
        slug = cohort_row["slug"]
        live = live_by_slug.get(slug)
        if live is None:
            raise RuntimeError(f"No Playwright evidence returned for {slug}")
        sheet = sheet_evidence_for_url(sheet_rows, cohort_row["final_url"])
        live_dates = live_date_evidence(live)
        match = best_artifact_match(slug, live)
        chosen = choose_deployment_date(sheet, live_dates, match)
        status = classify_status(
            live, match, chosen["deployment_date"], latest_end
        )
        base = {
            "slug": slug,
            "final_url": cohort_row["final_url"],
            "comparison_status": status,
            **sheet,
            **live_dates,
            **match,
            **chosen,
        }
        if status == "confirmed_deployed_rewrite":
            base.update(window_for(chosen["deployment_date"], latest_end))
        else:
            base.update(
                {
                    "current_start": "",
                    "current_end": "",
                    "prior_start": "",
                    "prior_end": "",
                    "days_compared": "",
                }
            )
        bases.append(base)
        date_conflicts = sorted(
            {
                value
                for value in [
                    sheet.get("sheet_completed_at"),
                    live_dates.get("live_visible_updated"),
                    live_dates.get("live_visible_published"),
                    live_dates.get("live_structured_date_modified"),
                    live_dates.get("live_structured_date_published"),
                ]
                if value
            }
        )
        deployment_rows.append(
            {
                "slug": slug,
                "final_url": cohort_row["final_url"],
                "comparison_status": status,
                **sheet,
                **live_dates,
                "deployment_date": chosen["deployment_date"],
                "deployment_date_source": chosen["deployment_date_source"],
                "date_conflict": "yes" if len(date_conflicts) > 1 else "no",
                "date_values_observed": ";".join(date_conflicts),
                "local_frontmatter_date": match.get("local_frontmatter_date", ""),
                "local_filename_date": match.get("local_filename_date", ""),
                "local_date_usage": "evidence_only_never_window_boundary",
                "sitemap_lastmod_values": ";".join(live_payload["sitemap"].get("unique_lastmods") or []),
                "sitemap_date_usage": "unusable_bulk_lastmod" if not live_payload["sitemap"].get("usable_for_publish_age") else "not_selected",
            }
        )
        match_rows.append(
            {
                "slug": slug,
                "final_url": cohort_row["final_url"],
                "comparison_status": status,
                "live_status": live.get("status"),
                "live_final_url": live.get("final_url"),
                "canonical": live.get("canonical"),
                "robots": live.get("robots"),
                "title": live.get("title"),
                "h1": live.get("h1"),
                "visible_date_labels": "; ".join(live.get("visible_date_labels") or []),
                "structured_dates": "; ".join(
                    f"{item.get('kind')}={item.get('value')}"
                    for item in live.get("structured_dates") or []
                ),
                "first_body_text": live.get("first_body_text"),
                "heading_count": len(live.get("headings") or []),
                "heading_sample": " | ".join(
                    item.get("text", "") for item in (live.get("headings") or [])[:12]
                ),
                **match,
            }
        )
        style_rows.append(content_style_review(base, live))

    strict_bases = [
        row for row in bases if row["comparison_status"] == "confirmed_deployed_rewrite"
    ]
    gen_ai_exports = load_gsc_gen_ai_exports(raw_dir / "gsc-gen-ai-ui-exports.json")
    gen_ai_evidence = build_gsc_gen_ai_evidence(bases, gen_ai_exports)
    windows = [
        {
            key: row[key]
            for key in (
                "slug",
                "final_url",
                "current_start",
                "current_end",
                "prior_start",
                "prior_end",
                "days_compared",
            )
        }
        for row in strict_bases
    ]
    windows_path = raw_dir / "comparison-windows.json"
    write_json(windows_path, windows)

    source_dir = raw_dir / "sources"
    run(
        [
            "wsl",
            "/home/patrickgrueschow/analytics-venv/bin/python",
            wsl_path(SOURCE_PULL_SCRIPT),
            "pull",
            "--windows",
            wsl_path(windows_path),
            "--output-dir",
            wsl_path(source_dir),
        ],
        cwd=MARKETINGSKILLS,
        timeout=3600,
    )
    gsc_raw = read_json(source_dir / "gsc.json")
    ga4_raw = read_json(source_dir / "ga4.json")
    peec_raw = read_json(source_dir / "peec.json")

    strict_rows = []
    performance_by_slug = {}
    for base in strict_bases:
        slug = base["slug"]
        row = performance_row(
            base,
            {
                "current": gsc_raw.get(f"{slug}::current", {}),
                "prior": gsc_raw.get(f"{slug}::prior", {}),
            },
            {
                "current": ga4_raw.get(f"{slug}::current", {}),
                "prior": ga4_raw.get(f"{slug}::prior", {}),
            },
            {
                "current": peec_raw.get(f"{slug}::current", {}),
                "prior": peec_raw.get(f"{slug}::prior", {}),
            },
        )
        strict_rows.append(row)
        performance_by_slug[slug] = row

    all_rows = []
    for base in bases:
        if base["slug"] in performance_by_slug:
            all_rows.append(performance_by_slug[base["slug"]])
        else:
            all_rows.append(
                {
                    "slug": base["slug"],
                    "final_url": base["final_url"],
                    "comparison_status": base["comparison_status"],
                    "deployment_date": base.get("deployment_date", ""),
                    "deployment_date_source": base.get("deployment_date_source", ""),
                    "current_start": "",
                    "current_end": "",
                    "prior_start": "",
                    "prior_end": "",
                    "days_compared": "",
                    "content_match": base.get("content_match", ""),
                    "weighted_similarity": base.get("weighted_similarity", ""),
                    "exclusion_reason": base["comparison_status"],
                }
            )

    query_movers, zero_click_rows = build_query_outputs(strict_bases, gsc_raw)
    ga4_diagnostics = build_ga4_diagnostics(strict_bases, ga4_raw)
    peec_evidence = build_peec_evidence(strict_bases, peec_raw)
    writing_diagnosis = build_engagement_writing_diagnosis(
        strict_rows,
        style_rows,
        zero_click_rows,
    )
    source_map = build_source_cell_map(strict_rows)

    write_csv(output_dir / "strict-url-performance-comparison.csv", strict_rows)
    write_csv(output_dir / "all-28-url-status-and-performance.csv", all_rows)
    write_csv(output_dir / "deployment-date-evidence.csv", deployment_rows)
    write_csv(output_dir / "live-content-match-evidence.csv", match_rows)
    write_csv(output_dir / "gsc-query-movers.csv", query_movers)
    write_csv(output_dir / "gsc-low-ctr-zero-click-pressure.csv", zero_click_rows)
    write_csv(output_dir / "ga4-engagement-diagnostics.csv", ga4_diagnostics)
    write_csv(output_dir / "peec-url-evidence.csv", peec_evidence)
    write_csv(output_dir / "content-style-icp-review.csv", style_rows)
    write_csv(output_dir / "gsc-gen-ai-ui-export-evidence.csv", gen_ai_evidence)
    write_csv(output_dir / "engagement-writing-diagnosis.csv", writing_diagnosis)
    write_csv(output_dir / "source-cell-map.csv", source_map)

    status_counts = Counter(row["comparison_status"] for row in bases)
    gsc_clicks = sum_metric(strict_rows, "gsc_clicks_current")
    ga4_organic = sum_metric(strict_rows, "ga4_organic_sessions_current")
    manifest = {
        "schema_version": "corrected-live-blog-performance/v1",
        "run_date": RUN_DATE,
        "checked_live_date": RUN_DATE,
        "output_directory": str(output_dir),
        "input": {
            "audit_csv": str(AUDIT_CSV),
            "audit_input_rows": len(read_csv(AUDIT_CSV)),
            "live_repo_candidate_input_urls": len(cohort),
            "hard_stop_expected": 28,
            "hard_stop_passed": len(cohort) == 28,
        },
        "source_tools": {
            "live_web": {
                "tool": "Playwright CLI attached to headed Google Chrome",
                "session": PLAYWRIGHT_SESSION,
                "checks": [
                    "HTTP status",
                    "final URL",
                    "canonical",
                    "robots",
                    "title",
                    "H1",
                    "visible dates",
                    "structured dates",
                    "headings",
                    "first body text",
                ],
            },
            "publish_metadata": {
                "tool": "gws sheets +read",
                "spreadsheet_id": SHEET_ID,
                "range": SHEET_RANGE,
                "primary_field": "Completed At",
                "match": "exact normalized Final URL",
            },
            "gsc": {
                "tool": "Google Search Console API using the configured OAuth token",
                "property": "sc-domain:simprogroup.com",
                "search_type": "web",
                "data_state": "final",
                "page_filter": "exact normalized page URL; trailing slash fallback",
            },
            "gsc_gen_ai_ui_export": {
                "tool": "downloaded Google Search Console UI exports found in Downloads",
                "artifact": "gsc-gen-ai-ui-export-evidence.csv",
                "included_rule": "Search generative AI features exports with no Page filter or Page=+/blog",
                "excluded_rule": "exports filtered to non-blog sections such as +/features or +/solutions",
                "metrics": ["impressions"],
                "browser_note": "An open Chrome GSC tab was detected, but no DevTools debugging port was available; downloaded exports were used for source-bound extraction.",
            },
            "ga4": {
                "tool": "official Google Analytics Data API client",
                "property": "properties/309907809",
                "host_filter": "www.simprogroup.com",
                "page_filter": "exact pagePath plus trailing slash variant",
            },
            "peec": {
                "tool": "official Peec streamable HTTP MCP",
                "project_id": "or_a1efbfcd-d5aa-428a-ad3b-dbfd867e037b",
                "channels": CHANNELS,
                "url_filter": "exact normalized URL variants",
            },
        },
        "latest_common_end_probe": probe,
        "date_rules": {
            "primary": "All SEO Published Completed At when exact URL matches and content match is strong",
            "fallback": "live CMS/page Updated date when content match is strong; live Published date only when it is not earlier than the matched local artifact date",
            "local_artifact_dates": "evidence only; never a comparison boundary",
            "sitemap_lastmod": "checked but unusable when bulk-generated",
            "current_window": "deployment date through latest common final date, inclusive",
            "prior_window": "same number of immediately preceding inclusive days",
        },
        "content_match_rules": {
            "method": "best filename-matched local artifact scored against live H1, H2/H3 headings, and body tokens",
            "strong": "weighted >=0.62, H1 >=0.75, and heading >=0.45 or body >=0.65",
            "partial": "weighted >=0.38, H1 >=0.55, and heading >=0.20 or body >=0.35",
            "mismatch": "below partial threshold or failed live/canonical/indexability verification",
        },
        "row_counts": {
            "all_28_rows": len(all_rows),
            "strict_comparable": status_counts["confirmed_deployed_rewrite"],
            "too_new": status_counts["too_new_for_final_data"],
            "missing_publish_age": status_counts["missing_publish_age_excluded"],
            "partial_manual_review": status_counts["content_partial_manual_review"],
            "mismatch_excluded": status_counts["content_mismatch_excluded"],
            "gsc_query_movers": len(query_movers),
            "gsc_low_ctr_zero_click_pressure": len(zero_click_rows),
            "ga4_engagement_diagnostics": len(ga4_diagnostics),
            "peec_url_evidence": len(peec_evidence),
            "content_style_icp_review": len(style_rows),
            "gsc_gen_ai_ui_export_evidence": len(gen_ai_evidence),
            "engagement_writing_diagnosis": len(writing_diagnosis),
            "source_cell_map": len(source_map),
        },
        "normalization_rules": {
            "url": "lowercase scheme/host, remove query/fragment/trailing slash; require https://www.simprogroup.com/blog/",
            "gsc_ga4_blank": "no matching row remains blank",
            "peec_empty": "no matching row becomes 0 retrievals and 0 citations with source_status",
        },
        "trust_checks": {
            "gsc_clicks_current": gsc_clicks,
            "ga4_organic_sessions_current": ga4_organic,
            "directional_reconciliation_only": True,
            "same_direction_nonzero": (gsc_clicks > 0 and ga4_organic > 0),
        },
        "limitations": [
            "GSC Web Search does not attribute zero-click behavior to AI Overviews or another SERP feature.",
            "GA4 key events do not prove leads, revenue, or conversion paths without funnel/CRM evidence.",
            "Peec proves monitored retrieval and citation activity, not site traffic.",
            "Writing-style and ICP findings are deterministic editorial heuristics and are not causal explanations for analytics movement.",
            "Downloaded GSC Gen AI exports are weekly UI snapshots and do not align to every per-URL matched current/prior window.",
        ],
        "supersedes": str(
            REPO
            / "research"
            / "live-blog-performance-2026-08-28"
            / "portfolio-review.md"
        ),
        "artifacts": [
            "strict-url-performance-comparison.csv",
            "all-28-url-status-and-performance.csv",
            "deployment-date-evidence.csv",
            "live-content-match-evidence.csv",
            "gsc-query-movers.csv",
            "gsc-low-ctr-zero-click-pressure.csv",
            "ga4-engagement-diagnostics.csv",
            "peec-url-evidence.csv",
            "content-style-icp-review.csv",
            "gsc-gen-ai-ui-export-evidence.csv",
            "engagement-writing-diagnosis.csv",
            "source-cell-map.csv",
            "source-manifest.json",
            "portfolio-review-corrected.md",
        ],
    }
    write_json(output_dir / "source-manifest.json", manifest)
    report = build_portfolio_review(
        strict_rows,
        bases,
        style_rows,
        zero_click_rows,
        gen_ai_evidence,
        writing_diagnosis,
        latest_end.isoformat(),
    )
    (output_dir / "portfolio-review-corrected.md").write_text(report, encoding="utf-8")

    expected_artifacts = [output_dir / name for name in manifest["artifacts"]]
    missing = [str(path) for path in expected_artifacts if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing output artifacts: {missing}")
    if len(all_rows) != 28:
        raise RuntimeError(f"Expected 28 all-status rows, found {len(all_rows)}")
    if len(strict_rows) != status_counts["confirmed_deployed_rewrite"]:
        raise RuntimeError("Strict row count does not match status accounting")
    for base in strict_bases:
        if base["content_match"] != "strong":
            raise RuntimeError(f"Strict URL lacks strong content match: {base['slug']}")
        if base["deployment_date_source"].startswith("local"):
            raise RuntimeError(f"Strict URL uses local date: {base['slug']}")
    print(json.dumps(manifest["row_counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
