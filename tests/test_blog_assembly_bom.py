from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from data_sources.modules.blog_assembly_bom import (
    build_blog_assembly_bom,
    build_blog_assembly_bom_from_files,
    write_blog_assembly_bom,
)
from data_sources.modules.blog_assembly_bom_guard import check_bom, check_bom_file


def _minimal_context():
    request = {
        "task": "Assemble a Simpro blog.",
        "scope": {
            "artifact_type": "blog",
            "brand": "Simpro",
            "title": "AI field service guide",
            "objective": "Explain AI field service software boundaries.",
            "audience": "field service leaders",
            "region": "US",
            "intended_public_use_modes": ["public_paraphrase"],
        },
    }
    revisions = {
        "approval_policy_revision": "policy-1",
        "claim_registry_revision": "claims-1",
        "content_revision": "content-1",
        "contract_revision": "contract-1",
        "inventory_revision": "inventory-1",
        "manifest_revision": "manifest-1",
    }
    pack = {
        "schema": "simpro-product-context-pack/v2",
        "revisions": revisions,
        "sections": {
            "Discovery Trace": {
                "selected_resource_ids": ["res-voice"],
                "selected_resource_purposes": {"res-voice": "guidance"},
            },
            "Approved Claim Evidence": [
                {
                    "claim_id": "claim-approved-1",
                    "support_resource_ids": ["res-voice"],
                }
            ],
        },
    }
    receipt = {
        "schema": "simpro-context-receipt/v1",
        "pack_sha256": "pack-hash",
        "receipt_sha256": "receipt-hash",
        "revisions": revisions,
        "claim_decisions": [
            {
                "claim_id": "claim-approved-1",
                "approved": True,
            }
        ],
    }
    return request, pack, receipt


