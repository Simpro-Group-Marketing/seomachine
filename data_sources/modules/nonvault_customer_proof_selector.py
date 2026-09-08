"""Select hash-bound public customer proof for nonconnector brand workflows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

try:
    from .blog_assembly_contract import atomic_write_json, validate_governance_output_path
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import atomic_write_json, validate_governance_output_path


SCHEMA = "simpro-nonvault-customer-proof-selector-evidence/v1"
SUPPORTED_BRAND_HOSTS = {
    "aroflo": "aroflo.com",
    "bigchange": "bigchange.com",
    "clockshark": "clockshark.com",
}
SUPPORTED_ROLES = ("metric", "quote", "theme", "experience_story")
SUPPORTED_SOURCE_TYPES = {"case_study", "customer_story", "reference"}
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}


class NonVaultProofDataError(RuntimeError):
    """Raised when non-vault proof inputs do not satisfy the contract."""


def select_nonvault_customer_proofs(
    topic: str,
    *,
    brand: str,
    index_path: str | Path = "context/customer-proof-index.json",
    ledger_path: str | Path = "context/customer-proof-usage-ledger.json",
    title: str = "",
    objective: str = "",
    article_slug: str = "",
    proof_role: str = "theme",
    require_eeat_story: bool = False,
    limit: int = 10,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """Return approved, brand-owned proof candidates for one nonconnector brand."""
    del article_slug
    if proof_role not in SUPPORTED_ROLES:
        raise NonVaultProofDataError(f"unsupported proof role: {proof_role}")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100:
        raise NonVaultProofDataError("limit must be an integer from 0 to 100")
    expected_host = SUPPORTED_BRAND_HOSTS[_brand_key(brand)]
    index = _read_json(index_path, "customer proof index")
    ledger = _read_json(ledger_path, "customer proof usage ledger")
    query_tokens = _tokens(" ".join((topic, title, objective)))
    reference = reference_date or date.today()

    ranked: list[dict[str, Any]] = []
    for source in index.get("proof", []):
        if not isinstance(source, dict):
            continue
        if not _eligible_source(source, expected_host=expected_host):
            continue
        if not _supports_role(source, proof_role, require_eeat_story=require_eeat_story):
            continue
        candidate = dict(source)
        candidate["proof_role"] = proof_role
        candidate["relevance_score"] = _relevance_score(query_tokens, source)
        candidate["recent_uses_90d"] = _recent_uses(
            ledger,
            proof_id=str(source.get("proof_id") or ""),
            reference_date=reference,
        )
        candidate["score"] = (
            candidate["relevance_score"]
            + _source_weight(str(source.get("source_type") or ""))
            - candidate["recent_uses_90d"] * 20
        )
        ranked.append(candidate)

    ranked.sort(
        key=lambda row: (
            -int(row.get("score", 0)),
            str(row.get("proof_id") or ""),
        )
    )
    return ranked[:limit]


def build_nonvault_customer_proof_slate(
    *,
    selector_command: str,
    roles: Sequence[Mapping[str, Any]],
    evidence_path: str = "",
    evidence_sha256: str = "",
) -> str:
    lines = ["Customer Proof Slate", f"- Selector command: {selector_command}"]
    if evidence_path and evidence_sha256:
        lines.append(
            f"- Selector evidence: {evidence_path} | SHA-256: {evidence_sha256}"
        )
    for row in roles:
        role = str(row["role"])
        candidates = ", ".join(str(value) for value in row["candidate_ids"]) or "none"
        selected = str(row.get("selected_id") or "none")
        rejected = row.get("rejected_overrides", {})
        rejected_text = "; ".join(
            f"{candidate}: {reason}"
            for candidate, reason in sorted(dict(rejected).items())
        ) or "none"
        lines.append(
            f"- Role: {role} | Top candidates: [{candidates}] | "
            f"Selected: [{selected}] | Rejected stronger candidates: [{rejected_text}]"
        )
    return "\n".join(lines) + "\n"


def write_nonvault_selector_evidence(
    output_path: str | Path,
    *,
    topic: str,
    brand: str,
    title: str,
    objective: str,
    article_slug: str,
    roles: Sequence[str],
    require_eeat_story: bool,
    limit: int,
    reference_date: date,
    selected_overrides: Mapping[str, str],
    rejected_overrides: Mapping[str, Mapping[str, str]],
    index_path: str | Path,
    ledger_path: str | Path,
) -> tuple[Path, str, list[dict[str, Any]]]:
    index = Path(index_path).resolve()
    ledger = Path(ledger_path).resolve()
    artifacts = {
        "index": {"path": str(index), "sha256": _file_sha256(index)},
        "ledger": {"path": str(ledger), "sha256": _file_sha256(ledger)},
    }
    role_rows: list[dict[str, Any]] = []
    for role in roles:
        results = select_nonvault_customer_proofs(
            topic,
            brand=brand,
            index_path=index,
            ledger_path=ledger,
            title=title,
            objective=objective,
            article_slug=article_slug,
            proof_role=role,
            require_eeat_story=role == "experience_story" and require_eeat_story,
            limit=limit,
            reference_date=reference_date,
        )
        candidate_ids = [str(row["proof_id"]) for row in results]
        selected_id = str(selected_overrides.get(role) or "none")
        if selected_id != "none" and selected_id not in candidate_ids:
            raise NonVaultProofDataError(
                f"Selected customer proof ID is not in the verified {role} candidate slate: {selected_id}"
            )
        selected_candidate = next(
            (row for row in results if str(row.get("proof_id")) == selected_id),
            None,
        )
        role_rows.append(
            {
                "role": role,
                "candidate_ids": candidate_ids,
                "selected_id": selected_id,
                "selected_candidate": (
                    _experience_binding(selected_candidate)
                    if role == "experience_story" and selected_candidate
                    else None
                ),
                "rejected_overrides": dict(rejected_overrides.get(role, {})),
            }
        )

    payload = {
        "schema": SCHEMA,
        "selection_outcome": (
            "customer_proof_candidates_available"
            if any(row["candidate_ids"] for row in role_rows)
            else "no_fit_customer_proof"
        ),
        "inputs": {
            "brand": _canonical_brand(brand),
            "topic": topic,
            "title": title,
            "objective": objective,
            "article_slug": article_slug,
            "roles": list(roles),
            "require_eeat_story": require_eeat_story,
            "limit": limit,
            "reference_date": reference_date.isoformat(),
            "selected_overrides": dict(selected_overrides),
            "rejected_overrides": {
                role: dict(rows) for role, rows in rejected_overrides.items()
            },
        },
        "artifacts": artifacts,
        "roles": role_rows,
    }
    output = Path(output_path)
    validate_governance_output_path(output)
    atomic_write_json(output, payload)
    return output, _file_sha256(output), role_rows


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Select public customer proof for a nonconnector brand."
    )
    parser.add_argument("topic")
    parser.add_argument(
        "--brand", required=True, choices=("AroFlo", "BigChange", "ClockShark")
    )
    parser.add_argument("--title", default="")
    parser.add_argument("--objective", default="")
    parser.add_argument("--article-slug", default="")
    parser.add_argument("--index", default="context/customer-proof-index.json")
    parser.add_argument("--ledger", default="context/customer-proof-usage-ledger.json")
    parser.add_argument("--roles", default="metric,quote,theme,experience_story")
    parser.add_argument("--require-eeat-story", action="store_true")
    parser.add_argument("--selected", action="append", default=[])
    parser.add_argument("--rejected", action="append", default=[])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--reference-date", default=date.today().isoformat())
    parser.add_argument("--slate", action="store_true")
    parser.add_argument("--evidence-output")
    args = parser.parse_args(argv)
    try:
        roles = _parse_roles(args.roles)
        selected = _parse_selected(args.selected, roles)
        rejected = _parse_rejected(args.rejected, roles)
        reference = date.fromisoformat(args.reference_date)
        if args.evidence_output:
            output, digest, role_rows = write_nonvault_selector_evidence(
                args.evidence_output,
                topic=args.topic,
                brand=args.brand,
                title=args.title,
                objective=args.objective,
                article_slug=args.article_slug,
                roles=roles,
                require_eeat_story=args.require_eeat_story,
                limit=args.limit,
                reference_date=reference,
                selected_overrides=selected,
                rejected_overrides=rejected,
                index_path=args.index,
                ledger_path=args.ledger,
            )
        else:
            output = None
            digest = ""
            role_rows = []
            for role in roles:
                results = select_nonvault_customer_proofs(
                    args.topic,
                    brand=args.brand,
                    index_path=args.index,
                    ledger_path=args.ledger,
                    title=args.title,
                    objective=args.objective,
                    article_slug=args.article_slug,
                    proof_role=role,
                    require_eeat_story=role == "experience_story"
                    and args.require_eeat_story,
                    limit=args.limit,
                    reference_date=reference,
                )
                candidate_ids = [str(row["proof_id"]) for row in results]
                selected_id = str(selected.get(role) or "none")
                if selected_id != "none" and selected_id not in candidate_ids:
                    raise NonVaultProofDataError(
                        f"Selected customer proof ID is not in the verified {role} candidate slate: {selected_id}"
                    )
                role_rows.append(
                    {
                        "role": role,
                        "candidate_ids": candidate_ids,
                        "selected_id": selected_id,
                        "rejected_overrides": dict(rejected.get(role, {})),
                    }
                )
        if args.slate:
            command = (
                "python data_sources/modules/nonvault_customer_proof_selector.py "
                + json.dumps(args.topic)
            )
            print(
                build_nonvault_customer_proof_slate(
                    selector_command=command,
                    roles=role_rows,
                    evidence_path=str(output) if output else "",
                    evidence_sha256=digest,
                ),
                end="",
            )
        else:
            print(json.dumps(role_rows, indent=2, sort_keys=True))
        return 0
    except (NonVaultProofDataError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _eligible_source(source: Mapping[str, Any], *, expected_host: str) -> bool:
    if str(source.get("approval_status") or "").casefold() != "approved":
        return False
    if source.get("public_copy_allowed") is not True:
        return False
    if str(source.get("source_type") or "").casefold() not in SUPPORTED_SOURCE_TYPES:
        return False
    proof_id = str(source.get("proof_id") or "").strip()
    if not proof_id:
        return False
    hostname = (urlsplit(str(source.get("public_url") or "")).hostname or "").casefold()
    return hostname in {expected_host, f"www.{expected_host}"}


def _supports_role(
    source: Mapping[str, Any],
    role: str,
    *,
    require_eeat_story: bool,
) -> bool:
    if role == "metric":
        return bool(source.get("approved_metrics"))
    if role == "quote":
        return bool(source.get("approved_quotes"))
    if role == "theme":
        return True
    story = source.get("review_story")
    if not isinstance(story, Mapping) or story.get("story_allowed") is not True:
        return not require_eeat_story
    identity = str(
        story.get("identity_display")
        or story.get("business_name")
        or story.get("person_name")
        or source.get("customer")
        or ""
    ).strip()
    public_url = str(
        story.get("public_url") or source.get("public_url") or ""
    ).strip()
    return bool(identity and public_url.startswith(("http://", "https://")))


def _experience_binding(source: Mapping[str, Any]) -> dict[str, str]:
    story = source.get("review_story")
    if not isinstance(story, Mapping):
        story = {}
    return {
        "proof_id": str(source.get("proof_id") or ""),
        "identity": str(
            story.get("identity_display")
            or story.get("business_name")
            or story.get("person_name")
            or source.get("customer")
            or ""
        ),
        "public_url": str(
            story.get("public_url") or source.get("public_url") or ""
        ),
        "story": str(story.get("workflow_story") or source.get("evidence") or ""),
    }


def _relevance_score(query_tokens: set[str], source: Mapping[str, Any]) -> int:
    source_text = " ".join(
        str(value)
        for key in (
            "proof_id",
            "customer",
            "industry",
            "workflow_fit",
            "themes",
            "evidence",
        )
        for value in _values(source.get(key))
    )
    return len(query_tokens.intersection(_tokens(source_text))) * 10


def _source_weight(source_type: str) -> int:
    return {"customer_story": 16, "reference": 14, "case_study": 12}.get(
        source_type.casefold(), 0
    )


def _recent_uses(
    ledger: Mapping[str, Any], *, proof_id: str, reference_date: date
) -> int:
    count = 0
    for row in ledger.get("uses", []):
        if (
            not isinstance(row, Mapping)
            or str(row.get("proof_id") or "") != proof_id
        ):
            continue
        raw_date = str(
            row.get("date_used") or row.get("date") or row.get("used_on") or ""
        )
        try:
            used_on = date.fromisoformat(raw_date)
        except ValueError:
            continue
        if 0 <= (reference_date - used_on).days <= 90:
            count += 1
    return count


def _parse_roles(value: str) -> list[str]:
    roles = [role.strip() for role in value.split(",") if role.strip()]
    if (
        not roles
        or len(set(roles)) != len(roles)
        or any(role not in SUPPORTED_ROLES for role in roles)
    ):
        raise NonVaultProofDataError("roles must be unique supported proof roles")
    if "experience_story" not in roles:
        raise NonVaultProofDataError("roles must include experience_story")
    return roles


def _parse_selected(values: Sequence[str], roles: Sequence[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        role, separator, proof_id = value.partition("=")
        if not separator or role not in roles or not proof_id.strip():
            raise NonVaultProofDataError(f"invalid selected override: {value}")
        parsed[role] = proof_id.strip()
    return parsed


def _parse_rejected(
    values: Sequence[str], roles: Sequence[str]
) -> dict[str, dict[str, str]]:
    parsed: dict[str, dict[str, str]] = {}
    for value in values:
        role, separator, remainder = value.partition("=")
        proof_id, reason_separator, reason = remainder.partition(":")
        if (
            not separator
            or not reason_separator
            or role not in roles
            or not proof_id.strip()
            or not reason.strip()
        ):
            raise NonVaultProofDataError(f"invalid rejected override: {value}")
        parsed.setdefault(role, {})[proof_id.strip()] = reason.strip()
    return parsed


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_file():
        raise NonVaultProofDataError(f"{label} is unavailable: {candidate}")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise NonVaultProofDataError(f"{label} must be a JSON object")
    return payload


def _file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _brand_key(brand: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "", brand.casefold())
    if key not in SUPPORTED_BRAND_HOSTS:
        raise NonVaultProofDataError(f"unsupported nonconnector brand: {brand}")
    return key


def _canonical_brand(brand: str) -> str:
    return {
        "aroflo": "AroFlo",
        "bigchange": "BigChange",
        "clockshark": "ClockShark",
    }[_brand_key(brand)]


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in STOPWORDS
    }


def _values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


if __name__ == "__main__":
    raise SystemExit(_main())
