"""Tests for the production BOM schema and its structural validators."""

from __future__ import annotations

import copy

from data_sources.modules.production import bom as bom_module
from tests.production_bom_support import connector_spec


def _bom() -> dict:
    return {
        "schema": bom_module.BOM_SCHEMA,
        "identity": {"slug": "s", "date": "2026-10-13", "run_id": "r", "brand": "Simpro",
                     "market": "US", "workflow_mode": "new", "article_path": "drafts/s-2026-10-13.md",
                     "title": "T", "objective": "O", "audience": "A",
                     "cta": {"text": "x", "url": "https://x.example"}, "schema_notes": ["BlogPosting"],
                     "spec": {"path": "research/production-bom-spec-s-2026-10-13.json", "sha256": "a" * 64}},
        "keyword": {}, "serp": {},
        "sections": [{"heading": "h", "purpose": "p", "priority": "must"}],
        "facts": [{"id": "f1", "claim": "c", "url": "https://x.example", "quote": "q",
                   "priority": "must", "verified_at": "2026-10-13T00:00:00Z", "check_detail": "ok",
                   "support": "quote_overlap"}],
        "proof": [{"id": "p1", "claim_id": "c1", "kind": "metric", "priority": "should", "text": "t"}],
        "paa": {"artifact": None, "questions": [{"question": "Q?", "priority": "should"}]},
        "links": [{"url": "https://x.example", "anchor": "a", "kind": "internal", "priority": "should"}],
        "context": {"status": "not_applicable", "reason": "r"},
    }


def test_schema_constants():
    assert bom_module.BOM_SCHEMA == "simpro-production-bom/v1"
    assert bom_module.SPEC_SCHEMA == "simpro-production-bom-spec/v1"


def test_valid_bom_has_no_errors():
    assert bom_module.validate_bom(_bom()) == []


def test_wrong_schema_and_missing_keys_are_reported():
    bom = _bom()
    bom["schema"] = "other"
    del bom["facts"]
    errors = bom_module.validate_bom(bom)
    assert any("schema" in e for e in errors)
    assert any("facts" in e for e in errors)


def test_non_object_bom_is_rejected():
    assert bom_module.validate_bom([]) != []


def test_priority_outside_must_should_is_rejected_everywhere():
    for path in ("sections", "facts", "proof", "links"):
        bom = _bom()
        bom[path][0]["priority"] = "could"
        assert any("priority" in e for e in bom_module.validate_bom(bom)), path
    bom = _bom()
    bom["paa"]["questions"][0]["priority"] = "nice"
    assert any("priority" in e for e in bom_module.validate_bom(bom))


def test_duplicate_fact_and_proof_ids_are_rejected():
    bom = _bom()
    bom["facts"].append(copy.deepcopy(bom["facts"][0]))
    bom["proof"].append(copy.deepcopy(bom["proof"][0]))
    errors = bom_module.validate_bom(bom)
    assert any("duplicate fact id" in e for e in errors)
    assert any("duplicate proof id" in e for e in errors)


def test_facts_need_verified_at_url_and_quote():
    for field in ("verified_at", "url", "quote"):
        bom = _bom()
        bom["facts"][0][field] = ""
        assert any(field in e for e in bom_module.validate_bom(bom)), field


def test_unknown_link_kind_is_rejected():
    bom = _bom()
    bom["links"][0]["kind"] = "affiliate"
    assert any("kind" in e for e in bom_module.validate_bom(bom))


def test_valid_spec_has_no_errors():
    assert bom_module.validate_spec(connector_spec()) == []


def test_spec_unknown_and_missing_keys_listed_together():
    spec = connector_spec()
    spec["extra"] = 1
    del spec["title"]
    errors = bom_module.validate_spec(spec)
    assert any("extra" in e for e in errors)
    assert any("title" in e for e in errors)


def test_spec_wrong_schema_and_bad_priority_and_proof_text():
    spec = connector_spec()
    spec["schema"] = "nope"
    spec["facts"][0]["priority"] = "could"
    spec["proof"][0]["text"] = "typed proof"
    errors = bom_module.validate_spec(spec)
    assert any("schema" in e for e in errors)
    assert any("priority" in e for e in errors)
    assert any("text" in e for e in errors)


def test_spec_duplicate_ids_and_bad_link_kind():
    spec = connector_spec()
    spec["facts"].append(copy.deepcopy(spec["facts"][0]))
    spec["links"][1]["kind"] = "affiliate"
    errors = bom_module.validate_spec(spec)
    assert any("duplicate fact id" in e for e in errors)
    assert any("kind" in e for e in errors)


def test_spec_non_object_is_rejected():
    assert bom_module.validate_spec("x") != []


def test_identity_spec_binding_is_required_and_checked():
    bom = _bom()
    del bom["identity"]["spec"]
    assert any("identity spec" in e for e in bom_module.validate_bom(bom))
    for bad in ({"path": "x"}, {"path": "x", "sha256": "A" * 64}, {"path": "x", "sha256": "a" * 63},
                {"path": "", "sha256": "a" * 64}, "nope"):
        bom = _bom()
        bom["identity"]["spec"] = bad
        assert any("identity spec" in e for e in bom_module.validate_bom(bom)), bad


def test_fact_support_must_be_quote_overlap():
    bom = _bom()
    bom["facts"][0]["support"] = "typed"
    assert any("support" in e for e in bom_module.validate_bom(bom))
    del bom["facts"][0]["support"]
    assert any("support" in e for e in bom_module.validate_bom(bom))
