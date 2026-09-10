"""Render and statically validate the plumbing recovery article preview."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_sources.modules.frontmatter import split_frontmatter


DEFAULT_ARTICLE = REPO_ROOT / "rewrites" / "best-plumbing-job-management-software-rewrite-2026-09-03.md"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "research"
    / "best-plumbing-job-management-software-remediation-2026-09-03"
    / "replacement-preview.html"
)
DEFAULT_VALIDATION = (
    DEFAULT_OUTPUT.parent / "raw" / "replacement-render" / "static-validation.json"
)
MARKED_VERSION = "16.3.0"
EXPECTED_TITLE = "Best Plumbing Job Management Software for 2026 | Simpro"
EXPECTED_H1 = "Best Plumbing Job Management Software for 2026"
EXPECTED_META_DESCRIPTION = (
    "Compare eight plumbing job management software platforms by business fit, "
    "workflow depth, pricing route, rollout questions, risk, and three-year cost "
    "for demos."
)
EXPECTED_CANONICAL = (
    "https://www.simprogroup.com/blog/best-plumbing-job-management-software"
)
EXPECTED_DATE_PUBLISHED = "2026-05-06"
EXPECTED_ITEM_LIST = [
    "BuildOps",
    "FieldPulse",
    "Housecall Pro",
    "Jobber",
    "Service Fusion",
    "ServiceTitan",
    "Simpro",
    "Workiz",
]
LEAK_PHRASES = [
    "original eight tools",
    "same order as the current article",
    "fixes the incorrect electrical",
    "keeps the existing url slug",
    "before cms publish",
    "cms publish",
]


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_markdown(body: str) -> str:
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        raise RuntimeError("npx is required to run the pinned marked renderer.")
    result = subprocess.run(
        [npx, "--yes", f"marked@{MARKED_VERSION}", "--gfm"],
        input=body,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "marked rendering failed")
    return result.stdout


def _schema_graph(metadata: dict[str, Any], body_html: str) -> dict[str, Any]:
    soup = BeautifulSoup(body_html, "html.parser")
    faq_heading = next(
        (
            tag
            for tag in soup.select("h2")
            if _normalize(tag.get_text(" ", strip=True)).casefold().startswith(
                "frequently asked questions"
            )
        ),
        None,
    )
    faq_rows: list[dict[str, str]] = []
    current = faq_heading.find_next_sibling() if faq_heading else None
    while current is not None and current.name != "h2":
        if current.name == "h3":
            answer_parts: list[str] = []
            answer_node = current.find_next_sibling()
            while answer_node is not None and answer_node.name not in {"h2", "h3"}:
                answer_parts.append(answer_node.get_text(" ", strip=True))
                answer_node = answer_node.find_next_sibling()
            faq_rows.append(
                {
                    "question": _normalize(current.get_text(" ", strip=True)),
                    "answer": _normalize(" ".join(answer_parts)),
                }
            )
        current = current.find_next_sibling()

    canonical = str(metadata.get("canonical_url") or "")
    featured_image = str(metadata.get("featured_image") or "")
    item_names = [str(value) for value in metadata.get("item_list_entries", [])]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "headline": str(metadata.get("title") or ""),
                "datePublished": str(metadata.get("date_published") or ""),
                "mainEntityOfPage": canonical,
                "image": {"@id": f"{canonical}#primaryimage"},
                "publisher": {"@type": "Organization", "name": "Simpro"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Blog",
                        "item": "https://www.simprogroup.com/blog",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": str(metadata.get("title") or ""),
                        "item": canonical,
                    },
                ],
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": row["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": row["answer"],
                        },
                    }
                    for row in faq_rows
                ],
            },
            {
                "@type": "ImageObject",
                "@id": f"{canonical}#primaryimage",
                "url": featured_image,
                "contentUrl": featured_image,
                "caption": str(metadata.get("featured_image_alt") or ""),
            },
            {
                "@type": "ItemList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "name": name,
                    }
                    for index, name in enumerate(item_names, start=1)
                ],
            },
        ],
    }


def _document(metadata: dict[str, Any], body_html: str, source_hash: str) -> str:
    title = html.escape(str(metadata.get("meta_title") or metadata.get("title") or ""))
    description = html.escape(str(metadata.get("meta_description") or ""), quote=True)
    canonical = html.escape(str(metadata.get("canonical_url") or ""), quote=True)
    schema_json = json.dumps(_schema_graph(metadata, body_html), ensure_ascii=True)
    return f"""<!doctype html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index,follow">
  <meta name="description" content="{description}">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="data:,">
  <title>{title}</title>
  <script type="application/ld+json">{schema_json}</script>
  <style>
    :root {{ color-scheme: light; font-family: Arial, Helvetica, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: #222; background: #fff; font-size: 17px; line-height: 1.62; }}
    header {{ border-bottom: 1px solid #d8d8d8; background: #f5f5f5; }}
    header div, article {{ width: min(100% - 32px, 1120px); margin: 0 auto; }}
    header div {{ padding: 14px 0; color: #555; font-size: 14px; }}
    article {{ padding: 36px 0 72px; }}
    h1, h2, h3 {{ color: #151515; line-height: 1.2; letter-spacing: 0; }}
    h1 {{ max-width: 860px; margin: 0 0 20px; font-size: 42px; }}
    h2 {{ margin: 48px 0 14px; font-size: 30px; }}
    h3 {{ margin: 32px 0 10px; font-size: 23px; }}
    p, ul, ol {{ max-width: 820px; overflow-wrap: anywhere; }}
    a {{ color: #006f75; text-underline-offset: 3px; }}
    img {{ display: block; width: auto; max-width: 100%; height: auto; margin: 28px 0; }}
    .table-responsive {{ width: 100%; margin: 28px 0; overflow-x: auto !important; border: 1px solid #cfcfcf; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; font-size: 15px; line-height: 1.4; }}
    th, td {{ padding: 12px; border: 1px solid #d8d8d8; text-align: left; vertical-align: top; }}
    thead th {{ background: #efefef; }}
    tbody th {{ background: #f8f8f8; }}
    @media (max-width: 640px) {{
      body {{ font-size: 16px; }}
      header div, article {{ width: min(100% - 24px, 1120px); }}
      article {{ padding-top: 24px; }}
      h1 {{ font-size: 33px; }}
      h2 {{ font-size: 26px; }}
      h3 {{ font-size: 21px; }}
    }}
  </style>
</head>
<body data-source-sha256="{source_hash}">
  <header><div>Local CMS render preview</div></header>
  <main><article>{body_html}</article></main>
</body>
</html>
"""


def _graph_nodes(soup: BeautifulSoup) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        payload = json.loads(script.string or script.get_text())
        if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
            nodes.extend(node for node in payload["@graph"] if isinstance(node, dict))
        elif isinstance(payload, dict):
            nodes.append(payload)
    return nodes


def _type_nodes(nodes: list[dict[str, Any]], schema_type: str) -> list[dict[str, Any]]:
    return [node for node in nodes if node.get("@type") == schema_type]


def _visible_faqs(soup: BeautifulSoup) -> list[dict[str, str]]:
    heading = next(
        (
            tag
            for tag in soup.select("h2")
            if _normalize(tag.get_text(" ", strip=True)).casefold()
            .startswith("frequently asked questions")
        ),
        None,
    )
    if heading is None:
        return []

    faqs: list[dict[str, str]] = []
    current: Tag | None = heading.find_next_sibling()
    while current is not None and current.name != "h2":
        if current.name == "h3":
            answer_parts: list[str] = []
            answer_node = current.find_next_sibling()
            while answer_node is not None and answer_node.name not in {"h2", "h3"}:
                answer_parts.append(answer_node.get_text(" ", strip=True))
                answer_node = answer_node.find_next_sibling()
            faqs.append(
                {
                    "question": _normalize(current.get_text(" ", strip=True)),
                    "answer": _normalize(" ".join(answer_parts)),
                }
            )
        current = current.find_next_sibling()
    return faqs


def _schema_faqs(node: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "question": _normalize(str(item.get("name", ""))),
            "answer": _normalize(str(item.get("acceptedAnswer", {}).get("text", ""))),
        }
        for item in node.get("mainEntity", [])
        if isinstance(item, dict)
    ]


def _result(name: str, passed: bool, actual: Any, expected: Any = None) -> dict[str, Any]:
    return {
        "check": name,
        "passed": passed,
        "actual": actual,
        "expected": expected,
    }


def _validate(document: str, article_hash: str) -> dict[str, Any]:
    soup = BeautifulSoup(document, "html.parser")
    nodes = _graph_nodes(soup)
    articles = _type_nodes(nodes, "BlogPosting")
    breadcrumbs = _type_nodes(nodes, "BreadcrumbList")
    faq_nodes = _type_nodes(nodes, "FAQPage")
    item_lists = _type_nodes(nodes, "ItemList")
    visible_faqs = _visible_faqs(soup)
    schema_faqs = _schema_faqs(faq_nodes[0]) if len(faq_nodes) == 1 else []
    body_text = _normalize(soup.body.get_text(" ", strip=True) if soup.body else "")
    article_element = soup.select_one("article")
    article_text = _normalize(
        article_element.get_text(" ", strip=True) if article_element else ""
    )
    public_text = article_text.casefold()
    h1_values = [_normalize(tag.get_text(" ", strip=True)) for tag in soup.select("h1")]
    tables = soup.select("table")
    first_table = tables[0] if tables else None
    table_wrapper = first_table.find_parent(class_="table-responsive") if first_table else None
    body_before_table = document.split("<table", 1)[0]
    words_before_table = len(
        BeautifulSoup(body_before_table, "html.parser").get_text(" ", strip=True).split()
    )
    first_100_words = " ".join(article_text.split()[:100]).casefold()
    article_node = articles[0] if len(articles) == 1 else {}
    author = article_node.get("author") if isinstance(article_node, dict) else None
    publisher = article_node.get("publisher", {}) if isinstance(article_node, dict) else {}
    item_names = []
    if len(item_lists) == 1:
        item_names = [
            str(
                item.get("name")
                or (
                    item.get("item", {}).get("name", "")
                    if isinstance(item.get("item"), dict)
                    else ""
                )
            )
            for item in item_lists[0].get("itemListElement", [])
            if isinstance(item, dict)
        ]
    schema_types = sorted(
        {str(node.get("@type")) for node in nodes if node.get("@type")}
    )

    title = _normalize(soup.title.get_text() if soup.title else "")
    description_tag = soup.select_one('meta[name="description"]')
    canonical_tag = soup.select_one('link[rel="canonical"]')
    robots_tag = soup.select_one('meta[name="robots"]')
    leak_matches = [phrase for phrase in LEAK_PHRASES if phrase in public_text]
    date_modified_present = "dateModified" in article_node

    checks = [
        _result("title", title == EXPECTED_TITLE, title, EXPECTED_TITLE),
        _result(
            "meta_description",
            bool(description_tag)
            and description_tag.get("content") == EXPECTED_META_DESCRIPTION,
            description_tag.get("content") if description_tag else None,
            EXPECTED_META_DESCRIPTION,
        ),
        _result(
            "canonical",
            bool(canonical_tag) and canonical_tag.get("href") == EXPECTED_CANONICAL,
            canonical_tag.get("href") if canonical_tag else None,
            EXPECTED_CANONICAL,
        ),
        _result(
            "robots_indexable",
            bool(robots_tag)
            and "index" in str(robots_tag.get("content", "")).casefold()
            and "noindex" not in str(robots_tag.get("content", "")).casefold(),
            robots_tag.get("content") if robots_tag else None,
            "index,follow without noindex",
        ),
        _result("single_expected_h1", h1_values == [EXPECTED_H1], h1_values, [EXPECTED_H1]),
        _result("comparison_table_present", len(tables) >= 1, len(tables), ">=1"),
        _result(
            "comparison_table_responsive_wrapper",
            table_wrapper is not None,
            table_wrapper.get("class") if table_wrapper else None,
            "table-responsive",
        ),
        _result("table_within_first_300_words", words_before_table <= 300, words_before_table, "<=300"),
        _result(
            "direct_answer_within_first_100_words",
            "the best plumbing job management software fits" in first_100_words,
            first_100_words,
            "direct answer phrase",
        ),
        _result(
            "publisher_disclosure_within_first_100_words",
            "simpro publishes this guide" in first_100_words,
            first_100_words,
            "Simpro publishes this guide",
        ),
        _result("operational_leakage", not leak_matches, leak_matches, []),
        _result("em_dash_absent", "\u2014" not in body_text, "\u2014" in body_text, False),
        _result(
            "required_schema_types",
            all(value in schema_types for value in ["BlogPosting", "BreadcrumbList", "FAQPage", "ItemList"]),
            schema_types,
            ["BlogPosting", "BreadcrumbList", "FAQPage", "ItemList"],
        ),
        _result("single_blog_posting", len(articles) == 1, len(articles), 1),
        _result("single_breadcrumb_list", len(breadcrumbs) == 1, len(breadcrumbs), 1),
        _result("single_faq_page", len(faq_nodes) == 1, len(faq_nodes), 1),
        _result("single_item_list", len(item_lists) == 1, len(item_lists), 1),
        _result(
            "date_published",
            article_node.get("datePublished") == EXPECTED_DATE_PUBLISHED,
            article_node.get("datePublished"),
            EXPECTED_DATE_PUBLISHED,
        ),
        _result(
            "date_modified_withheld_before_deployment",
            not date_modified_present,
            article_node.get("dateModified"),
            None,
        ),
        _result(
            "organization_publisher_without_person_author",
            author is None
            and isinstance(publisher, dict)
            and publisher.get("@type") == "Organization",
            {"author": author, "publisher": publisher},
            {"author": None, "publisher": {"@type": "Organization"}},
        ),
        _result("visible_faq_count", len(visible_faqs) == 4, len(visible_faqs), 4),
        _result("faq_schema_matches_visible_copy", schema_faqs == visible_faqs, schema_faqs, visible_faqs),
        _result("item_list_order_and_count", item_names == EXPECTED_ITEM_LIST, item_names, EXPECTED_ITEM_LIST),
        _result(
            "source_hash_binding",
            soup.body is not None and soup.body.get("data-source-sha256") == article_hash,
            soup.body.get("data-source-sha256") if soup.body else None,
            article_hash,
        ),
    ]
    return {
        "schema": "plumbing-remediation-static-render-validation/v1",
        "renderer": {"package": "marked", "version": MARKED_VERSION},
        "article_sha256": article_hash,
        "visible_body_word_count": len(body_text.split()),
        "visible_article_word_count": len(article_text.split()),
        "checks": checks,
        "summary": {
            "passed": sum(1 for check in checks if check["passed"]),
            "failed": sum(1 for check in checks if not check["passed"]),
            "all_passed": all(check["passed"] for check in checks),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--article", type=Path, default=DEFAULT_ARTICLE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    args = parser.parse_args()

    article = args.article.resolve()
    output = args.output.resolve()
    validation_path = args.validation.resolve()
    raw = article.read_text(encoding="utf-8")
    metadata, body, _ = split_frontmatter(raw)
    article_hash = _sha256(article)
    document = _document(metadata, _render_markdown(body), article_hash)
    validation = _validate(document, article_hash)

    output.parent.mkdir(parents=True, exist_ok=True)
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8", newline="\n")
    validation_path.write_text(
        json.dumps(validation, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(validation["summary"], indent=2))
    print(f"preview={output}")
    print(f"validation={validation_path}")
    return 0 if validation["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
