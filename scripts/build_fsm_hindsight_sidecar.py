"""Build the dated FSM validation sidecar from the intact historical release.

This avoids copying large Markdown through a terminal output channel. The
builder applies only the current Hindsight enrichment, current evidence
bindings, and current lifecycle/readability changes.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
SOURCE = RESEARCH / "validation-best-field-service-management-software-2026-09-24.md"
OUTPUT = RESEARCH / "validation-best-field-service-management-software-2026-09-25.md"
ARTICLE = ROOT / "rewrites" / "best-field-service-management-software-rewrite-2026-08-28.md"
REQUEST = RESEARCH / "context-request-best-field-service-management-software-2026-09-25.json"
PACK = RESEARCH / "context-pack-best-field-service-management-software-2026-09-25.json"
RECEIPT = RESEARCH / "context-receipt-best-field-service-management-software-2026-09-25.json"
HINDSIGHT = RESEARCH / "hindsight-strategy-evidence-best-field-service-management-software-2026-09-25.json"
CUSTOMER = RESEARCH / "customer-proof-selector-evidence-best-field-service-management-software-2026-09-25.json"
FRED = RESEARCH / "fred-authority-selector-evidence-best-field-service-management-software-2026-09-25.md"
SERP = RESEARCH / "serp-evidence-best-field-service-management-software-2026-09-25.json"

SOURCE_MAP_HEADING = "## Source Map"
SOURCE_MAP_NEXT_HEADING = "## Search Intent and Format Decision"
OBSOLETE_FIELDEDGE_CLAIM = (
    "FieldEdge offers custom forms and templates that can be used for a "
    "failed-inspection demonstration."
)
OBSOLETE_FIELDEDGE_URL = "https://fieldedge.com/field-service-software/"
FIELDEDGE_PRICING_URL = "https://fieldedge.com/pricing/"
CORRECTION_RECORD = """## Governed Correction and Supersession Record

- Active artifact: `research/validation-best-field-service-management-software-2026-09-25.md` supersedes `research/validation-best-field-service-management-software-2026-09-24.md` for the corrected article.
- Correction reason: the cited FieldEdge marketing page did not substantiate the removed downstream automation chain involving follow-up tasks, office notices, customer messages, or audit trails.
- Historical boundary: the 2026-09-24 artifact remains immutable release history and is not active support for the corrected public copy.
"""
SEMRUSH_REUSE_AUTHORIZATION = """## Semrush Prior Evidence Reuse Authorization

- Status: authorized_by_user
- User instruction date: 2026-09-25
- Authorized stale rule: semrush_keyword_decision_stale
- Keyword decision artifact: `research/semrush-keyword-decision-best-field-service-management-software-2026-09-24.json`
- Collection date: 2026-09-24
- Assembly date: 2026-09-25
- Scope: FieldEdge evidence correction only; no keyword metrics, query selection, Semrush-derived public claims, or commercial-pillar decisions changed in this correction.
- Reuse boundary: the keyword decision remains a 2026-09-24 authenticated main-Chrome Semrush artifact and must not be described as recollected on 2026-09-25.
- Status rationale: Patrick directed the workflow to continue because Semrush had already been completed; the current correction removes unsupported FieldEdge automation evidence and does not alter keyword targeting.
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(content: str, old: str, new: str) -> str:
    count = content.count(old)
    if count != 1:
        raise ValueError(f"Expected one occurrence, found {count}: {old[:100]!r}")
    return content.replace(old, new, 1)


def replace_markdown_line(content: str, label: str, value: str) -> str:
    pattern = re.compile(rf"^- {re.escape(label)}: .*?$", flags=re.MULTILINE)
    updated, count = pattern.subn(f"- {label}: {value}", content, count=1)
    if count != 1:
        raise ValueError(f"Could not replace Markdown line {label}")
    return updated


def replace_section(content: str, heading: str, next_heading: str, body: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(heading)}\n.*?(?=^{re.escape(next_heading)}\n)",
        flags=re.MULTILINE | re.DOTALL,
    )
    updated, count = pattern.subn(f"{heading}\n\n{body.strip()}\n\n", content, count=1)
    if count != 1:
        raise ValueError(f"Could not replace section {heading}")
    return updated


def replace_full_section(
    content: str,
    heading: str,
    next_heading: str,
    full_section: str,
) -> str:
    pattern = re.compile(
        rf"^{re.escape(heading)}\n.*?(?=^{re.escape(next_heading)}\n)",
        flags=re.MULTILINE | re.DOTALL,
    )
    updated, count = pattern.subn(f"{full_section.strip()}\n\n", content, count=1)
    if count != 1:
        raise ValueError(f"Could not replace full section {heading}")
    return updated


