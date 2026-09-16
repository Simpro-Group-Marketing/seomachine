"""Subprocess coverage for the standalone content scorer CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_content_scorer_aeo_geo_gate import (
    COMPLIANT_ARTICLE,
    CUSTOMER_PROOF_BLOCK,
    FAQ_PROOF_BLOCK,
    METRIC_ARTIFACT,
    METRIC_PROOF_BLOCK,
    PAA_ARTIFACT,
)
from tests.aeo_geo_rater_support import write_bound_experience_story_evidence
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
                "\n[Megan B's Capterra review](https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) describes using service jobs, quotes, invoices, and QBO integration in one connected workflow.\n",
            )
            article_content = article_content.replace(
                "Last Updated: 2026-05-22",
                f"Last Updated: {date.today().isoformat()}",
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
            proof_sidecar, sidecar_path = write_bound_experience_story_evidence(
                self,
                root,
            )
            proof_sidecar += (
                FAQ_PROOF_BLOCK
                + METRIC_PROOF_BLOCK
            )
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
        self.assertEqual(scorer.returncode, 1, scorer.stdout + scorer.stderr)
        self.assertIn("AEO/GEO Score: 90/100", scorer.stdout)


if __name__ == "__main__":
    unittest.main()
