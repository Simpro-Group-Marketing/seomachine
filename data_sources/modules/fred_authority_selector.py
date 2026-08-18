"""Vault-backed selector for Fred Voccola media and PR authority evidence."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence

try:
    from .blog_assembly_contract import validate_governance_output_path
    from .vault_claim_receipts import (
        ApprovedClaim,
        ValidatedClaimSet,
        VaultClaimReceiptError,
        load_validated_claim_set,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import validate_governance_output_path
    from vault_claim_receipts import (
        ApprovedClaim,
        ValidatedClaimSet,
        VaultClaimReceiptError,
        load_validated_claim_set,
    )


FRED_AUTHORITY_CLAIM_TYPE = "fred-authority-joined-v2"
RECEIPT_APPROVED_STATUS = "receipt_approved"

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "blog",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
}


class FredAuthorityDataError(RuntimeError):
    """Raised when the vault evidence contract cannot be verified."""


def select_fred_authority(
    topic: str,
    *,
    title: str = "",
    objective: str = "",
    vault_root: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    limit: int = 5,
) -> List[dict]:
    """Return ranked, vault-verified Fred Voccola authority candidates."""
    try:
        receipt_claims = load_validated_claim_set(
            context_pack,
            context_receipt,
            vault_root=vault_root,
        )
    except VaultClaimReceiptError as exc:
        raise FredAuthorityDataError(f"Fred authority context receipt is invalid: {exc}") from exc
    if not receipt_claims.available:
        raise FredAuthorityDataError(
            f"Fred authority context receipt is unavailable: {receipt_claims.blocker}"
        )
    query_tokens = _tokens(" ".join((topic, title, objective)))
    candidates: List[dict] = []

    for approved_claim in _fred_authority_claims(receipt_claims):
        candidate = _candidate_from_claim(approved_claim)
        candidate["relevance_score"] = _relevance_score(query_tokens, candidate)
        authority_bonus = 8 if not candidate["playlist_only"] else 0
        collection_penalty = 4 if candidate["playlist_collection"] else 0
        candidate["score"] = candidate["relevance_score"] + authority_bonus - collection_penalty
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            int(item.get("score", 0)),
            int(item.get("relevance_score", 0)),
            not bool(item.get("playlist_only", False)),
            str(item.get("inventory_id", "")),
        ),
        reverse=True,
    )
    return candidates[: max(limit, 0)]


def build_fred_authority_slate(
    topic: str,
    *,
    title: str = "",
    objective: str = "",
    vault_root: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    limit: int = 5,
    selected_id: Optional[str] = None,
    output_path: str | Path | None = None,
) -> str:
    """Return a sidecar-ready Fred Voccola Authority Selection block."""
    results = select_fred_authority(
        topic,
        title=title,
        objective=objective,
        vault_root=vault_root,
        context_pack=context_pack,
        context_receipt=context_receipt,
        limit=limit,
    )
    candidate_by_id = {
        str(result.get("inventory_id", "")): result for result in results
    }
    selected = selected_id.strip() if selected_id else "none"
    if selected != "none" and selected not in candidate_by_id:
        raise FredAuthorityDataError(
            f"Selected Fred authority ID is not in the verified candidate slate: {selected}"
        )

    command = _selector_command(
        topic,
        title=title,
        objective=objective,
        context_pack=context_pack,
        context_receipt=context_receipt,
        limit=limit,
        output_path=output_path,
    )
    top_candidates = [
        str(result["inventory_id"])
        for result in results
        if result.get("inventory_id")
    ]
    selected_row = candidate_by_id.get(selected)
    claim_ids = [
        str(result.get("claim_id", ""))
        for result in results
        if result.get("claim_id")
    ]
    receipt_revision = next(
        (
            str(result.get("context_receipt_revision", ""))
            for result in results
            if result.get("context_receipt_revision")
        ),
        "not available",
    )
    if selected_row:
        authority_id = selected_row.get("authority_id") or "none"
        public_url = selected_row.get("url_or_locator") or "not applicable"
        evidence_status = selected_row.get("evidence_status") or "not applicable"
        fit_decision = (
            "Editorial source review is still required before public use; "
            f"candidate {selected} ranked for direct topical overlap with {topic}."
        )
    else:
        authority_id = "none"
        public_url = "not applicable"
        evidence_status = "not applicable"
        fit_decision = (
            "No candidate has been editorially verified as directly supporting "
            f"the article topic '{topic}'; public use is rejected until that review occurs."
        )

    return "\n".join(
        [
            "## Fred Voccola Authority Selection",
            f"- Selector command: {command}",
            "- Evaluation status: completed",
            (
                "- Top candidates: "
                f"[{', '.join(top_candidates) if top_candidates else 'none'}]"
            ),
            f"- Selected: [{selected}]",
            f"- Context receipt: {context_receipt or 'not supplied'}",
            f"- Claim IDs: [{', '.join(claim_ids) if claim_ids else 'none'}]",
            f"- Receipt revision: {receipt_revision}",
            "- Approval source: connector_claim_result",
            f"- Fit decision: {fit_decision}",
            "- Intended use: none",
            "- Target section: not applicable",
            f"- Authority row: [{authority_id}]",
            f"- Public URL: {public_url}",
            f"- Evidence status: {evidence_status}",
            "- Verification method: not_applicable",
            "- Evidence excerpt: not applicable",
            "- Timestamp or locator: not applicable",
            "- Playback verified: not_applicable",
            "- Exact quote: not applicable",
            "- Embed decision: no",
            "- VideoObject: not applicable",
        ]
    )


def _fred_authority_claims(claims: ValidatedClaimSet) -> tuple[ApprovedClaim, ...]:
    """Return complete receipt-approved Fred claims without resolving raw locators."""
    return tuple(
        claim
        for claim in claims.approved_claims()
        if claim.claim_type == FRED_AUTHORITY_CLAIM_TYPE
        and claim.use_mode == "authority_support"
        and bool(claim.selector_id)
        and bool(claim.authority_resource_id)
        and bool(claim.assertion)
        and claim.public_url.startswith(("http://", "https://"))
    )


def _candidate_from_claim(claim: ApprovedClaim) -> dict:
    """Project validated connector claim metadata into the selector contract."""
    playlist_collection = bool(
        re.search(r"youtube\.com/playlist\?", claim.public_url, re.IGNORECASE)
    )
    return {
        "inventory_id": claim.selector_id,
        "authority_id": claim.authority_resource_id,
        "authority_resource_id": claim.authority_resource_id,
        "title": claim.assertion,
        "url_or_locator": claim.public_url,
        "evidence_status": RECEIPT_APPROVED_STATUS,
        "public_use_status": RECEIPT_APPROVED_STATUS,
        "authority_cluster": "",
        "authority_allowed_use": claim.use_mode,
        "authority_evidence_status": RECEIPT_APPROVED_STATUS,
        "authority_public_use_status": RECEIPT_APPROVED_STATUS,
        "authority_canonical_url": claim.public_url,
        "authority_kind": (
            "discovery_or_embed_only"
            if playlist_collection
            else "earned_media_authority"
        ),
        "claim_id": claim.claim_id,
        "approval_source": claim.approval_source,
        "context_receipt_revision": claim.receipt_revision,
        "playlist_only": playlist_collection,
        "playlist_collection": playlist_collection,
    }


def _resolve_vault_root(vault_root: str | Path | None) -> Path | None:
    """Normalize an explicit root for legacy callers without hidden fallbacks."""
    if vault_root is None or not str(vault_root).strip():
        return None
    return Path(vault_root)


def _is_public_youtube_url(url: str) -> bool:
    return bool(
        re.fullmatch(
            r"https://(?:www\.)?(?:youtube\.com/watch\?v=[A-Za-z0-9_-]{6,}"
            r"|youtu\.be/[A-Za-z0-9_-]{6,})(?:[&#?].*)?",
            url.strip(),
            flags=re.IGNORECASE,
        )
    )


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1 and token not in STOPWORDS
    }


def _relevance_score(query_tokens: set[str], candidate: dict) -> int:
    weighted_fields = (
        (candidate.get("title", ""), 4),
        (candidate.get("authority_cluster", ""), 4),
        (candidate.get("authority_allowed_use", ""), 2),
        (candidate.get("outlet", ""), 1),
        (candidate.get("notes", ""), 1),
    )
    return sum(
        len(query_tokens & _tokens(value)) * weight
        for value, weight in weighted_fields
    )


def _selector_command(
    topic: str,
    *,
    title: str,
    objective: str,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    limit: int,
    output_path: str | Path | None,
) -> str:
    parts = [
        "python",
        "data_sources/modules/fred_authority_selector.py",
        topic,
    ]
    if title:
        parts.extend(("--title", title))
    if objective:
        parts.extend(("--objective", objective))
    if context_pack:
        parts.extend(("--context-pack", str(context_pack)))
    if context_receipt:
        parts.extend(("--context-receipt", str(context_receipt)))
    parts.extend(("--slate", "--limit", str(limit)))
    if output_path:
        parts.extend(("--output", str(output_path)))
    return " ".join(shlex.quote(part) for part in parts)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rank vault-verified Fred Voccola authority evidence."
    )
    parser.add_argument("topic", help="Article topic or target query.")
    parser.add_argument("--title", default="", help="Working article title.")
    parser.add_argument("--objective", default="", help="Article objective.")
    parser.add_argument("--vault-root", help="Simpro Brand Context vault root.")
    parser.add_argument("--context-pack", help="simpro-product-context-pack/v2 JSON path.")
    parser.add_argument("--context-receipt", help="simpro-context-receipt/v1 JSON path.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum candidates.")
    parser.add_argument(
        "--slate",
        action="store_true",
        help="Print the sidecar-ready selection block.",
    )
    parser.add_argument(
        "--selected-id",
        help="Explicitly record one verified candidate in slate output.",
    )
    parser.add_argument(
        "--output",
        help="Atomically save the exact sidecar-ready slate as BOM evidence.",
    )
    return parser


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.output and not args.slate:
        parser.error("--output requires --slate")
    try:
        if args.slate:
            if args.output:
                _reject_evidence_output_collision(
                    args.output,
                    context_pack=args.context_pack,
                    context_receipt=args.context_receipt,
                )
            slate = build_fred_authority_slate(
                args.topic,
                title=args.title,
                objective=args.objective,
                vault_root=args.vault_root,
                context_pack=args.context_pack,
                context_receipt=args.context_receipt,
                limit=args.limit,
                selected_id=args.selected_id,
                output_path=args.output,
            )
            if args.output:
                _atomic_write_text(args.output, slate + "\n")
            print(slate)
        else:
            print(
                json.dumps(
                    select_fred_authority(
                        args.topic,
                        title=args.title,
                        objective=args.objective,
                        vault_root=args.vault_root,
                        context_pack=args.context_pack,
                        context_receipt=args.context_receipt,
                        limit=args.limit,
                    ),
                    indent=2,
                )
            )
    except (FredAuthorityDataError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def _reject_evidence_output_collision(
    output_path: str | Path,
    *,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
) -> None:
    output_identity = os.path.normcase(str(Path(output_path).resolve()))
    for label, value in (
        ("context pack", context_pack),
        ("context receipt", context_receipt),
    ):
        if value and output_identity == os.path.normcase(str(Path(value).resolve())):
            raise FredAuthorityDataError(
                f"Fred evidence output cannot overwrite the {label} input"
            )


def _atomic_write_text(path: str | Path, content: str) -> None:
    destination = validate_governance_output_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(_main())
