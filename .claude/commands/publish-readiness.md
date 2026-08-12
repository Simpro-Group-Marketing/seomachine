# Publish Readiness Command

Run the complete publish-readiness gate stack for a blog draft, rewrite, or published article artifact.

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

When `author_policy.status` is `not_provided`, first-person singular author judgment outside quotes is prohibited.

## Usage

Blog readiness is never a one-pass invocation. Use the exact Python build -> preflight -> finalize -> final lifecycle below. Non-readiness callers may still resolve nullable artifact kinds, but readiness must use strict identity and an explicit phase.

## Two-Phase Blog Seal

For every new or changed blog, use this exact order after final source artifacts and closed stage receipts exist. The `build` command below is schematic: add the applicable connector/proof paths and repeat `--stage-receipt` for every closed stage.

Tool-emitted machine artifacts carry an `execution_attestation`, a keyed local execution-integrity attestation. Require it on every `simpro-blog-stage-receipt/v1`, verified `simpro-serp-evidence/v1`, nested `simpro-answersocrates-run-receipt/v1`, `simpro-source-classification/v1`, and `simpro-source-capture-receipt/v1`. Readiness verifies the attestation and canonical hash; a handwritten or merely rehashed replacement does not qualify. This local control does not provide a remote/provider signature and does not prove that external observations are true, so source metadata, visible evidence, freshness, PAA eligibility, and semantic claim fit still require validation. A rewrite's dedicated pre-picked PAA brief section remains path/hash-bound and takes precedence over AnswerSocrates.

```powershell
python data_sources/modules/blog_assembly_bom.py build "[article]" --validation-sidecar "[sidecar]" --editorial-plan "[editorial-plan]" --serp-evidence "[serp-evidence]" --paa-artifact "[paa-artifact]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --customer-proof-selector-evidence "[selector-evidence]" --fred-authority-evidence "[fred-evidence]" --stage-receipt "[closed-stage-receipt]" --workflow-mode "[new|rewrite]" --assembly-date "[YYYY-MM-DD]" --output "[provisional-bom]"
python data_sources/modules/publish_readiness.py "[article]" --proof-sidecar "[sidecar]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --assembly-bom "[provisional-bom]" --phase preflight --output "[preflight-readiness]"
python data_sources/modules/blog_assembly_bom.py finalize --bom "[provisional-bom]" --preflight-readiness "[preflight-readiness]" --output "[final-bom]"
python data_sources/modules/publish_readiness.py "[article]" --proof-sidecar "[sidecar]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --assembly-bom "[final-bom]" --phase final --output "[final-readiness-attestation]" --stage-receipt-output "[final-readiness-stage-receipt]"
```

For a blog the shared applicability guard classifies as non-connector, first emit its Context Binding receipt with `context_binding_generator.py --not-applicable-reason "Final article contains no Simpro brand, URL, or connector-sensitive language."`, using the same stage, run ID, predecessor, and output receipt paths as the connector branch. Omit context request/pack/receipt, customer-proof selector, and Fred arguments from BOM build, and omit context request/pack/receipt from both readiness runs. This is derived from the final article and cannot override Simpro branding, official or schemeless Simpro URLs, or connector-sensitive language.

Preflight accepts only a valid provisional BOM. A failed preflight cannot finalize. Final readiness accepts only the final BOM, reruns every gate, and writes a detached final-readiness attestation that contains the final BOM hash and all final input hashes. It is not hashed back into the BOM. Readiness JSON declares `verification_scope: source_artifact`; it does not claim CMS or rendered-page verification.

Keep every preflight-bound provisional BOM immutable. Use `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json` for the initial provisional BOM and finalize out of place to `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-final.json`. After a recorded optimization, build the new provisional BOM at `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization.json` and finalize it out of place to `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization-final.json`. Do not overwrite the BOM referenced by the prior preflight. Each preflight result must retain the exact BOM path and hash that it validated.

When the preflight output is `research/preflight-readiness-[topic-slug]-[YYYY-MM-DD].json`, the runner automatically emits `research/preflight-readiness-[topic-slug]-[YYYY-MM-DD]-stage-receipt.json`. Preflight rejects a custom stage-receipt destination.

## Command Contract

This is the user-facing publish gate command. The agent executing `/publish-readiness` must run the repo publish-readiness runner internally and report the gate summary, content score, AEO/GEO score, and priority fixes. Do not ask the user to call the Python runner manually.

