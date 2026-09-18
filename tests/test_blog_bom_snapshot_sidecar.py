from __future__ import annotations

from pathlib import Path

from data_sources.modules import blog_assembly_contract
from data_sources.modules.blog_bom_validation.snapshot_adapters import (
    sidecar_binding_errors,
)


class _CapturedEvidence:
    def __init__(self, fred_content: str):
        self.fred_content = fred_content
        self.text_row_calls: list[tuple[object, str]] = []

    def text_row(self, row: object, *, field: str) -> str:
        self.text_row_calls.append((row, field))
        assert field == "artifacts.fred_authority_evidence"
        return self.fred_content


def test_sidecar_binding_errors_uses_compatibility_exports_for_captured_bindings(
    tmp_path: Path,
):
    fred_section = (
        "## Fred Voccola Authority Selection\n"
        "Selected: [none]\n"
        "Reason: no eligible authority source for this article objective."
    )
    selector_hash = "a" * 64
    sidecar = (
        "- Selector evidence: research/customer-proof-selector-evidence.json | "
        f"SHA-256: {selector_hash}\n\n"
        f"{fred_section}\n"
    )
    artifacts = {
        "customer_proof_selector_evidence": {
            "path": "research/customer-proof-selector-evidence.json",
            "sha256": selector_hash,
        },
        "fred_authority_evidence": {
            "path": "research/fred-authority-evidence.md",
            "sha256": "b" * 64,
        },
    }
    captured = _CapturedEvidence(fred_section)

    errors = sidecar_binding_errors(
        blog_assembly_contract,
        sidecar,
        artifacts,
        captured=captured,
        root=tmp_path,
        required=True,
    )

    assert errors == []
    assert captured.text_row_calls == [
        (artifacts["fred_authority_evidence"], "artifacts.fred_authority_evidence")
    ]


def test_sidecar_binding_errors_normalizes_captured_windows_newlines(
    tmp_path: Path,
):
    fred_section = (
        "## Fred Voccola Authority Selection\n"
        "Selected: [none]\n"
        "Reason: no eligible authority source for this article objective."
    )
    selector_hash = "a" * 64
    sidecar = (
        "- Selector evidence: research/customer-proof-selector-evidence.json | "
        f"SHA-256: {selector_hash}\r\n\r\n"
        f"{fred_section.replace(chr(10), chr(13) + chr(10))}\r\n"
    )
    artifacts = {
        "customer_proof_selector_evidence": {
            "path": "research/customer-proof-selector-evidence.json",
            "sha256": selector_hash,
        },
        "fred_authority_evidence": {
            "path": "research/fred-authority-evidence.md",
            "sha256": "b" * 64,
        },
    }
    captured = _CapturedEvidence(fred_section)

    errors = sidecar_binding_errors(
        blog_assembly_contract,
        sidecar,
        artifacts,
        captured=captured,
        root=tmp_path,
        required=True,
    )

    assert errors == []
