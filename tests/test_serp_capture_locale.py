"""Approved SERP capture locales follow the repository market vocabulary."""

import pytest

from data_sources.modules.editorial_plan.serp_capture import (
    _dataforseo_request_valid,
    _playwright_request_valid,
    _semrush_request_valid,
)


PLAYWRIGHT_URL = "https://www.google.com/search?q=field+service+software+training&gl={gl}&pws=0"
QUERY = "field service software training"


@pytest.mark.parametrize("gl", ["us", "gb", "uk", "au", "nz", "ca", "ie"])
def test_playwright_accepts_supported_markets(gl):
    assert _playwright_request_valid(
        PLAYWRIGHT_URL.format(gl=gl),
        {"hl": "en", "gl": gl, "pws": "0"},
        query=QUERY,
    )


@pytest.mark.parametrize("gl", ["de", "fr", "jp", ""])
def test_playwright_rejects_unsupported_markets(gl):
    assert not _playwright_request_valid(
        PLAYWRIGHT_URL.format(gl=gl),
        {"hl": "en", "gl": gl, "pws": "0"},
        query=QUERY,
    )


def test_playwright_still_requires_english_and_no_personalization():
    assert not _playwright_request_valid(
        PLAYWRIGHT_URL.format(gl="uk"),
        {"hl": "de", "gl": "uk", "pws": "0"},
        query=QUERY,
    )
    assert not _playwright_request_valid(
        PLAYWRIGHT_URL.format(gl="uk"),
        {"hl": "en", "gl": "uk", "pws": "1"},
        query=QUERY,
    )


def test_playwright_still_binds_query_and_host():
    assert not _playwright_request_valid(
        "https://www.bing.com/search?q=x&gl=uk&pws=0",
        {"hl": "en", "gl": "uk", "pws": "0"},
        query=QUERY,
    )
    assert not _playwright_request_valid(
        PLAYWRIGHT_URL.format(gl="uk"),
        {"hl": "en", "gl": "uk", "pws": "0"},
        query="a different query",
    )


@pytest.mark.parametrize("database", ["us", "uk", "au", "nz", "ca", "ie"])
def test_semrush_accepts_supported_markets(database):
    assert _semrush_request_valid(
        "semrush://keyword/phrase_organic", {"database": database}
    )


@pytest.mark.parametrize("database", ["de", "fr", ""])
def test_semrush_rejects_unsupported_markets(database):
    assert not _semrush_request_valid(
        "semrush://keyword/phrase_organic", {"database": database}
    )


@pytest.mark.parametrize(
    "location_code", [2840, 2826, 2036, 2554, 2124, 2372]
)
def test_dataforseo_accepts_supported_markets(location_code):
    assert _dataforseo_request_valid(
        "dataforseo://serp/google/organic/live/advanced",
        {"language_code": "en", "location_code": location_code},
    )


@pytest.mark.parametrize("location_code", [2276, 2250, 0])
def test_dataforseo_rejects_unsupported_markets(location_code):
    assert not _dataforseo_request_valid(
        "dataforseo://serp/google/organic/live/advanced",
        {"language_code": "en", "location_code": location_code},
    )


def test_dataforseo_still_requires_english_and_exact_endpoint():
    assert not _dataforseo_request_valid(
        "dataforseo://serp/google/organic/live/advanced",
        {"language_code": "de", "location_code": 2826},
    )
    assert not _dataforseo_request_valid(
        "dataforseo://serp/google/organic/live/basic",
        {"language_code": "en", "location_code": 2826},
    )


# Chrome connector collector. Mirrors the answersocrates_chrome_connector
# precedent already present in paa_provenance/contracts.py, so a browser
# connector capture records its own provenance instead of borrowing
# Playwright's.

CHROME_COLLECTOR = {
    "name": "research_serp_analysis:chrome_connector",
    "version": "1.0.0",
}


def test_chrome_connector_is_an_approved_serp_collector():
    from data_sources.modules.editorial_plan.contracts import (
        SERP_APPROVED_COLLECTORS,
    )

    assert (
        "research_serp_analysis:chrome_connector",
        "1.0.0",
    ) in SERP_APPROVED_COLLECTORS


@pytest.mark.parametrize("gl", ["us", "gb", "uk", "au", "nz", "ca", "ie"])
def test_chrome_connector_accepts_supported_markets(gl):
    from data_sources.modules.editorial_plan.serp_capture import (
        _validate_capture_request,
    )

    _validate_capture_request(
        {
            "query": QUERY,
            "request": {
                "url": PLAYWRIGHT_URL.format(gl=gl),
                "locale": {"hl": "en", "gl": gl, "pws": "0"},
            },
        },
        CHROME_COLLECTOR,
    )


def test_chrome_connector_rejects_unapproved_locale_and_host():
    from data_sources.modules.editorial_plan.serp_capture import (
        _validate_capture_request,
    )

    with pytest.raises(ValueError):
        _validate_capture_request(
            {
                "query": QUERY,
                "request": {
                    "url": PLAYWRIGHT_URL.format(gl="de"),
                    "locale": {"hl": "en", "gl": "de", "pws": "0"},
                },
            },
            CHROME_COLLECTOR,
        )
    with pytest.raises(ValueError):
        _validate_capture_request(
            {
                "query": QUERY,
                "request": {
                    "url": "https://www.bing.com/search?q=x&gl=uk&pws=0",
                    "locale": {"hl": "en", "gl": "uk", "pws": "0"},
                },
            },
            CHROME_COLLECTOR,
        )


