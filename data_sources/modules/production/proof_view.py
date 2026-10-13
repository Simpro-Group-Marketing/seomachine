"""Render the scorers' proof view solely from the production BOM.

The existing raters read a Markdown proof sidecar. This view is that sidecar, written
only from BOM data: PAA questions and their bound artifact, the bound customer-proof
selector evidence, approved proof items, and verified facts. Nothing here is typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.faq_proof_guard import _extract_public_urls
from data_sources.modules.faq_structure import detect_faq_structure
from data_sources.modules.production.source_class import classify_source
from data_sources.modules.proof_link_policy import canonicalize_link_identity

# The production PAA lane records AnswerSocrates captures (paa_provenance_guard record);
# the rater rejects any bound artifact that is not a structured AnswerSocrates record.
PAA_SOURCE_KIND = "answersocrates"
FAQ_SOURCE_POLICY = (
    "## FAQ Source Policy\n"
    "- Allowed source classes: neutral, non_competing_expert, owned_product.\n"
    "- Competitor-owned FAQ sources: prohibited.\n"
    "- Status: aligned."
)


def _cell(value: Any) -> str:
    """Keep a value inside one pipe-delimited row field."""
    return " ".join(str(value or "").replace("|", "/").split())


def _path(binding: Mapping[str, Any], root: Path | None) -> str:
    relative = str(binding["path"])
    if root is None or any(char.isspace() for char in str(root)):
        return relative
    return (root / relative).as_posix()


def _paa_block(bom: Mapping[str, Any], root: Path | None) -> str:
    paa = bom.get("paa") if isinstance(bom.get("paa"), Mapping) else {}
    binding = paa.get("artifact")
    if not isinstance(binding, Mapping):
        return ""
    selected = [f"  - {_cell(item['question'])}" for item in paa.get("questions") or []]
    lines = ["## PAA/FAQ Provenance", f"- Source: {PAA_SOURCE_KIND}", f"- Artifact: {_path(binding, root)}"]
    return "\n".join([*lines, "- Selected questions:", *selected])


def _customer_proof(bom: Mapping[str, Any]) -> Mapping[str, Any]:
    block = bom.get("customer_proof")
    return block if isinstance(block, Mapping) else {}


def _story_role(bom: Mapping[str, Any]) -> Mapping[str, Any] | None:
    roles = _customer_proof(bom).get("roles") or []
    return next((row for row in roles if isinstance(row, Mapping) and row.get("role") == "experience_story"), None)


def _selector_block(bom: Mapping[str, Any], root: Path | None) -> str:
    binding = _customer_proof(bom).get("evidence")
    if not isinstance(binding, Mapping):
        return ""
    return f"## Customer Proof Slate\n- Selector evidence: {_path(binding, root)} | SHA-256: {binding['sha256']}"


def _story_fields(role: Mapping[str, Any], item: Mapping[str, Any]) -> tuple[str, str, str]:
    """Identity, URL and story from the selector's binding, else from the approved proof item."""
    candidate = role.get("selected_candidate")
    if isinstance(candidate, Mapping):
        return str(candidate.get("identity", "")), str(candidate.get("public_url", "")), str(candidate.get("story", ""))
    return str(item.get("customer", "")), str(item.get("url", "")), str(item.get("text", ""))


def _mining_block(bom: Mapping[str, Any]) -> str:
    role = _story_role(bom)
    if role is None or str(role.get("selected_id", "none")).casefold() == "none":
        return ""
    item = next((p for p in bom.get("proof") or [] if p.get("claim_id") == role["selected_id"]), None)
    if item is None:
        return ""
    identity, url, story = _story_fields(role, item)
    use = str(item["kind"]).replace("_", " ")
    return "\n".join([
        "## Selected Customer Proof Mining",
        f"- Proof: {_cell(role['selected_id'])} | Customer: {_cell(identity)} | URL: {_cell(url)}",
        "- Status: approved",
        f"- Usable POV/story found: {_cell(story)}",
        f"- Final use in copy: {use}: {_cell(story)}",
    ])


def _no_fit_block(bom: Mapping[str, Any]) -> str:
    role = _story_role(bom)
    if role is None or str(role.get("selected_id", "")).casefold() != "none":
        return ""
    rejected = role.get("rejected_overrides") if isinstance(role.get("rejected_overrides"), Mapping) else {}
    reason = str(role.get("no_fit_reason") or "") or "; ".join(str(value) for value in rejected.values())
    if not reason.strip():
        return ""
    return f"## E-E-A-T Proof Map\n- First-hand evidence decision: Selected: [none] {_cell(reason)}"


def _proof_pack(bom: Mapping[str, Any]) -> str:
    rows = [
        f"- Proof: {_cell(item['claim_id'])} | Kind: {_cell(item['kind'])} | Customer: {_cell(item.get('customer'))}"
        f" | URL: {_cell(item.get('url'))} | Evidence: {_cell(item.get('text'))}"
        for item in bom.get("proof") or []
    ]
    return "\n".join(["## Customer Proof Pack", *rows]) if rows else ""


def _source_map(bom: Mapping[str, Any]) -> str:
    rows = [
        f"- Claim: {_cell(fact['claim'])} | URL: {_cell(fact['url'])} | Evidence: {_cell(fact['quote'])}"
        f" | Verified at: {_cell(fact.get('verified_at'))}"
        for fact in bom.get("facts") or []
    ]
    return "\n".join(["## Source Map", *rows]) if rows else ""


def _bom_support(bom: Mapping[str, Any]) -> dict[str, str]:
    """Map each BOM fact and proof URL to the verified text that supports it."""
    support: dict[str, str] = {}
    for item in bom.get("proof") or []:
        support.setdefault(canonicalize_link_identity(str(item.get("url", ""))), str(item.get("text", "")))
    for fact in bom.get("facts") or []:
        support[canonicalize_link_identity(str(fact.get("url", "")))] = str(fact.get("quote", ""))
    return support


def _faq_row(question: str, url: str, support: Mapping[str, str], brand: str, root: Path | None) -> str:
    text = support.get(canonicalize_link_identity(url))
    classified = classify_source(url, brand, root) if text else None
    if classified is None:
        return ""
    source_class, competitor_check = classified
    return (
        f"- FAQ: {_cell(question)} | URL: {_cell(url)} | Source class: {source_class}"
        f" | Competitor check: {competitor_check} | Support: {_cell(text)}"
    )


def _faq_proof_map(bom: Mapping[str, Any], article: str, root: Path | None) -> str:
    support = _bom_support(bom)
    brand = str((bom.get("identity") or {}).get("brand", ""))
    rows = [
        _faq_row(entry.question, url, support, brand, root)
        for entry in detect_faq_structure(article).entries
        for url in dict.fromkeys(_extract_public_urls(entry.answer))
    ]
    rows = [row for row in rows if row]
    return "\n".join(["## FAQ Proof Map", *rows]) if rows else ""


def render_proof_view(bom: Mapping[str, Any], *, article: str = "", root: Path | None = None) -> str:
    """Render the rater-facing proof view; with ``root`` artifact paths are absolute."""
    blocks: Sequence[str] = (
        _paa_block(bom, root),
        FAQ_SOURCE_POLICY,
        _selector_block(bom, root),
        _mining_block(bom),
        _no_fit_block(bom),
        _proof_pack(bom),
        _source_map(bom),
        _faq_proof_map(bom, article, root),
    )
    return "\n\n".join(block for block in blocks if block) + "\n"
