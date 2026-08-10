from __future__ import annotations

from pathlib import Path

from data_sources.modules.blog_assembly_bom import build_blog_assembly_bom
from data_sources.modules.blog_assembly_bom_guard import check_bom


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
