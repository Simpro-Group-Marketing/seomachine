from __future__ import annotations

import hashlib
import json

import pytest

from data_sources.modules.wording_edit import classify_wording_edit


BEFORE = """---
artifact_type: blog
title: Dispatch board guide
---
# Dispatch board guide

Dispatchers can see every open job in one place; the board shows each technician's day.

## How the board works

The board groups jobs by technician and shows 3 status colors for each visit.

Read the [scheduling overview](https://www.simprogroup.com/features/scheduling) before you start.

[IMAGE PLACEHOLDER | source: https://cdn.example.com/board.png | alt: "Dispatch board" | render target: 1200 x 630 px | resize and compress before upload]

## FAQs

### How many status colors does the board use?

The board uses 3 status colors so dispatchers can spot late visits quickly and reassign work before customers notice a delay in the schedule today.
"""

SIDECAR = """## Source Map
- Claim: The board groups jobs by technician and shows 3 status colors for each visit. | Claim type: product_claim | Source class: owned_product | URL: https://www.simprogroup.com/features/scheduling | Evidence: "status colors" | Status: approved

## Context Claim Use Map
```json
[{"claim_id": "claim-board", "public_text": "Read the scheduling overview before you start."}]
```
"""


def _report(after: str, *, before: str = BEFORE, sidecar: str = SIDECAR):
    return classify_wording_edit(before, after, sidecar=sidecar)


def test_modal_verb_and_semicolon_fix_is_wording_only():
    after = BEFORE.replace(
        "Dispatchers can see every open job in one place; the board shows each technician's day.",
        "Dispatchers see every open job in one place. The board shows each technician's day.",
    )

    report = _report(after)

    assert report.violations == ()
    assert 0 < report.changed_words <= 4
    assert report.body_words > 50


@pytest.mark.parametrize(
    ("violation", "old", "new"),
    [
        ("frontmatter", "title: Dispatch board guide", "title: Dispatch board basics"),
        ("headings", "## How the board works", "## How the dispatch board works"),
        (
            "links",
            "[scheduling overview](https://www.simprogroup.com/features/scheduling)",
            "[scheduling page](https://www.simprogroup.com/features/scheduling)",
        ),
        ("numbers", "shows 3 status colors for each visit", "shows 4 status colors for each visit"),
        ("faq_questions", "### How many status colors does the board use?", "### Which status colors does the board use?"),
        ("media_placeholders", 'alt: "Dispatch board"', 'alt: "The dispatch board"'),
        (
            "proof_claims",
            "The board groups jobs by technician and shows 3 status colors for each visit.",
            "The board sorts jobs by technician and shows 3 status colors for each visit.",
        ),
    ],
)
def test_structural_or_proof_change_is_not_wording_only(violation, old, new):
    assert BEFORE.count(old) == 1
    report = _report(BEFORE.replace(old, new))

    assert violation in report.violations


def test_quote_change_is_not_wording_only():
    before = BEFORE.replace(
        "Dispatchers can see", 'One owner said "the board is where our whole day starts" and dispatchers can see'
    )
    after = before.replace("whole day starts", "entire day starts")

    assert "quotes" in _report(after, before=before).violations


def test_context_claim_passage_must_still_occur_exactly_once():
    sidecar = SIDECAR.replace(
        "Read the scheduling overview before you start.",
        "Dispatchers can see every open job in one place",
    )
    after = BEFORE.replace("Dispatchers can see every open job", "Dispatchers see every open job")

    assert "context_claim_passages" in _report(after, sidecar=sidecar).violations


def test_changed_words_counts_every_replaced_or_inserted_word():
    after = BEFORE.replace(
        "the board shows each technician's day.",
        "the board shows what each technician is doing for the rest of the working day.",
    )

    report = _report(after)

    assert report.violations == ()
    assert report.changed_words >= 10


def test_report_payload_is_canonical_json():
    after = BEFORE.replace("Dispatchers can see", "Dispatchers see")

    payload = _report(after).as_payload()

    assert payload["before_sha256"] == hashlib.sha256(BEFORE.encode()).hexdigest()
    assert payload["after_sha256"] == hashlib.sha256(after.encode()).hexdigest()
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload
