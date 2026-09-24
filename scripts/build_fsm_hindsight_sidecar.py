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
SOURCE = RESEARCH / "validation-best-field-service-management-software-2026-09-22.md"
OUTPUT = RESEARCH / "validation-best-field-service-management-software-2026-09-24.md"
ARTICLE = ROOT / "rewrites" / "best-field-service-management-software-rewrite-2026-08-28.md"
REQUEST = RESEARCH / "context-request-best-field-service-management-software-2026-09-24.json"
PACK = RESEARCH / "context-pack-best-field-service-management-software-2026-09-24.json"
RECEIPT = RESEARCH / "context-receipt-best-field-service-management-software-2026-09-24.json"
HINDSIGHT = RESEARCH / "hindsight-strategy-evidence-best-field-service-management-software-2026-09-24.json"
CUSTOMER = RESEARCH / "customer-proof-selector-evidence-best-field-service-management-software-2026-09-24.json"
FRED = RESEARCH / "fred-authority-selector-evidence-best-field-service-management-software-2026-09-24.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(content: str, old: str, new: str) -> str:
    count = content.count(old)
    if count != 1:
        raise ValueError(f"Expected one occurrence, found {count}: {old[:100]!r}")
    return content.replace(old, new, 1)


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


def main() -> int:
    content = SOURCE.read_text(encoding="utf-8")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    hindsight = json.loads(HINDSIGHT.read_text(encoding="utf-8"))
    customer = json.loads(CUSTOMER.read_text(encoding="utf-8"))

    simple_replacements = {
        "- Workflow date: 2026-09-23": "- Workflow date: 2026-09-24",
        "- Current article SHA-256 at sidecar assembly: `5de5ab0959b3bc5175efef1f828f4a5ca39b3f3a2532a0857bde06ef6751110f`": f"- Current article SHA-256 at sidecar assembly: `{sha256(ARTICLE)}`",
        "- Context request: `research/context-request-best-field-service-management-software.json`": "- Context request: `research/context-request-best-field-service-management-software-2026-09-24.json`",
        "- Context pack: `research/context-pack-best-field-service-management-software.json`": "- Context pack: `research/context-pack-best-field-service-management-software-2026-09-24.json`",
        "- Context receipt: `research/context-receipt-best-field-service-management-software.json`": "- Context receipt: `research/context-receipt-best-field-service-management-software-2026-09-24.json`",
        "- Context trace: `research/context-refresh-best-field-service-management-software-12-tools-2026-09-22.json`": "- Context trace: `research/context-refresh-best-field-service-management-software-12-tools-2026-09-24.json`\n- Hindsight strategy evidence: `research/hindsight-strategy-evidence-best-field-service-management-software-2026-09-24.json`",
        "- Frozen editorial plan: `research/editorial-plan-best-field-service-management-software-2026-09-22.json`": "- Frozen editorial plan: `research/editorial-plan-best-field-service-management-software-2026-09-24.json`",
        "- Request canonical SHA-256: `ed86f145bbc077ada7edd27efce0e0611b855352c9286ae09d66251e56bf88ad`.": f"- Request canonical SHA-256: `{receipt['request_sha256']}`.",
        "- Context pack canonical SHA-256: `a354651eaed8f26c79aabf94698b2ff18c1956d5983851e47c45e3870c9cf418`.": f"- Context pack canonical SHA-256: `{receipt['pack_sha256']}`.",
        "- Context receipt canonical SHA-256: `2771da4fac69983bd7e3cb28a49803d456fab135b18336b58682f17533570a75`.": f"- Context receipt canonical SHA-256: `{receipt['receipt_sha256']}`.",
        "- Request file SHA-256: `1c69c6b6f879cec2b991c790d00562472a8b6b8613fe84b58b65d04a551867b3`.": f"- Request file SHA-256: `{sha256(REQUEST)}`.",
        "- Context pack file SHA-256: `8a4e4528acad8fea7020b67267100aeca63a7cde13082b83bd9971254229708a`.": f"- Context pack file SHA-256: `{sha256(PACK)}`.",
        "- Context receipt file SHA-256: `3c22ad5dde9c9cc3bbce414df2634992944e1e8c118eddde6a81dbd71cae5fc8`.": f"- Context receipt file SHA-256: `{sha256(RECEIPT)}`.",
        "- Content revision: `2b0fbff2335f086cc578aa92da8672dff6d2ac3098e796c6a96bb3b3cc213f25`.": f"- Content revision: `{receipt['revisions']['content_revision']}`.",
        "- Inventory revision: `374bdf14a4519293e50d7e1c5b7e886daece33e303c8ce087e77658244faf446`.": f"- Inventory revision: `{receipt['revisions']['inventory_revision']}`.",
        "- Manifest revision: `94dd66e9dfd6130fa8c1472c11df650d1b9e6590762409e61a9a89a3d15930c2`.": f"- Manifest revision: `{receipt['revisions']['manifest_revision']}`.",
        "- Active artifacts: `research/context-request-best-field-service-management-software.json`, `research/context-pack-best-field-service-management-software.json`, and `research/context-receipt-best-field-service-management-software.json`.": "- Active artifacts: `research/context-request-best-field-service-management-software-2026-09-24.json`, `research/context-pack-best-field-service-management-software-2026-09-24.json`, and `research/context-receipt-best-field-service-management-software-2026-09-24.json`.",
        "- Last-updated date: 2026-09-23": "- Last-updated date: 2026-09-24",
        "- Next review date: 2026-12-22": "- Next review date: 2026-12-23",
        "- Public metadata: `date_published: 2026-06-24`, `date_modified: 2026-09-23`, and `publisher: Simpro` are present in frontmatter.": "- Public metadata: `date_published: 2026-06-24`, `date_modified: 2026-09-24`, and `publisher: Simpro` are present in frontmatter.",
        "- Final article snapshot: Flesch Reading Ease 51.9, Flesch-Kincaid grade 9.3, rhythm 62, zero paragraphs above four sentences, and readability score 90.": "- Final article snapshot: Flesch Reading Ease 50.9, Flesch-Kincaid grade 9.5, rhythm 62, zero paragraphs above four sentences, and readability score 90.",
        "- SERP evidence artifact: research/serp-evidence-best-field-service-management-software-2026-09-23.json": "- SERP evidence artifact: research/serp-evidence-best-field-service-management-software-2026-09-24.json",
        "- Semrush lane: available: the current US keyword decision was captured in the main Chrome Semrush UI on 2026-09-23 and is recorded in research/semrush-keyword-decision-best-field-service-management-software-2026-09-23.json.": "- Semrush lane: available: the current US keyword decision was captured in the main Chrome Semrush UI on 2026-09-24 and is recorded in research/semrush-keyword-decision-best-field-service-management-software-2026-09-24.json.",
        "the 2026-09-23 revision date as original publication": "the 2026-09-24 revision date as original publication",
        "- SERP evidence SHA-256: 427c428075e353f2002dcfb7cf72c09b3c82f93f07981156744a44bbd3db2e6b": "- SERP evidence SHA-256: 9caf7f8150bd5d33392d7edfe16dc0506976fbec22523f3375a7330d563d2c35",
    }
    for old, new in simple_replacements.items():
        content = replace_once(content, old, new)

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
- evidence_output: research/hindsight-strategy-evidence-best-field-service-management-software-2026-09-24.json
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
- Applied decision: sharpen Jobber, Joblogic, FieldEdge, ServiceTitan, FieldPulse, Service Fusion, and Tradify live-demo tests. Reject the internal ServiceTitan asset-history assertion because current official documentation shows equipment-level history.
- Status rationale: the strategy pack is current, de-identified, internally retrievable, article-bound, and prohibited from public claim use.
"""
    content = replace_once(
        content,
        "\n## Named Feature/Add-On Link Check\n",
        f"\n{hindsight_block.strip()}\n\n## Named Feature/Add-On Link Check\n",
    )

    metric = next(row for row in customer["roles"] if row["role"] == "metric")
    no_fit = next(row for row in customer["roles"] if row["role"] == "quote")["no_fit_reason"]
    customer_body = f"""
