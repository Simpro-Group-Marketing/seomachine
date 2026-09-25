"""Editorial-plan schemas, constants, and deterministic finding helpers."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from typing import Any
import re


Finding = dict[str, Any]

EDITORIAL_PLAN_SCHEMA = 'simpro-blog-editorial-plan/v1'
SECTION_TYPES = frozenset(
    {
        'intro',
        'body_how_to',
        'body_comparison',
        'body_explanation',
        'body_list',
        'faq',
        'conclusion',
    }
)
CTA_TYPES = frozenset(
    {
        'soft',
        'medium',
        'strong',
        'soft_resource_action',
        'educational_next_step',
        'contextual_product',
        'commercial_contextual',
        'commercial_comparison',
        'commercial_conversion',
        'thought_leadership_next_action',
    }
)
FUNNEL_STAGES = frozenset({'tofu', 'mofu', 'bofu', 'thought leadership'})
FAQ_SECTION_TYPE = 'faq'
TOP_LEVEL_FIELDS = frozenset(
    {
        'schema',
        'brand',
        'topic',
        'date',
        'meta',
        'total_word_target',
        'sections',
        'engagement_map',
        'gap_mapping',
        'insight_mapping',
        'reader_contract',
        'serp_strategy',
        'original_contributions',
        'entity_map',
        'query_ownership',
        'internal_link_plan',
        'industry_cluster_link_policy',
        'rewrite_decisions',
        'audience_language_research',
        'link_policy_override',
        'keyword_decision',
        'faq_policy',
        'paa_policy',
    }
)
META_FIELDS = frozenset(
    {
        'title_options',
        'meta_title',
        'meta_description',
        'url_slug',
        'primary_keyword',
        'secondary_keywords',
    }
)
READER_CONTRACT_FIELDS = frozenset(
    {
        'primary_reader',
        'sophistication_level',
        'trigger_problem',
        'existing_belief',
        'decision_task_helped',
        'distinctive_angle',
        'promised_payoff',
        'funnel_stage',
        'exclusions',
    }
)
SECTION_FIELDS = frozenset(
    {
        'section_number',
        'type',
        'heading',
        'word_target',
        'strategic_angle',
        'engagement_hook',
        'knowledge_gaps',
        'unique_data',
        'internal_links',
        'cta',
        'next_action',
        'mini_story',
        'featured_snippet',
    }
)
ENGAGEMENT_FIELDS = frozenset(
    {
        'mini_stories',
        'ctas',
        'featured_snippets',
        'next_actions',
        'cta_exception_reason',
    }
)
SERP_STRATEGY_FIELDS = frozenset(
    {
        'status',
        'content_type',
        'serp_features',
        'serp_structure',
        'competitor_gaps',
        'exception_reasons',
    }
)
ORIGINAL_CONTRIBUTION_FIELDS = frozenset(
    {'description', 'final_section', 'visible_evidence'}
)
ENTITY_MAP_FIELDS = frozenset({'primary', 'supporting'})
QUERY_OWNERSHIP_FIELDS = frozenset({'decision', 'rationale'})
INTERNAL_LINK_FIELDS = frozenset({'target', 'role', 'rationale'})
REWRITE_DECISIONS_FIELDS = frozenset({'preserve', 'update', 'add', 'remove'})
AUDIENCE_LANGUAGE_RESEARCH_FIELDS = frozenset(
    {'status', 'rationale', 'source_urls', 'observations', 'intended_section_use'}
)
LINK_POLICY_OVERRIDE_FIELDS = frozenset(
    {'brief_path', 'brief_sha256', 'source_sentence', 'exact_count', 'scope'}
)
FAQ_POLICY_FIELDS = frozenset({'status', 'rationale'})
PAA_POLICY_FIELDS = frozenset({'source_kind', 'query', 'selected_questions'})
KEYWORD_DECISION_FIELDS = frozenset(
    {
        'status',
        'artifact_schema',
        'source',
        'database',
        'selected_primary_keyword',
        'selected_secondary_keywords',
        'selection_rationale',
    }
)
SERP_EVIDENCE_SCHEMA = 'simpro-serp-evidence/v1'
KEYWORD_DECISION_SCHEMA = 'simpro-semrush-keyword-decision/v1'
SERP_EVIDENCE_ATTESTATION_PURPOSE = 'simpro-serp-evidence/v1'
SERP_EVIDENCE_FIELDS = frozenset(
    {
        'schema',
        'status',
        'query',
        'collected_at',
        'collector',
        'run_id',
        'results',
        'observations',
        'raw_capture',
        'execution_attestation',
        'evidence_hash',
    }
)
SERP_RAW_CAPTURE_SCHEMA = 'simpro-serp-raw-capture/v1'
SERP_RAW_CAPTURE_ATTESTATION_PURPOSE = SERP_RAW_CAPTURE_SCHEMA
SERP_RAW_CAPTURE_FIELDS = frozenset({
    'schema', 'collector', 'query', 'collected_at', 'run_id', 'request',
    'raw_response', 'execution_attestation',
})
SERP_APPROVED_COLLECTORS = frozenset({
    ('research_serp_analysis:dataforseo', '1.0.0'),
    ('research_serp_analysis:playwright', '1.0.0'),
    ('research_serp_analysis:semrush', '1.0.0'),
    # Browser connector capture records its own provenance instead of
    # borrowing Playwright's. This mirrors the existing
    # ANSWERSOCRATES_CHROME_CONNECTOR_TOOL precedent in
    # paa_provenance/contracts.py. It is validated against the same Google
    # search URL, English-language, non-personalized locale contract as the
    # Playwright collector.
    ('research_serp_analysis:chrome_connector', '1.0.0'),
})
# Approved SERP capture locales, one per supported market. These mirror
# commercial_pillar_index.ALLOWED_MARKETS so SERP evidence can be captured for
# every market the commercial pillar index already accepts. English-language,
# non-personalized search remains required for every market.
# Google's gl parameter takes ISO 3166-1 alpha-2, where the United Kingdom is
# 'gb'. research_serp_analysis.py passes --google-country straight through to
# gl, and research-serp.md documents the UK run as --google-country gb, so 'gb'
# is the value the collector actually emits. 'uk' is the repo's market label and
# appears in hand-authored captures, so both are accepted here. This set tracks
# the Google parameter vocabulary, not commercial_pillar_index.ALLOWED_MARKETS.
SERP_APPROVED_GOOGLE_COUNTRIES = frozenset({'us', 'gb', 'uk', 'au', 'nz', 'ca', 'ie'})
# Semrush database codes use the repo market vocabulary.
SERP_APPROVED_SEMRUSH_DATABASES = frozenset({'us', 'uk', 'au', 'nz', 'ca', 'ie'})
SERP_APPROVED_DATAFORSEO_LOCATION_CODES = frozenset({
    2840,  # US
    2826,  # UK
    2036,  # AU
    2554,  # NZ
    2124,  # CA
    2372,  # IE
})
SERP_RESULT_FIELDS = frozenset({'position', 'url', 'title', 'result_type'})
SERP_OBSERVATION_FIELDS = frozenset(
    {'content_types', 'serp_features', 'must_have_sections', 'competitor_gaps'}
)
RFC3339_UTC_RE = re.compile(
    r'\A\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?Z\Z'
)
OWNED_INTERNAL_DOMAINS = frozenset(
    {
        'aroflo.com',
        'simprogroup.com',
        'simpro.ai',
        'clockshark.com',
        'bigchange.com',
    }
)
BRAND_INTERNAL_DOMAINS = {
    'aroflo': frozenset({'aroflo.com'}),
    'bigchange': frozenset({'bigchange.com'}),
    'clockshark': frozenset({'clockshark.com'}),
    'simpro': frozenset({'simprogroup.com', 'simpro.ai'}),
}


def _nested_string(value: Mapping[str, Any], parent: str, key: str) -> str:
    row = value.get(parent)
    if not isinstance(row, Mapping):
        return ''
    candidate = row.get(key)
    return candidate.strip() if isinstance(candidate, str) else ''


def _rfc3339_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or RFC3339_UTC_RE.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _invalid_serp_field(location: str, requirement: str) -> Finding:
    return _finding(
        'serp_evidence_field_invalid',
        f'SERP evidence field {location} {requirement}.',
        location,
        'Regenerate the verified SERP evidence artifact.',
    )

def _check_string_list(value: Any, location: str, *, required: bool = False) -> list[Finding]:
    if not isinstance(value, list) or (required and not value) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        qualifier = 'non-empty ' if required else ''
        return [_invalid_field(location, f'must be a {qualifier}list of non-empty strings')]
    return []


def _unknown_fields(
    value: Mapping[str, Any],
    allowed: frozenset[str],
    parent_location: str,
) -> list[Finding]:
    return [
        _finding(
            'editorial_plan_unknown_field',
            f'Editorial plan contains unsupported field {key}.',
            f'{parent_location}/{key}',
            'Remove the field or update the editorial-plan schema deliberately.',
        )
        for key in sorted(set(value) - allowed)
    ]


def _require_nonempty_string(
    value: Mapping[str, Any],
    key: str,
    findings: list[Finding],
    location: str,
) -> None:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate.strip():
        findings.append(_invalid_field(location, 'must be a non-empty string'))


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _invalid_field(location: str, requirement: str) -> Finding:
    return _finding(
        'editorial_plan_field_invalid',
        f'Editorial plan field {location} {requirement}.',
        location,
        'Regenerate the editorial plan from validated planner inputs.',
    )


def _finding(
    rule_id: str,
    message: str,
    location: str,
    suggestion: str,
) -> Finding:
    return {
        'severity': 'error',
        'rule_id': rule_id,
        'message': message,
        'suggestion': suggestion,
        'location': location,
    }


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    unique: dict[tuple[str, str, str], Finding] = {}
    for finding in findings:
        key = (
            str(finding.get('rule_id') or ''),
            str(finding.get('location') or ''),
            str(finding.get('message') or ''),
        )
        unique[key] = finding
    return list(unique.values())


def _sorted_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        _deduplicate(findings),
        key=lambda finding: (
            str(finding.get('location') or ''),
            str(finding.get('rule_id') or ''),
            str(finding.get('message') or ''),
        ),
    )
