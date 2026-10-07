"""Artifacts bound before a wording edit stay valid only for its lineage hashes."""

from __future__ import annotations

import hashlib
import unittest

from data_sources.modules import context_binding_guard
from tests import test_context_binding_guard as binding_fixture


PARAGRAPH = "Dispatchers review the board each morning before crews leave."


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ContextBindingCarryForwardTests(unittest.TestCase):
    setUp = binding_fixture.ContextBindingGuardTests.setUp
    write_current_sidecar = binding_fixture.ContextBindingGuardTests.write_current_sidecar

    def _anchor_then_edit(self) -> tuple[str, str]:
        claim_map = context_binding_guard._json_block(
            self.sidecar.read_text(encoding="utf-8"), "Context Claim Use Map"
        )
        self.article.write_text(
            self.article.read_text(encoding="utf-8") + f"\n{PARAGRAPH}\n", encoding="utf-8"
        )
        self.write_current_sidecar(claim_map)
        anchor = _sha256(self.article)
        self.article.write_text(
            self.article.read_text(encoding="utf-8").replace("review the board", "check the board"),
            encoding="utf-8",
        )
        return anchor, _sha256(self.article)

    def _rules(self, accepted=()) -> set[str]:
        findings = context_binding_guard.check_file(
            self.article,
            proof_sidecar=self.sidecar,
            context_request=self.request,
            context_pack=self.pack,
            context_receipt=self.receipt,
            client=binding_fixture.ValidatingClient(),
            accepted_article_sha256s=accepted,
        )
        return {finding["rule_id"] for finding in findings}

    def test_binding_for_the_anchor_article_is_accepted_for_its_lineage(self):
        anchor, edited = self._anchor_then_edit()

        self.assertEqual(self._rules(frozenset({anchor, edited})), set())

    def test_binding_for_an_unrelated_article_hash_is_still_rejected(self):
        _, edited = self._anchor_then_edit()

        self.assertIn("context_article_hash_mismatch", self._rules(frozenset({edited})))
        self.assertIn("context_article_hash_mismatch", self._rules())


def test_release_scrub_check_accepts_a_scrub_receipt_for_the_edit_anchor(tmp_path):
    import json

    from data_sources.modules.blog_creation_preflight import _check_scrub_receipt_article_binding

    article = tmp_path / "article.md"
    article.write_text("Dispatchers check the board.\n", encoding="utf-8")
    anchor = hashlib.sha256(b"Dispatchers review the board.\n").hexdigest()
    final = _sha256(article)

    def receipt(name, stage, article_in, article_out):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps({
            "stage": stage,
            "input_artifact_hashes": {"article": article_in},
            "output_artifact_hashes": {"article": article_out},
        }), encoding="utf-8")
        return path

    scrub = receipt("scrub", "scrub", anchor, anchor)
    chain = [scrub, receipt("binding", "context_binding", anchor, anchor), receipt("edit", "wording_edit", anchor, final)]

    assert _check_scrub_receipt_article_binding(scrub, article, chain) == []
    assert [row["rule_id"] for row in _check_scrub_receipt_article_binding(scrub, article, chain[:2])] == [
        "scrub_receipt_article_hash_mismatch"
    ]


def test_optimizer_output_accepts_a_lineage_article_but_no_other_stale_input(tmp_path):
    import json

    import pytest

    from data_sources.modules import optimizer_evidence

    files = {}
    for label in ("article", "editorial_plan", "proof_sidecar", "prior_preflight_readiness", "scorecard"):
        files[label] = tmp_path / f"{label}.txt"
        files[label].write_text(f"{label} v1\n", encoding="utf-8")
    bindings = {label: {"path": path.name, "sha256": _sha256(path)} for label, path in files.items()}
    output = tmp_path / "optimizer-output.json"
    output.write_text(json.dumps({
        "schema": "simpro-optimizer-output/v2",
        "status": "completed",
        "input_bindings": bindings,
    }), encoding="utf-8")
    anchor = _sha256(files["article"])
    files["article"].write_text("article v2\n", encoding="utf-8")

    def validate(accepted=()):
        optimizer_evidence.validate_optimizer_outputs(
            [output],
            article=files["article"],
            editorial_plan=files["editorial_plan"],
            proof_sidecar=files["proof_sidecar"],
            prior_preflight_readiness=files["prior_preflight_readiness"],
            workspace_root=tmp_path,
            accepted_article_sha256s=accepted,
        )

    validate({anchor, _sha256(files["article"])})
    with pytest.raises(optimizer_evidence.OptimizerEvidenceError):
        validate()
    files["editorial_plan"].write_text("editorial_plan v2\n", encoding="utf-8")
    with pytest.raises(optimizer_evidence.OptimizerEvidenceError):
        validate({anchor, _sha256(files["article"])})


def test_plan_fulfillment_accepts_only_lineage_article_hashes():
    from data_sources.modules.editorial_plan.plan_fulfillment import _hash_findings

    anchor = "Dispatchers review the board each morning."
    edited = "Dispatchers check the board each morning."
    value = {
        "editorial_plan_sha256": "1" * 64,
        "article_sha256": hashlib.sha256(anchor.encode("utf-8")).hexdigest(),
    }

    def rules(accepted=()):
        return {
            finding["rule_id"]
            for finding in _hash_findings(
                value,
                editorial_plan_sha256="1" * 64,
                article_content=edited,
                accepted_article_sha256s=accepted,
            )
        }

    assert rules({value["article_sha256"]}) == set()
    assert rules() == {"plan_fulfillment_article_hash_mismatch"}
