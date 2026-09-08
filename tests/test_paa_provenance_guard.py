from tests.fixture_text import fixture_text

import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from data_sources.modules import paa_provenance_guard
from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.paa_provenance_guard import (
    build_answersocrates_artifact,
    check_content,
    check_file as production_check_file,
    should_fail,
)
from tests.research_provenance_fixtures import build_answersocrates_fixture


FAQ_QUESTIONS = (
    'What is the best way to schedule HVAC technicians?',
    'Should HVAC scheduling connect to invoicing?',
)
PAA_QUERY = 'hvac technician scheduling'
COLLECTION_DATE = '2026-08-11'


def check_file(path, *args, **kwargs):
    """Supply the real fixture artifact run ID to legacy behavioral cases."""
    if "expected_run_id" not in kwargs:
        content = Path(path).read_text(encoding="utf-8")
        proof = kwargs.get("proof_sidecar")
        if proof:
            content += "\n" + Path(proof).read_text(encoding="utf-8")
        artifact_value = kwargs.get("paa_artifact")
        if not artifact_value:
            match = re.search(r"(?im)^-\s*Artifact:\s*`?([^`\s]+)", content)
            artifact_value = match.group(1) if match else None
        if artifact_value:
            artifact_path = Path(artifact_value)
            if not artifact_path.is_absolute():
                article = Path(path).resolve()
                root = article.parent.parent if article.parent.name == "drafts" else article.parent
                artifact_path = root / artifact_path
            try:
                payload = json.loads(artifact_path.read_text(encoding="utf-8"))
                run_id = payload.get("run_receipt", {}).get("run_id")
            except (OSError, json.JSONDecodeError):
                run_id = None
            if isinstance(run_id, str) and run_id:
                kwargs["expected_run_id"] = run_id
    return production_check_file(path, *args, **kwargs)


def strict_provenance_block(source_kind: str, artifact: str) -> str:
    return f'''```text
PAA/FAQ Provenance
- Source: {source_kind}
- Artifact: {artifact}
- Selected questions:
  - {FAQ_QUESTIONS[0]}
  - {FAQ_QUESTIONS[1]}
```'''


def structured_answersocrates(
    eligible_questions=FAQ_QUESTIONS,
    ineligible_fragments=(),
    *,
    status: str = 'collected',
    blocker: str = '',
    query: str = PAA_QUERY,
    collection_date: str = COLLECTION_DATE,
) -> str:
    recorded_blocker = (
        blocker
        if blocker in paa_provenance_guard.ANSWERSOCRATES_BLOCKER_STATES
        else ("quota" if status == "blocked" else "")
    )
    raw_capture = {"path": "research/test-raw-capture.json", "sha256": "a" * 64}
    payload = {
        "schema": paa_provenance_guard.ANSWERSOCRATES_ARTIFACT_SCHEMA,
        "source_kind": "answersocrates",
        "status": status,
        "query": query,
        "collection_date": collection_date,
        "eligible_question_section": "people_also_ask",
        "eligible_questions": list(eligible_questions),
        "ineligible_fragments": list(ineligible_fragments),
        "blocker": (
            {
                "kind": recorded_blocker,
                "reason": f"AnswerSocrates collection was blocked by {recorded_blocker}.",
            }
            if recorded_blocker else None
        ),
        "raw_capture": raw_capture,
    }
    receipt = attest_mapping({
        "schema": paa_provenance_guard.ANSWERSOCRATES_RECEIPT_SCHEMA,
        "run_id": "answersocrates-test-run",
        "tool": dict(paa_provenance_guard.ANSWERSOCRATES_TOOL),
        "started_at": f"{collection_date}T14:00:00Z",
        "completed_at": f"{collection_date}T14:01:00Z",
        "status": status,
        "payload_sha256": paa_provenance_guard.canonical_json_sha256(payload),
        "raw_capture": raw_capture,
    }, purpose=paa_provenance_guard.ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE)
    receipt["receipt_hash"] = paa_provenance_guard.canonical_json_sha256(receipt)
    artifact = {**payload, "run_receipt": receipt}
    if status == "blocked" and blocker != recorded_blocker:
        artifact["blocker"]["kind"] = blocker
    return json.dumps(artifact, indent=2, sort_keys=True) + "\n"


def write_bound_answersocrates(
    root: Path,
    path: Path,
    questions=FAQ_QUESTIONS,
    *,
    run_id: str,
) -> None:
    path.write_text(json.dumps(build_answersocrates_fixture(
        root,
        query=PAA_QUERY,
        collection_date=COLLECTION_DATE,
        questions=questions,
        run_id=run_id,
    )), encoding="utf-8")


def dedicated_brief_paa(questions=FAQ_QUESTIONS) -> str:
    rows = '\n'.join(f'- {question}' for question in questions)
    return f'''# Content Brief

## Pre-picked PAA Questions

{rows}
'''


