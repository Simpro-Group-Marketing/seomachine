# AEO/GEO Blog Strategy

**Purpose:** Canonical AEO/GEO workflow for Simpro blog research, writing, analysis, and rewrites.
**Use when:** Planning or checking blog content that needs PAA, source mapping, Customer Proof Pack, E-E-A-T proof, or AEO/GEO gates.
**Owns:** AEO/GEO variables, PAA workflow, proof-pack shape, draft rules, and publish gates.
**Does not own:** Brand voice, feature claims, competitor battlecards, keyword metrics, or internal-link inventories.
**Source boundary:** Workflow contract only; evidence still needs current public or approved context-backed sources.
**Refresh cadence:** Review when blog workflow gates, proof policy, or AEO/GEO scoring changes.
**Reference detail:** No separate reference file; operating guidance remains here.

---

This file is the canonical blog-writing strategy for AEO and GEO. In this repo, GEO means Generative Engine Optimization: structuring content so generative answer systems can understand, extract, cite, and recommend it.

## Simpro Vault Source Rule

Use the Simpro vault connector only for Simpro-owned artifacts or artifacts containing a Simpro signal. A Simpro signal is the name `Simpro` or an official `simprogroup.com` URL, including schemeless URLs and subdomains. AroFlo, BigChange, and ClockShark owned artifacts with no Simpro signal use the nonconnector branch. Missing, unknown, or malformed brand metadata fails closed into the connector workflow. The only configured connector content location is the vault root; prompts, guards, selectors, and workflow docs must not prescribe vault hubs, filenames, or internal directories.

For connector-bound workflows, run vault health first, describe available roles/topics/entities, search in the task's natural language, read and expand results by `resource_id`, query approved claims only when public proof-sensitive language is needed, then build and validate a context pack.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault connector exposes them as source evidence.

The repo-local context files are downstream operational state only and are never an active or fallback source for Simpro work. If vault MCP operations are absent, use the one enabled `simpro-context@simpro` installation whose `projectPath` matches this repository through `SimproVaultClient`, regardless of its reported version. Determine compatibility from `vault_status` and the required operation contracts. Never use an installation attached to another repository, worktree, or branch checkout. If both connector paths fail, stop and document the exact vault blocker in the validation sidecar.

Required validation evidence: every workflow records a generated Context Binding decision. Connector-bound workflows require vault context evidence and `Fred Voccola Authority Selection`; nonconnector AroFlo, BigChange, and ClockShark workflows record a not-applicable reason and omit context request/pack/receipt, Fred evidence, and vault-dependent customer-proof selector evidence. A nonconnector workflow may supply `simpro-nonvault-customer-proof-selector-evidence/v1` only when public customer proof is approved under the separate non-vault eligibility contract below. `Vault Brand Language Alignment` applies when connector-bound product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` applies to competitor-aware posts; `Named Feature/Add-On Link Check` applies when named Simpro features/add-ons appear. Connector sections must cite `context_pack_hash`, `receipt_hash`, `resource_id`, `claim_id`, use mode, public URL when required, and relevant revisions. Missing required evidence blocks `/publish-readiness`, `/optimize`, and dev-ready handoff.

## Author-Led Blog Voice

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

When `author_policy.status` is `no_author` or the legacy value `not_provided`, first-person singular author judgment outside quotes is prohibited.

## Named Feature Status And Commercial Treatment

When public copy names Lightning, RAIN, a current role agent, Intelligent AI Scheduler, or a roadmap specialist, the validation sidecar must contain exactly one row per detected name under `Named Feature Status and Commercial Treatment`.

```markdown
## Named Feature Status and Commercial Treatment

| Name | Capability claim ID | Commercial claim ID | Release status | Commercial treatment | Region or account boundary | Public wording decision |
|---|---|---|---|---|---|---|
```

Allowed release statuses are `current_public_context`, `preview`, `target_timed`, `roadmap`, and `not_publicly_available`. Allowed commercial treatments are `included`, `package_required`, `add_on_or_upsell`, `mixed`, and `not_asserted`. Supplied claim IDs must resolve uniquely through current connector claim results and the validated context receipt. Internal-only, expired, superseded, missing, and do-not-use evidence blocks public use. Commercial treatment requires a usable commercial claim ID. `not_asserted` is valid only when public copy makes no inclusion, package, price, upgrade, or upsell statement. Unusable current evidence requires `omit`. Intelligent AI Scheduler requires its current capability claim, `target_timed` qualification, and the RAIN Lightning requirement claim. Pulse remains blocked until a current usable claim supports its public roadmap name and treatment.

The blocking `Named Feature Status` gate runs through `data_sources/modules/named_feature_status_guard.py` inside `/publish-readiness`.

The routing policy is enforced through Context Binding plus claim-specific gates, without a duplicate routing sidecar block. For connector-bound work, brand, audience, ICP, product, feature, add-on, solution, industry, Lightning, competitor, Hindsight, customer proof, quotes, metrics, review stories, and approval status data must be connector-first. Repo `context/` owns SEO mechanics, AEO/GEO workflow, schema notes, publish gates, internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples, style mechanics, and operational proof-selector inputs.

## Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: connector-bound competitor-aware posts must document selected competitors, rejected competitors, connector-discovered competitive-context resources, approved claim IDs where public proof is used, and why the shortlist fits the article objective. Nonconnector AroFlo, BigChange, and ClockShark posts document the task-approved shortlist and public official-source basis without vault resource or claim IDs.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified through the claim registry. Keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked through connector-discovered product and feature resources before link decisions. Document the selected `resource_id` values, link decision, and reason in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from connector-discovered vault guidance first. Use semantic search/read/expand for messaging, positioning, feature, solution, and vertical context. When a named feature/add-on appears, include feature-specific `resource_id` evidence; when solution/industry language is used, include solution or vertical `resource_id` evidence. Document connector evidence, language applied, fallback context use, source-verification boundary, and `Status: aligned` in `Vault Brand Language Alignment`. The `vault_brand_language_guard.py` publish gate runs inside `/publish-readiness`; keep this block in the validation sidecar, not public copy. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

Required `Vault Brand Language Alignment` sidecar block:

```markdown
## Vault Brand Language Alignment
- Article title: [title]
- Product/solution language scope: product/feature | solution/industry | mixed
- Vault connector evidence: [vault_status/vault_describe/vault_search/vault_read/vault_expand operations used; context_pack_hash; receipt_hash; messaging/positioning resource_id values; feature resource_id values when named features/add-ons appear; solution or vertical resource_id values when solution/industry language is used; claim_id values for proof-sensitive public language; manifest/revision values]
- Product/feature language applied: [category, product naming, value pillar, workflow phrase, avoided terms]
- Solution/industry language applied: [vertical profile, audience, work environment, guardrails, or not applicable]
- Fallback context use: none | [repo-local fallback plus vault-unavailable blocker]
- Claims requiring source verification: none | mapped in Source Map / Customer Proof Pack / Metric Proof Pack
- Status: aligned
```

This block validates vault language alignment only. It does not approve claims, pricing, metrics, proof, customer outcomes, competitive statements, quotes, rankings, or ratings; those still route through Source Map, Customer Proof Pack, Metric Proof Pack, and the existing proof gates.

Use this file for blog workflows only. It supports `/research`, `/research-serp`, `/write`, `/analyze-existing`, `/rewrite`, and `/optimize`; it does not replace marketing skills.

## Native Blog Workflow, BOM, and Readiness

Command ownership:

- `/research` owns the research brief and validation sidecar planning. It does not write public blog Markdown.
- `/analyze-existing` owns the analysis report and rewrite routing. It does not write public blog Markdown.
- `/write`, `/rewrite`, and `/optimize` own public blog copy.
- `/scrub` owns read-only diagnostics.
- `/publish-readiness` owns release scoring, gates, readiness receipts, and final publish/no-publish status.

Mandatory scrub, scorecard, and optimization pass: every new or changed blog run must include `/scrub`, an initial `/publish-readiness` scorecard or exact non-scoring blocker, `/optimize`, a post-optimization `/scrub` when article bytes change, and a final `/publish-readiness` handoff. `/optimize` is required even when no edits are needed; record a no-op `simpro-optimizer-output/v1` artifact with the inspected scorecard, failed gates or blocker, `aeo_geo.checks`, `priority_fixes`, and the reason no source-safe edit was made. Score absence is a workflow blocker unless a pre-scoring gate blocked readiness; in that case, report the blocker exactly and do not present the article as ready.

`/write`, `/rewrite`, and `/optimize` own public blog copy. Python does not draft, rewrite, or patch Markdown in `drafts/`, `rewrites/`, or `published/`.

Python remains responsible for governance and workflow assistance: selector evidence, Context Binding evidence, verified Semrush keyword decisions, verified SERP/PAA artifacts, editorial-plan validation, BOM assembly, readiness output, readiness receipts, and publisher transport payloads.

`/scrub` is read-only diagnostics. If scrub diagnostics find Unicode marks, em dashes, or whitespace issues, the command/agent applies the copy edit and reruns `/scrub`. The scrubber may write governance diagnostics or receipts when explicitly requested, but it must not overwrite the article.

Every new or changed machine-reviewed blog requires a strict `simpro-blog-assembly-bom/v2`. Existing finalized BOM v1 artifacts remain readable as archived evidence. The vault is the knowledge graph and active evidence source only for connector-bound work. The BOM is the article-specific execution record for final article, validation sidecar, context request/pack/receipt when applicable, customer-proof selector evidence and Fred authority evidence only when connector-bound, editorial plan, plan/article machine reviews, Semrush keyword decision, verified SERP evidence, PAA or rewrite-brief evidence, governance receipts, provisional/final BOM, readiness outputs, and input hashes.

BOM build currently accepts `--stage-receipt` for retained machine-owned governance receipts, such as Context Binding or readiness receipts. Do not use receipt tooling as a public-copy authoring proxy. Do not require a Python-generated article mutation receipt for prose written by the native command/agent workflow.

Use this sequence after article copy, sidecar evidence, context evidence, editorial plan, Semrush keyword decision, SERP/PAA evidence, customer-proof selector evidence, Fred authority evidence when connector-bound, and required governance receipts exist:

```powershell
python data_sources/modules/blog_release.py "[article]" --run-id "[uuid]" --proof-sidecar "[sidecar]" --editorial-plan "[plan]" --plan-review "[plan-review]" --article-review "[article-review]" --keyword-decision "[keyword-decision]" --scrub-receipt "[scrub-receipt]" --serp-evidence "[serp-evidence]" --stage-receipt "[receipt]" --workflow-mode "[new|rewrite]" --assembly-date "[YYYY-MM-DD]" --output-dir "research/releases/[slug]-[date]-[run-id]"
```

The first wrapper run must advance missing optimizer evidence into `optimization_started`, not a dead-end exit. It writes `optimization-recovery.json` after the initial readiness output so `/optimize` has the exact blocker or scorecard. When the initial readiness result passes, it also writes `optimization-state.json` from the predecessor receipt; when readiness blocks before a passed receipt exists, it does not mint a fake optimization state. A passing preflight scorecard alone is not final release approval. After `/optimize`, rerun with the post-optimization scrub receipt, post-optimization stage receipts, optimizer output, and the prior preflight readiness output:

```powershell
python data_sources/modules/blog_release.py "[article]" --run-id "[uuid]" --proof-sidecar "[sidecar]" --editorial-plan "[plan]" --plan-review "[plan-review]" --article-review "[article-review]" --keyword-decision "[keyword-decision]" --scrub-receipt "[post-optimization-scrub-receipt]" --serp-evidence "[serp-evidence]" --stage-receipt "[receipt]" --optimizer-output "[optimizer-output]" --prior-preflight-readiness "[preflight-readiness]" --workflow-mode "[new|rewrite]" --assembly-date "[YYYY-MM-DD]" --output-dir "research/releases/[slug]-[date]-[run-id]-final"
```

Proceed to BOM build only when the pre-BOM report has `ready_for_bom: true`. This report blocks stale Semrush decisions, missing or mismatched scrub receipts, missing customer proof selector evidence when the connector branch or the approved non-vault proof contract makes selector evidence applicable, invalid selector evidence when applicable, unexpected vault-dependent customer-proof or Fred artifacts on nonconnector workflows, missing expertise evidence, missing commercial-page E-E-A-T strength decisions, and missing BOM dependency inputs before BOM assembly.

For commercial-investigation blogs, valid `no_fit_customer_proof` selector evidence prevents invented customer proof but does not by itself make the page strong. At least one positive E-E-A-T signal should be selected when available: selected customer proof, visible approved review-theme or review-story evidence, selected Fred authority, named author, or an approved SME review note. If none exists, the validation sidecar must include `## E-E-A-T Strength Decision` with `Decision: proof_unavailable_safe_to_publish`, a substantive reason, the required public-copy boundary, and `Status: approved`. `/publish-readiness` records this as warning `eeat_strength_safe_but_weak`; the BOM records the same policy under `eeat_strength_policy`.

