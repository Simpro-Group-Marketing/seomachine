"""Shared risk-tiered proof-link analysis for public blog copy.

The validation sidecar remains the complete machine evidence layer. This
module decides which mapped claims also need a reader-visible citation and
builds one canonical link inventory for guards, scorers, and machine reviews.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    from .faq_structure import detect_faq_structure
    from .frontmatter import FrontmatterError, split_frontmatter
    from .url_validator import UrlValidationSummary, extract_urls
except ImportError:  # pragma: no cover - supports direct script execution.
    from faq_structure import detect_faq_structure
    from frontmatter import FrontmatterError, split_frontmatter
    from url_validator import UrlValidationSummary, extract_urls


CitationMode = Literal[
    "inline_required",
    "section_source_allowed",
    "sidecar_only",
    "proof_not_required",
]
CitationOwner = Literal[
    "faq",
    "numeric_claim",
    "public_research",
    "customer_proof",
    "review_story",
    "fred_authority",
    "named_feature_status",
]


TRACKING_QUERY_KEYS = frozenset(
    {
        "dclid",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "msclkid",
    }
)
GENERIC_ANCHORS = frozenset(
    {"click here", "here", "link", "read more", "source", "this link"}
)
GROUP_OWNED_DOMAINS = {
    "simpro": ("simprogroup.com", "simpro.ai"),
    "clockshark": ("clockshark.com",),
    "bigchange": ("bigchange.com",),
    "aroflo": ("aroflo.com",),
}
LEGAL_OR_TIME_SENSITIVE_RE = re.compile(
    r"(?:\blocal\s+authorit(?:y|ies)\b|\b(?:annual(?:ly)?|availability|code|compliance|deadline|eligible|eligibility|exempt(?:ion|ions|ed)?|flsa|"
    r"expire[ds]?|fee|fees|insurance|law|legal|licen[cs](?:e|ed|ing|es)|must|"
    r"homestead|permit(?:ted|s)?|pricing|recordkeeping|regulat(?:e|ed|es|ion|ions|or|ory)|renew(?:al|ed|s)?|required?|"
    r"rule|rules|safety|statute|tax)\b)",
    re.IGNORECASE,
)
STRICT_PUBLIC_RISK_RE = re.compile(
    r"\b(?:code|compliance|deadline|expire[ds]?|fee|fees|insurance|law|legal|"
    r"licen[cs](?:e|ed|ing|es)|pricing|regulat(?:e|ed|es|ion|ions|or|ory)|"
    r"renew(?:al|ed|s)?|safety|statute|tax)\b",
    re.IGNORECASE,
)
INFERRED_HIGH_RISK_RE = re.compile(
    r"(?:\blocal\s+authorit(?:y|ies)\b|\b(?:cannot|compliance|deadline|expire[ds]?|exempt(?:ion|ions)?|"
    r"flsa|insurance|law|legal|must|only\s+under|permit(?:ted)?|prohibit(?:ed|s)?|"
    r"recordkeeping|"
    r"regulat(?:e|ed|es|ion|ions|or|ory)|renew(?:al|ed|s)?|required?|rule|"
    r"homestead|safety|statute|tax)\b)",
    re.IGNORECASE,
)
LICENSE_DEFINITION_RE = re.compile(
    r"(?:\b(?:credential|designation|licen[cs]e|registration)\b.{0,100}"
    r"\b(?:is|are|means|allows?|permits?)\b|"
    r"\b(?:is|are|means)\b.{0,100}\b(?:credential|designation|licen[cs]e|registration)\b)",
    re.IGNORECASE,
)
MATERIAL_NUMBER_RE = re.compile(
    r"(?:[$£€]\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:%|hours?|days?|years?|"
    r"businesses?|customers?|workers?|employees?|licenses?)\b)",
    re.IGNORECASE,
)
FACT_DRIVEN_RE = re.compile(
    r"\b(?:is|are|means|refers to|requires?|regulates?|regulated|must|law|rule|"
    r"fee|costs?|renew(?:al|ed|s)?|expire[ds]?|recognizes?|agency)\b",
    re.IGNORECASE,
)
RECOMMENDATION_RE = re.compile(
    r"\b(?:should|recommend(?:ed|s)?|consider|choose|avoid)\b",
    re.IGNORECASE,
)
COMPARATIVE_RANKING_RE = re.compile(
    r"\b(?:best|better|leading|top[- ]rated|rank(?:ed|ing|s)?)\b",
    re.IGNORECASE,
)
PURE_ADVICE_START_RE = re.compile(
    r"^(?:please\s+)?(?:apply|ask|before|check|compare|complete|confirm|consult|contact|create|for|"
    r"follow|gather|keep|locate|maintain|match|open|organize|prepare|read|record|"
    r"review|save|select|start|treat|use|verify|visit)\b",
    re.IGNORECASE,
)
ADVICE_FACT_ASSERTION_RE = re.compile(
    r"\b(?:although|because|can|causes?|cannot|despite|drives?|even\s+(?:if|when)|"
    r"helps?|if|improves?|increases?|is|are|leads?\s+to|means|must|prevents?|"
    r"reduces?|refers?\s+to|required?|results?\s+in|unless|when|will)\b",
    re.IGNORECASE,
)
RESOURCE_NAVIGATION_RE = re.compile(
    r"\b(?:account|checklist|details|form|guidance|information|instructions?|office|"
    r"lookup|notes|pages?|portal|record|requirements?|status|website)\b",
    re.IGNORECASE,
)
RECORD_SCOPED_INSTRUCTION_PREFIX_RE = re.compile(
    r"^for\b[^,]{0,80}\brecord,\s*",
    re.IGNORECASE,
)
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FRONTMATTER_BLOCK_RE = re.compile(
    r"\A---[ \t]*\r?\n.*?^---[ \t]*(?:\r?\n|\Z)",
    re.DOTALL | re.MULTILINE,
)
FENCED_CODE_BLOCK_RE = re.compile(
    r"^[ \t]*(?P<fence>`{3,}|~{3,})[^\r\n]*(?:\r?\n|\Z)"
    r".*?^[ \t]*(?P=fence)[ \t]*(?:\r?\n|\Z)",
    re.DOTALL | re.MULTILINE,
)
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
LIST_ITEM_MARKER_RE = re.compile(r"^\s*(?:>\s*)?(?:[-*+]\s+|\d+[.)]\s+)")
MATERIAL_INLINE_PUBLIC_RISK_RE = re.compile(
    r"\b(?:annual(?:ly)?|cannot|compliance|deadline|expire[ds]?|fee|fees|"
    r"insurance|law|legal|must|pricing|prohibit(?:ed|s)?|renew(?:al|ed|s)?|"
    r"rule|rules|safety|statute|tax)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LinkOccurrence:
    url: str
    canonical_url: str
    anchor: str
    line: int
    section: str
    internal: bool
    external: bool
    faq_question: str = ""


@dataclass(frozen=True)
class CitationRequirement:
    mode: CitationMode
    owner: CitationOwner
    reason: str
    line: int
    end_line: int
    section: str
    claim: str
    approved_urls: tuple[str, ...]
    visible_urls: tuple[str, ...]
    faq_question: str = ""


@dataclass(frozen=True)
class RedundantCitation:
    canonical_url: str
    section: str
    lines: tuple[int, ...]


@dataclass(frozen=True)
class ProofLinkReport:
    internal_occurrences: int
    external_occurrences: int
    distinct_internal_urls: tuple[str, ...]
    distinct_external_urls: tuple[str, ...]
    requirements: tuple[CitationRequirement, ...]
    generic_anchors: tuple[LinkOccurrence, ...]
    redundant_citations: tuple[RedundantCitation, ...]
    links: tuple[LinkOccurrence, ...]


@dataclass(frozen=True)
class _ArticleUnit:
    text: str
    line: int
    end_line: int
    section: str
    is_table_row: bool = False


@dataclass(frozen=True)
class _ProofRow:
    kind: str
    claim: str
    claim_type: str
    source_class: str
    url: str
    status: str
    use: str


def canonicalize_link_identity(url: str, *, final_url: str = "") -> str:
    """Return a stable URL identity without tracking or fragment variance."""
    candidate = (final_url or url or "").strip()
    if not candidate:
        return ""
    parsed = urlsplit(candidate)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if scheme not in {"http", "https"} or not hostname:
        return candidate

    try:
        port = parsed.port
    except ValueError:
        return candidate
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    path = parsed.path or ""
    if path == "/":
        path = ""
    elif path.endswith("/"):
        path = path.rstrip("/")

    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.casefold()
        if lowered.startswith("utm_") or lowered in TRACKING_QUERY_KEYS:
            continue
        query_items.append((key, value))
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, netloc, path, query, ""))


def analyze_proof_links(
    article_content: str,
    proof_content: str = "",
    *,
    brand: str | None = None,
    url_summary: UrlValidationSummary | None = None,
) -> ProofLinkReport:
    """Classify proof-link requirements and return one canonical inventory."""
    resolved_brand = brand or _article_brand(article_content)
    links = _link_occurrences(
        article_content,
        brand=resolved_brand,
        url_summary=url_summary,
    )
    units = tuple(_article_units(article_content))
    proof_rows = tuple(_proof_rows(proof_content))

    requirements: list[CitationRequirement] = []
    matched_claims_by_unit: dict[tuple[int, int], list[str]] = {}
    for proof in proof_rows:
        if proof.kind == "faq" or proof.status.casefold() != "approved":
            continue
        unit = _matching_unit(proof.claim, units)
        if unit is None:
            continue
        matched_claims_by_unit.setdefault((unit.line, unit.end_line), []).append(
            proof.claim
        )
        mode, owner, reason = _classify_proof_row(proof)
        approved_urls = _canonical_urls((proof.url,), url_summary=url_summary)
        link_scope = _links_for_unit(links, unit) if mode == "inline_required" else _links_for_section(links, unit.section)
        visible_urls = tuple(
            sorted(
                {
                    link.canonical_url
                    for link in link_scope
                    if link.canonical_url in approved_urls
                }
            )
        )
        requirements.append(
            CitationRequirement(
                mode=mode,
                owner=owner,
                reason=reason,
                line=unit.line,
                end_line=unit.end_line,
                section=unit.section,
                claim=proof.claim,
                approved_urls=approved_urls,
                visible_urls=visible_urls,
            )
        )

    faq_lines = {
        line_number
        for entry in detect_faq_structure(article_content).entries
        for line_number in range(
            entry.answer_line,
            entry.answer_line + max(1, entry.answer.count("\n") + 1),
        )
    }
    for unit in units:
        if any(line_number in faq_lines for line_number in range(unit.line, unit.end_line + 1)):
            continue
        claim = _plain_text(unit.text)
        residual_claim = _remove_mapped_claims(
            claim,
            matched_claims_by_unit.get((unit.line, unit.end_line), ()),
        )
        if not residual_claim:
            continue
        if _is_pure_navigation_or_advice(residual_claim):
            requirements.append(
                CitationRequirement(
                    mode="proof_not_required",
                    owner="public_research",
                    reason="navigation_or_nonfactual_advice",
                    line=unit.line,
                    end_line=unit.end_line,
                    section=unit.section,
                    claim=residual_claim,
                    approved_urls=(),
                    visible_urls=(),
                )
            )
            continue
        if MATERIAL_NUMBER_RE.search(residual_claim):
            owner: CitationOwner = "numeric_claim"
            reason = "material_numeric_claim"
        elif (
            INFERRED_HIGH_RISK_RE.search(residual_claim)
            or LICENSE_DEFINITION_RE.search(residual_claim)
            or COMPARATIVE_RANKING_RE.search(residual_claim)
        ):
            owner = "public_research"
            reason = "high_risk_public_claim_without_matching_proof"
        else:
            continue
        link_scope = _links_for_unit(links, unit)
        visible_urls = (
            ()
            if proof_content.strip()
            else tuple(
                sorted(
                    {
                        link.canonical_url
                        for link in link_scope
                        if link.external
                    }
                )
            )
        )
        requirements.append(
            CitationRequirement(
                mode="inline_required",
                owner=owner,
                reason=reason,
                line=unit.line,
                end_line=unit.end_line,
                section=unit.section,
                claim=residual_claim,
                approved_urls=(),
                visible_urls=visible_urls,
            )
        )

    faq_sources = _faq_proof_sources(proof_content)
    for entry in detect_faq_structure(article_content).entries:
        first_paragraph = _first_visible_paragraph(entry.answer)
        approved_urls = _canonical_urls(
            faq_sources.get(entry.question, ()),
            url_summary=url_summary,
        )
        first_urls = _canonical_urls(
            (extracted.url for extracted in extract_urls(first_paragraph)),
            url_summary=url_summary,
        )
        if _faq_is_fact_driven(entry.question, entry.answer):
            mode: CitationMode = "inline_required"
            reason = "fact_driven_faq"
        elif RECOMMENDATION_RE.search(first_paragraph):
            mode = "sidecar_only"
            reason = "editorial_recommendation"
        else:
            mode = "proof_not_required"
            reason = "navigation_or_nonfactual_advice"
        visible_urls = (
            tuple(url for url in first_urls if url in approved_urls)
            if proof_content.strip()
            else first_urls
        )
        requirements.append(
            CitationRequirement(
                mode=mode,
                owner="faq",
                reason=reason,
                line=entry.answer_line,
                end_line=entry.answer_line + first_paragraph.count("\n"),
                section="Frequently asked questions",
                claim=_plain_text(first_paragraph),
                approved_urls=approved_urls,
                visible_urls=visible_urls,
                faq_question=entry.question,
            )
        )

    generic = tuple(
        link for link in links if link.external and is_generic_proof_anchor(link.anchor)
    )
    redundant = _redundant_citations(links, requirements)
    internal_urls = tuple(sorted({link.canonical_url for link in links if link.internal}))
    external_urls = tuple(sorted({link.canonical_url for link in links if link.external}))
    return ProofLinkReport(
        internal_occurrences=sum(1 for link in links if link.internal),
        external_occurrences=sum(1 for link in links if link.external),
        distinct_internal_urls=internal_urls,
        distinct_external_urls=external_urls,
        requirements=tuple(sorted(requirements, key=lambda row: (row.line, row.owner, row.claim))),
        generic_anchors=generic,
        redundant_citations=redundant,
        links=links,
    )


def _link_occurrences(
    article_content: str,
    *,
    brand: str | None,
    url_summary: Optional[UrlValidationSummary],
) -> tuple[LinkOccurrence, ...]:
    section_by_line, faq_by_line = _line_context(article_content)
    occurrences: list[LinkOccurrence] = []
    for extracted in extract_urls(_reader_visible_link_source(article_content)):
        final_url = ""
        if url_summary is not None:
            result = next(
                (
                    item
                    for item in url_summary.results
                    if canonicalize_link_identity(item.url)
                    == canonicalize_link_identity(extracted.url)
                ),
                None,
            )
            if result is not None and result.status == "resolved":
                final_url = result.final_url
        canonical = canonicalize_link_identity(extracted.url, final_url=final_url)
        if not canonical.startswith(("http://", "https://")):
            continue
        hostname = (urlsplit(canonical).hostname or "").lower()
        relationship = _domain_relationship(hostname, brand)
        occurrences.append(
            LinkOccurrence(
                url=extracted.url,
                canonical_url=canonical,
                anchor=extracted.anchor.strip(),
                line=extracted.line,
                section=section_by_line.get(extracted.line, "intro"),
                internal=relationship == "internal",
                external=relationship == "external",
                faq_question=faq_by_line.get(extracted.line, ""),
            )
        )
    return tuple(sorted(occurrences, key=lambda link: (link.line, link.canonical_url)))


def _reader_visible_link_source(article_content: str) -> str:
    """Blank non-reader-visible spans without changing original line numbers."""
    visible = FRONTMATTER_BLOCK_RE.sub(_blank_non_newline, article_content, count=1)
    visible = HTML_COMMENT_RE.sub(_blank_non_newline, visible)
    visible = FENCED_CODE_BLOCK_RE.sub(_blank_non_newline, visible)
    return MARKDOWN_IMAGE_RE.sub(_blank_non_newline, visible)


def _blank_non_newline(match: re.Match[str]) -> str:
    return re.sub(r"[^\r\n]", " ", match.group(0))


def _domain_relationship(hostname: str, brand: str | None) -> str:
    brand_key = (brand or "Simpro").strip().casefold()
    owned = GROUP_OWNED_DOMAINS.get(brand_key, GROUP_OWNED_DOMAINS["simpro"])
    if any(hostname == domain or hostname.endswith(f".{domain}") for domain in owned):
        return "internal"
    all_group_domains = tuple(
        domain for domains in GROUP_OWNED_DOMAINS.values() for domain in domains
    )
    if any(hostname == domain or hostname.endswith(f".{domain}") for domain in all_group_domains):
        return "group_owned"
    return "external"


def _article_brand(article_content: str) -> str | None:
    try:
        metadata, _body, _line = split_frontmatter(article_content)
    except FrontmatterError:
        return None
    value = metadata.get("brand")
    return value if isinstance(value, str) and value.strip() else None


def _line_context(article_content: str) -> tuple[dict[int, str], dict[int, str]]:
    lines = article_content.splitlines()
    section = "intro"
    section_by_line: dict[int, str] = {}
    for line_number, line in enumerate(lines, start=1):
        match = H2_RE.match(line.strip())
        if match:
            section = match.group(1).strip()
        section_by_line[line_number] = section

    faq_by_line: dict[int, str] = {}
    for entry in detect_faq_structure(article_content).entries:
        answer_lines = max(1, entry.answer.count("\n") + 1)
        for line_number in range(entry.answer_line, entry.answer_line + answer_lines):
            faq_by_line[line_number] = entry.question
    return section_by_line, faq_by_line


def _article_units(article_content: str) -> list[_ArticleUnit]:
    try:
        _, body, body_start_line = split_frontmatter(article_content)
    except FrontmatterError:
        legacy_match = re.match(r"\A---\s*\n.*?\n---\s*", article_content, re.DOTALL)
        if legacy_match is None:
            raise
        body = article_content[legacy_match.end():]
        body_start_line = legacy_match.group(0).count("\n") + 1
    lines = body.splitlines()
    units: list[_ArticleUnit] = []
    section = "intro"
    paragraph: list[str] = []
    paragraph_line = body_start_line

    def flush(end_line: int) -> None:
        nonlocal paragraph, paragraph_line
        if paragraph:
            text = "\n".join(paragraph).strip()
            text = HTML_COMMENT_RE.sub("", text)
            text = MARKDOWN_IMAGE_RE.sub("", text).strip()
            if text and not text.startswith("#"):
                units.append(
                    _ArticleUnit(
                        text=text,
                        line=paragraph_line,
                        end_line=end_line,
                        section=section,
                    )
                )
        paragraph = []

    for index, line in enumerate(lines):
        offset = body_start_line + index
        h2 = H2_RE.match(line.strip())
        if h2:
            flush(offset - 1)
            section = h2.group(1).strip()
            continue
        if LIST_ITEM_MARKER_RE.match(line):
            flush(offset - 1)
            text = _strip_list_marker(line).strip()
            text = HTML_COMMENT_RE.sub("", text)
            text = MARKDOWN_IMAGE_RE.sub("", text).strip()
            if text:
                units.append(
                    _ArticleUnit(
                        text=text,
                        line=offset,
                        end_line=offset,
                        section=section,
                    )
                )
            continue
        if line.strip().startswith("|") and line.strip().endswith("|"):
            flush(offset - 1)
            next_is_separator = (
                index + 1 < len(lines)
                and bool(TABLE_SEPARATOR_RE.match(lines[index + 1].strip()))
            )
            if not TABLE_SEPARATOR_RE.match(line.strip()) and not next_is_separator:
                units.append(
                    _ArticleUnit(
                        text=line.strip(),
                        line=offset,
                        end_line=offset,
                        section=section,
                        is_table_row=True,
                    )
                )
            continue
        if not line.strip():
            flush(offset - 1)
            continue
        if not paragraph:
            paragraph_line = offset
        paragraph.append(line)
    flush(body_start_line + len(lines) - 1)
    return units


def _proof_rows(proof_content: str) -> list[_ProofRow]:
    rows: list[_ProofRow] = []
    for raw_line in proof_content.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("-") or ":" not in stripped:
            continue
        fields: dict[str, str] = {}
        for segment in stripped[1:].split("|"):
            key, separator, value = segment.partition(":")
            if separator:
                fields[key.strip().casefold()] = value.strip()
        kind = ""
        claim = ""
        for candidate in ("claim", "approved metric", "approved quote"):
            if fields.get(candidate):
                kind = candidate
                claim = fields[candidate]
                break
        if not claim:
            continue
        rows.append(
            _ProofRow(
                kind=kind,
                claim=claim,
                claim_type=fields.get("claim type", "").casefold(),
                source_class=fields.get("source class", "").casefold(),
                url=fields.get("url", ""),
                status=fields.get("status", "").casefold(),
                use=fields.get("use", "").casefold(),
            )
        )
    return rows


def _faq_proof_sources(proof_content: str) -> dict[str, tuple[str, ...]]:
    rows: dict[str, list[str]] = {}
    for raw_line in proof_content.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("- FAQ:"):
            continue
        fields: dict[str, str] = {}
        for segment in stripped[1:].split("|"):
            key, separator, value = segment.partition(":")
            if separator:
                fields[key.strip().casefold()] = value.strip()
        question = fields.get("faq", "")
        url = fields.get("url", "")
        if question and url:
            rows.setdefault(question, []).append(url)
    return {question: tuple(urls) for question, urls in rows.items()}


def _matching_unit(claim: str, units: tuple[_ArticleUnit, ...]) -> _ArticleUnit | None:
    normalized_claim = _normalize_text(claim)
    matches = [unit for unit in units if normalized_claim in _normalize_text(unit.text)]
    return matches[0] if matches else None


def _classify_proof_row(
    proof: _ProofRow,
) -> tuple[CitationMode, CitationOwner, str]:
    high_risk_numeric = bool(MATERIAL_NUMBER_RE.search(proof.claim))
    high_risk_public = bool(LEGAL_OR_TIME_SENSITIVE_RE.search(proof.claim))
    use = proof.use.casefold()
    source_class = proof.source_class.casefold()

    if source_class == "fred_authority" or "fred" in use:
        return "inline_required", "fred_authority", "fred_authority_proof"
    if source_class == "named_feature_status" or "named feature" in use:
        return "inline_required", "named_feature_status", "named_feature_status"
    if source_class in {"review_platform", "review_story"} or "review" in use:
        return "inline_required", "review_story", "review_proof"
    if proof.kind == "approved quote":
        return "inline_required", "customer_proof", "customer_quote_proof"
    if source_class in {"customer_proof", "customer_story", "case_study"} or "customer" in use:
        return "inline_required", "customer_proof", "customer_or_review_proof"
    if proof.claim_type == "recommendation" and not high_risk_numeric:
        if _is_pure_navigation_or_advice(proof.claim):
            return "sidecar_only", "public_research", "editorial_recommendation"
        if not STRICT_PUBLIC_RISK_RE.search(proof.claim):
            return "sidecar_only", "public_research", "editorial_recommendation"
    if high_risk_numeric:
        return "inline_required", "numeric_claim", "material_numeric_claim"
    if proof.claim_type in {"definition", "definitional", "process"}:
        if MATERIAL_INLINE_PUBLIC_RISK_RE.search(proof.claim):
            return "inline_required", "public_research", "high_risk_public_claim"
        return "section_source_allowed", "public_research", "lower_risk_background_claim"
    if high_risk_public or proof.claim_type in {"causal", "comparative"}:
        return "inline_required", "public_research", "high_risk_public_claim"
    if proof.source_class == "owned_product" or proof.claim_type == "recommendation":
        return "sidecar_only", "public_research", "low_risk_owned_or_editorial_claim"
    return "inline_required", "public_research", "ambiguous_claim_fails_closed"


def _links_for_unit(
    links: tuple[LinkOccurrence, ...], unit: _ArticleUnit
) -> tuple[LinkOccurrence, ...]:
    return tuple(link for link in links if unit.line <= link.line <= unit.end_line)


def _links_for_section(
    links: tuple[LinkOccurrence, ...], section: str
) -> tuple[LinkOccurrence, ...]:
    return tuple(link for link in links if link.section == section and not link.faq_question)


def _first_visible_paragraph(answer: str) -> str:
    paragraphs = re.split(r"\n\s*\n", answer.strip())
    return next((paragraph.strip() for paragraph in paragraphs if paragraph.strip()), "")


def _faq_is_fact_driven(question: str, answer: str) -> bool:
    first_paragraph = _first_visible_paragraph(answer)
    text = f"{question} {answer}"
    if LEGAL_OR_TIME_SENSITIVE_RE.search(text) or MATERIAL_NUMBER_RE.search(text):
        return True
    if COMPARATIVE_RANKING_RE.search(text):
        return True
    if RECOMMENDATION_RE.search(f"{question} {first_paragraph}"):
        return False
    lowered_question = question.casefold()
    if re.match(
        r"^(?:where|how) can (?:i|we|you) (?:start|find|open|go|access)\b",
        lowered_question,
    ):
        return False
    if lowered_question.startswith(
        (
            "what is",
            "what are",
            "what does",
            "who ",
            "when ",
            "where ",
            "which ",
            "does",
            "is ",
            "are ",
            "can ",
            "do ",
            "has ",
            "have ",
            "will ",
        )
    ):
        return True
    if re.match(r"^how (?:does|do) (?!i\b|we\b|you\b)", lowered_question):
        return True
    return bool(FACT_DRIVEN_RE.search(first_paragraph))


def _plain_text(text: str) -> str:
    return MARKDOWN_LINK_RE.sub(lambda match: match.group(1), text).strip()


def _strip_list_marker(text: str) -> str:
    return LIST_ITEM_MARKER_RE.sub("", text, count=1)


def _normalize_text(text: str) -> str:
    plain = _plain_text(text)
    return re.sub(r"\s+", " ", plain).strip().casefold().rstrip(".")


def _remove_mapped_claims(claim: str, mapped_claims) -> str:
    residual = claim
    for mapped_claim in mapped_claims:
        plain = _plain_text(str(mapped_claim)).strip()
        if plain:
            residual = re.sub(re.escape(plain), " ", residual, count=1, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", residual).strip(" .,;:-")


def _is_pure_navigation_or_advice(text: str) -> bool:
    """Return true only for direct actions with no asserted public fact."""
    plain = _plain_text(text).strip()
    start_text = RECORD_SCOPED_INSTRUCTION_PREFIX_RE.sub("", plain, count=1)
    if not PURE_ADVICE_START_RE.match(start_text):
        return False
    if MATERIAL_NUMBER_RE.search(plain):
        return False
    if ADVICE_FACT_ASSERTION_RE.search(plain):
        return False
    if COMPARATIVE_RANKING_RE.search(plain):
        return False
    if LEGAL_OR_TIME_SENSITIVE_RE.search(plain):
        return bool(RESOURCE_NAVIGATION_RE.search(plain))
    return True


def _canonical_urls(
    urls,
    *,
    url_summary: Optional[UrlValidationSummary] = None,
) -> tuple[str, ...]:
    def resolved_url(url: str) -> str:
        if url_summary is None:
            return ""
        identity = canonicalize_link_identity(url)
        result = next(
            (
                item
                for item in url_summary.results
                if canonicalize_link_identity(item.url) == identity
                and item.status == "resolved"
            ),
            None,
        )
        return result.final_url if result is not None else ""

    return tuple(
        sorted(
            {
                canonical
                for url in urls
                if (
                    canonical := canonicalize_link_identity(
                        str(url),
                        final_url=resolved_url(str(url)),
                    )
                )
                and canonical.startswith(("http://", "https://"))
            }
        )
    )


def is_generic_proof_anchor(anchor: str) -> bool:
    normalized = re.sub(r"\s+", " ", anchor).strip().casefold()
    return (
        not normalized
        or normalized in GENERIC_ANCHORS
        or normalized == "learn more"
        or normalized.startswith(("http://", "https://"))
        or bool(re.fullmatch(r"\[?\d+\]?", normalized))
    )


def _redundant_citations(
    links: tuple[LinkOccurrence, ...],
    requirements: list[CitationRequirement],
) -> tuple[RedundantCitation, ...]:
    grouped: dict[tuple[str, str], list[LinkOccurrence]] = {}
    for link in links:
        if not link.external or link.faq_question:
            continue
        grouped.setdefault((link.section, link.canonical_url), []).append(link)
    rows = []
    for (section, canonical), occurrences in grouped.items():
        if len(occurrences) <= 1:
            continue
        separate_bindings = {
            (requirement.line, requirement.end_line, requirement.claim)
            for requirement in requirements
            if not requirement.faq_question
            and requirement.mode == "inline_required"
            and requirement.section == section
            and canonical in requirement.visible_urls
        }
        if len(separate_bindings) >= len(occurrences):
            continue
        rows.append(
            RedundantCitation(
                canonical_url=canonical,
                section=section,
                lines=tuple(link.line for link in occurrences),
            )
        )
    return tuple(sorted(rows, key=lambda row: (row.section, row.canonical_url)))