class StrictPaaSourceTests(unittest.TestCase):
    def test_record_runs_fixed_collector_and_persists_exact_stdout_before_parsing(self):
        collection_date = datetime.now(timezone.utc).date().isoformat()
        exact_stdout = json.dumps({
            "page_url": "https://answersocrates.com/paa-extractor",
            "page_title": "People Also Ask Extractor",
            "body_text": "People Also Ask",
            "blocker_observations": [],
            "sections": [
                {"heading": "People Also Ask", "items": list(FAQ_QUESTIONS)},
                {"heading": "Search suggestions", "items": ["hvac scheduling"]},
            ],
        })

        def completed(command, **kwargs):
            stdout = exact_stdout if "run-code" in command else ""
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            paa_provenance_guard, "find_npx_executable", return_value="npx"
        ), patch.object(paa_provenance_guard.subprocess, "run", side_effect=completed):
            root = Path(temp_dir)
            raw_path = root / "research" / "answersocrates-raw.json"
            output_path = root / "research" / "paa.json"
            exit_code = paa_provenance_guard._main([
                "record",
                "--query", PAA_QUERY,
                "--collection-date", collection_date,
                "--run-id", "agency-run-123",
                "--raw-capture-output", str(raw_path),
                "--workspace-root", str(root),
                "--output", str(output_path),
            ])
            capture = json.loads(raw_path.read_text(encoding="utf-8"))
            artifact = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(capture["raw_response"]["stdout"], exact_stdout)
        self.assertEqual(capture["raw_response"]["stderr"], "")
        self.assertEqual(capture["raw_response"]["returncode"], 0)
        self.assertEqual(artifact["eligible_questions"], list(FAQ_QUESTIONS))
        self.assertEqual(artifact["ineligible_fragments"], ["hvac scheduling"])

    def test_record_derives_blocker_only_from_exact_persisted_collector_stdout(self):
        collection_date = datetime.now(timezone.utc).date().isoformat()
        exact_stdout = json.dumps({
            "page_url": "https://answersocrates.com/paa-extractor",
            "page_title": "People Also Ask Extractor",
            "body_text": "You have already used your free search quota.",
            "blocker_observations": [{
                "scope": "quota_container",
                "text": "You have already used your free search quota.",
            }],
            "sections": [],
        })

        def completed(command, **kwargs):
            stdout = exact_stdout if "run-code" in command else ""
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            paa_provenance_guard, "find_npx_executable", return_value="npx"
        ), patch.object(paa_provenance_guard.subprocess, "run", side_effect=completed):
            root = Path(temp_dir)
            raw_path = root / "research" / "answersocrates-raw.json"
            output_path = root / "research" / "paa.json"
            exit_code = paa_provenance_guard._main([
                "record",
                "--query", PAA_QUERY,
                "--collection-date", collection_date,
                "--run-id", "agency-run-blocked",
                "--raw-capture-output", str(raw_path),
                "--workspace-root", str(root),
                "--output", str(output_path),
            ])
            capture = json.loads(raw_path.read_text(encoding="utf-8"))
            artifact = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(capture["raw_response"]["stdout"], exact_stdout)
        self.assertEqual(artifact["status"], "blocked")
        self.assertEqual(artifact["blocker"]["kind"], "quota")
        self.assertEqual(artifact["eligible_questions"], [])

    def test_record_ignores_sign_in_navigation_when_valid_paa_is_observed(self):
        collection_date = datetime.now(timezone.utc).date().isoformat()
        exact_stdout = json.dumps({
            "page_url": "https://answersocrates.com/paa-extractor",
            "page_title": "People Also Ask Extractor",
            "body_text": "Sign in Navigation People Also Ask",
            "blocker_observations": [],
            "sections": [
                {"heading": "People Also Ask", "items": list(FAQ_QUESTIONS)},
            ],
        })

        def completed(command, **kwargs):
            stdout = exact_stdout if "run-code" in command else ""
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            paa_provenance_guard, "find_npx_executable", return_value="npx"
        ), patch.object(paa_provenance_guard.subprocess, "run", side_effect=completed):
            root = Path(temp_dir)
            raw_path = root / "research" / "answersocrates-raw.json"
            output_path = root / "research" / "paa.json"
            exit_code = paa_provenance_guard._main([
                "record",
                "--query", PAA_QUERY,
                "--collection-date", collection_date,
                "--run-id", "agency-run-navigation",
                "--raw-capture-output", str(raw_path),
                "--workspace-root", str(root),
                "--output", str(output_path),
            ])
            capture = json.loads(raw_path.read_text(encoding="utf-8"))
            artifact = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(capture["raw_response"]["stdout"], exact_stdout)
        self.assertEqual(artifact["status"], "collected")
        self.assertIsNone(artifact["blocker"])
        self.assertEqual(artifact["eligible_questions"], list(FAQ_QUESTIONS))

    def test_only_scoped_blocker_observations_establish_closed_blocker_kinds(self):
        cases = (
            ("login", "authentication_gate", "Authentication required. Log in to continue."),
            ("captcha", "captcha_container", "Complete the CAPTCHA. You are not a robot."),
            ("quota", "quota_container", "You have used your free search quota."),
            ("unavailability", "error_container", "Service unavailable."),
        )
        for expected_kind, scope, blocker_text in cases:
            with self.subTest(expected_kind=expected_kind):
                _, _, blocker = paa_provenance_guard._derive_answersocrates_observations({
                    "stdout": json.dumps({
                        "page_url": "https://answersocrates.com/paa-extractor",
                        "page_title": "People Also Ask Extractor",
                        "body_text": "Sign in Navigation",
                        "sections": [],
                        "blocker_observations": [{"scope": scope, "text": blocker_text}],
                    }),
                    "stderr": "",
                    "returncode": 0,
                })

                self.assertEqual(blocker["kind"], expected_kind)
                self.assertEqual(blocker["reason"], blocker_text)

    def test_scoped_blocker_observations_fail_closed_when_malformed_or_ambiguous(self):
        cases = (
            [{"scope": "navigation", "text": "Sign in"}],
            [{"scope": "role_alert", "text": ""}],
            [{"scope": "role_alert", "text": "Something happened."}],
            [
                {"scope": "captcha_container", "text": "Complete the CAPTCHA."},
                {"scope": "quota_container", "text": "Free search quota reached."},
            ],
        )
        for observations in cases:
            with self.subTest(observations=observations), self.assertRaises(ValueError):
                paa_provenance_guard._derive_answersocrates_observations({
                    "stdout": json.dumps({
                        "page_url": "https://answersocrates.com/paa-extractor",
                        "page_title": "People Also Ask Extractor",
                        "body_text": "Sign in Navigation",
                        "sections": [],
                        "blocker_observations": observations,
                    }),
                    "stderr": "",
                    "returncode": 0,
                })

    def test_record_rejects_caller_supplied_capture_and_requires_canonical_inputs(self):
        for argv in (
            ["record", "--raw-capture", "writer.json", "--output", "paa.json"],
            ["record", "--query", PAA_QUERY, "--output", "paa.json"],
        ):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                paa_provenance_guard._main(argv)

    def test_answersocrates_builder_requires_query_date_and_run_expectations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture = self._write_raw_capture(root)
            with self.assertRaisesRegex(TypeError, "expected_query"):
                build_answersocrates_artifact(
                    raw_capture_path=capture,
                    workspace_root=root,
                )

    def _write_raw_capture(
        self,
        root: Path,
        *,
        query: str = PAA_QUERY,
        run_id: str = "browser-run-123",
        started_at: str = f"{COLLECTION_DATE}T14:00:00Z",
        completed_at: str = f"{COLLECTION_DATE}T14:01:00Z",
        collector_name: str = "answersocrates_playwright_collector",
        raw_response: object | None = None,
    ) -> Path:
        if isinstance(raw_response, dict) and set(raw_response) == {"visible_sections", "blocker_output"}:
            blocker_output = str(raw_response.get("blocker_output") or "")
            raw_response = {
                "stdout": json.dumps({
                    "page_url": "https://answersocrates.com/paa-extractor",
                    "page_title": "People Also Ask Extractor",
                    "body_text": blocker_output or "People Also Ask",
                    "blocker_observations": ([{
                        "scope": "role_alert",
                        "text": blocker_output,
                    }] if blocker_output else []),
                    "sections": raw_response.get("visible_sections", []),
                }),
                "stderr": "",
                "returncode": 0,
            }
        payload = {
            "schema": "simpro-answersocrates-playwright-capture/v1",
            "collector": {"name": collector_name, "version": "1.0.0"},
            "query": query,
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "page_url": "https://answersocrates.com/paa-extractor",
            "raw_response": raw_response if raw_response is not None else {
                "stdout": json.dumps({
                    "page_url": "https://answersocrates.com/paa-extractor",
                    "page_title": "People Also Ask Extractor",
                    "body_text": "People Also Ask",
                    "blocker_observations": [],
                    "sections": [
                        {
                            "heading": "People Also Ask",
                            "items": [FAQ_QUESTIONS[0], FAQ_QUESTIONS[1]],
                        },
                        {"heading": "Search suggestions", "items": ["hvac scheduling"]},
                    ],
                }),
                "stderr": "",
                "returncode": 0,
            },
        }
        capture = attest_mapping(
            payload,
            purpose="simpro-answersocrates-playwright-capture/v1",
            workspace_root=root,
        )
        path = root / "research" / "answersocrates-playwright-raw.json"
        atomic_write_json(path, capture)
        return path

    def test_receipt_accepts_the_actual_playwright_cli_runtime(self):
        artifact = build_answersocrates_artifact(
            query=PAA_QUERY,
            collection_date=COLLECTION_DATE,
            eligible_questions=FAQ_QUESTIONS,
            run_id="answersocrates-playwright-cli-run",
            started_at=f"{COLLECTION_DATE}T14:00:00Z",
            completed_at=f"{COLLECTION_DATE}T14:01:00Z",
            tool={"name": "playwright_cli", "version": "0.1.19"},
        )

        record = paa_provenance_guard._parse_question_artifact(
            json.dumps(artifact)
        )

        self.assertIsNotNone(record)
        self.assertTrue(record.run_receipt_valid)
        self.assertEqual(
            artifact["run_receipt"]["tool"],
            {"name": "playwright_cli", "version": "0.1.19"},
        )

    def test_receipt_builder_rejects_an_unapproved_browser_runtime(self):
        with self.assertRaisesRegex(ValueError, "playwright_mcp or playwright_cli"):
            build_answersocrates_artifact(
                query=PAA_QUERY,
                collection_date=COLLECTION_DATE,
                eligible_questions=FAQ_QUESTIONS,
                run_id="answersocrates-unapproved-browser-run",
                started_at=f"{COLLECTION_DATE}T14:00:00Z",
                completed_at=f"{COLLECTION_DATE}T14:01:00Z",
                tool={"name": "unknown_browser", "version": "1.0.0"},
            )

    def _write_family(
        self,
        root: Path,
        *,
        source_kind: str,
        artifact_name: str,
        artifact_content: str,
    ):
        artifact = root / 'research' / artifact_name
        artifact.parent.mkdir(parents=True, exist_ok=True)
        try:
            requested = json.loads(artifact_content)
        except json.JSONDecodeError:
            requested = None
        if (
            source_kind == "answersocrates"
            and isinstance(requested, dict)
            and requested.get("schema") == paa_provenance_guard.ANSWERSOCRATES_ARTIFACT_SCHEMA
            and isinstance(requested.get("query"), str)
            and paa_provenance_guard.verify_mapping_attestation(
                requested.get("run_receipt", {}),
                purpose=paa_provenance_guard.ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE,
                excluded_fields=("receipt_hash",),
            )
        ):
            raw_response = {
                "visible_sections": [{
                    "heading": "People Also Ask",
                    "items": [
                        *requested.get("eligible_questions", []),
                        *requested.get("ineligible_fragments", []),
                    ],
                }],
                "blocker_output": (
                    requested.get("blocker", {}).get("reason", "")
                    if isinstance(requested.get("blocker"), dict) else ""
                ),
            }
            if requested.get("ineligible_fragments"):
                raw_response["visible_sections"][0]["items"] = requested.get("eligible_questions", [])
                raw_response["visible_sections"].append({
                    "heading": "Search suggestions",
                    "items": requested.get("ineligible_fragments", []),
                })
            capture = self._write_raw_capture(
                root,
                query=requested.get("query", PAA_QUERY),
                run_id="answersocrates-test-run",
                started_at=f"{requested.get('collection_date', COLLECTION_DATE)}T14:00:00Z",
                completed_at=f"{requested.get('collection_date', COLLECTION_DATE)}T14:01:00Z",
                raw_response=raw_response,
            )
            artifact_content = json.dumps(build_answersocrates_artifact(
                raw_capture_path=capture,
                workspace_root=root,
                expected_query=requested.get("query", PAA_QUERY),
                expected_collection_date=requested.get("collection_date", COLLECTION_DATE),
                expected_run_id="answersocrates-test-run",
            ))
        artifact.write_text(artifact_content, encoding='utf-8')
        article = root / 'drafts' / 'hvac-scheduling.md'
        article.parent.mkdir(parents=True, exist_ok=True)
        article.write_text(
            article_with_faq(
                strict_provenance_block(
                    source_kind,
                    f'research/{artifact_name}',
                )
            ),
            encoding='utf-8',
        )
        return article, artifact

    def _write_structured_artifact(
        self,
        root: Path,
        path: Path,
        *,
        questions=FAQ_QUESTIONS,
        status: str = "collected",
        blocker: str = "",
    ) -> None:
        blocker_output = (
            f"AnswerSocrates collection was blocked by {blocker}."
            if status == "blocked" else ""
        )
        capture = self._write_raw_capture(
            root,
            raw_response={
                "visible_sections": [{
                    "heading": "People Also Ask", "items": list(questions),
                }],
                "blocker_output": blocker_output,
            },
        )
        artifact = build_answersocrates_artifact(
            raw_capture_path=capture,
            workspace_root=root,
            expected_query=PAA_QUERY,
            expected_collection_date=COLLECTION_DATE,
            expected_run_id="browser-run-123",
        )
        path.write_text(json.dumps(artifact), encoding="utf-8")

    def _policy_findings(self, article: Path, **kwargs):
        return check_file(str(article), **kwargs)

    def test_source_kind_must_be_an_exact_enum_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='AnswerSocrates via Playwright MCP',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )

            findings = check_file(str(article))

        self.assertIn(
            'paa_source_unsupported',
            [finding['rule_id'] for finding in findings],
        )

    def test_serp_reddit_and_youtube_cannot_qualify(self):
        for source_kind in ('serp', 'reddit', 'youtube'):
            with self.subTest(source_kind=source_kind), tempfile.TemporaryDirectory() as temp_dir:
                article, _ = self._write_family(
                    Path(temp_dir),
                    source_kind=source_kind,
                    artifact_name='supplemental.md',
                    artifact_content=structured_answersocrates(),
                )

                findings = check_file(str(article))

            self.assertIn(
                'paa_supplemental_source_cannot_qualify',
                [finding['rule_id'] for finding in findings],
            )

    def test_answersocrates_artifact_must_be_structured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content='\n'.join(FAQ_QUESTIONS),
            )

            findings = check_file(str(article))

        self.assertIn(
            'paa_answersocrates_artifact_unstructured',
            [finding['rule_id'] for finding in findings],
        )

    def test_handwritten_answersocrates_labels_cannot_fabricate_collection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=(
                    '# AnswerSocrates PAA Collection\n\n'
                    'Source kind: answersocrates\nStatus: collected\n'
                    f'Query: {PAA_QUERY}\nDate: {COLLECTION_DATE}\n\n'
                    '## Eligible Questions\n\n'
                    + '\n'.join(f'- {question}' for question in FAQ_QUESTIONS)
                ),
            )

            findings = check_file(
                str(article),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_answersocrates_artifact_unstructured',
            [finding['rule_id'] for finding in findings],
        )

    def test_plain_rehash_cannot_forge_answersocrates_run_receipt(self):
        artifact_value = json.loads(
            structured_answersocrates(eligible_questions=(FAQ_QUESTIONS[0],))
        )
        artifact_value['eligible_questions'].append(FAQ_QUESTIONS[1])
        payload = {
            key: value
            for key, value in artifact_value.items()
            if key != 'run_receipt'
        }
        receipt = artifact_value['run_receipt']
        receipt['payload_sha256'] = paa_provenance_guard.canonical_json_sha256(
            payload
        )
        receipt.pop('receipt_hash')
        receipt['receipt_hash'] = paa_provenance_guard.canonical_json_sha256(
            receipt
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.json',
                artifact_content=json.dumps(artifact_value),
            )
            findings = check_file(
                str(article),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_answersocrates_artifact_unstructured',
            [finding['rule_id'] for finding in findings],
        )

    def test_ineligible_fragment_cannot_match_visible_faq(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(
                    eligible_questions=(FAQ_QUESTIONS[0],),
                    ineligible_fragments=(FAQ_QUESTIONS[1],),
                ),
            )

            findings = check_file(
                str(article),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_question_ineligible_fragment',
            [finding['rule_id'] for finding in findings],
        )

    def test_answersocrates_requires_expected_query_and_collection_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )

            findings = check_file(str(article), workflow_mode='new')

        self.assertIn(
            'paa_answersocrates_expectation_missing',
            [finding['rule_id'] for finding in findings],
        )

    def test_answersocrates_query_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )

            findings = check_file(
                str(article),
                workflow_mode='new',
                expected_query='hvac dispatch automation',
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_answersocrates_query_mismatch',
            [finding['rule_id'] for finding in findings],
        )

    def test_answersocrates_stale_collection_date_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(
                    collection_date='2026-08-10',
                ),
            )

            findings = check_file(
                str(article),
                workflow_mode='new',
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_answersocrates_date_mismatch',
            [finding['rule_id'] for finding in findings],
        )

    def test_answersocrates_metadata_requires_query_and_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_value = json.loads(structured_answersocrates())
            del artifact_value['query']
            artifact_content = json.dumps(artifact_value)
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=artifact_content,
            )

            findings = check_file(
                str(article),
                workflow_mode='new',
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_answersocrates_artifact_unstructured',
            [finding['rule_id'] for finding in findings],
        )

    def test_rewrite_dedicated_brief_paa_takes_precedence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article, _ = self._write_family(
                root,
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )
            brief = root / 'research' / 'brief-paa.md'
            brief.write_text(dedicated_brief_paa(), encoding='utf-8')

            findings = self._policy_findings(
                article,
                workflow_mode='rewrite',
                content_brief=str(brief),
            )

        self.assertIn(
            'paa_rewrite_brief_precedence_violation',
            [finding['rule_id'] for finding in findings],
        )

    def test_rewrite_rejects_duplicate_visible_dedicated_paa_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article, _ = self._write_family(
                root,
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )
            brief = root / 'research' / 'duplicate-brief-paa.md'
            brief.write_text(
                '# Content Brief\n\n'
                '## Pre-picked PAA Questions\n\n'
                f'- {FAQ_QUESTIONS[0]}\n\n'
                '## Reader Contract\n\nHelp dispatch leaders.\n\n'
                '## Pre-picked PAA Questions\n\n'
                f'- {FAQ_QUESTIONS[1]}\n',
                encoding='utf-8',
            )

            findings = self._policy_findings(
                article,
                workflow_mode='rewrite',
                content_brief=str(brief),
            )

        self.assertIn(
            'paa_brief_sections_duplicate',
            [finding['rule_id'] for finding in findings],
        )

    def test_rewrite_ignores_dedicated_paa_headings_inside_fenced_examples(self):
        for fence in ('```', '~~~'):
            with self.subTest(fence=fence), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                article, _ = self._write_family(
                    root,
                    source_kind='answersocrates',
                    artifact_name='paa.md',
                    artifact_content=structured_answersocrates(),
                )
                brief = root / 'research' / 'example-only-brief.md'
                brief.write_text(
                    '# Content Brief\n\n'
                    f'{fence}markdown\n'
                    '## Pre-picked PAA Questions\n\n'
                    f'- {FAQ_QUESTIONS[0]}\n'
                    f'{fence}\n\n'
                    '## Reader Contract\n\nHelp dispatch leaders.\n',
                    encoding='utf-8',
                )

                result = paa_provenance_guard.evaluate_file(
                    str(article),
                    workflow_mode='rewrite',
                    content_brief=str(brief),
                    expected_query=PAA_QUERY,
                    expected_collection_date=COLLECTION_DATE,
                    expected_run_id='answersocrates-test-run',
                )

            self.assertTrue(result.passed, result.findings)

    def test_rewrite_brief_questions_must_match_visible_faq(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article, brief = self._write_family(
                root,
                source_kind='brief_paa',
                artifact_name='brief-paa.md',
                artifact_content=dedicated_brief_paa((FAQ_QUESTIONS[0],)),
            )

            findings = self._policy_findings(
                article,
                workflow_mode='rewrite',
                content_brief=str(brief),
            )

        self.assertIn(
            'paa_question_missing_from_artifact',
            [finding['rule_id'] for finding in findings],
        )

    def test_unicode_questions_do_not_collapse_to_the_same_match_key(self):
        source_question = '如何调度技术人员?'
        different_question = '如何管理客户发票?'
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / 'research' / 'paa.json'
            artifact.parent.mkdir(parents=True)
            write_bound_answersocrates(
                root, artifact, (source_question,), run_id="unicode-run",
            )
            article = root / 'drafts' / 'unicode-faq.md'
            article.parent.mkdir(parents=True)
            article.write_text(
                '# Unicode FAQ\n\n'
                '```text\n'
                'PAA/FAQ Provenance\n'
                '- Source: answersocrates\n'
                '- Artifact: research/paa.json\n'
                '- Selected questions:\n'
                f'  - {different_question}\n'
                '```\n\n'
                '## Frequently Asked Questions\n\n'
                f'### {different_question}\n\n'
                'Use the verified operating workflow.\n',
                encoding='utf-8',
            )

            findings = check_file(
                str(article),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_question_missing_from_artifact',
            [finding['rule_id'] for finding in findings],
        )

    def test_answersocrates_rejects_empty_normalized_question_keys(self):
        with self.assertRaisesRegex(ValueError, 'normalization'):
            paa_provenance_guard._derive_answersocrates_observations(
                {"stdout": json.dumps({
                    "page_url": "https://answersocrates.com/paa-extractor",
                    "page_title": "PAA", "body_text": "People Also Ask",
                    "blocker_observations": [],
                    "sections": [{"heading": "People Also Ask", "items": ["???"]}],
                }), "stderr": "", "returncode": 0}
            )

    def test_answersocrates_rejects_colliding_normalized_question_keys(self):
        with self.assertRaisesRegex(ValueError, 'normalization'):
            paa_provenance_guard._derive_answersocrates_observations(
                {"stdout": json.dumps({
                    "page_url": "https://answersocrates.com/paa-extractor",
                    "page_title": "PAA", "body_text": "People Also Ask",
                    "blocker_observations": [],
                    "sections": [{"heading": "People Also Ask", "items": ["What's HVAC?", "What’s HVAC?"]}],
                }), "stderr": "", "returncode": 0}
            )

    def test_rewrite_content_brief_passes_and_binds_hash_and_questions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article, brief = self._write_family(
                root,
                source_kind='brief_paa',
                artifact_name='content-brief.md',
                artifact_content=dedicated_brief_paa(),
            )

            result = paa_provenance_guard.evaluate_file(
                str(article),
                workflow_mode='rewrite',
                content_brief=str(brief),
            )
            expected_hash = hashlib.sha256(brief.read_bytes()).hexdigest()

        self.assertTrue(result.passed)
        self.assertEqual(result.artifact_questions, FAQ_QUESTIONS)
        self.assertEqual(result.content_brief_sha256, expected_hash)

    def test_every_pre_picked_brief_question_must_be_a_visible_faq(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            extra_question = 'How often should an HVAC schedule be reviewed?'
            article, brief = self._write_family(
                root,
                source_kind='brief_paa',
                artifact_name='content-brief.md',
                artifact_content=dedicated_brief_paa(
                    FAQ_QUESTIONS + (extra_question,),
                ),
            )

            findings = check_file(
                str(article),
                workflow_mode='rewrite',
                content_brief=str(brief),
            )

        self.assertIn(
            'paa_brief_question_missing_from_faq',
            [finding['rule_id'] for finding in findings],
        )

    def test_rewrite_without_brief_requires_answersocrates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='brief_paa',
                artifact_name='brief-paa.md',
                artifact_content=dedicated_brief_paa(),
            )

            findings = self._policy_findings(article, workflow_mode='rewrite')

        self.assertIn(
            'paa_rewrite_answersocrates_required',
            [finding['rule_id'] for finding in findings],
        )

    def test_new_workflow_rejects_brief_paa_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='brief_paa',
                artifact_name='brief-paa.md',
                artifact_content=dedicated_brief_paa(),
            )

            findings = self._policy_findings(article, workflow_mode='new')

        self.assertIn(
            'paa_new_answersocrates_required',
            [finding['rule_id'] for finding in findings],
        )

    def test_rewrite_without_brief_accepts_answersocrates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )
            evaluator = getattr(paa_provenance_guard, 'evaluate_file', None)

            self.assertTrue(callable(evaluator))
            result = evaluator(
                str(article),
                workflow_mode='rewrite',
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='answersocrates-test-run',
            )

        self.assertTrue(result.passed)
        self.assertEqual(result.source_kind, 'answersocrates')

    def test_rewrite_ordinary_brief_without_pre_picked_paa_accepts_answersocrates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article, _ = self._write_family(
                root,
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )
            brief = root / 'research' / 'ordinary-brief.md'
            brief.write_text(
                '# Content Brief\n\n## Reader Contract\n\nHelp dispatch leaders.\n',
                encoding='utf-8',
            )

            result = paa_provenance_guard.evaluate_file(
                str(article),
                workflow_mode='rewrite',
                content_brief=str(brief),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='answersocrates-test-run',
            )

        self.assertTrue(result.passed)
        self.assertEqual(result.source_kind, 'answersocrates')

    def test_user_csv_requires_blocked_answersocrates_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_text = 'question\n' + '\n'.join(
                f'"{question}"' for question in FAQ_QUESTIONS
            )
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='user_csv',
                artifact_name='user-paa.csv',
                artifact_content=csv_text,
            )

            findings = self._policy_findings(article, workflow_mode='new')

        self.assertIn(
            'paa_user_csv_blocker_missing',
            [finding['rule_id'] for finding in findings],
        )

    def test_user_csv_rejects_non_csv_primary_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article, _ = self._write_family(
                root,
                source_kind='user_csv',
                artifact_name='user-paa.md',
                artifact_content='\n'.join(FAQ_QUESTIONS),
            )
            blocker = root / 'research' / 'answersocrates-blocker.md'
            self._write_structured_artifact(
                root,
                blocker,
                questions=(),
                status="blocked",
                blocker="quota",
            )

            findings = self._policy_findings(
                article,
                workflow_mode='new',
                answersocrates_blocker=str(blocker),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_user_csv_invalid',
            [finding['rule_id'] for finding in findings],
        )

    def test_user_csv_requires_blocker_status_and_reason(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_text = 'question\n' + '\n'.join(
                f'"{question}"' for question in FAQ_QUESTIONS
            )
            article, _ = self._write_family(
                root,
                source_kind='user_csv',
                artifact_name='user-paa.csv',
                artifact_content=csv_text,
            )
            blocker = root / 'research' / 'answersocrates-blocker.md'
            blocker.write_text(
                structured_answersocrates(),
                encoding='utf-8',
            )

            findings = self._policy_findings(
                article,
                workflow_mode='new',
                answersocrates_blocker=str(blocker),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_answersocrates_blocker_invalid',
            [finding['rule_id'] for finding in findings],
        )

    def test_user_csv_rejects_caller_choice_as_a_blocked_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_text = 'question\n' + '\n'.join(
                f'"{question}"' for question in FAQ_QUESTIONS
            )
            article, _ = self._write_family(
                root,
                source_kind='user_csv',
                artifact_name='user-paa.csv',
                artifact_content=csv_text,
            )
            blocker = root / 'research' / 'answersocrates-blocker.md'
            blocker.write_text(
                structured_answersocrates(
                    eligible_questions=(),
                    status='blocked',
                    blocker='I chose not to run it',
                ),
                encoding='utf-8',
            )

            findings = self._policy_findings(
                article,
                workflow_mode='new',
                answersocrates_blocker=str(blocker),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            'paa_answersocrates_blocker_invalid',
            [finding['rule_id'] for finding in findings],
        )

    def test_evaluate_file_returns_structured_reusable_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, artifact = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )
            evaluator = getattr(paa_provenance_guard, 'evaluate_file', None)

            self.assertTrue(callable(evaluator))
            result = evaluator(
                str(article),
                workflow_mode='new',
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='answersocrates-test-run',
            )
            expected_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()

        self.assertTrue(result.passed)
        self.assertEqual(result.workflow_mode, 'new')
        self.assertEqual(result.source_kind, 'answersocrates')
        self.assertEqual(result.artifact_sha256, expected_hash)
        self.assertEqual(result.artifact_questions, FAQ_QUESTIONS)
        self.assertEqual(result.artifact_query, PAA_QUERY)
        self.assertEqual(result.artifact_collection_date, COLLECTION_DATE)
        self.assertEqual(result.faq_questions, FAQ_QUESTIONS)
        self.assertEqual(result.selected_questions, FAQ_QUESTIONS)
        self.assertEqual(result.to_dict()['findings'], [])

    def test_user_csv_passes_with_structured_blocker_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_text = 'question\n' + '\n'.join(
                f'"{question}"' for question in FAQ_QUESTIONS
            )
            article, _ = self._write_family(
                root,
                source_kind='user_csv',
                artifact_name='user-paa.csv',
                artifact_content=csv_text,
            )
            blocker = root / 'research' / 'answersocrates-blocker.md'
            self._write_structured_artifact(
                root, blocker, questions=(), status="blocked", blocker="quota",
            )
            evaluator = getattr(paa_provenance_guard, 'evaluate_file', None)

            self.assertTrue(callable(evaluator))
            result = evaluator(
                str(article),
                workflow_mode='new',
                answersocrates_blocker=str(blocker),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='browser-run-123',
            )
            expected_blocker_hash = hashlib.sha256(
                blocker.read_bytes()
            ).hexdigest()

        self.assertTrue(result.passed)
        self.assertEqual(result.source_kind, 'user_csv')
        self.assertEqual(
            result.answersocrates_blocker,
            str(blocker),
        )
        self.assertEqual(
            result.answersocrates_blocker_sha256,
            expected_blocker_hash,
        )

    def test_h4_faq_questions_receive_the_same_provenance_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )
            article.write_text(
                article.read_text(encoding='utf-8').replace('### ', '#### '),
                encoding='utf-8',
            )

            result = paa_provenance_guard.evaluate_file(
                str(article),
                workflow_mode='new',
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='answersocrates-test-run',
            )

        self.assertTrue(result.passed)
        self.assertEqual(result.faq_questions, FAQ_QUESTIONS)

    def test_cli_accepts_workflow_and_brief_artifact_arguments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article, brief = self._write_family(
                root,
                source_kind='brief_paa',
                artifact_name='brief-paa.md',
                artifact_content=dedicated_brief_paa(),
            )
            output = io.StringIO()
            with redirect_stdout(output):
                try:
                    exit_code = paa_provenance_guard._main(
                        [
                            str(article),
                            '--workflow-mode',
                            'rewrite',
                            '--content-brief',
                            str(brief),
                        ]
                    )
                except SystemExit as error:
                    exit_code = error.code

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload['result']['workflow_mode'], 'rewrite')
        self.assertEqual(payload['result']['source_kind'], 'brief_paa')

    def test_cli_accepts_answersocrates_expectations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article, _ = self._write_family(
                Path(temp_dir),
                source_kind='answersocrates',
                artifact_name='paa.md',
                artifact_content=structured_answersocrates(),
            )
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = paa_provenance_guard._main(
                    [
                        str(article),
                        '--workflow-mode',
                        'new',
                        '--expected-query',
                        PAA_QUERY,
                '--expected-collection-date',
                COLLECTION_DATE,
                '--expected-run-id',
                'answersocrates-test-run',
                    ]
                )

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload['result']['passed'])
        self.assertEqual(payload['result']['artifact_query'], PAA_QUERY)
        self.assertEqual(
            payload['result']['artifact_collection_date'],
            COLLECTION_DATE,
        )


