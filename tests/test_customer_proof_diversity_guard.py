import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.customer_proof_diversity_guard import (
    check_content,
    check_file,
    should_fail,
)
from data_sources.modules.customer_proof_selector import _main as selector_main


ARTICLE_WITH_CASE_STUDY = """# Job quoting software

[TEAMWired](https://www.simprogroup.com/case-studies/teamwired) is used as customer proof for invoicing workflow context.
"""


def proof_slate(
    *,
    metric_selected: str = "case-study-teamwired",
    quote_selected: str = "none",
    theme_selected: str = "case-study-teamwired",
    metric_top: str = "case-study-teamwired",
    quote_top: str = "case-study-teamwired",
    theme_top: str = "case-study-teamwired",
    metric_rejected: str = "none",
    quote_rejected: str = "none",
    theme_rejected: str = "none",
    include_experience_story: bool = False,
) -> str:
    rows = [
        "Customer Proof Slate",
        '- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric --limit 10',
        f"- Role: metric | Top candidates: [{metric_top}] | Selected: [{metric_selected}] | Rejected stronger candidates: [{metric_rejected}]",
        f"- Role: quote | Top candidates: [{quote_top}] | Selected: [{quote_selected}] | Rejected stronger candidates: [{quote_rejected}]",
        f"- Role: theme | Top candidates: [{theme_top}] | Selected: [{theme_selected}] | Rejected stronger candidates: [{theme_rejected}]",
    ]
    if include_experience_story:
        rows.append(
            "- Role: experience_story | Top candidates: [review-capterra-owner-quote-invoice] | Selected: [review-capterra-owner-quote-invoice] | Rejected stronger candidates: [none]"
        )
    return "\n".join(rows) + "\n\n"


def proof_mining(
    *,
    usable_quotes: str = "none found",
    usable_metrics: str = "none found",
    usable_pov: str = "none found",
    recommended_use: str = "theme",
    final_use: str = "paraphrased case-study theme proof only",
    excluded_proof: str = "none",
    include_checked_for: bool = True,
    include_recommended_use: bool = True,
    include_final_use: bool = True,
    include_status: bool = True,
    include_usable_quotes: bool = True,
    include_usable_metrics: bool = True,
) -> str:
    rows = [
        "Selected Customer Proof Mining",
        "- Proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired",
    ]
    if include_checked_for:
        rows.append("- Checked for: exact quotes, customer metrics, POV story, workflow themes")
    if include_usable_quotes:
        rows.append(f"- Usable quotes found: {usable_quotes}")
    if include_usable_metrics:
        rows.append(f"- Usable metrics found: {usable_metrics}")
    rows.append(f"- Usable POV/story found: {usable_pov}")
    if include_recommended_use:
        rows.append(f"- Recommended use: {recommended_use}")
    if include_final_use:
        rows.append(f"- Final use in copy: {final_use}")
    rows.append(f"- Excluded proof: {excluded_proof}")
    if include_status:
        rows.append("- Status: approved")
    return "\n".join(rows) + "\n\n"


