"""Shared strict helpers for blog assembly artifacts and deterministic JSON."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
SELECTOR_EVIDENCE_LINE_RE = re.compile(
    r"(?im)^[-*+]\s*Selector evidence:\s*(.+?)\s*\|\s*"
    r"SHA-256:\s*([0-9a-f]{64})\s*$"
)
FRED_SELECTION_SECTION_RE = re.compile(
    r"(?ms)^##[ \t]+Fred Voccola Authority Selection[ \t]*\r?\n"
    r".*?(?=^##[ \t]+|\Z)"
)
DEFAULT_JSON_MAX_BYTES = 8 * 1024 * 1024
NORMAL_STAGE_SEQUENCE = (
    "draft",
    "scrub",
    "context_binding",
    "preflight_readiness",
    "final_readiness_attestation",
)
OPTIMIZED_STAGE_SEQUENCE = (
    "draft",
    "scrub",
    "context_binding",
    "preflight_readiness",
    "optimization",
    "post_optimization_scrub",
    "post_optimization_context_binding",
    "final_preflight_readiness",
    "final_readiness_attestation",
)
NORMAL_PROVISIONAL_STAGES = NORMAL_STAGE_SEQUENCE[:3]
NORMAL_FINAL_STAGES = NORMAL_STAGE_SEQUENCE[:4]
OPTIMIZED_PROVISIONAL_STAGES = OPTIMIZED_STAGE_SEQUENCE[:7]
OPTIMIZED_FINAL_STAGES = OPTIMIZED_STAGE_SEQUENCE[:8]


@dataclass(frozen=True, slots=True)
class BlogGateDescriptor:
    name: str
    condition: str = "always"


BLOG_GATE_DESCRIPTORS = (
    BlogGateDescriptor("artifact_identity"),
    BlogGateDescriptor("context_binding"),
    BlogGateDescriptor("blog_assembly_bom"),
    BlogGateDescriptor("public_artifact"),
    BlogGateDescriptor("ai_copy_linter"),
    BlogGateDescriptor("url_validator"),
    BlogGateDescriptor("public_research_links"),
    BlogGateDescriptor("metric_proof_pack"),
    BlogGateDescriptor("numeric_claim_source"),
    BlogGateDescriptor("faq_answer_quality", "visible_faq"),
    BlogGateDescriptor("faq_proof", "visible_faq"),
    BlogGateDescriptor("paa_provenance"),
    BlogGateDescriptor("editorial_plan"),
    BlogGateDescriptor("source_support"),
    BlogGateDescriptor("customer_proof_diversity"),
    BlogGateDescriptor("review_story_identity"),
    BlogGateDescriptor("early_artifact"),
    BlogGateDescriptor("answer_withholding"),
    BlogGateDescriptor("vault_brand_language", "connector_required"),
    BlogGateDescriptor("named_feature_status", "connector_required"),
    BlogGateDescriptor("fred_authority", "connector_required"),
    BlogGateDescriptor("content_scorer"),
    BlogGateDescriptor("input_seal"),
)


@dataclass(frozen=True, slots=True)
class ArtifactSnapshot:
    """One immutable read used for both a file digest and strict parsing."""

    path: Path
    data: bytes
    sha256: str
    payload: dict[str, Any]


def load_json_object_snapshot(
    path: str | Path,
    *,
    field: str,
    max_bytes: int = DEFAULT_JSON_MAX_BYTES,
) -> ArtifactSnapshot:
    """Read one bounded control-plane JSON object once and parse those exact bytes."""
    if not is_json_number(max_bytes) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    source = Path(path)
    try:
        with source.open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except OSError as error:
        raise ValueError(f"{field} must be a readable JSON object: {error}") from error
    if len(data) > max_bytes:
        raise ValueError(f"{field} exceeds {max_bytes} bytes")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError(f"{field} must use valid UTF-8: {error}") from error
    payload = load_json_text(text, field=field)
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be a JSON object")
    return ArtifactSnapshot(
        path=source.resolve(),
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        payload=payload,
    )


def load_json_text(text: str, *, field: str) -> Any:
    """Parse strict JSON already embedded in an immutable text artifact."""
    if not isinstance(text, str):
        raise ValueError(f"{field} must be strict JSON text")
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_object_keys,
            parse_constant=_reject_non_finite_constant,
            parse_float=_finite_float,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{field} must be strict JSON: {error}") from error


def load_json_object_text(text: str, *, field: str) -> dict[str, Any]:
    """Parse one strict embedded JSON object without permissive decoder behavior."""
    payload = load_json_text(text, field=field)
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be a JSON object")
    return payload


def _reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_non_finite_constant(value: str) -> Any:
    raise ValueError(f"non-finite number: {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite number: {value}")
    return parsed


def is_json_number(value: Any) -> bool:
    """Return whether a value is a finite JSON number, explicitly excluding bool."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (not isinstance(value, float) or math.isfinite(value))
    )