def remove_obsolete_fieldedge_source_row(content: str) -> str:
    """Remove only the obsolete FieldEdge evidence row from the Source Map."""
    pattern = re.compile(
        rf"^{re.escape(SOURCE_MAP_HEADING)}\n.*?"
        rf"(?=^{re.escape(SOURCE_MAP_NEXT_HEADING)}\n)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if match is None:
        raise ValueError("Historical Source Map section is missing")

    source_map = match.group(0)
    rows = source_map.splitlines(keepends=True)
    obsolete_rows = [
        row
        for row in rows
        if row.startswith(f"- Claim: {OBSOLETE_FIELDEDGE_CLAIM} ")
        and f"| URL: {OBSOLETE_FIELDEDGE_URL} |" in row
    ]
    if len(obsolete_rows) != 1:
        raise ValueError(
            "Expected exactly one obsolete FieldEdge custom-form Source Map row, "
            f"found {len(obsolete_rows)}"
        )

    pricing_rows = [
        row
        for row in rows
        if row.startswith("- Claim: FieldEdge ")
        and f"| URL: {FIELDEDGE_PRICING_URL} |" in row
    ]
    if len(pricing_rows) != 1:
        raise ValueError(
            "Expected exactly one valid FieldEdge pricing Source Map row, "
            f"found {len(pricing_rows)}"
        )

    updated_source_map = source_map.replace(obsolete_rows[0], "", 1)
    updated = content[: match.start()] + updated_source_map + content[match.end() :]
    if OBSOLETE_FIELDEDGE_CLAIM in updated or OBSOLETE_FIELDEDGE_URL in updated:
        raise ValueError("Obsolete FieldEdge custom-form evidence remains in sidecar")
    if pricing_rows[0] not in updated_source_map:
        raise ValueError("Valid FieldEdge pricing Source Map row was not preserved")
    return updated


def add_correction_record(content: str) -> str:
    """Add the governed correction record before the attribution boundary."""
    next_heading = "## Live-versus-local attribution boundary"
    return replace_once(
        content,
        f"\n{next_heading}\n",
        f"\n{CORRECTION_RECORD.strip()}\n\n{next_heading}\n",
    )


def main() -> int:
    content = SOURCE.read_text(encoding="utf-8")
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    hindsight = json.loads(HINDSIGHT.read_text(encoding="utf-8"))
    customer = json.loads(CUSTOMER.read_text(encoding="utf-8"))

    simple_replacements = {
        "- Workflow date: 2026-09-24": "- Workflow date: 2026-09-25",
        "- Last-updated date: 2026-09-24": "- Last-updated date: 2026-09-25",
        "- Next review date: 2026-12-23": "- Next review date: 2026-12-24",
        "- Public metadata: `date_published: 2026-06-24`, `date_modified: 2026-09-24`, and `publisher: Simpro` are present in frontmatter.": "- Public metadata: `date_published: 2026-06-24`, `date_modified: 2026-09-25`, and `publisher: Simpro` are present in frontmatter.",
        "the 2026-09-24 revision date as original publication": "the 2026-09-25 revision date as original publication",
    }
    for old, new in simple_replacements.items():
        content = replace_once(content, old, new)

    content = add_correction_record(content)
    content = replace_once(
        content,
        "\n## Author and Schema Decision\n",
        f"\n{SEMRUSH_REUSE_AUTHORIZATION.strip()}\n\n## Author and Schema Decision\n",
    )

    dated_artifacts = (
        "context-request-best-field-service-management-software",
        "context-pack-best-field-service-management-software",
        "context-receipt-best-field-service-management-software",
        "context-refresh-best-field-service-management-software-12-tools",
        "hindsight-strategy-evidence-best-field-service-management-software",
        "editorial-plan-best-field-service-management-software",
        "context-pack-best-field-service-management-software-customer-selector",
        "context-receipt-best-field-service-management-software-customer-selector",
        "customer-proof-selector-evidence-best-field-service-management-software",
        "fred-authority-selector-evidence-best-field-service-management-software",
        "serp-evidence-best-field-service-management-software",
    )
    for stem in dated_artifacts:
        old = f"{stem}-2026-09-24"
        new = f"{stem}-2026-09-25"
        if old not in content:
            raise ValueError(f"Expected dated artifact reference is missing: {old}")
        content = content.replace(old, new)

    dynamic_lines = {
        "Current article SHA-256 at sidecar assembly": f"`{sha256(ARTICLE)}`",
        "Request canonical SHA-256": f"`{receipt['request_sha256']}`.",
        "Context pack canonical SHA-256": f"`{receipt['pack_sha256']}`.",
        "Context receipt canonical SHA-256": f"`{receipt['receipt_sha256']}`.",
        "Request file SHA-256": f"`{sha256(REQUEST)}`.",
        "Context pack file SHA-256": f"`{sha256(PACK)}`.",
        "Context receipt file SHA-256": f"`{sha256(RECEIPT)}`.",
        "Content revision": f"`{receipt['revisions']['content_revision']}`.",
        "Contract revision": f"`{receipt['revisions']['contract_revision']}`.",
        "Inventory revision": f"`{receipt['revisions']['inventory_revision']}`.",
        "Manifest revision": f"`{receipt['revisions']['manifest_revision']}`.",
        "Claim registry revision": f"`{receipt['revisions']['claim_registry_revision']}`.",
        "Approval policy revision": f"`{receipt['revisions']['approval_policy_revision']}`.",
        "Selected resources": ", ".join(
            f"`{row['resource_id']}`" for row in receipt["resources"]
        )
        + ".",
        "SERP evidence SHA-256": sha256(SERP),
    }
    for label, value in dynamic_lines.items():
        content = replace_markdown_line(content, label, value)

    old_alignment = re.search(r"^- Vault connector evidence: .*manifest_revision=.*$", content, re.MULTILINE)
    if not old_alignment:
        raise ValueError("Vault Brand Language Alignment evidence row is missing")
    alignment = old_alignment.group(0)
    alignment = re.sub(r"context_pack_hash=[0-9a-f]+", f"context_pack_hash={receipt['pack_sha256']}", alignment)
    alignment = re.sub(r"receipt_hash=[0-9a-f]+", f"receipt_hash={receipt['receipt_sha256']}", alignment)
    alignment = re.sub(r"manifest_revision=[0-9a-f]+", f"manifest_revision={receipt['revisions']['manifest_revision']}", alignment)
    content = replace_once(content, old_alignment.group(0), alignment)

    hindsight_resources = ", ".join(
        f"`{resource_id}`" for resource_id in hindsight["sidecar"]["resource_ids"]
    )
    hindsight_block = f"""
## Hindsight Strategy Selection

- Status: internal_strategy_only
- evidence_output: research/hindsight-strategy-evidence-best-field-service-management-software-2026-09-25.json
- Selected current resource IDs: {hindsight_resources}
- Pack SHA-256: `{hindsight['receipt']['pack_sha256']}`
- Receipt SHA-256: `{hindsight['receipt']['receipt_sha256']}`
- public_claim_use: prohibited
- claim_support_allowed: false
- Permitted effects: demo-test emphasis and buyer objections only.
- Google Doc discovery provenance: `ING-20260924-001`, document ID `1IIAz7beD0tqP3_zPud0pziwEYKq5q6N4LgtxwTESkoE`, normalized-text SHA-256 `5dd1185cd22e6ea9e6f912d2672dcfc53e449c818cfa247279e3dacbc7849fb4`.
- Fresh formal capture provenance: `ING-20260924-002`, capture ID `HSI-SIMPRO-20260831-8A075E9979`, period 2025-09-01 through 2026-08-31.
- Discovery boundary: the Google Doc source node records internal discovery provenance only; it does not validate every statement in the synthesis.
- Publication boundary: official vendor product and support documentation is the only authority for public competitor facts. Hindsight is not cited and does not establish product limitations, metrics, rankings, customer outcomes, or comparative claims.
- Applied decision: sharpen Jobber, Joblogic, ServiceTitan, FieldPulse, Service Fusion, and Tradify live-demo tests. Reject the internal ServiceTitan asset-history assertion because current official documentation shows equipment-level history.
- Status rationale: the strategy pack is current, de-identified, internally retrievable, article-bound, and prohibited from public claim use.
"""
    content = replace_section(
        content,
        "## Hindsight Strategy Selection",
        "## Named Feature/Add-On Link Check",
        hindsight_block.removeprefix("\n## Hindsight Strategy Selection\n"),
    )

    metric = next(row for row in customer["roles"] if row["role"] == "metric")
    no_fit = next(row for row in customer["roles"] if row["role"] == "quote")["no_fit_reason"]
    customer_body = f"""
- Selector command: `python data_sources/modules/customer_proof_selector.py "best field service management software" --title "Best Field Service Management Software: 2026 Buyer's Guide to 12 Tools" --objective "Help US trade and field-service leaders build a fast, defensible 12-tool shortlist by business type, operating fit, workflow depth, implementation risk, and role needs." --context-pack "research/context-pack-best-field-service-management-software-customer-selector-2026-09-25.json" --context-receipt "research/context-receipt-best-field-service-management-software-customer-selector-2026-09-25.json" --evidence-output "research/customer-proof-selector-evidence-best-field-service-management-software-2026-09-25.json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10 --allow-no-proof --selected "metric=none" --reject "metric=case-study-teamwired:single-customer invoicing metric does not improve a neutral twelve-vendor buyer-routing objective"`
- Selector evidence: research/customer-proof-selector-evidence-best-field-service-management-software-2026-09-25.json | SHA-256: {sha256(CUSTOMER)}
- Context receipt: research/context-receipt-best-field-service-management-software-customer-selector-2026-09-25.json
- Approval source: connector_claim_result
- Selection outcome: customer_proof_candidates_available
- Role: metric | Top candidates: [case-study-teamwired] | Selected: [none] | Claim IDs: [claim-metric-MET-1482] | Receipt revision: {metric['receipt_revision']} | Rejected stronger candidates: [case-study-teamwired: single-customer invoicing metric does not improve a neutral twelve-vendor buyer-routing objective]
- Role: quote | Top candidates: [none] | Selected: [none] | Claim IDs: [none] | Receipt revision: not available | Rejected stronger candidates: [none]
  - No-fit reason: {no_fit}
- Role: theme | Top candidates: [none] | Selected: [none] | Claim IDs: [none] | Receipt revision: not available | Rejected stronger candidates: [none]
  - No-fit reason: {no_fit}
- Role: experience_story | Top candidates: [none] | Selected: [none] | Claim IDs: [none] | Receipt revision: not available | Rejected stronger candidates: [none: no eligible candidate exists for this article objective or any vendor section]
  - No-fit reason: {no_fit}
- Selection decision: TEAMWired was evaluated for the metric role and explicitly rejected because its single-customer invoicing metric does not improve a neutral twelve-vendor buyer-routing objective.
- Public-copy result: omit customer stories, customer metrics, testimonials, review stories, exact quotes, and customer outcomes.
- Objective-binding note: the selector evidence is bound to the exact current objective and to selector-specific context artifacts. The final public-copy context pack intentionally contains no approved claims because no customer proof was selected for public use.
"""
    content = replace_section(content, "## Customer Proof Slate", "## Fred Voccola Authority Selection", customer_body)
    fred_section = FRED.read_text(encoding="utf-8").strip()
    content = replace_full_section(
        content,
        "## Fred Voccola Authority Selection",
        "## E-E-A-T Strength Decision",
        fred_section,
    )

    content = remove_obsolete_fieldedge_source_row(content)

    resource_ids = [row["resource_id"] for row in receipt["resources"]]
    context_binding = {
        "approval_policy_revision": receipt["revisions"]["approval_policy_revision"],
        "article": {
            "file": ARTICLE.name,
            "sha256": sha256(ARTICLE),
        },
        "claim_registry_revision": receipt["revisions"]["claim_registry_revision"],
        "pack": {
            "canonical_sha256": receipt["pack_sha256"],
            "file": PACK.name,
            "schema": pack["schema"],
            "sha256": sha256(PACK),
        },
        "receipt": {
            "canonical_sha256": receipt["receipt_sha256"],
            "file": RECEIPT.name,
            "schema": receipt["schema"],
            "sha256": sha256(RECEIPT),
        },
        "repo_context": [],
        "request": {
            "file": REQUEST.name,
            "sha256": sha256(REQUEST),
        },
        "resource_ids": resource_ids,
        "revisions": receipt["revisions"],
        "schema": "seomachine-context-binding/v1",
        "task_satisfaction": receipt["task_satisfaction"],
        "unresolved_gaps": receipt["unresolved_gaps"],
    }
    context_binding_section = (
        "## Context Binding\n\n```json\n"
        + json.dumps(context_binding, indent=2, ensure_ascii=False)
        + "\n```"
    )
    content = replace_full_section(
        content,
        "## Context Binding",
        "## Context Claim Use Map",
        context_binding_section,
    )

    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    print(f"wrote {OUTPUT.relative_to(ROOT).as_posix()} ({len(content)} characters)")
    print(f"article_sha256={sha256(ARTICLE)}")
    print(f"sidecar_sha256={sha256(OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
