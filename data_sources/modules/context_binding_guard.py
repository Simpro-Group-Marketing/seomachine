"""Validate topology-agnostic Simpro context artifacts and sidecar bindings."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, List, Mapping, Optional, Sequence

from bs4 import BeautifulSoup

try:
    from .artifact_detection import extract_frontmatter, strip_frontmatter
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
    from .simpro_vault_client import SimproVaultClient, VaultClientError
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_detection import extract_frontmatter, strip_frontmatter
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content
    from simpro_vault_client import SimproVaultClient, VaultClientError


BINDING_SCHEMA = "seomachine-context-binding/v1"
PACK_SCHEMA = "simpro-product-context-pack/v2"
RECEIPT_SCHEMA = "simpro-context-receipt/v1"
REQUIRED_REVISIONS = {
    "approval_policy_revision",
    "claim_registry_revision",
    "content_revision",
    "contract_revision",
    "inventory_revision",
    "manifest_revision",
}
SIMPRO_ARTICLE_RE = re.compile(r"\bSimpro\b|https?://(?:www\.)?simprogroup\.com/", re.IGNORECASE)
REPO_CONTEXT_ALLOWLIST = {
    "context/seo-guidelines.md": frozenset({"SEO structure", "Schema rules", "Publish gates"}),
    "context/aeo-geo-blog-strategy.md": frozenset(
        {"AEO/GEO workflow", "FAQ policy", "Publish gates", "Schema rules"}
    ),
    "context/style-guide.md": frozenset({"Editorial mechanics"}),
    "context/target-keywords.md": frozenset({"Keyword data"}),
    "context/internal-links-map.md": frozenset({"Internal-link inventory"}),
    "context/cro-best-practices.md": frozenset({"CRO guidance"}),
    "context/reddit-strategy.md": frozenset({"Reddit strategy"}),
    "context/writing-examples.md": frozenset({"Writing examples"}),
    "context/field-service-management-platform-faq-list.md": frozenset(
        {"FAQ questions and formatting"}
    ),
    "context/ai-citation-targets.md": frozenset({"AI citation targets"}),
    "context/source-routing-map.md": frozenset({"Workflow routing policy"}),
    "context/customer-proof-usage-ledger.json": frozenset({"Proof usage tracking"}),
}
REPO_CONTEXT_ROLES = frozenset(
    role for roles in REPO_CONTEXT_ALLOWLIST.values() for role in roles
)
PUBLIC_CLAIM_USE_MODES = frozenset(
    {
        "authority_support",
        "exact_quote",
        "paraphrase",
        "public_claim",
        "public_metric",
        "public_paraphrase",
    }
)


def requires_context(content: str) -> bool:
    """Return whether an article workflow requires Simpro vault context.

    Blog classification is the security boundary.  Literal product tokens are
    useful search input, but can never be an opt-out switch for vault context.
    """
    return True


def build_binding(
    article_path: str | Path,
    request_path: str | Path,
    pack_path: str | Path,
    receipt_path: str | Path,
    *,
    repo_context: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Build the deterministic sidecar binding for four exact artifacts."""
    article = Path(article_path)
    request_file = Path(request_path)
    pack_file = Path(pack_path)
    receipt_file = Path(receipt_path)
    pack = _read_json(pack_file)
    receipt = _read_json(receipt_file)
    sections = pack.get("sections", {}) if isinstance(pack, dict) else {}
    discovery = sections.get("Discovery Trace", {}) if isinstance(sections, dict) else {}
    constraints = sections.get("Constraints and Unresolved Gaps", {}) if isinstance(sections, dict) else {}
    task_scope = sections.get("Task and Scope", {}) if isinstance(sections, dict) else {}
    normalized_repo_context = _validate_repo_context(repo_context)
    revisions = receipt.get("revisions")
    if not isinstance(revisions, dict):
        revisions = {}
    return {
        "schema": BINDING_SCHEMA,
        "article": {"file": article.name, "sha256": _file_hash(article)},
        "request": {"file": request_file.name, "sha256": _file_hash(request_file)},
        "pack": {
            "file": pack_file.name,
            "schema": pack.get("schema"),
            "sha256": _file_hash(pack_file),
            "canonical_sha256": receipt.get("pack_sha256"),
        },
        "receipt": {
            "file": receipt_file.name,
            "schema": receipt.get("schema"),
            "sha256": _file_hash(receipt_file),
            "canonical_sha256": receipt.get("receipt_sha256"),
        },
        "revisions": revisions,
        "approval_policy_revision": revisions.get("approval_policy_revision"),
        "claim_registry_revision": revisions.get("claim_registry_revision")
        or receipt.get("claim_registry_revision"),
        "resource_ids": discovery.get("selected_resource_ids", []),
        "task_satisfaction": task_scope.get("task_satisfaction"),
        "unresolved_gaps": constraints.get("unresolved_gaps", []),
        "repo_context": normalized_repo_context,
    }