Required sidecar block when the fallback is used:

```markdown
## E-E-A-T Strength Decision
- Applicability: required
- Intent: commercial_investigation
- Positive signals: [none]
- Decision: proof_unavailable_safe_to_publish
- Reason: [which proof lanes were checked and why no selected signal fits the article objective]
- Public copy boundary: public copy omits customer proof, named customer claims, review stories, exact quotes, testimonials, customer metrics, and unsupported SME claims.
- Status: approved
```

Optional SME signal row:

```markdown
- SME review note: Reviewer name: [name]; Role/title: [role]; Review date: [YYYY-MM-DD]; Source of review: [Asana comment, doc comment, or other retained review surface]; Status: approved
```

Omit context request/pack/receipt, customer-proof selector evidence, and Fred authority evidence only when Context Binding classifies the final article as nonconnector and the validation sidecar records the not-applicable rationale. The builder derives applicability from the final article and rejects a nonconnector branch for Simpro branding, official or schemeless Simpro URLs, connector-sensitive language, unknown brands, or malformed metadata.

Preflight accepts only a provisional BOM and must pass before finalization. Final readiness accepts only a final BOM, reruns every gate, and writes a detached final-readiness attestation bound to the final BOM and exact input hashes. Readiness outputs declare `verification_scope: source_artifact`; they do not claim CMS or rendered-page verification. Rendered canonical, indexability, schema deployment, Core Web Vitals, mobile rendering, image accessibility, and CMS link checks belong to launch QA until a separate rendered-page gate exists.

`/publish-readiness` owns the scorecard. Blog readiness requires:

- Content quality score of 85/100 or higher.
- SEO quality release floor of 90/100 or higher with zero critical SEO issues.
- AEO/GEO score of 90/100 or higher.

SEO quality optimization target is 95/100. Scores from 90 to 94 remain publishable when critical issues are zero, but `/optimize` should attempt one honest, source-safe improvement pass only when the fixes improve reader usefulness, search clarity, proof support, or structure. Do not force keyword stuffing, unsupported claims, brief drift, or scorer-gaming to hit 95.

An AEO/GEO or content score below threshold is a repair trigger, not a reporting endpoint. SEO below the 90/100 release floor or any SEO critical issue is blocking even when the content score passes.

## Post-Publish Performance Measurement

`/research-performance` without a target retains its queue-only Markdown output at `research/performance-review-[YYYY-MM-DD].md` and does not create a target receipt. A target-specific `/research-performance [URL-or-path]` writes the matched advisory pair `research/performance-review-[slug]-[YYYY-MM-DD].md` and `research/performance-receipt-[slug]-[YYYY-MM-DD].json` after resolving canonical identity, objective, conversion definition or not-applicable reason, success measure, owner, review date, a primary window, and its equal-length immediately preceding comparison window. Supplemental windows are optional.

Write and finalize the Markdown report first, then build and check the JSON with `post_publish_measurement_receipt.py build --metadata ... --performance-report ... [--article ... --final-bom ...] --output ...` and `post_publish_measurement_receipt.py check [receipt] --performance-report ... --fail-on error`. The validator checks exact rendered report headings against receipt status, requires exact blocked source identity and blocker values in data-only blocked rows, rejects metrics from blocked first-party lanes, and requires non-empty observed values for the documented metrics. Fenced examples and HTML comments do not satisfy report evidence. The receipt binds a current local article and final BOM as `release_artifact` only when its canonical path ends with the BOM-bound editorial-plan URL slug; otherwise `live_url` requires canonical identity verification, `verified_at`, `verification_method: live_canonical_observation`, and the limitation that no local release artifact was available. It records `verification_scope: recorded_observation_metadata`.

Keep source lanes separate: GSC is search-performance truth, GA4 is behavior/conversion evidence, and third-party tools are optional opportunity/SERP context that never satisfy first-party observation. Record property IDs, exact target filters, UTC retrieval times, limitations, and exact source-specific blockers. Emit `observed` only with at least one observed first-party lane. Otherwise emit `blocked` and preserve the lane blockers. A blocked target report is limited to `Scope and evidence`, `Data-quality and causality limits`, and exact per-source blockers and limitations. A blocked target report contains no opportunity queue, diagnosis, recommendation of any kind, verdict, recommended action, owning-command or other workflow handoff, or success claim.

The report and receipt are advisory internal evidence, not public-claim proof, not Customer Proof Pack or validation-sidecar proof, not an assembly BOM, not a `/publish-readiness` input or gate, and not a release requirement. They are never public proof or authorization to edit copy or post externally. Their hashes validate recorded observation metadata and current artifact bindings, not external analytics truth or causal claims.