class CustomerProofDiversityGuardTests(unittest.TestCase):
    def test_only_case_studies_without_non_case_study_search_attempt_fails(self):
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Approved quotes: none used.
- Review-site experience evidence: none collected.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: none.
"""

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(any(f["rule_id"] == "customer_proof_non_case_study_attempt_missing" for f in findings))
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_customer_proof_without_mining_block_fails(self):
        sidecar = proof_slate() + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(any(f["rule_id"] == "selected_customer_proof_mining_missing" for f in findings))

    def test_mining_block_missing_required_fields_fails(self):
        sidecar = proof_slate() + proof_mining(
            include_checked_for=False,
            include_recommended_use=False,
            include_final_use=False,
            include_status=False,
        ) + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        missing = [f for f in findings if f["rule_id"] == "selected_customer_proof_mining_required_field_missing"]
        self.assertGreaterEqual(len(missing), 4)

    def test_approved_quotes_none_requires_quote_mining_result(self):
        sidecar = proof_slate() + proof_mining(include_usable_quotes=False) + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Approved quotes: none used.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(any(f["rule_id"] == "selected_customer_proof_mining_quote_result_missing" for f in findings))

    def test_usable_quote_omitted_without_rejection_reason_warns(self):
        sidecar = proof_slate() + proof_mining(
            usable_quotes="Joel Anderson quote about quote-to-job workflow is usable if an exact quote is selected",
            excluded_proof="none",
        ) + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Approved quotes: none used.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        warning = next(
            finding
            for finding in findings
            if finding["rule_id"] == "selected_customer_proof_mining_usable_proof_omitted"
        )
        self.assertEqual(warning["severity"], "warning")
        self.assertFalse(should_fail(findings, fail_on="error"))

    def test_usable_quote_omitted_with_rejection_reason_passes(self):
        sidecar = proof_slate() + proof_mining(
            usable_quotes="Joel Anderson quote about quote-to-job workflow is usable if an exact quote is selected",
            excluded_proof="exact Joel Anderson quote omitted because this section needs concise paraphrased workflow proof, not a quote block",
        ) + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Approved quotes: none used.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""
        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertEqual(findings, [])

    def test_repeated_case_study_without_reuse_reason_fails(self):
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof; no approved exact quote selected for public copy.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.
"""
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(any(f["rule_id"] == "customer_proof_reuse_requires_source_specific_reason" for f in findings))

    def test_documented_quote_matrix_and_reuse_reason_passes(self):
        sidecar = proof_slate() + proof_mining() + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof; no exact quote selected because no public-copy approval was recorded for this topic.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
- Reuse reason: case-study-teamwired remains the best public source-visible invoicing metric for this draft after non-case-study proof checks.
- Stronger underused candidates rejected: none found for the same invoicing role.
"""
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }
        index = {"version": 1, "proof": []}

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            index_path = Path(temp_dir) / "index.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            index_path.write_text(json.dumps(index), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=index_path,
            )

        self.assertEqual(findings, [])

    def test_selector_generated_slate_is_accepted_by_diversity_guard(self):
        article = """# Job quoting software