- Selector command: `python data_sources/modules/customer_proof_selector.py "best field service management software" --title "Best Field Service Management Software: 2026 Buyer's Guide to 12 Tools" --objective "Help US trade and field-service leaders build a fast, defensible 12-tool shortlist by business type, operating fit, workflow depth, implementation risk, and role needs." --context-pack "research/context-pack-best-field-service-management-software-customer-selector-2026-09-24.json" --context-receipt "research/context-receipt-best-field-service-management-software-customer-selector-2026-09-24.json" --evidence-output "research/customer-proof-selector-evidence-best-field-service-management-software-2026-09-24.json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10 --allow-no-proof --selected "metric=none" --reject "metric=case-study-teamwired:single-customer invoicing metric does not improve a neutral twelve-vendor buyer-routing objective"`
- Selector evidence: research/customer-proof-selector-evidence-best-field-service-management-software-2026-09-24.json | SHA-256: {sha256(CUSTOMER)}
- Context receipt: research/context-receipt-best-field-service-management-software-customer-selector-2026-09-24.json
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

    source_rows = """
- Claim: Jobber's job-costing view includes labor, material or line-item costs, expenses, profit, and margin, and current access depends on plan. | Claim type: product_status | URL: https://www.getjobber.com/features/job-costing-software/ | Evidence: the official Jobber product page describes labor, material, expense, profit, margin, and job-profitability reporting, and links buyers to current plan selection. | Source class: competitor_owned | Original-source status: original | Source date: undated | Checked date: 2026-09-24 | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: the live product page is undated, so approval is limited to the page state checked on 2026-09-24. | Status: approved | Intended use: Jobber demo test and quoted-plan check | Citation mode: inline_required
- Claim: Joblogic projects can be divided into phases for separate work and billing control. | Claim type: product_status | URL: https://support.joblogic.com/docs/adding-a-project | Evidence: the official Joblogic support page describes adding a project and using project phases. | Source class: competitor_owned | Original-source status: original | Source date: 2026-07-29 | Checked date: 2026-09-24 | Claim fit: direct | Freshness decision: current | Freshness reason: the dated support article remains within the high-volatility 90-day review window. | Status: approved | Intended use: Joblogic phased-project demo test | Citation mode: inline_required
- Claim: Joblogic's current project workflow includes variation controls that should be tested with staged payments, retention, and final invoicing. | Claim type: product_status | URL: https://support.joblogic.com/docs/joblogic-release-20th-august-2026 | Evidence: the official Joblogic release documentation describes current project variation controls; staged-payment and retention behavior remain live-demo checks rather than asserted outcomes. | Source class: competitor_owned | Original-source status: original | Source date: 2026-08-28 | Checked date: 2026-09-24 | Claim fit: direct | Freshness decision: current | Freshness reason: the official release article is less than one month old. | Status: approved | Intended use: Joblogic variations link and broader project test | Citation mode: inline_required
- Claim: FieldEdge offers custom forms and templates that can be used for a failed-inspection demonstration. | Claim type: product_status | URL: https://fieldedge.com/field-service-software/ | Evidence: the current official FieldEdge product page presents custom forms and templates; follow-up tasks, office notices, customer messages, and audit trails remain buyer tests rather than product claims. | Source class: competitor_owned | Original-source status: original | Source date: undated | Checked date: 2026-09-24 | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: the live product page is undated, so approval is limited to the page state checked on 2026-09-24. | Status: approved | Intended use: FieldEdge custom-form link and failed-inspection test | Citation mode: inline_required
- Claim: ServiceTitan supports equipment-level history for individual physical equipment, including service activity that can be traced across visits. | Claim type: product_status | URL: https://help.servicetitan.com/docs/view-equipment-history-in-fma | Evidence: the official ServiceTitan help page documents viewing equipment history and related activity at the equipment level. | Source class: competitor_owned | Original-source status: original | Source date: 2026-04-07 | Checked date: 2026-09-24 | Claim fit: direct | Freshness decision: current | Freshness reason: the official support article is current within the 2026 product year and was checked against the live page. | Status: approved | Intended use: ServiceTitan equipment-history demo test and explicit rejection of the unsupported no-individual-asset-history assertion | Citation mode: inline_required
- Claim: ServiceTitan mobile supports forms associated with equipment. | Claim type: product_status | URL: https://help.servicetitan.com/docs/manage-forms-for-equipment-in-servicetitan-mobile | Evidence: the official ServiceTitan mobile help page documents managing forms for equipment. | Source class: competitor_owned | Original-source status: original | Source date: 2026-05-27 | Checked date: 2026-09-24 | Claim fit: direct | Freshness decision: current | Freshness reason: the official support article is current within the 2026 product year and was checked against the live page. | Status: approved | Intended use: ServiceTitan equipment forms within the live demo test | Citation mode: section_source_allowed
- Claim: FieldPulse provides current QuickBooks integration routes for representative invoice and payment testing. | Claim type: product_status | URL: https://www.fieldpulse.com/company/partners/quickbooks | Evidence: the current official FieldPulse partner page describes supported QuickBooks integration workflows; reconciliation, duplicate prevention, and error recovery remain buyer tests rather than reliability claims. | Source class: competitor_owned | Original-source status: original | Source date: undated | Checked date: 2026-09-24 | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: the live partner page is undated, so approval is limited to the page state checked on 2026-09-24. | Status: approved | Intended use: FieldPulse QuickBooks-edition link and sync test | Citation mode: inline_required
- Claim: Service Fusion documents purchase orders and inventory orders for receiving and stock-flow testing. | Claim type: product_status | URL: https://servicefusion.zendesk.com/hc/en-us/articles/360032125951-Purchase-Orders-and-Inventory-Orders | Evidence: the official Service Fusion support article documents purchase orders and inventory orders; warehouse-to-truck movement, job consumption, reconciliation, and low-stock behavior remain buyer tests rather than deficiency claims. | Source class: competitor_owned | Original-source status: original | Source date: 2023-12-28 | Checked date: 2026-09-24 | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: the support article is older than the 90-day product-status window, so the copy links to the current live page and frames the workflow as a live verification test. | Status: approved | Intended use: Service Fusion parts-receiving link and inventory test | Citation mode: inline_required
- Claim: Tradify's web console and mobile app depend on a live internet connection. | Claim type: product_status | URL: https://help.tradifyhq.com/hc/en-us/articles/360026848353-Does-Tradify-Work-Offline | Evidence: the official Tradify support page states that both the web console and mobile app depend on a live internet connection; the disqualifying treatment is buyer guidance for crews that must work without signal. | Source class: competitor_owned | Original-source status: original | Source date: 2024-08-05 | Checked date: 2026-09-24 | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: the official support article is older than the 90-day product-status window but remains the current live vendor statement; the claim must be rechecked before the scheduled review. | Status: approved | Intended use: Tradify mismatch and no-signal pass-or-fail test | Citation mode: inline_required
""".strip()
    content = replace_once(
        content,
        "\n## Search Intent and Format Decision\n",
        f"\n{source_rows}\n\n## Search Intent and Format Decision\n",
    )

    OUTPUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT).as_posix()} ({len(content)} characters)")
    print(f"article_sha256={sha256(ARTICLE)}")
    print(f"sidecar_sha256={sha256(OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
