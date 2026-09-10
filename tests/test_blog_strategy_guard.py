from datetime import date
import hashlib
from pathlib import Path

import pytest

from data_sources.modules.blog_strategy_contract import validate_contract
from data_sources.modules.blog_strategy_guard import _main, check_content, check_file
from data_sources.modules.commercial_pillar_index import (
    CommercialPillarIndex,
    CommercialPillarRecord,
    load_index,
)
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX = load_index(REPO_ROOT / "context" / "commercial-pillar-index.json")
PILLAR_URL = "https://www.simprogroup.com/"
PILLAR_DESTINATION_ID = "simpro-us-homepage-field-service-management-software"
STRATEGY_TODAY = date(2026, 9, 8)


def sidecar(**replacements: str) -> str:
    values = {
        "primary_query": "field service software checklist",
        "article_keyword": "field service software checklist",
        "pillar_difference": "The article is an informational guide while the pillar is a commercial landing page with different intent and different content type.",
        "cannibalization": "different_intent",
        "anchor": "field service management software",
        "h2": "Choosing field service software",
        "pillar_url": PILLAR_URL,
        "pillar_status": "aligned",
        "search_status": "ready",
        "lifecycle_status": "scheduled",
    }
    values.update(replacements)
    return f"""## Search Intent and Format Decision
- Contract version: blog-strategy-contract/v1
- Primary query or prompt: {values['primary_query']}
- Searcher task: Compare the workflow capabilities to evaluate.
- Intent class: informational
- Funnel stage: MOFU
- SERP evidence artifact: research/serp-field-service-software-checklist-2026-08-06.md
- Dominant content type: guide
- Selected content type: guide
- Observed SERP features: People also ask | featured snippets
- Related-query/PAA artifact: research/paa-field-service-software-checklist-2026-08-06.md
- Format decision: match_dominant
- Exception reason: none
- Status: {values['search_status']}

## Commercial Pillar and Anchor Decision
- Contract version: blog-strategy-contract/v1
- Article title: Field Service Software Checklist
- Article primary keyword: {values['article_keyword']}
- Article intent: informational
- Destination ID: {PILLAR_DESTINATION_ID}
- Commercial pillar URL: {values['pillar_url']}
- Planned anchor text: {values['anchor']}
- Planned H2 section: {values['h2']}
- Existing overlapping URLs checked: https://www.simprogroup.com/blog/best-field-service-management-software
- Pillar-versus-blog intent difference: {values['pillar_difference']}
- Cannibalization decision: {values['cannibalization']}
- Incoming-link candidates: https://www.simprogroup.com/blog/what-is-field-service-management
- Status: {values['pillar_status']}

## Lifecycle Refresh Record
- Contract version: blog-strategy-contract/v1
- Last-updated date: 2026-08-06
- Volatility: standard
- Next review date: 2027-02-01
- Review command: /performance-review published/field-service-software-checklist.md
- GSC lane: unavailable: new article has no post-publication data
- GA4 lane: unavailable: new article has no post-publication data
- Semrush lane: available: destination evidence is in the verified index
- AI-citation lane: unavailable: new article has no post-publication data
- Decision: retain
- Status: {values['lifecycle_status']}
"""


def article(body: str, **frontmatter: str) -> str:
    fields = {
        "title": "Field Service Software Checklist",
        "brand": "Simpro",
        "market": "US",
        "primary_keyword": "field service software checklist",
        "last_updated": "2026-08-06",
    }
    fields.update(frontmatter)
    yaml = "\n".join(f"{key}: {value}" for key, value in fields.items())
    return f"---\n{yaml}\n---\n# Field Service Software Checklist\n\n{body}\n"