def _bom(*, author: str | None = None, stages: list[str] | None = None):
    request, pack, receipt = _minimal_context()
    return build_blog_assembly_bom(
        topic_slug="ai-field-service-guide",
        article_path="drafts/ai-field-service-guide-2026-08-10.md",
        validation_sidecar_path=(
            "research/validation-ai-field-service-guide-2026-08-10.md"
        ),
        context_request_path="research/context-request-ai-field-service-guide.json",
        context_pack_path="research/context-pack-ai-field-service-guide.json",
        context_receipt_path="research/context-receipt-ai-field-service-guide.json",
        request=request,
        pack=pack,
        receipt=receipt,
        author=author,
        schema_notes=[
            "BlogPosting",
            "BreadcrumbList",
            "FAQPage",
            "ImageObject",
            "Organization publisher reference",
            *(["Person as author"] if author else []),
        ],
        stages=stages or ["draft", "scrub", "context_binding", "publish_readiness"],
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_real_artifacts(
    tmp_path: Path,
    *,
    author: str | None = None,
    schema_notes: list[str] | None = None,
    body: str = "Body copy.",
):
    request, pack, receipt = _minimal_context()
    frontmatter = [
        "---",
        "artifact_type: blog",
        "brand: Simpro",
        'title: "AI field service guide"',
        'objective: "Explain AI field service software boundaries."',
        'audience: "field service leaders"',
        "region: US",
        "last_updated: 2026-08-10",
    ]
    if author:
        frontmatter.append(f'author: "{author}"')
    notes = schema_notes or [
        "BlogPosting",
        "BreadcrumbList",
        "ImageObject",
        "Organization publisher reference",
    ]
    frontmatter.append("schema_notes:")
    for note in notes:
        frontmatter.append(f"  - {note}")
    frontmatter.append("---")
    article = tmp_path / "drafts" / "ai-field-service-guide-2026-08-10.md"
    article.parent.mkdir(parents=True, exist_ok=True)
    article.write_text(
        "\n".join(frontmatter) + "\n\n# AI field service guide\n\n" + body + "\n",
        encoding="utf-8",
    )
    sidecar = tmp_path / "research" / "validation-ai-field-service-guide-2026-08-10.md"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(
        (
            "Author policy: named_author\n"
            if author
            else "Author policy: not_provided\nNo named author available.\n"
        ),
        encoding="utf-8",
    )
    context_request = _write_json(tmp_path / "research" / "context-request-ai-field-service-guide.json", request)
    context_pack = _write_json(tmp_path / "research" / "context-pack-ai-field-service-guide.json", pack)
    context_receipt = _write_json(tmp_path / "research" / "context-receipt-ai-field-service-guide.json", receipt)
    selector = _write_json(tmp_path / "research" / "customer-proof-selector-evidence-ai-field-service-guide.json", {"selector": "ok"})
    fred = tmp_path / "research" / "fred-authority-selection-ai-field-service-guide.md"
    fred.write_text("Fred Voccola Authority Selection\nSelected: none\n", encoding="utf-8")
    optimizer = tmp_path / "research" / "optimizer-ai-field-service-guide.json"
    _write_json(optimizer, {"optimizer": "seo"})
    readiness = _write_json(tmp_path / "research" / "publish-readiness-ai-field-service-guide.json", {"passed": True})
    return {
        "article": article,
        "sidecar": sidecar,
        "context_request": context_request,
        "context_pack": context_pack,
        "context_receipt": context_receipt,
        "selector": selector,
        "fred": fred,
        "optimizer": optimizer,
        "readiness": readiness,
    }


def _build_real_bom(tmp_path: Path, **kwargs):
    paths = _write_real_artifacts(tmp_path, **kwargs)
    bom = build_blog_assembly_bom_from_files(
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        context_request_path=paths["context_request"],
        context_pack_path=paths["context_pack"],
        context_receipt_path=paths["context_receipt"],
        customer_proof_selector_evidence_path=paths["selector"],
        fred_authority_evidence_path=paths["fred"],
        optimizer_output_paths=[paths["optimizer"]],
        readiness_output_path=paths["readiness"],
        stage_names=[
            "draft",
            "scrub",
            "context_binding",
            "publish_readiness",
            "optimization",
            "post_optimization_scrub",
            "post_optimization_context_binding",
            "final_publish_readiness",
        ],
    )
    bom_path = tmp_path / "research" / "blog-assembly-bom-ai-field-service-guide-2026-08-10.json"
    write_blog_assembly_bom(bom_path, bom)
    return bom_path, bom, paths


def test_bom_cli_builder_hashes_actual_artifacts_and_connector_binding(tmp_path: Path):
    bom_path, bom, paths = _build_real_bom(tmp_path)

    assert bom_path.exists()
    assert bom["connector_binding"]["status"] == "required"
    assert bom["file_hashes"]["article"] == _sha256(paths["article"])
    assert bom["file_hashes"]["validation_sidecar"] == _sha256(paths["sidecar"])
    assert bom["file_hashes"]["customer_proof_selector_evidence"] == _sha256(paths["selector"])
    assert bom["file_hashes"]["fred_authority_evidence"] == _sha256(paths["fred"])
    assert bom["optimizer_outputs"] == [
        {
            "path": paths["optimizer"].as_posix(),
            "sha256": _sha256(paths["optimizer"]),
        }
    ]
    assert bom["context"]["selected_resource_ids"] == ["res-voice"]
    assert bom["context"]["claim_ids"] == ["claim-approved-1"]


def test_bom_file_guard_rejects_tampered_article_hash(tmp_path: Path):
    bom_path, _, paths = _build_real_bom(tmp_path)
    paths["article"].write_text(paths["article"].read_text(encoding="utf-8") + "\nTampered.\n", encoding="utf-8")

    findings = check_bom_file(
        bom_path,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        context_request_path=paths["context_request"],
        context_pack_path=paths["context_pack"],
        context_receipt_path=paths["context_receipt"],
    )

    assert any(finding["rule_id"] == "bom_article_hash_mismatch" for finding in findings)


def test_bom_file_guard_validates_author_policy_against_article_and_sidecar(tmp_path: Path):
    bom_path, bom, paths = _build_real_bom(tmp_path)
    bom["author_policy"] = {
        "status": "named_author",
        "name": "Corey O'Donnell",
        "frontmatter_author_required": True,
        "schema_person_required": True,
        "named_author_voice_allowed": True,
    }
    bom["schema_notes"]["required_entities"].append("Person as author")
    write_blog_assembly_bom(bom_path, bom)

    findings = check_bom_file(
        bom_path,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        context_request_path=paths["context_request"],
        context_pack_path=paths["context_pack"],
        context_receipt_path=paths["context_receipt"],
    )

    assert any(finding["rule_id"] == "bom_named_author_frontmatter_missing" for finding in findings)
    assert any(finding["rule_id"] == "bom_named_author_sidecar_missing" for finding in findings)


def test_bom_file_guard_rejects_faq_schema_without_visible_faq(tmp_path: Path):
    bom_path, bom, paths = _build_real_bom(tmp_path)
    bom["schema_notes"]["required_entities"].append("FAQPage")
    write_blog_assembly_bom(bom_path, bom)

    findings = check_bom_file(
        bom_path,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        context_request_path=paths["context_request"],
        context_pack_path=paths["context_pack"],
        context_receipt_path=paths["context_receipt"],
    )

    assert any(finding["rule_id"] == "bom_faqpage_without_visible_faq" for finding in findings)


def test_bom_file_guard_rejects_missing_faq_schema_for_visible_faq(tmp_path: Path):
    body = "## Frequently asked questions\n\n### What is AI field service software?\n\nIt is software."
    bom_path, _, paths = _build_real_bom(tmp_path, body=body)

    findings = check_bom_file(
        bom_path,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        context_request_path=paths["context_request"],
        context_pack_path=paths["context_pack"],
        context_receipt_path=paths["context_receipt"],
    )

    assert any(finding["rule_id"] == "bom_faqpage_missing" for finding in findings)


def test_bom_file_guard_rejects_video_object_without_embed(tmp_path: Path):
    bom_path, bom, paths = _build_real_bom(tmp_path)
    bom["schema_notes"]["required_entities"].append("VideoObject")
    write_blog_assembly_bom(bom_path, bom)

    findings = check_bom_file(
        bom_path,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        context_request_path=paths["context_request"],
        context_pack_path=paths["context_pack"],
        context_receipt_path=paths["context_receipt"],
    )

    assert any(finding["rule_id"] == "bom_video_object_without_embed" for finding in findings)


def test_bom_builder_supports_explicit_non_connector_blog(tmp_path: Path):
    paths = _write_real_artifacts(tmp_path)
    bom = build_blog_assembly_bom_from_files(
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        connector_binding_status="not_applicable",
        connector_not_applicable_reason="Non-Simpro editorial blog with no connector claims.",
        stage_names=["draft", "scrub", "publish_readiness"],
    )

    assert bom["connector_binding"] == {
        "status": "not_applicable",
        "reason": "Non-Simpro editorial blog with no connector claims.",
    }
    assert bom["files"]["context_request"] == ""
    assert bom["context"]["selected_resource_ids"] == []


def test_bom_builder_rejects_invalid_pack_schema_from_files(tmp_path: Path):
    paths = _write_real_artifacts(tmp_path)
    pack = json.loads(paths["context_pack"].read_text(encoding="utf-8"))
    pack["schema"] = "wrong"
    paths["context_pack"].write_text(json.dumps(pack), encoding="utf-8")

    with pytest.raises(ValueError, match="simpro-product-context-pack/v2"):
        build_blog_assembly_bom_from_files(
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            context_request_path=paths["context_request"],
            context_pack_path=paths["context_pack"],
            context_receipt_path=paths["context_receipt"],
            stage_names=["draft", "scrub", "context_binding", "publish_readiness"],
        )


def test_bom_records_optional_author_without_requiring_person_schema(tmp_path: Path):
    request, pack, receipt = _minimal_context()

    bom = build_blog_assembly_bom(
        topic_slug="field-service-scheduling-guide",
        article_path=tmp_path
        / "drafts"
        / "field-service-scheduling-guide-2026-08-10.md",
        validation_sidecar_path=tmp_path
        / "research"
        / "validation-field-service-scheduling-guide-2026-08-10.md",
        context_request_path=tmp_path
        / "research"
        / "context-request-field-service-scheduling-guide.json",
        context_pack_path=tmp_path
        / "research"
        / "context-pack-field-service-scheduling-guide.json",
        context_receipt_path=tmp_path
        / "research"
        / "context-receipt-field-service-scheduling-guide.json",
        request=request,
        pack=pack,
        receipt=receipt,
        author=None,
        schema_notes=[
            "BlogPosting",
            "BreadcrumbList",
            "FAQPage",
            "ImageObject",
            "Organization publisher reference",
        ],
        stages=["draft", "scrub", "context_binding", "publish_readiness"],
    )

    assert bom["schema"] == "simpro-blog-assembly-bom/v1"
    assert bom["identity"]["artifact_type"] == "blog"
    assert bom["author_policy"] == {
        "status": "not_provided",
        "name": "",
        "frontmatter_author_required": False,
        "schema_person_required": False,
        "named_author_voice_allowed": False,
    }
    assert "author" not in bom["frontmatter"]["required_fields"]
    assert "author" in bom["frontmatter"]["optional_fields"]
    assert "Person as author" not in bom["schema_notes"]["required_entities"]
    assert bom["context"]["context_pack_hash"] == "pack-hash"
    assert bom["context"]["receipt_hash"] == "receipt-hash"
    assert bom["context"]["selected_resource_ids"] == ["res-voice"]
    assert bom["context"]["claim_ids"] == ["claim-approved-1"]


def test_bom_requires_person_schema_only_when_named_author_exists(tmp_path: Path):
    request, pack, receipt = _minimal_context()

    bom = build_blog_assembly_bom(
        topic_slug="ai-field-service-guide",
        article_path=tmp_path / "drafts" / "ai-field-service-guide-2026-08-10.md",
        validation_sidecar_path=tmp_path
        / "research"
        / "validation-ai-field-service-guide-2026-08-10.md",
        context_request_path=tmp_path
        / "research"
        / "context-request-ai-field-service-guide.json",
        context_pack_path=tmp_path
        / "research"
        / "context-pack-ai-field-service-guide.json",
        context_receipt_path=tmp_path
        / "research"
        / "context-receipt-ai-field-service-guide.json",
        request=request,
        pack=pack,
        receipt=receipt,
        author="Corey O'Donnell",
        schema_notes=[
            "BlogPosting",
            "BreadcrumbList",
            "FAQPage",
            "Person as author",
            "ImageObject",
            "Organization publisher reference",
        ],
        stages=["draft", "scrub", "context_binding", "publish_readiness"],
    )

    assert "author" in bom["frontmatter"]["required_fields"]
    assert bom["frontmatter"]["optional_fields"] == []
    assert "Person as author" in bom["schema_notes"]["required_entities"]
    assert bom["author_policy"] == {
        "status": "named_author",
        "name": "Corey O'Donnell",
        "frontmatter_author_required": True,
        "schema_person_required": True,
        "named_author_voice_allowed": True,
    }


def test_bom_guard_requires_context_artifact_inventory():
    bom = _bom()
    del bom["files"]["context_pack"]

    findings = check_bom(
        bom,
        article_path="drafts/ai-field-service-guide-2026-08-10.md",
        validation_sidecar_path=(
            "research/validation-ai-field-service-guide-2026-08-10.md"
        ),
        context_request_path="research/context-request-ai-field-service-guide.json",
        context_pack_path="research/context-pack-ai-field-service-guide.json",
        context_receipt_path="research/context-receipt-ai-field-service-guide.json",
    )

    assert any(finding["rule_id"] == "bom_context_pack_missing" for finding in findings)


def test_bom_guard_blocks_person_author_without_named_author():
    bom = _bom()
    bom["schema_notes"]["required_entities"].append("Person as author")

    findings = check_bom(
        bom,
        article_path="drafts/ai-field-service-guide-2026-08-10.md",
        validation_sidecar_path=(
            "research/validation-ai-field-service-guide-2026-08-10.md"
        ),
        context_request_path="research/context-request-ai-field-service-guide.json",
        context_pack_path="research/context-pack-ai-field-service-guide.json",
        context_receipt_path="research/context-receipt-ai-field-service-guide.json",
    )

    assert any(
        finding["rule_id"] == "bom_person_author_without_author"
        for finding in findings
    )


def test_bom_guard_blocks_named_author_without_person_schema():
    bom = _bom(author="Corey O'Donnell")
    bom["schema_notes"]["required_entities"].remove("Person as author")

    findings = check_bom(
        bom,
        article_path="drafts/ai-field-service-guide-2026-08-10.md",
        validation_sidecar_path=(
            "research/validation-ai-field-service-guide-2026-08-10.md"
        ),
        context_request_path="research/context-request-ai-field-service-guide.json",
        context_pack_path="research/context-pack-ai-field-service-guide.json",
        context_receipt_path="research/context-receipt-ai-field-service-guide.json",
    )

    assert any(finding["rule_id"] == "bom_person_author_missing" for finding in findings)


def test_bom_guard_rejects_hard_coded_vault_topology():
    bom = _bom()
    bom["context"]["debug_source"] = (
        "C:/Users/patrick.grueschow/Desktop/Obsidian/Simpro Brand Context/wiki/hub.md"
    )

    findings = check_bom(
        bom,
        article_path="drafts/ai-field-service-guide-2026-08-10.md",
        validation_sidecar_path=(
            "research/validation-ai-field-service-guide-2026-08-10.md"
        ),
        context_request_path="research/context-request-ai-field-service-guide.json",
        context_pack_path="research/context-pack-ai-field-service-guide.json",
        context_receipt_path="research/context-receipt-ai-field-service-guide.json",
    )

    assert any(
        finding["rule_id"] == "bom_hard_coded_vault_topology"
        for finding in findings
    )


def test_bom_guard_rejects_literal_wiki_topology_string():
    bom = _bom()
    bom["context"]["legacy_route"] = "wiki/authority_root/blog-voice.md"

    findings = check_bom(
        bom,
        article_path="drafts/ai-field-service-guide-2026-08-10.md",
        validation_sidecar_path=(
            "research/validation-ai-field-service-guide-2026-08-10.md"
        ),
        context_request_path="research/context-request-ai-field-service-guide.json",
        context_pack_path="research/context-pack-ai-field-service-guide.json",
        context_receipt_path="research/context-receipt-ai-field-service-guide.json",
    )

    assert any(
        finding["rule_id"] == "bom_hard_coded_vault_topology"
        for finding in findings
    )


def test_bom_guard_requires_post_optimization_revalidation_order():
    bom = _bom(
        stages=[
            "draft",
            "scrub",
            "context_binding",
            "publish_readiness",
            "optimization",
        ]
    )

    findings = check_bom(
        bom,
        article_path="drafts/ai-field-service-guide-2026-08-10.md",
        validation_sidecar_path=(
            "research/validation-ai-field-service-guide-2026-08-10.md"
        ),
        context_request_path="research/context-request-ai-field-service-guide.json",
        context_pack_path="research/context-pack-ai-field-service-guide.json",
        context_receipt_path="research/context-receipt-ai-field-service-guide.json",
    )

    assert any(
        finding["rule_id"] == "bom_post_optimization_revalidation_missing"
        for finding in findings
    )