Strict artifact identity is the first `/publish-readiness` gate. Missing, unsupported, or contradictory blog/landing-page identity fails before Context Binding. Context Binding follows for Simpro artifacts, then Blog Assembly BOM validation. Missing, stale, tampered, unsupported, or mismatched request, pack, receipt, sidecar bindings, BOM inventory, author policy, schema policy, research evidence, or hard-coded vault topology strings stop readiness before downstream proof gates or scoring. Explicit non-Simpro artifacts with no Simpro claims or URLs do not require a Simpro context pack.

Use this command before `/optimize`, after `/optimize`, before an Asana intake handoff, and before moving an article into `published/`.

## Required Inputs

- Article artifact path
- Validation sidecar path
- Current context request, `simpro-product-context-pack/v2`, and `simpro-context-receipt/v1` paths for Simpro artifacts
- Editorial plan, verified SERP evidence, bound PAA/brief/CSV/blocker evidence, and closed stage receipts; customer-proof selector and Fred evidence are additionally required when connector-bound
- Provisional or final blog assembly BOM path, `simpro-blog-assembly-bom/v1`, as required by the selected phase, for every blog artifact

Vault product-language gate: When the article uses Simpro product, feature, add-on, solution, industry, or related Simpro product URL language, `/publish-readiness` runs `vault_brand_language_guard.py`. The validation sidecar must contain `Vault Brand Language Alignment` with connector evidence, `context_pack_hash`, `receipt_hash`, relevant `resource_id` values, feature-specific `resource_id` evidence when named features/add-ons appear, solution or vertical `resource_id` evidence when solution/industry language appears, any required `claim_id` values, language applied, fallback context use, source-verification boundary, and `Status: aligned`. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

Source policy enforcement: Context Binding plus claim-specific gates enforce connector-first evidence for brand voice, audience, ICP, message pillars, tone, Customer proof, quotes, metrics, review stories, approval status, product, feature, add-on, solution, industry, Lightning, competitor, Hindsight, and public factual or statistical claims. SEO mechanics, AEO/GEO workflow, schema notes, publish gates, internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples, and style mechanics may use repo `context/` under the routing matrix. No duplicate routing sidecar block is required.

### General Source Support Classes

The only general source-map classes are `primary_authority`, `independent_research`, `non_competing_expert`, `owned_product`, `customer_proof`, `review_platform`, and `competitor`. General causal, comparative, definitional, process, and recommendation claims require a claim-fit row. Duplicate or weak URLs cannot satisfy authority by increasing link count.

### Schema And Author Conditionals

Always require BlogPosting, BreadcrumbList, ImageObject for the featured image or logo, and Organization as publisher reference only, not a separate full schema block. `FAQPage` and `Question and Answer inside FAQPage` are required only when visible FAQs exist. `Person as author` is required only when a named author exists. Require `VideoObject` if and only if a verified video embed exists. If a named author is present, include `author` in frontmatter. If no named author is available, omit `author`, omit `Person as author`, and record that decision in the BOM and validation sidecar.

Named feature gate: When public copy names Lightning, RAIN, a current role agent, Intelligent AI Scheduler, or a roadmap specialist, `/publish-readiness` runs `named_feature_status_guard.py`. The validation sidecar must contain exactly one row per detected name under `Named Feature Status and Commercial Treatment`, using the current vault claim IDs, allowed release status, allowed commercial treatment, region or account boundary, and public wording decision. The gate is reported as `Named Feature Status`.

The validation sidecar should live at:

```text
research/validation-[topic-slug]-[YYYY-MM-DD].md
```

## Gate Stack

The command runs the complete publish-readiness stack. FAQ-specific gates are conditional: run them only when visible FAQs exist; otherwise they are `not_applicable` and their scoring weights leave the denominator.

1. `artifact_identity`
2. `context_binding_guard`
3. `blog_assembly_bom_guard`
4. `public_artifact_guard`
5. `ai_copy_linter`
6. `url_validator`
7. `public_research_link_guard`
8. `metric_proof_pack_guard`
9. `numeric_claim_source_guard`
10. `faq_answer_quality_guard.py` when visible FAQs exist
11. `faq_proof_guard` when visible FAQs exist
12. `paa_provenance_guard`
13. `source_support_guard`
14. `customer_proof_diversity_guard`
15. `review_story_identity_guard`
16. `early_artifact_guard`
17. `answer_withholding_guard`
18. `vault_brand_language_guard`
19. `named_feature_status` via `named_feature_status_guard.py`
20. `fred_authority` via `fred_authority_guard.py`
21. `content_scorer` for consolidated quality and AEO/GEO scoring; URL and source-support gates are reused rather than requested twice

