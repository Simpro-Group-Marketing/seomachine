from __future__ import annotations

from pathlib import Path

from data_sources.modules.hindsight_boundary_guard import check_content, check_file


VALID_SIDECAR_BLOCK = """## Hindsight Strategy Selection

- Status: internal_strategy_only
- Selected resources: res-hindsight-plumbing
- public_claim_use: prohibited
- claim_support_allowed: false
- source_pack_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
- source_receipt_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
"""


def test_public_copy_blocks_hindsight_labels_and_ids() -> None:
    content = """---
brand: Simpro
---
# Article

Hindsight shows the team reviewed HSI-2026-plumbing and 42 deals.
"""

    findings = check_content(content)

    rule_ids = {finding["rule_id"] for finding in findings}
    assert "hindsight_label_public_copy" in rule_ids
    assert "hindsight_id_public_copy" in rule_ids
    assert "raw_deal_count_public_copy" in rule_ids


def test_valid_internal_strategy_sidecar_block_passes_when_public_copy_is_clean() -> None:
    content = """---
brand: Simpro
---
# Article

Field service leaders should baseline dispatch and closeout before automation.
"""

    assert check_content(content, proof_content=VALID_SIDECAR_BLOCK) == []


def test_internal_strategy_sidecar_requires_public_use_boundary() -> None:
    content = "# Article\n\nClean public copy.\n"
    sidecar = """## Hindsight Strategy Selection

- Status: internal_strategy_only
- Selected resources: res-hindsight-plumbing
"""

    findings = check_content(content, proof_content=sidecar)

    rule_ids = {finding["rule_id"] for finding in findings}
    assert "hindsight_public_use_boundary_missing" in rule_ids
    assert "hindsight_internal_evidence_binding_missing" in rule_ids


def test_check_file_accepts_publish_readiness_signature(tmp_path: Path) -> None:
    article = tmp_path / "draft.md"
    sidecar = tmp_path / "validation.md"
    article.write_text("# Article\n\nClean public copy.\n", encoding="utf-8")
    sidecar.write_text(VALID_SIDECAR_BLOCK, encoding="utf-8")

    assert check_file(article, proof_sidecar=sidecar, fail_on="error") == []
