import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import Request

import pytest

from tools import humanizer_upstream


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "humanizer_upstream.py"
COMMIT = "e2e92e7b4b8229253ed5c8e81dc65463fdeddda5"
NEXT_COMMIT = "f" * 40
SKILL_TEXT = """---
name: humanizer
license: MIT
metadata:
  version: "2.11.2"
---

# Humanizer

### 1. Inflated claims

Guidance.

### 2. Vague sources

Guidance.
"""
LICENSE_TEXT = """MIT License

Copyright (c) 2025 Example

Permission is hereby granted, free of charge, to any person obtaining a copy.
"""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_repository(root: Path, *, reviewed_commit: str = COMMIT) -> None:
    vendor = root / "vendor" / "blader-humanizer"
    vendor.mkdir(parents=True)
    skill_bytes = SKILL_TEXT.encode("utf-8")
    license_bytes = LICENSE_TEXT.encode("utf-8")
    (vendor / "SKILL.md").write_bytes(skill_bytes)
    (vendor / "LICENSE").write_bytes(license_bytes)
    manifest = {
        "schema": "simpro-humanizer-upstream/v1",
        "repository": "https://github.com/blader/humanizer",
        "source_ref": "refs/heads/main",
        "resolved_commit": COMMIT,
        "declared_version": "2.11.2",
        "commit_verification": {"verified": None, "reason": "not_checked"},
        "license_spdx": "MIT",
        "network_at_runtime": False,
        "executed_upstream_files": [],
        "files": {
            "SKILL.md": {"sha256": _sha256(skill_bytes), "bytes": len(skill_bytes)},
            "LICENSE": {"sha256": _sha256(license_bytes), "bytes": len(license_bytes)},
        },
        "patterns": [
            {"id": 1, "heading": "Inflated claims"},
            {"id": 2, "heading": "Vague sources"},
        ],
    }
    (vendor / "UPSTREAM.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    config = root / "config"
    config.mkdir()
    policy = {
        "schema": "simpro-humanizer-policy/v1",
        "reviewed_upstream_commit": reviewed_commit,
        "precedence": ["vault", "proof", "factual_accuracy", "native_edit", "simpro_style"],
        "protected_spans": ["exact_quotation", "connector_bound_claim"],
        "runtime_network": False,
        "patterns": [
            {
                "upstream_id": 1,
                "upstream_heading": "Inflated claims",
                "stable_rule_id": "humanizer.inflated_claims",
                "disposition": "advisory",
                "channels": ["blog"],
                "exceptions": [],
                "rationale": "Requires editorial context.",
            },
            {
                "upstream_id": 2,
                "upstream_heading": "Vague sources",
                "stable_rule_id": "humanizer.vague_sources",
                "disposition": "proof_routed",
                "channels": ["blog"],
                "exceptions": [],
                "rationale": "Existing proof guards own attribution.",
            },
        ],
    }
    (config / "humanizer-policy.json").write_text(
        json.dumps(policy, indent=2) + "\n",
        encoding="utf-8",
    )


def _run_cli(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _candidate_fetcher(url: str) -> bytes:
    if url.endswith("/SKILL.md"):
        return SKILL_TEXT.replace('2.11.2', '2.11.3').encode("utf-8")
    if url.endswith("/LICENSE"):
        return LICENSE_TEXT.encode("utf-8")
    raise AssertionError(f"unexpected URL: {url}")


def test_verify_accepts_hash_bound_snapshot_and_complete_policy(tmp_path: Path):
    """Removing snapshot, hash, or policy validation must make this fail."""
    _write_repository(tmp_path)

    result = _run_cli(tmp_path, "verify")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "status": "valid",
        "resolved_commit": COMMIT,
        "declared_version": "2.11.2",
        "pattern_count": 2,
        "reviewed": True,
    }


def test_verify_rejects_unreviewed_upstream_commit(tmp_path: Path):
    """Ignoring the activation boundary must make this fail."""
    _write_repository(tmp_path, reviewed_commit="0" * 40)

    result = _run_cli(tmp_path, "verify")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "invalid"
    assert payload["error"]["code"] == "unreviewed_upstream_commit"


def test_verify_rejects_missing_pattern_classification(tmp_path: Path):
    """Accepting an unmapped upstream pattern must make this fail."""
    _write_repository(tmp_path)
    policy_path = tmp_path / "config" / "humanizer-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["patterns"].pop()
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    result = _run_cli(tmp_path, "verify")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "pattern_policy_incomplete"


def test_verify_rejects_stale_upstream_heading_classification(tmp_path: Path):
    """A renamed upstream pattern requires an explicit local policy review."""
    _write_repository(tmp_path)
    policy_path = tmp_path / "config" / "humanizer-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["patterns"][0]["upstream_heading"] = "Previous heading"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    result = _run_cli(tmp_path, "verify")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "pattern_policy_heading_mismatch"


def test_verify_rejects_blocking_policy_without_explicit_enforcement(tmp_path: Path):
    """Inferring blocker behavior from upstream prose must make this fail."""
    _write_repository(tmp_path)
    policy_path = tmp_path / "config" / "humanizer-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["runtime_network"] = False
    policy["patterns"][0]["disposition"] = "blocking"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    result = _run_cli(tmp_path, "verify")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "pattern_enforcement_invalid"


def test_verify_rejects_runtime_network_in_policy(tmp_path: Path):
    """Permitting runtime network access must make this fail."""
    _write_repository(tmp_path)
    policy_path = tmp_path / "config" / "humanizer-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["runtime_network"] = True
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    result = _run_cli(tmp_path, "verify")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "runtime_network_invalid"


def test_stage_resolves_commit_and_writes_only_validated_allowlisted_snapshot(tmp_path: Path):
    """Fetching moving refs or extra upstream files must make this fail."""
    output = tmp_path / "candidate"

    result = humanizer_upstream.stage_candidate(
        ref="main",
        output=output,
        resolver=lambda ref: NEXT_COMMIT,
        fetcher=_candidate_fetcher,
        verification_loader=lambda commit: {"verified": True, "reason": "valid"},
    )

    assert result["status"] == "staged"
    assert result["resolved_commit"] == NEXT_COMMIT
    assert result["declared_version"] == "2.11.3"
    assert sorted(path.name for path in output.iterdir()) == ["LICENSE", "SKILL.md", "UPSTREAM.json"]
    manifest = json.loads((output / "UPSTREAM.json").read_text(encoding="utf-8"))
    assert manifest["resolved_commit"] == NEXT_COMMIT
    assert manifest["commit_verification"] == {"verified": True, "reason": "valid"}
    assert manifest["patterns"] == [
        {"id": 1, "heading": "Inflated claims"},
        {"id": 2, "heading": "Vague sources"},
    ]


def test_stage_rejects_non_mit_candidate_before_writing(tmp_path: Path):
    """Removing license continuity validation must make this fail."""
    output = tmp_path / "candidate"

    def fetcher(url: str) -> bytes:
        if url.endswith("/SKILL.md"):
            return SKILL_TEXT.encode("utf-8")
        return b"Different license\n"

    with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
        humanizer_upstream.stage_candidate(
            ref=NEXT_COMMIT,
            output=output,
            resolver=lambda ref: NEXT_COMMIT,
            fetcher=fetcher,
            verification_loader=lambda commit: {"verified": None, "reason": "not_checked"},
        )

    assert error.value.code == "license_invalid"
    assert not output.exists()


def test_stage_rejects_capability_expanding_skill_metadata(tmp_path: Path):
    """Allowing upstream executable capabilities into the snapshot must make this fail."""
    output = tmp_path / "candidate"

    def fetcher(url: str) -> bytes:
        if url.endswith("/SKILL.md"):
            return SKILL_TEXT.replace(
                "license: MIT\n",
                "license: MIT\nallowed-tools: Bash\n",
            ).encode("utf-8")
        return LICENSE_TEXT.encode("utf-8")

    with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
        humanizer_upstream.stage_candidate(
            ref="main",
            output=output,
            resolver=lambda ref: NEXT_COMMIT,
            fetcher=fetcher,
            verification_loader=lambda commit: {"verified": True, "reason": "valid"},
        )

    assert error.value.code == "skill_capability_expansion"
    assert not output.exists()


def test_fetch_rejects_non_allowlisted_host_before_transport_runs():
    """Allowing arbitrary download hosts must make this fail."""
    transport_used = False

    def transport(url: str) -> bytes:
        nonlocal transport_used
        transport_used = True
        return b"payload"

    with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
        humanizer_upstream.fetch_allowed_url("https://example.com/SKILL.md", transport=transport)

    assert error.value.code == "download_host_invalid"
    assert transport_used is False


def test_fetch_rejects_query_or_fragment_variants_of_allowlisted_paths():
    """The network allowlist must match exact GitHub resource paths."""
    base = "https://raw.githubusercontent.com/blader/humanizer/" + NEXT_COMMIT

    for suffix in ("/SKILL.md?download=1", "/LICENSE#text"):
        with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
            humanizer_upstream.fetch_allowed_url(base + suffix, transport=lambda url: b"")
        assert error.value.code == "download_url_invalid"


def test_redirect_handler_rejects_nonallowlisted_redirect_before_following():
    """Redirects must be validated as strictly as initial download URLs."""
    handler = humanizer_upstream._AllowlistedRedirectHandler()
    request = Request(
        "https://raw.githubusercontent.com/blader/humanizer/" + NEXT_COMMIT + "/SKILL.md"
    )

    with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://example.com/SKILL.md",
        )

    assert error.value.code == "download_host_invalid"


