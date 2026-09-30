"""Guard the repo-local context boundary for vault-only Simpro authority."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

try:
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding, should_fail, summarize_findings


ALLOWED_CATEGORIES = frozenset(
    {
        "seo_aeo",
        "editorial_strategy",
        "cro_best_practice",
        "link_map",
        "source_governance",
    }
)
POLICY_SCHEMA = "seomachine-context-boundary-policy/v1"
DEFAULT_POLICY_PATH = Path("context/context-policy.json")

PROHIBITED_CONTEXT_PATH_RE = re.compile(
    r"(?:^|/)(?:"
    r"brand-voice\.md|features\.md|lightning-positioning\.md|style-guide\.md|"
    r"customer-proof-index\.json|customer-proof-intake[^/]*\.csv|"
    r"_coverage-report\.md|competitor-analysis\.md|"
    r"reference/competitors/battlecards/|reference/writing-examples/|reference/coverage/"
    r")$",
    re.IGNORECASE,
)
PROHIBITED_CONTEXT_REFERENCE_RE = re.compile(
    r"context/(?:"
    r"brand-voice\.md|features\.md|lightning-positioning\.md|style-guide\.md|"
    r"customer-proof-index\.json|customer-proof-intake[^\\s`'\"),]*|"
    r"reference/competitors/battlecards/[^\\s`'\"),]+|"
    r"reference/writing-examples/[^\\s`'\"),]+"
    r")",
    re.IGNORECASE,
)
LOCAL_FALLBACK_RE = re.compile(
    r"\b(?:fallback mirror|local fallback|repo-local fallback|context-backed proof|"
    r"context files are an internal source of truth|use .*?fallback|fallbacks?)\b",
    re.IGNORECASE,
)
ROUTING_VERB_RE = re.compile(
    r"\b(?:use|load|read|consult|follow|source|authorize|authorise|fallback|mirror|"
    r"calibrate|choose|select|mine|check)\b",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(
    r"\b(?:do not|don't|does not|doesn't|never|no longer|"
    r"no (?:local|repo-local)(?: [a-z-]+){0,4} fallback|"
    r"must not|cannot|can't|not an? |not a |not the|prohibit|prohibited|"
    r"reject|deleted|removed|omit)\b",
    re.IGNORECASE,
)
BRAND_AUTHORITY_LANGUAGE_RE = re.compile(
    r"\b(?:brand voice|message house|voice and tone|tone guidance|ICP|audience|"
    r"brand messaging|terminology|product language|feature language|solution language|"
    r"industry language|Lightning positioning|competitor positioning|battlecard|"
    r"customer proof|proof inventory|quote matrix|approved claims?|case stud(?:y|ies)|"
    r"customer stor(?:y|ies)|reviews?|ebooks?|E-E-A-T|EEAT|approved metrics?)\b",
    re.IGNORECASE,
)
LOCAL_AUTHORITY_CLAIM_RE = re.compile(
    r"\b(?:source of truth|approved metrics?|approved claims?|proof candidates?|"
    r"customer proof index|quote matrix|brand voice|message house|battlecards?|"
    r"Lightning positioning|writing examples?)\b",
    re.IGNORECASE,
)
LOCAL_OWNERSHIP_CONTEXT_RE = re.compile(
    r"\b(?:repo-local|local|context-backed|context files?|this file|this inventory|"
    r"this index|stored locally|local proof artifact|context/)\b",
    re.IGNORECASE,
)
EXCLUDED_DOC_PARTS = frozenset({"worktrees", "__pycache__"})


def check_content(
    content: str = "",
    *,
    proof_content: str | None = None,
    source_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
    policy_path: str | Path | None = None,
) -> list[Finding]:
    """Validate the local context policy and optional sidecar evidence."""
    del content
    root = _workspace_root(workspace_root, source_path)
    policy_file = (root / (policy_path or DEFAULT_POLICY_PATH)).resolve()
    findings = _policy_findings(root, policy_file)
    findings.extend(_active_doc_findings(root))
    if proof_content:
        findings.extend(_evidence_findings(proof_content))
    return sorted(
        findings,
        key=lambda finding: (
            finding.get("severity") != "error",
            str(finding.get("path", "")),
            int(finding.get("line", 1)),
            str(finding.get("rule_id", "")),
        ),
    )


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: str | Path | None = None,
    policy_path: str | Path | None = None,
) -> list[Finding]:
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    article = Path(path)
    proof_content = ""
    if proof_sidecar:
        proof_path = Path(proof_sidecar)
        if not proof_path.is_absolute():
            proof_path = article.parent / proof_path
        if proof_path.exists():
            proof_content = proof_path.read_text(encoding="utf-8")
    return check_content(
        article.read_text(encoding="utf-8") if article.exists() else "",
        proof_content=proof_content,
        source_path=article,
        policy_path=policy_path,
    )


def _workspace_root(
    workspace_root: str | Path | None,
    source_path: str | Path | None,
) -> Path:
    if workspace_root is not None:
        return Path(workspace_root).resolve()
    if source_path is not None:
        candidate = Path(source_path).resolve()
        for parent in (candidate.parent, *candidate.parents):
            if (parent / "context").is_dir():
                return parent
    return Path.cwd().resolve()


def _policy_findings(root: Path, policy_path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not policy_path.exists():
        return [
            _finding(
                "context_policy_missing",
                "context/context-policy.json is required to classify every context file.",
                path=str(policy_path),
            )
        ]
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return [
            _finding(
                "context_policy_invalid",
                f"Context boundary policy is invalid JSON: {error}",
                path=str(policy_path),
            )
        ]
    if policy.get("schema") != POLICY_SCHEMA:
        findings.append(
            _finding(
                "context_policy_schema_invalid",
                f"Context boundary policy must use {POLICY_SCHEMA}.",
                path=_relative(policy_path, root),
            )
        )
    files = policy.get("files")
    if not isinstance(files, Mapping):
        files = {}
        findings.append(
            _finding(
                "context_policy_files_invalid",
                "Context boundary policy requires a files object.",
                path=_relative(policy_path, root),
            )
        )
    registered = {_normalize_context_path(path): value for path, value in files.items()}
    context_files = {
        _relative(path, root)
        for path in (root / "context").rglob("*")
        if path.is_file()
    }
    for path in sorted(context_files):
        row = registered.get(path)
        if row is None:
            findings.append(
                _finding(
                    "context_file_unregistered",
                    "Every file under context/ must be registered in context-policy.json.",
                    path=path,
                )
            )
            continue
        category = _category(row)
        if category not in ALLOWED_CATEGORIES:
            findings.append(
                _finding(
                    "context_file_category_invalid",
                    f"Context file category is not allowed: {category or '[missing]'}.",
                    path=path,
                )
            )
        if PROHIBITED_CONTEXT_PATH_RE.search(path):
            findings.append(
                _finding(
                    "context_brand_authority_file_present",
                    "A deleted local brand/proof authority class is still present under context/.",
                    path=path,
                )
            )
        findings.extend(_context_file_content_findings(root / path, path, category))
    for path in sorted(set(registered) - context_files):
        findings.append(
            _finding(
                "context_policy_registered_file_missing",
                "Context policy registers a file that does not exist.",
                path=path,
            )
        )
    return findings


def _context_file_content_findings(
    file_path: Path,
    relative_path: str,
    category: str,
) -> list[Finding]:
    findings: list[Finding] = []
    if _is_probably_binary(file_path):
        return findings
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return findings
    for line_number, line in enumerate(lines, start=1):
        normalized = line.strip()
        if not normalized:
            continue
        if _routes_to_local_brand_authority(normalized):
            findings.append(
                _finding(
                    "context_local_brand_fallback_reference",
                    "Context content routes brand/proof work to a local authority file.",
                    path=relative_path,
                    line=line_number,
                    match=normalized[:240],
                )
            )
        if _stores_local_brand_authority(normalized):
            findings.append(
                _finding(
                    "context_local_brand_authority_language",
                    "Context content appears to store or authorize brand/proof language locally.",
                    path=relative_path,
                    line=line_number,
                    match=normalized[:240],
                )
            )
    return findings


def _active_doc_findings(root: Path) -> list[Finding]:
    candidates: list[Path] = []
    for path in ("AGENTS.md", "CLAUDE.md", "README.md"):
        candidate = root / path
        if candidate.exists():
            candidates.append(candidate)
    for folder in (".claude", ".agents"):
        folder_path = root / folder
        if folder_path.exists():
            candidates.extend(
                path
                for path in folder_path.rglob("*.md")
                if path.is_file() and not _is_excluded_doc_path(path, root)
            )
    findings: list[Finding] = []
    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        relative_path = _relative(path, root)
        for line_number, line in enumerate(lines, start=1):
            normalized = line.strip()
            if _routes_to_local_brand_authority(normalized) or (
                LOCAL_FALLBACK_RE.search(normalized)
                and BRAND_AUTHORITY_LANGUAGE_RE.search(normalized)
                and not NEGATION_RE.search(normalized)
            ):
                findings.append(
                    _finding(
                        "active_doc_local_brand_fallback_reference",
                        "Active instructions must not route Simpro brand/proof work to local fallback files.",
                        path=relative_path,
                        line=line_number,
                        match=normalized[:240],
                    )
                )
    return findings


def _evidence_findings(content: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        normalized = line.strip()
        if _routes_to_local_brand_authority(normalized):
            findings.append(
                _finding(
                    "sidecar_local_brand_authority_reference",
                    "Validation sidecars and context-pack evidence cannot cite repo-local files as brand authority.",
                    line=line_number,
                    match=normalized[:240],
                )
            )
    return findings


def _routes_to_local_brand_authority(line: str) -> bool:
    if not PROHIBITED_CONTEXT_REFERENCE_RE.search(line):
        return False
    if NEGATION_RE.search(line):
        return False
    return bool(ROUTING_VERB_RE.search(line) or LOCAL_FALLBACK_RE.search(line))


def _stores_local_brand_authority(line: str) -> bool:
    if not LOCAL_AUTHORITY_CLAIM_RE.search(line):
        return False
    if _line_routes_authority_to_vault(line):
        return False
    if not LOCAL_OWNERSHIP_CONTEXT_RE.search(line):
        return False
    return True


def _line_routes_authority_to_vault(line: str) -> bool:
    normalized = line.casefold()
    if "vault" in normalized or "connector" in normalized:
        return True
    if NEGATION_RE.search(line):
        return True
    if "not a brand" in normalized or "not brand" in normalized:
        return True
    return False


def _is_excluded_doc_path(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    return any(part in EXCLUDED_DOC_PARTS for part in relative.parts)


def _category(row: object) -> str:
    if isinstance(row, str):
        return row.strip()
    if isinstance(row, Mapping):
        return str(row.get("category") or "").strip()
    return ""


def _normalize_context_path(path: object) -> str:
    return str(path).replace("\\", "/").strip().lstrip("./")


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_probably_binary(path: Path) -> bool:
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf"}


def _finding(
    rule_id: str,
    message: str,
    *,
    path: str = "",
    line: int = 1,
    match: str = "",
) -> Finding:
    finding = make_finding(
        rule_id,
        "error",
        line,
        message=message,
        suggestion=(
            "Move Simpro brand/proof authority to the vault connector path; keep "
            "context/ limited to SEO/AEO, editorial mechanics, generic CRO, link maps, and source governance."
        ),
    )
    if path:
        finding["path"] = path
    if match:
        finding["match"] = match
    return finding


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the vault-only context boundary.")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--proof-sidecar", action="append", default=[])
    parser.add_argument("--fail-on", choices=["error", "warning", "none"], default="error")
    args = parser.parse_args(argv)

    proof_content_parts = []
    for raw_path in args.proof_sidecar:
        path = Path(raw_path)
        if path.exists():
            proof_content_parts.append(path.read_text(encoding="utf-8"))
    findings = check_content(
        proof_content="\n".join(proof_content_parts),
        workspace_root=args.workspace_root,
        policy_path=args.policy,
    )
    print(json.dumps({"summary": summarize_findings(findings), "findings": findings}, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