def rule_ids(findings: list[dict[str, object]]) -> set[str]:
    return {str(finding["rule_id"]) for finding in findings}


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def industries_hub_index(tmp_path: Path) -> CommercialPillarIndex:
    keyword_path = tmp_path / "target-keywords.md"
    link_path = tmp_path / "internal-links-map.md"
    market_line = "**Source boundary**: Semrush Exact US Keyword Metrics using `phrase_these` with `database=us`."
    keyword_line = "| trades | 10 | 1 |"
    title_line = "### Trades"
    url_line = "- **URL**: https://www.simprogroup.com/industries"
    keyword_path.write_text(f"{market_line}\n{keyword_line}\n", encoding="utf-8")
    link_path.write_text(f"{title_line}\n{url_line}\n", encoding="utf-8")
    return CommercialPillarIndex(
        schema_version="commercial-pillar-index/v1",
        updated_at="2026-08-06",
        source_path=tmp_path / "commercial-pillar-index.json",
        records=(
            CommercialPillarRecord(
                destination_id="simpro-us-industries-hub",
                brand="Simpro",
                market="US",
                pillar_type="industries_hub",
                canonical_url="https://www.simprogroup.com/industries",
                page_title="Trades",
                title_checked="2026-08-01",
                title_valid_through="2026-11-01",
                main_keyword="trades",
                semrush_database="us",
                semrush_report="phrase_these",
                semrush_checked="2026-08-01",
                semrush_valid_through="2026-09-01",
                semrush_result_status="exact",
                volume=10,
                keyword_difficulty=1,
                evidence_path=(str(keyword_path), str(link_path), str(link_path)),
                evidence_locator=("lines:1-2", "line:1", "line:2"),
                evidence_sha256=(sha256(f"{market_line}\n{keyword_line}"), sha256(title_line), sha256(url_line)),
                vault_routes=(),
                status="verified",
            ),
        ),
    )


def test_contract_parser_accepts_complete_versioned_blocks() -> None:
    contract, findings = validate_contract(sidecar())

    assert findings == []
    assert contract is not None
    assert contract.commercial_pillar.destination_id == PILLAR_DESTINATION_ID
    assert contract.lifecycle.volatility == "standard"


def test_contract_parser_accepts_existing_bare_sidecar_headings() -> None:
    proof = sidecar()
    for heading in (
        "Search Intent and Format Decision",
        "Commercial Pillar and Anchor Decision",
        "Lifecycle Refresh Record",
    ):
        proof = proof.replace(f"## {heading}", heading)

    contract, findings = validate_contract(proof)

    assert findings == []
    assert contract is not None
    assert contract.commercial_pillar.destination_id == (
        PILLAR_DESTINATION_ID
    )


def test_research_artifact_paths_must_resolve_to_nonempty_repo_files(tmp_path: Path) -> None:
    content = article(
        "## Choosing field service software\n\n"
        f"Use [field service management software]({PILLAR_URL}) to compare workflows."
    )

    missing = check_content(
        content,
        proof_content=sidecar(),
        index=INDEX,
        today=STRATEGY_TODAY,
        artifact_root=tmp_path,
    )
    assert "blog_strategy_serp_artifact_missing" in rule_ids(missing)
    assert "blog_strategy_related_query_artifact_missing" in rule_ids(missing)

    serp_path = tmp_path / "research" / "serp-field-service-software-checklist-2026-08-06.md"
    paa_path = tmp_path / "research" / "paa-field-service-software-checklist-2026-08-06.md"
    serp_path.parent.mkdir()
    serp_path.write_text("Verified guide SERP observations.\n", encoding="utf-8")
    paa_path.write_text("Verified related questions.\n", encoding="utf-8")

    assert check_content(
        content,
        proof_content=sidecar(),
        index=INDEX,
        today=STRATEGY_TODAY,
        artifact_root=tmp_path,
    ) == []


@pytest.mark.parametrize(
    ("mutator", "expected_rule"),
    [
        (lambda text: text.replace("blog-strategy-contract/v1", "blog-strategy-contract/v2", 1), "blog_strategy_contract_version_unsupported"),
        (lambda text: text + "\n## Lifecycle Refresh Record\n- Contract version: blog-strategy-contract/v1\n", "blog_strategy_contract_section_duplicate"),
        (lambda text: text.replace("- Intent class: informational\n", "- Intent class: informational\n- Intent class: commercial\n"), "blog_strategy_contract_field_duplicate"),
        (lambda text: text.replace("- Funnel stage: MOFU", "- Funnel stage: maybe"), "blog_strategy_contract_enum_invalid"),
        (lambda text: text.replace("- SERP evidence artifact: research/serp-field-service-software-checklist-2026-08-06.md", "- SERP evidence artifact: TBD"), "blog_strategy_contract_placeholder"),
    ],
)
def test_contract_parser_fails_closed_on_malformed_or_conflicting_blocks(mutator, expected_rule: str) -> None:
    contract, findings = validate_contract(mutator(sidecar()))

    assert contract is None
    assert expected_rule in rule_ids(findings)


def test_contract_parser_ignores_fenced_example_blocks() -> None:
    contract, findings = validate_contract("```markdown\n" + sidecar() + "\n```\n")

    assert contract is None
    assert "blog_strategy_contract_section_missing" in rule_ids(findings)


def test_match_dominant_format_decision_requires_matching_content_type() -> None:
    contract, findings = validate_contract(
        sidecar().replace(
            "- Selected content type: guide",
            "- Selected content type: video landing page",
        )
    )

    assert contract is None
    assert "blog_strategy_contract_format_mismatch" in rule_ids(findings)


def test_visible_canonical_pillar_link_with_keyword_anchor_in_planned_h2_passes() -> None:
    content = article(
        "## Choosing field service software\n\n"
        f"Use [**field service management software**]({PILLAR_URL}) to compare connected workflows."
    )

    findings = check_content(content, proof_content=sidecar(), index=INDEX, today=STRATEGY_TODAY)

    assert findings == []


@pytest.mark.parametrize(
    ("body", "expected_rule"),
    [
        ("## Choosing field service software\n\n" + PILLAR_URL, "blog_strategy_pillar_link_missing"),
        ("## Choosing field service software\n\n`[field service management software](" + PILLAR_URL + ")`", "blog_strategy_pillar_link_missing"),
        ("## Choosing field service software\n\n    [field service management software](" + PILLAR_URL + ")", "blog_strategy_pillar_link_missing"),
        ("## Choosing field service software\n\n<!-- [field service management software](" + PILLAR_URL + ") -->", "blog_strategy_pillar_link_missing"),
        ("## Choosing field service software\n\n![field service management software](" + PILLAR_URL + ")", "blog_strategy_pillar_link_missing"),
        ("## Choosing field service software\n\n[learn more](" + PILLAR_URL + ")", "blog_strategy_anchor_keyword_missing"),
        ("## Choosing field service software\n\n[field operations platform](" + PILLAR_URL + ")", "blog_strategy_anchor_keyword_missing"),
        ("## Choosing field service software\n\n[field service management softwareish](" + PILLAR_URL + ")", "blog_strategy_anchor_keyword_missing"),
        ("## Choosing field service software\n\n[best field service management software guide](" + PILLAR_URL + ")", "blog_strategy_approved_anchor_missing"),
        ("## Another section\n\n[field service management software](" + PILLAR_URL + ")", "blog_strategy_planned_h2_mismatch"),
        ("## Choosing field service software\n\n[field service management software](" + PILLAR_URL + "?utm_source=blog)", "blog_strategy_pillar_link_noncanonical"),
        ("## Choosing field service software\n\n[field service management software](" + PILLAR_URL + "#demo)", "blog_strategy_pillar_link_noncanonical"),
    ],
)
def test_article_link_guard_rejects_nonvisible_noncanonical_or_unsupported_anchor(
    body: str,
    expected_rule: str,
) -> None:
    findings = check_content(article(body), proof_content=sidecar(), index=INDEX, today=STRATEGY_TODAY)

    assert expected_rule in rule_ids(findings)


