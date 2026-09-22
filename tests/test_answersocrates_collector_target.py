"""The collector must drive the page and control that actually exist.

Two faults made every Playwright run return zero questions even when it
completed:

* it targeted `/paa-extractor`, whose headings never include "People Also Ask" --
  the section `observations.py` requires -- while the main page does carry it;
* it clicked a button matching /search|extract|submit|get questions/i, but the
  live control reads "Analyze Questions" (recorded in
  research/raw-answersocrates-operational-accountability-field-service-2026-09-17.json:19).

The existing collection test could not catch either one: it stubs the
subprocess runner and hand-feeds a fixture, so the page and the button are
never exercised.
"""

import re

from data_sources.modules.paa_provenance.collection import (
    _answersocrates_extraction_code,
)
from data_sources.modules.paa_provenance.contracts import (
    ANSWERSOCRATES_COLLECTOR_PAGE_URL,
    ANSWERSOCRATES_PAGE_URL,
    ANSWERSOCRATES_PAGE_URLS,
    ANSWERSOCRATES_SUBMIT_BUTTON_PATTERN,
)

LIVE_SUBMIT_LABEL = "Analyze Questions"


def test_submit_pattern_matches_the_live_control():
    assert re.search(ANSWERSOCRATES_SUBMIT_BUTTON_PATTERN, LIVE_SUBMIT_LABEL, re.I)


def test_submit_pattern_still_matches_the_previously_known_labels():
    """Widening the pattern must not drop labels the tool used before."""
    for label in ("Search", "Extract", "Submit", "Get Questions"):
        assert re.search(ANSWERSOCRATES_SUBMIT_BUTTON_PATTERN, label, re.I), label


def test_collector_targets_the_page_that_carries_the_paa_heading():
    assert ANSWERSOCRATES_COLLECTOR_PAGE_URL == "https://answersocrates.com/"


def test_extraction_code_navigates_to_the_collector_page():
    code = _answersocrates_extraction_code("hvac technician scheduling")

    # Exact quoted target: the extractor URL contains the main URL as a prefix.
    assert '"https://answersocrates.com/"' in code
    assert "paa-extractor" not in code


def test_extraction_code_clicks_the_live_control():
    code = _answersocrates_extraction_code("hvac technician scheduling")

    assert ANSWERSOCRATES_SUBMIT_BUTTON_PATTERN in code


def test_both_page_urls_stay_accepted_for_historical_captures():
    """Captures already recorded against /paa-extractor must remain valid."""
    assert ANSWERSOCRATES_PAGE_URL == "https://answersocrates.com/paa-extractor"
    assert ANSWERSOCRATES_PAGE_URLS == {
        "https://answersocrates.com/paa-extractor",
        "https://answersocrates.com/",
    }
