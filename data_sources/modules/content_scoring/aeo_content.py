"""Focused aeo content scoring."""

from __future__ import annotations

from .aeo_metadata_schema import _check_metadata_quality
from .aeo_text import _contains_ordered_target
from .aeo_text import _extract_h2_sections
from .aeo_text import _first_body_paragraph
from .aeo_text import _first_paragraph
from .aeo_text import _is_capsule
from .aeo_text import _plain_text
from .aeo_text import _sentences
from .aeo_text import _word_count
from collections.abc import Mapping
from data_sources.modules.faq_structure import is_faq_h2
from typing import Any
from typing import Dict
from typing import Optional
import re

def _check_external_source_diagnostic(content: str) -> Dict[str, Any]:
    links = re.findall(r'\[[^\]]+\]\((https?://[^)]+)\)', content)
    return {
        'passed': True,
        'applicable': False,
        'status': 'not_applicable',
        'issue': (
            'External link totals are diagnostic in AEO scoring; release policy '
            'still uses a 2 distinct non-owned authority source baseline.'
        ),
        'fix': (
            'Use 2 distinct non-owned authority sources as the standard-post '
            'baseline. Add further claim-fit sources whenever evidence requires '
            'them, add no quota-only third source, and apply no maximum to '
            'required evidence.'
        ),
        'severity': 'info',
        'details': {
            'external_link_count': len(links),
            'external_links': links,
            'reason': (
                'AEO fixed source-count scoring is disabled; release link policy '
                'owns the baseline and claim-level proof gates own additions.'
            ),
        },
    }

def _check_direct_answer(body: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    paragraph = _first_body_paragraph(body)
    first_two = " ".join(_sentences(paragraph)[:2])
    text_lower = _plain_text(first_two).lower().strip()
    primary_keyword = str(metadata.get("primary_keyword", "")).lower().strip()
    main_question = str(metadata.get("main_question", "")).lower().strip()
    topic = str(metadata.get("topic", "")).lower().strip()
    targets = []
    declarative_targets = []
    for target in [primary_keyword, main_question, topic]:
        if not target:
            continue
        targets.append(target)
        definition_match = re.fullmatch(r"what\s+(is|are)\s+(.+?)\??", target)
        if definition_match:
            verb, subject = definition_match.groups()
            declarative_targets.append(f"{subject.strip()} {verb}")

    includes_target = any(
        _contains_ordered_target(text_lower, target)
        for target in targets
    ) or any(
        re.match(rf"^{re.escape(target)}\b", text_lower)
        for target in declarative_targets
    )
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

def _check_capsule_coverage(body: str) -> Dict[str, Any]:
    sections = [
        (heading, section)
        for heading, section in _extract_h2_sections(body)
        if not is_faq_h2(f"## {heading}")
    ]
    h2_count = len(sections)
    section_details = []
    for heading, section in sections:
        paragraph = _plain_text(_first_paragraph(section))
        word_count = _word_count(paragraph)
        sentence_count = len(_sentences(paragraph))
        passed_section = _is_capsule(paragraph)
        if passed_section:
            reason = "First paragraph is a 50-60 word capsule."
        elif word_count < 50 or word_count > 60:
            reason = "First paragraph must contain 50-60 words."
        else:
            reason = "First paragraph must contain 2-4 sentences."
        section_details.append(
            {
                "heading": heading,
                "word_count": word_count,
                "sentence_count": sentence_count,
                "passed": passed_section,
                "reason": reason,
            }
        )
    capsule_count = sum(
        1 for _, section in sections if _is_capsule(_first_paragraph(section))
    )
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
            "sections": section_details,
        },
    }

def _check_external_sources(content: str) -> Dict[str, Any]:
    return _check_external_source_diagnostic(content)

def _check_metadata(
    metadata: Dict[str, Any],
    *,
    finalized_bom: Optional[Mapping[str, Any]] = None,
    assembly_date: Optional[str] = None,
) -> Dict[str, Any]:
    return _check_metadata_quality(
        metadata,
        finalized_bom=finalized_bom,
        assembly_date=assembly_date,
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


__all__ = [
    "_check_external_source_diagnostic",
    "_check_direct_answer",
    "_check_capsule_coverage",
    "_check_external_sources",
    "_check_metadata",
    "_check_section_clarity",
]