def test_adopt_rejects_expected_current_race_without_changing_vendor(tmp_path: Path):
    """Dropping compare-and-swap protection must make this fail."""
    _write_repository(tmp_path)
    candidate = tmp_path / "candidate"
    humanizer_upstream.stage_candidate(
        ref="main",
        output=candidate,
        resolver=lambda ref: NEXT_COMMIT,
        fetcher=_candidate_fetcher,
        verification_loader=lambda commit: {"verified": True, "reason": "valid"},
    )
    original = (tmp_path / "vendor" / "blader-humanizer" / "UPSTREAM.json").read_bytes()

    with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
        humanizer_upstream.adopt_candidate(
            repo_root=tmp_path,
            candidate=candidate,
            expected_current="0" * 40,
        )

    assert error.value.code == "expected_current_mismatch"
    assert (tmp_path / "vendor" / "blader-humanizer" / "UPSTREAM.json").read_bytes() == original


def test_adopt_rejects_unexpected_candidate_files(tmp_path: Path):
    """Adoption must not copy files outside the exact snapshot allowlist."""
    _write_repository(tmp_path)
    candidate = tmp_path / "candidate"
    humanizer_upstream.stage_candidate(
        ref="main",
        output=candidate,
        resolver=lambda ref: NEXT_COMMIT,
        fetcher=_candidate_fetcher,
        verification_loader=lambda commit: {"verified": True, "reason": "valid"},
    )
    (candidate / "unexpected.txt").write_text("do not adopt", encoding="utf-8")

    with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
        humanizer_upstream.adopt_candidate(
            repo_root=tmp_path,
            candidate=candidate,
            expected_current=COMMIT,
        )

    assert error.value.code == "candidate_files_invalid"


