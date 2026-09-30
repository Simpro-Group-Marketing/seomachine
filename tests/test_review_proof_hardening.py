"""Hardening for multi-story review selections and nonvault review-site eligibility."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.customer_proof.nonconnector_eligibility import (
    _eligible_source,
    _supports_role,
)
from data_sources.modules.review_story_identity_guard import (
    REVIEW_RATING_RANKING_CLAIM_RE,
    check_content,
)
from tests.test_review_story_identity_guard import (
    BIGCHANGE_CAPTERRA_URL,
    TWO_REVIEWER_ARTICLE,
    two_reviewer_sidecar,
    write_two_reviewer_index,
)

INVENTED_SUZANNE_ARTICLE = (
    "# Article\n\n"
    f"[Clare's Capterra review]({BIGCHANGE_CAPTERRA_URL}) describes onboarding new team members quickly.\n\n"
    f"[Suzanne's Capterra review]({BIGCHANGE_CAPTERRA_URL}), "
    '"This invented sentence was never approved for any review row."\n'
)
ONE_BLOCK_SIDECAR = f"""Review Story Selection
- Selected story: review-capterra-suzanne-job-scheduling | Identity: Suzanne | Platform: Capterra | URL: {BIGCHANGE_CAPTERRA_URL} | Status: approved | Use: E-E-A-T experience story
- Selected story: review-capterra-clare-onboarding | Identity: Clare | Platform: Capterra | URL: {BIGCHANGE_CAPTERRA_URL} | Status: approved | Use: E-E-A-T experience story
"""
CLARE_FIRST_SIDECAR = two_reviewer_sidecar(
    "review-capterra-clare-onboarding", "Clare", "review-capterra-suzanne-job-scheduling", "Suzanne"
)


def _quote_findings(article: str, sidecar: str, **index_kwargs) -> list:
    with TemporaryDirectory() as temp_dir:
        index_path = write_two_reviewer_index(Path(temp_dir), **index_kwargs)
        findings = check_content(article, proof_content=sidecar, proof_index_path=index_path)
    return [f for f in findings if f["rule_id"] == "review_quote_requires_approved_quote"]


def test_invented_quote_fails_when_its_story_is_not_the_last_bullet_in_one_block():
    assert _quote_findings(INVENTED_SUZANNE_ARTICLE, ONE_BLOCK_SIDECAR)


def test_invented_quote_fails_when_its_story_is_in_a_later_block():
    assert _quote_findings(INVENTED_SUZANNE_ARTICLE, CLARE_FIRST_SIDECAR)


def test_bound_quote_passes_in_both_layouts():
    assert _quote_findings(TWO_REVIEWER_ARTICLE, ONE_BLOCK_SIDECAR) == []
    assert _quote_findings(TWO_REVIEWER_ARTICLE, CLARE_FIRST_SIDECAR) == []


def test_unapproved_suzanne_quote_fails_in_clare_first_layout():
    assert _quote_findings(
        TWO_REVIEWER_ARTICLE, CLARE_FIRST_SIDECAR, suzanne_quote="A different approved snippet."
    )


def test_unapproved_quote_suggestion_points_at_the_index_row():
    findings = _quote_findings(INVENTED_SUZANNE_ARTICLE, CLARE_FIRST_SIDECAR)
    assert "approved_quotes" in findings[0]["suggestion"]


def test_identity_match_is_whole_word_not_substring():
    article = (
        "# Article\n\n"
        f"[Clare's Capterra review]({BIGCHANGE_CAPTERRA_URL}) describes onboarding new team members quickly.\n\n"
        f"[Hannah's Capterra review]({BIGCHANGE_CAPTERRA_URL}), "
        '"This invented sentence was never approved for any review row."\n'
    )
    sidecar = two_reviewer_sidecar(
        "review-capterra-clare-onboarding", "Clare", "review-capterra-suzanne-job-scheduling", "Ann"
    )
    assert _quote_findings(article, sidecar)


def test_rating_regex_catches_percentages_and_spelled_out_stars():
    assert REVIEW_RATING_RANKING_CLAIM_RE.search("scheduling got 30% faster")
    assert REVIEW_RATING_RANKING_CLAIM_RE.search("she gave it five stars")
    assert REVIEW_RATING_RANKING_CLAIM_RE.search("a 4 out of 5 score")
    assert not REVIEW_RATING_RANKING_CLAIM_RE.search("Clare built her worksheets in-house")


def _review_row(url: str, **overrides) -> dict:
    row = {
        "proof_id": "review-capterra-row",
        "source_type": "review_site",
        "approval_status": "approved",
        "public_copy_allowed": True,
        "public_url": url,
        "approved_metrics": [{"metric": "30% faster", "status": "approved"}],
        "review_story": {"story_allowed": True, "platform": "Capterra", "identity_display": "Sam", "public_url": url},
    }
    row.update(overrides)
    return row


def test_real_mixed_case_aroflo_and_clockshark_capterra_urls_are_eligible():
    index = json.loads(Path("context/customer-proof-index.json").read_text(encoding="utf-8"))
    urls = {
        brand: next(
            row["public_url"] for row in index["proof"]
            if row.get("source_type") == "review_site" and f"/{brand}/" in row.get("public_url", "")
        )
        for brand in ("AroFlo", "ClockShark")
    }
    assert _eligible_source(_review_row(urls["AroFlo"]), expected_host="aroflo.com", brand_key="aroflo")
    assert _eligible_source(_review_row(urls["ClockShark"]), expected_host="clockshark.com", brand_key="clockshark")


def test_review_url_with_parent_traversal_is_not_eligible():
    url = "https://www.capterra.co.uk/software/149479/jobwatch-powered-by-bigchange/../../1/other"
    assert not _eligible_source(_review_row(url), expected_host="bigchange.com", brand_key="bigchange")


def test_review_site_rows_never_fill_the_metric_role():
    row = _review_row(BIGCHANGE_CAPTERRA_URL)
    assert not _supports_role(row, "metric", require_eeat_story=False)
    assert _supports_role({**row, "source_type": "case_study"}, "metric", require_eeat_story=False)
