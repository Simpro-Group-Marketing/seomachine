#!/usr/bin/env python3
"""Manage the reviewed, vendored blader/humanizer snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


MANIFEST_SCHEMA = "simpro-humanizer-upstream/v1"
POLICY_SCHEMA = "simpro-humanizer-policy/v1"
REPOSITORY = "https://github.com/blader/humanizer"
SOURCE_REF = "refs/heads/main"
VENDOR_RELATIVE = Path("vendor/blader-humanizer")
POLICY_RELATIVE = Path("config/humanizer-policy.json")
ALLOWED_VENDOR_FILES = ("SKILL.md", "LICENSE")
ALLOWED_DISPOSITIONS = {"blocking", "advisory", "proof_routed", "overridden", "excluded"}
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
PATTERN_RE = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$", re.MULTILINE)
MAX_DOWNLOAD_BYTES = 512_000
RAW_HOST = "raw.githubusercontent.com"
API_HOST = "api.github.com"

Resolver = Callable[[str], str]
Fetcher = Callable[[str], bytes]
VerificationLoader = Callable[[str], Mapping[str, object]]


class HumanizerUpstreamError(ValueError):
    """A machine-readable upstream snapshot validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise HumanizerUpstreamError(code, message)


def _read_json(path: Path, *, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise HumanizerUpstreamError(code, f"Cannot read {path}: {error}") from error
    _require(isinstance(value, dict), code, f"{path} must contain a JSON object")
    return value


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _frontmatter_value(skill_text: str, field: str) -> str:
    frontmatter = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", skill_text, re.DOTALL)
    _require(frontmatter is not None, "skill_metadata_invalid", "SKILL.md requires YAML frontmatter")
    if field == "version":
        match = re.search(r'^\s{2}version:\s*["\']?([^"\'\s]+)', frontmatter.group(1), re.MULTILINE)
    else:
        match = re.search(rf"^{re.escape(field)}:\s*[\"']?([^\"'\n]+)", frontmatter.group(1), re.MULTILINE)
    _require(match is not None, "skill_metadata_invalid", f"SKILL.md requires {field} metadata")
    return match.group(1).strip()


def _validate_no_capability_metadata(skill_text: str) -> None:
    frontmatter = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", skill_text, re.DOTALL)
    _require(frontmatter is not None, "skill_metadata_invalid", "SKILL.md requires YAML frontmatter")
    capability = re.search(
        r"^(?:allowed-tools|tools|agent|context|hooks|mcp-servers|commands):",
        frontmatter.group(1),
        re.MULTILINE | re.IGNORECASE,
    )
    _require(capability is None, "skill_capability_expansion", "Upstream skill metadata may not add executable capabilities")


def _patterns(skill_text: str) -> list[dict[str, object]]:
    patterns = [
        {"id": int(match.group(1)), "heading": match.group(2).strip()}
        for match in PATTERN_RE.finditer(skill_text)
    ]
    ids = [int(item["id"]) for item in patterns]
    _require(bool(ids), "pattern_inventory_invalid", "SKILL.md contains no numbered Humanizer patterns")
    _require(len(ids) == len(set(ids)), "pattern_inventory_invalid", "Humanizer pattern IDs must be unique")
    _require(ids == list(range(1, len(ids) + 1)), "pattern_inventory_invalid", "Humanizer pattern IDs must be consecutive from 1")
    return patterns


def _validate_file_entry(manifest: Mapping[str, Any], name: str, content: bytes) -> None:
    files = manifest.get("files")
    _require(isinstance(files, dict), "manifest_files_invalid", "UPSTREAM.json requires a files object")
    entry = files.get(name)
    _require(isinstance(entry, dict), "manifest_files_invalid", f"UPSTREAM.json requires files.{name}")
    expected_hash = entry.get("sha256")
    expected_bytes = entry.get("bytes")
    _require(isinstance(expected_hash, str) and SHA256_RE.fullmatch(expected_hash) is not None, "manifest_files_invalid", f"files.{name}.sha256 is invalid")
    _require(isinstance(expected_bytes, int) and expected_bytes >= 0, "manifest_files_invalid", f"files.{name}.bytes is invalid")
    _require(_sha256(content) == expected_hash, "snapshot_hash_mismatch", f"{name} does not match its recorded SHA-256")
    _require(len(content) == expected_bytes, "snapshot_size_mismatch", f"{name} does not match its recorded byte size")


def _validate_manifest(manifest: Mapping[str, Any]) -> None:
    _require(manifest.get("schema") == MANIFEST_SCHEMA, "manifest_schema_invalid", f"Manifest schema must be {MANIFEST_SCHEMA}")
    _require(manifest.get("repository") == REPOSITORY, "manifest_repository_invalid", f"Repository must be {REPOSITORY}")
    commit = manifest.get("resolved_commit")
    _require(isinstance(commit, str) and FULL_SHA_RE.fullmatch(commit) is not None, "manifest_commit_invalid", "resolved_commit must be a lowercase 40-character SHA")
    source_ref = manifest.get("source_ref")
    _require(source_ref == SOURCE_REF or source_ref == commit or (isinstance(source_ref, str) and source_ref.startswith("refs/tags/v")), "manifest_ref_invalid", "source_ref must identify main, a tag, or the resolved commit")
    version = manifest.get("declared_version")
    _require(isinstance(version, str) and SEMVER_RE.fullmatch(version) is not None, "manifest_version_invalid", "declared_version must be semantic version text")
    _require(manifest.get("license_spdx") == "MIT", "license_invalid", "Vendored Humanizer must remain MIT licensed")
    _require(manifest.get("network_at_runtime") is False, "runtime_network_invalid", "network_at_runtime must be false")
    _require(manifest.get("executed_upstream_files") == [], "upstream_execution_invalid", "No upstream files may be executable")
    files = manifest.get("files")
    _require(isinstance(files, dict) and set(files) == set(ALLOWED_VENDOR_FILES), "manifest_files_invalid", "Manifest file allowlist must contain only SKILL.md and LICENSE")
    verification = manifest.get("commit_verification")
    _require(isinstance(verification, dict), "commit_verification_invalid", "commit_verification must be an object")
    _require(verification.get("verified") in {True, False, None}, "commit_verification_invalid", "commit_verification.verified must be true, false, or null")
    _require(isinstance(verification.get("reason"), str), "commit_verification_invalid", "commit_verification.reason must be text")


def _validate_snapshot_directory(directory: Path) -> tuple[dict[str, Any], list[dict[str, object]]]:
    try:
        entries = list(directory.iterdir())
    except OSError as error:
        raise HumanizerUpstreamError("candidate_unreadable", str(error)) from error
    names = {path.name for path in entries}
    _require(names == {"SKILL.md", "LICENSE", "UPSTREAM.json"}, "candidate_files_invalid", "Candidate must contain only SKILL.md, LICENSE, and UPSTREAM.json")
    _require(
        all(path.is_file() and not path.is_symlink() for path in entries),
        "candidate_files_invalid",
        "Candidate entries must be regular files",
    )
    manifest = _read_json(directory / "UPSTREAM.json", code="manifest_unreadable")
    _validate_manifest(manifest)
    try:
        skill_bytes = (directory / "SKILL.md").read_bytes()
        license_bytes = (directory / "LICENSE").read_bytes()
        skill_text = skill_bytes.decode("utf-8")
        license_text = license_bytes.decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise HumanizerUpstreamError("snapshot_unreadable", str(error)) from error
    _validate_file_entry(manifest, "SKILL.md", skill_bytes)
    _validate_file_entry(manifest, "LICENSE", license_bytes)
    _require(license_text.startswith("MIT License\n"), "license_invalid", "LICENSE must contain the MIT license")
    _validate_no_capability_metadata(skill_text)
    _require(_frontmatter_value(skill_text, "name") == "humanizer", "skill_metadata_invalid", "SKILL.md name must remain humanizer")
    _require(_frontmatter_value(skill_text, "license") == "MIT", "license_invalid", "SKILL.md license must remain MIT")
    version = _frontmatter_value(skill_text, "version")
    _require(version == manifest.get("declared_version"), "manifest_version_mismatch", "Manifest version does not match SKILL.md")
    patterns = _patterns(skill_text)
    _require(manifest.get("patterns") == patterns, "pattern_inventory_mismatch", "Manifest patterns do not match SKILL.md")
    return manifest, patterns


def _validate_policy(policy: Mapping[str, Any], manifest: Mapping[str, Any], patterns: Sequence[Mapping[str, object]]) -> None:
    _require(policy.get("schema") == POLICY_SCHEMA, "policy_schema_invalid", f"Policy schema must be {POLICY_SCHEMA}")
    reviewed = policy.get("reviewed_upstream_commit")
    _require(reviewed == manifest.get("resolved_commit"), "unreviewed_upstream_commit", "Local policy has not reviewed the vendored upstream commit")
    precedence = policy.get("precedence")
    _require(isinstance(precedence, list) and all(isinstance(item, str) and item for item in precedence), "policy_precedence_invalid", "Policy precedence must be a non-empty string list")
    protected = policy.get("protected_spans")
    _require(isinstance(protected, list) and all(isinstance(item, str) and item for item in protected), "policy_protected_spans_invalid", "Policy protected_spans must be a non-empty string list")
    _require(policy.get("runtime_network") is False, "runtime_network_invalid", "Policy runtime_network must be false")
    entries = policy.get("patterns")
    _require(isinstance(entries, list), "pattern_policy_invalid", "Policy patterns must be a list")
    expected_headings = {int(item["id"]): str(item["heading"]) for item in patterns}
    upstream_ids: list[int] = []
    stable_ids: list[str] = []
    for entry in entries:
        _require(isinstance(entry, dict), "pattern_policy_invalid", "Each policy pattern must be an object")
        upstream_id = entry.get("upstream_id")
        stable_id = entry.get("stable_rule_id")
        disposition = entry.get("disposition")
        _require(isinstance(upstream_id, int), "pattern_policy_invalid", "Each policy pattern requires an integer upstream_id")
        _require(
            entry.get("upstream_heading") == expected_headings.get(upstream_id),
            "pattern_policy_heading_mismatch",
            f"Pattern {upstream_id} heading does not match the reviewed upstream snapshot",
        )
        _require(isinstance(stable_id, str) and stable_id.startswith("humanizer."), "pattern_policy_invalid", "Each policy pattern requires a namespaced stable_rule_id")
        _require(disposition in ALLOWED_DISPOSITIONS, "pattern_policy_invalid", f"Unsupported disposition for pattern {upstream_id}")
        channels = entry.get("channels")
        exceptions = entry.get("exceptions")
        _require(isinstance(channels, list) and channels and all(isinstance(item, str) and item for item in channels), "pattern_policy_invalid", f"Pattern {upstream_id} requires channels")
        _require(isinstance(exceptions, list) and all(isinstance(item, str) and item for item in exceptions), "pattern_policy_invalid", f"Pattern {upstream_id} requires exceptions")
        _require(isinstance(entry.get("rationale"), str) and entry.get("rationale").strip(), "pattern_policy_invalid", f"Pattern {upstream_id} requires rationale")
        enforcement = entry.get("enforcement")
        if disposition == "blocking":
            _require(isinstance(enforcement, dict), "pattern_enforcement_invalid", f"Blocking pattern {upstream_id} requires explicit enforcement")
            mode = enforcement.get("mode")
            _require(mode in {"existing_rules", "policy_regex"}, "pattern_enforcement_invalid", f"Blocking pattern {upstream_id} has an unsupported enforcement mode")
            if mode == "existing_rules":
                rule_ids = enforcement.get("rule_ids")
                _require(isinstance(rule_ids, list) and all(isinstance(item, str) and item for item in rule_ids), "pattern_enforcement_invalid", f"Blocking pattern {upstream_id} requires existing rule IDs")
                _require(isinstance(enforcement.get("advisory_remainder"), bool), "pattern_enforcement_invalid", f"Blocking pattern {upstream_id} requires advisory_remainder")
            else:
                _require(enforcement.get("severity") == "error", "pattern_enforcement_invalid", f"Policy regex {upstream_id} must use error severity")
                pattern = enforcement.get("pattern")
                _require(isinstance(pattern, str) and pattern, "pattern_enforcement_invalid", f"Policy regex {upstream_id} requires a pattern")
                try:
                    re.compile(pattern)
                except re.error as error:
                    raise HumanizerUpstreamError("pattern_enforcement_invalid", f"Policy regex {upstream_id} is invalid: {error}") from error
                flags = enforcement.get("flags")
                _require(isinstance(flags, list) and set(flags) <= {"ignore_case"}, "pattern_enforcement_invalid", f"Policy regex {upstream_id} has unsupported flags")
                _require(isinstance(enforcement.get("message"), str) and enforcement.get("message").strip(), "pattern_enforcement_invalid", f"Policy regex {upstream_id} requires a message")
                _require(isinstance(enforcement.get("suggestion"), str) and enforcement.get("suggestion").strip(), "pattern_enforcement_invalid", f"Policy regex {upstream_id} requires a suggestion")
        else:
            _require(enforcement is None, "pattern_enforcement_invalid", f"Non-blocking pattern {upstream_id} cannot define enforcement")
        upstream_ids.append(upstream_id)
        stable_ids.append(stable_id)
    _require(len(upstream_ids) == len(set(upstream_ids)), "pattern_policy_duplicate", "Policy upstream_id values must be unique")
    _require(len(stable_ids) == len(set(stable_ids)), "pattern_policy_duplicate", "Policy stable_rule_id values must be unique")
    expected_ids = [int(item["id"]) for item in patterns]
    _require(sorted(upstream_ids) == expected_ids, "pattern_policy_incomplete", "Policy must classify every upstream pattern exactly once")


def verify_repository(repo_root: str | Path) -> dict[str, object]:
    """Validate the current vendored snapshot and its Simpro activation policy."""

    root = Path(repo_root).resolve()
    vendor = root / VENDOR_RELATIVE
    policy = _read_json(root / POLICY_RELATIVE, code="policy_unreadable")
    manifest, patterns = _validate_snapshot_directory(vendor)
    version = str(manifest["declared_version"])
    _validate_policy(policy, manifest, patterns)
    return {
        "status": "valid",
        "resolved_commit": manifest["resolved_commit"],
        "declared_version": version,
        "pattern_count": len(patterns),
        "reviewed": True,
    }


def _source_ref(ref: str, commit: str) -> str:
    if ref == "main":
        return SOURCE_REF
    if FULL_SHA_RE.fullmatch(ref):
        return commit
    if re.fullmatch(r"v\d+\.\d+\.\d+", ref):
        return f"refs/tags/{ref}"
    raise HumanizerUpstreamError("upstream_ref_invalid", "ref must be main, a full commit SHA, or a vX.Y.Z tag")


def resolve_ref(ref: str) -> str:
    """Resolve an allowed upstream ref to one immutable commit."""

    if FULL_SHA_RE.fullmatch(ref):
        return ref
    source_ref = _source_ref(ref, "0" * 40)
    try:
        completed = subprocess.run(
            ["git", "ls-remote", f"{REPOSITORY}.git", source_ref],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise HumanizerUpstreamError("upstream_ref_unavailable", str(error)) from error
    _require(completed.returncode == 0, "upstream_ref_unavailable", completed.stderr.strip() or "git ls-remote failed")
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    _require(len(lines) == 1, "upstream_ref_unavailable", f"Expected exactly one result for {source_ref}")
    commit = lines[0].split()[0]
    _require(FULL_SHA_RE.fullmatch(commit) is not None, "upstream_ref_unavailable", "Upstream returned an invalid commit")
    return commit


def _validate_allowed_url(url: str) -> None:
    parsed = urlparse(url)
    _require(parsed.scheme == "https", "download_scheme_invalid", "Downloads require HTTPS")
    try:
        port = parsed.port
    except ValueError as error:
        raise HumanizerUpstreamError("download_url_invalid", str(error)) from error
    _require(
        parsed.username is None
        and parsed.password is None
        and port in {None, 443}
        and not parsed.query
        and not parsed.fragment,
        "download_url_invalid",
        "Download URLs may not contain credentials, custom ports, queries, or fragments",
    )
    _require(parsed.hostname in {RAW_HOST, API_HOST}, "download_host_invalid", f"Download host is not allowlisted: {parsed.hostname}")
    if parsed.hostname == RAW_HOST:
        parts = [part for part in parsed.path.split("/") if part]
        valid = (
            len(parts) == 4
            and parts[0:2] == ["blader", "humanizer"]
            and FULL_SHA_RE.fullmatch(parts[2]) is not None
            and parts[3] in ALLOWED_VENDOR_FILES
        )
        _require(valid, "download_path_invalid", "Raw download path is not allowlisted")
    else:
        parts = [part for part in parsed.path.split("/") if part]
        valid = (
            len(parts) == 5
            and parts[0:4] == ["repos", "blader", "humanizer", "commits"]
            and FULL_SHA_RE.fullmatch(parts[4]) is not None
        )
        _require(valid, "download_path_invalid", "API download path is not allowlisted")


class _AllowlistedRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        _validate_allowed_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _http_transport(url: str) -> bytes:
    opener = build_opener(_AllowlistedRedirectHandler())
    request = Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "seomachine-humanizer-updater"},
    )
    try:
        with opener.open(request, timeout=30) as response:
            content = response.read(MAX_DOWNLOAD_BYTES + 1)
    except OSError as error:
        raise HumanizerUpstreamError("download_failed", str(error)) from error
    _require(len(content) <= MAX_DOWNLOAD_BYTES, "download_too_large", "Downloaded file exceeds the size limit")
    return content


