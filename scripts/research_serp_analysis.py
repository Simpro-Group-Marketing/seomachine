#!/usr/bin/env python3
"""
Research SERP Analysis

Deep analysis of what Google wants for a specific keyword.
DataForSEO is the primary source. When DataForSEO is unavailable, the script
falls back to a Playwright CLI capture of browser-visible Google SERP facts.
"""

from __future__ import annotations

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

from modules.content_length_comparator import ContentLengthComparator
from modules.dataforseo import DataForSEO
from modules.search_intent_analyzer import SearchIntentAnalyzer


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print('Usage: python scripts/research_serp_analysis.py "keyword phrase"')
        print('\nExample: python scripts/research_serp_analysis.py "your target keyword"')
        return

    run_serp_analysis(sys.argv[1])


def run_serp_analysis(
    keyword: str,
    output_dir: str | Path = "research",
    now: Optional[datetime] = None,
    dataforseo_factory: Callable[[], Any] = DataForSEO,
    fallback_runner: Optional[Callable[..., Dict[str, Any]]] = None,
    intent_analyzer_factory: Callable[[], Any] = SearchIntentAnalyzer,
    content_comparator_factory: Callable[[], Any] = ContentLengthComparator,
    print_fn: Callable[[str], None] = print,
) -> Dict[str, Any]:
    """Run SERP analysis with DataForSEO first and Playwright fallback second."""
    now = now or datetime.now()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fallback_runner = fallback_runner or run_playwright_serp_fallback

    print_fn("=" * 80)
    print_fn(f"SERP ANALYSIS: {keyword}")
    print_fn("=" * 80)
    print_fn(f"Date: {now.strftime('%Y-%m-%d %H:%M')}")
    print_fn("Strategy: Understand what Google wants before creating content")
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
            serp_data = dfs.get_serp_data(keyword, limit=20)
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
        "domains": [],
        "domain_authority": [],
        "freshness_signals": [],
        "common_h2_topics": [],
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
            word_count = content_comparator.fetch_word_count(url)
            if word_count and word_count > 100:
                analysis["word_counts"].append(word_count)
                print_fn(f"   [{index}] {domain} - {word_count:,} words - {content_type}")
            else:
                print_fn(f"   [{index}] {domain} - Word count unavailable - {content_type}")
        except Exception:
            print_fn(f"   [{index}] {domain} - Word count unavailable - {content_type}")

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
        print_fn("2. Use the content brief to create your article")
        print_fn("3. Ensure your content meets/exceeds the recommended word count")
        print_fn("4. Match the dominant content type identified")
        print_fn("5. Target the SERP features present (PAA, featured snippet, etc.)")
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
    print_fn("\n4. Calculating content requirements...")

    if analysis["content_types"]:
        type_counts = Counter(analysis["content_types"])
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
        analysis["recommended_word_count"] = int(avg_words * 1.1)

        print_fn(f"   Average Word Count: {avg_words:,.0f}")
        print_fn(f"   Median Word Count: {median_words:,.0f}")
        print_fn(f"   Range: {min_words:,} - {max_words:,}")
        print_fn(f"   Recommended: {analysis['recommended_word_count']:,}+ words")

    freshness_ratio = (
        len(analysis["freshness_signals"]) / len(organic_results)
        if organic_results
        else 0
    )
    analysis["freshness_important"] = freshness_ratio >= 0.6
    freshness_label = "IMPORTANT" if analysis["freshness_important"] else "Normal"
    print_fn(
        f"   Freshness: {freshness_label} "
        f"({len(analysis['freshness_signals'])}/{len(organic_results)} results mention year)"
    )

    print_fn("\n   SERP Features Present:")
    if analysis["serp_features"]:
        for feature in analysis["serp_features"][:5]:
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
        payload = parse_playwright_cli_payload(raw_output)
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


