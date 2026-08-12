from __future__ import annotations

from copy import deepcopy

from data_sources.modules.execution_attestation import (
    attest_mapping,
    verify_mapping_attestation,
)


PURPOSE = "test-artifact/v1"


def test_attestation_binds_payload_and_purpose(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "SEOMACHINE_ARTIFACT_ATTESTATION_KEY",
        "test-only-execution-attestation-key-material",
    )
    payload = {"schema": "test/v1", "value": 7}

    attested = attest_mapping(payload, purpose=PURPOSE, workspace_root=tmp_path)

    assert verify_mapping_attestation(
        attested,
        purpose=PURPOSE,
        workspace_root=tmp_path,
    )
    assert not verify_mapping_attestation(
        attested,
        purpose="different-purpose/v1",
        workspace_root=tmp_path,
    )
    tampered = deepcopy(attested)
    tampered["value"] = 8
    assert not verify_mapping_attestation(
        tampered,
        purpose=PURPOSE,
        workspace_root=tmp_path,
    )


def test_local_key_is_created_only_by_emission(monkeypatch, tmp_path):
    monkeypatch.delenv("SEOMACHINE_ARTIFACT_ATTESTATION_KEY", raising=False)
    unsigned = {"schema": "test/v1", "value": 7}

    assert not verify_mapping_attestation(
        unsigned,
        purpose=PURPOSE,
        workspace_root=tmp_path,
    )

    attested = attest_mapping(unsigned, purpose=PURPOSE, workspace_root=tmp_path)

    assert verify_mapping_attestation(
        attested,
        purpose=PURPOSE,
        workspace_root=tmp_path,
    )
    key_path = tmp_path / ".cache" / "seomachine-execution-attestation.key"
    assert key_path.is_file()
    assert len(key_path.read_bytes()) >= 32


def test_caller_recomputed_plain_hash_cannot_replace_hmac(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "SEOMACHINE_ARTIFACT_ATTESTATION_KEY",
        "test-only-execution-attestation-key-material",
    )
    attested = attest_mapping(
        {"schema": "test/v1", "value": 7},
        purpose=PURPOSE,
        workspace_root=tmp_path,
    )
    forged = deepcopy(attested)
    forged["value"] = 9
    forged["execution_attestation"]["signature"] = "0" * 64

    assert not verify_mapping_attestation(
        forged,
        purpose=PURPOSE,
        workspace_root=tmp_path,
    )