## PAA Provenance and Intent-Driven FAQ Policy

- Every new article requires a structured AnswerSocrates artifact, even when no FAQ is useful.
- For a rewrite, PAA pre-picked in a dedicated brief section takes precedence. Bind the brief path and hash, do not rerun AnswerSocrates, and use those exact questions as visible FAQ headings.
- A rewrite without pre-picked brief PAA requires a structured AnswerSocrates artifact.
- A user CSV is allowed only when a saved AnswerSocrates artifact records a genuine blocked state: login, CAPTCHA, quota, or unavailability.
- SERP, Reddit, and YouTube are supplemental research and cannot satisfy PAA provenance.
- Match source kinds exactly. Reject stale artifacts, mismatched queries or dates, keyword fragments, and questions found only outside the eligible question section.
- Record `FAQ policy: required | not_applicable`. `required` applies when a rewrite brief pre-picks PAA or the editorial plan selects a useful FAQ. `not_applicable` requires a non-empty rationale.
- Run FAQ answer-quality, proof, `FAQPage`/`Question`/`Answer` schema, and FAQ scoring only when visible FAQs exist.

## Editorial Plan Contract

Every new or changed blog requires `simpro-blog-editorial-plan/v1`, created through the native command/agent planning workflow rather than a parallel Python writing system. It must contain:

- the complete Reader Contract;
- a `keyword_decision` reference bound to `simpro-semrush-keyword-decision/v1`, including source `semrush_connector`, database, selected primary keyword, selected secondary keywords, and selection rationale;
- verified intent and SERP decisions bound to `simpro-serp-evidence/v1`, including exact result observations, collection metadata, evidence path, canonical evidence hash, and observed features/structure; metadata-only verified labels do not qualify;
- at least 1 original contribution mapped to an exact visible final section with a substantive exact `visible_evidence` excerpt that appears there;
- primary and supporting entity coverage mapped to sections without density targets;
- a query ownership/cannibalization decision of `clear | differentiated | blocked`, where `blocked` prevents readiness;
- intent-appropriate internal links using the 3 to 5 standard-blog target, including the required contextual down-funnel or cluster link counted inside that total unless a brief-bound override narrows the supporting-link count;
- `FAQ policy: required | not_applicable` with its rationale; and
- the PAA source/binding/selected-question decision required by the workflow mode.

The plan may include `rewrite_decisions`, `audience_language_research`, and `link_policy_override` when the workflow needs them. `rewrite_decisions` records evidence-bound preserve, update, add, and remove decisions from `/analyze-existing`. `audience_language_research` is conditional: use genuine Reddit, YouTube, or trade-community language only when it improves reader comprehension, never as regulatory, product, metric, PAA, or public-claim proof. Regulatory and licensing articles default to `not_applicable` unless the brief explicitly requests audience-language research. A valid `link_policy_override` binds the exact brief sentence, brief hash, count, and pre-FAQ body scope when the brief requires an exact internal-link count; it may replace the 3 to 5 default supporting-link target but can never exceed the hard maximum of 7. For single-trade Simpro posts, the matching industry-cluster link remains additive unless the bound brief explicitly prohibits the industry page.

The BOM binds the final serialized plan path/hash. Publish readiness validates the plan against the final article rather than accepting marker-only planning text.

## Semrush Keyword Decision Contract

Every new or changed SEO/AEO blog requires a machine-readable `simpro-semrush-keyword-decision/v1` artifact at `research/semrush-keyword-decision-[topic-slug]-[YYYY-MM-DD].json` before optimization decisions are finalized. When the task requires Semrush UI, use the authenticated Semrush UI in the main Chrome profile and record `execution_surface: semrush_ui_chrome_main_browser` in the report parameters. Do not substitute Semrush API, MCP, stale repo keyword tables, or estimates for current opportunity and SERP feasibility decisions. Existing `context/target-keywords.md` may inform seed terms only.

Default Semrush databases by brand and market:

- Simpro: `us`
- ClockShark: `us`
- BigChange: `uk`
- AroFlo: `au` primary; add `nz` as a secondary check only when the brief is explicitly NZ or ANZ

Required connector sequence:

- `_keyword_research` to confirm available reports
- `_get_report_schema` before running report types
- `phrase_these` for exact candidate keyword metrics
- `phrase_related` for adjacent opportunity discovery
- `phrase_questions` for question demand and FAQ candidates
- `phrase_organic` for SERP feasibility on finalists
- `phrase_this` for final exact-primary confirmation when needed

Selection rule: choose by intent fit first, then page ownership and cannibalization risk, then volume, difficulty, CPC, trend, SERP shape, and competitor feasibility.

The keyword artifact must include seed terms, candidate metrics, finalist SERP rows, selected primary keyword, selected secondary keywords, rejected keywords with reasons, database used, connector report parameters, collection date, and this source boundary: `Semrush is third-party opportunity/SERP context; GSC remains first-party performance truth.`

The BOM stores the artifact path/hash. Publish readiness runs `semrush_keyword_decision` and fails when the editorial plan, article metadata, BOM hash, or keyword artifact disagree.

If the main Chrome Semrush UI opens but DOM or screenshot extraction times out or resets, record `blocked_semrush_ui_refresh` and stop before BOM assembly. The blocker proves the UI lane was attempted, but it does not satisfy the current keyword decision requirement.

## Required Variable Resolution

Before drafting with `/write` or `/rewrite`, resolve these variables from the user prompt, research brief, generated vault context binding, and repo context files only as fallback/mirror inputs. `/analyze-existing` must audit which inputs are present, missing, or blocked before a rewrite proceeds.

| Variable | First source | Fallback |
|---|---|---|
| `topic` | User prompt or topic file | Ask the user |
| `audience` | Connector-discovered messaging and vertical resources | `context/brand-voice.md` fallback mirror if the vault is unavailable |
| `main_question` | SERP/PAA intent, title, or brief | Ask if no clear primary question exists |
| `related_questions` | Structured AnswerSocrates artifact; for rewrites, the dedicated pre-picked brief section takes precedence | User PAA/FAQ CSV only with a bound AnswerSocrates genuine blocked-state artifact |
| `tone` | Connector semantic search and `resource_id` reads for current messaging and style guidance | `context/brand-voice.md` and `context/style-guide.md` fallback mirrors if the connector is unavailable |
| `expertise` | Connector-discovered product/workflow resources and approved claims, plus verified expert sources | Ask if a named author/reviewer is required and missing |
| `length` | Complete Reader Contract, verified intent, and available evidence | Keep the scope intent-complete without competitor-derived or universal word targets |

Do not synthesize facts, search volume, PAA questions, customer claims, or expert quotes. If the repo and live research do not provide an input, ask for it or mark it as missing.

## Existing-Content Rewrite Use

For `/analyze-existing`, audit whether the current post has the strategy inputs needed for a safe rewrite: main answer target, related-question provenance, source-backed claims, Source Map, E-E-A-T proof, direct-answer opportunities, capsule opportunities, schema notes, and quality-gate risks.

For `/rewrite`, resolve the same variables before drafting. Reuse existing strategy artifacts only when they match the post topic and current rewrite direction. If the rewrite brief contains pre-picked PAA in its dedicated section, preserve those exact visible FAQ headings and bind the brief path/hash. If it does not, collect a current structured AnswerSocrates artifact. If source-backed claims or proof are missing, collect them or mark the blocker before writing.

Do not invent replacement questions, customer proof, author names, reviewer names, search-volume data, ranking data, or external claims to fill rewrite gaps.

## E-E-A-T Proof Map

Every `/write` and `/rewrite` plan must resolve an E-E-A-T Proof Map before drafting. `/analyze-existing` must report Experience proof present/missing, Expertise proof present/missing, case-study proof candidates, Review-site VoC candidates, review-site experience evidence candidates, and claims that must stay out because proof is missing.

| Dimension | Approved inputs | Public-copy rule |
|---|---|---|
| Experience | Customer case studies, customer outcomes, identity-backed Review Story Selection rows, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples | Cite the public case-study URL, approved review-site/source URL, or verified source page. Review-derived E-E-A-T stories need a public review URL in the same paragraph as the paraphrase. Do not cite internal context language. |
| Expertise | Product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity | Use Simpro product/workflow links and source-backed explanations. Do not invent author, reviewer, or expert claims. |
| Authority/Trust | Public research, case-study URLs, review-site/source links, limitations, caveats, and no invented proof | Follow the claim's machine-assigned citation mode. For `inline_required`, use a natural descriptive anchor to the public source in the claim's paragraph; lower-risk claims may use `section_source_allowed`, `sidecar_only`, or `proof_not_required` when assigned. |