def build_playwright_serp_extraction_code(search_url: str) -> str:
    """Return JavaScript function source for Playwright CLI run-code."""
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

  const features = [];
  const featureChecks = [
    ['ai_overview', /ai overview/i],
    ['featured_snippet', /featured snippet|about featured snippets/i],
    ['people_also_ask', /people also ask/i],
    ['video', /videos?/i],
    ['image_pack', /images?/i],
    ['ads', /sponsored|ad\\s/i],
    ['discussions_and_forums', /discussions and forums|forums?/i],
    ['shopping', /shopping/i]
  ];
  for (const [feature, pattern] of featureChecks) {{
    if (pattern.test(bodyText)) features.push(feature);
  }}

  const organicResults = await page.evaluate(() => {{
    const blockedHosts = new Set([
      'www.google.com',
      'google.com',
      'accounts.google.com',
      'support.google.com',
      'policies.google.com',
      'maps.google.com',
      'translate.google.com'
    ]);
    const normalizeHref = href => {{
      try {{
        const parsed = new URL(href);
        if (parsed.hostname.endsWith('google.com') && parsed.pathname === '/url') {{
          return parsed.searchParams.get('q') || parsed.searchParams.get('url') || href;
        }}
        return href;
      }} catch (error) {{
        return href;
      }}
    }};
    const cleanText = value => (value || '').replace(/\\s+/g, ' ').trim();
    const results = [];
    const seen = new Set();
    for (const anchor of Array.from(document.querySelectorAll('a'))) {{
      const h3 = anchor.querySelector('h3');
      const title = cleanText(h3 ? h3.innerText : '');
      if (!title) continue;
      const normalizedUrl = normalizeHref(anchor.href || '');
      let parsed;
      try {{
        parsed = new URL(normalizedUrl);
      }} catch (error) {{
        continue;
      }}
      if (!['http:', 'https:'].includes(parsed.protocol)) continue;
      if (blockedHosts.has(parsed.hostname)) continue;
      if (seen.has(normalizedUrl)) continue;
      seen.add(normalizedUrl);
      const container = anchor.closest('div.MjjYud, div.g, div[data-sokoban-container], div[jscontroller]') || anchor.parentElement;
      const containerText = cleanText(container ? container.innerText : '');
      const lines = containerText
        .split('\\n')
        .map(cleanText)
        .filter(line => line && line !== title && !line.startsWith('http'));
      const description = lines.slice(0, 3).join(' ');
      results.push({{ title, url: normalizedUrl, description }});
      if (results.length >= 10) break;
    }}
    return results;
  }});

  const paaQuestions = Array.from(new Set(
    bodyText
      .split('\\n')
      .map(line => line.replace(/\\s+/g, ' ').trim())
      .filter(line => line.endsWith('?') && line.length >= 12 && line.length <= 140)
  )).slice(0, 12);

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

    return "General Article"


def has_freshness_signal(title: str, now: Optional[datetime] = None) -> bool:
    """Check if title contains year or freshness signals."""
    now = now or datetime.now()
    current_year = now.year
    last_year = current_year - 1

    freshness_patterns = [
        str(current_year),
        str(last_year),
        "updated",
        "latest",
        "new",
    ]

    return any(pattern in title.lower() for pattern in freshness_patterns)


def assess_difficulty(domains: List[str]) -> str:
    """Assess competitive difficulty based on domains."""
    if not domains:
        return "unknown"

    high_authority = [
        "youtube.com",
        "wikipedia.org",
        "forbes.com",
        "nytimes.com",
        "washingtonpost.com",
        "cnn.com",
        "bbc.com",
        "techcrunch.com",
        "wired.com",
        "theverge.com",
        "reddit.com",
        "hubspot.com",
    ]

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "competitors.json")
    medium_authority = []
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as config_file:
            config = json.load(config_file)
        medium_authority = config.get("direct_competitors", []) + config.get("content_competitors", [])

    high_count = sum(1 for domain in domains if any(authority in domain for authority in high_authority))
    medium_count = sum(1 for domain in domains if any(authority in domain for authority in medium_authority))

    if high_count >= 6:
        return "very high"
    if high_count >= 4:
        return "high"
    if medium_count >= 5:
        return "medium"
    return "low"


