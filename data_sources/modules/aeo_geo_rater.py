"""
AEO/GEO Rater

Scores blog drafts for answer engine optimization and generative engine
optimization readiness. The score is out of 100; drafts should score 90+
before they are treated as publish-ready for AEO/GEO.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from .faq_proof_guard import check_content as check_faq_proof
except ImportError:
    from faq_proof_guard import check_content as check_faq_proof


PASS_THRESHOLD = 90


def rate_aeo_geo(
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Rate content against AEO/GEO publishing requirements.

    Args:
        content: Full markdown article content.
        metadata: Optional metadata such as primary_keyword, main_question, author.

    Returns:
        Dict with score, passed, checks, issues, and details.
    """
    metadata = metadata or {}
    frontmatter = _extract_frontmatter(content)
    merged_metadata = {**frontmatter, **metadata}
    body = _strip_frontmatter(content)

    checks = {
        "direct_answer": _check_direct_answer(body, merged_metadata),
        "capsule_coverage": _check_capsule_coverage(body),
        "faq_questions": _check_faq_questions(body),
        "faq_answer_length": _check_faq_answer_lengths(body),
        "external_sources": _check_external_sources(content),
        "metadata": _check_metadata(merged_metadata),
        "eeat_proof": _check_eeat_proof(content, body, merged_metadata),
        "faq_proof": _check_faq_proof(content),
    }
    section_clarity = _check_section_clarity(body)

    weights = {
        "direct_answer": 20,
        "capsule_coverage": 20,
        "faq_questions": 15,
        "faq_answer_length": 15,
        "external_sources": 5,
        "metadata": 5,
        "eeat_proof": 10,
        "faq_proof": 10,
    }

    score = sum(weights[name] if check["passed"] else 0 for name, check in checks.items())
    issues = []
    for name, check in checks.items():
        if not check["passed"]:
            issues.append(
                {
                    "check": name,
                    "issue": check["issue"],
                    "fix": check["fix"],
                    "severity": check["severity"],
                }
            )

    return {
        "score": score,
        "passed": (
            score >= PASS_THRESHOLD
            and checks["eeat_proof"]["passed"]
            and checks["faq_proof"]["passed"]
        ),
        "threshold": PASS_THRESHOLD,
        "checks": checks,
        "issues": issues,
        "details": {
            "h2_count": checks["capsule_coverage"]["details"]["h2_count"],
            "capsule_count": checks["capsule_coverage"]["details"]["capsule_count"],
            "faq_question_count": checks["faq_questions"]["details"]["question_count"],
            "external_link_count": checks["external_sources"]["details"]["external_link_count"],
            "case_study_links": checks["eeat_proof"]["details"]["case_study_links"],
            "review_site_links": checks["eeat_proof"]["details"]["review_site_links"],
            "experience_signals": checks["eeat_proof"]["details"]["experience_signals"],
            "expertise_signals": checks["eeat_proof"]["details"]["expertise_signals"],
            "faq_proof_findings": checks["faq_proof"]["details"]["findings"],
            "section_clarity": section_clarity,
        },
    }


def _extract_frontmatter(content: str) -> Dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*", content, re.DOTALL)
    if not match:
        return {}

    metadata = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[_normalize_key(key)] = value.strip().strip('"')
    return metadata


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_").replace("-", "_")


def _strip_frontmatter(content: str) -> str:
    return re.sub(r"\A---\s*\n.*?\n---\s*", "", content, flags=re.DOTALL).strip()