def article_with_faq(provenance_block: str = "") -> str:
    return f"""# HVAC Scheduling Software

{provenance_block}

## Frequently Asked Questions

### What is the best way to schedule HVAC technicians?

The best way to schedule HVAC technicians is to use [field service scheduling](https://www.simprogroup.com/features/scheduling-software) that shows availability, job priority, location, and skill fit. This helps office teams assign work without overloading technicians or missing urgent calls.

### Should HVAC scheduling connect to invoicing?

HVAC scheduling should connect to invoicing because completed work loses value when job details stay trapped in the field. When technician notes and approvals flow into [field service invoicing](https://www.simprogroup.com/features/invoicing-software-for-construction), office teams can invoice faster.
"""


class PaaProvenanceGuardTests(unittest.TestCase):
    def test_common_questions_heading_is_subject_to_paa_provenance(self):
        content = article_with_faq().replace(
            "## Frequently Asked Questions",
            "## Common questions",
        )

        findings = check_content(content, workflow_mode="new")

        self.assertEqual(findings[0]["rule_id"], "paa_provenance_missing")

    def test_details_question_markup_is_blocked_instead_of_skipped(self):
        content = (
            "# Guide\n\n"
            "<details><summary>What does field service software do?</summary>\n\n"
            "It coordinates field work.\n\n"
            "</details>\n"
        )

        findings = check_content(content, workflow_mode="new")

        self.assertEqual(findings[0]["rule_id"], "paa_faq_structure_unsupported")

    def test_bold_question_markup_is_blocked_instead_of_skipped(self):
        content = "# Guide\n\n**What does field service software do?**\n\nIt coordinates field work.\n"

        findings = check_content(content, workflow_mode="new")

        self.assertEqual(findings[0]["rule_id"], "paa_faq_structure_unsupported")

    def test_new_blog_without_visible_faq_still_validates_bound_answersocrates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article = root / "drafts" / "guide.md"
            artifact = root / "research" / "paa.md"
            article.parent.mkdir(parents=True)
            artifact.parent.mkdir(parents=True)
            article.write_text("# Guide\n\nA direct answer.\n", encoding="utf-8")
            write_bound_answersocrates(root, artifact, run_id="no-faq-run")

            findings = check_file(
                str(article),
                workflow_mode="new",
                paa_artifact=str(artifact),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='no-faq-run',
            )

        self.assertEqual(findings, [])

    def test_new_blog_without_visible_faq_rejects_non_answersocrates_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article = root / "drafts" / "guide.md"
            artifact = root / "research" / "serp.md"
            article.parent.mkdir(parents=True)
            artifact.parent.mkdir(parents=True)
            article.write_text("# Guide\n\nA direct answer.\n", encoding="utf-8")
            artifact.write_text(
                "Source kind: serp\nStatus: collected\n",
                encoding="utf-8",
            )

            findings = check_file(
                str(article),
                workflow_mode="new",
                paa_artifact=str(artifact),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='answersocrates-test-run',
            )

        self.assertIn(
            "paa_answersocrates_artifact_unstructured",
            {finding["rule_id"] for finding in findings},
        )
    def test_new_workflow_without_faq_or_answersocrates_artifact_fails(self):
        content = fixture_text("sealed_workflows:test_paa_provenance_guard-1026-1")

        self.assertIn(
            "paa_new_answersocrates_required",
            {finding["rule_id"] for finding in check_content(content)},
        )

    def test_rewrite_without_faq_or_bound_paa_source_requires_answersocrates(self):
        content = "# HVAC Scheduling Software\n\nA direct answer.\n"

        findings = check_content(content, workflow_mode="rewrite")

        self.assertIn(
            "paa_rewrite_answersocrates_required",
            {finding["rule_id"] for finding in findings},
        )

    def test_rewrite_ordinary_brief_without_faq_still_requires_answersocrates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            brief = Path(temp_dir) / "brief.md"
            brief.write_text(
                "# Content Brief\n\n## Reader Contract\n\nHelp dispatch leaders.\n",
                encoding="utf-8",
            )

            findings = check_content(
                "# HVAC Scheduling Software\n\nA direct answer.\n",
                workflow_mode="rewrite",
                content_brief=str(brief),
            )

        self.assertIn(
            "paa_rewrite_answersocrates_required",
            {finding["rule_id"] for finding in findings},
        )

    def test_rewrite_dedicated_brief_is_recognized_but_questions_remain_mandatory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            brief = Path(temp_dir) / "brief.md"
            brief.write_text(dedicated_brief_paa(), encoding="utf-8")

            findings = check_content(
                "# HVAC Scheduling Software\n\nA direct answer.\n",
                workflow_mode="rewrite",
                content_brief=str(brief),
                paa_artifact=str(brief),
            )

        rules = {finding["rule_id"] for finding in findings}
        self.assertNotIn("paa_rewrite_answersocrates_required", rules)
        self.assertIn("paa_brief_question_missing_from_faq", rules)

    def test_paa_artifact_directory_returns_stable_finding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = Path(temp_dir) / "paa.md"
            artifact.mkdir()

            findings = check_content(
                "# HVAC Scheduling Software\n\nA direct answer.\n",
                workflow_mode="new",
                paa_artifact=str(artifact),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            "paa_artifact_missing",
            {finding["rule_id"] for finding in findings},
        )

    def test_invalid_utf8_paa_artifact_returns_stable_finding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = Path(temp_dir) / "paa.md"
            artifact.write_bytes(b"\xff\xfe\xfa")

            findings = check_content(
                "# HVAC Scheduling Software\n\nA direct answer.\n",
                workflow_mode="new",
                paa_artifact=str(artifact),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
            )

        self.assertIn(
            "paa_artifact_unreadable",
            {finding["rule_id"] for finding in findings},
        )

    def test_disappearing_paa_artifact_returns_stable_finding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = Path(temp_dir) / "paa.md"
            artifact.write_text(structured_answersocrates(), encoding="utf-8")

            with patch.object(
                Path,
                "read_text",
                side_effect=FileNotFoundError("artifact disappeared"),
            ):
                findings = check_content(
                    "# HVAC Scheduling Software\n\nA direct answer.\n",
                    workflow_mode="new",
                    paa_artifact=str(artifact),
                    expected_query=PAA_QUERY,
                    expected_collection_date=COLLECTION_DATE,
                    expected_run_id='answersocrates-test-run',
                )

        self.assertIn(
            "paa_artifact_unreadable",
            {finding["rule_id"] for finding in findings},
        )

    def test_paa_artifact_disappearing_during_final_hash_check_is_stable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article = root / "article.md"
            artifact = root / "paa.md"
            article.write_text("# HVAC Scheduling Software\n\nA direct answer.\n", encoding="utf-8")
            artifact.write_text(structured_answersocrates(), encoding="utf-8")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

            with patch.object(
                paa_provenance_guard,
                "_file_sha256",
                side_effect=(digest, FileNotFoundError("artifact disappeared")),
            ):
                findings = check_file(
                    str(article),
                    workflow_mode="new",
                    paa_artifact=str(artifact),
                    expected_query=PAA_QUERY,
                    expected_collection_date=COLLECTION_DATE,
                )

        self.assertIn(
            "paa_artifact_unreadable",
            {finding["rule_id"] for finding in findings},
        )

    def test_faq_with_proof_links_but_no_provenance_fails(self):
        findings = check_content(article_with_faq())

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "paa_provenance_missing")
        self.assertEqual(findings[0]["severity"], "error")

    def test_matching_answersocrates_artifact_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "paa-questions-hvac-scheduling-2026-06-12.md"
            artifact.parent.mkdir()
            write_bound_answersocrates(root, artifact, run_id="matching-run")
            article = root / "drafts" / "hvac-scheduling.md"
            article.parent.mkdir()
            article.write_text(
                article_with_faq(
                    fixture_text("sealed_workflows:test_paa_provenance_guard-1189-4")
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                check_file(
                    str(article),
                    expected_query=PAA_QUERY,
                    expected_collection_date=COLLECTION_DATE,
                ),
                [],
            )

    def test_matching_provenance_sidecar_passes_clean_draft(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "paa-questions-hvac-scheduling-2026-06-12.md"
            sidecar = root / "research" / "validation-hvac-scheduling-2026-06-12.md"
            artifact.parent.mkdir()
            write_bound_answersocrates(root, artifact, run_id="sidecar-run")
            sidecar.write_text(
                fixture_text("sealed_workflows:test_paa_provenance_guard-1221-2"),
                encoding="utf-8",
            )
            article = root / "drafts" / "hvac-scheduling-2026-06-12.md"
            article.parent.mkdir()
            article.write_text(article_with_faq(), encoding="utf-8")

            self.assertEqual(
                check_file(
                    str(article),
                    proof_sidecar=str(sidecar),
                    expected_query=PAA_QUERY,
                    expected_collection_date=COLLECTION_DATE,
                ),
                [],
            )

    def test_faq_question_missing_from_artifact_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "paa-questions-hvac-scheduling-2026-06-12.md"
            artifact.parent.mkdir()
            write_bound_answersocrates(
                root, artifact, (FAQ_QUESTIONS[0],), run_id="missing-question-run",
            )
            article = root / "drafts" / "hvac-scheduling.md"
            article.parent.mkdir()
            article.write_text(
                article_with_faq(
                    fixture_text("sealed_workflows:test_paa_provenance_guard-1258-5")
                ),
                encoding="utf-8",
            )

            findings = check_file(
                str(article),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='missing-question-run',
            )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "paa_question_missing_from_artifact")
        self.assertEqual(
            findings[0]["question"],
            "Should HVAC scheduling connect to invoicing?",
        )

    def test_missing_artifact_path_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article = Path(temp_dir) / "drafts" / "hvac-scheduling.md"
            article.parent.mkdir()
            article.write_text(
                article_with_faq(
                    fixture_text("sealed_workflows:test_paa_provenance_guard-1289-6")
                ),
                encoding="utf-8",
            )

            findings = check_file(str(article))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "paa_artifact_missing")

    def test_unsupported_source_label_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "paa-questions-hvac-scheduling-2026-06-12.md"
            artifact.parent.mkdir()
            artifact.write_text(
                fixture_text("sealed_workflows:test_paa_provenance_guard-1312-3"),
                encoding="utf-8",
            )
            article = root / "drafts" / "hvac-scheduling.md"
            article.parent.mkdir()
            article.write_text(
                article_with_faq(
                    fixture_text("sealed_workflows:test_paa_provenance_guard-1323-7")
                ),
                encoding="utf-8",
            )

            findings = check_file(str(article))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "paa_source_unsupported")

    def test_check_file_and_failure_threshold(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write(article_with_faq())
            temp_path = temp_file.name

        try:
            findings = check_file(temp_path, fail_on="error")
        finally:
            os.unlink(temp_path)

        self.assertTrue(should_fail(findings, fail_on="error"))
        self.assertFalse(should_fail(findings, fail_on="none"))


class ExplicitPaaBindingTests(unittest.TestCase):
    def test_explicit_bom_artifact_uses_visible_faq_as_selected_questions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "paa.md"
            article = root / "drafts" / "hvac.md"
            artifact.parent.mkdir()
            article.parent.mkdir()
            write_bound_answersocrates(root, artifact, run_id="explicit-run")
            article.write_text(article_with_faq(), encoding="utf-8")

            findings = check_file(
                str(article),
                workflow_mode="new",
                paa_artifact=str(artifact),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='explicit-run',
            )

        self.assertEqual(findings, [])

    def test_explicit_bom_artifact_must_match_sidecar_provenance_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            declared = root / "research" / "declared.md"
            bound = root / "research" / "bound.md"
            declared.parent.mkdir()
            write_bound_answersocrates(root, declared, run_id="declared-run")
            write_bound_answersocrates(root, bound, run_id="bound-run")
            article = root / "drafts" / "hvac.md"
            article.parent.mkdir()
            article.write_text(
                article_with_faq(
                    strict_provenance_block("answersocrates", "research/declared.md")
                ),
                encoding="utf-8",
            )

            findings = check_file(
                str(article),
                workflow_mode="new",
                paa_artifact=str(bound),
                expected_query=PAA_QUERY,
                expected_collection_date=COLLECTION_DATE,
                expected_run_id='browser-run-123',
            )

        self.assertIn(
            "paa_artifact_binding_mismatch",
            [finding["rule_id"] for finding in findings],
        )


if __name__ == "__main__":
    unittest.main()