def generate_content_brief(
    keyword: str,
    analysis: Dict[str, Any],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Generate a comprehensive content brief."""
    now = now or datetime.now()
    if not analysis.get("top_results"):
        return {
            "target_keyword": keyword,
            "serp_brief_available": False,
            "blocker": analysis.get("fallback_blocker") or "No organic results captured",
            "search_intent": analysis.get("search_intent", "unknown"),
        }

    brief = {
        "target_keyword": keyword,
        "content_type": analysis.get("dominant_content_type", "Guide"),
        "recommended_word_count": analysis.get("recommended_word_count", 2000),
        "search_intent": analysis.get("search_intent", "informational"),
        "tone": determine_tone(analysis.get("search_intent", "informational")),
        "must_have_elements": [],
        "serp_features_to_target": [],
        "structure_recommendations": [],
    }

    content_type = brief["content_type"]

    if "Listicle" in content_type:
        brief["must_have_elements"] = [
            "Numbered list format",
            "Comparison table",
            "Pros and cons for each item",
            "Clear introduction explaining criteria",
            "Summary/conclusion with top recommendation",
        ]
        brief["structure_recommendations"] = [
            "Introduction (what, why, how to choose)",
            f"Item 1-{extract_number_from_titles(analysis.get('title_patterns', []))} (each with description, pros/cons)",
            "Comparison table",
            "FAQs",
            "Conclusion with top pick",
        ]

    elif "How-To" in content_type:
        brief["must_have_elements"] = [
            "Step-by-step instructions",
            "Visual aids (screenshots, diagrams)",
            "Prerequisites section",
            "Time estimate",
            "Troubleshooting tips",
        ]
        brief["structure_recommendations"] = [
            "Introduction (what you'll learn)",
            "Prerequisites/Requirements",
            "Step-by-step instructions",
            "Common mistakes to avoid",
            "FAQs",
            "Conclusion/Next steps",
        ]

    elif "Definition" in content_type:
        brief["must_have_elements"] = [
            "Clear, concise definition upfront",
            "Examples",
            "History/etymology if relevant",
            "Related concepts",
            "Practical applications",
        ]
        brief["structure_recommendations"] = [
            "Quick definition (target featured snippet)",
            "Detailed explanation",
            "Examples",
            "Related terms/concepts",
            "Practical applications",
            "FAQs",
        ]

    else:
        brief["must_have_elements"] = [
            "Comprehensive coverage",
            "Expert insights",
            "Real examples",
            "Data and statistics",
        ]
        brief["structure_recommendations"] = [
            "Introduction",
            "Main sections (3-5)",
            "Examples and case studies",
            "FAQs",
            "Conclusion",
        ]

    serp_features = analysis.get("serp_features", [])
    serp_feature_text = str(serp_features).lower()

    if "featured_snippet" in serp_feature_text:
        brief["serp_features_to_target"].append(
            "Featured Snippet - Add concise definition/answer in first 100 words"
        )

    if "people_also_ask" in serp_feature_text:
        brief["serp_features_to_target"].append(
            "People Also Ask - Add FAQ section answering related questions"
        )

    if "video" in serp_feature_text:
        brief["serp_features_to_target"].append("Video - Consider embedding relevant video or creating one")

    if "images" in serp_feature_text or "image_pack" in serp_feature_text:
        brief["serp_features_to_target"].append("Images - Include high-quality images with alt text")

    if analysis.get("freshness_important"):
        brief["must_have_elements"].append(f"Current year ({now.year}) in title and content")
        brief["must_have_elements"].append("Latest statistics and examples")

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
        report.write("**Purpose:** Understand what Google wants for this keyword before creating content\n\n")
        report.write("---\n\n")

        if analysis.get("fallback_used"):
            write_playwright_fallback_section(report, analysis)

        report.write("## Overview\n\n")
        report.write(f"- **Target Keyword:** {keyword}\n")
        report.write(f"- **Search Intent:** {analysis.get('search_intent', 'unknown')}\n")
        report.write(f"- **Dominant Content Type:** {analysis.get('dominant_content_type', 'Unknown')}\n")
        report.write(f"- **Competitive Difficulty:** {analysis.get('competitive_difficulty', 'medium').upper()}\n")
        report.write(f"- **Freshness Important:** {'Yes' if analysis.get('freshness_important') else 'No'}\n\n")

        report.write("## Content Requirements\n\n")
        if analysis.get("avg_word_count"):
            report.write("### Word Count\n\n")
            report.write(f"- **Average:** {analysis['avg_word_count']:,} words\n")
            report.write(f"- **Median:** {analysis.get('median_word_count', 0):,} words\n")
            report.write(f"- **Range:** {analysis.get('min_word_count', 0):,} - {analysis.get('max_word_count', 0):,} words\n")
            report.write(f"- **Recommended:** {analysis.get('recommended_word_count', 2000):,}+ words (exceed average by 10%)\n\n")

        report.write("### Content Type Distribution\n\n")
        if analysis.get("content_type_distribution"):
            for content_type, count in sorted(
                analysis["content_type_distribution"].items(),
                key=lambda item: item[1],
                reverse=True,
            ):
                report.write(f"- {content_type}: {count}/10 results\n")
            report.write(
                f"\n**Recommendation:** Your content should be a **{analysis.get('dominant_content_type', 'Guide')}**\n\n"
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
        for index, result in enumerate(analysis["top_results"], 1):
            domain = extract_domain(result.get("url", ""))
            content_type = analysis["content_types"][index - 1] if index <= len(analysis["content_types"]) else "Unknown"
            word_count: Any = analysis["word_counts"][index - 1] if index <= len(analysis["word_counts"]) else "N/A"
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
            "and public sources before making competitor-derived content requirements.\n\n"
        )
        return

    report.write("### Target Specifications\n\n")
    report.write(f"- **Primary Keyword:** {brief.get('target_keyword')}\n")
    report.write(f"- **Content Type:** {brief.get('content_type')}\n")
    report.write(f"- **Target Word Count:** {brief.get('recommended_word_count', 2000):,}+ words\n")
    report.write(f"- **Search Intent:** {brief.get('search_intent')}\n")
    report.write(f"- **Tone:** {brief.get('tone')}\n\n")

    report.write("### Must-Have Elements\n\n")
    for element in brief.get("must_have_elements", []):
        report.write(f"- [ ] {element}\n")
    report.write("\n")

    if brief.get("serp_features_to_target"):
        report.write("### SERP Features to Target\n\n")
        for feature in brief["serp_features_to_target"]:
            report.write(f"- [ ] {feature}\n")
        report.write("\n")

    report.write("### Recommended Structure\n\n")
    for index, section in enumerate(brief.get("structure_recommendations", []), 1):
        report.write(f"{index}. {section}\n")
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

    report.write(f"\n### Competitive Difficulty: {analysis.get('competitive_difficulty', 'medium').upper()}\n\n")
    difficulty = analysis.get("competitive_difficulty", "medium")
    if difficulty in ["very high", "high"]:
        report.write("High competition - Major authority sites dominate. You'll need:\n")
        report.write("- Exceptional content quality\n")
        report.write("- Strong backlink profile\n")
        report.write("- Unique angle or superior depth\n")
        report.write("- Time to build authority (6-12 months)\n\n")
    elif difficulty == "medium":
        report.write("Moderate competition - Mix of authority and niche sites. You can rank with:\n")
        report.write("- Comprehensive, well-researched content\n")
        report.write("- Better formatting and user experience\n")
        report.write("- Some quality backlinks\n")
        report.write("- Expected timeline: 3-6 months\n\n")
    else:
        if difficulty == "unknown":
            report.write(
                "Competitive difficulty unavailable because no organic results were captured. "
                "Do not use SERP competitor metrics from this run.\n\n"
            )
            return
        report.write("Low competition - Opportunity for quick rankings. Focus on:\n")
        report.write("- Quality content exceeding current results\n")
        report.write("- Proper on-page SEO\n")
        report.write("- Internal linking\n")
        report.write("- Expected timeline: 1-3 months\n\n")


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
    report.write("- [ ] Read all top 10 ranking articles\n")
    report.write("- [ ] Identify common topics covered\n")
    report.write("- [ ] Find gaps they missed\n")
    report.write("- [ ] Collect statistics and examples\n\n")

    report.write("### Step 2: Outline (30 minutes)\n")
    report.write("- [ ] Create detailed outline following recommended structure\n")
    report.write("- [ ] Plan unique angles or superior depth\n")
    report.write("- [ ] List all H2 and H3 headings\n\n")

    report.write("### Step 3: Write (3-4 hours)\n")
    report.write("- [ ] Write to the recommended word count\n")
    report.write("- [ ] Include all must-have elements\n")
    report.write("- [ ] Target SERP features (featured snippet, PAA)\n")
    report.write("- [ ] Add visuals/screenshots\n\n")

    report.write("### Step 4: Optimize (30 minutes)\n")
    report.write(f"- [ ] Optimize title tag (include '{keyword}')\n")
    report.write("- [ ] Write compelling meta description\n")
    report.write("- [ ] Add internal links to related content\n")
    report.write("- [ ] Add FAQ schema markup\n")
    report.write("- [ ] Optimize images with alt text\n\n")

    report.write("### Step 5: Publish & Promote\n")
    report.write("- [ ] Publish on your site\n")
    report.write("- [ ] Share on social media\n")
    report.write("- [ ] Reach out for backlinks if appropriate\n")
    report.write("- [ ] Monitor rankings weekly\n\n")


if __name__ == "__main__":
    main()
