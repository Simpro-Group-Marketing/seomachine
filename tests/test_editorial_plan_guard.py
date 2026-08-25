from importlib import import_module
from pathlib import Path
import json

import pytest

from data_sources.modules.blog_assembly_contract import canonical_json_sha256
from data_sources.modules.editorial_plan_guard import build_serp_evidence


def _rule_ids(findings):
    return {finding['rule_id'] for finding in findings}


def _guard():
    return import_module('data_sources.modules.editorial_plan_guard')


def article_plan():
    return {
        'schema': 'simpro-blog-editorial-plan/v1',
        'topic': 'Field service scheduling',
        'date': '2026-08-05',
        'meta': {
            'title_options': ['Field Service Scheduling Guide'],
            'meta_title': 'Field Service Scheduling Guide for Teams | Simpro',
            'meta_description': (
                'Field service scheduling guidance for teams balancing job priority, '
                'technician skills, travel constraints, and customer commitments.'
            ),
            'url_slug': 'field-service-scheduling-guide',
            'primary_keyword': 'field service scheduling',
            'secondary_keywords': ['dispatch workflow'],
        },
        'keyword_decision': {
            'status': 'resolved',
            'artifact_schema': 'simpro-semrush-keyword-decision/v1',
            'source': 'semrush_connector',
            'database': 'us',
            'selected_primary_keyword': 'field service scheduling',
            'selected_secondary_keywords': ['dispatch workflow'],
            'selection_rationale': 'The selected keyword matches reader intent and page ownership.',
        },
        'total_word_target': 275,
        'sections': [
            {
                'section_number': 1,
                'type': 'intro',
                'heading': 'Scheduling constraints',
                'word_target': 275,
                'strategic_angle': 'Start with the dispatch decision',
                'engagement_hook': None,
                'knowledge_gaps': [],
                'unique_data': [],
                'internal_links': [],
                'cta': None,
                'next_action': None,
                'mini_story': False,
                'featured_snippet': False,
            }
        ],
        'engagement_map': {
            'mini_stories': [],
            'ctas': {},
            'featured_snippets': [],
            'next_actions': {},
            'cta_exception_reason': 'No CTA is needed for this single-section fixture.',
        },
        'gap_mapping': {},
        'insight_mapping': {},
        'reader_contract': {
            'primary_reader': 'Field service operations manager',
            'sophistication_level': 'Intermediate; understands scheduling basics',
            'trigger_problem': 'Recurring dispatch conflicts',
            'existing_belief': 'More scheduling rules will solve the problem',
            'decision_task_helped': 'Choose a practical scheduling workflow',
            'distinctive_angle': 'Separate hard constraints from judgment calls',
            'promised_payoff': 'A workflow the reader can test this month',
            'funnel_stage': 'tofu',
            'exclusions': ['Vendor rankings', 'Unsupported ROI claims'],
        },
        'serp_strategy': {
            'status': 'unresolved_no_verified_serp_context',
            'content_type': {
                'observed': None,
                'selected': None,
                'status': 'not_claimed',
            },
            'serp_features': {},
            'serp_structure': {},
            'competitor_gaps': {},
            'exception_reasons': {
                'content_type': {},
                'serp_features': {},
                'serp_structure': {},
                'competitor_gaps': {},
            },
        },
        'original_contributions': [
            {
                'description': 'Constraint-first scheduling checklist',
                'final_section': 'Scheduling constraints',
                'visible_evidence': 'Match urgent work to current technician capacity',
            }
        ],
        'entity_map': {
            'primary': ['field service scheduling'],
            'supporting': ['dispatch workflow'],
        },
        'query_ownership': {
            'decision': 'clear',
            'rationale': 'No existing owned page serves the same reader decision.',
        },
        'internal_link_plan': [
            {
                'target': '/field-service-management-software/',
                'role': 'down_funnel',
                'rationale': 'Gives the reader an intent-appropriate product next step.',
            }
        ],
        'faq_policy': {
            'status': 'not_applicable',
            'rationale': 'No FAQ adds a useful decision answer for this plan.',
        },
        'paa_policy': {
            'source_kind': 'answersocrates',
            'query': 'field service scheduling',
            'selected_questions': [],
        },
    }


