from __future__ import annotations

import pytest

from data_sources.modules.proof_link_policy import (
    analyze_proof_links,
    canonicalize_link_identity,
)
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


def test_canonicalize_link_identity_removes_tracking_fragments_and_default_ports():
    assert canonicalize_link_identity(
        "HTTPS://Example.COM:443/rules/?utm_source=newsletter&chapter=2#fees"
    ) == "https://example.com/rules?chapter=2"
    assert canonicalize_link_identity(
        "http://Example.com:80/Rules/?fbclid=abc"
    ) == "http://example.com/Rules"


def test_link_inventory_counts_distinct_external_urls_without_fragment_links():
    article = """# Guide

[first authority](https://example.org/rules?utm_source=email)
[same authority](https://EXAMPLE.org/rules#renewal)
[second authority](https://regulator.gov/license)
[body section](#requirements)
[email](mailto:licensing@example.org)
[phone](tel:+15551234567)
[owned guide](https://www.simprogroup.com/blog/licensing-guide)
"""

    report = analyze_proof_links(article, brand="Simpro")

    assert report.external_occurrences == 3
    assert report.distinct_external_urls == (
        "https://example.org/rules",
        "https://regulator.gov/license",
    )
    assert report.internal_occurrences == 1


def test_link_inventory_counts_only_reader_visible_links_and_preserves_claim_lines():
    article = """---
brand: Simpro
canonical_url: https://frontmatter.example.org/guide
---
# License guide

![Hidden linked image](https://images.example.org/license.png)
<!--
[hidden comment link](https://comments.example.org/license)
-->

```markdown
[hidden backtick fence](https://code.example.org/backticks)
```
~~~text
https://code.example.org/tildes
~~~

Licenses [must be renewed annually](https://regulator.gov/renewal).
[Owned guide](https://www.simprogroup.com/blog/license-guide)
[Fragment](#renewal)
[Email](mailto:licensing@example.org)
[Phone](tel:+15551234567)
"""
    sidecar = """## Source Map
- Claim: Licenses must be renewed annually. | Claim type: process | Source class: primary_authority | URL: https://regulator.gov/renewal | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")
    requirement = next(row for row in report.requirements if row.owner == "public_research")

    assert report.external_occurrences == 1
    assert report.distinct_external_urls == ("https://regulator.gov/renewal",)
    assert report.internal_occurrences == 1
    assert report.distinct_internal_urls == (
        "https://www.simprogroup.com/blog/license-guide",
    )
    assert [(link.canonical_url, link.line) for link in report.links] == [
        ("https://regulator.gov/renewal", 19),
        ("https://www.simprogroup.com/blog/license-guide", 20),
    ]
    assert requirement.line == 19
    assert requirement.visible_urls == ("https://regulator.gov/renewal",)


def test_link_inventory_reads_non_simpro_brand_from_frontmatter():
    article = """---
brand: AroFlo
---
# Guide