def test_frontmatter_and_sidecar_urls_do_not_count_as_article_links() -> None:
    content = article("## Choosing field service software\n\nNo commercial link here.", pillar_url=PILLAR_URL)

    findings = check_content(content, proof_content=sidecar(), index=INDEX, today=STRATEGY_TODAY)

    assert "blog_strategy_pillar_link_missing" in rule_ids(findings)


def test_non_simpro_article_without_strategy_contract_is_out_of_scope() -> None:
    content = article(
        "## Choosing job software\n\nClockShark has its own routing.",
        brand="ClockShark",
        market="US",
    )

    findings = check_content(content, proof_content="", index=INDEX, today=STRATEGY_TODAY)

    assert findings == []


def test_required_mode_blocks_missing_brand_from_skipping_strategy_contract() -> None:
    content = article(
        "## Choosing field service software\n\nNo commercial link here.",
        brand="",
    )

    findings = check_content(
        content,
        proof_content="",
        index=INDEX,
        today=STRATEGY_TODAY,
        require_strategy=True,
    )

    assert "blog_strategy_contract_section_missing" in rule_ids(findings)


def test_standalone_cli_requires_blog_strategy_by_default(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    article_path = tmp_path / "draft.md"
    sidecar_path = tmp_path / "validation-draft.md"
    article_path.write_text(
        article("## Choosing field service software\n\nNo commercial link here.", brand=""),
        encoding="utf-8",
    )
    sidecar_path.write_text("", encoding="utf-8")

    exit_code = _main(
        [str(article_path), "--proof-sidecar", str(sidecar_path)]
    )

    assert exit_code == 1
    assert "blog_strategy_contract_section_missing" in capsys.readouterr().out


def test_required_mode_still_skips_explicit_non_simpro_brand_without_contract() -> None:
    content = article(
        "## Choosing job software\n\nClockShark has its own routing.",
        brand="ClockShark",
        market="US",
    )

    findings = check_content(
        content,
        proof_content="",
        index=INDEX,
        today=STRATEGY_TODAY,
        require_strategy=True,
    )

    assert findings == []


def test_simpro_article_missing_sidecar_returns_findings_instead_of_crashing(tmp_path: Path) -> None:
    path = tmp_path / "draft.md"
    path.write_text(article("## Choosing field service software\n\nNo link."), encoding="utf-8")

    findings = check_file(path, proof_sidecar=None)

    assert "blog_strategy_contract_section_missing" in rule_ids(findings)


def test_redirected_pillar_url_fails_without_second_request() -> None:
    content = article(
        "## Choosing field service software\n\n"
        f"Use [field service management software]({PILLAR_URL}) to compare workflows."
    )
    url_summary = UrlValidationSummary(
        [
            UrlValidationResult(
                url=PILLAR_URL,
                status="resolved",
                status_code=200,
                reason="resolved",
                line=11,
                anchor="field service management software",
                final_url="https://www.simprogroup.com/?redirected=1",
            )
        ]
    )

    findings = check_content(
        content,
        proof_content=sidecar(),
        index=INDEX,
        today=STRATEGY_TODAY,
        url_summary=url_summary,
    )

    assert "blog_strategy_pillar_redirect" in rule_ids(findings)


def test_article_brand_market_and_primary_keyword_collisions_fail() -> None:
    content = article(
        "## Choosing field service software\n\n"
        f"Use [field service management software]({PILLAR_URL}) to compare workflows.",
        market="UK",
        primary_keyword="field service management software",
    )
    findings = check_content(
        content,
        proof_content=sidecar(article_keyword="field service management software"),
        index=INDEX,
        today=STRATEGY_TODAY,
    )

    assert "blog_strategy_market_mismatch" in rule_ids(findings)
    assert "blog_strategy_primary_keyword_collision" in rule_ids(findings)


def test_article_h1_is_checked_when_frontmatter_title_is_absent() -> None:
    content = article(
        "## Choosing field service software\n\n"
        f"Use [field service management software]({PILLAR_URL}) to compare workflows.",
        title="",
    ).replace("# Field Service Software Checklist", "# Unrelated Article Title")

    findings = check_content(
        content,
        proof_content=sidecar(),
        index=INDEX,
        today=STRATEGY_TODAY,
    )

    assert "blog_strategy_article_title_mismatch" in rule_ids(findings)


def test_containment_collision_requires_verified_intent_and_content_type_difference() -> None:
    content = article(
        "## Choosing field service software\n\n"
        f"Use [field service management software]({PILLAR_URL}) to compare workflows.",
        primary_keyword="best field service management software",
    )
    findings = check_content(
        content,
        proof_content=sidecar(
            article_keyword="best field service management software",
            pillar_difference="The pages are different.",
        ),
        index=INDEX,
        today=STRATEGY_TODAY,
    )

    assert "blog_strategy_keyword_overlap_unproved" in rule_ids(findings)


def test_containment_collision_rejects_unrelated_serp_artifacts(tmp_path: Path) -> None:
    content = article(
        "## Choosing field service software\n\n"
        f"Use [field service management software]({PILLAR_URL}) to compare workflows.",
        primary_keyword="best field service management software",
    )
    serp_path = tmp_path / "research" / "serp-field-service-software-checklist-2026-08-06.md"
    paa_path = tmp_path / "research" / "paa-field-service-software-checklist-2026-08-06.md"
    serp_path.parent.mkdir()
    serp_path.write_text("Generic guide observations with no intent split.", encoding="utf-8")
    paa_path.write_text("Generic PAA observations.", encoding="utf-8")

    findings = check_content(
        content,
        proof_content=sidecar(article_keyword="best field service management software"),
        index=INDEX,
        today=STRATEGY_TODAY,
        artifact_root=tmp_path,
    )

    assert "blog_strategy_keyword_overlap_unproved" in rule_ids(findings)


def test_new_draft_is_blocked_when_research_decides_update_existing() -> None:
    content = article(
        "## Choosing field service software\n\n"
        f"Use [field service management software]({PILLAR_URL}) to compare workflows."
    )
    findings = check_content(
        content,
        proof_content=sidecar(cannibalization="update_existing"),
        index=INDEX,
        today=STRATEGY_TODAY,
        article_path=Path("drafts/new-field-service-checklist.md"),
    )

    assert "blog_strategy_new_article_blocked" in rule_ids(findings)


def test_pillar_paragraph_keeps_one_link_per_paragraph() -> None:
    content = article(
        "## Choosing field service software\n\n"
        f"Use [field service management software]({PILLAR_URL}) and "
        "[review pricing](https://www.simprogroup.com/pricing) before choosing."
    )

    findings = check_content(content, proof_content=sidecar(), index=INDEX, today=STRATEGY_TODAY)

    assert "blog_strategy_pillar_paragraph_link_count" in rule_ids(findings)


def test_industries_hub_requires_documented_no_specific_fit_reason(tmp_path: Path) -> None:
    content = article(
        "## Choosing field service software\n\n"
        "Use [trades](https://www.simprogroup.com/industries) to compare trade-specific options.",
        primary_keyword="trade software comparison",
    )
    proof = sidecar(
        article_keyword="trade software comparison",
        pillar_url="https://www.simprogroup.com/industries",
        anchor="trades",
        pillar_difference="The article and hub have different intent and different content type.",
    ).replace(
        f"Destination ID: {PILLAR_DESTINATION_ID}",
        "Destination ID: simpro-us-industries-hub",
    )

    findings = check_content(
        content,
        proof_content=proof,
        index=industries_hub_index(tmp_path),
        today=date(2026, 8, 6),
    )

    assert "blog_strategy_industries_hub_reason_missing" in rule_ids(findings)
