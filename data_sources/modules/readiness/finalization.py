"""Input resealing and blocked-result sealing for publish readiness."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Mapping

from .inputs import ReadinessInputs


def reseal_readiness_inputs(
    inputs: ReadinessInputs | None,
    *,
    capture_error: ValueError | None = None,
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    """Reseal one captured inventory and return a gate-ready failure finding."""
    hashes = inputs.hash_inventory() if inputs is not None else {}
    try:
        if capture_error is not None:
            raise capture_error
        if inputs is None:
            raise ValueError("readiness input snapshot is unavailable")
        inputs.reseal()
        return inputs.hash_inventory(), []
    except ValueError as error:
        return hashes, [{
            "rule_id": "readiness_inputs_changed_during_run",
            "severity": "error",
            "line": 1,
            "column": 1,
            "message": str(error),
            "suggestion": (
                "Resume at the mutation receipt, then rerun scrub, Context Binding, "
                "BOM build, and readiness."
            ),
        }]


def finalize_blocked_result(
    result: Mapping[str, Any],
    *,
    inputs: ReadinessInputs | None,
    capture_error: ValueError | None = None,
) -> dict[str, Any]:
    """Attach the mandatory final input seal to any post-capture blocked exit."""
    hashes, findings = reseal_readiness_inputs(inputs, capture_error=capture_error)
    seal_gate = _input_seal_gate(findings)
    finalized = copy.deepcopy(dict(result))
    gates = list(finalized.get("gates") or [])
    if not any(
        isinstance(gate, Mapping) and gate.get("name") == "input_seal"
        for gate in gates
    ):
        gates.append(seal_gate)
    finalized["gates"] = gates
    finalized["gate_inventory"] = [
        str(gate.get("name") or "")
        for gate in gates
        if isinstance(gate, Mapping)
    ]
    finalized["input_hashes"] = hashes
    finalized["input_seal"] = {"status": "failed" if findings else "verified"}
    if findings:
        finalized["passed"] = False
        fixes = list(finalized.get("priority_fixes") or [])
        fixes.append({"dimension": "input_seal", "issue": findings[0]["message"]})
        finalized["priority_fixes"] = fixes
    return finalized


def _input_seal_gate(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": "input_seal",
        "label": "Input Seal",
        "passed": not findings,
        "errors": len(findings),
        "warnings": 0,
        "findings": findings,
        "blockers": [
            f"line 1: {finding['rule_id']} - {finding['message']}"
            for finding in findings[:3]
        ],
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "finalize_blocked_result",
    "reseal_readiness_inputs",
]
