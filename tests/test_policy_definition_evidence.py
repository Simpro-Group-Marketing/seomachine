"""Humanizer policy files resolve as repository definitions at release."""
from __future__ import annotations

import hashlib
from pathlib import Path

from data_sources.modules import blog_assembly_capabilities as capabilities
from data_sources.modules.blog_assembly.preflight import _resolvable_receipt_evidence_hashes


def _write(root: Path, relative: str, text: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tail_receipts(evidence: dict[str, str]) -> list[dict]:
    return [
        {"stage": "post_optimization_scrub", "output_artifact_hashes": {}, "evidence_hashes": evidence},
        {"stage": "post_optimization_context_binding", "output_artifact_hashes": {}, "evidence_hashes": {}},
    ]


def test_policy_definition_hashes_cover_both_humanizer_files(tmp_path: Path) -> None:
    policy = _write(tmp_path, "config/humanizer-policy.json", "{}")
    upstream = _write(tmp_path, "vendor/blader-humanizer/UPSTREAM.json", '{"x": 1}')
    assert capabilities.resolvable_policy_definition_hashes(workspace_root=tmp_path) == {policy, upstream}


def test_policy_definition_hashes_skip_missing_files(tmp_path: Path) -> None:
    assert capabilities.resolvable_policy_definition_hashes(workspace_root=tmp_path) == set()


def test_humanizer_receipt_evidence_resolves_against_current_files(tmp_path: Path) -> None:
    digest = _write(tmp_path, "config/humanizer-policy.json", "{}")
    resolvable = _resolvable_receipt_evidence_hashes(
        _tail_receipts({"humanizer_policy": digest}), artifacts={}, workspace_root=tmp_path
    )
    assert digest in resolvable


def test_edited_humanizer_policy_no_longer_resolves_old_digest(tmp_path: Path) -> None:
    old = _write(tmp_path, "config/humanizer-policy.json", "{}")
    _write(tmp_path, "config/humanizer-policy.json", '{"changed": true}')
    resolvable = _resolvable_receipt_evidence_hashes(
        _tail_receipts({"humanizer_policy": old}), artifacts={}, workspace_root=tmp_path
    )
    assert old not in resolvable
