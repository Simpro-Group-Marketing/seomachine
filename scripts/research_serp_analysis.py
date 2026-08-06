#!/usr/bin/env python3
"""
Research SERP Analysis

Evidence-bound analysis to understand what Google wants for a specific keyword
from verified visible SERP context.
DataForSEO is the primary source. When DataForSEO is unavailable, the script
falls back to a Playwright CLI capture of browser-visible Google SERP facts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv


load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data_sources"))

from modules.content_length_comparator import ContentLengthComparator  # noqa: E402
from modules.dataforseo import DataForSEO  # noqa: E402
from modules.search_intent_analyzer import SearchIntentAnalyzer  # noqa: E402


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("word target must be a positive integer")
    return parsed


def parse_cli_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report SERP patterns and observed competitor length context."
    )
    parser.add_argument("keyword", nargs="?", help="Keyword phrase to research")
    parser.add_argument(
        "--word-target",
        type=_positive_int,
        default=None,
        help="Optional caller-supplied intent/evidence-complete article target",
    )
    return parser.parse_args(argv)


def main() -> None:
    """CLI entry point."""
    args = parse_cli_args()
    if not args.keyword:
        print('Usage: python scripts/research_serp_analysis.py "keyword phrase"')
        print(
            '\nExample: python scripts/research_serp_analysis.py '
            '"your target keyword" --word-target 1600'
        )
        return
    run_serp_analysis(args.keyword, word_target=args.word_target)


def run_serp_analysis(
    keyword: str,
    output_dir: str | Path = "research",
    now: Optional[datetime] = None,
    dataforseo_factory: Callable[[], Any] = DataForSEO,
    fallback_runner: Optional[Callable[..., Dict[str, Any]]] = None,
    intent_analyzer_factory: Callable[[], Any] = SearchIntentAnalyzer,
    content_comparator_factory: Callable[[], Any] = ContentLengthComparator,
    print_fn: Callable[[str], None] = print,
    word_target: Optional[int] = None,
) -> Dict[str, Any]:
    """Run SERP analysis with DataForSEO first and Playwright fallback second."""
    if not isinstance(keyword, str) or not keyword.strip():
        raise ValueError("keyword must be a non-empty string")
    keyword = keyword.strip()
    if (
        word_target is not None
        and (
            not isinstance(word_target, int)
            or isinstance(word_target, bool)
            or word_target <= 0
        )
    ):
        raise ValueError("word_target must be a positive integer or None")

    now = now or datetime.now()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fallback_runner = fallback_runner or run_playwright_serp_fallback

    print_fn("=" * 80)
    print_fn(f"SERP ANALYSIS: {keyword}")
    print_fn("=" * 80)
    print_fn(f"Date: {now.strftime('%Y-%m-%d %H:%M')}")
    print_fn(
        "Strategy: Use verified SERP observations as strong defaults, with "
        "documented Reader Contract exceptions"
    )
    print_fn("=" * 80)

    print_fn("\n1. Initializing analysis tools...")
    dataforseo_error = ""
    dfs = None
    try:
        dfs = dataforseo_factory()
        print_fn("   DataForSEO connected")
    except Exception as exc:
        dataforseo_error = str(exc)
        print_fn(f"   DataForSEO Error: {dataforseo_error}")

    intent_analyzer = intent_analyzer_factory()
    content_comparator = content_comparator_factory()
    print_fn("   Analysis modules loaded")

    serp_data: Dict[str, Any] = {}
    fallback_data: Dict[str, Any] = {}

    if dfs is not None:
        print_fn(f"\n2. Fetching SERP data for '{keyword}'...")
        try:
            serp_data = normalize_serp_payload(
                dfs.get_serp_data(keyword, limit=20),
                source="DataForSEO",
            )
            if not serp_data or "organic_results" not in serp_data:
                dataforseo_error = "No SERP data available from DataForSEO"
                print_fn(f"   {dataforseo_error}")
                serp_data = {}
            else:
                print_fn(f"   Retrieved top {len(serp_data['organic_results'][:10])} organic results")
        except Exception as exc:
            dataforseo_error = str(exc)
            print_fn(f"   Error fetching SERP data: {dataforseo_error}")
            serp_data = {}

    if not serp_data:
        print_fn("\n2b. Attempting Playwright SERP fallback...")
        fallback_data = fallback_runner(keyword, output_dir=output_dir, now=now)
        if fallback_data.get("fallback_blocker"):
            print_fn(f"   Playwright fallback blocker: {fallback_data['fallback_blocker']}")
        else:
            print_fn(
                "   Playwright fallback captured "
                f"{len(fallback_data.get('organic_results', []))} organic results"
            )
        serp_data = {
            "organic_results": fallback_data.get("organic_results", []),
            "features": fallback_data.get("features", []),
        }

    organic_results = serp_data.get("organic_results", [])[:10]
    print_fn("\n3. Analyzing SERP patterns...")

    analysis: Dict[str, Any] = {
        "keyword": keyword,
        "word_target": word_target,
        "analyzed_date": now.strftime("%Y-%m-%d"),
        "top_results": organic_results,
        "serp_features": serp_data.get("features", []),
        "paa_questions": fallback_data.get("paa_questions", []),
        "dataforseo_error": dataforseo_error,
        "fallback_used": bool(fallback_data.get("fallback_used", False)),
        "fallback_blocker": fallback_data.get("fallback_blocker"),
        "fallback_search_url": fallback_data.get("search_url", ""),
        "fallback_raw_artifact": fallback_data.get("raw_artifact", ""),
        "fallback_captured_at": fallback_data.get("captured_at", now.isoformat()),
        "content_types": [],
        "title_patterns": [],
        "word_counts": [],
        "word_count_by_position": {},
        "competitor_lengths": [],
        "domains": [],
        "domain_authority": [],
        "freshness_signals": [],
        "common_h2_topics": [],
        "heading_observations": [],
        "competitive_difficulty": "unknown",
    }

    for index, result in enumerate(organic_results, 1):
        title = result.get("title", "")
        url = result.get("url", "")
        domain = extract_domain(url)

        analysis["domains"].append(domain)
        analysis["title_patterns"].append(title)

        content_type = detect_content_type(title)
        analysis["content_types"].append(content_type)

        if has_freshness_signal(title, now=now):
            analysis["freshness_signals"].append(index)

        try:
            fetch_context = getattr(content_comparator, "fetch_content_context", None)
            if callable(fetch_context):
                page_context = fetch_context(url)
                if not isinstance(page_context, dict):
                    page_context = {}
                word_count = page_context.get("word_count")
                headings = page_context.get("h2_headings") or []
                if isinstance(headings, list):
                    verified_headings = [
                        heading.strip()
                        for heading in headings
                        if isinstance(heading, str) and heading.strip()
                    ]
                    if verified_headings:
                        analysis["heading_observations"].append(
                            {
                                "position": index,
                                "url": url,
                                "headings": verified_headings,
                            }
                        )
            else:
                word_count = content_comparator.fetch_word_count(url)
            if word_count and word_count > 100:
                analysis["word_counts"].append(word_count)
                analysis["word_count_by_position"][index] = word_count
                analysis["competitor_lengths"].append(
                    {
                        "position": index,
                        "title": title,
                        "url": url,
                        "domain": domain,
                        "word_count": word_count,
                    }
                )
                print_fn(f"   [{index}] {domain} - {word_count:,} words - {content_type}")
            else:
                print_fn(f"   [{index}] {domain} - Word count unavailable - {content_type}")
        except Exception:
            print_fn(f"   [{index}] {domain} - Word count unavailable - {content_type}")

    analysis["common_h2_topics"] = identify_recurring_h2_topics(
        analysis["heading_observations"]
    )

    calculate_content_requirements(analysis, organic_results, print_fn)
    analyze_search_intent(keyword, analysis, organic_results, intent_analyzer, print_fn)

    print_fn("\n6. Assessing competitive difficulty...")
    analysis["competitive_difficulty"] = assess_difficulty(analysis["domains"])
    print_fn(f"   Competitive Difficulty: {analysis['competitive_difficulty'].upper()}")

    print_fn("\n7. Generating content brief...")
    analysis["content_brief"] = generate_content_brief(keyword, analysis, now=now)

    report_path = output_dir / f"serp-analysis-{sanitize_filename(keyword)}.md"
    print_fn(f"\n8. Writing report to {report_path}...")
    write_markdown_report(keyword, analysis, output_dir=output_dir, now=now)

    print_fn("\n" + "=" * 80)
    print_fn("SERP ANALYSIS COMPLETE")
    print_fn("=" * 80)
    print_fn("\nNext steps:")
    if organic_results:
        print_fn(f"1. Review detailed report: {report_path}")
        print_fn("2. Use verified visible observations to understand what Google wants")
        print_fn("3. Resolve or apply the caller-supplied Reader Contract word target")
        print_fn(
            "4. Match the dominant content type by default; document a Reader "
            "Contract exception when another format is justified"
        )
        print_fn(
            "5. Target the SERP features present when applicable to intent, format, "
            "reader value, and verified inputs"
        )
    else:
        print_fn(f"1. Review blocker details in: {report_path}")
        print_fn("2. Provide a SERP/PAA export or rerun after Google automation access is available")
        print_fn("3. Use verified Asana brief, GSC, live page evidence, and public sources only")
        print_fn("4. Do not use competitor rankings, PAA questions, or difficulty claims from this blocked run")

    return analysis


def calculate_content_requirements(
    analysis: Dict[str, Any],
    organic_results: List[Dict[str, Any]],
    print_fn: Callable[[str], None],
) -> None:
    """Calculate content type, word count, freshness, and SERP feature summaries."""
    print_fn("\n4. Summarizing observed SERP context...")

    if analysis["content_types"]:
        type_counts = Counter(
            content_type
            for content_type in analysis["content_types"]
            if content_type != "Unknown"
        )
        if not type_counts:
            analysis["dominant_content_type"] = "Unknown"
            analysis["content_type_distribution"] = {}
            print_fn("   Dominant Content Type: unresolved from title evidence")
            type_counts = None
        if type_counts:
            dominant_type = type_counts.most_common(1)[0][0]
            analysis["dominant_content_type"] = dominant_type
            analysis["content_type_distribution"] = dict(type_counts)
            print_fn(f"   Dominant Content Type: {dominant_type}")
            print_fn(f"   Distribution: {dict(type_counts)}")

    if analysis["word_counts"]:
        avg_words = statistics.mean(analysis["word_counts"])
        median_words = statistics.median(analysis["word_counts"])
        min_words = min(analysis["word_counts"])
        max_words = max(analysis["word_counts"])

        analysis["avg_word_count"] = int(avg_words)
        analysis["median_word_count"] = int(median_words)
        analysis["min_word_count"] = min_words
        analysis["max_word_count"] = max_words
        if analysis.get("word_target") is not None:
            analysis["difference_from_observed_average"] = (
                analysis["word_target"] - analysis["avg_word_count"]
            )
        print_fn(f"   Average Word Count: {avg_words:,.0f}")
        print_fn(f"   Median Word Count: {median_words:,.0f}")
        print_fn(f"   Range: {min_words:,} - {max_words:,}")
        print_fn("   Competitor word counts are context only")

    freshness_ratio = (
        len(analysis["freshness_signals"]) / len(organic_results)
        if organic_results
        else 0
    )
    analysis["freshness_important"] = freshness_ratio >= 0.6
    freshness_label = "Prevalent" if analysis["freshness_important"] else "Not prevalent"
    print_fn(
        f"   Observed Freshness Signals: {freshness_label} "
        f"({len(analysis['freshness_signals'])}/{len(organic_results)} result titles)"
    )

    print_fn("\n   SERP Features Present:")
    if analysis["serp_features"]:
        for feature in analysis["serp_features"]:
            print_fn(f"   - {feature}")
    else:
        print_fn("   - None detected")


def analyze_search_intent(
    keyword: str,
    analysis: Dict[str, Any],
    organic_results: List[Dict[str, Any]],
    intent_analyzer: Any,
    print_fn: Callable[[str], None],
) -> None:
    """Analyze search intent, with a blocked fallback when no SERP results exist."""
    print_fn("\n5. Analyzing search intent...")
    if organic_results:
        intent_result = intent_analyzer.analyze(
            keyword=keyword,
            serp_features=analysis["serp_features"],
            top_results=organic_results,
        )
    else:
        intent_result = {
            "primary_intent": "unknown",
            "confidence": 0,
            "recommendations": [
                "SERP analysis blocked; use a user-provided SERP/PAA export or verified non-SERP evidence."
            ],
        }

    primary_intent = intent_result.get("primary_intent", "unknown")
    if hasattr(primary_intent, "value"):
        primary_intent = primary_intent.value

    analysis["search_intent"] = str(primary_intent)

    confidence_data = intent_result.get("confidence", 0)
    if isinstance(confidence_data, dict):
        analysis["intent_confidence"] = confidence_data.get("overall", 0)
    else:
        analysis["intent_confidence"] = float(confidence_data) if confidence_data else 0

    analysis["intent_recommendations"] = intent_result.get("recommendations", [])

    print_fn(f"   Primary Intent: {analysis['search_intent']}")
    print_fn(f"   Confidence: {analysis['intent_confidence']:.0f}%")


def build_google_search_url(keyword: str) -> str:
    """Build the controlled Google SERP URL used by the Playwright fallback."""
    return f"https://www.google.com/search?q={quote_plus(keyword)}&num=10&hl=en&gl=us&pws=0"


def npx_available() -> bool:
    """Return True when npx is available for Playwright CLI execution."""
    return find_npx_executable() is not None


def find_npx_executable() -> Optional[str]:
    """Resolve the npx executable path for direct subprocess calls."""
    return shutil.which("npx") or shutil.which("npx.cmd") or shutil.which("npx.exe")


def normalize_serp_payload(
    payload: Any,
    *,
    source: str,
    require_paa: bool = False,
) -> Dict[str, Any]:
    """Validate untrusted SERP payloads before treating values as observations."""
    if not isinstance(payload, dict):
        raise ValueError(f"{source} SERP payload must be an object")

    organic_results = payload.get("organic_results")
    features = payload.get("features")
    paa_questions = payload.get("paa_questions", [])
    if not isinstance(organic_results, list):
        raise ValueError(f"{source} organic_results must be a list")
    if not isinstance(features, list):
        raise ValueError(f"{source} features must be a list")
    if require_paa and not isinstance(paa_questions, list):
        raise ValueError(f"{source} paa_questions must be a list")

    normalized_results = []
    for result in organic_results:
        if not isinstance(result, dict):
            raise ValueError(f"{source} organic results must be objects")
        title = result.get("title")
        url = result.get("url")
        description = result.get("description", "")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"{source} organic result title must be non-empty")
        if not isinstance(url, str) or not url.strip():
            raise ValueError(f"{source} organic result URL must be non-empty")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise ValueError(f"{source} organic result description must be text")
        normalized_results.append({**result, "title": title, "url": url, "description": description})

    for field_name, values in (("features", features), ("paa_questions", paa_questions)):
        if not isinstance(values, list) or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError(f"{source} {field_name} must contain non-empty strings")

    return {
        **payload,
        "organic_results": normalized_results,
        "features": features,
        "paa_questions": paa_questions,
    }


def run_playwright_serp_fallback(
    keyword: str,
    output_dir: str | Path = "research",
    now: Optional[datetime] = None,
    cli_runner: Optional[Callable[[str], str]] = None,
    npx_checker: Callable[[], bool] = npx_available,
) -> Dict[str, Any]:
    """Capture visible Google SERP facts through Playwright CLI and save raw provenance."""
    now = now or datetime.now()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    search_url = build_google_search_url(keyword)
    artifact_path = output_dir / (
        f"serp-playwright-{sanitize_filename(keyword)}-{now.strftime('%Y-%m-%d')}.json"
    )

    if not npx_checker():
        result = empty_playwright_fallback(
            keyword,
            search_url,
            artifact_path,
            now,
            "npx unavailable; install Node/npm or provide a SERP/PAA export.",
        )
        write_json_artifact(artifact_path, result)
        return result

    try:
        raw_output = (cli_runner or run_playwright_cli_serp_capture)(keyword)
        payload = normalize_serp_payload(
            parse_playwright_cli_payload(raw_output),
            source="Playwright",
            require_paa=True,
        )
        blocker = payload.get("blocker")
    except Exception as exc:
        result = empty_playwright_fallback(
            keyword,
            search_url,
            artifact_path,
            now,
            f"Playwright SERP fallback failed: {exc}",
        )
        write_json_artifact(artifact_path, result)
        return result

    organic_results = []
    if not blocker:
        for position, result in enumerate(payload.get("organic_results", [])[:10], start=1):
            url = result.get("url", "").strip()
            organic_results.append(
                {
                    "position": position,
                    "title": result.get("title", "").strip(),
                    "url": url,
                    "description": result.get("description", "").strip(),
                    "domain": extract_domain(url),
                    "source": "playwright_google",
                }
            )

    normalized = {
        "keyword": keyword,
        "captured_at": now.isoformat(),
        "fallback_used": True,
        "fallback_blocker": blocker,
        "search_url": payload.get("search_url") or search_url,
        "locale": {"hl": "en", "gl": "us", "pws": "0"},
        "raw_artifact": str(artifact_path),
        "organic_results": organic_results,
        "features": [] if blocker else dedupe_strings(payload.get("features", [])),
        "paa_questions": [] if blocker else dedupe_questions(payload.get("paa_questions", [])),
        "limitations": fallback_limitations(),
    }
    write_json_artifact(artifact_path, normalized)
    return normalized


def run_playwright_cli_serp_capture(keyword: str) -> str:
    """Run Playwright CLI against Google and return the extraction JSON string."""
    search_url = build_google_search_url(keyword)
    code = build_playwright_serp_extraction_code(search_url)
    npx_path = find_npx_executable()
    if not npx_path:
        raise RuntimeError("npx unavailable; install Node/npm or provide a SERP/PAA export.")
    command_prefix = [npx_path, "--yes", "--package", "@playwright/cli", "playwright-cli"]

    subprocess.run(
        command_prefix + ["open", "about:blank"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".js", delete=False) as temp_file:
            temp_file.write(code)
            code_path = temp_file.name
        try:
            completed = subprocess.run(
                command_prefix + ["run-code", "--filename", code_path, "--raw"],
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
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
        subprocess.run(
            command_prefix + ["close"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )


def build_playwright_serp_feature_extraction_code() -> str:
    """Return browser JavaScript for structurally verified SERP features and PAA."""
    return r"""() => {
    const cleanText = value => (value || '').replace(/\s+/g, ' ').trim();
    const nodeText = node => cleanText(
      node.getAttribute('aria-label') || node.innerText || node.textContent || ''
    );
    const featureEvidenceNodes = Array.from(document.querySelectorAll(
      'h1, h2, h3, [role="heading"]'
    ));
    const evidenceText = node => nodeText(node).toLowerCase();
    const isVerifiedFeatureHeading = node => !node.closest(
      'a, nav, [role="navigation"], div.MjjYud, div.g, div[data-sokoban-container]'
    );
    const verifiedFeatureHeadings = featureEvidenceNodes.filter(
      isVerifiedFeatureHeading
    );
    const evidenceLabels = new Set(
      verifiedFeatureHeadings.map(evidenceText).filter(Boolean)
    );
    const featureLabels = [
      ['ai_overview', ['ai overview']],
      ['featured_snippet', ['featured snippet', 'about featured snippets']],
      ['people_also_ask', ['people also ask']],
      ['video', ['video', 'videos']],
      ['image_pack', ['image', 'images']],
      ['ads', ['sponsored', 'ads']],
      ['discussions_and_forums', ['discussions and forums', 'forums']],
      ['shopping', ['shopping']]
    ];
    const features = featureLabels
      .filter(([, labels]) => labels.some(label => evidenceLabels.has(label)))
      .map(([feature]) => feature);

    const peopleAlsoAskHeading = verifiedFeatureHeadings.find(
      node => evidenceText(node) === 'people also ask'
    );
    const peopleAlsoAskRoot = peopleAlsoAskHeading
      ? peopleAlsoAskHeading.closest('section, div[data-hveid], div[jscontroller]')
      : null;
    const paaQuestions = peopleAlsoAskRoot
      ? Array.from(new Set(
          Array.from(peopleAlsoAskRoot.querySelectorAll('button, [role="button"]'))
            .map(nodeText)
            .filter(text => text.endsWith('?') && text.length >= 12 && text.length <= 140)
        )).slice(0, 12)
      : [];

    return { features, paaQuestions };
  }"""


def build_playwright_serp_organic_extraction_code() -> str:
    """Return browser JavaScript for verified organic result containers."""
    return r"""() => {
    const blockedHosts = new Set([
      'www.google.com',
      'google.com',
      'accounts.google.com',
      'support.google.com',
      'policies.google.com',
      'maps.google.com',
      'translate.google.com'
    ]);
    const normalizeHref = href => {
      try {
        const parsed = new URL(href);
        if (parsed.hostname.endsWith('google.com') && parsed.pathname === '/url') {
          return parsed.searchParams.get('q') || parsed.searchParams.get('url') || href;
        }
        return href;
      } catch (error) {
        return href;
      }
    };
    const cleanText = value => (value || '').replace(/\s+/g, ' ').trim();
    const results = [];
    const seen = new Set();
    const resultContainerSelectors = 'div.MjjYud, div.g, div[data-sokoban-container]';
    for (const anchor of Array.from(document.querySelectorAll('a'))) {
      const h3 = anchor.querySelector('h3');
      const title = cleanText(h3 ? h3.innerText : '');
      if (!title) continue;
      const container = anchor.closest(resultContainerSelectors);
      if (!container) continue;
      const normalizedUrl = normalizeHref(anchor.href || '');
      let parsed;
      try {
        parsed = new URL(normalizedUrl);
      } catch (error) {
        continue;
      }
      if (!['http:', 'https:'].includes(parsed.protocol)) continue;
      if (
        blockedHosts.has(parsed.hostname) ||
        parsed.hostname.endsWith('.google.com')
      ) continue;
      if (seen.has(normalizedUrl)) continue;
      seen.add(normalizedUrl);
      const containerText = cleanText(container.innerText || '');
      const lines = containerText
        .split('\n')
        .map(cleanText)
        .filter(line => line && line !== title && !line.startsWith('http'));
      const description = lines.slice(0, 3).join(' ');
      results.push({ title, url: normalizedUrl, description });
      if (results.length >= 10) break;
    }
    return results;
  }"""


def build_playwright_serp_extraction_code(search_url: str) -> str:
    """Return JavaScript function source for Playwright CLI run-code."""
    feature_code = build_playwright_serp_feature_extraction_code()
    organic_code = build_playwright_serp_organic_extraction_code()
    return f"""async page => {{
  const searchUrl = {json.dumps(search_url)};
  await page.goto(searchUrl, {{ waitUntil: 'domcontentloaded', timeout: 30000 }});
  await page.waitForTimeout(2500);
  const bodyText = await page.locator('body').innerText({{ timeout: 5000 }}).catch(() => '');
  const lowerText = bodyText.toLowerCase();
  let blocker = null;
  if (
    lowerText.includes('unusual traffic') ||
    lowerText.includes('not a robot') ||
    lowerText.includes('captcha') ||
    lowerText.includes('before you continue') ||
    lowerText.includes('consent.google')
  ) {{
    blocker = 'captcha_or_consent_or_unusual_traffic';
  }}

  const featurePayload = await page.evaluate({feature_code});
  const features = featurePayload.features;
  const organicResults = await page.evaluate({organic_code});

  const paaQuestions = featurePayload.paaQuestions;

  return JSON.stringify({{
    search_url: searchUrl,
    organic_results: organicResults,
    features,
    paa_questions: paaQuestions,
    blocker
  }});
}}"""


def parse_playwright_cli_payload(raw_output: str) -> Dict[str, Any]:
    """Parse JSON returned by Playwright CLI run-code, including raw string wrapping."""
    parsed = json.loads(raw_output.strip())
    if isinstance(parsed, str):
        parsed = json.loads(parsed)
    if not isinstance(parsed, dict):
        raise ValueError("Playwright fallback returned non-object JSON")
    return parsed


def empty_playwright_fallback(
    keyword: str,
    search_url: str,
    artifact_path: Path,
    now: datetime,
    blocker: str,
) -> Dict[str, Any]:
    """Build a blocked fallback payload without inventing SERP evidence."""
    return {
        "keyword": keyword,
        "captured_at": now.isoformat(),
        "fallback_used": True,
        "fallback_blocker": blocker,
        "search_url": search_url,
        "locale": {"hl": "en", "gl": "us", "pws": "0"},
        "raw_artifact": str(artifact_path),
        "organic_results": [],
        "features": [],
        "paa_questions": [],
        "limitations": fallback_limitations(),
    }


def fallback_limitations() -> List[str]:
    """Return standard limitations for Playwright SERP fallback evidence."""
    return [
        "browser-visible only",
        "no search volume",
        "no DataForSEO rank metrics",
        "no invented competitor metrics",
    ]


def write_json_artifact(path: Path, payload: Dict[str, Any]) -> None:
    """Write raw fallback provenance."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def dedupe_strings(values: List[Any]) -> List[str]:
    """Deduplicate non-empty strings in order."""
    seen = set()
    deduped = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped


def dedupe_questions(values: List[Any]) -> List[str]:
    """Deduplicate exact visible question strings in order."""
    questions = []
    seen = set()
    for value in values:
        question = str(value).strip()
        if not question.endswith("?") or question in seen:
            continue
        seen.add(question)
        questions.append(question)
    return questions


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")


def detect_content_type(title: str) -> str:
    """Detect content type from title."""
    title_lower = title.lower()

    patterns = {
        "Listicle": [r"\d+\s+(best|top|ways|tips|tools|ideas|examples|reasons)"],
        "How-To Guide": [r"how to", r"guide to", r"tutorial"],
        "Definition": [r"what is", r"what are", r"meaning of", r"definition"],
        "Comparison": [r"vs\.?", r"versus", r"compared", r"comparison", r"difference between"],
        "Review": [r"review", r"reviewed"],
        "Tool/Resource": [r"calculator", r"tool", r"generator", r"template", r"free"],
    }

    for content_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, title_lower):
                return content_type

    return "Unknown"


def has_freshness_signal(title: str, now: Optional[datetime] = None) -> bool:
    """Check if title contains year or freshness signals."""
    now = now or datetime.now()
    current_year = now.year
    last_year = current_year - 1

    freshness_pattern = re.compile(
        rf"\b(?:{current_year}|{last_year}|updated|latest|new)\b",
        re.IGNORECASE,
    )
    return bool(freshness_pattern.search(title))