def canonical_article_run_id(
    article_path: str | Path,
    *,
    workspace_root: str | Path,
    assembly_date: str | date,
) -> str:
    """Derive a run identity from the canonical article path and assembly date."""
    root = Path(workspace_root).resolve()
    candidate = Path(article_path).resolve()
    if not _within(candidate, root):
        raise ValueError("article is outside workspace")
    relative = candidate.relative_to(root).as_posix()
    resolve_artifact(relative, workspace_root=root)
    if isinstance(assembly_date, datetime):
        raise ValueError("assembly_date must be a date or canonical ISO date")
    if isinstance(assembly_date, date):
        date_text = assembly_date.isoformat()
    elif isinstance(assembly_date, str):
        try:
            parsed = date.fromisoformat(assembly_date)
        except ValueError as error:
            raise ValueError("assembly_date must be a canonical ISO date") from error
        if parsed.isoformat() != assembly_date:
            raise ValueError("assembly_date must be a canonical ISO date")
        date_text = assembly_date
    else:
        raise ValueError("assembly_date must be a date or canonical ISO date")
    digest = hashlib.sha256(
        f"simpro-blog-run/v1\n{relative}\n{date_text}\n".encode("utf-8")
    ).hexdigest()
    return f"blog-run-{digest}"


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
    return [
        descriptor.name
        for descriptor in BLOG_GATE_DESCRIPTORS
        if _gate_descriptor_enabled(
            descriptor,
            visible_faq=visible_faq,
            connector_required=connector_required,
        )
    ]


def order_blog_gate_results(
    gates: Sequence[Mapping[str, Any]],
    *,
    visible_faq: bool,
    connector_required: bool,
) -> list[Mapping[str, Any]]:
    """Order complete executor results using the canonical conditional descriptors."""
    expected = expected_blog_gate_inventory(
        visible_faq=visible_faq,
        connector_required=connector_required,
    )
    by_name: dict[str, Mapping[str, Any]] = {}
    for row in gates:
        name = row.get("name") if isinstance(row, Mapping) else None
        if not isinstance(name, str) or not name or name in by_name:
            raise ValueError("blog gate results contain an invalid or duplicate name")
        by_name[name] = row
    if set(by_name) != set(expected):
        raise ValueError("blog gate results do not match the expected conditional inventory")
    return [by_name[name] for name in expected]


def _gate_descriptor_enabled(
    descriptor: BlogGateDescriptor,
    *,
    visible_faq: bool,
    connector_required: bool,
) -> bool:
    if descriptor.condition == "always":
        return True
    if descriptor.condition == "visible_faq":
        return visible_faq
    if descriptor.condition == "connector_required":
        return connector_required
    raise ValueError(f"unsupported blog gate condition: {descriptor.condition}")


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
            allow_nan=False,
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
    data = candidate.read_bytes()
    return canonical_artifact_identity(
        candidate,
        sha256=hashlib.sha256(data).hexdigest(),
        workspace_root=root,
    )


def canonical_snapshot_artifact(
    snapshot: ArtifactSnapshot,
    *,
    workspace_root: str | Path,
) -> dict[str, str]:
    """Create a BOM row from the exact immutable bytes that were parsed."""
    return canonical_artifact_identity(
        snapshot.path,
        sha256=snapshot.sha256,
        workspace_root=workspace_root,
    )


def canonical_artifact_identity(
    path: str | Path,
    *,
    sha256: str,
    workspace_root: str | Path,
) -> dict[str, str]:
    """Bind a previously observed digest to one canonical workspace path."""
    root = Path(workspace_root).resolve()
    candidate = Path(path).resolve()
    if not candidate.is_file() or not _within(candidate, root):
        raise ValueError(f"artifact is unavailable or outside workspace: {path}")
    relative = candidate.relative_to(root).as_posix()
    resolve_artifact(relative, workspace_root=root)
    return {
        "path": relative,
        "sha256": validate_sha256(sha256, field="artifact.sha256"),
    }


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
    destination = Path(path)
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
