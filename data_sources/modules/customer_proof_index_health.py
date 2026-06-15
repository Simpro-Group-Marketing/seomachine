"""
Customer proof index health report.

This is a read-only planning tool for researchers and writers. It summarizes
the curated customer proof index so proof gaps can be fixed through the intake
workflow before a draft depends on weak or overused evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:  # pragma: no cover - import fallback for direct script execution
    from .proof_usage import count_customer_proof_usage
except ImportError:  # pragma: no cover
    from proof_usage import count_customer_proof_usage


FindingDict = Dict[str, Any]


def analyze_proof_index(
    *,
    index_path: str | Path = "context/customer-proof-index.json",
    ledger_path: str | Path = "context/customer-proof-usage-ledger.json",
) -> FindingDict:
    """Return a read-only health summary for the customer proof index."""
    index = _load_json(index_path, {"proof": []})
    ledger = _load_json(ledger_path, {"uses": []})
    proof_rows = [row for row in index.get("proof", []) if isinstance(row, dict)]

    return {
        "index_path": str(index_path),
        "ledger_path": str(ledger_path),
        "total_rows": len(proof_rows),
        "counts": _counts(proof_rows),
        "proof_assets": _proof_assets(proof_rows),
        "workflow_coverage": _workflow_coverage(proof_rows),
        "overused_proof": _overused_proof(proof_rows, ledger),
        "blocked_from_public_copy": _blocked_from_public_copy(proof_rows),
        "gaps": _gaps(proof_rows),
        "priority_intake_targets": _priority_intake_targets(proof_rows, ledger),
        "priority_workflow_gaps": _priority_workflow_gaps(proof_rows),
    }


def _load_json(path: str | Path, default: FindingDict) -> FindingDict:
    json_path = Path(path)
    if not json_path.exists():
        return dict(default)
    return json.loads(json_path.read_text(encoding="utf-8"))


def _counts(proof_rows: Sequence[FindingDict]) -> FindingDict:
    return {
        "source_type": dict(sorted(Counter(_text(row.get("source_type")) for row in proof_rows).items())),
        "approval_status": dict(
            sorted(Counter(_text(row.get("approval_status")) for row in proof_rows).items())
        ),
        "public_copy_allowed": dict(
            sorted(Counter("true" if bool(row.get("public_copy_allowed")) else "false" for row in proof_rows).items())
        ),
    }


def _proof_assets(proof_rows: Sequence[FindingDict]) -> FindingDict:
    quote_counts = [_approved_item_count(row.get("approved_quotes", [])) for row in proof_rows]
    metric_counts = [_approved_item_count(row.get("approved_metrics", [])) for row in proof_rows]
    return {
        "rows_with_approved_quotes": sum(1 for count in quote_counts if count > 0),
        "approved_quote_count": sum(quote_counts),
        "rows_with_approved_metrics": sum(1 for count in metric_counts if count > 0),
        "approved_metric_count": sum(metric_counts),
    }


def _approved_item_count(items: Any) -> int:
    if not isinstance(items, list):
        return 0
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if _text(item.get("status")) == "approved":
            count += 1
    return count


def _workflow_coverage(proof_rows: Sequence[FindingDict]) -> List[FindingDict]:
    coverage: Dict[str, FindingDict] = defaultdict(
        lambda: {
            "workflow": "",
            "total_rows": 0,
            "approved_public_rows": 0,
            "source_types": Counter(),
        }
    )
    for row in proof_rows:
        workflows = _list_values(row.get("workflow_fit"))
        for workflow in workflows:
            bucket = coverage[workflow]
            bucket["workflow"] = workflow
            bucket["total_rows"] += 1
            bucket["source_types"][_text(row.get("source_type"))] += 1
            if _is_approved_public(row):
                bucket["approved_public_rows"] += 1

    normalized = []
    for workflow in sorted(coverage):
        bucket = coverage[workflow]
        normalized.append(
            {
                "workflow": bucket["workflow"],
                "total_rows": bucket["total_rows"],
                "approved_public_rows": bucket["approved_public_rows"],
                "source_types": dict(sorted(bucket["source_types"].items())),
            }
        )
    return normalized


def _overused_proof(proof_rows: Sequence[FindingDict], ledger: FindingDict) -> List[FindingDict]:
    overused = []
    for row in proof_rows:
        usage = count_customer_proof_usage(
            ledger,
            proof_id=_text(row.get("proof_id")),
            source_url=_text(row.get("public_url")),
            customer=_text(row.get("customer")),
        )
        if not usage.get("overused"):
            continue
        overused.append(
            {
                "proof_id": _text(row.get("proof_id")),
                "customer": _text(row.get("customer")),
                "source_type": _text(row.get("source_type")),
                "public_url": _text(row.get("public_url")),
                "recent_uses_90d": usage.get("recent_uses_90d", 0),
                "total_uses": usage.get("total_uses", 0),
                "total_occurrences": usage.get("total_occurrences", 0),
                "overused": bool(usage.get("overused")),
            }
        )
    return sorted(overused, key=lambda row: (-int(row["recent_uses_90d"]), row["proof_id"]))


def _blocked_from_public_copy(proof_rows: Sequence[FindingDict]) -> List[FindingDict]:
    blocked = []
    for row in proof_rows:
        reasons = _blocked_reasons(row)
        if not reasons:
            continue
        blocked.append(
            {
                "proof_id": _text(row.get("proof_id")),
                "customer": _text(row.get("customer")),
                "source_type": _text(row.get("source_type")),
                "approval_status": _text(row.get("approval_status")),
                "reasons": reasons,
            }
        )
    return sorted(blocked, key=lambda row: (row["source_type"], row["proof_id"]))


def _blocked_reasons(row: FindingDict) -> List[str]:
    reasons = []
    approval_status = _text(row.get("approval_status"))
    if not bool(row.get("public_copy_allowed")):
        reasons.append("public_copy_allowed false")
    if approval_status in {"blocked", "candidate", "rejected"}:
        reasons.append(f"approval_status {approval_status}")
    if _text(row.get("source_type")) == "review_site":
        review_story = row.get("review_story", {})
        if isinstance(review_story, dict) and bool(review_story.get("story_allowed")):
            if not _text(review_story.get("public_url")):
                reasons.append("review_story public_url missing")
            if not (
                _text(review_story.get("identity_display"))
                or _text(review_story.get("business_name"))
                or _text(review_story.get("person_name"))
            ):
                reasons.append("review_story identity missing")
    return reasons


def _gaps(proof_rows: Sequence[FindingDict]) -> List[FindingDict]:
    workflow_rows = _workflow_coverage(proof_rows)
    return [
        {
            "type": "workflow_without_approved_public_proof",
            "workflow": row["workflow"],
            "total_rows": row["total_rows"],
        }
        for row in workflow_rows
        if row["total_rows"] > 0 and row["approved_public_rows"] == 0
    ]


def _priority_intake_targets(proof_rows: Sequence[FindingDict], ledger: FindingDict) -> List[FindingDict]:
    targets = []
    for row in proof_rows:
        if _is_approved_public(row):
            continue
        if _is_source_register(row):
            continue
        usage = count_customer_proof_usage(
            ledger,
            proof_id=_text(row.get("proof_id")),
            source_url=_text(row.get("public_url")),
            customer=_text(row.get("customer")),
        )
        score = _target_priority_score(row, usage)
        if score <= 0:
            continue
        targets.append(
            {
                "proof_id": _text(row.get("proof_id")),
                "customer": _text(row.get("customer")),
                "source_type": _text(row.get("source_type")),
                "approval_status": _text(row.get("approval_status")),
                "public_copy_allowed": bool(row.get("public_copy_allowed")),
                "public_url": _text(row.get("public_url")),
                "workflows": _list_values(row.get("workflow_fit")),
                "blocking_reasons": _target_blocking_reasons(row),
                "recommended_action": _recommended_action(row),
                "priority_score": score,
                "overused": bool(usage.get("overused")),
            }
        )
    return sorted(targets, key=lambda row: (-int(row["priority_score"]), row["proof_id"]))


def _priority_workflow_gaps(proof_rows: Sequence[FindingDict]) -> List[FindingDict]:
    coverage = _workflow_coverage(proof_rows)
    rows_by_workflow: Dict[str, List[FindingDict]] = defaultdict(list)
    for row in proof_rows:
        for workflow in _list_values(row.get("workflow_fit")):
            rows_by_workflow[workflow].append(row)

    priority_gaps = []
    for row in coverage:
        if row["approved_public_rows"] > 0:
            continue
        workflow = row["workflow"]
        candidates = [
            candidate for candidate in rows_by_workflow.get(workflow, []) if not _is_source_register(candidate)
        ]
        ranked = sorted(
            candidates,
            key=lambda candidate: (-_target_priority_score(candidate, {}), _text(candidate.get("proof_id"))),
        )
        best = ranked[0] if ranked else {}
        priority_gaps.append(
            {
                "workflow": workflow,
                "total_rows": row["total_rows"],
                "source_types": row["source_types"],
                "candidate_proof_ids": [_text(candidate.get("proof_id")) for candidate in ranked],
                "best_candidate": _text(best.get("proof_id")) if best else "",
                "recommended_action": _recommended_action(best) if best else "add_source_backed_candidate",
                "priority_score": _target_priority_score(best, {}) if best else 0,
            }
        )
    return sorted(
        priority_gaps,
        key=lambda row: (-int(row["priority_score"]), -int(row["total_rows"]), row["workflow"]),
    )


def _target_priority_score(row: FindingDict, usage: FindingDict) -> int:
    approval_status = _text(row.get("approval_status"))
    source_type = _text(row.get("source_type"))
    score = 0
    if approval_status == "approved":
        score += 60
    elif approval_status == "ready":
        score += 50
    elif approval_status == "candidate":
        score += 10
    elif approval_status in {"blocked", "rejected"}:
        score -= 100

    if _text(row.get("public_url")):
        score += 30
    if bool(row.get("public_copy_allowed")):
        score += 20

    score += {
        "reference": 25,
        "quote_matrix": 22,
        "case_study": 20,
        "review_site": 14,
        "customer_story": 8,
    }.get(source_type, 0)

    if _approved_item_count(row.get("approved_quotes", [])):
        score += 8
    if _approved_item_count(row.get("approved_metrics", [])):
        score += 8
    if usage.get("overused"):
        score -= 30
    return score


def _target_blocking_reasons(row: FindingDict) -> List[str]:
    reasons = _blocked_reasons(row)
    approval_status = _text(row.get("approval_status"))
    if approval_status and approval_status != "approved":
        reasons.append(f"approval_status {approval_status}")
    if not _text(row.get("public_url")):
        reasons.append("public_url missing")
    return sorted(set(reasons))


def _recommended_action(row: FindingDict) -> str:
    if not row:
        return "add_source_backed_candidate"
    approval_status = _text(row.get("approval_status"))
    if not _text(row.get("public_url")):
        return "capture_public_url"
    if not bool(row.get("public_copy_allowed")):
        return "resolve_public_copy_permission"
    if approval_status != "approved":
        return "approve_theme_only"
    has_quote_or_metric = bool(
        _approved_item_count(row.get("approved_quotes", []))
        or _approved_item_count(row.get("approved_metrics", []))
    )
    if not has_quote_or_metric:
        return "add_quote_or_metric_evidence"
    return "review_source_boundary"


def _is_approved_public(row: FindingDict) -> bool:
    return _text(row.get("approval_status")) == "approved" and bool(row.get("public_copy_allowed"))


def _is_source_register(row: FindingDict) -> bool:
    proof_id = _text(row.get("proof_id"))
    customer = _text(row.get("customer"))
    restrictions = " ".join(_list_values(row.get("restrictions")))
    if proof_id.endswith("source-register"):
        return True
    if "source register" in customer:
        return True
    return "selection source only" in restrictions or "selection and governance source only" in restrictions


def _list_values(value: Any) -> List[str]:
    if isinstance(value, list):
        return sorted({_text(item) for item in value if _text(item)})
    if isinstance(value, str) and value.strip():
        return sorted({item.strip().lower() for item in value.replace("|", ";").split(";") if item.strip()})
    return []


def _text(value: Any) -> str:
    return str(value or "").strip().lower()


def _print_text_report(report: FindingDict) -> None:
    print("Customer Proof Index Health")
    print(f"- Index: {report['index_path']}")
    print(f"- Ledger: {report['ledger_path']}")
    print(f"- Total rows: {report['total_rows']}")
    print(f"- Source types: {_format_counts(report['counts']['source_type'])}")
    print(f"- Approval statuses: {_format_counts(report['counts']['approval_status'])}")
    print(f"- Public copy allowed: {_format_counts(report['counts']['public_copy_allowed'])}")
    assets = report["proof_assets"]
    print(
        "- Approved proof assets: "
        f"{assets['rows_with_approved_quotes']} rows with quotes "
        f"({assets['approved_quote_count']} total), "
        f"{assets['rows_with_approved_metrics']} rows with metrics "
        f"({assets['approved_metric_count']} total)"
    )
    print(f"- Overused proof rows: {len(report['overused_proof'])}")
    for row in report["overused_proof"][:10]:
        print(
            f"  - {row['proof_id']} ({row['customer']}): "
            f"{row['recent_uses_90d']} recent uses, {row['total_occurrences']} raw occurrences"
        )
    print(f"- Blocked from public copy: {len(report['blocked_from_public_copy'])}")
    print(f"- Priority intake targets: {len(report['priority_intake_targets'])}")
    for row in report["priority_intake_targets"][:10]:
        workflows = ", ".join(row["workflows"][:4]) if row["workflows"] else "no workflow"
        reasons = "; ".join(row["blocking_reasons"]) if row["blocking_reasons"] else "approval needed"
        print(
            f"  - {row['proof_id']} ({row['source_type']}/{row['approval_status']}): "
            f"{workflows}; {row['recommended_action']}; {reasons}"
        )
    print(f"- Priority workflow gaps: {len(report['priority_workflow_gaps'])}")
    for row in report["priority_workflow_gaps"][:10]:
        print(
            f"  - {row['workflow']}: best={row['best_candidate'] or 'none'}; "
            f"{row['recommended_action']}; {row['total_rows']} indexed rows"
        )
    print(f"- Workflow gaps: {len(report['gaps'])}")
    for row in report["gaps"][:10]:
        print(f"  - {row['workflow']}: {row['total_rows']} indexed rows, 0 approved public rows")


def _format_counts(counts: FindingDict) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in counts.items())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report customer proof index health without writing files.")
    parser.add_argument("--index", default="context/customer-proof-index.json")
    parser.add_argument("--ledger", default="context/customer-proof-usage-ledger.json")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report = analyze_proof_index(index_path=args.index, ledger_path=args.ledger)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        _print_text_report(report)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