def render_generated_blocks(
    binding: Mapping[str, Any],
    claim_use_map: Sequence[Mapping[str, Any]],
) -> str:
    """Render the machine-readable non-public sidecar blocks."""
    return "\n".join(
        [
            "## Context Binding",
            "",
            "```json",
            json.dumps(dict(binding), ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## Context Claim Use Map",
            "",
            "```json",
            json.dumps([dict(item) for item in claim_use_map], ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    vault_root: str | Path | None = None,
    client: Any = None,
) -> List[Finding]:
    """Validate live connector state and the exact article-sidecar binding."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    article = Path(path)
    content = article.read_text(encoding="utf-8")
    if not requires_context(content):
        return []
    supplied = {
        "request": context_request,
        "pack": context_pack,
        "receipt": context_receipt,
    }
    findings: List[Finding] = []
    for label, value in supplied.items():
        if value is None:
            findings.append(_finding(f"context_{label}_missing", f"Simpro content requires a context {label} artifact."))
    if findings:
        return findings
    request_path = Path(str(context_request))
    pack_path = Path(str(context_pack))
    receipt_path = Path(str(context_receipt))
    for label, artifact in (("request", request_path), ("pack", pack_path), ("receipt", receipt_path)):
        if not artifact.is_file():
            findings.append(_finding(f"context_{label}_unavailable", f"Context {label} artifact is unavailable: {artifact}"))
    if findings:
        return findings
    try:
        request = _read_json(request_path)
        pack = _read_json(pack_path)
        receipt = _read_json(receipt_path)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return [_finding("context_artifact_invalid", f"Context artifact is invalid: {error}")]
    findings.extend(validate_request_article(request, content))
    pack_revisions = pack.get("revisions")
    receipt_revisions = receipt.get("revisions")
    if (
        not isinstance(pack_revisions, dict)
        or not isinstance(receipt_revisions, dict)
        or set(pack_revisions) != REQUIRED_REVISIONS
        or pack_revisions != receipt_revisions
        or any(
            not isinstance(pack_revisions.get(name), str)
            or not pack_revisions.get(name)
            for name in REQUIRED_REVISIONS
        )
    ):
        findings.append(
            _finding(
                "context_revisions_invalid",
                "Context pack and receipt must bind the same complete current revision set.",
            )
        )
    if pack.get("schema") != PACK_SCHEMA:
        findings.append(_finding("context_pack_schema_invalid", f"Context pack must use {PACK_SCHEMA}."))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        findings.append(_finding("context_receipt_schema_invalid", f"Context receipt must use {RECEIPT_SCHEMA}."))
    if findings:
        return findings
    try:
        validator = client or SimproVaultClient(vault_root=vault_root)
        validation = validator.validate_context(request, pack, receipt)
    except VaultClientError as error:
        rule = "context_pack_stale" if error.code == "pack_stale" else f"context_{error.code}"
        return [_finding(rule, str(error), connector_error_code=error.code)]
    except Exception as error:  # pragma: no cover - defensive fail-closed boundary.
        return [_finding("context_validation_failed", f"Context validation failed: {error}")]
    if not isinstance(validation, dict) or validation.get("valid") is not True or validation.get("errors"):
        return [_finding("context_validation_failed", "The shared connector did not validate the context artifacts.")]
    sidecar = load_sidecar_content(article, proof_sidecar)
    try:
        binding = _json_block(sidecar, "Context Binding")
        claim_map = _json_block(sidecar, "Context Claim Use Map")
    except ValueError as error:
        return [_finding("context_binding_invalid", str(error))]
    try:
        expected = build_binding(
            article,
            request_path,
            pack_path,
            receipt_path,
            repo_context=binding.get("repo_context", []) if isinstance(binding, dict) else [],
        )
    except ValueError as error:
        return [_finding("context_binding_invalid", str(error))]
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        findings.append(_finding("context_binding_schema_invalid", f"Context Binding must use {BINDING_SCHEMA}."))
    elif binding != expected:
        if binding.get("article", {}).get("sha256") != expected["article"]["sha256"]:
            findings.append(_finding("context_article_hash_mismatch", "The article changed after Context Binding was generated."))
        else:
            findings.append(_finding("context_binding_hash_mismatch", "Context Binding does not match the supplied artifacts."))
    if expected.get("task_satisfaction") != "satisfied" or expected.get("unresolved_gaps"):
        findings.append(_finding("context_task_unsatisfied", "Context task satisfaction must be satisfied with no unresolved gaps."))
    findings.extend(validate_claim_map(content, pack, receipt, claim_map))
    return findings


def validate_claim_map(
    article_content: str,
    pack: Mapping[str, Any],
    receipt: Mapping[str, Any],
    claim_map: Any,
) -> List[Finding]:
    findings: List[Finding] = []
    if not isinstance(claim_map, list):
        return [_finding("context_claim_use_map_invalid", "Context Claim Use Map must be a JSON array.")]
    decisions = receipt.get("claim_decisions", [])
    if not isinstance(decisions, list):
        return [_finding("context_claim_decisions_invalid", "Receipt claim decisions must be an array.")]
    evidence_rows = pack.get("sections", {}).get("Approved Claim Evidence", [])
    evidence = {}
    for row in evidence_rows:
        if isinstance(row, dict) and isinstance(row.get("claim_id"), str):
            evidence.setdefault(row["claim_id"], []).append(row)
    mapped = {}
    for row in claim_map:
        if not isinstance(row, dict) or not isinstance(row.get("claim_id"), str):
            findings.append(_finding("context_claim_use_map_invalid", "Every claim-use row must be an object with a claim ID."))
            continue
        mapped.setdefault(row["claim_id"], []).append(row)
    normalized_article = normalize_public_body(article_content)
    for decision in decisions:
        if not isinstance(decision, dict) or decision.get("approved") is not True:
            findings.append(_finding("context_claim_decision_invalid", "Receipt contains an invalid claim decision."))
            continue
        claim_id = decision.get("claim_id")
        rows = mapped.get(claim_id, [])
        if not rows:
            findings.append(_finding("context_claim_use_missing", f"Approved claim is not bound to public copy: {claim_id}"))
            continue
        evidence_matches = evidence.get(claim_id, [])
        if len(evidence_matches) != 1:
            findings.append(_finding("context_claim_evidence_ambiguous", f"Claim {claim_id} must resolve to exactly one evidence row."))
            continue
        evidence_row = evidence_matches[0]
        for row in rows:
            for field in ("use_mode", "brand_scope"):
                if row.get(field) != decision.get(field):
                    findings.append(_finding("context_claim_use_mismatch", f"Claim {claim_id} has a mismatched {field}."))
            if row.get("public_url") != evidence_row.get("public_url"):
                findings.append(_finding("context_claim_public_url_mismatch", f"Claim {claim_id} has a mismatched public URL."))
            public_text = row.get("public_text")
            if not isinstance(public_text, str) or not public_text.strip():
                findings.append(_finding("context_claim_public_text_missing", f"Claim {claim_id} has no exact public passage."))
                continue
            normalized = _normalize_public_text(public_text)
            if row.get("public_text_sha256") != _text_hash(normalized):
                findings.append(_finding("context_claim_public_text_hash_mismatch", f"Claim {claim_id} passage hash is invalid."))
            if normalized_article.count(normalized) != 1:
                findings.append(_finding("context_claim_public_text_mismatch", f"Claim {claim_id} passage must occur exactly once in the article."))
            use_mode = str(decision.get("use_mode", "")).strip()
            if use_mode not in PUBLIC_CLAIM_USE_MODES:
                findings.append(
                    _finding(
                        "context_claim_use_mode_invalid",
                        f"Claim {claim_id} has unsupported public use mode: {use_mode or '[missing]'}.",
                    )
                )
                continue
            if use_mode == "exact_quote":
                verbatim = evidence_row.get("verbatim_evidence")
                exact_text = verbatim.get("text") if isinstance(verbatim, dict) else None
                if not isinstance(exact_text, str) or normalized != _normalize_public_text(exact_text):
                    findings.append(_finding("context_claim_exact_quote_mismatch", f"Claim {claim_id} exact quote must equal its bound verbatim evidence."))
            if use_mode == "public_metric":
                assertion = evidence_row.get("assertion")
                if not isinstance(assertion, str) or normalized != _normalize_public_text(assertion):
                    findings.append(_finding("context_claim_public_metric_mismatch", f"Claim {claim_id} metric passage must equal its bound assertion."))
            if use_mode == "authority_support":
                assertion = evidence_row.get("assertion")
                if not isinstance(assertion, str) or normalized != _normalize_public_text(assertion):
                    findings.append(
                        _finding(
                            "context_claim_authority_support_mismatch",
                            f"Claim {claim_id} authority passage must equal its approved evidence assertion.",
                        )
                    )
            if use_mode in {"paraphrase", "public_paraphrase", "public_claim"}:
                assertion = evidence_row.get("assertion")
                if not isinstance(assertion, str) or normalized != _normalize_public_text(assertion):
                    findings.append(
                        _finding(
                            "context_claim_evidence_mismatch",
                            f"Claim {claim_id} public passage must equal its approved evidence assertion.",
                        )
                    )
    extra = set(mapped) - {decision.get("claim_id") for decision in decisions if isinstance(decision, dict)}
    for claim_id in sorted(extra):
        findings.append(_finding("context_claim_not_in_receipt", f"Claim map references a claim outside the receipt: {claim_id}"))
    return findings


def _json_block(content: str, heading: str) -> Any:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\s*```json\s*(?P<json>.*?)\s*```",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        raise ValueError(f"Validation sidecar is missing {heading}.")
    try:
        return json.loads(match.group("json"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{heading} is not valid JSON: {error}") from error


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON artifact must contain an object: {path}")
    return value


def validate_request_article(
    request: Mapping[str, Any],
    article_content: str,
) -> List[Finding]:
    """Validate the exact request scope against the article before mutation."""
    findings: List[Finding] = []
    request_rule, request_error = _request_error(request)
    if request_error:
        findings.append(_finding(request_rule or "context_request_scope_invalid", request_error))
    article_scope_error = _request_article_error(request, article_content)
    if article_scope_error:
        findings.append(_finding("context_request_article_mismatch", article_scope_error))
    return findings


def _request_error(request: Mapping[str, Any]) -> tuple[str | None, str | None]:
    task = request.get("task")
    scope = request.get("scope")
    if not isinstance(task, str) or not task.strip() or not isinstance(scope, dict):
        return "context_request_scope_invalid", "Context request requires the exact non-empty task and a scope object."
    required_strings = ("artifact_type", "brand", "title", "objective", "audience", "region")
    if any(not isinstance(scope.get(field), str) or not scope.get(field).strip() for field in required_strings):
        return "context_request_scope_invalid", "Context request scope requires artifact type, brand, title, objective, audience, and region."
    request_kinds, kind_error = _mapping_artifact_kinds(scope)
    if kind_error:
        return "context_request_scope_invalid", f"Context request {kind_error}"
    if len(set(request_kinds)) > 1:
        return "context_request_scope_mismatch", "Context request artifact_type and artifact_kind conflict."
    if not request_kinds or request_kinds[0] != "blog":
        return "context_request_scope_invalid", "Context request artifact type must identify a blog."
    if str(scope.get("brand")).strip().casefold() != "simpro":
        return "context_request_scope_invalid", "Context request brand scope must be Simpro."
    use_modes = scope.get("intended_public_use_modes")
    if not isinstance(use_modes, list) or not all(
        isinstance(mode, str) and mode.strip() for mode in use_modes
    ):
        return "context_request_scope_invalid", "Context request scope requires intended public-use modes."
    return None, None


def _request_article_error(request: Mapping[str, Any], content: str) -> str | None:
    scope = request.get("scope")
    if not isinstance(scope, Mapping):
        return None
    frontmatter = extract_frontmatter(content)
    body, _ = strip_frontmatter(content)
    h1_match = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
    article_title = (frontmatter.get("title") or (h1_match.group(1) if h1_match else "")).strip()
    request_title = str(scope.get("title", "")).strip()
    if not article_title:
        return "Article requires a title in frontmatter or its first H1."
    if _normalize_public_text(article_title).casefold() != _normalize_public_text(request_title).casefold():
        return "Context request title does not match the article title."
    article_brand = frontmatter.get("brand", "").strip()
    request_brand = str(scope.get("brand", "")).strip()
    if article_brand and article_brand.casefold() != request_brand.casefold():
        return "Context request brand does not match article frontmatter."
    article_kinds, article_kind_error = _mapping_artifact_kinds(frontmatter)
    if article_kind_error:
        return f"Article {article_kind_error}"
    if len(set(article_kinds)) > 1:
        return "Article artifact_type and artifact_kind conflict."
    request_kinds, request_kind_error = _mapping_artifact_kinds(scope)
    if request_kind_error or len(set(request_kinds)) > 1:
        return None
    if article_kinds and request_kinds and article_kinds[0] != request_kinds[0]:
        return "Context request artifact type does not match article frontmatter."
    return None


def _mapping_artifact_kinds(values: Mapping[str, Any]) -> tuple[list[str], str | None]:
    kinds: list[str] = []
    for field in ("artifact_type", "artifact_kind"):
        raw = values.get(field)
        if raw is None or not str(raw).strip():
            continue
        normalized = _normalize_artifact_kind(str(raw))
        if normalized is None:
            return [], f"{field} is unsupported: {raw}."
        kinds.append(normalized)
    return kinds, None


def _normalize_artifact_kind(value: str) -> str | None:
    normalized = value.strip().casefold().replace("-", "_").replace(" ", "_")
    if normalized in {"article", "post", "posts"}:
        return "blog"
    if normalized in {"page", "pages", "landing", "landingpage"}:
        return "landing_page"
    if normalized in {"blog", "landing_page"}:
        return normalized
    return None


def _validate_repo_context(
    repo_context: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in repo_context:
        if not isinstance(item, Mapping):
            raise ValueError("Repository context bindings must be objects.")
        path = str(item.get("path", "")).replace("\\", "/").strip()
        role = str(item.get("role", "")).strip()
        if not path.startswith("context/") or not role:
            raise ValueError("Repository context bindings require a context/ path and role.")
        canonical_path = next(
            (allowed for allowed in REPO_CONTEXT_ALLOWLIST if allowed.casefold() == path.casefold()),
            None,
        )
        if canonical_path is None:
            raise ValueError(
                "Repository context path is not approved for SEO, AEO, or editorial-mechanics binding."
            )
        if role not in REPO_CONTEXT_ROLES or role not in REPO_CONTEXT_ALLOWLIST[canonical_path]:
            raise ValueError("Repository context role is not approved for this context path.")
        normalized.append({"path": canonical_path, "role": role})
    return normalized


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_public_text(value: str) -> str:
    return normalize_public_text(value)


def normalize_public_text(value: str) -> str:
    """Canonicalize a public passage for evidence comparison and hashing."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip())


def normalize_public_body(content: str) -> str:
    """Return searchable visible Markdown body text without internal metadata."""
    body, _ = strip_frontmatter(content)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.DOTALL)
    body = re.sub(r"^(?:```|~~~).*?^(?:```|~~~)\s*$", " ", body, flags=re.MULTILINE | re.DOTALL)
    if "<" in body and ">" in body:
        soup = BeautifulSoup(body, "html.parser")
        for tag in soup(["script", "style", "template", "noscript", "head", "title", "meta"]):
            tag.decompose()
        for tag in soup.find_all(True):
            if tag.attrs is None:
                continue
            hidden = "hidden" in tag.attrs
            aria_hidden = str(tag.attrs.get("aria-hidden", "")).strip().casefold() == "true"
            if hidden or aria_hidden:
                tag.decompose()
        body = str(soup)
    body = re.sub(
        r"<(?:script|style|template|noscript|head|title)\b[^>]*>.*?</(?:script|style|template|noscript|head|title)>",
        " ",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    body = re.sub(r"<meta\b[^>]*>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(
        r"<([a-z][a-z0-9:-]*)\b(?=[^>]*(?:\bhidden\b|\baria-hidden\s*=\s*['\"]?true['\"]?))[^>]*>.*?</\1>",
        " ",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    body = re.sub(
        r"<[a-z][a-z0-9:-]*\b(?=[^>]*(?:\bhidden\b|\baria-hidden\s*=\s*['\"]?true['\"]?))[^>]*/?>",
        " ",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", body)
    body = re.sub(r"<[^>]+>", " ", body)
    body = html.unescape(body)
    body = re.sub(r"(?<!\\)[*_~`]", "", body)
    return _normalize_public_text(body)


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _finding(rule_id: str, message: str, **extra: object) -> Finding:
    return make_finding(
        rule_id,
        "error",
        1,
        message=message,
        suggestion="Regenerate and revalidate the Simpro context artifacts before publishing.",
        **extra,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Simpro context artifacts and sidecar binding.")
    parser.add_argument("path", help="Markdown article path")
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--context-request", required=True)
    parser.add_argument("--context-pack", required=True)
    parser.add_argument("--context-receipt", required=True)
    parser.add_argument("--vault-root")
    parser.add_argument("--fail-on", choices=["error", "warning", "none"], default="error")
    args = parser.parse_args(argv)
    findings = check_file(
        args.path,
        proof_sidecar=args.proof_sidecar,
        context_request=args.context_request,
        context_pack=args.context_pack,
        context_receipt=args.context_receipt,
        vault_root=args.vault_root,
        fail_on=args.fail_on,
    )
    print(json.dumps({"summary": summarize_findings(findings), "findings": findings}, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(main())
