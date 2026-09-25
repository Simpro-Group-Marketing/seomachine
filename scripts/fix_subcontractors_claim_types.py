"""Align Source Map claim types with the type the guard detects for each unit.

Guard findings carry a ``proof_line`` numbered against the composed
article-plus-sidecar document, so the line is translated back to the sidecar
before the row is rewritten.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, ".")

from data_sources.modules.proof_sidecar import compose_with_sidecar
from data_sources.modules.source_support_guard import check_file

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
ARTICLE = pathlib.Path(f"rewrites/{SLUG}-{DATE}.md")
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")
SUGGESTION = re.compile(r"Set Claim type to (\w+)")


def sidecar_offset(sidecar_lines: list[str]) -> int:
    composed = compose_with_sidecar(
        ARTICLE.read_text(encoding="utf-8"),
        "\n".join(sidecar_lines) + "\n",
    ).splitlines()
    span = len(sidecar_lines)
    return next(
        index
        for index in range(len(composed) - span + 1)
        if composed[index : index + span] == sidecar_lines
    )


def main() -> int:
    seen: set[tuple[str, str]] = set()
    for _ in range(25):
        findings = check_file(ARTICLE, proof_sidecar=str(SIDECAR))
        lines = SIDECAR.read_text(encoding="utf-8").splitlines()
        offset = sidecar_offset(lines)
        edits: dict[int, str] = {}
        for finding in findings:
            match = SUGGESTION.search(finding.get("suggestion", ""))
            if finding.get("rule_id") != "source_claim_type_mismatch" or not match:
                continue
            index = finding["proof_line"] - offset - 1
            key = (lines[index], match.group(1))
            if key not in seen:
                edits[index] = match.group(1)
        if not edits:
            break
        for index, want in edits.items():
            seen.add((lines[index], want))
            lines[index] = re.sub(
                r"Claim type: \w+", f"Claim type: {want}", lines[index], count=1
            )
        SIDECAR.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"applied {len(edits)} claim-type edits")
    remaining = [
        finding
        for finding in check_file(ARTICLE, proof_sidecar=str(SIDECAR))
        if finding.get("severity") == "error"
    ]
    print(f"errors remaining: {len(remaining)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
