"""Artifacts responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _read_artifact_text(proof: ProofEntry, base_path: Path) -> Optional[str]:
    resolved = _resolve_local_artifact(
        proof.artifact,
        base_path,
        LOCAL_ARTIFACT_EXTENSION_RE,
    )
    if resolved is None:
        return None
    return resolved.read_text(encoding="utf-8")

def _resolve_local_artifact(
    reference: str,
    base_path: Path,
    extension_pattern: re.Pattern[str],
) -> Optional[Path]:
    if not reference or not extension_pattern.search(Path(reference).name):
        return None
    artifact_path = Path(reference)
    candidates = [artifact_path] if artifact_path.is_absolute() else [
        base_path / artifact_path,
        base_path.parent / artifact_path,
        Path.cwd() / artifact_path,
    ]
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_file():
            return resolved
    return None

def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _read_json_object(path: Path) -> Optional[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None

def _is_strict_classification_payload(payload: dict) -> bool:
    publisher = payload.get("publisher")
    registry = payload.get("registry")
    emitter = payload.get("emitter")
    return all((
        set(payload) == {
        "schema",
        "source_url",
        "source_class",
        "classified_at",
        "publisher",
        "registry",
        "emitter",
        "execution_attestation",
        },
        payload.get("schema") == SOURCE_CLASSIFICATION_SCHEMA,
        payload.get("source_class") in SOURCE_CLASSES,
        _is_nonempty_string(payload.get("source_url")),
        _is_valid_utc_timestamp(payload.get("classified_at")),
        _is_strict_publisher(publisher),
        _is_strict_registry(registry),
        _is_strict_emitter(emitter, SOURCE_CLASSIFICATION_EMITTER),
    ))


def _is_strict_publisher(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"hostname", "relationship"}
        and _is_nonempty_string(value.get("hostname"))
        and value.get("relationship") in PUBLISHER_RELATIONSHIPS
    )


def _is_strict_registry(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {
        "authority_mode", "record_id", "revision", "decision_path", "decision_sha256"
        }
        and value.get("authority_mode") == "repository_decision"
        and all(_is_nonempty_string(value.get(key)) for key in (
            "record_id", "revision", "decision_path",
        ))
        and _is_sha256(value.get("decision_sha256"))
    )


def _is_strict_emitter(value: object, expected_name: str) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"name", "version"}
        and value.get("name") == expected_name
        and _is_nonempty_string(value.get("version"))
    )


def _is_strict_capture_payload(payload: dict) -> bool:
    artifact = payload.get("artifact")
    extraction = payload.get("extraction")
    emitter = payload.get("emitter")
    return all((
        set(payload) == {
        "schema",
        "source_url",
        "retrieved_at",
        "source_content_sha256",
        "artifact",
        "extraction",
        "emitter",
        "execution_attestation",
        },
        payload.get("schema") == SOURCE_CAPTURE_SCHEMA,
        _is_nonempty_string(payload.get("source_url")),
        _is_valid_utc_timestamp(payload.get("retrieved_at")),
        _is_sha256(payload.get("source_content_sha256")),
        _is_strict_artifact(artifact),
        _is_strict_extraction(extraction),
        _is_strict_emitter(emitter, SOURCE_CAPTURE_EMITTER),
    ))


def _is_strict_artifact(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"path", "sha256"}
        and _is_nonempty_string(value.get("path"))
        and _is_sha256(value.get("sha256"))
    )


def _is_strict_extraction(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {
        "method",
        "tool_name",
        "tool_version",
        "input_sha256",
        "output_sha256",
        }
        and value.get("method") in {"html_visible_text", "pdf_text"}
        and value.get("tool_name") == SOURCE_CAPTURE_EMITTER
        and _is_nonempty_string(value.get("tool_version"))
        and _is_sha256(value.get("input_sha256"))
        and _is_sha256(value.get("output_sha256"))
    )

def _is_valid_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not RFC3339_UTC_RE.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo == timezone.utc and parsed <= datetime.now(timezone.utc)

def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))

def _required_emitter_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()

def _utc_timestamp_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

def _attestation_workspace_root(base_path: Path) -> Path:
    resolved = base_path.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    return resolved


__all__ = [
    "_read_artifact_text", "_resolve_local_artifact", "_sha256_file",
    "_read_json_object", "_is_strict_classification_payload", "_is_strict_capture_payload",
    "_is_valid_utc_timestamp", "_is_nonempty_string", "_is_sha256",
    "_required_emitter_text", "_utc_timestamp_now", "_attestation_workspace_root",
]
