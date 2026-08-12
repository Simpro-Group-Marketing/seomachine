"""Authenticate locally emitted execution artifacts with a workspace trust key.

The attestation is an integrity boundary for persisted machine receipts. It is
not a claim that a remote publisher signed the underlying data. An environment
key supports managed runners; otherwise emission creates one ignored local key
for the workspace. Validation never creates trust material.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ATTESTATION_SCHEMA = "simpro-execution-attestation/v1"
ATTESTATION_ALGORITHM = "hmac-sha256"
ATTESTATION_FIELD = "execution_attestation"
ATTESTATION_KEY_ENV = "SEOMACHINE_ARTIFACT_ATTESTATION_KEY"
LOCAL_KEY_RELATIVE_PATH = Path(".cache") / "seomachine-execution-attestation.key"
ATTESTATION_FIELDS = frozenset(
    {"schema", "purpose", "algorithm", "key_id", "signature"}
)


class ExecutionAttestationError(ValueError):
    """Execution artifact signing could not be completed safely."""


def attest_mapping(
    payload: Mapping[str, Any],
    *,
    purpose: str,
    workspace_root: str | Path | None = None,
    attestation_field: str = ATTESTATION_FIELD,
) -> dict[str, Any]:
    """Return a signed copy of one machine-emitted mapping."""
    if not isinstance(payload, Mapping):
        raise ExecutionAttestationError("attested payload must be a mapping")
    normalized_purpose = _required_text(purpose, "purpose")
    normalized_field = _required_text(attestation_field, "attestation_field")
    if normalized_field in payload:
        raise ExecutionAttestationError(
            f"payload already contains {normalized_field}"
        )

    root = _workspace_root(workspace_root)
    key = _load_key(root, create=True)
    result = dict(payload)
    try:
        signature = _signature(
            result,
            purpose=normalized_purpose,
            key=key,
            attestation_field=normalized_field,
        )
    except (TypeError, ValueError) as error:
        raise ExecutionAttestationError(
            f"attested payload is not canonical JSON: {error}"
        ) from error
    result[normalized_field] = {
        "schema": ATTESTATION_SCHEMA,
        "purpose": normalized_purpose,
        "algorithm": ATTESTATION_ALGORITHM,
        "key_id": _key_id(key),
        "signature": signature,
    }
    return result


def verify_mapping_attestation(
    payload: Mapping[str, Any],
    *,
    purpose: str,
    workspace_root: str | Path | None = None,
    attestation_field: str = ATTESTATION_FIELD,
    excluded_fields: tuple[str, ...] = (),
) -> bool:
    """Verify an attestation without ever creating a key as a side effect."""
    if not isinstance(payload, Mapping):
        return False
    try:
        normalized_purpose = _required_text(purpose, "purpose")
        normalized_field = _required_text(attestation_field, "attestation_field")
        root = _workspace_root(workspace_root)
        key = _load_key(root, create=False)
    except ExecutionAttestationError:
        return False

    attestation = payload.get(normalized_field)
    if not isinstance(attestation, Mapping) or set(attestation) != ATTESTATION_FIELDS:
        return False
    if (
        attestation.get("schema") != ATTESTATION_SCHEMA
        or attestation.get("purpose") != normalized_purpose
        or attestation.get("algorithm") != ATTESTATION_ALGORITHM
        or attestation.get("key_id") != _key_id(key)
    ):
        return False
    supplied_signature = attestation.get("signature")
    if not isinstance(supplied_signature, str) or len(supplied_signature) != 64:
        return False

    unsigned = {
        field: value
        for field, value in payload.items()
        if field not in excluded_fields
    }
    try:
        expected = _signature(
            unsigned,
            purpose=normalized_purpose,
            key=key,
            attestation_field=normalized_field,
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(supplied_signature, expected)


def _signature(
    payload: Mapping[str, Any],
    *,
    purpose: str,
    key: bytes,
    attestation_field: str,
) -> str:
    unsigned = {
        field: value
        for field, value in payload.items()
        if field != attestation_field
    }
    canonical = json.dumps(
        unsigned,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    message = purpose.encode("utf-8") + b"\0" + canonical
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _workspace_root(workspace_root: str | Path | None) -> Path:
    if workspace_root is None:
        package_root = Path(__file__).resolve().parents[2]
        root = package_root if (package_root / ".git").exists() else Path.cwd()
    else:
        root = Path(workspace_root)
    try:
        resolved = root.resolve(strict=True)
    except OSError as error:
        raise ExecutionAttestationError(
            f"workspace root is unavailable: {error}"
        ) from error
    if not resolved.is_dir():
        raise ExecutionAttestationError("workspace root must be a directory")
    return resolved


def _load_key(workspace_root: Path, *, create: bool) -> bytes:
    environment_value = os.environ.get(ATTESTATION_KEY_ENV)
    if environment_value is not None:
        encoded = environment_value.encode("utf-8")
        if len(encoded) < 32:
            raise ExecutionAttestationError(
                f"{ATTESTATION_KEY_ENV} must contain at least 32 UTF-8 bytes"
            )
        return hashlib.sha256(encoded).digest()

    key_path = workspace_root / LOCAL_KEY_RELATIVE_PATH
    if create and not key_path.is_file():
        _create_local_key(key_path)
    try:
        key = key_path.read_bytes()
    except OSError as error:
        raise ExecutionAttestationError(
            "execution-attestation key is unavailable; emit the artifact in "
            "this workspace or configure the managed runner key"
        ) from error
    if len(key) < 32:
        raise ExecutionAttestationError("execution-attestation key is invalid")
    return key


def _create_local_key(key_path: Path) -> None:
    key_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=key_path.parent,
            prefix=f".{key_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(secrets.token_bytes(48))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, key_path)
        except FileExistsError:
            pass
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
    except OSError as error:
        raise ExecutionAttestationError(
            f"could not create the workspace attestation key: {error}"
        ) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _key_id(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionAttestationError(f"{field} must be a non-empty string")
    return value.strip()