def test_adopt_rejects_unexpected_candidate_directories(tmp_path: Path):
    """Nested candidate paths must not bypass the exact file allowlist."""
    _write_repository(tmp_path)
    candidate = tmp_path / "candidate"
    humanizer_upstream.stage_candidate(
        ref="main",
        output=candidate,
        resolver=lambda ref: NEXT_COMMIT,
        fetcher=_candidate_fetcher,
        verification_loader=lambda commit: {"verified": True, "reason": "valid"},
    )
    (candidate / "nested").mkdir()

    with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
        humanizer_upstream.adopt_candidate(
            repo_root=tmp_path,
            candidate=candidate,
            expected_current=COMMIT,
        )

    assert error.value.code == "candidate_files_invalid"


def test_adopt_updates_vendor_only_and_leaves_policy_unreviewed(tmp_path: Path):
    """Updating local policy automatically must make this fail."""
    _write_repository(tmp_path)
    candidate = tmp_path / "candidate"
    humanizer_upstream.stage_candidate(
        ref="main",
        output=candidate,
        resolver=lambda ref: NEXT_COMMIT,
        fetcher=_candidate_fetcher,
        verification_loader=lambda commit: {"verified": True, "reason": "valid"},
    )
    policy_before = (tmp_path / "config" / "humanizer-policy.json").read_bytes()

    result = humanizer_upstream.adopt_candidate(
        repo_root=tmp_path,
        candidate=candidate,
        expected_current=COMMIT,
    )

    assert result == {
        "status": "adopted",
        "previous_commit": COMMIT,
        "resolved_commit": NEXT_COMMIT,
        "review_required": True,
    }
    assert (tmp_path / "config" / "humanizer-policy.json").read_bytes() == policy_before
    with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
        humanizer_upstream.verify_repository(tmp_path)
    assert error.value.code == "unreviewed_upstream_commit"