Required proof sources:
- Discover customer, review, product, competitor, and expert evidence through connector search/read/expand by `resource_id`.
- Use `vault_claims` for every public metric, quote, review theme, customer outcome, or other proof-sensitive passage; the selected claim must be present in the validated context pack and receipt.
- Use the claim registry's public URL and source-visibility decision for public citations. Repo-local proof indexes and ledgers are operational selection and reuse state only; they cannot approve a claim or override the connector.
- Context-backed metrics are valid only when the context pack carries an approved claim, permitted use mode, public proof URL, and source-visible evidence anchor. Public copy must link to the public case study, review site, or source URL, not to internal context files.
- Metric-sensitive topics must include a Metric Proof Pack before drafting or publish readiness. The pack requires a Search log, each Approved metric, public proof URL or local proof artifact, source-visible Evidence, Status: approved, intended Use, and rejected candidates.
- The source support guard requires each high-risk claim to map to a strict proof row with Claim, URL, Evidence, and Status: approved. The Evidence snippet must be visible in the cited public source or local proof artifact.
- The PAA provenance guard requires each visible FAQ question to map exactly to the bound structured AnswerSocrates artifact or, for a rewrite, the dedicated pre-picked brief section. A user CSV requires a bound AnswerSocrates genuine blocked-state artifact. Proof links and supplemental SERP, Reddit, or YouTube research do not prove PAA provenance.
- Do not write source/proof meta-commentary in public copy, such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.

## Metric Proof Pack

Every `/research`, `/write`, `/analyze-existing`, and `/rewrite` workflow for software, comparison, pricing, cost, ROI, KPI, profit, margin, guide, or vs topics must resolve a Metric Proof Pack before numbers enter public copy.

Required Metric Proof Pack shape:

```markdown
## Metric Proof Pack
- **Metric requirement**: required / not applicable
- **Reason**: [required only when not applicable]
- **Search log**: [public pages and local proof artifacts checked for usable numbers]
- **Approved metric**: [metric claim] | URL: [public proof URL or local proof artifact] | Evidence: "[source-visible Evidence]" | Status: approved | Use: [intended use]
- **Rejected metrics**: [candidate metric, source checked, reason excluded]
```

Run `python data_sources/modules/metric_proof_pack_guard.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error` before scoring or `/optimize`. The guard blocks metric-free software-selection, buyer-guide, comparison, pricing, cost, ROI, KPI, profit, margin, guide, and vs topics unless `Metric requirement: not applicable` is documented with a reason and search log. Numeric claim source guard and source support guard still prove any numbers that appear in the final article.

## Review-Site Experience Evidence and VoC Routing

Public review sites are approved for sourced review-site experience evidence, VoC themes, and competitor-review themes. Approved surfaces include G2, Capterra, Software Advice, GetApp, TrustRadius, Gartner/Gartner Digital Markets, Trustpilot, app stores, and Google reviews.

Review narratives are first-hand customer experience when reviewers describe product use, implementation, support, switching, pains, outcomes, or workflows. Review-site themes can inform VoC research, but they do not satisfy E-E-A-T story proof unless the sidecar contains an identity-backed `Review Story Selection` with a real person or business, a usable public review URL, Status: approved, and an article link requirement that places the source link in the same paragraph as the paraphrase.

For Capterra rows that fit a blog topic but do not need an E-E-A-T story, use `Review Site Theme Selection` in the validation sidecar. It must include `Platform: Capterra`, `Source row ref: Capterra tab row [n]`, `Public review-site URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`, `Workflow theme`, and `Status: approved for paraphrased review-theme use`. Public copy may paraphrase the theme only when the same paragraph links to the Capterra review-site URL. Limits: no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved.

Use review sites for sourced VoC themes, objections, switching triggers, implementation or support themes, competitor-review themes, and first-hand customer experience patterns. Default to theme-level citation: cite the theme and link to the relevant review, profile, category, or comparison page.

When a brief uses review-site experience evidence, capture platform, URL, date checked, product/competitor, experience pattern, evidence summary, and whether any exact quote/rating claim was approved. When public copy uses a review-derived experience story, the command workflow must automatically run the selector before drafting story copy and add this sidecar block:

```markdown
## Review Story Selection
- **Article title**: [title]
- **Content objective**: [objective]
- **Selector command**: automatically run python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles experience_story --require-eeat-story --limit 10
- **Selected story**: [proof_id] | Identity: [person or business] | Platform: [G2/Capterra/Google] | URL: [public review URL] | Workflow story: [short paraphrase] | Status: approved | Use: E-E-A-T experience story
- **Why selected**: [fit to article objective/title]
- **Article link requirement**: same paragraph as review-derived paraphrase must link to the selected public review URL
- **Exact quote use**: not approved unless listed under Approved quote
```

```markdown
## Review Site Theme Selection
- **Article title**: [title]
- **Content objective**: [objective]
- **Platform**: Capterra
- **Source row ref**: Capterra tab row [n]
- **Public review-site URL**: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/
- **Workflow theme**: [short paraphrase]
- **Status**: approved for paraphrased review-theme use
- **Article link requirement**: same paragraph must link to the Capterra review-site URL
- **Limits**: no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved
```

Exact quotes, named reviewers, star ratings, badges, rankings, aggregate ratings, and category-leadership claims are Trust/Authority claims; they require current source verification and brief-level approval.

### Optional Story and Scenario Policy

E-E-A-T stories are optional, and E-E-A-T story usage is optional in public copy. experience_story consideration is required whenever customer proof appears in public copy. Use a proof-backed customer/review POV only when it improves the article objective. A named public POV must be an actual person or business POV from approved customer proof, a public case study, Quote Matrix route, reference, customer story, or review-site row, with proof in the validation sidecar and a public source link when used in copy.

Review-theme evidence is VoC only unless it is identity-backed and link-backed through `Review Story Selection`. Unnamed workflow scenarios are explanatory only and do not count as E-E-A-T proof; fictional named personas are prohibited.

## Customer Proof Pack

Every `/research`, `/write`, `/analyze-existing`, and `/rewrite` workflow must resolve a task-specific Customer Proof Pack before placing direct quotes, named customer proof, approved metrics, or review-derived Experience patterns in public copy. Keep the Quote Matrix external; do not bulk-load it into repo context.

Use the Global Customer Quote Matrix first for exact customer quotes. Use Customer Stories, References, and public case studies to verify the story path and publishability. Use review sites for first-hand Experience patterns by default, not unverified testimonial harvesting. Metrics from `context/features.md` must pair with public proof paths from `context/internal-links-map.md`.

Before selecting customer proof for connector-bound work, the command workflow must resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and write the generated selector-first `Customer Proof Slate` to the validation sidecar before drafting customer proof. "Consult" means reviewing generated selector output, not skipping execution. If the selector reports no approved claims bound to the customer proof inventory and the article will use no customer proof, rerun the same full-role slate with `--allow-no-proof`; valid no-fit evidence records `selection_outcome: no_fit_customer_proof`, represents metric, quote, theme, and experience_story, sets each role to `Selected: [none]`, and states that public copy must omit customer proof. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails for any other reason, write the failure or blocker into the validation sidecar and do not invent proof. The selector uses `customer-proof-index.json` and `customer-proof-usage-ledger.json` to choose the most relevant approved proof, then penalizes proof with `recent_uses_90d` above 0 and overused proof. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. Do not pick the easiest mapped case study when a better-fit Quote Matrix, Reference, Customer Story, or review-site proof route exists. experience_story consideration is required and E-E-A-T story usage is optional; if no story fits, use `Selected: [none]` with section-specific rejection reasons. Edit selected/rejected rows only when editorial judgment requires it. If a recently used or overused proof source is still the best proof, add a `Customer Proof Selection Decision` with a source-specific `Reuse reason` plus selector-backed proof that no stronger underused approved proof fits the same role.

For nonconnector AroFlo, BigChange, and ClockShark work, never run the vault-dependent selector. Public customer proof is allowed only when an approved proof-index row satisfies the separate non-vault eligibility contract and the workflow runs `python data_sources/modules/nonvault_customer_proof_selector.py "[topic]" --brand "[brand]" --title "[title]" --objective "[objective]" --article-slug "[slug]" --evidence-output "research/nonvault-customer-proof-selector-evidence-[topic-slug]-[YYYY-MM-DD].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`. The emitted artifact must use `simpro-nonvault-customer-proof-selector-evidence/v1` and bind the brand, topic, title, objective, article slug, reference date, roles, selected and candidate proof IDs, proof-index hash, and usage-ledger hash. V1 accepts brand-owned `customer_story`, `case_study`, and `reference` sources only. Review-platform sources, vault selector evidence, Fred evidence, exact quotes, metrics, ratings, and named-person attribution remain prohibited unless separately approved by a later contract. Add the public use to the ledger only after finalizing the article paragraph, then regenerate evidence so its ledger hash matches release inputs.

