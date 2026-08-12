from importlib import import_module
from pathlib import Path
import json

from data_sources.modules import article_planner
from data_sources.modules.blog_assembly_contract import atomic_write_json, canonical_json_sha256
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.editorial_plan_guard import build_serp_evidence
from tests.test_editorial_runtime_guidance import article_plan


def _rule_ids(findings):
    return {finding['rule_id'] for finding in findings}


def _guard():
    return import_module('data_sources.modules.editorial_plan_guard')


def _bound_serp_evidence(
    root: Path,
    *,
    query: str,
    collected_at: str,
    run_id: str,
    title: str,
    url: str,
    features: list[str],
    must_have_sections: list[str],
):
    raw_path = root / 'research' / f'raw-{run_id}.json'
    capture = attest_mapping({
        'schema': 'simpro-serp-raw-capture/v1',
        'collector': {
            'name': 'research_serp_analysis:dataforseo',
            'version': '1.0.0',
        },
        'query': query,
        'collected_at': collected_at,
        'run_id': run_id,
        'request': {
            'url': 'dataforseo://serp/google/organic/live/advanced',
            'locale': {'language_code': 'en', 'location_code': 2840},
        },
        'raw_response': {
            'organic_results': [{'title': title, 'url': url, 'description': ''}],
            'features': features,
        },
    }, purpose='simpro-serp-raw-capture/v1', workspace_root=root)
    atomic_write_json(raw_path, capture)
    return build_serp_evidence(
        raw_capture_path=raw_path,
        workspace_root=root,
        must_have_sections=must_have_sections,
        competitor_gaps=[],
    )


def test_serp_raw_capture_rejects_wrong_approved_collector_version(tmp_path: Path):
    raw_path = tmp_path / 'research' / 'wrong-version.json'
    capture = attest_mapping({
        'schema': 'simpro-serp-raw-capture/v1',
        'collector': {
            'name': 'research_serp_analysis:dataforseo',
            'version': '9.9.9',
        },
        'query': 'field service scheduling',
        'collected_at': '2026-08-11T14:30:00Z',
        'run_id': 'agency-run-123',
        'request': {
            'url': 'dataforseo://serp/google/organic/live/advanced',
            'locale': {'language_code': 'en', 'location_code': 2840},
        },
        'raw_response': {
            'organic_results': [{
                'title': 'Guide', 'url': 'https://example.com/guide',
                'description': '',
            }],
            'features': [],
        },
    }, purpose='simpro-serp-raw-capture/v1', workspace_root=tmp_path)
    atomic_write_json(raw_path, capture)

    try:
        build_serp_evidence(
            raw_capture_path=raw_path,
            workspace_root=tmp_path,
            must_have_sections=[],
            competitor_gaps=[],
        )
    except ValueError as error:
        assert 'collector' in str(error).casefold()
    else:
        raise AssertionError('wrong collector version must fail closed')


def test_editorial_serp_validation_requires_and_matches_expected_run_id(tmp_path: Path):
    plan_path = tmp_path / 'article-plan.json'
    plan_path.write_text(article_planner.serialize_article_plan(article_plan()), encoding='utf-8')
    evidence = _bound_serp_evidence(
        tmp_path,
        query='field service scheduling',
        collected_at='2026-08-11T14:30:00Z',
        run_id='agency-run-123',
        title='Guide',
        url='https://example.com/guide',
        features=[],
        must_have_sections=[],
    )
    evidence_path = tmp_path / 'research' / 'serp.json'
    atomic_write_json(evidence_path, evidence)

    missing = _guard().check_file(
        plan_path,
        serp_evidence_path=evidence_path,
        assembly_date='2026-08-11',
    )
    wrong = _guard().check_file(
        plan_path,
        serp_evidence_path=evidence_path,
        assembly_date='2026-08-11',
        expected_run_id='different-run',
    )

    assert 'serp_evidence_run_expectation_missing' in _rule_ids(missing)
    assert 'serp_evidence_run_mismatch' in _rule_ids(wrong)


def test_guard_accepts_serialized_article_plan(tmp_path: Path):
    output = tmp_path / 'article-plan.json'
    output.write_text(
        article_planner.serialize_article_plan(article_plan()),
        encoding='utf-8',
    )

    assert _guard().check_file(output) == []


def test_guard_rejects_missing_or_wrong_schema():
    payload = article_plan().to_dict()
    payload.pop('schema')

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_schema_invalid' in _rule_ids(findings)

    payload['schema'] = 'simpro-blog-editorial-plan/v0'
    findings = _guard().check_plan(payload)

    assert 'editorial_plan_schema_invalid' in _rule_ids(findings)


