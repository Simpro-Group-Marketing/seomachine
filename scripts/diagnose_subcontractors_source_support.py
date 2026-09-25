"""Report, per failing claim, the detected type and every mapped row's verdict."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, ".")

from data_sources.modules.proof_sidecar import compose_with_sidecar
from data_sources.modules.source_support import orchestration as orchestrator
from data_sources.modules.source_support.evidence_validation import (
    _matching_proofs,
    _validate_proof_entry,
)

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
ARTICLE = pathlib.Path(f"rewrites/{SLUG}-{DATE}.md")
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")


def main() -> int:
    article = ARTICLE.read_text(encoding="utf-8")
    proof_source = compose_with_sidecar(article, SIDECAR.read_text(encoding="utf-8"))
    entries = orchestrator._extract_proof_entries(proof_source)
    candidates = orchestrator._policy_aligned_candidates(
        orchestrator._extract_claim_candidates(
            article, orchestrator._known_customer_names(entries)
        ),
        orchestrator.analyze_proof_links(article, proof_source),
    )
    for candidate in candidates:
        proofs = _matching_proofs(candidate, entries)
        verdicts = [
            (proof, _validate_proof_entry(proof, candidate, base_path=ARTICLE.parent, fetcher=None))
            for proof in proofs
        ]
        if any(finding is None for _, finding in verdicts):
            continue
        print(f"\nLINE {candidate.line} | type={candidate.claim_type!r} | numeric={candidate.numeric_tokens}")
        print(f"  TEXT: {candidate.text[:200]}")
        for proof, finding in verdicts[-4:]:
            print(f"    row {proof.line} {proof.claim_type:<13} -> {finding['rule_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