The blocking `fred_authority` gate passes the validation sidecar to `fred_authority_guard.py`. It requires a complete `Fred Voccola Authority Selection` evaluation for every new or changed Simpro blog and for existing content when next rewritten, optimized, or passed through publish readiness. A selector or vault failure remains blocked; public Fred use is optional and receives no AEO/E-E-A-T credit merely because the internal block exists.

PAA and FAQ policy: every new article requires a structured AnswerSocrates artifact. For a rewrite, PAA pre-picked in a dedicated brief section takes precedence; use those exact questions as visible FAQ headings. A rewrite without that section requires AnswerSocrates. A user CSV is permitted only with a saved AnswerSocrates artifact recording a genuine blocked state: login, CAPTCHA, quota, or unavailability. SERP, Reddit, and YouTube are supplemental research and cannot satisfy PAA provenance. Record `FAQ policy: required | not_applicable`; `not_applicable` requires a non-empty rationale.

When visible FAQs exist, every answer must use a 40-60 word first paragraph and lead with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Generic deflections block the FAQ answer-quality gate. The FAQ proof gate separately requires at least 1 authoritative non-owned public evidence link inside each visible FAQ answer; a Source Map or FAQ Proof Map cannot replace that link, so sidecar-only proof does not pass.

FAQ Source Policy: Gate 8 receives the proof sidecar and requires one exact `FAQ Proof Map` row for each visible non-owned FAQ URL: `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`. The only allowed classes are `neutral` and `non_competing_expert`. Competitor-owned FAQ sources: prohibited. Simpro-owned links remain supplemental and cannot satisfy the non-owned proof requirement; reframe or remove vendor-specific FAQs without compliant evidence.


403 replacement rule: If a DOL, Capterra, G2, Trustpilot, Google Play, or other public research/source URL returns 401, 403, or `manual_review`, do not remove the citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. Source Map notes must document both the rejected 403 URL and the replacement URL. The `public_research_link_guard` blocks sidecar-only handling of public research, compliance, legal, regulatory, or statistical proof and requires visible resolved non-owned public research links in the relevant article section or FAQ answer. Full policy lives in `context/aeo-geo-blog-strategy.md`.

## AEO/GEO Recovery Loop

An AEO/GEO score below 90/100 is a repair trigger, not a reporting endpoint. Unless the user explicitly requested a read-only audit, the LLM must continue in the same workflow:

1. Review every failed check in `aeo_geo.checks` and the scorer's `priority_fixes`.
2. Classify each failure as a public-copy gap, validation-sidecar/proof gap, or scorer or parser false negative.
3. If the article visibly satisfies the written requirement but scoring misses it, add a regression test and fix the scorer or parser false negative. Do not distort accurate, brief-approved copy to satisfy brittle matching.
4. Apply the top 3-5 fixes that address root causes. Do not invent PAA questions, claims, proof, metrics, quotes, or customer experience to gain points.
5. Treat every edit as a mutation. Rerun `/scrub` and Context Binding, rebuild the provisional BOM, run preflight, finalize only after it passes, then run detached final readiness using the Two-Phase Blog Seal sequence above.
6. Repeat once if needed. If AEO/GEO remains below 90/100 after 2 iterations, route the artifact to `review-required/` with the score, failed checks, attempted fixes, and any external evidence or authority blocker.

`/optimize` is allowed inside this recovery loop when all proof, source, URL, and public-artifact gates pass but content quality or AEO/GEO does not. Final handoff still requires content quality of at least 85/100, AEO/GEO of at least 90/100, and every blocking gate to pass.

## Output

Return:

- Overall pass/fail
- One row per gate
- Error and warning counts
- Content score out of 100, its 85-point threshold, and pass/fail status
- AEO/GEO score out of 100, its 90-point threshold, and pass/fail status
- Priority fixes
- Whether the artifact is ready for `/optimize`, handoff, or `published/`

If the command fails, fix the highest-severity gate first and rerun `/publish-readiness`.

AI copy lint failures include copy avoid-rule errors. The Simpro web-copy linter blocks modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences before publish readiness can pass.

Simpro web copy rules still apply during recovery: Use numerals for cardinal numbers, including 1-9. Do not block source-visible metric wording when a public proof source spells out the number; preserve the supported claim wording and rely on Metric Proof Pack, numeric claim source guard, and source support guard for proof. Because comma decisions are grammar/context dependent. No comma when the because clause is essential to the sentence meaning. Use a comma when the because clause is nonessential, contrastive, or needed to prevent misreading. Review negative constructions carefully because comma placement can change meaning. When `/publish-readiness` fails, the agent must revise the sentence and rerun the command instead of treating `because` punctuation as a passive warning.