def identify_recurring_h2_topics(
    heading_observations: List[Dict[str, Any]],
    minimum_distinct_urls: int = 3,
) -> List[str]:
    """Return exact normalized H2s observed on at least three distinct URLs."""
    urls_by_heading: Dict[str, set[str]] = {}
    display_by_heading: Dict[str, str] = {}
    for observation in heading_observations:
        url = observation.get("url")
        headings = observation.get("headings")
        if not isinstance(url, str) or not url.strip() or not isinstance(headings, list):
            continue
        for heading in headings:
            if not isinstance(heading, str) or not heading.strip():
                continue
            display = re.sub(r"\s+", " ", heading).strip()
            normalized = display.casefold()
            display_by_heading.setdefault(normalized, display)
            urls_by_heading.setdefault(normalized, set()).add(url.strip())

    recurring = [
        display_by_heading[normalized]
        for normalized, urls in urls_by_heading.items()
        if len(urls) >= minimum_distinct_urls
    ]
    return sorted(recurring, key=str.casefold)


def assess_difficulty(domains: List[str]) -> str:
    """Keep difficulty unresolved when only observed ranking domains are available."""
    if not domains:
        return "unknown"
    return "unresolved"


def generate_content_brief(
    keyword: str,
    analysis: Dict[str, Any],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Generate an evidence-bound SERP context block for Reader Contract planning."""
    if not analysis.get("top_results"):
        return {
            "target_keyword": keyword,
            "word_target": analysis.get("word_target"),
            "recommended_word_count": None,
            "serp_brief_available": False,
            "blocker": analysis.get("fallback_blocker") or "No organic results captured",
            "search_intent": analysis.get("search_intent", "unknown"),
            "observed_elements": [],
            "serp_features_to_evaluate": [],
            "structure_patterns": [],
            "must_have_elements": [],
            "serp_features_to_target": [],
            "structure_recommendations": [],
        }

    brief = {
        "target_keyword": keyword,
        "content_type": analysis.get("dominant_content_type") or "Unknown",
        "word_target": analysis.get("word_target"),
        "recommended_word_count": None,
        "search_intent": analysis.get("search_intent", "informational"),
        "tone": determine_tone(analysis.get("search_intent", "informational")),
        "observed_elements": [],
        "serp_features_to_evaluate": [],
        "structure_patterns": [],
    }

    freshness_signals = analysis.get("freshness_signals") or []
    top_result_count = len(analysis.get("top_results") or [])
    if freshness_signals and top_result_count:
        brief["observed_elements"].append(
            f"{len(freshness_signals)} of {top_result_count} result titles contain a freshness signal"
        )

    common_h2_topics = analysis.get("common_h2_topics") or []
    brief["structure_patterns"] = [
        str(topic).strip()
        for topic in common_h2_topics
        if isinstance(topic, str) and topic.strip()
    ]

    feature_guidance = {
        "featured_snippet": (
            "Featured Snippet - evaluate whether a concise direct answer fits the "
            "Reader Contract"
        ),
        "people_also_ask": (
            "People Also Ask - evaluate whether sourced FAQ answers fit the article"
        ),
        "video": (
            "Video - evaluate only if a relevant, approved video supports the article"
        ),
        "images": (
            "Images - evaluate whether useful images improve reader understanding"
        ),
        "image_pack": (
            "Image Pack - evaluate whether useful images improve reader understanding"
        ),
    }
    observed_feature_names = []
    for feature in analysis.get("serp_features", []):
        if isinstance(feature, dict):
            raw_name = feature.get("type") or feature.get("name") or feature.get("feature")
        else:
            raw_name = feature
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        normalized = re.sub(r"[\s-]+", "_", raw_name.strip().lower())
        if normalized in observed_feature_names:
            continue
        observed_feature_names.append(normalized)
        brief["serp_features_to_evaluate"].append(
            feature_guidance.get(
                normalized,
                f"{normalized.replace('_', ' ').title()} - evaluate applicability "
                "against intent, format, reader value, and verified inputs",
            )
        )

    # Transitional aliases preserve existing brief consumers without restoring
    # heuristic recommendations or a SERP-derived word target.
    brief["must_have_elements"] = None
    brief["serp_features_to_target"] = None
    brief["structure_recommendations"] = None

    return brief


def extract_number_from_titles(titles: List[str]) -> int:
    """Extract common number from listicle titles."""
    numbers = []
    for title in titles:
        match = re.search(r"(\d+)\s+", title)
        if match:
            numbers.append(int(match.group(1)))

    if numbers:
        return statistics.mode(numbers) if numbers else 10
    return 10


def determine_tone(intent: str) -> str:
    """Determine appropriate tone based on search intent."""
    intent_lower = str(intent).lower()

    if "transactional" in intent_lower:
        return "Direct and action-oriented"
    if "commercial" in intent_lower:
        return "Balanced and informative, helping decision-making"
    if "navigational" in intent_lower:
        return "Clear and straightforward"
    return "Educational and helpful"


def sanitize_filename(keyword: str) -> str:
    """Convert keyword to safe filename."""
    safe = re.sub(r"[^\w\s-]", "", keyword)
    safe = re.sub(r"[\s]+", "-", safe)
    safe = safe.lower().strip("-")
    return safe[:50]


def write_markdown_report(
    keyword: str,
    analysis: Dict[str, Any],
    output_dir: str | Path = "research",
    now: Optional[datetime] = None,
) -> Path:
    """Write detailed markdown report."""
    now = now or datetime.now()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f"serp-analysis-{sanitize_filename(keyword)}.md"

    with filename.open("w", encoding="utf-8") as report:
        report.write(f"# SERP Analysis: {keyword}\n\n")
        report.write(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M')}\n\n")
        report.write(
            "**Purpose:** Use verified visible SERP observations as strong editorial "
            "defaults, with documented Reader Contract exceptions.\n\n"
        )
        report.write("---\n\n")

        if analysis.get("fallback_used"):
            write_playwright_fallback_section(report, analysis)

        report.write("## Overview\n\n")
        report.write(f"- **Target Keyword:** {keyword}\n")
        report.write(f"- **Search Intent:** {analysis.get('search_intent', 'unknown')}\n")
        report.write(f"- **Dominant Content Type:** {analysis.get('dominant_content_type', 'Unknown')}\n")
        report.write(f"- **Competitive Difficulty:** {analysis.get('competitive_difficulty', 'unknown').upper()}\n")
        report.write(
            "- **Year Signals Prevalent:** "
            f"{'Yes' if analysis.get('freshness_important') else 'No'} "
            "(observed context only)\n\n"
        )

        report.write("## Content Context\n\n")
        if analysis.get("avg_word_count"):
            report.write("### Word Count\n\n")
            report.write(f"- **Average:** {analysis['avg_word_count']:,} words\n")
            report.write(f"- **Median:** {analysis.get('median_word_count', 0):,} words\n")
            report.write(f"- **Range:** {analysis.get('min_word_count', 0):,} - {analysis.get('max_word_count', 0):,} words\n")
            report.write("- **Use:** Competitor word counts are context only; they do not set the article target.\n")
        if analysis.get("word_target") is not None:
            report.write(
                f"- **Caller-Supplied Word Target:** {analysis['word_target']:,} words\n\n"
            )
            if analysis.get("difference_from_observed_average") is not None:
                difference = analysis["difference_from_observed_average"]
                report.write(
                    "- **Difference From Observed Competitor Average:** "
                    f"{difference:+,} words (reported as context only)\n\n"
                )
        else:
            report.write(
                "- **Word Target:** Unresolved until Reader Contract planning identifies intent, payoff, and required evidence.\n\n"
            )

        if analysis.get("competitor_lengths"):
            report.write("### Individual Competitor Counts\n\n")
            report.write("| Position | Page | Domain | Observed Words |\n")
            report.write("|----------|------|--------|----------------|\n")
            for competitor in analysis["competitor_lengths"]:
                title = str(competitor.get("title", "Untitled")).replace("|", "\\|")
                url = competitor.get("url", "")
                domain = competitor.get("domain", "")
                count = competitor.get("word_count", 0)
                report.write(
                    f"| {competitor.get('position', '')} | [{title}]({url}) | "
                    f"{domain} | {count:,} |\n"
                )
            report.write("\n")

        report.write("### Content Type Distribution\n\n")
        if analysis.get("content_type_distribution"):
            for content_type, count in sorted(
                analysis["content_type_distribution"].items(),
                key=lambda item: item[1],
                reverse=True,
            ):
                report.write(f"- {content_type}: {count}/{len(analysis.get('top_results', []))} results\n")
            report.write(
                f"\n**Observed Content Pattern:** {analysis.get('dominant_content_type', 'Guide')}\n\n"
            )
        else:
            report.write("- No content type distribution available because no organic results were captured.\n\n")

        report.write("## SERP Features Present\n\n")
        serp_features = analysis.get("serp_features", [])
        if serp_features:
            for feature in serp_features:
                report.write(f"- {feature}\n")
        else:
            report.write("- No special SERP features detected\n")
        report.write("\n")

        if analysis.get("paa_questions"):
            report.write("### Visible PAA Questions\n\n")
            for question in analysis["paa_questions"]:
                report.write(f"- {question}\n")
            report.write("\n")

        report.write("## Top 10 Ranking Analysis\n\n")
        report.write("| Position | Domain | Content Type | Word Count |\n")
        report.write("|----------|--------|--------------|------------|\n")
        word_count_by_position = {
            int(item["position"]): item["word_count"]
            for item in analysis.get("competitor_lengths", [])
            if item.get("position") is not None and item.get("word_count") is not None
        }
        word_count_by_position.update(
            {
                int(position): count
                for position, count in analysis.get("word_count_by_position", {}).items()
            }
        )
        for index, result in enumerate(analysis["top_results"], 1):
            domain = extract_domain(result.get("url", ""))
            content_type = analysis["content_types"][index - 1] if index <= len(analysis["content_types"]) else "Unknown"
            word_count: Any = word_count_by_position.get(index, "N/A")
            if isinstance(word_count, int):
                word_count = f"{word_count:,}"
            report.write(f"| {index} | {domain[:30]} | {content_type} | {word_count} |\n")
        if not analysis["top_results"]:
            report.write("| N/A | N/A | N/A | N/A |\n")
        report.write("\n")

        write_content_brief_section(report, analysis)
        write_competitive_insights_section(report, analysis)
        write_action_plan_section(report, keyword, analysis)

        report.write("## Top Ranking Titles (for reference)\n\n")
        if analysis["top_results"]:
            for index, result in enumerate(analysis["top_results"], 1):
                report.write(f"{index}. {result.get('title', 'No title')}\n")
        else:
            report.write("No titles captured.\n")
        report.write("\n")

    print(f"   Report saved: {filename}")
    return filename


def write_playwright_fallback_section(report: Any, analysis: Dict[str, Any]) -> None:
    """Write fallback provenance and limitations."""
    report.write("## Playwright SERP Fallback\n\n")
    report.write(f"- **DataForSEO failure reason:** {analysis.get('dataforseo_error') or 'not applicable'}\n")
    report.write(f"- **Search URL used:** {analysis.get('fallback_search_url') or 'not available'}\n")
    report.write(f"- **Timestamp:** {analysis.get('fallback_captured_at') or 'not available'}\n")
    report.write("- **Locale assumptions:** US, English, personalization disabled via `pws=0`\n")
    report.write(f"- **Raw artifact:** `{analysis.get('fallback_raw_artifact') or 'not available'}`\n")
    if analysis.get("fallback_blocker"):
        report.write(f"- **Playwright SERP fallback failed:** {analysis['fallback_blocker']}\n")
        report.write("- **No SERP competitor metrics were used.**\n")
        report.write(
            "- **Next acceptable evidence:** user-provided SERP/PAA export, verified Asana brief, GSC, live page evidence, and public sources.\n"
        )
    report.write(
        "- **Limitations:** browser-visible only; no search volume; no DataForSEO rank metrics; no invented competitor metrics.\n\n"
    )


def write_content_brief_section(report: Any, analysis: Dict[str, Any]) -> None:
    """Write content brief section."""
    brief = analysis.get("content_brief", {})
    if not brief:
        return

    report.write("## Content Brief\n\n")
    if not brief.get("serp_brief_available", True):
        report.write(
            "SERP-derived content brief unavailable because no organic results were captured. "
            "Use a user-provided SERP/PAA export, verified Asana brief, GSC, live page evidence, "
            "and public sources before making any competitor-informed editorial decisions.\n\n"
        )
        return

    report.write("### Article Context\n\n")
    report.write(f"- **Primary Keyword:** {brief.get('target_keyword')}\n")
    report.write(f"- **Observed Content Pattern:** {brief.get('content_type')}\n")
    if brief.get("word_target") is not None:
        report.write(
            f"- **Caller-Supplied Word Target:** {brief['word_target']:,} words\n"
        )
    else:
        report.write("- **Word Target:** Unresolved until Reader Contract planning\n")
    report.write(f"- **Search Intent:** {brief.get('search_intent')}\n")
    report.write(f"- **Tone:** {brief.get('tone')}\n\n")

    report.write("### Observation and Proof Status\n\n")
    observation_source = (
        "Playwright browser-visible capture"
        if analysis.get("fallback_used")
        else "DataForSEO structured SERP results"
    )
    report.write(f"- **Observation source:** {observation_source}\n")
    report.write(
        "- **Observation rule:** Only captured titles, URLs, snippets, feature labels, "
        "PAA text, extracted structure, and fetched word counts may be labeled observed.\n"
    )
    report.write(
        "- **Public-claim proof status:** SERP observations guide editorial strategy but "
        "do not approve customer claims, quotes, metrics, rankings, or outcomes.\n\n"
    )

    report.write("### Default Recommendation and Exception Rule\n\n")
    observed_content_type = brief.get('content_type')
    if observed_content_type and observed_content_type != "Unknown":
        report.write(
            f"- Match the dominant observed content type, **{observed_content_type}**, "
            "by default.\n"
        )
    else:
        report.write(
            "- Dominant content type is unresolved; do not infer a format without "
            "verified SERP evidence.\n"
        )
    report.write(
        "- Evaluate every identified SERP feature and target every applicable feature "
        "supported by search intent, article format, reader value, and verified inputs.\n"
    )
    report.write(
        "- A different format or an excluded applicable pattern requires a documented "
        "Reader Contract exception with the reader, intent, evidence, or business reason.\n\n"
    )

    observed_elements = brief.get("observed_elements", [])
    report.write("### Observed Elements To Evaluate\n\n")
    for element in observed_elements:
        report.write(f"- {element}\n")
    report.write("\n")

    serp_features_to_evaluate = brief.get("serp_features_to_evaluate", [])
    report.write("### SERP Features To Evaluate\n\n")
    if serp_features_to_evaluate:
        for feature in serp_features_to_evaluate:
            report.write(f"- {feature}\n")
    else:
        report.write("- No SERP feature action is implied by this run.\n")
    report.write("\n")

    structure_patterns = brief.get("structure_patterns", [])
    report.write("### Observed Structure Patterns\n\n")
    if structure_patterns:
        for index, section in enumerate(structure_patterns, 1):
            report.write(f"{index}. {section}\n")
    else:
        report.write("- No H2 topic recurred across at least three fetched competitor pages.\n")
    if analysis.get("heading_observations"):
        report.write("\n**Heading observation provenance:**\n")
        for observation in analysis["heading_observations"]:
            headings = "; ".join(observation.get("headings", []))
            report.write(f"- {observation.get('url')}: {headings}\n")
    report.write("\n")


def write_competitive_insights_section(report: Any, analysis: Dict[str, Any]) -> None:
    """Write competitive insights."""
    report.write("## Competitive Insights\n\n")
    report.write("### Domain Authority Mix\n\n")

    domain_counts = Counter(analysis["domains"])
    report.write("Top domains ranking:\n")
    if domain_counts:
        for domain, count in domain_counts.most_common(5):
            report.write(f"- {domain}: {count} result(s)\n")
    else:
        report.write("- No ranking domains captured.\n")

    difficulty = analysis.get("competitive_difficulty", "unknown")
    report.write(f"\n### Competitive Difficulty: {difficulty.upper()}\n\n")
    if difficulty == "unknown":
        report.write(
            "Competitive difficulty unavailable because no organic results were captured. "
            "Do not use SERP competitor metrics from this run.\n\n"
        )
        return
    report.write(
        "Competitive difficulty is unresolved because observed ranking domains alone "
        "do not establish keyword difficulty. Use a verified difficulty source before "
        "making a difficulty claim.\n\n"
    )


def write_action_plan_section(report: Any, keyword: str, analysis: Dict[str, Any]) -> None:
    """Write action plan section."""
    report.write("## Action Plan\n\n")
    if not analysis.get("top_results"):
        report.write("### Step 1: Resolve SERP Evidence Blocker\n")
        report.write("- [ ] Provide a SERP/PAA export or rerun after Google automation access is available\n")
        report.write("- [ ] Use verified Asana brief, GSC, live page evidence, and public sources only until SERP evidence is available\n")
        report.write("- [ ] Do not use competitor rankings, PAA questions, or difficulty claims from this blocked run\n\n")
        return

    report.write("### Step 1: Research (1-2 hours)\n")
    report.write("- [ ] Verify the visible observations against the captured ranking pages\n")
    report.write("- [ ] Identify must-have topics supported by verified recurrence, reader importance, and evidence\n")
    report.write("- [ ] Classify recurring, reader-critical, evidence-supported gaps as must-fill\n")
    report.write("- [ ] Collect only the approved evidence and examples the Reader Contract needs\n\n")

    report.write("### Step 2: Outline (30 minutes)\n")
    report.write("- [ ] Create detailed outline from the Reader Contract first\n")
    report.write("- [ ] Match the dominant observed content type unless the Reader Contract documents a justified exception\n")
    report.write("- [ ] Include must-fill gaps unless a Reader Contract exception records irrelevance, redundancy, or missing evidence\n")
    report.write("- [ ] Define only the H2 and H3 headings needed for continuity and payoff\n\n")

    report.write("### Step 3: Write (3-4 hours)\n")
    if analysis.get("word_target") is not None:
        report.write("- [ ] Write to the caller-supplied target without padding\n")
    else:
        report.write("- [ ] Resolve the Reader Contract word target before drafting\n")
    report.write("- [ ] Include must-have observed elements unless a Reader Contract exception is documented\n")
    report.write("- [ ] Evaluate every identified SERP feature and target each applicable feature without inventing answers\n")
    report.write("- [ ] Add visuals or screenshots only when they improve reader understanding\n\n")

    report.write("### Step 4: Optimize (30 minutes)\n")
    report.write(f"- [ ] Optimize title tag (include '{keyword}')\n")
    report.write("- [ ] Write compelling meta description\n")
    report.write("- [ ] Add internal links to related content\n")
    report.write("- [ ] Add FAQ schema markup only when approved FAQs are present\n")
    report.write("- [ ] Optimize images with alt text\n\n")

    report.write("### Step 5: Publish & Promote\n")
    report.write("- [ ] Publish on your site\n")
    report.write("- [ ] Share on social media\n")
    report.write("- [ ] Reach out for backlinks if appropriate\n")
    report.write("- [ ] Monitor rankings weekly\n\n")


if __name__ == "__main__":
    main()