Selector chooses proof candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. When public copy uses selected customer proof, the validation sidecar must include `Selected Customer Proof Mining`. This block proves the selected source was checked for stronger quote, metric, POV/story, and theme evidence before the final copy used only the selected proof role.

Required Selected Customer Proof Mining shape:

```text
Selected Customer Proof Mining
- Proof: [proof_id] | Customer: [customer] | URL: [public URL]
- Checked for: exact quotes, customer metrics, POV story, workflow themes
- Usable quotes found: [exact approved quote rows or none found]
- Usable metrics found: [approved metric rows or none found]
- Usable POV/story found: [identity-backed POV summary or none found]
- Recommended use: [theme / paraphrased POV / exact quote / metric / omit]
- Final use in copy: [what the article actually uses]
- Excluded proof: [quote/metric/POV and section-specific reason]
- Status: approved
```

If `Approved quotes: none used` or `Approved metrics: none used` appears in the Customer Proof Pack, the mining block must still document whether usable quotes or metrics were found and why they were omitted. When usable quote or POV evidence is found but omitted, add a section-specific reason under `Excluded proof`.

### proof-index intake and health

The proof-index health report is `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json`; use it to inspect source mix, approval status, public-copy gaps, `recent_uses_90d`, recently used or overused proof, and ledger backfill needs before expanding the index.

New customer proof candidates must enter `context/customer-proof-index.json` through `context/customer-proof-intake-template.csv` and `data_sources/modules/customer_proof_index_intake.py` before a writer relies on them in selector slates. Use:

```powershell
python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json
python data_sources/modules/customer_proof_index_intake.py merge [input.csv] --index context/customer-proof-index.json --out context/customer-proof-index.json
```

The intake row must state source type, source ref, approval status, public-copy boundary, evidence summary, restrictions, and verification date. Exact quotes, metrics, review-story identity claims, reviewer-name claims, ratings, rankings, and badges need explicit source-visible evidence before approval. Google review rows stay candidate and `public_copy_allowed: false` unless a usable public review URL is captured.

Required Customer Proof Slate shape:

```text
Customer Proof Slate
- Selector command: automatically run python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10
- Selector evidence: research/customer-proof-selector-evidence-[topic-slug].json | SHA-256: [generated digest]
- Selection outcome: [customer_proof_candidates_available or no_fit_customer_proof]
- Role: metric | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id] | Rejected stronger candidates: [proof_id: reason]
- Role: quote | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id or none] | Rejected stronger candidates: [proof_id: reason]
- Role: theme | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id or none] | Rejected stronger candidates: [proof_id: reason]
- Role: experience_story | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id or none] | Rejected stronger candidates: [proof_id: reason]
```

For `selection_outcome: no_fit_customer_proof`, every role must have `Top candidates: [none]`, `Selected: [none]`, no claim IDs, and a no-fit reason stating that public copy must omit customer proof, named customer claims, review stories, exact quotes, testimonials, and customer metrics. Publish readiness still fails if the article contains proof-sensitive customer copy under a no-fit selector artifact.

Required Customer Proof Pack shape:

```markdown
## Customer Proof Pack
- **Pack status**: ready / partial / blocked
- **Topic or page fit**: [topic, audience, region, trade, funnel stage]
- **Quote Matrix candidates**: [customer, trade, region, theme, exact quote or summary, source row/link, approval status]
- **Case-study proof paths**: [customer, public URL, supported non-numeric theme]
- **Review-site experience evidence**: [platform, URL, date checked, product/competitor, experience pattern, evidence summary, exact quote/rating approval status]
- **Customer Proof Slate**: [selector command plus metric, quote, theme, and experience_story role rows; story usage optional]
- **Selected Customer Proof Mining**: [selected public URL checked for exact quotes, customer metrics, POV story, workflow themes, recommended use, final use, excluded proof, and Status: approved]
- **Customer Proof Selection Decision**: [selector command, selected proof IDs, rejected stronger candidates, final use in copy]
- **Reuse reason**: [source-specific; required when selected proof has `recent_uses_90d` above 0 or is already marked recently used or overused in the ledger; must include selector-backed proof that no stronger underused approved proof fits the same role]
- **Approved quotes**: [exact quote/testimonial, customer/brand/reviewer, source type, public proof URL, Evidence, approval status]
- **Approved metrics**: [named customer metric, customer/brand, public proof URL, Evidence, approval status]
- **Use in copy**: [exact quote / paraphrased theme / named metric / omit]
- **Claims excluded**: [claim and missing proof reason]
```

Example strict proof rows:

```markdown
- Claim: Shaffer Beacon Mechanical can process twice the amount of business with the same resources | URL: https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical | Evidence: "We can process twice the amount of business with the same amount of resources" | Status: approved | Use: paraphrased customer outcome
- Approved quote: "The system gives our technicians one place to work from." | Customer/brand: Shaffer Beacon Mechanical | Source type: case study | URL: https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical | Evidence: "The system gives our technicians one place to work from." | Status: approved | Use: exact quote
- Approved metric: Simpro 24,000+ trade businesses | Customer/brand: Simpro | URL: https://www.simprogroup.com/company/press/simpro-group-unveils-lightning | Evidence: "More than 24,000 trade businesses" | Status: approved
```

Case-study proof paths and Review-site experience evidence may support non-numeric E-E-A-T PoV and paraphrased themes only. Exact quotes or testimonial wording must appear under Approved quotes with customer/brand or reviewer, source type, public URL, source-visible Evidence, and Status: approved. Any named customer metric must appear under Approved metrics with Customer/brand, public URL, source-visible Evidence, and Status: approved. Source Map alone is insufficient for quotes, testimonials, or named metrics.

## Fred Voccola Authority Selection

Every `/research`, `/write`, `/rewrite`, `/analyze-existing`, and `/optimize` workflow for a new or changed Simpro blog must resolve `topic`, `title`, and `objective`, automatically run:

```powershell
python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5 --output "research/fred-authority-selection-[topic-slug].md"
```

Write the complete selector evaluation to `research/validation-[topic-slug]-[YYYY-MM-DD].md` before drafting or changing public Fred content. Evaluation is mandatory; public use is optional and must materially support the article subject and target section. The selector defaults to `Selected: none`; selection requires an explicit editorial decision after the source is reviewed. If the selector, vault, manifest, or required inventory is unavailable or stale, set `Evaluation status: blocked`, document the blocker, and do not invent, infer, quote, paraphrase, cite, or embed Fred evidence.

The Simpro vault connector and claim registry are the sole eligibility source for Fred media eligibility and status. The selector resolves only the configured vault root, validates current connector revisions, resource hashes, and claim decisions, and fails closed when the manifest, claim registry, context receipt, or selected evidence is unavailable or stale. Only current usable authority records and public playlist assets are candidates. Internal assets, blocked rows, syndicated-placement-only rows, non-Simpro evidence, and any row outside its allowed-use status are excluded.

Fred's source-backed industry observations supplement E-E-A-T Expertise and Authority by default. They count as Experience only when the source explicitly supports Fred's first-hand personal or operating experience. Fred evidence is additive: it does not replace customer Experience proof, customer stories, the Customer Proof Pack, or authoritative independent evidence. No usage ledger or frequency penalty applies in v1; direct topical support is the primary selection criterion.

Required sidecar block:

```markdown
## Fred Voccola Authority Selection
- Selector command: [...]
- Evaluation status: completed | blocked
- Top candidates: [FVMI IDs or none]
- Selected: [FVMI ID or none]
- Fit decision: [specific article relevance or rejection reason]
- Intended use: none | embed | inline_citation | paraphrased_industry_observation | exact_quote | embed_and_paraphrase | embed_and_quote
- Target section: [heading or not applicable]
- Authority row: [AUTH ID or none]
- Public URL: [URL or not applicable]
- Evidence status: [vault status or not applicable]
- Verification method: not_applicable | source_visible_article_text | transcript_and_playback | paraphrase_evidence
- Evidence excerpt: [source text or not applicable]
- Timestamp or locator: [timestamp, article locator, or not applicable]
- Playback verified: yes | not_applicable
- Exact quote: [text or not applicable]
- Embed decision: yes | no
- VideoObject: required | not_applicable
```

`Selected: none` passes only when `Fit decision` gives a substantive, article-specific topical rejection reason. A generic statement such as "not relevant" does not pass. For a selected row, the sidecar must match the fields it carries: selected ID, authority ID, public URL, and evidence status. The guard must also confirm that the current manifest-backed inventory and authority rows agree on title, URL, recommended brand, evidence status, public-use status, and allowed-use eligibility.

Public-use rules:

