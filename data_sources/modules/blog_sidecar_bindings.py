"""Validate exact sidecar bindings to selector and Fred evidence artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Mapping


SELECTOR_EVIDENCE_LINE_RE = re.compile(
    r"(?im)^[-*+]\s*Selector evidence:\s*(.+?)\s*\|\s*"
    r"SHA-256:\s*([0-9a-f]{64})\s*$"
)
FRED_SELECTION_SECTION_RE = re.compile(
    r"(?ms)^##[ \t]+Fred Voccola Authority Selection[ \t]*\r?\n"
    r".*?(?=^##[ \t]+|\Z)"
)


def binding_errors(
    sidecar_content: str,
    artifacts: Mapping[str, Any],
    *,
    workspace_root: str | Path,
    required: bool,
    resolve_artifact: Callable[..., Path],
) -> list[tuple[str, str]]:
    """Bind connector proof/Fred evidence inventory to exact sidecar evidence."""
    if not required:
        return []
    errors: list[tuple[str, str]] = []
    selector = artifacts.get("customer_proof_selector_evidence")
    selector_matches = list(SELECTOR_EVIDENCE_LINE_RE.finditer(sidecar_content))
    if len(selector_matches) != 1:
        errors.append(
            (
                "bom_customer_proof_evidence_binding_missing",
                "Connector-bound sidecar must contain exactly one selector evidence path/hash binding.",
            )
        )
    elif not isinstance(selector, Mapping):
        errors.append(
            (
                "bom_customer_proof_evidence_binding_mismatch",
                "Selector evidence binding has no matching BOM artifact.",
            )
        )
    else:
        match = selector_matches[0]
        sidecar_path = match.group(1).strip().strip("\"'")
        sidecar_hash = match.group(2)
        if sidecar_path != selector.get("path") or sidecar_hash != selector.get("sha256"):
            errors.append(
                (
                    "bom_customer_proof_evidence_binding_mismatch",
                    "Sidecar selector evidence path/hash does not match the BOM inventory.",
                )
            )

    fred = artifacts.get("fred_authority_evidence")
    fred_sections = [
        match.group(0).strip()
        for match in FRED_SELECTION_SECTION_RE.finditer(sidecar_content)
    ]
    if len(fred_sections) != 1:
        errors.append(
            (
                "bom_fred_evidence_binding_missing",
                "Connector-bound sidecar must contain exactly one Fred Voccola Authority Selection block.",
            )
        )
    elif not isinstance(fred, Mapping):
        errors.append(
            (
                "bom_fred_evidence_binding_mismatch",
                "Fred selection evidence has no matching BOM artifact.",
            )
        )
    else:
        try:
            fred_path = resolve_artifact(
                fred.get("path"),
                workspace_root=workspace_root,
            )
            fred_content = fred_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError, ValueError):
            fred_content = ""
        if not fred_content or fred_content != fred_sections[0]:
            errors.append(
                (
                    "bom_fred_evidence_binding_mismatch",
                    "Sidecar Fred selection block does not exactly match the BOM evidence artifact.",
                )
            )
    return errors