def _plain_text(markdown: str) -> str:
    text = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`>]", "", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def _extract_markdown_links(content: str) -> List[Tuple[str, str]]:
    return [
        (match.group(1).strip(), match.group(2).strip())
        for match in re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", content)
    ]


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _sentences(text: str) -> List[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]


def _first_body_paragraph(body: str) -> str:
    lines = body.splitlines()
    paragraphs = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if stripped.startswith("#") or stripped.startswith(">") or stripped.startswith("- "):
            continue
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs[0] if paragraphs else ""


def _check_direct_answer(body: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    paragraph = _first_body_paragraph(body)
    first_two = " ".join(_sentences(paragraph)[:2])
    text_lower = first_two.lower()
    primary_keyword = str(metadata.get("primary_keyword", "")).lower().strip()
    main_question = str(metadata.get("main_question", "")).lower().strip()
    topic = str(metadata.get("topic", "")).lower().strip()
    targets = [target for target in [primary_keyword, main_question, topic] if target]

    includes_target = any(target in text_lower for target in targets)
    concise = 12 <= _word_count(first_two) <= 90
    answer_like = bool(
        re.search(
            r"\b(is|are|helps|means|should|gives|reduces|connects|provides|allows|enables)\b",
            text_lower,
        )
    )

    passed = bool(first_two and includes_target and concise and answer_like)
    return {
        "passed": passed,
        "issue": "The article does not directly answer the target query in the first 1-2 sentences.",
        "fix": "Start with a concise answer that names the target query or primary keyword before the hook.",
        "severity": "high",
        "details": {
            "first_two_sentences": first_two,
            "word_count": _word_count(first_two),
            "includes_target": includes_target,
        },
    }


def _extract_h2_sections(body: str) -> List[Tuple[str, str]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, re.MULTILINE))
    sections = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append((match.group(1).strip(), body[start:end].strip()))

    return sections


def _first_paragraph(section_body: str) -> str:
    lines = section_body.splitlines()
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                break
            continue
        if stripped.startswith("#") or stripped.startswith(">") or stripped.startswith("- "):
            continue
        current.append(stripped)

    return " ".join(current)


def _is_capsule(paragraph: str) -> bool:
    words = _word_count(_plain_text(paragraph))
    if words < 50 or words > 60:
        return False
    sentences = _sentences(_plain_text(paragraph))
    return 2 <= len(sentences) <= 4


def _check_capsule_coverage(body: str) -> Dict[str, Any]:
    sections = [
        (heading, section)
        for heading, section in _extract_h2_sections(body)
        if "frequently asked" not in heading.lower() and heading.lower() != "faq"
    ]
    h2_count = len(sections)
    capsule_count = sum(1 for _, section in sections if _is_capsule(_first_paragraph(section)))
    coverage = capsule_count / h2_count if h2_count else 0
    passed = h2_count > 0 and coverage >= 0.60

    return {
        "passed": passed,
        "issue": "Fewer than 60% of major H2 sections have 50-60 word direct-answer capsules.",
        "fix": "Add a 50-60 word direct-answer paragraph immediately below the H1 and at least 60% of major H2s.",
        "severity": "high",
        "details": {
            "h2_count": h2_count,
            "capsule_count": capsule_count,
            "coverage": round(coverage, 2),
        },
    }


def _extract_faq_questions(body: str) -> List[Tuple[str, str]]:
    faq_match = re.search(
        r"^##\s+(?:Frequently Asked Questions|FAQ)\s*$",
        body,
        re.IGNORECASE | re.MULTILINE,
    )
    if not faq_match:
        return []

    faq_body = body[faq_match.end() :]
    next_h2 = re.search(r"^##\s+", faq_body, re.MULTILINE)
    if next_h2:
        faq_body = faq_body[: next_h2.start()]

    matches = list(re.finditer(r"^###\s+(.+\?)\s*$", faq_body, re.MULTILINE))
    questions = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(faq_body)
        questions.append((match.group(1).strip(), faq_body[start:end].strip()))

    return questions


def _check_faq_questions(body: str) -> Dict[str, Any]:
    questions = _extract_faq_questions(body)
    question_count = len(questions)
    passed = 3 <= question_count <= 5

    return {
        "passed": passed,
        "issue": "The FAQ/PAA section does not include 3-5 natural-language questions.",
        "fix": "Use AnswerSocrates or a PAA export to select 3-5 relevant user questions for the FAQ.",
        "severity": "high",
        "details": {
            "question_count": question_count,
            "questions": [question for question, _ in questions],
        },
    }


def _check_faq_answer_lengths(body: str) -> Dict[str, Any]:
    questions = _extract_faq_questions(body)
    lengths = []
    failing = []

    for question, answer_body in questions:
        paragraph = _first_paragraph(answer_body)
        words = _word_count(_plain_text(paragraph))
        lengths.append({"question": question, "words": words})
        if words < 40 or words > 60:
            failing.append({"question": question, "words": words})

    passed = bool(questions) and not failing
    return {
        "passed": passed,
        "issue": "One or more FAQ answers is outside the 40-60 word AEO snippet range.",
        "fix": "Rewrite each FAQ answer as a 40-60 word direct answer, then add context after it if needed.",
        "severity": "medium",
        "details": {
            "answer_lengths": lengths,
            "failing_answers": failing,
        },
    }


def _check_faq_proof(content: str) -> Dict[str, Any]:
    findings = check_faq_proof(content)
    passed = not findings

    return {
        "passed": passed,
        "issue": "One or more FAQ answers lacks linked proof for its claims.",
        "fix": (
            "Add 1 public proof link inside each FAQ answer, or add a "
            "question-specific Source Map / FAQ Proof Map entry with the exact "
            "FAQ question and public URL. Context file paths alone do not count."
        ),
        "severity": "high",
        "details": {
            "finding_count": len(findings),
            "findings": findings,
        },
    }


def _check_external_sources(content: str) -> Dict[str, Any]:
    links = re.findall(r"\[[^\]]+\]\((https?://[^)]+)\)", content)
    passed = len(links) >= 3
    return {
        "passed": passed,
        "issue": "The article has fewer than three external source-backed links.",
        "fix": "Integrate at least three credible external sources naturally inside supporting sentences.",
        "severity": "medium",
        "details": {
            "external_link_count": len(links),
            "external_links": links,
        },
    }


def _check_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {_normalize_key(str(key)): value for key, value in metadata.items()}
    has_author = bool(normalized.get("author"))
    has_last_updated = bool(
        normalized.get("last_updated")
        or normalized.get("updated")
        or normalized.get("date_updated")
    )
    passed = has_author and has_last_updated

    return {
        "passed": passed,
        "issue": "The draft is missing named author or last-updated metadata.",
        "fix": "Add Author and Last Updated fields to the article frontmatter.",
        "severity": "medium",
        "details": {
            "has_author": has_author,
            "has_last_updated": has_last_updated,
        },
    }


def _check_eeat_proof(
    content: str,
    body: str,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    links = _extract_markdown_links(content)
    normalized = {_normalize_key(str(key)): value for key, value in metadata.items()}

    case_study_links = [
        url for _, url in links if re.search(r"/case-stud(?:y|ies)/", url.lower())
    ]
    review_site_links = [
        url for _, url in links if _is_review_site_link(url)
    ]
    simpro_product_links = [
        url for _, url in links if _is_simpro_product_or_workflow_link(url)
    ]

    experience_signals = []
    if case_study_links:
        experience_signals.append("case_study_link")
    if review_site_links:
        experience_signals.append("review_site_link")
    if _has_review_site_theme(body):
        experience_signals.append("review_site_theme")

    expertise_signals = []
    if normalized.get("author"):
        expertise_signals.append("author_metadata")
    if (
        normalized.get("reviewer")
        or normalized.get("reviewed_by")
        or normalized.get("expert_reviewer")
    ):
        expertise_signals.append("reviewer_metadata")
    if simpro_product_links:
        expertise_signals.append("simpro_product_or_workflow_link")
    if _has_expert_quote(body):
        expertise_signals.append("expert_quote")

    has_experience = bool(experience_signals)
    has_expertise = bool(expertise_signals)
    passed = has_experience and has_expertise

    return {
        "passed": passed,
        "issue": "The draft is missing required E-E-A-T proof for both experience and expertise.",
        "fix": (
            "Add at least one customer-experience signal such as a public case "
            "study or source-backed review-site experience evidence / VoC "
            "theme, and at least one expertise "
            "signal such as author/reviewer metadata, Simpro product/workflow "
            "links, expert quote, or source-backed workflow explanation."
        ),
        "severity": "high",
        "details": {
            "case_study_links": case_study_links,
            "review_site_links": review_site_links,
            "simpro_product_links": simpro_product_links,
            "experience_signals": experience_signals,
            "expertise_signals": expertise_signals,
            "has_experience": has_experience,
            "has_expertise": has_expertise,
        },
    }


def _is_review_site_link(url: str) -> bool:
    lower = url.lower()
    review_domains = (
        "g2.com",
        "capterra.com",
        "softwareadvice.com",
        "getapp.com",
        "trustradius.com",
        "gartner.com",
        "gartnerdigitalmarkets.com",
        "trustpilot.com",
        "apps.apple.com",
        "play.google.com",
    )
    return any(domain in lower for domain in review_domains)


def _is_simpro_product_or_workflow_link(url: str) -> bool:
    lower = url.lower()
    if "simprogroup.com" not in lower:
        return False

    product_paths = (
        "/features/",
        "/solutions/",
        "/industries/",
        "/product/",
        "/products/",
    )
    return any(path in lower for path in product_paths)


def _has_review_site_theme(body: str) -> bool:
    text = _plain_text(body).lower()
    review_surfaces = (
        "g2",
        "capterra",
        "software advice",
        "getapp",
        "trustradius",
        "gartner",
        "trustpilot",
        "app store",
        "google reviews",
    )
    review_terms = (
        "review",
        "reviews",
        "review-site",
        "review site",
        "customer feedback",
        "customer themes",
        "voc",
    )
    return any(surface in text for surface in review_surfaces) and any(
        term in text for term in review_terms
    )


def _has_expert_quote(body: str) -> bool:
    quote_pattern = r'"[^"]{20,240}"\s*(?:,?\s*(?:said|says|according to|explained|wrote)\b)'
    attribution_pattern = r'(?:said|says|according to|explained|wrote)\s+[^.]{3,80}:\s*"[^"]{20,240}"'
    return bool(
        re.search(quote_pattern, body, re.IGNORECASE)
        or re.search(attribution_pattern, body, re.IGNORECASE)
    )


def _check_section_clarity(body: str) -> Dict[str, Any]:
    sections = _extract_h2_sections(body)
    unclear_sections = []

    for heading, section in sections:
        plain = _plain_text(section)
        word_count = _word_count(plain)
        h3_count = len(re.findall(r"^###\s+", section, re.MULTILINE))
        if word_count > 450 and h3_count == 0:
            unclear_sections.append({"heading": heading, "words": word_count})

    passed = not unclear_sections
    return {
        "passed": passed,
        "issue": "One or more major sections appears to cover too much without H3 structure.",
        "fix": "Keep one clear idea per major section, or split broad sections with focused H3s.",
        "severity": "low",
        "details": {
            "unclear_sections": unclear_sections,
        },
    }