def fetch_allowed_url(url: str, *, transport: Fetcher | None = None) -> bytes:
    """Fetch one allowlisted upstream URL without following redirects off-host."""

    _validate_allowed_url(url)
    content = (transport or _http_transport)(url)
    _require(isinstance(content, bytes), "download_invalid", "Download transport must return bytes")
    _require(len(content) <= MAX_DOWNLOAD_BYTES, "download_too_large", "Downloaded file exceeds the size limit")
    return content


def load_commit_verification(commit: str) -> Mapping[str, object]:
    """Read GitHub's commit-verification state without making it an activation authority."""

    url = f"https://{API_HOST}/repos/blader/humanizer/commits/{commit}"
    try:
        payload = json.loads(fetch_allowed_url(url).decode("utf-8"))
        verification = payload["commit"]["verification"]
        verified = verification.get("verified")
        reason = verification.get("reason")
        if verified not in {True, False} or not isinstance(reason, str):
            raise KeyError("verification")
        return {"verified": verified, "reason": reason}
    except (HumanizerUpstreamError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        return {"verified": None, "reason": "lookup_failed"}


def _candidate_payload(
    *,
    ref: str,
    commit: str,
    skill_bytes: bytes,
    license_bytes: bytes,
    verification: Mapping[str, object],
) -> tuple[dict[str, Any], str, list[dict[str, object]]]:
    try:
        skill_text = skill_bytes.decode("utf-8")
        license_text = license_bytes.decode("utf-8")
    except UnicodeError as error:
        raise HumanizerUpstreamError("snapshot_encoding_invalid", str(error)) from error
    _require(license_text.startswith("MIT License\n"), "license_invalid", "Candidate LICENSE must remain MIT")
    _validate_no_capability_metadata(skill_text)
    _require(_frontmatter_value(skill_text, "name") == "humanizer", "skill_metadata_invalid", "Candidate skill name must remain humanizer")
    _require(_frontmatter_value(skill_text, "license") == "MIT", "license_invalid", "Candidate skill license must remain MIT")
    version = _frontmatter_value(skill_text, "version")
    _require(SEMVER_RE.fullmatch(version) is not None, "manifest_version_invalid", "Candidate version must use X.Y.Z")
    patterns = _patterns(skill_text)
    normalized_verification = {
        "verified": verification.get("verified"),
        "reason": verification.get("reason"),
    }
    _require(normalized_verification["verified"] in {True, False, None}, "commit_verification_invalid", "Invalid verification state")
    _require(isinstance(normalized_verification["reason"], str), "commit_verification_invalid", "Invalid verification reason")
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "repository": REPOSITORY,
        "source_ref": _source_ref(ref, commit),
        "resolved_commit": commit,
        "declared_version": version,
        "commit_verification": normalized_verification,
        "license_spdx": "MIT",
        "network_at_runtime": False,
        "executed_upstream_files": [],
        "files": {
            "SKILL.md": {"sha256": _sha256(skill_bytes), "bytes": len(skill_bytes)},
            "LICENSE": {"sha256": _sha256(license_bytes), "bytes": len(license_bytes)},
        },
        "patterns": patterns,
    }
    return manifest, version, patterns