def test_guard_accepts_serialized_article_plan(tmp_path: Path):
    output = tmp_path / 'article-plan.json'
    output.write_text(
        json.dumps(article_plan(), indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )

    assert _guard().check_file(output) == []


def test_guard_rejects_missing_or_wrong_schema():
    payload = article_plan()
    payload.pop('schema')

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_schema_invalid' in _rule_ids(findings)

    payload['schema'] = 'simpro-blog-editorial-plan/v0'
    findings = _guard().check_plan(payload)

    assert 'editorial_plan_schema_invalid' in _rule_ids(findings)


def test_guard_rejects_unknown_top_level_fields():
    payload = article_plan()
    payload['invented_policy'] = {'status': 'approved'}

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_unknown_field' in _rule_ids(findings)
    assert any(
        finding.get('location') == '/invented_policy' for finding in findings
    )


def test_guard_requires_keyword_decision_reference():
    payload = article_plan()
    payload.pop('keyword_decision')

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_field_invalid' in _rule_ids(findings)
    assert any(
        finding.get('location') == '/keyword_decision'
        for finding in findings
    )


def test_guard_rejects_keyword_decision_that_disagrees_with_meta():
    payload = article_plan()
    payload['keyword_decision']['selected_primary_keyword'] = 'job scheduling software'

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_keyword_decision_mismatch' in _rule_ids(findings)


def test_guard_rejects_non_contiguous_sections_and_word_total_mismatch():
    payload = article_plan()
    payload['sections'][0]['section_number'] = 2
    payload['total_word_target'] = 300

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_section_sequence_invalid' in _rule_ids(findings)
    assert 'editorial_plan_word_total_mismatch' in _rule_ids(findings)


def test_guard_rejects_engagement_references_that_do_not_match_sections():
    payload = article_plan()
    payload['engagement_map']['ctas'] = {'soft_resource_action': 1}

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_engagement_mismatch' in _rule_ids(findings)


def test_file_guard_reports_invalid_json_without_crashing(tmp_path: Path):
    output = tmp_path / 'article-plan.json'
    output.write_text('{not-json}\n', encoding='utf-8')

    findings = _guard().check_file(output)

    assert _rule_ids(findings) == {'editorial_plan_json_invalid'}


def test_guard_rejects_missing_reader_contract_field():
    payload = article_plan()
    payload['reader_contract'].pop('distinctive_angle')

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_field_invalid' in _rule_ids(findings)
    assert any(
        finding.get('location') == '/reader_contract/distinctive_angle'
        for finding in findings
    )


def test_guard_requires_world_class_editorial_decisions():
    payload = article_plan()

    for field in (
        'original_contributions',
        'entity_map',
        'query_ownership',
        'internal_link_plan',
        'faq_policy',
        'paa_policy',
    ):
        broken = dict(payload)
        broken.pop(field)

        findings = _guard().check_plan(broken)

        assert 'editorial_plan_field_invalid' in _rule_ids(findings), field


def test_guard_blocks_owned_query_conflict_and_missing_down_funnel_link():
    payload = article_plan()
    payload['query_ownership'] = {
        'decision': 'blocked',
        'rationale': 'The commercial pillar already owns this intent.',
    }
    payload['internal_link_plan'] = [
        {
            'target': '/resources/scheduling-template/',
            'role': 'supporting',
            'rationale': 'Adds a related resource.',
        }
    ]

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_query_ownership_blocked' in _rule_ids(findings)
    assert 'editorial_plan_down_funnel_link_missing' in _rule_ids(findings)


def test_guard_requires_industry_cluster_policy_for_single_trade_simpro_blog():
    payload = article_plan()
    payload['brand'] = 'Simpro'
    payload['topic'] = 'CRM for electricians'
    payload['meta']['meta_title'] = 'CRM for Electricians | Simpro'
    payload['meta']['primary_keyword'] = 'CRM for electricians'
    payload['keyword_decision']['selected_primary_keyword'] = 'CRM for electricians'
    payload['reader_contract']['primary_reader'] = 'Electrical contractor owner'
    payload['reader_contract']['decision_task_helped'] = (
        'Compare CRM options for electrical contractors'
    )
    payload['internal_link_plan'] = [
        {
            'target': 'https://www.simprogroup.com/features/crm-for-field-service',
            'role': 'down_funnel',
            'rationale': 'Gives the reader a CRM feature next step.',
        }
    ]

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_industry_cluster_link_missing' in _rule_ids(findings)


def test_guard_accepts_required_industry_cluster_policy_for_electrical_blog():
    payload = article_plan()
    payload['brand'] = 'Simpro'
    payload['topic'] = 'CRM for electricians'
    payload['meta']['meta_title'] = 'CRM for Electricians | Simpro'
    payload['meta']['primary_keyword'] = 'CRM for electricians'
    payload['keyword_decision']['selected_primary_keyword'] = 'CRM for electricians'
    payload['reader_contract']['primary_reader'] = 'Electrical contractor owner'
    payload['reader_contract']['decision_task_helped'] = (
        'Compare CRM options for electrical contractors'
    )
    payload['internal_link_plan'] = [
        {
            'target': 'https://www.simprogroup.com/features/crm-for-field-service',
            'role': 'down_funnel',
            'rationale': 'Gives the reader a CRM feature next step.',
        },
        {
            'target': 'https://www.simprogroup.com/industries/electrical-software',
            'role': 'down_funnel',
            'rationale': 'Builds the electrical contractor software cluster.',
        },
    ]
    payload['industry_cluster_link_policy'] = {
        'status': 'required',
        'industry': 'electrical',
        'target': 'https://www.simprogroup.com/industries/electrical-software',
        'anchor': 'electrical contractor software',
        'placement': 'intro_first_300_words',
        'vault_vertical_query': (
            'electrical contractor software industry page vertical profile '
            'Simpro industries electrical-software'
        ),
        'required_resource_ids': ['res-25a1152f611e5cd69ba57cf16b34a826'],
        'rationale': 'Single-trade Simpro blog should reinforce the electrical industry page.',
    }

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_industry_cluster_link_missing' not in _rule_ids(findings)
    assert 'editorial_plan_industry_cluster_policy_invalid' not in _rule_ids(findings)


def test_guard_validates_serp_evidence_and_final_article_mapping(tmp_path: Path):
    plan_path = tmp_path / 'research' / 'editorial-plan.json'
    article_path = tmp_path / 'drafts' / 'article.md'
    serp_path = tmp_path / 'research' / 'serp-evidence.json'
    plan_path.parent.mkdir(parents=True)
    article_path.parent.mkdir(parents=True)
    plan = article_plan()
    plan['original_contributions'][0]['visible_evidence'] = (
        'A field service scheduling dispatch workflow needs hard constraints.'
    )
    plan['serp_strategy'] = {
        'status': 'resolved',
        'content_type': {
            'observed': 'guide',
            'selected': 'guide',
            'status': 'matched_default',
        },
        'serp_features': {'featured snippet': 'targeted'},
        'serp_structure': {'scheduling constraints': 'included'},
        'competitor_gaps': {},
        'exception_reasons': {
            'serp_features': {},
            'serp_structure': {},
            'competitor_gaps': {},
        },
    }
    plan_path.write_text(json.dumps(plan), encoding='utf-8')
    article_path.write_text(
        '---\nartifact_type: blog\nlast_updated: 2026-08-05\n---\n'
        '# Field service scheduling\n\n'
        '## Scheduling constraints\n\n'
        'A field service scheduling dispatch workflow needs hard constraints.\n\n'
        '[Explore field service software](/field-service-management-software/).\n',
        encoding='utf-8',
    )
    serp_path.write_text(
        json.dumps(build_serp_evidence(
            query='field service scheduling',
            collected_at='2026-08-05T12:00:00Z',
            collector_name='serp_research',
            collector_version='1.0.0',
            run_id='serp-test-run',
            results=[{
                'position': 1,
                'url': 'https://example.com/scheduling-guide',
                'title': 'Field service scheduling guide',
                'result_type': 'organic',
            }],
            content_types=['guide'],
            serp_features=['featured snippet'],
            must_have_sections=['scheduling constraints'],
            competitor_gaps=[],
        )),
        encoding='utf-8',
    )

    assert _guard().check_file(
        plan_path,
        article_path=article_path,
        serp_evidence_path=serp_path,
        assembly_date='2026-08-05',
    ) == []

    article_path.write_text(
        '# Different section\n\nNo planned entities or internal link.\n',
        encoding='utf-8',
    )
    findings = _guard().check_file(
        plan_path,
        article_path=article_path,
        serp_evidence_path=serp_path,
        assembly_date='2026-08-05',
    )

    rules = _rule_ids(findings)
    assert 'editorial_plan_original_contribution_unmapped' in rules
    assert 'editorial_plan_entity_missing' in rules
    assert 'editorial_plan_internal_link_missing' in rules


def test_guard_rejects_stale_or_unverified_serp_evidence(tmp_path: Path):
    serp_path = tmp_path / 'serp.json'
    serp_path.write_text(
        json.dumps(
            {
                'schema': 'simpro-serp-evidence/v1',
                'status': 'collected',
                'query': 'field service scheduling',
                'collected_at': '2026-08-04T12:00:00Z',
            }
        ),
        encoding='utf-8',
    )

    findings = _guard().check_serp_evidence_file(
        serp_path,
        expected_query='field service scheduling',
        assembly_date='2026-08-05',
    )

    rules = _rule_ids(findings)
    assert 'serp_evidence_status_invalid' in rules
    assert 'serp_evidence_stale' in rules


def test_metadata_only_verified_serp_evidence_is_blocking(tmp_path: Path):
    serp_path = tmp_path / 'serp.json'
    serp_path.write_text(
        json.dumps({
            'schema': 'simpro-serp-evidence/v1',
            'status': 'verified',
            'query': 'field service scheduling',
            'collected_at': '2026-08-05T12:00:00Z',
        }),
        encoding='utf-8',
    )

    rules = _rule_ids(_guard().check_serp_evidence_file(
        serp_path,
        expected_query='field service scheduling',
        assembly_date='2026-08-05',
    ))

    assert 'serp_evidence_shape_invalid' in rules
    assert 'serp_evidence_hash_invalid' in rules


def test_plain_rehashed_serp_json_cannot_mint_verified_collection(tmp_path: Path):
    path = tmp_path / 'serp.json'
    payload = build_serp_evidence(
        query='field service scheduling',
        collected_at='2026-08-11T12:00:00Z',
        collector_name='research_serp_analysis:dataforseo',
        collector_version='1.0.0',
        run_id='serp-run-1',
        results=[{
            'position': 1,
            'url': 'https://example.org/guide',
            'title': 'Scheduling guide',
            'result_type': 'organic',
        }],
        content_types=['guide'],
        serp_features=[],
        must_have_sections=['Scheduling workflow'],
        competitor_gaps=[],
    )
    payload.pop('execution_attestation')
    unsigned = dict(payload)
    unsigned.pop('evidence_hash')
    payload['evidence_hash'] = canonical_json_sha256(unsigned)
    path.write_text(json.dumps(payload), encoding='utf-8')

    rules = _rule_ids(_guard().check_serp_evidence_file(
        path,
        expected_query='field service scheduling',
        assembly_date='2026-08-11',
    ))

    assert 'serp_evidence_execution_attestation_invalid' in rules


def test_resolved_serp_strategy_cannot_use_empty_decision_maps():
    payload = article_plan()
    payload['serp_strategy'] = {
        'status': 'resolved',
        'content_type': {
            'observed': 'guide',
            'selected': 'guide',
            'status': 'matched_default',
        },
        'serp_features': {},
        'serp_structure': {},
        'competitor_gaps': {},
        'exception_reasons': {
            'serp_features': {},
            'serp_structure': {},
            'competitor_gaps': {},
        },
    }

    assert 'editorial_plan_serp_strategy_empty' in _rule_ids(
        _guard().check_plan(payload)
    )


def test_original_contribution_requires_visible_evidence_in_mapped_section(
    tmp_path: Path,
):
    plan_path = tmp_path / 'plan.json'
    article_path = tmp_path / 'article.md'
    payload = article_plan()
    payload['original_contributions'][0]['visible_evidence'] = (
        'A benchmark table comparing dispatch utilization by team size.'
    )
    plan_path.write_text(json.dumps(payload), encoding='utf-8')
    article_path.write_text(
        '---\nlast_updated: 2026-08-05\n---\n'
        '# Field service scheduling\n\n'
        '## Scheduling constraints\n\n'
        'This section gives ordinary scheduling background with no benchmark.\n',
        encoding='utf-8',
    )

    rules = _rule_ids(_guard().check_file(
        plan_path,
        article_path=article_path,
        assembly_date='2026-08-05',
    ))

    assert 'editorial_plan_original_contribution_evidence_missing' in rules


def test_faq_and_paa_policy_must_agree():
    payload = article_plan()
    payload['faq_policy'] = {
        'status': 'not_applicable',
        'rationale': 'No useful FAQ.',
    }
    payload['paa_policy']['selected_questions'] = ['What is scheduling?']

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_faq_paa_mismatch' in _rule_ids(findings)


def test_entity_binding_uses_visible_body_and_whole_entity_boundaries(tmp_path: Path):
    plan_path = tmp_path / 'editorial-plan.json'
    article_path = tmp_path / 'article.md'
    plan = article_plan()
    plan['entity_map']['primary'] = ['AI']
    plan_path.write_text(json.dumps(plan), encoding='utf-8')
    article_path.write_text(
        '---\n'
        'artifact_type: blog\n'
        'title: AI scheduling guide\n'
        'last_updated: 2026-08-05\n'
        '---\n'
        '# Field service scheduling\n\n'
        '## Scheduling constraints\n\n'
        'A dispatcher said the dispatch workflow is ready.\n\n'
        '[Explore field service software]('
        '/field-service-management-software/?utm_campaign=ai).\n',
        encoding='utf-8',
    )

    findings = _guard().check_file(
        plan_path,
        article_path=article_path,
        assembly_date='2026-08-05',
    )

    assert any(
        finding['rule_id'] == 'editorial_plan_entity_missing'
        and finding['location'] == '/entity_map/primary/0'
        for finding in findings
    )


def test_plan_date_must_be_canonical_iso_date():
    payload = article_plan()
    payload['date'] = '2026-8-5'

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_date_invalid' in _rule_ids(findings)


def test_plan_date_must_match_workflow_and_article_dates(tmp_path: Path):
    plan_path = tmp_path / 'editorial-plan.json'
    article_path = tmp_path / 'article.md'
    plan_path.write_text(json.dumps(article_plan()), encoding='utf-8')
    article_path.write_text(
        '---\n'
        'artifact_type: blog\n'
        'last_updated: 2026-08-07\n'
        '---\n'
        '# Field service scheduling\n\n'
        '## Scheduling constraints\n\n'
        'Field service scheduling uses a dispatch workflow.\n\n'
        '[Explore field service software](/field-service-management-software/).\n',
        encoding='utf-8',
    )

    findings = _guard().check_file(
        plan_path,
        article_path=article_path,
        assembly_date='2026-08-06',
    )

    rules = _rule_ids(findings)
    assert 'editorial_plan_assembly_date_mismatch' in rules
    assert 'editorial_plan_article_date_mismatch' in rules


def test_serp_timestamp_requires_extended_rfc3339_utc(tmp_path: Path):
    serp_path = tmp_path / 'serp.json'
    invalid_timestamps = (
        '2026-08-05 12:00:00Z',
        '2026-08-05T12:00Z',
        '20260805T120000Z',
        '2026-08-05T12:00:00+00:00',
    )

    for timestamp in invalid_timestamps:
        serp_path.write_text(
            json.dumps(
                {
                    'schema': 'simpro-serp-evidence/v1',
                    'status': 'verified',
                    'query': 'field service scheduling',
                    'collected_at': timestamp,
                }
            ),
            encoding='utf-8',
        )

        findings = _guard().check_serp_evidence_file(
            serp_path,
            expected_query='field service scheduling',
            assembly_date='2026-08-05',
        )

        assert any(
            finding['rule_id'] == 'serp_evidence_field_invalid'
            and finding['location'] == '/collected_at'
            for finding in findings
        ), timestamp


def test_down_funnel_plan_rejects_external_target_and_accepts_same_brand_target():
    payload = article_plan()
    payload['internal_link_plan'][0]['target'] = (
        'https://external.example/features/scheduling/'
    )

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_internal_link_external' in _rule_ids(findings)

    payload['internal_link_plan'][0]['target'] = (
        'https://www.simprogroup.com/features/scheduling/'
    )

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_internal_link_external' not in _rule_ids(findings)


@pytest.mark.parametrize(
    ('brand', 'target'),
    (
        ('AroFlo', 'https://aroflo.com/features/job-estimating'),
        ('BigChange', 'https://www.bigchange.com/job-management-software/'),
        ('ClockShark', 'https://www.clockshark.com/tour/job-management'),
        ('Simpro', 'https://www.simprogroup.com/features/scheduling/'),
    ),
)
def test_down_funnel_plan_accepts_matching_owned_brand_domain(brand: str, target: str):
    payload = article_plan()
    payload['brand'] = brand
    payload['internal_link_plan'][0]['target'] = target

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_internal_link_external' not in _rule_ids(findings)


@pytest.mark.parametrize(
    ('brand', 'cross_brand_target'),
    (
        ('AroFlo', 'https://www.bigchange.com/job-management-software/'),
        ('BigChange', 'https://www.clockshark.com/tour/job-management'),
        ('ClockShark', 'https://www.simprogroup.com/features/scheduling/'),
        ('Simpro', 'https://aroflo.com/features/job-estimating'),
    ),
)
def test_down_funnel_plan_rejects_cross_brand_owned_domain(
    brand: str,
    cross_brand_target: str,
):
    payload = article_plan()
    payload['brand'] = brand
    payload['internal_link_plan'][0]['target'] = cross_brand_target

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_internal_link_external' in _rule_ids(findings)
