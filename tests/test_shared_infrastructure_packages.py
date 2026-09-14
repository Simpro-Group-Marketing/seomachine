from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from data_sources.modules.bounded_io import (
    canonical_json_bytes,
    canonical_json_sha256,
    decode_utf8,
    file_identity,
    parse_json_object,
    read_bounded,
    stream_sha256,
)
from data_sources.modules.connector_snapshot import (
    CACHEABLE_CONNECTOR_OPERATIONS,
    ConnectorSnapshot,
)
from data_sources.modules.resource_metrics import process_peak_rss_bytes


def test_bounded_io_reads_hashes_and_parses_strict_json(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    path.write_bytes(b'{"name":"value"}\n')

    data = read_bounded(path, max_bytes=1024, field="fixture")

    assert decode_utf8(data, field="fixture") == '{"name":"value"}\n'
    assert parse_json_object(data, field="fixture") == {"name": "value"}
    assert stream_sha256(path) == hashlib.sha256(data).hexdigest()
    assert file_identity(path)[2] == len(data)


def test_bounded_io_rejects_duplicate_keys_and_non_finite_numbers() -> None:
    with pytest.raises(ValueError, match="duplicate key: name"):
        parse_json_object(b'{"name":1,"name":2}', field="fixture")
    with pytest.raises(ValueError, match="non-finite number"):
        parse_json_object(b'{"value":NaN}', field="fixture")


def test_canonical_json_contract_matches_durable_format() -> None:
    payload = {"z": 1, "a": [True, None]}
    encoded = canonical_json_bytes(payload)

    assert encoded == b'{\n  "a": [\n    true,\n    null\n  ],\n  "z": 1\n}\n'
    assert canonical_json_sha256(payload) == hashlib.sha256(encoded).hexdigest()


def test_connector_snapshot_caches_successes_but_not_exceptions() -> None:
    calls = 0

    def load() -> dict[str, list[str]]:
        nonlocal calls
        calls += 1
        return {"rows": ["one"]}

    snapshot = ConnectorSnapshot()
    first = snapshot.result("search", {"query": "same"}, load)
    second = snapshot.result("search", {"query": "same"}, load)

    assert first is second
    assert calls == 1
    with pytest.raises(TypeError):
        first["rows"] = ()

    attempts = 0

    def fail() -> object:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("transient")

    with pytest.raises(RuntimeError, match="transient"):
        snapshot.result("read", {"resource_id": "one"}, fail)
    with pytest.raises(RuntimeError, match="transient"):
        snapshot.result("read", {"resource_id": "one"}, fail)
    assert attempts == 2


def test_connector_snapshot_rejects_mutation_capable_operations() -> None:
    assert "search" in CACHEABLE_CONNECTOR_OPERATIONS
    with pytest.raises(ValueError, match="not cacheable"):
        ConnectorSnapshot().result("delete", None, lambda: None)


def test_process_peak_rss_is_optional_positive_measurement() -> None:
    value = process_peak_rss_bytes()
    assert value is None or (isinstance(value, int) and value > 0)


def test_existing_bounded_io_facades_match_shared_implementation(tmp_path: Path) -> None:
    from data_sources.modules import blog_assembly_contract
    from data_sources.modules.readiness import artifact_io

    path = tmp_path / "payload.json"
    payload = {"value": 1}
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert artifact_io.stream_sha256(path) == stream_sha256(path)
    assert blog_assembly_contract.canonical_json_bytes(payload) == canonical_json_bytes(
        payload
    )
