"""Subprocess coverage for the standalone content scorer CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.nonvault_customer_proof_selector import _main
from tests.nonvault_proof_fixture import write_nonvault_proof_inputs
from tests.test_content_scorer_aeo_geo_gate import (
    COMPLIANT_ARTICLE,
    CUSTOMER_PROOF_BLOCK,
    FAQ_PROOF_BLOCK,
    METRIC_ARTIFACT,
    METRIC_PROOF_BLOCK,
    PAA_ARTIFACT,
)
from tests.research_provenance_fixtures import build_answersocrates_fixture


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PAA_QUERY = "hvac scheduling software"
PAA_COLLECTION_DATE = "2026-05-22"
PAA_RUN_ID = "content-scorer-fixture"


class ContentScorerCliTests(unittest.TestCase):
    def test_bound_paa_fixture_passes_guard_and_reaches_scorer_aeo_gate(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article_content = COMPLIANT_ARTICLE.replace(CUSTOMER_PROOF_BLOCK, "")
            article_content = article_content.replace(
                "\n[BWE Engineering](https://www.simprogroup.com/case-studies/bwe-engineering) shows how field service teams use connected workflows to improve operational control.\n",
                "\nNo customer story is included because the available stories do not support this HVAC scheduling objective.\n",
            )
            article_content = article_content.replace(
                "Last Updated: 2026-05-22",
                f"Last Updated: {date.today().isoformat()}",
            )
            article_content = article_content.replace(
                "## Frequently Asked Questions",
                (
                    "Keep the board simple. Put urgent work at the top. Show who owns each job. "
                    "Add travel notes before the tech leaves. Use clear status names. Don't ask the "
                    "office to guess what happened on site. When the job is done, send the notes to "
                    "billing the same day. Teams that need a broader operating platform can compare "
                    "[field service management software](https://www.simprogroup.com/) options before "
                    "they choose a scheduling workflow.\n\n## Frequently Asked Questions"
                ),
                1,
            )
            article_path = root / "drafts" / "hvac-scheduling-software.md"
            article_path.parent.mkdir(parents=True)
            article_path.write_text(article_content, encoding="utf-8")
            artifact_path = root / PAA_ARTIFACT
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text(
                json.dumps(
                    build_answersocrates_fixture(
                        root,
                        query=PAA_QUERY,
                        collection_date=PAA_COLLECTION_DATE,
                        questions=(
                            "What is the best way to schedule HVAC technicians?",
                            "How does HVAC scheduling software reduce missed appointments?",
                            "Should HVAC scheduling connect to invoicing?",
                        ),
                        run_id=PAA_RUN_ID,
                    ),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            metric_path = root / METRIC_ARTIFACT
            metric_path.parent.mkdir(parents=True, exist_ok=True)
            metric_path.write_text(
                "Simpro supports more than 24,000 trade businesses worldwide.",
                encoding="utf-8",
            )
            index_path, ledger_path = write_nonvault_proof_inputs(root / "proof")
            selector_evidence_path = root / "research" / "customer-proof-selector-evidence.json"
            selector_stdout = StringIO()
            selector_stderr = StringIO()
            rejection_reason = (
                "this ClockShark timekeeping story does not support the HVAC "
                "scheduling objective"
            )
            with redirect_stdout(selector_stdout), redirect_stderr(selector_stderr):
                selector_exit_code = _main(
                    [
                        "hvac scheduling software",
                        "--brand",
                        "ClockShark",
                        "--title",
                        "HVAC Scheduling Software for Contractors",
                        "--objective",
                        "Explain practical HVAC scheduling workflows.",
                        "--article-slug",
                        "hvac-scheduling-software",
                        "--index",
                        str(index_path),
                        "--ledger",
                        str(ledger_path),
                        "--roles",
                        "metric,quote,theme,experience_story",
                        "--require-eeat-story",
                        "--selected",
                        "experience_story=none",
                        "--rejected",
                        (
                            "experience_story=clockshark-customer-story-mabrys-electrical-service:"
                            + rejection_reason
                        ),
                        "--rejected",
                        (
                            "experience_story=clockshark-customer-story-bear-down-builders:"
                            + rejection_reason
                        ),
                        "--limit",
                        "10",
                        "--reference-date",
                        date.today().isoformat(),
                        "--slate",
                        "--evidence-output",
                        str(selector_evidence_path),
                    ]
                )
            self.assertEqual(selector_exit_code, 0, selector_stderr.getvalue())
            proof_sidecar = (
                "## "
                + selector_stdout.getvalue()
                + "\n## E-E-A-T Proof Map\n"
                + "- First-hand evidence decision: Selected: [none] because the available "
                + "ClockShark customer stories support timekeeping workflows rather than this "
                + "HVAC scheduling objective.\n"
                + FAQ_PROOF_BLOCK
                + METRIC_PROOF_BLOCK
            )
            sidecar_path = root / "validation-hvac-scheduling.md"
            sidecar_path.write_text(proof_sidecar, encoding="utf-8")
            environment = os.environ | {"PYTHONPATH": str(REPOSITORY_ROOT)}
            paa_arguments = [
                "--workflow-mode",
                "new",
                "--expected-query",
                PAA_QUERY,
                "--expected-collection-date",
                PAA_COLLECTION_DATE,
                "--expected-run-id",
                PAA_RUN_ID,
                "--paa-artifact",
                str(artifact_path),
            ]

            guard = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "data_sources.modules.paa_provenance_guard",
                    str(article_path),
                    "--proof-sidecar",
                    str(sidecar_path),
                    *paa_arguments,
                ],
                cwd=REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            scorer = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "data_sources.modules.content_scorer",
                    str(article_path),
                    "--proof-sidecar",
                    str(sidecar_path),
                    "--paa-workflow-mode",
                    "new",
                    "--paa-expected-query",
                    PAA_QUERY,
                    "--paa-expected-collection-date",
                    PAA_COLLECTION_DATE,
                    "--paa-expected-run-id",
                    PAA_RUN_ID,
                    "--paa-artifact",
                    str(artifact_path),
                    "--assembly-date",
                    date.today().isoformat(),
                ],
                cwd=REPOSITORY_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(guard.returncode, 0, guard.stdout + guard.stderr)
        self.assertEqual(scorer.returncode, 0, scorer.stdout + scorer.stderr)
        self.assertIn("AEO/GEO Score: 100/100", scorer.stdout)


if __name__ == "__main__":
    unittest.main()