[Zebra Plumbing](https://www.simprogroup.com/case-studies/zebra-plumbing) is used as customer proof for onsite quoting workflow context.
"""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "index.json"
            ledger_path = root / "ledger.json"
            index_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "proof": [
                            {
                                "proof_id": "quote-matrix-zebra-plumbing-onsite-quoting",
                                "customer": "Zebra Plumbing",
                                "source_type": "quote_matrix",
                                "workflow_fit": ["quoting", "invoicing"],
                                "themes": ["onsite quoting"],
                                "public_url": "https://www.simprogroup.com/case-studies/zebra-plumbing",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "approved_metrics": [{"metric": "20x quoting", "status": "approved"}],
                            },
                            {
                                "proof_id": "quote-matrix-bwe-engineering-job-to-invoice",
                                "customer": "BWE Engineering",
                                "source_type": "quote_matrix",
                                "workflow_fit": ["job cards", "invoicing"],
                                "themes": ["job-to-invoice"],
                                "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "approved_quotes": [{"quote": "Approved quote", "status": "approved"}],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            buffer = StringIO()

            with redirect_stdout(buffer):
                selector_main(
                    [
                        "job quoting software",
                        "--index",
                        str(index_path),
                        "--ledger",
                        str(ledger_path),
                        "--slate",
                        "--roles",
                        "metric,quote,theme",
                        "--limit",
                        "3",
                    ]
                )

            sidecar = buffer.getvalue() + proof_mining(
                usable_metrics="20x quoting metric available for Zebra Plumbing",
                recommended_use="theme and metric if needed",
                final_use="paraphrased customer proof only",
                excluded_proof="metric proof omitted because this fixture only checks slate compatibility",
            ) + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Zebra Plumbing and BWE Engineering checked for quote-to-invoice proof.
- Case-study proof path: Zebra Plumbing, URL: https://www.simprogroup.com/case-studies/zebra-plumbing, supported theme: onsite quoting workflow.
- Review-site experience evidence: Capterra, https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/, date checked 2026-06-12, product: Simpro, experience pattern: quoting workflow, evidence summary: review themes checked, exact quote/rating approval status: not approved.
- Use in copy: paraphrased customer proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "job quoting software" --proof-role metric
- Selected proof: quote-matrix-zebra-plumbing-onsite-quoting | Customer: Zebra Plumbing | URL: https://www.simprogroup.com/case-studies/zebra-plumbing | Use: onsite quoting workflow proof
"""

            findings = check_content(
                article,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=index_path,
            )

        self.assertEqual([finding for finding in findings if finding["severity"] == "error"], [])

    def test_customer_proof_without_slate_fails(self):
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""

        findings = check_content(ARTICLE_WITH_CASE_STUDY, proof_content=sidecar)

        self.assertTrue(any(f["rule_id"] == "customer_proof_slate_missing" for f in findings))
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_selected_proof_missing_from_slate_fails(self):
        sidecar = proof_slate(
            metric_selected="quote-matrix-bwe-engineering-job-to-invoice",
            theme_selected="quote-matrix-bwe-engineering-job-to-invoice",
        ) + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""

        findings = check_content(ARTICLE_WITH_CASE_STUDY, proof_content=sidecar)

        self.assertTrue(any(f["rule_id"] == "customer_proof_selected_not_in_slate" for f in findings))

    def test_non_overused_selected_proof_with_stronger_slate_candidate_warns(self):
        sidecar = proof_slate(
            metric_top="quote-matrix-bwe-engineering-job-to-invoice, case-study-teamwired",
            metric_selected="case-study-teamwired",
        ) + proof_mining() + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof and found BWE Engineering.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""
        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        warning = next(
            finding
            for finding in findings
            if finding["rule_id"] == "customer_proof_stronger_slate_candidate_available"
        )
        self.assertEqual(warning["severity"], "warning")
        self.assertFalse(should_fail(findings, fail_on="error"))

    def test_stronger_slate_candidate_rejected_with_reason_passes(self):
        sidecar = proof_slate(
            metric_top="quote-matrix-bwe-engineering-job-to-invoice, case-study-teamwired",
            metric_selected="case-study-teamwired",
            metric_rejected="quote-matrix-bwe-engineering-job-to-invoice: rejected because this section needs security-specific invoicing proof",
        ) + proof_mining() + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof and found BWE Engineering.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""
        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertEqual(findings, [])

    def test_review_story_copy_requires_experience_story_slate_role(self):
        sidecar = proof_slate() + """Customer Proof Pack
- Pack status: ready.
- Review-site experience evidence: Capterra, https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/, date checked 2026-06-12, product: Simpro, experience pattern: quote-to-invoice workflow, evidence summary: reviewer discusses quotes and invoices, exact quote/rating approval status: not approved.
- Use in copy: paraphrased review story.
- Claims excluded: exact review quote.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "quote invoice review story" --proof-role experience_story --require-eeat-story
- Selected proof: review-capterra-owner-quote-invoice | Customer: Capterra owner review | URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/ | Use: review story proof

Review Story Selection
- Article title: Best job quoting and invoicing software
- Content objective: help trade buyers evaluate quote-to-cash workflow
- Selector command: python data_sources/modules/customer_proof_selector.py "quote invoice review story" --proof-role experience_story --require-eeat-story
- Selected story: review-capterra-owner-quote-invoice | Identity: Megan B | Platform: Capterra | URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/ | Workflow story: owner uses service jobs, recurring jobs, quotes, invoices, and QBO | Status: approved | Use: E-E-A-T experience story
"""

        findings = check_content(
            "# Reviews\n\nA [Capterra reviewer](https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) describes quote-to-invoice workflow.",
            proof_content=sidecar,
        )

        self.assertTrue(any(f["rule_id"] == "customer_proof_slate_experience_story_missing" for f in findings))

    def test_vague_global_reuse_reason_fails_for_repeated_proof(self):
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Reuse reason: repeated case studies remain useful.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.
"""
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(any(f["rule_id"] == "customer_proof_reuse_requires_source_specific_reason" for f in findings))

    def test_overused_proof_with_better_underused_candidate_fails_even_with_specific_reuse_reason(self):
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof and found BWE Engineering.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "job invoicing software" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
- Reuse reason: case-study-teamwired remains useful for invoicing workflow.
"""
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }
        index = {
            "version": 1,
            "proof": [
                {
                    "proof_id": "case-study-teamwired",
                    "customer": "TEAMWired",
                    "source_type": "case_study",
                    "workflow_fit": ["invoicing", "payments"],
                    "themes": ["manual invoicing"],
                    "public_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "approval_status": "approved",
                    "public_copy_allowed": True,
                    "approved_metrics": [{"claim": "TEAMWired manual invoicing time fell by 90%"}],
                },
                {
                    "proof_id": "quote-matrix-bwe-engineering-job-to-invoice",
                    "customer": "BWE Engineering",
                    "source_type": "quote_matrix",
                    "workflow_fit": ["job cards", "invoicing", "cash flow", "field service"],
                    "themes": ["job-to-invoice speed", "cash flow"],
                    "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
                    "approval_status": "approved",
                    "public_copy_allowed": True,
                    "approved_metrics": [{"claim": "BWE Engineering reduced job-to-invoice time by 50%"}],
                },
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            index_path = Path(temp_dir) / "index.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            index_path.write_text(json.dumps(index), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=index_path,
            )

        self.assertTrue(any(f["rule_id"] == "customer_proof_stronger_underused_candidate_available" for f in findings))

    def test_overused_proof_passes_when_stronger_underused_candidate_is_rejected_with_reason(self):
        sidecar = proof_slate(
            metric_top="quote-matrix-bwe-engineering-job-to-invoice, case-study-teamwired",
            metric_selected="case-study-teamwired",
            metric_rejected="quote-matrix-bwe-engineering-job-to-invoice: rejected because BWE is agricultural engineering, while this section specifically needs security contractor invoicing proof",
        ) + proof_mining() + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof and found BWE Engineering.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "security invoicing software" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: security invoicing workflow proof
- Reuse reason: case-study-teamwired remains the best security-specific invoicing proof for this section.
- Rejected stronger underused candidate: quote-matrix-bwe-engineering-job-to-invoice | Reason: rejected because BWE is agricultural engineering, while this section specifically needs security contractor invoicing proof.
"""
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }
        index = {
            "version": 1,
            "proof": [
                {
                    "proof_id": "case-study-teamwired",
                    "customer": "TEAMWired",
                    "source_type": "case_study",
                    "workflow_fit": ["invoicing", "payments"],
                    "themes": ["manual invoicing"],
                    "public_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "approval_status": "approved",
                    "public_copy_allowed": True,
                    "approved_metrics": [{"claim": "TEAMWired manual invoicing time fell by 90%"}],
                },
                {
                    "proof_id": "quote-matrix-bwe-engineering-job-to-invoice",
                    "customer": "BWE Engineering",
                    "source_type": "quote_matrix",
                    "workflow_fit": ["job cards", "invoicing", "cash flow", "field service"],
                    "themes": ["job-to-invoice speed", "cash flow"],
                    "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
                    "approval_status": "approved",
                    "public_copy_allowed": True,
                    "approved_metrics": [{"claim": "BWE Engineering reduced job-to-invoice time by 50%"}],
                },
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            index_path = Path(temp_dir) / "index.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            index_path.write_text(json.dumps(index), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=index_path,
            )

        self.assertEqual(findings, [])

    def test_reuse_threshold_counts_unique_article_slugs(self):
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": "same-article",
                    "artifact_path": f"artifact-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(5)
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertFalse(any(f["rule_id"].startswith("customer_proof_reuse") for f in findings))

    def test_missing_proof_index_fails_when_overused_selection_must_be_compared(self):
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: invoicing workflow, evidence summary: reviewers discuss invoice workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
- Reuse reason: case-study-teamwired remains the best invoicing proof.
"""
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            missing_index_path = Path(temp_dir) / "missing-index.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=missing_index_path,
            )

        self.assertTrue(any(f["rule_id"] == "customer_proof_index_missing" for f in findings))

    def test_overuse_baseline_triggers_reuse_guard_without_usage_rows(self):
        article = """# Job quoting software

[BGE Digital](https://www.simprogroup.com/case-studies/bge-digital) is used as customer proof for quoting workflow context.
"""
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof and found Zebra Plumbing.
- Case-study proof path: BGE Digital, URL: https://www.simprogroup.com/case-studies/bge-digital, supported theme: quote workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: quote workflow, evidence summary: reviewers discuss quote workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "quoting software" --proof-role metric
- Selected proof: case-study-bge-digital | Customer: BGE Digital | URL: https://www.simprogroup.com/case-studies/bge-digital | Use: quote workflow proof
"""
        ledger = {
            "version": 1,
            "overuse_baselines": [
                {
                    "proof_id": "case-study-bge-digital",
                    "customer": "BGE Digital",
                    "source_url": "https://www.simprogroup.com/case-studies/bge-digital",
                    "recent_uses_90d": 3,
                    "total_uses": 3,
                    "source_note": "repo scan before active article repair",
                    "last_reviewed": "2026-06-15",
                }
            ],
            "uses": [],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                article,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(any(f["rule_id"] == "customer_proof_reuse_requires_source_specific_reason" for f in findings))

    def test_review_site_theme_evidence_passes_without_exact_quote(self):
        sidecar = proof_slate(
            metric_selected="case-study-bge-digital",
            theme_selected="case-study-bge-digital",
            metric_top="case-study-bge-digital",
            theme_top="case-study-bge-digital",
        ) + proof_mining() + """Customer Proof Pack