def stage_candidate(
    *,
    ref: str,
    output: str | Path,
    resolver: Resolver = resolve_ref,
    fetcher: Fetcher = fetch_allowed_url,
    verification_loader: VerificationLoader = load_commit_verification,
) -> dict[str, object]:
    """Fetch and validate a candidate into a new, non-repository directory."""

    destination = Path(output).resolve()
    _require(not destination.exists(), "candidate_output_exists", f"Candidate output already exists: {destination}")
    commit = resolver(ref)
    _require(FULL_SHA_RE.fullmatch(commit) is not None, "manifest_commit_invalid", "Resolver must return a full lowercase commit SHA")
    base = f"https://{RAW_HOST}/blader/humanizer/{commit}"
    skill_bytes = fetcher(f"{base}/SKILL.md")
    license_bytes = fetcher(f"{base}/LICENSE")
    _require(len(skill_bytes) <= MAX_DOWNLOAD_BYTES and len(license_bytes) <= MAX_DOWNLOAD_BYTES, "download_too_large", "Candidate file exceeds the size limit")
    manifest, version, patterns = _candidate_payload(
        ref=ref,
        commit=commit,
        skill_bytes=skill_bytes,
        license_bytes=license_bytes,
        verification=verification_loader(commit),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        (temporary / "SKILL.md").write_bytes(skill_bytes)
        (temporary / "LICENSE").write_bytes(license_bytes)
        (temporary / "UPSTREAM.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        _validate_snapshot_directory(temporary)
        temporary.replace(destination)
    except Exception:
        if temporary.exists():
            for path in temporary.iterdir():
                path.unlink(missing_ok=True)
            temporary.rmdir()
        raise
    return {
        "status": "staged",
        "resolved_commit": commit,
        "declared_version": version,
        "pattern_count": len(patterns),
        "output": str(destination),
    }


def _pattern_changes(current: Sequence[Mapping[str, object]], candidate: Sequence[Mapping[str, object]]) -> dict[str, list[object]]:
    old = {int(item["id"]): str(item["heading"]) for item in current}
    new = {int(item["id"]): str(item["heading"]) for item in candidate}
    return {
        "added": [{"id": item, "heading": new[item]} for item in sorted(set(new) - set(old))],
        "removed": [{"id": item, "heading": old[item]} for item in sorted(set(old) - set(new))],
        "renamed": [
            {"id": item, "from": old[item], "to": new[item]}
            for item in sorted(set(old) & set(new))
            if old[item] != new[item]
        ],
    }


def check_upstream(
    *,
    repo_root: str | Path,
    ref: str = "main",
    resolver: Resolver = resolve_ref,
    fetcher: Fetcher = fetch_allowed_url,
) -> dict[str, object]:
    """Compare the vendored snapshot with upstream without writing files."""

    root = Path(repo_root).resolve()
    manifest, current_patterns = _validate_snapshot_directory(root / VENDOR_RELATIVE)
    latest = resolver(ref)
    _require(FULL_SHA_RE.fullmatch(latest) is not None, "manifest_commit_invalid", "Resolver must return a full lowercase commit SHA")
    current = str(manifest["resolved_commit"])
    if latest == current:
        return {
            "status": "current",
            "current_commit": current,
            "latest_commit": latest,
            "declared_version": manifest["declared_version"],
            "current_declared_version": manifest["declared_version"],
            "latest_declared_version": manifest["declared_version"],
            "current_commit_verification": manifest["commit_verification"],
            "current_files": manifest["files"],
            "latest_files": manifest["files"],
            "pattern_changes": {"added": [], "removed": [], "renamed": []},
        }
    base = f"https://{RAW_HOST}/blader/humanizer/{latest}"
    skill_bytes = fetcher(f"{base}/SKILL.md")
    license_bytes = fetcher(f"{base}/LICENSE")
    candidate_manifest, version, candidate_patterns = _candidate_payload(
        ref=ref,
        commit=latest,
        skill_bytes=skill_bytes,
        license_bytes=license_bytes,
        verification={"verified": None, "reason": "not_checked"},
    )
    return {
        "status": "update_available",
        "current_commit": current,
        "latest_commit": latest,
        "declared_version": version,
        "current_declared_version": manifest["declared_version"],
        "latest_declared_version": version,
        "current_commit_verification": manifest["commit_verification"],
        "pattern_changes": _pattern_changes(current_patterns, candidate_patterns),
        "current_files": manifest["files"],
        "latest_files": candidate_manifest["files"],
        "files": candidate_manifest["files"],
    }


def adopt_candidate(
    *,
    repo_root: str | Path,
    candidate: str | Path,
    expected_current: str,
) -> dict[str, object]:
    """Atomically replace only the vendored snapshot after compare-and-swap validation."""

    root = Path(repo_root).resolve()
    vendor = root / VENDOR_RELATIVE
    current_manifest, _ = _validate_snapshot_directory(vendor)
    current = str(current_manifest["resolved_commit"])
    _require(current == expected_current, "expected_current_mismatch", "Current snapshot changed after review began")
    candidate_path = Path(candidate).resolve()
    candidate_manifest, _ = _validate_snapshot_directory(candidate_path)
    _require(
        (candidate_path / "LICENSE").read_bytes() == (vendor / "LICENSE").read_bytes(),
        "license_changed",
        "Candidate license text changed and requires a separate legal review",
    )
    replacement_names = ("SKILL.md", "LICENSE", "UPSTREAM.json")
    previous = {name: (vendor / name).read_bytes() for name in replacement_names}
    temporary_paths: dict[str, Path] = {}
    try:
        for name in replacement_names:
            handle, temp_name = tempfile.mkstemp(prefix=f".{name}.", dir=vendor)
            os.close(handle)
            temp_path = Path(temp_name)
            temp_path.write_bytes((candidate_path / name).read_bytes())
            temporary_paths[name] = temp_path
        for name in replacement_names:
            os.replace(temporary_paths[name], vendor / name)
        _validate_snapshot_directory(vendor)
    except Exception as error:
        for name, content in previous.items():
            handle, temp_name = tempfile.mkstemp(prefix=f".rollback-{name}.", dir=vendor)
            os.close(handle)
            temp_path = Path(temp_name)
            temp_path.write_bytes(content)
            os.replace(temp_path, vendor / name)
        if isinstance(error, HumanizerUpstreamError):
            raise
        raise HumanizerUpstreamError("candidate_adoption_failed", str(error)) from error
    finally:
        for temp_path in temporary_paths.values():
            temp_path.unlink(missing_ok=True)
    return {
        "status": "adopted",
        "previous_commit": current,
        "resolved_commit": candidate_manifest["resolved_commit"],
        "review_required": candidate_manifest["resolved_commit"] != current,
    }


def _json_print(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify", help="Validate the local snapshot and policy without network access")
    check = subparsers.add_parser("check-upstream", help="Compare the reviewed snapshot with upstream")
    check.add_argument("--ref", default="main")
    stage = subparsers.add_parser("stage", help="Fetch and validate a candidate outside tracked files")
    stage.add_argument("--ref", default="main")
    stage.add_argument("--output", required=True)
    adopt = subparsers.add_parser("adopt", help="Replace only the vendored snapshot from a candidate")
    adopt.add_argument("--candidate", required=True)
    adopt.add_argument("--expected-current", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "verify":
            _json_print(verify_repository(args.repo_root))
            return 0
        if args.command == "check-upstream":
            _json_print(check_upstream(repo_root=args.repo_root, ref=args.ref))
            return 0
        if args.command == "stage":
            _json_print(stage_candidate(ref=args.ref, output=args.output))
            return 0
        if args.command == "adopt":
            _json_print(
                adopt_candidate(
                    repo_root=args.repo_root,
                    candidate=args.candidate,
                    expected_current=args.expected_current,
                )
            )
            return 0
    except HumanizerUpstreamError as error:
        _json_print({"status": "invalid", "error": {"code": error.code, "message": str(error)}})
        return 1
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
