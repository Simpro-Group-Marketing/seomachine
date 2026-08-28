import json
from unittest.mock import patch

import pytest

from data_sources.modules.fred_authority_guard import (
    _main,
    _normalize_url,
    check_content,
    requires_authority_review,
    should_fail,
)
from tests.test_fred_authority_selector import (
    ARTICLE_URL,
    VIDEO_URL,
    default_fred_claims,
    fred_claim,
    load_validated_claim_set_for_unit_test,
    write_context_receipt_fixture,
)


ARTICLE_RESOURCE_ID = "res-fred-fvmi-001"
VIDEO_RESOURCE_ID = "res-fred-fvmi-003"
ARTICLE_QUOTE = "Connected workforce technology helps skilled trades teams coordinate work."
VIDEO_QUOTE = "Field service leaders need operating visibility across every team."


@pytest.fixture(autouse=True)
def _mock_live_validator():
    with patch(
        "data_sources.modules.fred_authority_guard.load_validated_claim_set",
        new=load_validated_claim_set_for_unit_test,
    ):
        yield


def selection_block(
    revision: str,
    *,
    selected: str = "none",
    claim_ids: str = "claim-fred-FVMI-001, claim-fred-FVMI-002, claim-fred-FVMI-003",
    fit: str | None = None,
    intended_use: str = "none",
    target: str = "not applicable",
    authority_id: str | None = None,
    url: str | None = None,
    evidence_status: str | None = None,
    method: str = "not_applicable",
    excerpt: str = "not applicable",
    locator: str = "not applicable",
    playback: str = "not_applicable",
    exact_quote: str = "not applicable",
    embed: str = "no",
    video_object: str = "not applicable",
    approval_source: str = "connector_claim_result",
) -> str:
    selected_values = {
        "FVMI-001": (ARTICLE_RESOURCE_ID, ARTICLE_URL),
        "FVMI-003": (VIDEO_RESOURCE_ID, VIDEO_URL),
    }
    selected_resource, selected_url = selected_values.get(
        selected,
        ("none", "not applicable"),
    )
    if fit is None:
        fit = (
            "No candidate directly supports the article's tax compliance objective, so public use is rejected."
            if selected == "none"
            else "The selected source directly supports the named article section and intended public use."
        )
    fields = [
        ("Selector command", "python data_sources/modules/fred_authority_selector.py topic --slate"),
        ("Evaluation status", "completed"),
        ("Top candidates", "[FVMI-001, FVMI-002, FVMI-003]"),
        ("Selected", f"[{selected}]"),
        ("Context receipt", "context-receipt.json"),
        ("Claim IDs", f"[{claim_ids}]"),
        ("Receipt revision", revision),
        ("Approval source", approval_source),
        ("Fit decision", fit),
        ("Intended use", intended_use),
        ("Target section", target),
        ("Authority row", f"[{authority_id or selected_resource}]"),
        ("Public URL", url or selected_url),
        ("Evidence status", evidence_status or ("receipt_approved" if selected != "none" else "not applicable")),
        ("Verification method", method),
        ("Evidence excerpt", excerpt),
        ("Timestamp or locator", locator),
        ("Playback verified", playback),
        ("Exact quote", exact_quote),
        ("Embed decision", embed),
        ("VideoObject", video_object),
    ]
    return "## Fred Voccola Authority Selection\n" + "\n".join(
        f"- {key}: {value}" for key, value in fields
    )


def article_quote_block(revision: str, **overrides: str) -> str:
    values = {
        "selected": "FVMI-001",
        "intended_use": "exact_quote",
        "target": "Workforce technology",
        "method": "source_visible_article_text",
        "excerpt": f"Source text states: {ARTICLE_QUOTE}",
        "locator": "Article paragraph 4",
        "exact_quote": ARTICLE_QUOTE,
    }
    values.update(overrides)
    return selection_block(revision, **values)