- Pack status: ready.
- Case-study proof path: BGE Digital, URL: https://www.simprogroup.com/case-studies/bge-digital, supported theme: quote workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: quoting workflow, evidence summary: reviewers discuss quote and job workflow visibility, exact quote/rating approval status: not approved.
- Reuse reason: BGE Digital remains the best source-visible quote workflow proof in this fixture.
- Use in copy: paraphrased review-site theme and case-study proof only.
- Claims excluded: exact review quotes and ratings.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "quote workflow" --proof-role theme
- Selected proof: case-study-bge-digital | Customer: BGE Digital | URL: https://www.simprogroup.com/case-studies/bge-digital | Use: quote workflow theme proof
"""

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(
                "# Quoting\n\nReview themes can inform a paraphrased workflow discussion.",
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertEqual(findings, [])

    def test_exact_quote_requires_approved_quote_row(self):
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: scheduling workflow, evidence summary: reviewers discuss scheduling workflows, exact quote/rating approval status: not approved.
- Use in copy: paraphrased review-site theme only.
- Claims excluded: exact review quotes.
"""
        article = '# Review proof\n\nA G2 reviewer said, "Scheduling is much easier for our field team now."'

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(article, proof_content=sidecar, ledger_path=ledger_path)

        self.assertTrue(any(f["rule_id"] == "customer_quote_requires_approved_quote" for f in findings))

    def test_exact_quote_passes_with_approved_quote_row(self):
        sidecar = proof_slate(
            metric_selected="none",
            quote_selected="quote-matrix-example-customer",
            theme_selected="none",
            quote_top="quote-matrix-example-customer",
        ) + proof_mining(
            usable_quotes='"Scheduling is much easier for our field team now." approved for exact quote use',
            recommended_use="exact quote",
            final_use="exact quote",
        ) + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for scheduling proof and selected an approved exact quote.