- Exact article quotations require source-visible article text, `Verification method: source_visible_article_text`, an evidence excerpt, and an article locator. Exact video or audio quotations require source-visible transcript or caption evidence, a timestamp, `Verification method: transcript_and_playback`, and `Playback verified: yes`. If those checks are incomplete, paraphrase or omit the observation.
- An exact quote or paraphrased industry observation must include a contextual public source link in the same paragraph. The source must directly support the surrounding statement; a sidecar URL alone does not satisfy this requirement.
- playlist-only rows may be used for discovery or an eligible embed, but never as independent earned-media authority. Do not present a curated playlist entry as third-party validation.
- Embedding is content-first and optional. Embed only a selected, public, embeddable YouTube source that materially supports the target section. Use the existing responsive 16:9 handoff: a privacy-enhanced `https://www.youtube-nocookie.com/embed/[video-id]` URL, visible public fallback link, descriptive iframe title, `loading="lazy"`, no autoplay, verified video metadata, and responsive dimensions.
- Frontmatter must include `VideoObject` when a Fred video is embedded and must omit `VideoObject` when no video is embedded. The internal selection block alone never earns AEO or E-E-A-T credit; only source-backed public content counts.

Existing articles and sidecars are not bulk-backfilled. This block becomes mandatory when an existing Simpro article is next rewritten, optimized, or passed through `/publish-readiness`.

## AnswerSocrates PAA Workflow

For every new `/write` run, collect People Also Ask style questions from `https://answersocrates.com` with Playwright MCP.

Required browser flow:

1. Open AnswerSocrates with `browser_navigate`.
2. Use `browser_snapshot` to identify the query input and submit action.
3. Enter the inferred `main_question`; if no main question exists, enter `topic`.
4. Submit with snapshot-derived targets only. Do not hard-code selectors.
5. Wait for results and extract visible questions with `browser_evaluate`.
6. Immediately record the observed run as `research/paa-questions-[topic-slug]-[YYYY-MM-DD].json` with the recorder below. Do not hand-author the JSON or its hashes.

If AnswerSocrates records a genuine blocked state such as login, CAPTCHA, quota, or unavailability, preserve that structured blocker artifact before asking for a PAA/FAQ CSV export. Do not invent replacement questions.

For `/rewrite`, first inspect the brief for a dedicated pre-picked PAA section. It takes precedence over all other sources and its exact questions must remain visible FAQ headings. Without that section, collect a current structured AnswerSocrates artifact. SERP, Reddit, and YouTube stay supplemental and never satisfy PAA provenance.

The rewrite-only brief section must use this exact heading:

```markdown
## Pre-picked PAA Questions
- [Exact complete question?]
```

### Collected AnswerSocrates Artifact Template

After the Playwright run finishes, execute this recorder command with the actual browser run ID, UTC timestamps, and every observed eligible question. Repeat `--eligible-question` and `--ineligible-fragment` as needed; omit either repeatable flag when its observed list is empty.

```powershell
python data_sources/modules/paa_provenance_guard.py record --query "[main question or topic]" --collection-date "[YYYY-MM-DD matching the assembly date]" --run-id "[Playwright run ID]" --started-at "[RFC 3339 UTC start]" --completed-at "[RFC 3339 UTC completion]" --eligible-question "[complete eligible question?]" --ineligible-fragment "[observed keyword fragment]" --output "research/paa-questions-[topic-slug]-[YYYY-MM-DD].json"
```

The recorder emits `simpro-answersocrates-artifact/v1` with a nested `simpro-answersocrates-run-receipt/v1`, fixed `playwright_mcp` tool identity, payload SHA-256, and receipt SHA-256. Handwritten labels, Markdown templates, and self-described browser blockers are invalid provenance.

### Blocked AnswerSocrates Artifact Template

Save the observed blocker before accepting a user CSV. The blocker reason must describe what the browser actually showed.

```powershell
python data_sources/modules/paa_provenance_guard.py record --query "[main question or topic]" --collection-date "[YYYY-MM-DD matching the assembly date]" --run-id "[Playwright run ID]" --started-at "[RFC 3339 UTC start]" --completed-at "[RFC 3339 UTC completion]" --status blocked --blocker "[login | captcha | quota | unavailability]" --blocker-reason "[observed browser evidence]" --output "research/paa-questions-[topic-slug]-[YYYY-MM-DD].json"
```

For the blocked fallback, the BOM builder must receive `--user-paa-csv "[user-csv]" --answersocrates-blocker "[blocked-answersocrates-artifact]"`. Direct provenance debugging passes the CSV as `paa_provenance_guard.py --paa-artifact "[user-csv]" --answersocrates-blocker "[blocked-answersocrates-artifact]"`. Readiness reruns the semantic guard against those exact BOM-bound hashes.

## Question Relevance Selection

Select only the complete eligible questions that materially support the main concept and planned FAQ. Do not target a fixed count. Group selected questions by search intent such as How-to, Understanding, Comparative, Future-Trends, or Commercial. Summarize what they reveal, write the suggested blog focus, and assign each selected question to an article section and answer format.

## General Source Support Classes

Use only these exact general source-map classes: `primary_authority`, `independent_research`, `non_competing_expert`, `owned_product`, `customer_proof`, `review_platform`, and `competitor`. Every proof-sensitive claim requires an exact machine-generated claim-fit source-map row with `Claim`, `Claim type`, `Evidence relation: directly_supports`, `Source class`, `Classification artifact`, `Classification hash`, `URL`, source-visible `Evidence`, `Citation mode`, and `Status: approved`. The classification artifact must be a hash-bound `simpro-source-classification/v1` registry export; a writer-supplied source-class or citation-mode label is not evidence. Owned product sources support product facts; connector claims govern proof-sensitive Simpro language; customer and review proof retain their specialist gates.

The policy engine assigns exactly one of four citation modes:

- `inline_required`: legal, regulatory, licensing, compliance, safety, fees, deadlines, pricing, status, material numeric, causal, comparative, benchmark, quote, customer, review, Fred, and fact-driven FAQ claims require a natural public link in the same paragraph or table row. FAQ links must appear in the first visible answer paragraph.
- `section_source_allowed`: lower-risk body definitions, background, and process explanations may use one mapped source in the same H2 section.
- `sidecar_only`: approved low-risk product or brand language and clearly framed low-risk editorial recommendations may remain mapped in the validation sidecar without a visible public link.
- `proof_not_required`: navigation, explicit opinion, or advice with no externally verifiable factual claim requires no proof. Only the policy engine may generate this mode.

Unknown or ambiguous high-risk claims fail closed to `inline_required`. A Source Map or FAQ Proof Map documents the mapping but cannot replace a required reader-facing link. Use natural descriptive anchors rather than pasted URLs, generic calls to action, or repetitive exact-match anchors. Prefer one authority link for a contiguous claim cluster, but allow multiple distinct authority links in one paragraph when separate evidence-triggered claims require them; never split or remove required proof solely to satisfy a per-paragraph link count.

Two distinct authoritative non-owned external sources satisfy the standard-blog baseline. Multiple links to one source count as one source, and a third source added only to satisfy a quota is redundant. Source support, regulations, public proof, specialist same-paragraph rules, and other claim-fit evidence exceptions are uncapped. Standard blogs use 3 to 5 internal links and must not exceed 7. URL fragments and `mailto:` or `tel:` links are navigation utilities and do not count toward internal or external totals.

Machine reviewers must preserve every `inline_required` link and every other specialist-required public link. They must report any proposed deletion, anchor rewrite, or relocation that would break the mapping, and flag repeated destinations, duplicate support, or a quota-only third external source as redundancy. Reviewers return advisory findings only. `/publish-readiness` remains the sole release verdict; this workflow has no human approval stage.

When a PDF extraction or unreachable HTML fallback is necessary, also bind `Capture receipt` and `Capture receipt hash` from `simpro-source-capture-receipt/v1`. That receipt must identify the source URL, retrieval time, source and output hashes, extraction method, and exact capture tool. A locally authored evidence file without this receipt blocks readiness.

## Drafting Rules