def test_adopt_rejects_license_text_change_even_when_candidate_says_mit(tmp_path: Path):
    """Treating an upstream license-text change as routine must make this fail."""
    _write_repository(tmp_path)
    candidate = tmp_path / "candidate"

    def changed_license_fetcher(url: str) -> bytes:
        if url.endswith("/SKILL.md"):
            return SKILL_TEXT.replace("2.11.2", "2.11.3").encode("utf-8")
        return LICENSE_TEXT.replace("2025 Example", "2026 Different Owner").encode("utf-8")

    humanizer_upstream.stage_candidate(
        ref="main",
        output=candidate,
        resolver=lambda ref: NEXT_COMMIT,
        fetcher=changed_license_fetcher,
        verification_loader=lambda commit: {"verified": True, "reason": "valid"},
    )
    original = (tmp_path / "vendor" / "blader-humanizer" / "LICENSE").read_bytes()

    with pytest.raises(humanizer_upstream.HumanizerUpstreamError) as error:
        humanizer_upstream.adopt_candidate(
            repo_root=tmp_path,
            candidate=candidate,
            expected_current=COMMIT,
        )

    assert error.value.code == "license_changed"
    assert (tmp_path / "vendor" / "blader-humanizer" / "LICENSE").read_bytes() == original


def test_check_upstream_reports_pattern_changes_without_writing(tmp_path: Path):
    """A check that mutates the vendored snapshot must make this fail."""
    _write_repository(tmp_path)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    result = humanizer_upstream.check_upstream(
        repo_root=tmp_path,
        ref="main",
        resolver=lambda ref: NEXT_COMMIT,
        fetcher=_candidate_fetcher,
    )

    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert result["status"] == "update_available"
    assert result["current_commit"] == COMMIT
    assert result["latest_commit"] == NEXT_COMMIT
    assert result["declared_version"] == "2.11.3"
    assert result["current_declared_version"] == "2.11.2"
    assert result["latest_declared_version"] == "2.11.3"
    assert result["current_files"]["SKILL.md"]["sha256"] == _sha256(SKILL_TEXT.encode("utf-8"))
    assert result["latest_files"]["SKILL.md"]["sha256"] == _sha256(
        SKILL_TEXT.replace("2.11.2", "2.11.3").encode("utf-8")
    )
    assert result["current_commit_verification"] == {"verified": None, "reason": "not_checked"}
    assert result["pattern_changes"] == {"added": [], "removed": [], "renamed": []}
    assert after == before


def test_vendored_snapshot_forces_lf_for_cross_platform_hash_stability():
    """Removing the LF attribute must make snapshot verification platform-dependent."""
    result = subprocess.run(
        ["git", "check-attr", "eol", "--", "vendor/blader-humanizer/SKILL.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("eol: lf")

    policy_result = subprocess.run(
        ["git", "check-attr", "eol", "--", "config/humanizer-policy.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert policy_result.returncode == 0, policy_result.stderr
    assert policy_result.stdout.strip().endswith("eol: lf")