def test_serp_raw_module_shares_the_same_locale_contract():
    """serp_raw.py duplicates the validators; both copies must agree.

    serp_validation reaches the serp_raw copy, so a locale approved in
    serp_capture but not here silently fails at evidence build time.
    """
    from data_sources.modules.editorial_plan import serp_capture, serp_raw

    for gl in ("us", "gb", "uk", "au", "nz", "ca", "ie"):
        locale = {"hl": "en", "gl": gl, "pws": "0"}
        url = PLAYWRIGHT_URL.format(gl=gl)
        assert serp_capture._playwright_request_valid(
            url, locale, query=QUERY
        ) is serp_raw._playwright_request_valid(url, locale, query=QUERY)
    for db in ("us", "uk", "au", "de"):
        assert serp_capture._semrush_request_valid(
            "semrush://keyword/phrase_organic", {"database": db}
        ) is serp_raw._semrush_request_valid(
            "semrush://keyword/phrase_organic", {"database": db}
        )
    for code in (2840, 2826, 2036, 2276):
        locale = {"language_code": "en", "location_code": code}
        assert serp_capture._dataforseo_request_valid(
            "dataforseo://serp/google/organic/live/advanced", locale
        ) is serp_raw._dataforseo_request_valid(
            "dataforseo://serp/google/organic/live/advanced", locale
        )


def test_build_serp_evidence_end_to_end_for_a_uk_chrome_connector_capture(tmp_path):
    """End-to-end through the real entry point, not just the unit validators."""
    from data_sources.modules.blog_assembly_contract import atomic_write_json
    from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
    from data_sources.modules.execution_attestation import attest_mapping

    (tmp_path / "research").mkdir()
    raw_path = tmp_path / "research" / "serp-raw-uk-chrome.json"
    capture = attest_mapping(
        {
            "schema": "simpro-serp-raw-capture/v1",
            "collector": {
                "name": "research_serp_analysis:chrome_connector",
                "version": "1.0.0",
            },
            "query": QUERY,
            "collected_at": "2026-09-18T12:00:00Z",
            "run_id": "uk-chrome-run",
            "request": {
                "url": PLAYWRIGHT_URL.format(gl="uk"),
                "locale": {"hl": "en", "gl": "uk", "pws": "0"},
            },
            "raw_response": {
                "organic_results": [
                    {
                        "title": "Example result",
                        "url": "https://example.com",
                        "description": "Observed in the UK SERP.",
                    }
                ],
                "features": ["People also ask"],
            },
        },
        purpose="simpro-serp-raw-capture/v1",
        workspace_root=tmp_path,
    )
    atomic_write_json(raw_path, capture)

    evidence = build_serp_evidence(
        raw_capture_path=raw_path,
        workspace_root=tmp_path,
        must_have_sections=["a section"],
        competitor_gaps=["a gap"],
    )

    assert evidence["status"] == "verified"
    assert evidence["collector"]["name"] == "research_serp_analysis:chrome_connector"
    assert len(evidence["results"]) == 1


def test_chrome_connector_still_binds_the_query():
    from data_sources.modules.editorial_plan.serp_capture import (
        _validate_capture_request,
    )

    with pytest.raises(ValueError):
        _validate_capture_request(
            {
                "query": "a different query",
                "request": {
                    "url": PLAYWRIGHT_URL.format(gl="uk"),
                    "locale": {"hl": "en", "gl": "uk", "pws": "0"},
                },
            },
            CHROME_COLLECTOR,
        )


def test_uk_capture_from_the_documented_collector_is_approved():
    """research-serp.md documents the UK run as --google-country gb.

    scripts/research_serp_analysis.py passes that value straight into
    locale["gl"], so a UK capture from the documented path arrives as "gb".
    Accepting only the repo's "uk" market label left that path blocked.
    """
    assert _playwright_request_valid(
        PLAYWRIGHT_URL.format(gl="gb"),
        {"hl": "en", "gl": "gb", "pws": "0"},
        query=QUERY,
    )


def test_declared_locale_must_agree_with_the_fetched_url():
    """A capture cannot claim one market while requesting another.

    The validator reads gl from the locale mapping; with the market variable
    rather than hardcoded to US, an unchecked URL could name a different one.
    """
    from data_sources.modules.editorial_plan import serp_capture, serp_raw

    mismatched_url = PLAYWRIGHT_URL.format(gl="de")
    locale = {"hl": "en", "gl": "gb", "pws": "0"}
    for module in (serp_capture, serp_raw):
        assert not module._playwright_request_valid(
            mismatched_url, locale, query=QUERY
        )
        assert module._playwright_request_valid(
            PLAYWRIGHT_URL.format(gl="gb"), locale, query=QUERY
        )