- Open with a direct answer in the first 1-2 sentences. The answer comes before the hook.
- Use the Capsule Method below the H1 and at least 60% of major H2s: 50-60 words, complete answer, no preamble.
- Include a Key Takeaways block after the introduction with 3-5 standalone conclusions.
- Place a usable artifact within the first 300 words of body copy: a filled data table, a download link (PDF, Excel, Doc, or template), a checklist deliverable, or a calculator/tool reference. Key Takeaways bullets, plain lists, and image placeholders do not count. If no artifact fits the topic, mark `Early artifact requirement: not applicable` with a Reason in the `Early Artifact Plan` block of the validation sidecar.
- When image or video work remains, use a visible standalone marker so developers cannot miss it. `/write`, `/rewrite`, and `/optimize` must normalize hidden HTML comments, blockquotes, inline labels, and shorthand media notes into `[IMAGE PLACEHOLDER | source: ... | alt: "..." | render target: ... | resize and compress before upload]` or `[VIDEO PLACEHOLDER | source: ... | title: "..." | placement: ... | embed target: ... | VideoObject: add only after embed]`. Treat unclear media placeholder warnings as LLM repair instructions, not publish blockers.
- If the target query implies a number, range, or template, supply a concrete version in the article with disclaimers as needed. Placeholder-only table cells such as `Enter lender-approved value`, `TBD`, or `varies` withhold the answer and block publish; fill tables with concrete sourced values or delete them. Non-scaffold exemptions go in the `Concrete Answer Check` block of the validation sidecar with a Reason.
- Use one clear idea per H2/H3 section.
- Integrate claim-fit credible external sources naturally inside sentences; evidence needs determine the count.
- Place each link where it directly supports the sentence and reader task. Do not impose a per-paragraph quota.
- Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough.
- Context files are an internal source of truth for voice, positioning, approved claims, proof candidates, and approved metrics only when the Obsidian vault is unavailable; otherwise they are repo-local mirrors/fallbacks. Use public sources and context-backed proof when available, but do not write phrases like "repo context," "context/features.md," "Source Map," "PAA artifact," "change summary," or internal proof-path notes in the public article body.
- Use context-backed metrics only with public-facing source links, such as case-study URLs, review-site URLs, or public research sources.
- 403 replacement rule: if a source URL returns 401, 403, or `manual_review`, do not remove the public citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. DOL, Capterra, G2, Trustpilot, Google Play, and other review or authority-site 403s are URL-validity blockers, not permission to hide the source in the validation sidecar. Source Map notes must document the rejected 403 URL and the replacement URL.
- Include a Metric Proof Pack when the topic calls for metrics, with a Search log and at least one Approved metric carrying source-visible Evidence before numeric claims are placed in the draft.
- Include a visible FAQ only when `FAQ policy: required`; otherwise record `not_applicable` with a non-empty rationale and omit FAQ schema.
- When visible FAQs exist, write each answer as a 40-60 word direct answer before supporting context.
- FAQ answer quality is mandatory when visible FAQs exist: lead with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Do not open with `There is no`, `It depends`, `Pricing depends`, `Costs vary`, `We do not know`, `It is unclear`, `No source ranks`, or an equivalent deflection. Put limitations after the direct answer. Replace or remove a question when no defensible answer exists. Run `python data_sources/modules/faq_answer_quality_guard.py [file] --fail-on error` before scoring or `/optimize`.
- FAQ proof is risk-tiered. Fact-driven or high-risk answers use `inline_required` and place a natural authoritative non-owned public evidence link in the first visible paragraph. Lower-risk answers follow their machine-assigned mode and do not receive a visible link solely to satisfy a quota. A question-specific Source Map / FAQ Proof Map row documents the evidence but cannot replace a reader-facing link when `inline_required` applies. Context file paths and owned product links alone do not satisfy an `inline_required` FAQ claim. Run `python data_sources/modules/faq_proof_guard.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error` before scoring or `/optimize`.
- **FAQ Source Policy**: Every visible non-owned FAQ URL needs one exact `FAQ Proof Map` row with `FAQ`, `URL`, `Source class`, `Competitor check`, and source-grounded `Support`.
  - Allowed source classes: neutral, non_competing_expert.
  - Competitor-owned FAQ sources: prohibited.
  - Use regulators, standards bodies, universities, trade associations, independent research/editorial, or non-competing expert sources.
  - Simpro-owned links can be additional reader resources but never satisfy the non-owned FAQ-proof requirement.
  - If no compliant source supports a vendor-specific question, remove or reframe the FAQ and retain vendor evidence in a comparison or vendor-specific body section.
  - Add `- Status: aligned.` in the `FAQ Source Policy` sidecar block.

- PAA provenance is required for each FAQ question: include `PAA/FAQ Provenance` with Source, Artifact, and exact Selected questions. Run `python data_sources/modules/paa_provenance_guard.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error` before scoring or `/optimize`.
- Add schema notes for standard blog posts: always require `BlogPosting`, `BreadcrumbList`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`. `FAQPage` and `Question and Answer inside FAQPage` are required only when visible FAQs exist. `Person as author` is required only when a named author exists. Require `VideoObject` if and only if a verified video embed exists. For public Markdown blog artifacts, place `schema_notes` in the top YAML frontmatter block between the opening and closing --- delimiters. If a named author is present, include `author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and record the no-author decision in the BOM and validation sidecar.
- Evaluate Fred authority evidence for every new or changed Simpro blog, but add Fred content only when a selected source directly supports the section. Keep `Fred Voccola Authority Selection` in the validation sidecar, not public copy.

## AEO/GEO Map

Every `/write` plan and every moderate, major, or complete `/rewrite` plan must include:

| Field | Requirement |
|---|---|
| Main answer target | The core question the article answers |
| Capsule targets | H1 plus 60%+ major H2s |
| Selected PAA questions | Complete eligible questions selected by intent, without a fixed count; rewrite brief questions take precedence |
| PAA/FAQ provenance | Exact source kind, artifact or brief path/hash, query, date, status, eligible section, and selected questions |
| Source map | Source, claim, anchor text, target section |
| Metric Proof Pack | Metric requirement, Search log, Approved metric rows, public URL or local proof artifact, source-visible Evidence, Status: approved, intended Use, rejected candidates |
| E-E-A-T Proof Map | Experience proof, Expertise proof, Authority/Trust proof, case-study candidates, review-site VoC candidates, omitted unsupported claims |
| Customer Proof Pack | Pack status, Quote Matrix candidates, Case-study proof paths, Review-site experience evidence, Approved metrics, Use in copy, Claims excluded, approval status |
| E-E-A-T Strength Decision | Required for commercial-investigation blogs when no positive signal is selected: Applicability, Intent, Positive signals, Decision, Reason, Public copy boundary, Status, and optional approved SME review note |
| Fred Voccola Authority Selection | Mandatory only for connector-bound work: selector evaluation, ranked FVMI candidates, explicit selected-or-none decision, topical fit, intended use, source verification, embed decision, and VideoObject decision |
| Named Feature Status and Commercial Treatment | Exactly one current claim-status row per detected Lightning, RAIN, role-agent, scheduler, or roadmap specialist name |
| Review Story Selection | Required only when public copy paraphrases a review-derived E-E-A-T story; must include identity-backed selected story, public review URL, same paragraph link requirement, and exact quote boundary |
| Review Site Theme Selection | Required when public copy paraphrases a Capterra review-site theme without using an E-E-A-T story; must include Capterra tab row, public Capterra review-site URL, approved workflow theme, same paragraph link requirement, and exact quote/rating boundary |
| Early usable artifact | Filled data table, download link, checklist deliverable, or calculator reference planned within the first 300 words of body copy, or a documented not-applicable reason |
| AI citation target | Snippet, PAA, FAQ, comparison table, definition, or list |

## Publish Gates

A draft is publish-ready only when both gates pass:

- General content quality score: 85/100 or higher.
- SEO quality release floor: 90/100 or higher with zero critical SEO issues; 95/100 optimization target when honest, source-safe improvements exist.
- AEO/GEO score: 90/100 or higher.
- Validation sidecar: proof-only blocks must live in `research/validation-[topic-slug]-[YYYY-MM-DD].md`, not in public copy. Public artifacts must pass `data_sources/modules/public_artifact_guard.py --fail-on error` and must not contain an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, `Fred Voccola Authority Selection`, `Named Feature Status and Commercial Treatment`, `Vault Brand Language Alignment`, `Early Artifact Plan`, `Concrete Answer Check`, bracketed editorial labels, publication confirmation notes, unresolved availability notes, standalone TODO/TBD/TK markers, or structured data plan. Fenced examples, quoted source text, reader instructions, and canonical standalone media placeholders remain allowed. Hidden, blockquoted, inline, or shorthand media placeholders produce warnings that `/write`, `/rewrite`, or `/optimize` should normalize before handoff; those warnings do not block publish readiness.
- AI copy linting: `data_sources/modules/ai_copy_linter.py --profile simpro-web --fail-on error` blocks copy avoid-rule errors before publish readiness. Copy avoid-rule errors include modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences.
- Publish readiness runner: use the build -> preflight -> finalize -> final sequence in **Blog Assembly BOM and Two-Phase Seal**. A one-pass readiness call is invalid for blogs. Use the individual gates below only for debugging and policy-specific failures.
- URL validation gate: `data_sources/modules/url_validator.py --fail-on unresolved` must pass before scoring, `/optimize`, handoff, or publish. URL validation confirms destinations resolve; it does not prove the page supports the claim.
- Public research link guard: `data_sources/modules/public_research_link_guard.py --fail-on error` must pass before scoring or `/optimize`. It enforces machine-assigned citation modes, treats `manual_review` URLs as replacement-rule blockers, and requires a natural visible resolved non-owned link in the claim's paragraph when `inline_required` applies. Lower-risk claims follow `section_source_allowed`, `sidecar_only`, or `proof_not_required` as assigned.
- Optimization scoring expectation: `seo_quality_rater.py --validate-urls` and `/optimize` use 2 distinct non-owned authority sources as the standard-post baseline. Do not add a quota-only third source. Add as many further claim-fit, resolved sources as the evidence requires; required evidence has no maximum. Owned product links do not count as independent authority.
- Metric Proof Pack guard: `data_sources/modules/metric_proof_pack_guard.py --fail-on error` must pass before scoring or `/optimize`. Required topics need a Search log and at least one Approved metric with public URL or local proof artifact, source-visible Evidence, Status: approved, and intended Use.
- Numeric claim source guard: `data_sources/modules/numeric_claim_source_guard.py --fail-on error` must pass before scoring or `/optimize`. In addition to numeric claims, it blocks unsupported source-sensitive verbal quantities and comparisons such as single-digit or double-digit performance, number-word business sizes, average/most/majority business claims, and operator-group performance comparisons. Material numeric claims use `inline_required`: they need a natural public evidence link in the same paragraph or table row plus the machine-generated claim mapping required by the workflow.
- FAQ answer quality gate: `data_sources/modules/faq_answer_quality_guard.py --fail-on error` must pass when FAQ answers are present. The first visible paragraph must answer the question directly; generic deflections, missing answers, and unexplained binary answers block publish readiness. This is a mandatory AEO/GEO condition but does not reweight the existing 100-point score.
- FAQ proof gate: `data_sources/modules/faq_proof_guard.py --fail-on error` must pass when FAQ answers are present. It requires a first-paragraph authoritative non-owned public link for fact-driven or high-risk answers and validates the assigned lower-risk mode for other answers. A Source Map or FAQ Proof Map cannot replace a link required by `inline_required`.
- PAA provenance guard: `data_sources/modules/paa_provenance_guard.py --workflow-mode new|rewrite --paa-artifact [artifact] [--content-brief [brief]] [--answersocrates-blocker [artifact]] --fail-on error` always runs for blogs. Each visible FAQ question must match the bound eligible selected-question set exactly.
- Source support guard: `data_sources/modules/source_support_guard.py --fail-on error` must pass before scoring or `/optimize`. Evidence snippets must be visible in the cited source, and named customer metric claims must be approved in Customer Proof Pack Approved metrics.
- Customer proof diversity guard: `data_sources/modules/customer_proof_diversity_guard.py --fail-on error` must pass before scoring or `/optimize` when customer proof evidence is applicable to the binding branch. It verifies that case-study proof is not the only checked source route, that recently used or overused customer proof has a source-specific `Reuse reason`, that the sidecar includes `Customer Proof Selection Decision`, and that the applicable selector inputs from `customer-proof-index.json` and `customer-proof-usage-ledger.json` were respected, including selector-backed proof that no stronger underused approved proof fits the same role. Valid connector `no_fit_customer_proof` evidence can satisfy consideration only when public copy omits customer proof, named customer claims, review stories, exact quotes, testimonials, and customer metrics. Plain nonconnector AroFlo, BigChange, and ClockShark workflows with no Simpro signal omit vault-dependent selector evidence; supplying it is a pre-BOM blocker. Approved nonconnector customer proof instead requires hash-bound `simpro-nonvault-customer-proof-selector-evidence/v1` for the matching brand and public article.
- Selected customer proof mining: the customer proof diversity guard also requires `Selected Customer Proof Mining` whenever public copy uses customer proof, so selected proof is mined for quotes, metrics, POV/story, and workflow themes before final use is documented.
- Review story identity guard: `data_sources/modules/review_story_identity_guard.py --fail-on error` must pass before scoring or `/optimize`. It verifies that review-derived E-E-A-T story copy has an identity-backed `Review Story Selection`, a usable public review URL, and a same paragraph public link. It also verifies that Capterra review-theme copy has `Review Site Theme Selection`, `Source row ref: Capterra tab row [n]`, `Public review-site URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`, same paragraph source link, and no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved.
- E-E-A-T strength guard: `data_sources/modules/eeat_strength_guard.py --fail-on error` runs inside `/publish-readiness` for commercial-investigation blogs. It passes cleanly with selected customer proof, visible approved review-theme or review-story evidence, selected Fred authority, a named author, or an approved SME review note. If no positive signal exists, it passes only when the sidecar has `Decision: proof_unavailable_safe_to_publish` and emits warning `eeat_strength_safe_but_weak`. Missing or mismatched decisions are blocking. This guard does not change the AEO/GEO score formula.
- Fred authority guard: `data_sources/modules/fred_authority_guard.py --fail-on error` is a blocking `/publish-readiness` gate for Simpro blogs. It requires the complete `Fred Voccola Authority Selection` sidecar block, validates selected inventory and authority fields against the current manifest-backed vault, enforces exact quote and same-paragraph link evidence, restricts playlist assets to discovery or embedding, validates the privacy-enhanced responsive YouTube handoff, and requires `VideoObject` if and only if a video is embedded. A completed selection block without source-backed public use receives no AEO or E-E-A-T score credit.
- Early artifact guard: `data_sources/modules/early_artifact_guard.py --fail-on error` must pass before scoring or `/optimize`. A usable artifact — a filled data table, a download link, a checklist deliverable, or a calculator/tool reference — must start within the first 300 words of body copy. The only exemption is an `Early Artifact Plan` block in the validation sidecar with `Early artifact requirement: not applicable` and a Reason.
- Answer withholding guard: `data_sources/modules/answer_withholding_guard.py --fail-on error` must pass before scoring or `/optimize`. Placeholder table scaffolds block publish unconditionally with no exemption. When the target query implies a number, range, or template, the article must supply a concrete numeric answer early or a filled data table or download; a `Concrete Answer Check` block with `Concrete answer requirement: not applicable` and a Reason exempts only the numeric/template answer requirement, never scaffolds.
- Vault brand language guard: `data_sources/modules/vault_brand_language_guard.py --fail-on error` must pass before scoring or `/optimize` when Simpro product, feature, add-on, solution, industry, or related Simpro product URL language appears. It requires `Vault Brand Language Alignment` in the validation sidecar with connector evidence, context pack and receipt hashes, feature-specific `resource_id` values when named features/add-ons appear, solution or vertical `resource_id` values when solution/industry language appears, fallback blocker details if fallback mirrors were used, and `Status: aligned`.
- Named feature status guard: `data_sources/modules/named_feature_status_guard.py --fail-on error` is the blocking `Named Feature Status` gate. It requires `Named Feature Status and Commercial Treatment`, resolves current claim IDs through the vault, rejects unusable status or commercial evidence, and fails closed on unsupported public wording.

Use `--proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` with Metric Proof Pack, numeric claim, FAQ proof, PAA provenance, source support, customer proof diversity, review story identity, E-E-A-T strength, Fred authority, vault brand language, Named Feature Status, and content scorer commands so proof maps stay out of the article copy artifact.

The validation sidecar is the only approved place for proof maps and proof packs that are not publishable article copy.

## AEO/GEO Recovery Loop

An AEO/GEO score below 90/100 is a repair trigger, not a reporting endpoint. Unless the user explicitly requested a read-only audit, the LLM must continue in the same workflow:

1. Review every failed check in `aeo_geo.checks` and the scorer's `priority_fixes`.
2. Classify each failure as a public-copy gap, validation-sidecar/proof gap, or scorer or parser false negative.
3. If the article visibly satisfies the written requirement but scoring misses it, add a regression test and fix the scorer or parser false negative. Do not distort accurate, brief-approved copy to satisfy brittle matching.
4. Apply the top 3-5 fixes that address root causes. Do not invent PAA questions, claims, proof, metrics, quotes, or customer experience to gain points.
5. Treat every edit as a mutation. Rerun `/scrub` and Context Binding, rebuild the provisional BOM, run preflight, finalize only after it passes, then run detached final readiness using the Blog Assembly BOM and Two-Phase Seal sequence.
6. Repeat once if needed. If AEO/GEO remains below 90/100 after 2 iterations, leave the article in place, write a machine-readable blocker under `research/` with the score, failed checks, attempted fixes, and any external evidence or authority blocker, then return nonzero.

`/optimize` is allowed inside this recovery loop when all proof, source, URL, and public-artifact gates pass but content quality, SEO release floor, SEO advisory target, or AEO/GEO does not. Final handoff still requires content quality of at least 85/100, SEO quality release floor of at least 90/100 with zero critical SEO issues, AEO/GEO of at least 90/100, and every blocking gate to pass. When SEO is 90-94 after one target-safe pass or no honest SEO fix is recommended, record `release-pass, below-target` and keep the artifact publishable.

Below-threshold drafts route to machine repair. If still blocked after the allowed repair cycles, write a machine-readable blocker under `research/` with notes explaining failed checks.