[AroFlo feature](https://www.aroflo.com/features)
[Simpro feature](https://www.simprogroup.com/features)
[authority](https://example.org/rules)
"""

    report = analyze_proof_links(article)

    assert report.internal_occurrences == 1
    assert report.external_occurrences == 1
    assert report.distinct_internal_urls == ("https://www.aroflo.com/features",)


def test_legal_claim_requires_matching_natural_anchor_in_same_paragraph():
    article = """# Texas plumbing license

## Renewal

Texas plumbing licenses must be renewed every year.

Read the [TSBPE renewal guidance](https://tsbpe.texas.gov/applyrenew-online/).
"""
    sidecar = """## Source Map
- Claim: Texas plumbing licenses must be renewed every year. | Claim type: process | Source class: primary_authority | Evidence relation: directly_supports | URL: https://tsbpe.texas.gov/applyrenew-online/ | Evidence: "renew annually" | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")

    requirement = next(row for row in report.requirements if "renewed every year" in row.claim)
    assert requirement.mode == "inline_required"
    assert requirement.owner == "public_research"
    assert requirement.approved_urls == ("https://tsbpe.texas.gov/applyrenew-online",)
    assert requirement.visible_urls == ()


def test_markdown_table_row_is_a_valid_inline_decision_unit():
    article = """# Texas plumbing license

| License | Requirement |
|---|---|
| [Journeyman Plumber requirements](https://tsbpe.texas.gov/license-types/journeyman-plumber/) | Texas requires 8,000 hours of registered experience. |
"""
    sidecar = """## Source Map
- Claim: Texas requires 8,000 hours of registered experience. | Claim type: process | Source class: primary_authority | Evidence relation: directly_supports | URL: https://tsbpe.texas.gov/license-types/journeyman-plumber/ | Evidence: "8,000 hours" | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")

    requirement = next(row for row in report.requirements if "8,000 hours" in row.claim)
    assert requirement.mode == "inline_required"
    assert requirement.owner == "numeric_claim"
    assert requirement.visible_urls == (
        "https://tsbpe.texas.gov/license-types/journeyman-plumber",
    )


def test_ordered_list_step_markers_do_not_create_material_numeric_requirements():
    article = """# Texas plumbing license

## Applying through TSBPE

Use the [TSBPE application guidance](https://tsbpe.texas.gov/applyrenew-online/) for the online path.

1. Create an online account with an email address you control.
2. Add an existing registration or license when applicable.
3. Select the application action for the credential you need.
4. Submit the required identity, background, experience, and training materials.
5. Pay the TSBPE charge shown for that action.
6. If an exam is required, wait for approval before scheduling. Master applicants pay Pearson VUE separately.
"""
    sidecar = """## Source Map
- Claim: Submit the required identity, background, experience, and training materials. | Claim type: process | Source class: primary_authority | Evidence relation: directly_supports | URL: https://tsbpe.texas.gov/applyrenew-online/ | Evidence: "complete applications online" | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")

    requirement = next(
        row
        for row in report.requirements
        if row.claim == "Submit the required identity, background, experience, and training materials."
    )
    assert requirement.mode == "section_source_allowed"
    assert requirement.visible_urls == ("https://tsbpe.texas.gov/applyrenew-online",)
    assert [
        row
        for row in report.requirements
        if row.owner == "numeric_claim"
    ] == []


def test_create_log_checklist_without_external_fact_needs_no_public_proof():
    article = """# License guide

## Experience

Create a simple experience log before details fade. Record the employer, worksite dates, supervisor's name and license level, and the type of plumbing work performed. Compare that log with employer records periodically.
"""

    report = analyze_proof_links(article, "", brand="Simpro")

    assert len(report.requirements) == 1
    assert report.requirements[0].mode == "proof_not_required"


def test_regulatory_navigation_advice_without_material_number_needs_no_public_proof():
    article = """# License guide

## Applying

Before submitting, compare processing, examination, initial-license, and renewal charges on the credential page.

## Homestead work

Ask the local permitting office before starting homestead work.

## Renewal

Verify the public record before treating a credential as current after online payment.
"""

    report = analyze_proof_links(article, "", brand="Simpro")

    assert len(report.requirements) == 3
    assert {requirement.mode for requirement in report.requirements} == {"proof_not_required"}


def test_mapped_navigation_recommendation_with_risk_words_stays_sidecar_only():
    article = """# License guide

## Applying

Before submitting, compare processing, examination, initial-license, and renewal charges on the credential page.
"""
    sidecar = """## Source Map
- Claim: Before submitting, compare processing, examination, initial-license, and renewal charges on the credential page. | Claim type: recommendation | Source class: primary_authority | Evidence relation: directly_supports | URL: https://regulator.gov/licenses | Evidence: To obtain a license, take an exam and pay a fee. | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")

    assert len(report.requirements) == 1
    assert report.requirements[0].mode == "sidecar_only"


def test_low_risk_definition_can_use_one_mapped_source_in_same_section():
    article = """# Dispatch guide

## What dispatching means

Dispatching is a process for assigning work to available field technicians.

The [field operations definition](https://example.org/field-dispatch) explains the workflow.
"""
    sidecar = """## Source Map
- Claim: Dispatching is a process for assigning work to available field technicians. | Claim type: definitional | Source class: non_competing_expert | Evidence relation: directly_supports | URL: https://example.org/field-dispatch | Evidence: "assigning work" | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")

    requirement = next(row for row in report.requirements if row.claim.startswith("Dispatching"))
    assert requirement.mode == "section_source_allowed"
    assert requirement.visible_urls == ("https://example.org/field-dispatch",)


def test_fact_driven_faq_requires_natural_proof_in_first_visible_paragraph():
    article = """# Texas plumbing license

## Frequently asked questions

### Which agency regulates plumbers in Texas?

The Texas State Board of Plumbing Examiners regulates plumbers in Texas.

The [official TSBPE licensing page](https://tsbpe.texas.gov/license-types/) lists the regulated license types.
"""
    sidecar = """## FAQ Source Policy
- Allowed source classes: neutral, non_competing_expert.
- Competitor-owned FAQ sources: prohibited.
- Status: aligned.

## FAQ Proof Map
- FAQ: Which agency regulates plumbers in Texas? | URL: https://tsbpe.texas.gov/license-types/ | Source class: neutral | Competitor check: passed | Support: The regulator identifies its licensing authority.
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")

    requirement = next(row for row in report.requirements if row.owner == "faq")
    assert requirement.mode == "inline_required"
    assert requirement.visible_urls == ()


def test_navigation_faq_is_machine_classified_as_proof_not_required():
    article = """# Application guide

## Frequently asked questions

### Where can I start the application?

Use the application link in the section above, then follow the on-screen steps.
"""

    report = analyze_proof_links(article, brand="Simpro")

    requirement = next(row for row in report.requirements if row.owner == "faq")
    assert requirement.mode == "proof_not_required"
    assert requirement.approved_urls == ()


def test_personal_advice_faq_is_sidecar_only_without_a_quota_link():
    article = """# Dispatch guide

## Frequently asked questions

### How do I choose a daily planning routine?

You should choose a routine that your team can repeat consistently.
"""

    report = analyze_proof_links(article, brand="Simpro")

    requirement = next(row for row in report.requirements if row.owner == "faq")
    assert requirement.mode == "sidecar_only"


def test_comparative_best_faq_cannot_be_downgraded_to_advice():
    article = """# Software guide

## Frequently asked questions

### Which field service software is best?

Simpro is the best field service platform for every trade business.
"""

    report = analyze_proof_links(article, brand="Simpro")

    requirement = next(row for row in report.requirements if row.owner == "faq")
    assert requirement.mode == "inline_required"
    assert requirement.visible_urls == ()


def test_images_comments_table_headers_and_navigation_advice_do_not_create_claims():
    article = """# License guide

![Texas license pathway](IMAGE_PLACEHOLDER)
<!-- Original license image source: https://example.com/license-image.jpg -->

## Requirements

| License | Current fees | Renewal |
|---|---|---|

## Next steps

Match your next license to your intended work, then visit the official application page.
"""

    report = analyze_proof_links(article, brand="Simpro")

    assert len(report.requirements) == 1
    assert report.requirements[0].mode == "proof_not_required"
    assert report.requirements[0].reason == "navigation_or_nonfactual_advice"


def test_operational_navigation_checklists_are_proof_not_required():
    article = """# License guide

## Renewal

- Confirm the credential status and expiration date in the online account.
- Complete continuing education through an approved provider.
- For an RMP record, confirm insurance and business information.

Contact the board before treating an expired or unchanged record as current.

Start renewal planning before the online window. Locate the account record and resolve discrepancies early.

## Verification

Review these fields before assigning plumbing work.

## Next step

Use the regulator license pages to recheck current eligibility, training, examinations, and fees. Treat the current instructions as controlling.
"""

    report = analyze_proof_links(article, brand="Simpro")
    relevant = [
        requirement
        for requirement in report.requirements
        if requirement.owner == "public_research"
    ]

    assert relevant
    assert {requirement.mode for requirement in relevant} == {"proof_not_required"}


@pytest.mark.parametrize(
    "article",
    (
        "# License guide\n\n## Experience records\n\nCreate a simple experience log before details fade. Record the employer, worksite dates, supervisor's name and license level, and the type of plumbing work performed. Compare that log with employer records periodically.\n",
        "# License guide\n\n## Renewal records\n\nMaintain one renewal record for each annual cycle. Keep the course completion record, account confirmation, payment receipt, and a note of the date you checked the public record. For an RMP renewal, keep the business and insurance documents used for that cycle with the same record.\n",
        "# License guide\n\n## Homestead records\n\nPrepare the property address, ownership status, and a plain-language description of the proposed work. Ask which permits, plans, inspections, or licensed-contractor steps apply to that address and project. File the local response with the project records instead of applying the homestead exception to a different property or job.\n",
        "# License guide\n\n## Homestead work\n\nApply the exemption only to the qualifying property and confirm local requirements before starting.\n",
        "# License guide\n\n## Next step\n\nUse the regulator's license pages to recheck eligibility, training, examinations, and fees before each application or renewal.\n",
    ),
)
def test_imperative_navigation_advice_examples_are_proof_not_required(article):
    report = analyze_proof_links(article, brand="Simpro")
    requirement = next(
        row for row in report.requirements if row.owner == "public_research"
    )

    assert requirement.mode == "proof_not_required"


def test_imperative_wording_does_not_hide_a_factual_licensing_rule():
    article = """# License guide

## Renewal

Use the regulator page because licenses must renew annually.
"""

    report = analyze_proof_links(article, brand="Simpro")
    requirement = next(
        row for row in report.requirements if row.owner == "public_research"
    )

    assert requirement.mode == "inline_required"


def test_unmapped_regulatory_assertion_still_fails_closed():
    article = """# License guide

## Renewal

Licensees must renew annually and complete six hours of education.
"""

    report = analyze_proof_links(article, brand="Simpro")

    requirement = next(row for row in report.requirements if row.owner == "public_research")
    assert requirement.mode == "inline_required"


def test_later_regulatory_faq_claim_still_requires_first_paragraph_proof():
    article = """# Application guide

## Frequently asked questions

### Where should I start?

Start with the application checklist above.

Texas licenses must be renewed annually.
"""

    report = analyze_proof_links(article, brand="Simpro")

    requirement = next(row for row in report.requirements if row.owner == "faq")
    assert requirement.mode == "inline_required"
    assert requirement.visible_urls == ()


def test_direct_factual_question_forms_are_inline_required():
    questions_and_answers = (
        ("Who founded the association?", "Alex Morgan in 1998."),
        ("What are common dispatch workflows?", "Priority, route, and skill matching."),
        ("Which agency oversees the trade?", "The State Trade Board."),
        ("Where is the application filed?", "The state licensing portal."),
    )
    entries = "\n\n".join(
        f"### {question}\n\n{answer}" for question, answer in questions_and_answers
    )
    article = f"# Guide\n\n## Frequently asked questions\n\n{entries}\n"

    report = analyze_proof_links(article, brand="Simpro")

    assert {
        requirement.faq_question: requirement.mode
        for requirement in report.requirements
        if requirement.owner == "faq"
    } == {question: "inline_required" for question, _answer in questions_and_answers}


def test_required_proof_rejects_generic_anchor_and_reports_redundant_citations():
    article = """# License guide

## Renewal

Licenses must be renewed annually under the [source](https://regulator.gov/renewal).

The [renewal rules](https://regulator.gov/renewal#deadlines) explain the filing window.
"""
    sidecar = """## Source Map
- Claim: Licenses must be renewed annually. | Claim type: process | Source class: primary_authority | Evidence relation: directly_supports | URL: https://regulator.gov/renewal | Evidence: "renewed annually" | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")

    assert [link.anchor for link in report.generic_anchors] == ["source"]
    assert len(report.redundant_citations) == 1
    assert report.redundant_citations[0].canonical_url == "https://regulator.gov/renewal"


def test_low_risk_recommendation_is_sidecar_only_and_unknown_claim_fails_closed():
    article = """# Dispatch guide

## Plan the day

Dispatchers should review technician capacity before assigning urgent work.

Falcon mode changes customer pricing immediately.
"""
    sidecar = """## Source Map
- Claim: Dispatchers should review technician capacity before assigning urgent work. | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | URL: https://example.org/dispatch | Evidence: "review technician capacity" | Status: approved
- Claim: Falcon mode changes customer pricing immediately. | Claim type: mystery | Source class: unknown | Evidence relation: directly_supports | URL: https://example.org/falcon | Evidence: "changes pricing" | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")
    by_claim = {requirement.claim: requirement for requirement in report.requirements}

    assert by_claim[
        "Dispatchers should review technician capacity before assigning urgent work."
    ].mode == "sidecar_only"
    assert by_claim["Falcon mode changes customer pricing immediately."].mode == "inline_required"


def test_recommendation_about_technician_availability_remains_sidecar_only():
    article = """# Dispatch guide

## Plan the day

Dispatchers should review technician availability before assigning urgent work.
"""
    sidecar = """## Source Map
- Claim: Dispatchers should review technician availability before assigning urgent work. | Claim type: recommendation | Source class: non_competing_expert | URL: https://example.org/dispatch | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")
    requirement = next(row for row in report.requirements if row.claim.startswith("Dispatchers"))

    assert requirement.mode == "sidecar_only"


def test_specialist_proof_rows_have_exclusive_guard_owners():
    article = """# Proof guide

## Evidence

Acme reported that crews completed twice as many jobs.

A named reviewer described faster invoice follow-up.

Fred Voccola said connected operations improve visibility.

Lightning is currently available to eligible accounts.
"""
    sidecar = """## Source Map
- Claim: Acme reported that crews completed twice as many jobs. | Claim type: outcome | Source class: customer_proof | URL: https://www.simprogroup.com/case-studies/acme | Status: approved | Use: customer metric
- Claim: A named reviewer described faster invoice follow-up. | Claim type: experience | Source class: review_platform | URL: https://example.org/reviews | Status: approved | Use: review story
- Claim: Fred Voccola said connected operations improve visibility. | Claim type: observation | Source class: fred_authority | URL: https://example.org/fred | Status: approved | Use: Fred observation
- Claim: Lightning is currently available to eligible accounts. | Claim type: product_status | Source class: named_feature_status | URL: https://www.simprogroup.com/lightning | Status: approved | Use: named feature status
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")
    owners = {requirement.claim: requirement.owner for requirement in report.requirements}

    assert owners["Acme reported that crews completed twice as many jobs."] == "customer_proof"
    assert owners["A named reviewer described faster invoice follow-up."] == "review_story"
    assert owners["Fred Voccola said connected operations improve visibility."] == "fred_authority"
    assert owners["Lightning is currently available to eligible accounts."] == "named_feature_status"


def test_bare_required_url_is_a_generic_anchor():
    article = """# License guide

## Renewal

Licenses must be renewed annually: https://regulator.gov/renewal
"""
    sidecar = """## Source Map
- Claim: Licenses must be renewed annually: https://regulator.gov/renewal | Claim type: process | Source class: primary_authority | URL: https://regulator.gov/renewal | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")

    assert len(report.generic_anchors) == 1
    assert report.generic_anchors[0].anchor == ""


def test_separate_required_claim_bindings_allow_reusing_one_source_in_an_h2():
    article = """# License guide

## Renewal

Licenses [must be renewed annually](https://regulator.gov/renewal).

Late renewals follow the [same renewal rules](https://regulator.gov/renewal#late).
"""
    sidecar = """## Source Map
- Claim: Licenses must be renewed annually. | Claim type: process | Source class: primary_authority | URL: https://regulator.gov/renewal | Status: approved
- Claim: Late renewals follow the same renewal rules. | Claim type: process | Source class: primary_authority | URL: https://regulator.gov/renewal | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")

    assert report.redundant_citations == ()


def test_one_mapped_claim_does_not_hide_an_unmapped_high_risk_claim_in_same_paragraph():
    article = """# License guide

## Renewal

Licenses [must be renewed annually](https://regulator.gov/renewal), and a separate late-renewal fee applies.
"""
    sidecar = """## Source Map
- Claim: Licenses must be renewed annually. | Claim type: process | Source class: primary_authority | URL: https://regulator.gov/renewal | Status: approved
"""

    report = analyze_proof_links(article, sidecar, brand="Simpro")
    requirements = [
        requirement
        for requirement in report.requirements
        if requirement.line == 5 and requirement.owner == "public_research"
    ]

    assert len(requirements) == 2
    assert any(
        requirement.reason == "high_risk_public_claim_without_matching_proof"
        and requirement.approved_urls == ()
        for requirement in requirements
    )


def test_approved_and_visible_urls_share_resolved_redirect_identity():
    old_url = "http://regulator.gov/renewal/"
    final_url = "https://regulator.gov/renewal"
    article = f"""# License guide

## Renewal

Licenses [must be renewed annually]({old_url}).
"""
    sidecar = f"""## Source Map
- Claim: Licenses must be renewed annually. | Claim type: process | Source class: primary_authority | URL: {old_url} | Status: approved
"""
    summary = UrlValidationSummary(
        [
            UrlValidationResult(
                url=old_url,
                status="resolved",
                status_code=200,
                reason="HTTP 200",
                line=5,
                anchor="must be renewed annually",
                final_url=final_url,
            )
        ]
    )

    report = analyze_proof_links(article, sidecar, brand="Simpro", url_summary=summary)
    requirement = next(row for row in report.requirements if row.owner == "public_research")

    assert requirement.approved_urls == (final_url,)
    assert requirement.visible_urls == (final_url,)