def video_quote_block(revision: str, **overrides: str) -> str:
    values = {
        "selected": "FVMI-003",
        "intended_use": "exact_quote",
        "target": "Field service leadership",
        "method": "transcript_and_playback",
        "excerpt": f"Transcript states: {VIDEO_QUOTE}",
        "locator": "01:23",
        "playback": "yes",
        "exact_quote": VIDEO_QUOTE,
    }
    values.update(overrides)
    return selection_block(revision, **values)


def embedded_article(
    *,
    provider: str = "www.youtube-nocookie.com",
    video_id: str = "abc123XYZ00",
    autoplay: bool = False,
    schema: bool = True,
    responsive: bool = True,
) -> str:
    schema_line = "  - VideoObject\n" if schema else ""
    wrapper = ' style="aspect-ratio: 16 / 9; width: 100%;"' if responsive else ""
    autoplay_query = "?autoplay=1" if autoplay else ""
    return (
        "---\n"
        "schema_notes:\n"
        "  - BlogPosting\n"
        f"{schema_line}"
        "---\n"
        "# Article\n\n"
        "## Field service leadership\n\n"
        "This discussion explains why operating visibility matters before presenting the supporting video.\n\n"
        f"<div class=\"video-embed\"{wrapper}>\n"
        f"<iframe src=\"https://{provider}/embed/{video_id}{autoplay_query}\" "
        "title=\"Fred Voccola on field service leadership\" loading=\"lazy\" "
        "allowfullscreen></iframe>\n"
        "</div>\n\n"
        f"[Watch Fred Voccola discuss field service leadership]({VIDEO_URL}).\n"
    )


def guard_check(article: str, proof: str, pack, receipt):
    return check_content(
        article,
        proof_content=proof,
        context_pack=pack,
        context_receipt=receipt,
    )


def test_missing_selection_block_fails():
    findings = check_content("# Article\n\nBody.", proof_content="# Validation")

    assert should_fail(findings)
    assert {item["rule_id"] for item in findings} == {"fred_authority_selection_missing"}


def test_malformed_frontmatter_requires_review_without_raising():
    malformed = "---\nbrand: [broken\n---\n# Article\n\nBody."

    assert requires_authority_review(malformed) is True


def test_malformed_frontmatter_returns_stable_fail_closed_finding():
    malformed = "---\nbrand: [broken\n---\n# Article\n\nBody."

    findings = check_content(malformed, proof_content="# Validation")

    assert {finding["rule_id"] for finding in findings} == {
        "fred_authority_frontmatter_invalid"
    }


def test_malformed_frontmatter_cli_returns_finding_instead_of_crashing(tmp_path, capsys):
    article = tmp_path / "malformed.md"
    article.write_text("---\nbrand: [broken\n---\n# Article\n\nBody.", encoding="utf-8")

    exit_code = _main([str(article), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert {finding["rule_id"] for finding in payload["findings"]} == {
        "fred_authority_frontmatter_invalid"
    }


def test_explicit_non_simpro_article_without_fred_use_is_exempt():
    article = (
        "---\nbrand: BigChange\nartifact_type: blog\ntitle: Job management\n---\n"
        "# Job management\n\nBigChange helps teams coordinate field work."
    )

    assert check_content(article, proof_content="# Validation") == []


def test_cross_brand_simpro_product_mention_without_fred_use_is_exempt():
    article = (
        "---\nbrand: ClockShark\nartifact_type: blog\ntitle: Simpro comparison\n---\n"
        "# Simpro comparison\n\nThis comparison discusses Simpro product workflows."
    )

    assert check_content(article, proof_content="# Validation") == []


def test_cross_brand_public_fred_use_still_requires_selection():
    article = (
        "---\nbrand: AroFlo\nartifact_type: blog\ntitle: Industry view\n---\n"
        "# Industry view\n\nFred Voccola discusses field service operations at Simpro."
    )

    findings = check_content(article, proof_content="# Validation")

    assert {item["rule_id"] for item in findings} == {"fred_authority_selection_missing"}


@pytest.mark.parametrize(
    "hidden_markup",
    [
        '<div hidden>Fred Voccola discusses field service operations.</div>',
        '<div aria-hidden="true">Fred Voccola discusses field service operations.</div>',
        '<div style="display: none">Fred Voccola discusses field service operations.</div>',
        '<div style="color:red; visibility : hidden !important">Fred Voccola discusses field service operations.</div>',
    ],
)
def test_cross_brand_hidden_fred_text_does_not_trigger_authority_review(hidden_markup):
    article = (
        "---\nbrand: AroFlo\nartifact_type: blog\ntitle: Industry view\n---\n"
        f"# Industry view\n\n{hidden_markup}\n\nVisible AroFlo guidance."
    )

    assert check_content(article, proof_content="# Validation") == []


def test_simpro_article_without_public_fred_use_still_requires_evaluation():
    article = (
        "---\nbrand: Simpro\nartifact_type: blog\ntitle: Field service\n---\n"
        "# Field service\n\nOperational guidance."
    )

    findings = check_content(article, proof_content="# Validation")

    assert {item["rule_id"] for item in findings} == {"fred_authority_selection_missing"}

def test_valid_none_selection_passes_with_valid_receipt(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)

    findings = guard_check(
        "# Article\n\nTax compliance details.",
        selection_block(revision),
        pack,
        receipt,
    )

    assert findings == []


def test_none_selection_requires_substantive_rejection_reason(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)

    findings = guard_check(
        "# Article\n\nBody.",
        selection_block(revision, fit="Not used."),
        pack,
        receipt,
    )

    assert any(item["rule_id"] == "fred_authority_none_reason_weak" for item in findings)


def test_none_selection_rejects_public_fred_use(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)

    findings = guard_check(
        f'# Article\n\nFred Voccola said, "{ARTICLE_QUOTE}"',
        selection_block(revision),
        pack,
        receipt,
    )

    assert any(
        item["rule_id"] == "fred_authority_public_use_without_selection"
        for item in findings
    )


def test_missing_receipt_fails_closed(tmp_path):
    _, _, revision = write_context_receipt_fixture(tmp_path)

    findings = check_content(
        "# Article\n\nBody.",
        proof_content=selection_block(revision),
    )

    assert should_fail(findings)
    assert any(item["rule_id"] == "fred_authority_receipt_unavailable" for item in findings)


def test_unknown_selected_id_fails_receipt_approval(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)

    findings = guard_check(
        "# Article\n\nBody.",
        selection_block(
            revision,
            selected="FVMI-999",
            intended_use="inline_citation",
            target="Workforce technology",
            authority_id="res-unknown",
            url="https://example.com/unknown",
            evidence_status="receipt_approved",
        ),
        pack,
        receipt,
    )

    assert any(item["rule_id"] == "fred_authority_id_unknown" for item in findings)


def test_selected_claim_metadata_must_match_receipt(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)

    findings = guard_check(
        f'# Article\n\n[Fred Voccola]({ARTICLE_URL}) said, "{ARTICLE_QUOTE}"',
        article_quote_block(
            revision,
            authority_id="res-wrong",
            url="https://example.com/wrong",
            evidence_status="wrong_status",
            claim_ids="claim-fred-FVMI-003",
            approval_source="manual",
        ),
        pack,
        receipt,
    )
    rules = {item["rule_id"] for item in findings}

    assert "fred_authority_row_mismatch" in rules
    assert "fred_authority_url_mismatch" in rules
    assert "fred_authority_status_mismatch" in rules
    assert "fred_authority_claim_id_mismatch" in rules
    assert "fred_authority_approval_source_mismatch" in rules


def test_authority_support_receipt_does_not_authorize_exact_article_quote(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    article = f'# Article\n\n[Fred Voccola]({ARTICLE_URL}) said, "{ARTICLE_QUOTE}"'

    findings = guard_check(article, article_quote_block(revision), pack, receipt)

    assert any(
        item["rule_id"] == "fred_authority_public_use_unapproved"
        for item in findings
    )


def test_receipt_approved_exact_article_quote_passes(tmp_path):
    claims = default_fred_claims() + [
        fred_claim(
            "FVMI-001",
            ARTICLE_QUOTE,
            ARTICLE_URL,
            authority_resource_id=ARTICLE_RESOURCE_ID,
            claim_id="claim-fred-FVMI-001-exact",
            use_mode="exact_quote",
        )
    ]
    pack, receipt, revision = write_context_receipt_fixture(tmp_path, claims)
    article = f'# Article\n\n[Fred Voccola]({ARTICLE_URL}) said, "{ARTICLE_QUOTE}"'
    proof = article_quote_block(
        revision,
        claim_ids="claim-fred-FVMI-001, claim-fred-FVMI-001-exact",
    )

    findings = guard_check(article, proof, pack, receipt)

    assert findings == []


@pytest.mark.parametrize(
    "hidden_attribute",
    [
        "hidden",
        'aria-hidden="true"',
        'style="display:none"',
        'style="visibility: hidden !important"',
    ],
)
def test_hidden_html_link_does_not_satisfy_public_quote_link(tmp_path, hidden_attribute):
    claims = default_fred_claims() + [
        fred_claim(
            "FVMI-001",
            ARTICLE_QUOTE,
            ARTICLE_URL,
            authority_resource_id=ARTICLE_RESOURCE_ID,
            claim_id="claim-fred-FVMI-001-exact",
            use_mode="exact_quote",
        )
    ]
    pack, receipt, revision = write_context_receipt_fixture(tmp_path, claims)
    article = (
        f'# Article\n\nFred Voccola said, "{ARTICLE_QUOTE}" '
        f'<span {hidden_attribute}><a href="{ARTICLE_URL}">Source</a></span>'
    )
    proof = article_quote_block(
        revision,
        claim_ids="claim-fred-FVMI-001, claim-fred-FVMI-001-exact",
    )

    findings = guard_check(article, proof, pack, receipt)

    assert any(item["rule_id"] == "fred_authority_public_link_missing" for item in findings)


def test_hidden_exact_quote_does_not_satisfy_public_quote_use(tmp_path):
    claims = default_fred_claims() + [
        fred_claim(
            "FVMI-001",
            ARTICLE_QUOTE,
            ARTICLE_URL,
            authority_resource_id=ARTICLE_RESOURCE_ID,
            claim_id="claim-fred-FVMI-001-exact",
            use_mode="exact_quote",
        )
    ]
    pack, receipt, revision = write_context_receipt_fixture(tmp_path, claims)
    article = (
        f'# Article\n\n[Read the source]({ARTICLE_URL}). '
        f'<span style="display:none">Fred Voccola said, "{ARTICLE_QUOTE}"</span>'
    )
    proof = article_quote_block(
        revision,
        claim_ids="claim-fred-FVMI-001, claim-fred-FVMI-001-exact",
    )

    findings = guard_check(article, proof, pack, receipt)

    assert any(item["rule_id"] == "fred_authority_exact_quote_missing" for item in findings)


def test_url_equality_uses_shared_canonical_identity():
    assert _normalize_url("HTTPS://EXAMPLE.COM:443/skilled-trades?View=Full") == _normalize_url(
        "https://example.com/skilled-trades?View=Full"
    )
    assert _normalize_url("http://EXAMPLE.COM:80/") == _normalize_url("http://example.com")
    assert _normalize_url("https://example.com/Skilled-trades?View=Full") != _normalize_url(
        "https://example.com/skilled-trades?View=Full"
    )
    assert _normalize_url("https://example.com/skilled-trades?View=Full") != _normalize_url(
        "https://example.com/skilled-trades?view=Full"
    )
    assert _normalize_url(
        "https://example.com/skilled-trades/?utm_source=article#quote"
    ) == _normalize_url("https://example.com/skilled-trades")


def test_default_port_and_authority_case_variants_join_to_receipt_url(tmp_path):
    claims = default_fred_claims() + [
        fred_claim(
            "FVMI-001",
            ARTICLE_QUOTE,
            ARTICLE_URL,
            authority_resource_id=ARTICLE_RESOURCE_ID,
            claim_id="claim-fred-FVMI-001-exact",
            use_mode="exact_quote",
        )
    ]
    pack, receipt, revision = write_context_receipt_fixture(tmp_path, claims)
    equivalent_url = "HTTPS://EXAMPLE.COM:443/skilled-trades"
    article = f'# Article\n\n[Fred Voccola]({equivalent_url}) said, "{ARTICLE_QUOTE}"'
    proof = article_quote_block(
        revision,
        url=equivalent_url,
        claim_ids="claim-fred-FVMI-001, claim-fred-FVMI-001-exact",
    )

    assert guard_check(article, proof, pack, receipt) == []


def test_url_equality_removes_non_root_trailing_slash_difference():
    assert _normalize_url("https://example.com/skilled-trades/") == _normalize_url(
        "https://example.com/skilled-trades"
    )


@pytest.mark.parametrize(
    "link_markup",
    [
        f"[source]({ARTICLE_URL})",
        ARTICLE_URL,
    ],
)
def test_fred_quote_rejects_generic_or_bare_proof_links(tmp_path, link_markup):
    claims = default_fred_claims() + [
        fred_claim(
            "FVMI-001",
            ARTICLE_QUOTE,
            ARTICLE_URL,
            authority_resource_id=ARTICLE_RESOURCE_ID,
            claim_id="claim-fred-FVMI-001-exact",
            use_mode="exact_quote",
        )
    ]
    pack, receipt, revision = write_context_receipt_fixture(tmp_path, claims)
    article = f'# Article\n\nFred Voccola said, "{ARTICLE_QUOTE}" {link_markup}'
    proof = article_quote_block(
        revision,
        claim_ids="claim-fred-FVMI-001, claim-fred-FVMI-001-exact",
    )

    rules = {
        finding["rule_id"]
        for finding in guard_check(article, proof, pack, receipt)
    }

    assert "fred_authority_public_link_missing" in rules


def test_exact_quote_and_link_in_different_paragraphs_fails(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    article = (
        f'# Article\n\nFred Voccola said, "{ARTICLE_QUOTE}"\n\n'
        f"[Read the source]({ARTICLE_URL})."
    )

    findings = guard_check(article, article_quote_block(revision), pack, receipt)

    assert any(item["rule_id"] == "fred_authority_public_link_missing" for item in findings)


def test_authority_support_receipt_does_not_authorize_paraphrase(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    article = (
        f"# Article\n\n[Fred Voccola argues]({ARTICLE_URL}) that connected workforce "
        "tools can help skilled trades teams coordinate work."
    )
    proof = selection_block(
        revision,
        selected="FVMI-001",
        intended_use="paraphrased_industry_observation",
        target="Workforce technology",
        method="paraphrase_evidence",
        excerpt="Connected tools help skilled trades businesses coordinate their workforce.",
        locator="Article paragraph 4",
    )

    findings = guard_check(article, proof, pack, receipt)

    assert any(
        item["rule_id"] == "fred_authority_public_use_unapproved"
        for item in findings
    )


def test_receipt_approved_attributed_paraphrase_passes(tmp_path):
    approved_paraphrase = (
        "Connected tools help skilled trades businesses coordinate their workforce."
    )
    claims = default_fred_claims() + [
        fred_claim(
            "FVMI-001",
            approved_paraphrase,
            ARTICLE_URL,
            authority_resource_id=ARTICLE_RESOURCE_ID,
            claim_id="claim-fred-FVMI-001-paraphrase",
            use_mode="public_paraphrase",
        )
    ]
    pack, receipt, revision = write_context_receipt_fixture(tmp_path, claims)
    article = (
        f"# Article\n\n[Fred Voccola argues]({ARTICLE_URL}) that connected workforce "
        "tools can help skilled trades teams coordinate work."
    )
    proof = selection_block(
        revision,
        selected="FVMI-001",
        claim_ids="claim-fred-FVMI-001, claim-fred-FVMI-001-paraphrase",
        intended_use="paraphrased_industry_observation",
        target="Workforce technology",
        method="paraphrase_evidence",
        excerpt=approved_paraphrase,
        locator="Article paragraph 4",
    )

    findings = guard_check(article, proof, pack, receipt)

    assert findings == []


def test_unlinked_or_unsupported_paraphrase_fails(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    proof = selection_block(
        revision,
        selected="FVMI-001",
        intended_use="paraphrased_industry_observation",
        target="Workforce technology",
        method="paraphrase_evidence",
        excerpt="not applicable",
    )

    findings = guard_check(
        "# Article\n\nFred Voccola argues that connected workforce tools improve coordination.",
        proof,
        pack,
        receipt,
    )
    rules = {item["rule_id"] for item in findings}

    assert "fred_authority_public_link_missing" in rules
    assert "fred_authority_paraphrase_evidence_missing" in rules


def test_authority_support_receipt_does_not_authorize_video_quote(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    article = f'# Article\n\n[Fred Voccola]({VIDEO_URL}) said, "{VIDEO_QUOTE}"'

    findings = guard_check(article, video_quote_block(revision), pack, receipt)

    assert any(
        item["rule_id"] == "fred_authority_public_use_unapproved"
        for item in findings
    )


def test_receipt_approved_video_quote_passes(tmp_path):
    claims = default_fred_claims() + [
        fred_claim(
            "FVMI-003",
            VIDEO_QUOTE,
            VIDEO_URL,
            authority_resource_id=VIDEO_RESOURCE_ID,
            claim_id="claim-fred-FVMI-003-exact",
            use_mode="exact_quote",
        )
    ]
    pack, receipt, revision = write_context_receipt_fixture(tmp_path, claims)
    article = f'# Article\n\n[Fred Voccola]({VIDEO_URL}) said, "{VIDEO_QUOTE}"'
    proof = video_quote_block(
        revision,
        claim_ids="claim-fred-FVMI-003, claim-fred-FVMI-003-exact",
    )

    findings = guard_check(article, proof, pack, receipt)

    assert findings == []


def test_public_use_claim_must_be_listed_in_sidecar(tmp_path):
    claims = default_fred_claims() + [
        fred_claim(
            "FVMI-001",
            ARTICLE_QUOTE,
            ARTICLE_URL,
            authority_resource_id=ARTICLE_RESOURCE_ID,
            claim_id="claim-fred-FVMI-001-exact",
            use_mode="exact_quote",
        )
    ]
    pack, receipt, revision = write_context_receipt_fixture(tmp_path, claims)
    article = f'# Article\n\n[Fred Voccola]({ARTICLE_URL}) said, "{ARTICLE_QUOTE}"'

    findings = guard_check(article, article_quote_block(revision), pack, receipt)

    assert any(
        item["rule_id"] == "fred_authority_public_use_claim_id_mismatch"
        for item in findings
    )


@pytest.mark.parametrize(
    ("selector_id", "authority_resource_id", "public_url"),
    [
        ("FVMI-002", ARTICLE_RESOURCE_ID, ARTICLE_URL),
        ("FVMI-001", "res-fred-other-source", ARTICLE_URL),
        ("FVMI-001", ARTICLE_RESOURCE_ID, "https://example.com/different-source"),
    ],
)
def test_public_use_authorization_must_match_claim_source_and_url(
    tmp_path,
    selector_id,
    authority_resource_id,
    public_url,
):
    claims = default_fred_claims() + [
        fred_claim(
            selector_id,
            ARTICLE_QUOTE,
            public_url,
            authority_resource_id=authority_resource_id,
            claim_id="claim-fred-mismatched-exact",
            use_mode="exact_quote",
        )
    ]
    pack, receipt, revision = write_context_receipt_fixture(tmp_path, claims)
    article = f'# Article\n\n[Fred Voccola]({ARTICLE_URL}) said, "{ARTICLE_QUOTE}"'
    proof = article_quote_block(
        revision,
        claim_ids="claim-fred-FVMI-001, claim-fred-mismatched-exact",
    )

    findings = guard_check(article, proof, pack, receipt)

    assert any(
        item["rule_id"] == "fred_authority_public_use_unapproved"
        for item in findings
    )

def test_video_quote_cannot_claim_article_text_verification(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    article = f'# Article\n\n[Fred Voccola]({VIDEO_URL}) said, "{VIDEO_QUOTE}"'
    proof = video_quote_block(revision).replace(
        "Verification method: transcript_and_playback",
        "Verification method: source_visible_article_text",
    ).replace("Playback verified: yes", "Playback verified: no")

    findings = guard_check(article, proof, pack, receipt)
    rules = {item["rule_id"] for item in findings}

    assert "fred_authority_transcript_required" in rules
    assert "fred_authority_playback_required" in rules


@pytest.mark.parametrize("locator", ["article paragraph 4", "00:61", "1:02:75"])
def test_video_quote_requires_well_formed_timestamp(tmp_path, locator):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    article = f'# Article\n\n[Fred Voccola]({VIDEO_URL}) said, "{VIDEO_QUOTE}"'

    findings = guard_check(
        article,
        video_quote_block(revision, locator=locator),
        pack,
        receipt,
    )

    assert any(item["rule_id"] == "fred_authority_video_timestamp_invalid" for item in findings)


def test_content_first_youtube_embed_with_video_object_passes(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    proof = selection_block(
        revision,
        selected="FVMI-003",
        intended_use="embed",
        target="Field service leadership",
        embed="yes",
        video_object="required",
    )

    findings = guard_check(embedded_article(), proof, pack, receipt)

    assert findings == []


@pytest.mark.parametrize(
    ("article", "rule_id"),
    [
        (embedded_article(autoplay=True), "fred_authority_embed_autoplay"),
        (embedded_article(schema=False), "fred_authority_video_object_missing"),
        (
            embedded_article(provider="player.vimeo.com"),
            "fred_authority_embed_provider_invalid",
        ),
        (
            embedded_article(video_id="abc123XYZ00extra"),
            "fred_authority_embed_video_mismatch",
        ),
        (
            embedded_article(responsive=False),
            "fred_authority_embed_responsive_missing",
        ),
    ],
)
def test_youtube_embed_contract_fails_closed(tmp_path, article, rule_id):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    proof = selection_block(
        revision,
        selected="FVMI-003",
        intended_use="embed",
        target="Field service leadership",
        embed="yes",
        video_object="required",
    )

    findings = guard_check(article, proof, pack, receipt)

    assert any(item["rule_id"] == rule_id for item in findings)


def test_hidden_youtube_iframe_does_not_satisfy_public_embed(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    proof = selection_block(
        revision,
        selected="FVMI-003",
        intended_use="embed",
        target="Field service leadership",
        embed="yes",
        video_object="required",
    )
    article = embedded_article().replace(
        'class="video-embed"',
        'class="video-embed" hidden',
    )

    findings = guard_check(article, proof, pack, receipt)
    rules = {item["rule_id"] for item in findings}

    assert "fred_authority_embed_missing" in rules
    assert "fred_authority_video_object_without_embed" in rules


def test_video_object_without_embed_is_rejected(tmp_path):
    pack, receipt, revision = write_context_receipt_fixture(tmp_path)
    article = "---\nschema_notes:\n  - BlogPosting\n  - VideoObject\n---\n# Article\n\nBody."

    findings = guard_check(article, selection_block(revision), pack, receipt)

    assert any(
        item["rule_id"] == "fred_authority_video_object_without_embed"
        for item in findings
    )
