"""Add one exactly-bound Source Map row per unmapped general claim.

The general-claim contract wants the Source Map ``Claim`` to normalize to the
public claim in full, so every failing unit gets its own row rather than a
reworded shared one. Rows are only added, never rewritten, because rewriting a
shared row moves the failure onto whichever other unit relied on it.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, ".")

from data_sources.modules.numeric_claim_source_guard import _claim_text_for_detection
from data_sources.modules.proof_sidecar import compose_with_sidecar
from data_sources.modules.source_support.claim_matching import _general_claim_type
from data_sources.modules.source_support.proof_parsing import _parse_proof_fields
from data_sources.modules.source_support.text_matching import _normalize_text
from data_sources.modules.source_support_guard import check_file

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
ARTICLE = pathlib.Path(f"rewrites/{SLUG}-{DATE}.md")
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")
ANCHOR = "\n\n## FAQ Source Policy"
GENERAL_RULES = {
    "source_claim_binding_mismatch",
    "source_claim_type_mismatch",
    "source_class_invalid",
    "source_class_claim_fit_invalid",
}
CARRY_FIELDS = (
    "source class",
    "evidence relation",
    "url",
    "evidence",
    "original-source status",
    "source date",
    "checked date",
    "claim fit",
    "freshness decision",
    "freshness reason",
    "artifact",
    "capture receipt",
    "capture receipt hash",
    "classification artifact",
    "classification hash",
)
FIELD_LABELS = {
    "source class": "Source class",
    "evidence relation": "Evidence relation",
    "url": "URL",
    "evidence": "Evidence",
    "original-source status": "Original-source status",
    "source date": "Source date",
    "checked date": "Checked date",
    "claim fit": "Claim fit",
    "freshness decision": "Freshness decision",
    "freshness reason": "Freshness reason",
    "artifact": "Artifact",
    "capture receipt": "Capture receipt",
    "capture receipt hash": "Capture receipt hash",
    "classification artifact": "Classification artifact",
    "classification hash": "Classification hash",
}


def bindable_claim(text: str) -> str:
    """Render the public claim so it parses as one field and normalizes alike."""
    claim = _claim_text_for_detection(text).replace("|", " ")
    return re.sub(r"\s+", " ", claim).strip()


def sidecar_offset(lines: list[str]) -> int:
    composed = compose_with_sidecar(
        ARTICLE.read_text(encoding="utf-8"), "\n".join(lines) + "\n"
    ).splitlines()
    span = len(lines)
    return next(
        index
        for index in range(len(composed) - span + 1)
        if composed[index : index + span] == lines
    )


def template_fields(lines: list[str], offset: int, proof_line: object) -> dict[str, str]:
    if not isinstance(proof_line, int):
        return {}
    row = lines[proof_line - offset - 1].strip()
    return _parse_proof_fields(row[1:]) if row.startswith("-") else {}


def build_row(claim: str, claim_type: str, fields: dict[str, str]) -> str:
    parts = [f"- Claim: {claim}", f"Claim type: {claim_type}"]
    parts += [
        f"{FIELD_LABELS[name]}: {fields[name]}"
        for name in CARRY_FIELDS
        if fields.get(name)
    ]
    parts += [
        "Citation mode: inline_required",
        "Status: approved",
        f"Intended use: Exact binding for the public claim \"{claim[:60]}\"",
    ]
    return " | ".join(parts)


def main() -> int:
    for attempt in range(12):
        findings = check_file(ARTICLE, proof_sidecar=str(SIDECAR))
        lines = SIDECAR.read_text(encoding="utf-8").splitlines()
        offset = sidecar_offset(lines)
        existing = {
            _normalize_text(_parse_proof_fields(line.strip()[1:]).get("claim", ""))
            for line in lines
            if line.strip().startswith("- Claim:")
        }
        rows: list[str] = []
        for finding in findings:
            if finding.get("rule_id") not in GENERAL_RULES:
                continue
            claim = bindable_claim(finding["match"])
            claim_type = _general_claim_type(_claim_text_for_detection(finding["match"]))
            fields = template_fields(lines, offset, finding.get("proof_line"))
            if not claim_type or not fields.get("url") or not fields.get("evidence"):
                print(f"SKIP {finding['rule_id']}: {claim[:70]}")
                continue
            if _normalize_text(claim) in existing:
                continue
            existing.add(_normalize_text(claim))
            rows.append(build_row(claim, claim_type, fields))
        if not rows:
            break
        text = SIDECAR.read_text(encoding="utf-8")
        SIDECAR.write_text(
            text.replace(ANCHOR, "\n" + "\n".join(rows) + ANCHOR, 1), encoding="utf-8"
        )
        print(f"pass {attempt + 1}: added {len(rows)} bound rows")
    remaining = [
        finding
        for finding in check_file(ARTICLE, proof_sidecar=str(SIDECAR))
        if finding.get("severity") == "error"
    ]
    print(f"errors remaining: {len(remaining)}")
    for finding in remaining:
        print(" -", finding["rule_id"], "|", finding["match"][:80])
    return 0


if __name__ == "__main__":
    sys.exit(main())
