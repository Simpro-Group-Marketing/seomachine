# Publish Readiness Command

Run the complete publish-readiness gate stack for a blog draft, rewrite, or published article artifact.

For every Simpro blog, read `wiki/messaging/Voice and Tone.md` and `wiki/messaging/Tone Voice and Localization Rules.md` from the vault. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

## Usage

```text
/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

Examples:

```text
/publish-readiness rewrites/hvac-ppc-rewrite-2026-06-17.md --proof-sidecar research/validation-hvac-ppc-2026-06-17.md
/publish-readiness published/best-job-quoting-and-invoicing-software-for-field-service-businesses-2026-06-12.md --proof-sidecar research/validation-best-job-quoting-and-invoicing-software-for-field-service-businesses-2026-06-12.md
```

## Command Contract

This is the user-facing publish gate command. The agent executing `/publish-readiness` must run the repo publish-readiness runner internally and report the gate summary, content score, AEO/GEO score, and priority fixes. Do not ask the user to call the Python runner manually.

Use this command before `/optimize`, after `/optimize`, before an Asana intake handoff, and before moving an article into `published/`.

## Required Inputs

- Article artifact path
- Validation sidecar path

Vault product-language gate: When the article uses Simpro product, feature, add-on, solution, industry, or related Simpro product URL language, `/publish-readiness` runs `vault_brand_language_guard.py`. The validation sidecar must contain `Vault Brand Language Alignment` with `wiki/messaging/Simpro Core Messaging Repository.md`, `wiki/messaging/Message House.md`, `wiki/messaging/Core Value Pillars.md`, `wiki/product/Product Positioning.md`, `wiki/features/Feature Library.md`, any needed `wiki/features/source-docs/` route, `wiki/verticals/Vertical Profile Library.md` for solution/industry language, and `Status: aligned`. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

Source routing gate: For Simpro articles, `/publish-readiness` runs `source_routing_guard.py`. The validation sidecar must contain `Source Routing Decision` with `Vault-sourced data types`, `Repo-context-sourced data types`, `Vault routes checked`, `Repo context files checked`, `Fallback context use`, `Conflicts found`, and `Status: aligned`. Brand voice, audience, ICP, message pillars, tone, Customer proof, quotes, metrics, review stories, approval status, product, feature, add-on, solution, industry, Lightning, competitor, Hindsight, and public factual/statistical claims cannot use repo context as the primary authority. SEO mechanics, AEO/GEO workflow, schema notes, publish gates, internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples, and style mechanics may route through repo `context/`.

Named feature gate: When public copy names Lightning, RAIN, a current role agent, Intelligent AI Scheduler, or a roadmap specialist, `/publish-readiness` runs `named_feature_status_guard.py`. The validation sidecar must contain exactly one row per detected name under `Named Feature Status and Commercial Treatment`, using the current vault claim IDs, allowed release status, allowed commercial treatment, region or account boundary, and public wording decision. The gate is reported as `Named Feature Status`.

The validation sidecar should live at:

```text
research/validation-[topic-slug]-[YYYY-MM-DD].md
```

## Gate Stack

The command runs the complete publish-readiness stack:

1. `public_artifact_guard`
2. `ai_copy_linter`
3. `url_validator`
4. `public_research_link_guard`
5. `metric_proof_pack_guard`
6. `numeric_claim_source_guard`
7. `faq_answer_quality_guard.py`
8. `faq_proof_guard`
9. `paa_provenance_guard`
10. `source_support_guard`
11. `customer_proof_diversity_guard`
12. `review_story_identity_guard`
13. `early_artifact_guard`
14. `answer_withholding_guard`
15. `vault_brand_language_guard`
16. `named_feature_status` via `named_feature_status_guard.py`
17. `source_routing_guard`
18. `fred_authority` via `fred_authority_guard.py`
19. `content_scorer` with URL and source-support validation

The blocking `fred_authority` gate passes the validation sidecar to `fred_authority_guard.py`. It requires a complete `Fred Voccola Authority Selection` evaluation for every new or changed Simpro blog and for existing content when next rewritten, optimized, or passed through publish readiness. A selector or vault failure remains blocked; public Fred use is optional and receives no AEO/E-E-A-T credit merely because the internal block exists.

FAQ answer-quality rule: every FAQ must use a 40-60 word first paragraph and lead with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Generic deflections block gate 7. Gate 8 separately requires at least 1 authoritative non-owned public evidence link inside each visible FAQ answer; a Source Map or FAQ Proof Map cannot replace that link, so sidecar-only proof does not pass.

FAQ Source Policy: Gate 8 receives the proof sidecar and requires one exact `FAQ Proof Map` row for each visible non-owned FAQ URL: `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`. The only allowed classes are `neutral` and `non_competing_expert`. Competitor-owned FAQ sources: prohibited. Simpro-owned links remain supplemental and cannot satisfy the non-owned proof requirement; reframe or remove vendor-specific FAQs without compliant evidence.


403 replacement rule: If a DOL, Capterra, G2, Trustpilot, Google Play, or other public research/source URL returns 401, 403, or `manual_review`, do not remove the citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. Source Map notes must document both the rejected 403 URL and the replacement URL. The `public_research_link_guard` blocks sidecar-only handling of public research, compliance, legal, regulatory, or statistical proof and requires visible resolved non-owned public research links in the relevant article section or FAQ answer. Full policy lives in `context/aeo-geo-blog-strategy.md`.

## Output

Return:

- Overall pass/fail
- One row per gate
- Error and warning counts
- Content score
- AEO/GEO score
- Priority fixes
- Whether the artifact is ready for `/optimize`, handoff, or `published/`

If the command fails, fix the highest-severity gate first and rerun `/publish-readiness`.

AI copy lint failures include copy avoid-rule errors. The Simpro web-copy linter blocks modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences before publish readiness can pass.

Simpro web copy rules still apply during recovery: Use numerals for cardinal numbers, including 1-9. Do not block source-visible metric wording when a public proof source spells out the number; preserve the supported claim wording and rely on Metric Proof Pack, numeric claim source guard, and source support guard for proof. Because comma decisions are grammar/context dependent. No comma when the because clause is essential to the sentence meaning. Use a comma when the because clause is nonessential, contrastive, or needed to prevent misreading. Review negative constructions carefully because comma placement can change meaning. When `/publish-readiness` fails, the agent must revise the sentence and rerun the command instead of treating `because` punctuation as a passive warning.