def test_guard_rejects_unknown_top_level_fields():
    payload = article_plan().to_dict()
    payload['invented_policy'] = {'status': 'approved'}

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_unknown_field' in _rule_ids(findings)
    assert any(
        finding.get('location') == '/invented_policy' for finding in findings
    )


def test_guard_rejects_non_contiguous_sections_and_word_total_mismatch():
    payload = article_plan().to_dict()
    payload['sections'][0]['section_number'] = 2
    payload['total_word_target'] = 300

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_section_sequence_invalid' in _rule_ids(findings)
    assert 'editorial_plan_word_total_mismatch' in _rule_ids(findings)


def test_guard_rejects_engagement_references_that_do_not_match_sections():
    payload = article_plan().to_dict()
    payload['engagement_map']['ctas'] = {'soft_resource_action': 1}

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_engagement_mismatch' in _rule_ids(findings)


def test_file_guard_reports_invalid_json_without_crashing(tmp_path: Path):
    output = tmp_path / 'article-plan.json'
    output.write_text('{not-json}\n', encoding='utf-8')

    findings = _guard().check_file(output)

    assert _rule_ids(findings) == {'editorial_plan_json_invalid'}


def test_guard_rejects_missing_reader_contract_field():
    payload = article_plan().to_dict()
    payload['reader_contract'].pop('distinctive_angle')

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_field_invalid' in _rule_ids(findings)
    assert any(
        finding.get('location') == '/reader_contract/distinctive_angle'
        for finding in findings
    )


def test_guard_requires_world_class_editorial_decisions():
    payload = article_plan().to_dict()

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
    payload = article_plan().to_dict()
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


def test_guard_validates_serp_evidence_and_final_article_mapping(tmp_path: Path):
    plan_path = tmp_path / 'research' / 'editorial-plan.json'
    article_path = tmp_path / 'drafts' / 'article.md'
    serp_path = tmp_path / 'research' / 'serp-evidence.json'
    plan_path.parent.mkdir(parents=True)
    article_path.parent.mkdir(parents=True)
    plan = article_plan().to_dict()
    plan['original_contributions'][0]['visible_evidence'] = (
        'A field service scheduling dispatch workflow needs hard constraints.'
    )
    plan['serp_strategy'] = {
        'status': 'resolved',
        'content_type': {
            'observed': 'General Article',
            'selected': 'General Article',
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
        json.dumps(_bound_serp_evidence(
            tmp_path,
            query='field service scheduling',
            collected_at='2026-08-05T12:00:00Z',
            run_id='serp-test-run',
            url='https://example.com/scheduling-guide',
            title='Field service scheduling guide',
            features=['featured snippet'],
            must_have_sections=['scheduling constraints'],
        )),
        encoding='utf-8',
    )

    assert _guard().check_file(
        plan_path,
        article_path=article_path,
        serp_evidence_path=serp_path,
        assembly_date='2026-08-05',
        expected_run_id='serp-test-run',
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
        expected_run_id='serp-test-run',
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
        expected_run_id='run-123',
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
        expected_run_id='run-123',
    ))

    assert 'serp_evidence_shape_invalid' in rules
    assert 'serp_evidence_hash_invalid' in rules


def test_plain_rehashed_serp_json_cannot_mint_verified_collection(tmp_path: Path):
    path = tmp_path / 'serp.json'
    payload = _bound_serp_evidence(
        tmp_path,
        query='field service scheduling',
        collected_at='2026-08-11T12:00:00Z',
        run_id='serp-run-1',
        url='https://example.org/guide',
        title='Scheduling guide',
        features=[],
        must_have_sections=['Scheduling workflow'],
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
        expected_run_id='agency-run-123',
    ))

    assert 'serp_evidence_execution_attestation_invalid' in rules


def test_resolved_serp_strategy_cannot_use_empty_decision_maps():
    payload = article_plan().to_dict()
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
    payload = article_plan().to_dict()
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
    payload = article_plan().to_dict()
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
    plan = article_plan().to_dict()
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
    payload = article_plan().to_dict()
    payload['date'] = '2026-8-5'

    findings = _guard().check_plan(payload)

    assert 'editorial_plan_date_invalid' in _rule_ids(findings)


def test_plan_date_must_match_workflow_and_article_dates(tmp_path: Path):
    plan_path = tmp_path / 'editorial-plan.json'
    article_path = tmp_path / 'article.md'
    plan_path.write_text(json.dumps(article_plan().to_dict()), encoding='utf-8')
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
            expected_run_id='run-123',
        )

        assert any(
            finding['rule_id'] == 'serp_evidence_field_invalid'
            and finding['location'] == '/collected_at'
            for finding in findings
        ), timestamp


def test_down_funnel_plan_rejects_external_target_and_accepts_owned_target():
    payload = article_plan().to_dict()
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