- Approved quote: "Scheduling is much easier for our field team now." | Customer/brand: Example Customer | Source type: Quote Matrix | URL: https://example.com/customer-proof | Evidence: "Scheduling is much easier for our field team now." | Status: approved | Use: exact quote
- Use in copy: exact quote.
- Claims excluded: none.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "scheduling proof" --proof-role quote
- Selected proof: quote-matrix-example-customer | Customer: Example Customer | URL: https://example.com/customer-proof | Use: exact quote proof
"""
        article = '# Review proof\n\nExample Customer said, "Scheduling is much easier for our field team now."'

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
            findings = check_content(article, proof_content=sidecar, ledger_path=ledger_path)

        self.assertEqual(findings, [])

    def test_check_file_accepts_sidecar_and_ledger_paths(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article = root / "drafts" / "job-quoting.md"
            sidecar = root / "research" / "validation-job-quoting.md"
            ledger = root / "context" / "customer-proof-usage-ledger.json"
            article.parent.mkdir(parents=True)
            sidecar.parent.mkdir(parents=True)
            ledger.parent.mkdir(parents=True)
            article.write_text(ARTICLE_WITH_CASE_STUDY, encoding="utf-8")
            sidecar.write_text(
                proof_slate() + proof_mining() + """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof; no exact quote selected.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Reuse reason: TEAMWired remains the best public source-visible invoicing metric.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
""",
                encoding="utf-8",
            )
            ledger.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")

            findings = check_file(
                article,
                proof_sidecar=str(sidecar),
                ledger_path=ledger,
            )

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
