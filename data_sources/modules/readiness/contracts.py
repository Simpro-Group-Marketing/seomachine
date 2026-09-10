"""Stable publish-readiness result and gate contracts."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
from typing import Any, Mapping

from ..blog_assembly_contract import canonical_json_bytes


GateResult = dict[str, Any]
ReadinessResult = dict[str, Any]
READINESS_RESULT_SCHEMA = "simpro-publish-readiness-result/v1"
READINESS_TOOL = {"name": "publish_readiness", "version": "1.0.0"}
PASSED_RESULT_FIELDS = frozenset(
    {
        "schema",
        "tool",
        "phase",
        "verification_scope",
        "file",
        "proof_sidecar",
        "context_request",
        "context_pack",
        "context_receipt",
        "assembly_bom",
        "passed",
        "artifact_kind",
        "gates",
        "score",
        "score_threshold",
        "aeo_geo",
        "scorecard",
        "priority_fixes",
        "gate_inventory",
        "input_hashes",
        "input_seal",
        "run_id",
        "started_at",
        "completed_at",
    }
)
GATE_RESULT_FIELDS = frozenset(
    {"name", "label", "passed", "errors", "warnings", "findings", "blockers"}
)


_READINESS_EXECUTION_KEY = os.urandom(32)


class ExecutedReadinessResult(dict[str, Any]):
    """Process-local proof that the result came from the complete gate runner."""

    __slots__ = ("_execution_signature", "_workspace_root")

    def __init__(self, value: Mapping[str, Any], *, workspace_root: Path) -> None:
        super().__init__(value)
        self._workspace_root = workspace_root.resolve()
        self._execution_signature = sign_readiness_execution(self)


def sign_readiness_execution(value: Mapping[str, Any]) -> str:
    return hmac.new(
        _READINESS_EXECUTION_KEY,
        canonical_json_bytes(value),
        hashlib.sha256,
    ).hexdigest()
