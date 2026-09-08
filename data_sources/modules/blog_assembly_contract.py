"""Shared strict helpers for blog assembly artifacts and deterministic JSON."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
PUBLIC_ARTICLE_DIRECTORIES = frozenset(
    {"drafts", "rewrites", "published", "review-required"}
)
SELECTOR_EVIDENCE_LINE_RE = re.compile(
    r"(?im)^[-*+]\s*Selector evidence:\s*(.+?)\s*\|\s*"
    r"SHA-256:\s*([0-9a-f]{64})\s*$"
)
FRED_SELECTION_SECTION_RE = re.compile(
    r"(?ms)^##[ \t]+Fred Voccola Authority Selection[ \t]*\r?\n"
    r".*?(?=^##[ \t]+|\Z)"
)


def current_utc_date() -> date:
    """Return today's date in UTC through a patchable workflow clock."""
    test_override = os.environ.get("SEOMACHINE_TEST_CURRENT_UTC_DATE")
    if test_override:
        return date.fromisoformat(test_override)
    return datetime.now(timezone.utc).date()


def validate_current_assembly_date(
    value: Any,
    *,
    field: str = "assembly_date",
) -> date:
    """Require one canonical ISO date equal to the current UTC workflow date."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{field} must be a canonical ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be a canonical ISO date") from error
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must be a canonical ISO date")
    if parsed != current_utc_date():
        raise ValueError(f"{field} must equal the current UTC date")
    return parsed


def expected_blog_gate_inventory(
    *,
    visible_faq: bool,
    connector_required: bool,
) -> list[str]:
    """Return the closed, ordered gate inventory for a passed blog run."""
    gates = [
        "artifact_identity",
        "context_binding",
        "blog_assembly_bom",
        "public_artifact",
        "ai_copy_linter",
        "url_validator",
        "public_research_links",
        "metric_proof_pack",
        "numeric_claim_source",
    ]
    if visible_faq:
        gates.extend(("faq_answer_quality", "faq_proof"))
    gates.extend(
        (
            "paa_provenance",
            "editorial_plan",
            "source_support",
            "customer_proof_diversity",
            "review_story_identity",
            "early_artifact",
            "answer_withholding",
        )
    )
    if connector_required:
        gates.extend(
            (
                "vault_brand_language",
                "named_feature_status",
                "fred_authority",
            )
        )
    gates.extend(("content_scorer", "input_seal"))
    return gates


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 digest of the exact bytes on disk."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized_text_sha256(value: Any, *, field: str) -> str:
    """Hash one required text value after the workflow's whitespace normalization."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize one JSON object exactly as the durable artifact writer does."""
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    return (
        json.dumps(
            dict(payload),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    """Return the SHA-256 digest of canonical durable JSON bytes."""
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def validate_sha256(value: Any, *, field: str = "sha256") -> str:
    """Return a valid canonical digest or raise a field-specific error."""
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be a 64-character lowercase SHA-256 digest")
    return value


def validate_governance_output_path(
    path: str | Path,
    *,
    inputs: Mapping[str, str | Path] | None = None,
) -> Path:
    """Keep Python-authored governance artifacts out of public article trees."""
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ValueError("governance output path must be non-empty")
    destination = Path(path).resolve(strict=False)
    protected_parts = {
        part.casefold()
        for part in destination.parts
        if part.casefold() in PUBLIC_ARTICLE_DIRECTORIES
    }
    if protected_parts:
        names = ", ".join(sorted(protected_parts))
        raise ValueError(
            f"governance output cannot target a public article directory: {names}"
        )
    destination_identity = os.path.normcase(str(destination))
    for label, input_path in (inputs or {}).items():
        input_identity = os.path.normcase(str(Path(input_path).resolve(strict=False)))
        if destination_identity == input_identity:
            raise ValueError(f"governance output cannot overwrite input {label}")
    return destination


def canonical_artifact(
    path: str | Path,
    *,
    workspace_root: str | Path,
) -> dict[str, str]:
    """Snapshot one existing file with a workspace-relative POSIX identity."""
    root = Path(workspace_root).resolve()
    candidate = Path(path).resolve()
    if not candidate.is_file():
        raise ValueError(f"artifact is unavailable: {path}")
    if not _within(candidate, root):
        raise ValueError(f"artifact is outside workspace: {path}")
    relative = candidate.relative_to(root).as_posix()
    try:
        resolve_artifact(relative, workspace_root=root)
    except ValueError as error:
        raise ValueError(f"artifact path is not canonical: {path}") from error
    return {"path": relative, "sha256": file_sha256(candidate)}


def artifact_inventory_snapshots(
    artifacts: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    """Flatten a strict BOM artifact inventory into readiness snapshots."""
    if not isinstance(artifacts, Mapping):
        raise ValueError("artifacts must be an object")
    snapshots: dict[str, dict[str, str]] = {}
    for label, value in artifacts.items():
        if value is None:
            continue
        if isinstance(value, list):
            for index, row in enumerate(value):
                snapshots[f"{label}[{index}]"] = _snapshot_row(
                    row,
                    field=f"artifacts.{label}[{index}]",
                )
            continue
        snapshots[str(label)] = _snapshot_row(value, field=f"artifacts.{label}")
    return snapshots


def sidecar_evidence_binding_errors(
    sidecar_content: str,
    artifacts: Mapping[str, Any],
    *,
    workspace_root: str | Path,
    required: bool,
) -> list[tuple[str, str]]:
    """Bind connector proof/Fred evidence inventory to exact sidecar evidence."""
    if not required:
        return []
    errors: list[tuple[str, str]] = []
    selector = artifacts.get("customer_proof_selector_evidence")
    selector_matches = list(SELECTOR_EVIDENCE_LINE_RE.finditer(sidecar_content))
    if len(selector_matches) != 1:
        errors.append(
            (
                "bom_customer_proof_evidence_binding_missing",
                "Connector-bound sidecar must contain exactly one selector evidence path/hash binding.",
            )
        )
    elif not isinstance(selector, Mapping):
        errors.append(
            (
                "bom_customer_proof_evidence_binding_mismatch",
                "Selector evidence binding has no matching BOM artifact.",
            )
        )
    else:
        match = selector_matches[0]
        sidecar_path = match.group(1).strip().strip("\"'")
        sidecar_hash = match.group(2)
        if (
            sidecar_path != selector.get("path")
            or sidecar_hash != selector.get("sha256")
        ):
            errors.append(
                (
                    "bom_customer_proof_evidence_binding_mismatch",
                    "Sidecar selector evidence path/hash does not match the BOM inventory.",
                )
            )

    fred = artifacts.get("fred_authority_evidence")
    fred_sections = [match.group(0).strip() for match in FRED_SELECTION_SECTION_RE.finditer(sidecar_content)]
    if len(fred_sections) != 1:
        errors.append(
            (
                "bom_fred_evidence_binding_missing",
                "Connector-bound sidecar must contain exactly one Fred Voccola Authority Selection block.",
            )
        )
    elif not isinstance(fred, Mapping):
        errors.append(
            (
                "bom_fred_evidence_binding_mismatch",
                "Fred selection evidence has no matching BOM artifact.",
            )
        )
    else:
        try:
            fred_path = resolve_artifact(
                fred.get("path"),
                workspace_root=workspace_root,
            )
            fred_content = fred_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError, ValueError):
            fred_content = ""
        if not fred_content or fred_content != fred_sections[0]:
            errors.append(
                (
                    "bom_fred_evidence_binding_mismatch",
                    "Sidecar Fred selection block does not exactly match the BOM evidence artifact.",
                )
            )
    return errors


def _snapshot_row(value: Any, *, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an artifact object")
    if set(value) != {"path", "sha256"}:
        raise ValueError(f"{field} must contain only path and sha256")
    path = value.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError(f"{field}.path must be a non-empty string")
    digest = validate_sha256(value.get("sha256"), field=f"{field}.sha256")
    return {"path": path, "sha256": digest}


def resolve_artifact(
    stored_path: Any,
    *,
    workspace_root: str | Path,
) -> Path:
    """Resolve a declared workspace-relative POSIX path without allowing escape."""
    if not isinstance(stored_path, str) or not stored_path.strip():
        raise ValueError("artifact path must be a non-empty workspace-relative POSIX path")
    value = stored_path
    pure = PurePosixPath(value)
    raw_parts = value.split("/")
    if (
        value != value.strip()
        or any(character.isspace() for character in value)
        or "\\" in value
        or pure.is_absolute()
        or WINDOWS_DRIVE_RE.match(value)
        or value.startswith("//")
        or any(part in {"", ".", ".."} for part in raw_parts)
    ):
        raise ValueError("artifact path must be a canonical workspace-relative POSIX path")
    root = Path(workspace_root).resolve()
    if not _uses_existing_path_spelling(root, raw_parts):
        raise ValueError("artifact path must be a canonical workspace-relative POSIX path")
    candidate = root.joinpath(*pure.parts).resolve()
    if not _within(candidate, root):
        raise ValueError("artifact path resolves outside workspace")
    return candidate


def _uses_existing_path_spelling(root: Path, parts: list[str]) -> bool:
    """Reject case aliases when the filesystem resolves them to another name."""
    current = root
    for part in parts:
        try:
            entries = tuple(current.iterdir())
        except OSError:
            return True
        exact = next((entry for entry in entries if entry.name == part), None)
        if exact is not None:
            current = exact
            continue
        alias = next(
            (
                entry
                for entry in entries
                if os.path.normcase(entry.name) == os.path.normcase(part)
            ),
            None,
        )
        if alias is not None:
            return False
        return True
    return True


def verify_artifact(
    row: Any,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path:
    """Validate one strict path/hash object against the current file bytes."""
    if not isinstance(row, Mapping):
        raise ValueError(f"{field} must be a path/hash object")
    expected = validate_sha256(row.get("sha256"), field=f"{field}.sha256")
    path = resolve_artifact(row.get("path"), workspace_root=workspace_root)
    if not path.is_file():
        raise ValueError(f"{field}.path is unavailable")
    if file_sha256(path) != expected:
        raise ValueError(f"{field}.sha256 does not match current file contents")
    return path


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    """Persist deterministic JSON atomically and durably in the target directory."""
    destination = validate_governance_output_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = canonical_json_bytes(payload).decode("utf-8")
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
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _within(candidate: Path, root: Path) -> bool:
    candidate_identity = os.path.normcase(str(candidate))
    root_identity = os.path.normcase(str(root))
    try:
        return os.path.commonpath((candidate_identity, root_identity)) == root_identity
    except ValueError:
        return False
