"""Orchestrate customer-proof diversity validation."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, List, Mapping, Optional

from ..guard_common import Finding
from ..proof_sidecar import compose_with_sidecar, load_sidecar_content, resolve_sidecar_path
from .diversity_common import _case_study_urls, _customer_proof_link_findings, _customer_proof_urls, _has_customer_quote_claim, _load_ledger
from .diversity_contracts import DEFAULT_INDEX_PATH, DEFAULT_LEDGER_PATH
from .diversity_mining import _proof_mining_findings, _selector_evidence_findings
from .diversity_parsing import _extract_customer_proof_pack, _extract_customer_proof_slate, _extract_selected_customer_proof_mining, _extract_selection_decision
from .diversity_reuse import _reuse_findings, _stronger_underused_candidate_findings
from .diversity_selection import _missing_pack_findings, _pack_selection_findings
from .diversity_slate import _slate_findings


def check_content(
    content: str,
    *,
    proof_content: Optional[str] = None,
    proof_sidecar_path: str | Path | None = None,
    source_path: str | Path | None = None,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    proof_index_path: str | Path = DEFAULT_INDEX_PATH,
    ledger_payload: Mapping[str, Any] | None = None,
    proof_index_payload: Mapping[str, Any] | None = None,
    validated_claim_set: object | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    reference_date: Optional[date] = None,
) -> List[Finding]:
    """Return customer-proof selection and reuse findings."""
    proof_source = compose_with_sidecar(content, proof_content)
    pack = _extract_customer_proof_pack(proof_source)
    decision = _extract_selection_decision(proof_source)
    slate = _extract_customer_proof_slate(proof_source)
    mining = _extract_selected_customer_proof_mining(proof_source)
    article_case_study_urls = _case_study_urls(content)
    proof_urls = _customer_proof_urls(proof_source)
    findings: List[Finding] = _customer_proof_link_findings(
        content,
        proof_source,
    )

    if pack is None:
        findings.extend(_missing_pack_findings(content, article_case_study_urls))
        return sorted(
            findings,
            key=lambda finding: (
                finding["severity"] != "error",
                finding["line"],
                finding["rule_id"],
            ),
        )

    all_case_study_urls = sorted(
        set(article_case_study_urls + _case_study_urls("\n".join(pack["lines"])))
    )
    all_customer_proof_urls = sorted(set(all_case_study_urls + proof_urls))
    findings.extend(
        _pack_selection_findings(
            content,
            pack,
            decision,
            all_case_study_urls=all_case_study_urls,
            all_customer_proof_urls=all_customer_proof_urls,
        )
    )
    findings.extend(
        _slate_findings(
            content,
            proof_source,
            slate,
            decision,
            all_customer_proof_urls=all_customer_proof_urls,
        )
    )
    if (
        proof_sidecar_path
        and slate is not None
        and (all_customer_proof_urls or _has_customer_quote_claim(content))
    ):
        findings.extend(
            _selector_evidence_findings(
                slate,
                proof_content or "",
                proof_sidecar_path,
            )
        )
    findings.extend(
        _proof_mining_findings(
            content,
            pack,
            mining,
            all_customer_proof_urls=all_customer_proof_urls,
        )
    )

    ledger = dict(ledger_payload) if ledger_payload is not None else _load_ledger(ledger_path)
    reference = reference_date or date.today()
    reuse_findings, overused_sources = _reuse_findings(
        all_customer_proof_urls,
        pack=pack,
        decision=decision,
        ledger=ledger,
        reference=reference,
    )
    findings.extend(reuse_findings)

    if overused_sources:
        findings.extend(
            _stronger_underused_candidate_findings(
                overused_sources,
                pack=pack,
                decision=decision,
                ledger=ledger,
                ledger_path=ledger_path,
                proof_index_path=proof_index_path,
                context_pack=context_pack,
                context_receipt=context_receipt,
                proof_index_payload=proof_index_payload,
                validated_claim_set=validated_claim_set,
                reference=reference,
            )
        )

    return sorted(
        findings,
        key=lambda finding: (
            finding["severity"] != "error",
            finding["line"],
            finding["rule_id"],
        ),
    )


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    proof_index_path: str | Path = DEFAULT_INDEX_PATH,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
) -> List[Finding]:
    """Check a public article file plus optional validation sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    file_path = Path(path)
    sidecar_path = resolve_sidecar_path(file_path, proof_sidecar)
    proof_content = load_sidecar_content(file_path, proof_sidecar)
    return check_content(
        file_path.read_text(encoding="utf-8"),
        proof_content=proof_content,
        proof_sidecar_path=(
            str(sidecar_path.resolve())
            if sidecar_path is not None and sidecar_path.is_file()
            else None
        ),
        source_path=file_path,
        ledger_path=ledger_path,
        proof_index_path=proof_index_path,
        context_pack=context_pack,
        context_receipt=context_receipt,
    )


__all__ = [
    'check_content',
    'check_file'
]
