"""Load reviewed deterministic Humanizer rules for release linting."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple, Pattern


MANIFEST_SCHEMA = "simpro-humanizer-upstream/v1"
POLICY_SCHEMA = "simpro-humanizer-policy/v1"


class PolicyRegexRule(NamedTuple):
    rule_id: str
    severity: str
    pattern: Pattern[str]
    message: str
    suggestion: str


def _read_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Humanizer policy is unreadable: {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"Humanizer policy file must contain an object: {path}")
    return value


@lru_cache(maxsize=1)
def load_policy_regex_rules() -> tuple[PolicyRegexRule, ...]:
    """Return only explicitly reviewed, deterministic policy-regex blockers."""

    root = Path(__file__).resolve().parents[2]
    manifest = _read_object(root / "vendor" / "blader-humanizer" / "UPSTREAM.json")
    policy = _read_object(root / "config" / "humanizer-policy.json")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise RuntimeError("Humanizer upstream manifest schema is invalid")
    if policy.get("schema") != POLICY_SCHEMA:
        raise RuntimeError("Humanizer policy schema is invalid")
    if policy.get("reviewed_upstream_commit") != manifest.get("resolved_commit"):
        raise RuntimeError("Humanizer upstream snapshot has not been reviewed")
    if manifest.get("network_at_runtime") is not False or policy.get("runtime_network") is not False:
        raise RuntimeError("Humanizer runtime network access must remain disabled")
    entries = policy.get("patterns")
    if not isinstance(entries, list):
        raise RuntimeError("Humanizer policy patterns must be a list")

    rules: list[PolicyRegexRule] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("disposition") != "blocking":
            continue
        enforcement = entry.get("enforcement")
        if not isinstance(enforcement, dict) or enforcement.get("mode") != "policy_regex":
            continue
        rule_id = entry.get("stable_rule_id")
        pattern_text = enforcement.get("pattern")
        message = enforcement.get("message")
        suggestion = enforcement.get("suggestion")
        severity = enforcement.get("severity")
        flags_value = enforcement.get("flags")
        if not isinstance(rule_id, str) or not rule_id.startswith("humanizer."):
            raise RuntimeError("Humanizer policy regex requires a stable rule ID")
        if severity != "error":
            raise RuntimeError(f"Humanizer release rule {rule_id} must use error severity")
        if not isinstance(pattern_text, str) or not pattern_text:
            raise RuntimeError(f"Humanizer release rule {rule_id} requires a regex")
        if not isinstance(message, str) or not message or not isinstance(suggestion, str) or not suggestion:
            raise RuntimeError(f"Humanizer release rule {rule_id} requires guidance")
        if not isinstance(flags_value, list) or set(flags_value) - {"ignore_case"}:
            raise RuntimeError(f"Humanizer release rule {rule_id} has unsupported flags")
        flags = re.IGNORECASE if "ignore_case" in flags_value else 0
        try:
            pattern = re.compile(pattern_text, flags)
        except re.error as error:
            raise RuntimeError(f"Humanizer release rule {rule_id} has invalid regex: {error}") from error
        rules.append(PolicyRegexRule(rule_id, severity, pattern, message, suggestion))
    return tuple(rules)
