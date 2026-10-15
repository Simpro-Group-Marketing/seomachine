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

For connector-bound workflows, run vault health first, describe available roles/topics/entities, search in the task's natural language, read and expand results by `resource_id`, query approved claims only when public proof-sensitive language is needed, then build and validate a context pack. Write `research/context-build-spec-[slug]-[date].json` from `config/context-build-spec.example.json`, then run `python -m data_sources.modules.context_build research/context-build-spec-[slug]-[date].json`. If the run stops (memory pressure, timeout), rerun with `--resume`; finished packs that still validate are reused and never rewritten. Stage `claim_requests`, claim lookups, and any proof-boundary text must come from the current topic's selector slate and claim lookups, never from the example or another topic.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault connector exposes them as source evidence.

The repo-local context files are downstream operational state only and are never an active or fallback source for Simpro work. If vault MCP operations are absent, use the one enabled `simpro-context@simpro` installation whose `projectPath` matches this repository through `SimproVaultClient`, regardless of its reported version. Determine compatibility from `vault_status` and the required operation contracts. Never use an installation attached to another repository, worktree, or branch checkout. If both connector paths fail, stop and document the exact vault blocker in the research brief.

Required evidence: the production BOM records the binding branch, which the builder decides from the BOM spec content. A connector-bound BOM binds the context pack and receipt and the connector customer-proof selector evidence, and its proof items must be approved claims in that receipt. A nonconnector AroFlo, BigChange, or ClockShark spec carries `not_applicable_context_reason`, binds `simpro-nonvault-customer-proof-selector-evidence/v1`, and carries no context pack, receipt, Fred evidence, or vault-dependent customer-proof selector evidence; nonvault proof is allowed only under the separate non-vault eligibility contract below. A spec with a Simpro signal, an unknown brand, or malformed metadata is connector-bound. Missing required evidence refuses the BOM build, which blocks `/write` and the release. `Vault Brand Language Alignment` (connector-bound product, feature, add-on, solution, industry, or related Simpro product URL language), `Competitive Shortlist Decision` (competitor-aware posts), and `Named Feature/Add-On Link Check` (named Simpro features/add-ons) are private research notes that cite `context_pack_hash`, `receipt_hash`, `resource_id`, `claim_id`, use mode, public URL when required, and relevant revisions; they shape the BOM spec, and the release does not read them.

## Author-Led Blog Voice

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

Author metadata controls public identity, Person schema, and whether first-person author voice is allowed; it provides zero Expertise and zero Experience credit without selected, source-visible evidence that satisfies the corresponding proof boundary.

When `author_policy.status` is `no_author` or the legacy value `not_provided`, first-person singular author judgment outside quotes is prohibited.

## Named Feature Status And Commercial Treatment

When public copy names Lightning, RAIN, a current role agent, Intelligent AI Scheduler, or a roadmap specialist, check each name's current status and commercial treatment through connector claims before drafting. An optional private note in the validation sidecar can record one row per detected name under `Named Feature Status and Commercial Treatment`.

```markdown
## Named Feature Status and Commercial Treatment

| Name | Capability claim ID | Commercial claim ID | Release status | Commercial treatment | Region or account boundary | Public wording decision |
|---|---|---|---|---|---|---|
```

Allowed release statuses are `current_public_context`, `preview`, `target_timed`, `roadmap`, and `not_publicly_available`. Allowed commercial treatments are `included`, `package_required`, `add_on_or_upsell`, `mixed`, and `not_asserted`. Supplied claim IDs must resolve uniquely through current connector claim results and the validated context receipt. Internal-only, expired, superseded, missing, and do-not-use evidence blocks public use. Commercial treatment requires a usable commercial claim ID. `not_asserted` is valid only when public copy makes no inclusion, package, price, upgrade, or upsell statement. Unusable current evidence requires `omit`. Intelligent AI Scheduler requires its current capability claim, `target_timed` qualification, and the RAIN Lightning requirement claim. Pulse remains blocked until a current usable claim supports its public roadmap name and treatment.

Keep this table in the validation sidecar as a private research note; the release does not read it. Public status or commercial wording for a named feature still needs a BOM fact or approved proof item, linked where the claim appears.

The routing policy is enforced through the production BOM's binding branch, the context-boundary policy, and the release's truth checks, without a duplicate routing sidecar block. For connector-bound work, brand, audience, ICP, product, feature, add-on, solution, industry, Lightning, competitor, Hindsight, customer proof, quotes, metrics, review stories, ebooks, E-E-A-T sources, writing exemplars, and approval status data must come from the Brand Vault connector. Repo `context/` owns SEO mechanics, AEO/GEO workflow, schema notes, publish gates, internal-link routing, keyword snapshots, AI citation targets, generic CRO guidance, and brand-neutral editorial mechanics only.

## Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: connector-bound competitor-aware posts decide the shortlist from connector evidence; an optional private note can record selected competitors, rejected competitors, connector-discovered competitive-context resources, approved claim IDs where public proof is used, and why the shortlist fits the article objective. Nonconnector AroFlo, BigChange, and ClockShark posts base the shortlist on task-approved, public official sources without vault resource or claim IDs.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified through the claim registry. Keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked through connector-discovered product and feature resources before link decisions. The selected `resource_id` values, link decision, and reason can be kept as an optional private note in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from connector-discovered vault guidance. Use semantic search/read/expand for messaging, positioning, feature, solution, and vertical context. When a named feature/add-on appears, include feature-specific `resource_id` evidence; when solution/industry language is used, include solution or vertical `resource_id` evidence. An optional `Vault Brand Language Alignment` note in the validation sidecar can record the connector evidence, language applied, and source-verification boundary; it is never public copy, and the release does not read it. Connector unavailability blocks brand-language use.

Optional `Vault Brand Language Alignment` note shape:

```markdown
## Vault Brand Language Alignment
- Article title: [title]
- Product/solution language scope: product/feature | solution/industry | mixed
- Vault connector evidence: [vault_status/vault_describe/vault_search/vault_read/vault_expand operations used; context_pack_hash; receipt_hash; messaging/positioning resource_id values; feature resource_id values when named features/add-ons appear; solution or vertical resource_id values when solution/industry language is used; claim_id values for proof-sensitive public language; manifest/revision values]
- Product/feature language applied: [category, product naming, value pillar, workflow phrase, avoided terms]
- Solution/industry language applied: [vertical profile, audience, work environment, guardrails, or not applicable]
- Local brand fallback: none; connector unavailability blocks brand-language use
- Claims requiring source verification: none | mapped in Source Map / Customer Proof Pack / Metric Proof Pack
- Status: aligned
```

This block validates vault language alignment only. It does not approve claims, pricing, metrics, proof, customer outcomes, competitive statements, quotes, rankings, or ratings; those still route through Source Map, Customer Proof Pack, Metric Proof Pack, and the existing proof gates.

Use this file for blog workflows only. It supports `/research`, `/research-serp`, `/write`, `/analyze-existing`, `/rewrite`, and `/optimize`; it does not replace marketing skills.

## Native Blog Workflow, Production BOM, and Release

Command ownership:

- `/research` owns the research brief, the production BOM spec, and the production BOM. It does not write public blog Markdown.
- `/analyze-existing` owns the analysis report and rewrite routing. It does not write public blog Markdown.
- `/write`, `/rewrite`, and `/optimize` own public blog copy.
- `/scrub` owns read-only diagnostics.
- `/publish-readiness` owns the scorecard: it runs the one-pass release and is the sole publish/no-publish verdict.

`/write`, `/rewrite`, and `/optimize` own public blog copy. Python does not draft, rewrite, or patch Markdown in `drafts/`, `rewrites/`, or `published/`.

Python remains responsible for governance and workflow assistance: the article layout and run id, context packs and receipts, selector evidence, the recorded Semrush keyword decision and shortlist, SERP evidence and the page-1 coverage map, the PAA artifact, the production BOM build, the release record, and publisher transport payloads.

`/scrub` is read-only diagnostics. If scrub diagnostics find Unicode marks, em dashes, or whitespace issues, the command/agent applies the copy edit and reruns `/scrub`. The scrubber must not overwrite the article.

Mandatory release loop: every new or changed blog run must include `/scrub`, a release through `/publish-readiness`, `/optimize` after the first release record, and a final release whose record passed for the exact article bytes being handed off. On a blocked release, revise from the record's blocking findings and release again. `/optimize` makes no edits when the release passed and no source-safe priority fix exists. Score absence is a workflow blocker unless the release stopped before scoring; in that case, report the stop reason exactly and do not present the article as ready.

### Production BOM

Every new or changed blog is written from a production BOM, `research/production-bom-[slug]-[YYYY-MM-DD].json` (schema `simpro-production-bom/v1`). Paths derive from the article path `drafts/[slug]-[YYYY-MM-DD].md` or `rewrites/[slug]-[YYYY-MM-DD].md`, dated with today's UTC date: AnswerSocrates records its UTC capture date as `collection_date`, which must equal the article date; the run state `research/runs/[slug]-[YYYY-MM-DD].json` holds the production `run_id` and the hash of the BOM the pipeline last wrote. `/research` runs `python -m data_sources.modules.production.layout [article]` first, which prints every path and mints the run id, so the PAA capture can be recorded under that run id.

The BOM holds identity (slug, date, run id, brand, market, workflow mode, article path, title, objective, audience, CTA, schema notes), the keyword decision and shortlist, the SERP query and page-1 coverage, sections, facts, proof, PAA questions, links, the context binding or its not-applicable reason, and the customer-proof selector evidence. Every bound artifact carries its path and sha256.

The BOM is honest by construction. Claude writes the judgment in `research/production-bom-spec-[slug]-[YYYY-MM-DD].json` (schema `simpro-production-bom-spec/v1`), and `python -m data_sources.modules.production.bom_build [article]` admits only what it can verify:

- a fact only when its exact quote is on the live page at build time (or, only when that live fetch is blocked, in the hash-bound Chrome page capture of that exact URL under the capture exception in Source Map and BOM rules), the quote supports the claim, and every number in the claim is in the quote;
- a proof item only when its claim ID is an approved claim in the validated context receipt and a selected candidate in the customer-proof selector evidence; nonconnector brands take proof only from approved rows in `config/nonvault-customer-proof-index.json` selected by the nonvault selector;
- a PAA question only when it is in the eligible questions of the PAA artifact captured for this run id on the article date;
- a commercial pillar link only when its destination ID and canonical URL match a valid record in `context/commercial-pillar-index.json` and its anchor contains that record's main keyword; connector-bound work needs exactly one, marked `must`;
- the keyword and SERP blocks only from the artifacts `keyword_record` and `serp_coverage` wrote.

Each section, fact, proof item, PAA question, and link is marked `must` or `should`. A refused build lists every reason, exits `1`, and moves any earlier BOM aside as `.refused`, so it cannot be released.

Subagents speed up research and review but never decide what is true. `/research` runs parallel lanes for vault context and approved proof, page-1 coverage, PAA capture, and source facts; Semrush stays one lane because it needs one Chrome session. `/write` and `/rewrite` use one writer for voice, then parallel advisory reviewers (editor, SEO, AEO, fact-check) whose findings the writer applies. Subagents never write public copy and never add a BOM entry the builder has not verified.

Earlier governance artifacts (`simpro-blog-editorial-plan/v2`, `simpro-blog-plan-fulfillment/v1`, `simpro-blog-assembly-bom/v4`, machine-review JSON, stage and wording-edit receipts, optimizer output, and readiness outputs) remain readable history. The release does not read them, and they cannot authorize a new release.

Private research notes live in the research brief and, where a policy below names a sidecar block, in the validation sidecar `research/validation-[topic-slug]-[YYYY-MM-DD].md`. Neither is a release input, and neither replaces a BOM entry: a fact, proof item, PAA question, or link reaches public copy only through the BOM.

Hindsight Strategy Selection is a private research note. If Hindsight is not relevant, record `Status: not_applicable` or omit it. If Hindsight internal strategy informs the plan, record `public_claim_use: prohibited` and `claim_support_allowed: false`, and do not cite it in public copy. Permitted use is private strategy shaping only: reader angle, section emphasis, section purpose, objections to answer, and commercial framing. The writer may execute the Hindsight-informed angle already recorded in the research brief, but cannot introduce new Hindsight-derived claims or a new unplanned angle inside public prose. Hindsight never becomes a BOM fact, proof item, PAA question, or link.

For commercial-investigation blogs, valid `no_fit_customer_proof` selector evidence prevents invented customer proof but does not by itself make the page strong. At least one positive E-E-A-T signal should be selected when available: selected customer proof, visible approved review-theme or review-story evidence, a verified Fred authority fact, named author, or an approved SME review note. If none exists, record this decision in the validation sidecar as a private note; the release does not read it:

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

### Release and release record

`/publish-readiness [article]` runs `python -m data_sources.modules.production.release [article]`. It refreshes the customer-proof selector evidence so it is same-day, rebuilds the BOM (re-verifying every fact quote), then runs the truth and coverage checks concurrently with scoring, and writes one `release-record.json` (schema `simpro-release-record/v1`) in `research/releases/[slug]-[YYYY-MM-DD]-[run8]-[n]/`. The record holds the article, BOM, spec, and evidence hashes, every finding with its check, severity, and line, the three scores with their gates and priority fixes, and `passed`. Exit `0` is passed, `1` is blocked, and `2` is an operational or argument error. `SEOMACHINE_RELEASE_WORKERS` (default `2`) or `--workers` sets the pool size; `1` runs sequentially.

Only the latest release record counts: it must have passed, and the article, BOM, spec, and every bound artifact must still match the hashes it recorded. Any edit after a pass needs a new release. Release never writes the customer-proof usage ledger. The WordPress and Grav publishers check the latest release record before every blog publish and record the customer-proof use in `config/customer-proof-usage-ledger.json` after a successful live publish; when publishing outside them, record it before final handoff, as `.claude/rules/customer-proof.md` requires.

Release records verify source artifacts only. They do not claim CMS or rendered-page verification. Rendered canonical, indexability, schema deployment, Core Web Vitals, mobile rendering, image accessibility, and CMS link checks belong to launch QA until a separate rendered-page gate exists.

`/publish-readiness` owns the scorecard. Blog release requires:

- Content quality score of 85/100 or higher.
- SEO quality release floor of 90/100 or higher with zero critical SEO issues.
- AEO/GEO score of 90/100 or higher.

SEO quality optimization target is 95/100. Scores from 90 to 94 remain publishable when critical issues are zero, but `/optimize` should attempt one honest, source-safe improvement pass only when the fixes improve reader usefulness, search clarity, proof support, or structure. Do not force keyword stuffing, unsupported claims, brief drift, or scorer-gaming to hit 95.

An AEO/GEO or content score below threshold is a repair trigger, not a reporting endpoint. SEO below the 90/100 release floor or any SEO critical issue is blocking even when the content score passes.

## Post-Publish Performance Measurement

`/research-performance` without a target retains its queue-only Markdown output at `research/performance-review-[YYYY-MM-DD].md` and does not create a target receipt. A target-specific `/research-performance [URL-or-path]` writes the matched advisory pair `research/performance-review-[slug]-[YYYY-MM-DD].md` and `research/performance-receipt-[slug]-[YYYY-MM-DD].json` after resolving canonical identity, objective, conversion definition or not-applicable reason, success measure, owner, review date, a primary window, and its equal-length immediately preceding comparison window. Supplemental windows are optional.

Write and finalize the Markdown report first, then build and check the JSON with `post_publish_measurement_receipt.py build --metadata ... --performance-report ... [--article ... --final-bom ...] --output ...` and `post_publish_measurement_receipt.py check [receipt] --performance-report ... --fail-on error`. The validator checks exact rendered report headings against receipt status, requires exact blocked source identity and blocker values in data-only blocked rows, rejects metrics from blocked first-party lanes, and requires non-empty observed values for the documented metrics. Fenced examples and HTML comments do not satisfy report evidence. The receipt binds a current local article and its archived pre-production final BOM, if one exists, as `release_artifact` only when its canonical path ends with the BOM-bound editorial-plan URL slug. Articles built through the production BOM use `live_url`, which requires canonical identity verification, `verified_at`, `verification_method: live_canonical_observation`, and the limitation that no local release artifact was available. It records `verification_scope: recorded_observation_metadata`.

Keep source lanes separate: GSC is search-performance truth, GA4 is behavior/conversion evidence, and third-party tools are optional opportunity/SERP context that never satisfy first-party observation. Record property IDs, exact target filters, UTC retrieval times, limitations, and exact source-specific blockers. Emit `observed` only with at least one observed first-party lane. Otherwise emit `blocked` and preserve the lane blockers. A blocked target report is limited to `Scope and evidence`, `Data-quality and causality limits`, and exact per-source blockers and limitations. A blocked target report contains no opportunity queue, diagnosis, recommendation of any kind, verdict, recommended action, owning-command or other workflow handoff, or success claim.

The report and receipt are advisory internal evidence, not public-claim proof, not customer proof, not a production BOM input, not a `/publish-readiness` input or gate, and not a release requirement. They are never public proof or authorization to edit copy or post externally. Their hashes validate recorded observation metadata and current artifact bindings, not external analytics truth or causal claims.

## PAA Provenance and Intent-Driven FAQ Policy

- Every new article and rewrite requires a PAA capture recorded under the production run id on the article date, even when no FAQ is useful: a structured AnswerSocrates artifact or, when AnswerSocrates is unavailable, the Google SERP PAA fallback.
- The production BOM admits a FAQ question only from that capture's eligible questions, and the release blocks any visible FAQ question that is not a BOM PAA question.
- Rewrites follow the same rule: there is no pre-picked brief precedence. Existing FAQ questions that the run's capture does not contain are removed or turned into body sections.
- When AnswerSocrates shows a genuine blocked state (login, CAPTCHA, quota, or unavailability), record the Google SERP PAA fallback: the Google results page's "People also ask" questions for the same query, together with the observed AnswerSocrates blocker (see Google SERP PAA Fallback). The BOM build refuses a bare blocked AnswerSocrates artifact, because the release scorer accepts only a collected capture or the fallback. A user CSV cannot supply FAQ questions to the production BOM.
- Outside that recorded fallback, SERP, Reddit, and YouTube are supplemental research and cannot satisfy PAA provenance.
- Match source kinds exactly. Reject stale artifacts, mismatched queries or dates, keyword fragments, and questions found only outside the eligible question section.
- Record `FAQ policy: required | not_applicable` in the research brief. `required` applies when the BOM spec selects useful PAA questions. `not_applicable` requires a non-empty rationale.
- Run FAQ answer-quality, proof, `FAQPage`/`Question`/`Answer` schema, and FAQ scoring only when visible FAQs exist.

## Research Plan and BOM Spec

Every new or changed blog is planned by `/research` for new work, or by `/analyze-existing` findings plus the `/research` BOM process for rewrites, rather than by a parallel Python writing system. The research brief carries:

- the complete Reader Contract;
- the searcher task, intent class, funnel stage, dominant and selected content type, and format decision from the SERP evidence;
- the commercial pillar decision, the existing overlapping URLs checked, and a cannibalization decision, where `update_existing` and `consolidate` prevent a new article;
- section throughlines with reader question, payoff, and adjacent-section bridges;
- at least 1 original contribution and the section that delivers it;
- primary and supporting entity coverage mapped to sections without density targets;
- the lifecycle: volatility and next review date;
- `FAQ policy: required | not_applicable` with its rationale.

The BOM spec carries what the release checks: sections with their purpose and `must` or `should` priority, chosen from the page-1 coverage map and the article's own contribution; facts; approved proof; PAA questions; links, including the commercial pillar link and intent-appropriate internal links within the 3 to 5 standard-blog target; the CTA; and schema notes. The keyword decision and shortlist come from `keyword_record`, bound to the saved Semrush transcript.

During `/research` and `/analyze-existing`, consult `context/site-architecture-map.json` when the article needs homepage, industry, solution, or feature cluster context, especially for AUS-oriented Simpro blog planning. Use it to identify candidate cluster URLs and nearby supporting pages before the BOM spec fixes internal-link intent. Treat it as guidance-only sitemap inventory: commercial pillar ownership still comes only from `context/commercial-pillar-index.json`, editorial link treatment still comes from `context/internal-links-map.md`, and the site architecture map cannot support keyword ownership, Semrush evidence, product claims, customer proof, page performance, public claims, or publish readiness.

Rewrites record evidence-bound preserve, update, add, and remove decisions from `/analyze-existing` in the brief. Audience-language research is conditional: use genuine Reddit, YouTube, or trade-community language only when it improves reader comprehension, never as regulatory, product, metric, PAA, or public-claim proof. Regulatory and licensing articles default to `not_applicable` unless the brief explicitly requests audience-language research. When the brief requires an exact internal-link count, it may replace the 3 to 5 default supporting-link target but can never exceed the hard maximum of 7. For single-trade Simpro posts, the matching industry-cluster link remains additive unless the brief explicitly prohibits the industry page.

The writer chooses final language independently. Coverage checks that every `must` section, fact, proof item, PAA question, and link is present; the editor and content-analyzer reviewers judge whether each section accomplishes its planned purpose.

## Semrush Keyword Decision Contract

Every new or changed SEO/AEO blog requires a machine-readable `simpro-semrush-keyword-decision/v1` artifact at `research/semrush-keyword-decision-[topic-slug]-[YYYY-MM-DD].json` before optimization decisions are finalized. When the task requires Semrush UI, use the authenticated Semrush UI in the main Chrome profile through the running client's live-browser tools, and record `execution_surface: semrush_ui_chrome_main_browser` and `client: claude_code` or `client: codex` in the report parameters. Do not substitute Semrush API, MCP, stale repo keyword tables, or estimates for current opportunity and SERP feasibility decisions. Existing `context/target-keywords.md` may inform seed terms only.

Default Semrush databases by brand and market:

- Simpro: `us` for the US market; `au` for the AU market
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

Save the verbatim captured Semrush page text and record the decision with `python -m data_sources.modules.production.keyword_record`, which writes the decision and a keyword shortlist only when every candidate metric appears next to its keyword in the saved transcript. The production BOM binds the decision and shortlist by path and hash and copies the primary keyword, secondary keywords, and shortlist; the release checks the primary keyword in the title, H1, and first 100 words.

If the main Chrome Semrush UI opens but DOM or screenshot extraction times out or resets, record `blocked_semrush_ui_refresh` and stop before the BOM build. The blocker proves the UI lane was attempted, but it does not satisfy the current keyword decision requirement.

## SERP Evidence Collector Provenance

`research_serp_analysis:playwright` and `research_serp_analysis:chrome_connector` are both approved SERP evidence collectors, but they do not carry equal provenance strength. `playwright` requires `raw_response` to be the exact CLI text the tool printed, so the evidence is a machine-captured artifact. `chrome_connector` accepts a structured mapping assembled from what the connector observed on the results page; that mapping is agent-transcribed browser observation, not raw tool output, and no automated check can distinguish a faithful transcription from a fabricated one.

Use `chrome_connector` only when a live browser session (already authenticated, human-driven navigation) is the only way to reach the locale or surface needed, and record it as such rather than presenting it as an equivalent-strength capture. This is a documented boundary, not a defect: `execution_attestation.py` itself states its HMAC signature is a local integrity check, not a claim that a remote publisher signed the underlying data, so no SERP evidence collector proves more than "this workspace attests it collected this."

The same caveat applies to a Chrome page capture of a fact page that blocks bots (see the capture exception in the Source Map and BOM rules): its receipt proves the text is unchanged since capture, not where the text came from, and its `surface` and `client` values are self-declared. Record it as such rather than as a machine-captured page.

### Live-browser surface

Browser steps in this repo run in the user's main Chrome window, already signed in where a site needs it, through the running client's live-browser tools: Claude-in-Chrome in Claude Code, the Chrome browser backend in Codex. The steps are the same in both clients: open the exact URL, read the page text or the named DOM attributes, never retype or summarize what the page shows, and confirm saved text against the live tab before recording it. Every browser capture records the client that made it: the recorders `page_capture`, `browser_capture`, and `google_paa` require `--client claude_code` or `--client codex`, URL allowlist entries carry `"client"`, and Semrush report parameters carry `client`. The value is self-declared; a recorder running inside Claude Code refuses `codex`. Captures made before the field shipped (2026-10-15T18:38:35Z) read as `unrecorded`; a later record without a client is refused.

## Required Variable Resolution

Before drafting with `/write` or `/rewrite`, resolve these variables from the user prompt, research brief, generated vault context binding, and allowed repo-local SEO/AEO/editorial/link-map inputs. `/analyze-existing` must audit which inputs are present, missing, or blocked before a rewrite proceeds.

| Variable | First source | Fallback |
|---|---|---|
| `topic` | User prompt or topic file | Ask the user |
| `audience` | Connector-discovered messaging and vertical resources | Stop if unavailable for Simpro brand work |
| `main_question` | SERP/PAA intent, title, or brief | Ask if no clear primary question exists |
| `related_questions` | Structured AnswerSocrates artifact captured under the production run id, for new articles and rewrites alike | The Google SERP PAA fallback when AnswerSocrates records a blocker; no pre-picked brief precedence and no CSV fallback |
| `tone` | Connector semantic search and `resource_id` reads for current messaging and style guidance | Stop if unavailable for Simpro brand work |
| `expertise` | Connector-discovered product/workflow resources and approved claims, plus verified expert sources | Ask if a named author/reviewer is required and missing |
| `length` | Complete Reader Contract, verified intent, and available evidence | Keep the scope intent-complete without competitor-derived or universal word targets |

Do not synthesize facts, search volume, PAA questions, customer claims, or expert quotes. If the repo and live research do not provide an input, ask for it or mark it as missing.

## Existing-Content Rewrite Use

For `/analyze-existing`, audit whether the current post has the strategy inputs needed for a safe rewrite: main answer target, related-question provenance, source-backed claims, Source Map, E-E-A-T proof, direct-answer opportunities, capsule opportunities, schema notes, and quality-gate risks.

For `/rewrite`, resolve the same variables before drafting. Reuse existing strategy artifacts only when they match the post topic and current rewrite direction. Collect a current PAA capture under the production run id (AnswerSocrates, or the Google SERP fallback when it is unavailable); existing FAQ questions that it does not contain are removed or turned into body sections. If source-backed claims or proof are missing, collect them or mark the blocker before writing.

Do not invent replacement questions, customer proof, author names, reviewer names, search-volume data, ranking data, or external claims to fill rewrite gaps.

## E-E-A-T Proof Map

Every `/write` and `/rewrite` plan should decide its Experience, Expertise, and Authority/Trust proof in the research brief before drafting; the release renders the scorers' E-E-A-T Proof Map from the BOM. `/analyze-existing` must report Experience proof present/missing, Expertise proof present/missing, case-study proof candidates, Review-site VoC candidates, review-site experience evidence candidates, and claims that must stay out because proof is missing.

| Dimension | Approved inputs | Public-copy rule |
|---|---|---|
| Experience | Customer case studies, customer outcomes, identity-backed Review Story Selection rows, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples | Cite the public case-study URL, approved review-site/source URL, or verified source page. Review-derived E-E-A-T stories need a public review URL in the same paragraph as the paraphrase. Do not cite internal context language. |
| Expertise | Product/feature knowledge, source-backed workflow explanations, source-visible expert evidence, and Simpro workflow specificity | Use Simpro product/workflow links and source-backed explanations. Do not invent author, reviewer, or expert claims. |
| Authority/Trust | Public research, case-study URLs, review-site/source links, limitations, caveats, and no invented proof | Follow the claim's machine-assigned citation mode. For `inline_required`, use a natural descriptive anchor to the public source in the claim's paragraph; lower-risk claims may use `section_source_allowed`, `sidecar_only`, or `proof_not_required` when assigned. |

Required proof sources:
- Discover customer, review, product, competitor, and expert evidence through connector search/read/expand by `resource_id`.
- Use `vault_claims` for every public metric, quote, review theme, customer outcome, or other proof-sensitive passage; the selected claim must be present in the validated context pack and receipt.
- Use the claim registry's public URL and source-visibility decision for public citations. Repo-local proof indexes and ledgers are operational selection and reuse state only; they cannot approve a claim or override the connector.
- Connector-backed metrics are valid only when the context pack carries an approved claim, permitted use mode, public proof URL, and source-visible evidence anchor. Public copy must link to the public case study, review site, or source URL, not to internal context files.
- Every public metric must be a BOM fact whose verified quote contains the number, or an approved BOM proof item. The release blocks a material number that is not in a BOM fact quote or proof item linked in the same paragraph.
- Every external factual, comparative, causal, commercial, absolute, or guarantee claim needs a BOM fact: the builder admits it only when the exact quote is on the live page (or, only when the live fetch is blocked, in the hash-bound Chrome capture of that exact URL) and supports the claim, and the release blocks a claim that cites a source outside the BOM. A link alone does not prove the proposition. Explicit first-person opinion, direct imperative instructions, and non-outcome explanatory scenarios need no fact. Do not write unsupported outcome promises such as always, never, eliminates, guarantees, and ensures.
- Each visible FAQ question must be a BOM PAA question, copied from the PAA capture recorded for the production run (AnswerSocrates, or the Google SERP fallback). Proof links and supplemental SERP, Reddit, and YouTube research do not prove PAA provenance.
- Do not write source/proof meta-commentary in public copy, such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.

## Metric Proof Pack

Every `/research`, `/write`, `/analyze-existing`, and `/rewrite` workflow for software, comparison, pricing, cost, ROI, KPI, profit, margin, guide, or vs topics must search for usable public numbers before drafting. Numbers enter public copy only as BOM facts or approved proof. Keep the search log and rejected candidates as a private note in the validation sidecar when they help later research.

Optional Metric Proof Pack note shape:

```markdown
## Metric Proof Pack
- **Metric requirement**: required / not applicable
- **Reason**: [required only when not applicable]
- **Search log**: [public pages and hash-bound source-capture receipts checked for usable numbers]
- **Approved metric**: [metric claim] | URL: [public proof URL or source-capture receipt for the cited public source] | Evidence: "[source-visible Evidence]" | Status: approved | Use: [intended use]
- **Rejected metrics**: [candidate metric, source checked, reason excluded]
```

The release does not read this note. The truth check proves every material number in the final article against a BOM fact quote or proof item linked in the same paragraph.

## Review-Site Experience Evidence and VoC Routing

Public review sites are approved for sourced review-site experience evidence, VoC themes, and competitor-review themes. Approved surfaces include G2, Capterra, Software Advice, GetApp, TrustRadius, Gartner/Gartner Digital Markets, Trustpilot, app stores, and Google reviews.

Review narratives are first-hand customer experience when reviewers describe product use, implementation, support, switching, pains, outcomes, or workflows. Review-site themes can inform VoC research, but they do not satisfy E-E-A-T story proof unless the story is an approved `experience_story` proof item in the BOM, identity-backed by a real person or business with a usable public review URL, and the article links that URL in the same paragraph as the paraphrase.

For Capterra rows that fit a blog topic but do not need an E-E-A-T story, the theme reaches public copy only as an approved `theme` proof item in the BOM, and public copy may paraphrase it only when the same paragraph links the Capterra review-site URL. An optional `Review Site Theme Selection` note can record `Platform: Capterra`, `Source row ref: Capterra tab row [n]`, `Public review-site URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`, and `Workflow theme`. Limits: no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved.

Use review sites for sourced VoC themes, objections, switching triggers, implementation or support themes, competitor-review themes, and first-hand customer experience patterns. Default to theme-level citation: cite the theme and link to the relevant review, profile, category, or comparison page.

When a brief uses review-site experience evidence, capture platform, URL, date checked, product/competitor, experience pattern, evidence summary, and whether any exact quote/rating claim was approved. When public copy uses a review-derived experience story, the selector picks it (role `experience_story`) before drafting, and the story must be a BOM proof item. This optional private-note shape records the choice:

```markdown
## Review Story Selection
- **Article title**: [title]
- **Content objective**: [objective]
- **Selector command**: automatically run python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[slug].json" --context-receipt "research/context-receipt-[slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles experience_story --require-eeat-story --limit 10
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

E-E-A-T stories are optional, and E-E-A-T story usage is optional in public copy. experience_story consideration is required whenever customer proof appears in public copy. Use a proof-backed customer/review POV only when it improves the article objective. A named public POV must be an actual person or business POV from approved customer proof, a public case study, Quote Matrix route, reference, customer story, or review-site row, admitted as a BOM proof item and linked to its public source when used in copy.

Review-theme evidence is VoC only unless it is identity-backed and link-backed through `Review Story Selection`. Unnamed workflow scenarios are explanatory only and do not count as E-E-A-T proof; fictional named personas are prohibited.

## Customer Proof Pack

Every `/research`, `/write`, `/analyze-existing`, and `/rewrite` workflow must select task-specific customer proof through the selector, and the BOM must admit it, before placing direct quotes, named customer proof, approved metrics, or review-derived Experience patterns in public copy. Keep proof inventories external to repo `context/`; do not bulk-load proof sources into local mirrors.

For Simpro connector-bound work, run task-specific vault claim searches for `public_metric`, `exact_quote`, and `public_paraphrase`. Use only approved claim results bound to the current context pack and receipt. If a case study, ebook, quote, review theme, or customer story is discoverable but lacks an approved claim for the intended use, report a vault claim-promotion blocker and omit the proof.

Before selecting customer proof for connector-bound work, the command workflow must resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[slug].json" --context-receipt "research/context-receipt-[slug].json" --evidence-output "research/customer-proof-selector-evidence-[slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10` against the layout's public context pack and receipt (the pack the BOM build approves proof from) before drafting customer proof. The selector evidence file is the record of the slate; keep any `Customer Proof Slate` note privately in the research brief. "Consult" means reviewing generated selector output, not skipping execution. If complete, non-truncated claim searches prove no eligible approved claim for the role and the article will use no customer proof, rerun the same full-role slate with `--allow-no-proof`; valid no-fit evidence records `selection_outcome: no_fit_customer_proof`, represents metric, quote, theme, and experience_story, sets each role to `Selected: [none]`, and states that public copy must omit customer proof. If inputs are missing, resolve them from the brief, context request, context pack, or receipt, or stop before drafting customer proof. If the selector fails for any other reason, record the failure or blocker in the research brief and do not invent proof. The selector uses approved claim results from the current context pack and receipt, plus the operational usage ledger at `config/customer-proof-usage-ledger.json`. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the claim ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `config/customer-proof-usage-ledger.json`, rerun selector checks, and document the backfill in the research brief. Choose the most relevant approved claim, not the easiest searchable case study. experience_story consideration is required and E-E-A-T story usage is optional; if no story fits, use `Selected: [none]` with section-specific rejection reasons. Edit selected/rejected rows only when editorial judgment requires it. If a recently used or overused proof source is still the best proof, record a `Customer Proof Selection Decision` note in the research brief with a source-specific `Reuse reason` plus selector-backed proof that no stronger underused approved claim fits the same role.

For nonconnector AroFlo, BigChange, and ClockShark work, never run the vault-dependent selector. Public customer proof is allowed only when an approved nonvault inventory row in `config/nonvault-customer-proof-index.json` satisfies the separate non-vault eligibility contract and the workflow runs `python data_sources/modules/nonvault_customer_proof_selector.py "[topic]" --brand "[brand]" --title "[title]" --objective "[objective]" --article-slug "[slug]" --index config/nonvault-customer-proof-index.json --ledger config/customer-proof-usage-ledger.json --evidence-output "research/nonvault-customer-proof-selector-evidence-[slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`. The emitted artifact must use `simpro-nonvault-customer-proof-selector-evidence/v1` and bind the brand, topic, title, objective, article slug, reference date, roles, selected and candidate proof IDs, nonvault index hash, and usage-ledger hash. V1 accepts brand-owned `customer_story`, `case_study`, and `reference` rows and approved Capterra `review_site` rows on the brand's listed product page. Review-derived stories are paraphrased, using the first name and role as displayed with a same-paragraph link to the public review. Exact snippets are allowed only when they are stored in that row's `approved_quotes` and live-captured. Ratings, stars, aggregate ratings, rankings, review metrics, vault selector evidence, and Fred evidence remain prohibited. Copy note: avoid the words "reviewer", "rated", and "stars" in public copy, which trigger strict proof. Release never writes `config/customer-proof-usage-ledger.json`; the publishers add the public use after a successful live publish (or it is added by hand before final handoff when publishing outside them), and each release refreshes the selector evidence so its ledger hash is current.

Selector chooses proof candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. When public copy uses selected customer proof, the proof item must be in the production BOM, and the WordPress or Grav publisher records the use after a successful live publish; when publishing outside them, a matching entry must be added to `config/customer-proof-usage-ledger.json` before final handoff. Release never writes the ledger. The release renders the `Selected Customer Proof Mining` view for the scorer from the BOM. This block proves the selected source was checked for stronger quote, metric, POV/story, and theme evidence before the final copy used only the selected proof role.

The release renders the `Selected Customer Proof Mining` view from the BOM for the scorer; this shape is for reference and optional private notes:

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

When proof mining finds usable quotes, metrics, or POV evidence that the article omits, a private note can record the section-specific reason under `Excluded proof`.

### Nonconnector proof inventory intake and health

The nonconnector proof inventory health report is `python data_sources/modules/customer_proof_index_health.py --index config/nonvault-customer-proof-index.json --ledger config/customer-proof-usage-ledger.json`; use it only for AroFlo, BigChange, and ClockShark inventory health, approval status, public-copy gaps, `recent_uses_90d`, recently used or overused proof, and ledger backfill needs.

New nonconnector proof candidates must enter `config/nonvault-customer-proof-index.json` through a nonconnector intake CSV and `data_sources/modules/customer_proof_index_intake.py` before a writer relies on them in nonvault selector slates. Simpro candidates are promoted through the vault claim workflow, not repo-local intake. Use:

```powershell
python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index config/nonvault-customer-proof-index.json
python data_sources/modules/customer_proof_index_intake.py merge [input.csv] --index config/nonvault-customer-proof-index.json --out config/nonvault-customer-proof-index.json
```

The intake row must state source type, source ref, approval status, public-copy boundary, evidence summary, restrictions, and verification date. Exact quotes, metrics, review-story identity claims, reviewer-name claims, ratings, rankings, and badges need explicit source-visible evidence before approval. Google review rows stay candidate and `public_copy_allowed: false` unless a usable public review URL is captured.

Customer Proof Slate shape (the selector's `--slate` output, kept as an optional private note):

```text
Customer Proof Slate
- Selector command: automatically run python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[slug].json" --context-receipt "research/context-receipt-[slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10
- Selector evidence: research/customer-proof-selector-evidence-[topic-slug].json | SHA-256: [generated digest]
- Selection outcome: [customer_proof_candidates_available or no_fit_customer_proof]
- Role: metric | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id] | Rejected stronger candidates: [proof_id: reason]
- Role: quote | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id or none] | Rejected stronger candidates: [proof_id: reason]
- Role: theme | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id or none] | Rejected stronger candidates: [proof_id: reason]
- Role: experience_story | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id or none] | Rejected stronger candidates: [proof_id: reason]
```

For `selection_outcome: no_fit_customer_proof`, every role must have `Top candidates: [none]`, `Selected: [none]`, no claim IDs, and a no-fit reason stating that public copy must omit customer proof, named customer claims, review stories, exact quotes, testimonials, and customer metrics. A no-fit outcome leaves no BOM proof items, and the release blocks a customer or review claim that links no BOM proof URL, so public copy cannot carry customer proof under it.

Optional Customer Proof Pack note shape:

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

Case-study proof paths and Review-site experience evidence may support non-numeric E-E-A-T PoV and paraphrased themes only. Exact quotes or testimonial wording must be an approved `quote` proof item in the BOM, quoted verbatim, and any named customer metric an approved `metric` proof item; the release blocks a quoted customer or review passage that does not match a BOM proof item. A Source Map or fact alone is insufficient for quotes, testimonials, or named metrics.

## Fred Voccola Authority Selection

Every `/research`, `/write`, `/rewrite`, `/analyze-existing`, and `/optimize` workflow for a new or changed Simpro blog must resolve `topic`, `title`, and `objective`, automatically run:

```powershell
python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug]-fred-evaluation-[YYYY-MM-DD].json" --context-receipt "research/context-receipt-[topic-slug]-fred-evaluation-[YYYY-MM-DD].json" --slate --limit 5 --output "research/fred-authority-selection-[topic-slug].md"
```

Evaluate the selector output before drafting or changing public Fred content; the evaluation can be kept as a private note in `research/validation-[topic-slug]-[YYYY-MM-DD].md`. Public use is optional and must materially support the article subject and target section. The selector defaults to `Selected: none`; selection requires an explicit editorial decision after the source is reviewed. If the selector, vault, manifest, or required inventory is unavailable or stale, set `Evaluation status: blocked`, document the blocker, and do not invent, infer, quote, paraphrase, cite, or embed Fred evidence.

The Simpro vault connector and claim registry are the sole eligibility source for Fred media eligibility and status. The selector resolves only the configured vault root, validates current connector revisions, resource hashes, and claim decisions, and fails closed when the manifest, claim registry, context receipt, or selected evidence is unavailable or stale. Only current usable authority records and public playlist assets are candidates. Internal assets, blocked rows, syndicated-placement-only rows, non-Simpro evidence, and any row outside its allowed-use status are excluded.

Fred's source-backed industry observations supplement E-E-A-T Expertise and Authority by default. They count as Experience only when the source explicitly supports Fred's first-hand personal or operating experience. Fred evidence is additive: it does not replace customer Experience proof, customer stories, the Customer Proof Pack, or authoritative independent evidence. No usage ledger or frequency penalty applies in v1; direct topical support is the primary selection criterion.

Optional private-note shape:

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

A `Selected: none` decision should give a substantive, article-specific topical rejection reason, not a generic statement such as "not relevant". A selected row is usable only when the current manifest-backed inventory and authority rows agree on title, URL, recommended brand, evidence status, public-use status, and allowed-use eligibility.

Public-use rules:

- Exact article quotations require source-visible article text, `Verification method: source_visible_article_text`, an evidence excerpt, and an article locator. Exact video or audio quotations require source-visible transcript or caption evidence, a timestamp, `Verification method: transcript_and_playback`, and `Playback verified: yes`. If those checks are incomplete, paraphrase or omit the observation.
- An exact quote or paraphrased industry observation must include a contextual public source link in the same paragraph. The source must directly support the surrounding statement; a sidecar URL alone does not satisfy this requirement.
- playlist-only rows may be used for discovery or an eligible embed, but never as independent earned-media authority. Do not present a curated playlist entry as third-party validation.
- Embedding is content-first and optional. Embed only a selected, public, embeddable YouTube source that materially supports the target section. Use the existing responsive 16:9 handoff: a privacy-enhanced `https://www.youtube-nocookie.com/embed/[video-id]` URL, visible public fallback link, descriptive iframe title, `loading="lazy"`, no autoplay, verified video metadata, and responsive dimensions.
- Frontmatter must include `VideoObject` when a Fred video is embedded and must omit `VideoObject` when no video is embedded. The internal selection block alone never earns AEO or E-E-A-T credit; only source-backed public content counts.

Fred content reaches public copy only as a BOM fact whose quote the builder verified on the public source, so an exact Fred quote must match that verified quote. The selection block is a private research note; the release does not read it. Existing articles are not bulk-backfilled; evaluate Fred when an existing Simpro article is next rewritten or optimized.

## AnswerSocrates PAA Workflow

For every new `/write` run, collect People Also Ask style questions from `https://answersocrates.com` with Playwright MCP.

Required fixed collector flow:

1. Open the fixed page URL.
2. Resolve the query input and submit action from the observed DOM.
3. Enter the mandatory `--query` value.
4. Submit and wait within the repository's fixed timeout bounds.
5. Emit exact JSON to stdout containing observed page URL, title, diagnostic body text, section headings/items, and structurally scoped blocker observations from the fixed selector set. General body text never establishes a blocker.
6. Immediately record the observed run at the layout's PAA path, `research/paa-evidence-[slug]-[YYYY-MM-DD].json`, with the recorder below. Do not hand-author the JSON or its hashes.

If AnswerSocrates shows a genuine blocked state such as login, CAPTCHA, quota, or unavailability, switch to the Google SERP PAA fallback below. Do not invent replacement questions.

For `/rewrite`, collect a current PAA capture under the production run id, AnswerSocrates first. There is no pre-picked brief precedence: existing FAQ questions that the capture does not contain are removed or turned into body sections. Apart from the recorded Google SERP fallback, SERP, Reddit, and YouTube stay supplemental and never satisfy PAA provenance.

### Collected AnswerSocrates Artifact Template

The `record` command runs the fixed repository-approved Playwright collector, `answersocrates_playwright_collector`, itself, persists exact bounded Playwright CLI stdout before interpretation, and parses only observed page headings/items plus structurally scoped blocker observations through a closed blocker mapping. General body text never establishes a blocker.

```powershell
python data_sources/modules/paa_provenance_guard.py record --query "[the exact SERP evidence query]" --collection-date "[article date, YYYY-MM-DD]" --run-id "[production run_id printed by the layout command]" --raw-capture-output "research/answersocrates-playwright-raw-[slug]-[YYYY-MM-DD].json" --workspace-root "." --output "research/paa-evidence-[slug]-[YYYY-MM-DD].json"
```

The recorder emits `simpro-answersocrates-artifact/v1` with a nested `simpro-answersocrates-run-receipt/v1`, fixed `answersocrates_playwright_collector` version `1.0.0`, payload SHA-256, and receipt SHA-256. Handwritten labels, caller-authored captures, Markdown templates, and self-described browser blockers are invalid provenance.

When the Playwright collector cannot complete a session, pass an already-collected Chrome-connector capture with `--raw-capture-input "research/answersocrates-chrome-raw-[topic-slug]-[YYYY-MM-DD].json"` in place of `--raw-capture-output`. The two flags are mutually exclusive and exactly one is required. The recorder then skips collection and validates the supplied capture's schema, execution attestation, query, collection date, and run ID exactly as it validates one it collected itself. A `simpro-answersocrates-chrome-connector-capture/v1` capture is operator-transcribed browser observation, not raw tool output, so record it as that lane and use it only when a live browser session is the only way to reach the page.

### Google SERP PAA Fallback

Use the fallback only when AnswerSocrates shows a genuine blocked state: a login wall, a CAPTCHA, a search quota or daily-limit message, or an unavailable page.

1. In the user's main Chrome window, through the running client's live-browser tools, note the UTC time and save the AnswerSocrates blocker text exactly as the live tab shows it as `research/answersocrates-blocker-[slug]-[YYYY-MM-DD].txt`.
2. Open `https://www.google.com/search?q=[the exact SERP evidence query]&hl=en&gl=[google-country]&pws=0`, read the "People also ask" questions from the page's `[data-q]` attributes in page order, and save them as a JSON list, `research/google-paa-questions-[slug]-[YYYY-MM-DD].json` (an empty list when Google shows no PAA box). Note the UTC time.
3. Confirm both saved files against the live tabs, then record:

```powershell
python -m data_sources.modules.production.google_paa --query "[the exact SERP evidence query]" --run-id "[production run_id printed by the layout command]" --google-country [au|gb|us] --page-url "[the Google results URL]" --collected-at "[UTC time, YYYY-MM-DDTHH:MM:SSZ]" --questions-file "research/google-paa-questions-[slug]-[YYYY-MM-DD].json" --answersocrates-state [login|captcha|quota|unavailability] --answersocrates-text-file "research/answersocrates-blocker-[slug]-[YYYY-MM-DD].txt" --answersocrates-url "[the AnswerSocrates tab URL]" --answersocrates-observed-at "[UTC time, YYYY-MM-DDTHH:MM:SSZ]" --client [claude_code|codex] --output "research/paa-evidence-[slug]-[YYYY-MM-DD].json"
```

The recorder writes an attested `simpro-google-serp-paa-capture/v1` capture (source kind `google_serp_paa`) at the layout's PAA path. The BOM build and the release scorer accept it only with a valid blocker observed on the article date before the Google capture, and with the run's query, date, and run id. Its questions are eligible PAA questions under the same FAQ rules. The release record carries a `paa_google_serp_fallback` warning that names the blocker. Provenance caveat: the attestation proves the workspace wrote the record and that it is unchanged, not that Google or AnswerSocrates served it; both observations are self-declared. The BOM build refuses a bare blocked AnswerSocrates artifact.

## Question Relevance Selection

Select only the complete eligible questions that materially support the main concept and planned FAQ. Do not target a fixed count. Group selected questions by search intent such as How-to, Understanding, Comparative, Future-Trends, or Commercial. Summarize what they reveal, write the suggested blog focus, and assign each selected question to an article section and answer format.

## General Source Support Classes

Use only these exact general source-map classes: `primary_authority`, `independent_research`, `non_competing_expert`, `owned_product`, `customer_proof`, `review_platform`, and `competitor`. Every proof-sensitive claim needs a BOM fact whose quote the builder verified on the live page and found to support the claim. The release renders the scorers' Source Map from those facts and classifies each source itself; a writer-supplied source-class or citation-mode label is not evidence. Owned product sources support product facts: an approved `owned_product` row typed `product_claim` or `feature_claim` for a Simpro sentence that says what the product is, how it works, or what it lets a user do is `sidecar_only`, while outcome, numeric, pricing, status, comparative, and guarantee wording stays `inline_required`; connector claims govern other proof-sensitive Simpro language; customer and review proof retain their specialist gates.

The policy engine assigns exactly one of four citation modes:

- `inline_required`: legal, regulatory, licensing, compliance, safety, fees, deadlines, pricing, status, material numeric, causal, comparative, benchmark, quote, customer, review, Fred, and fact-driven FAQ claims require a natural public link in the same paragraph or table row. FAQ links must appear in the first visible answer paragraph.
- `section_source_allowed`: lower-risk body definitions, background, and process explanations may use one mapped source in the same H2 section.
- `sidecar_only`: approved low-risk product or brand language and clearly framed low-risk editorial recommendations may stay unlinked in public copy, with their mapping noted in the research brief.
- `proof_not_required`: navigation, explicit opinion, or advice with no externally verifiable factual claim requires no proof. Only the policy engine may generate this mode.

Unknown or ambiguous high-risk claims fail closed to `inline_required`. A Source Map or FAQ Proof Map documents the mapping but cannot replace a required reader-facing link. Use natural descriptive anchors rather than pasted URLs, generic calls to action, or repetitive exact-match anchors. Prefer one authority link for a contiguous claim cluster, but allow multiple distinct authority links in one paragraph when separate evidence-triggered claims require them; never split or remove required proof solely to satisfy a per-paragraph link count.

Two distinct authoritative non-owned external sources satisfy the standard-blog baseline. Multiple links to one source count as one source, and a third source added only to satisfy a quota is redundant. Source support, regulations, public proof, specialist same-paragraph rules, and other claim-fit evidence exceptions are uncapped. Standard blogs use 3 to 5 internal links and must not exceed 7 below 3,000 visible words; the SEO scorer waives that maximum at 3,000 or more visible words. URL fragments and `mailto:` or `tel:` links are navigation utilities and do not count toward internal or external totals.

Reviewers must preserve every `inline_required` link and every other specialist-required public link. They must report any proposed deletion, anchor rewrite, or relocation that would break the mapping, and flag repeated destinations, duplicate support, or a quota-only third external source as redundancy. Reviewers return advisory findings only. `/publish-readiness` remains the sole release verdict; this workflow has no human approval stage.

The builder admits a fact only when it can verify the quote on the live page itself. The single exception is the user's 2026-10-14 decision: a Chrome page capture (`simpro-chrome-page-capture/v1`, written by `python -m data_sources.modules.production.page_capture record`) admits a fact only when the live fetch is blocked (HTTP 403, 429, or 503, a timeout, or a connection error). It never admits a fact for a 404 or 410, for a reachable page, or for a 401, 451, other 4xx, or 500/502 answer. It applies only to the exact fact URL, with the page text and receipt saved under `research/source-captures/` and bound by hash, and a capture older than 90 days refuses the build. The release re-checks the live page every time, warns while the page stays blocked and cites the capture's `captured_at`, and blocks an edited capture. Provenance caveat: the receipt proves the text is unchanged since capture, not where it came from. Its `surface` and `client` values are self-declared, and no automated check can tell a faithful Chrome capture from typed text, so treat it with the same reduced provenance as `chrome_connector` SERP evidence. Any other locally authored capture or evidence file never admits a fact.

### Known Vocabulary Drift

Three source-class vocabularies are not yet reconciled, so two rows are currently unwritable. Do not work around this by relabelling a source to make a guard pass.

- `neutral` is accepted by the classification registry but is missing from the list above. Treat the hash-bound registry export as authoritative.
- `Claim type: regulation` and `Claim type: standard` require a `Source class` of `official`, `regulator`, `standards_body`, or `government`, but the registry classifies every government and regulator URL in this repo as `primary_authority`. No artifact can satisfy that rule today, which is why no row uses either claim type. Map a regulatory citation under the applicable general claim type and keep the official URL as the inline source.
- The registry can emit `independent_research`, while the source-map quality gate accepts `original_research`. The two names are not interchangeable.

Reconciling these vocabularies changes the release contract and needs its own review. Do not widen a guard's class list to make a single row pass.

## Reader-Facing Public Copy Boundary

Public blog body copy must read as an article for the ICP, not as a workflow explanation for the operator. Keep brief instructions, editorial rationale, command results, claim-selection decisions, source-fit reasoning, product-mention omissions, schema notes, and publish-readiness status out of the body. Put that material in YAML frontmatter when it is public metadata, and in the research brief, the validation sidecar notes, or the BOM spec when it is workflow evidence.

Never write public body sentences such as "this article uses," "the brief asks," "that is the right editorial lane," "it does not name a specific feature," or similar commentary that explains why the draft was assembled a certain way. Translate the decision into reader-facing guidance, or omit it. The AI copy linter's `editorial_process_leakage` rule is a release blocker for this class of mistake.

## Drafting Rules

- Open with a direct answer in the first 1-2 sentences. The answer comes before the hook.
- Use the Capsule Method below the H1 and at least 60% of major H2s: 50-60 words, complete answer, no preamble.
- Include a Key Takeaways block after the introduction with 3-5 standalone conclusions.
- Place a usable artifact within the first 300 words of body copy: a filled data table, a download link (PDF, Excel, Doc, or template), a checklist deliverable, or a calculator/tool reference. Key Takeaways bullets, plain lists, and image placeholders do not count. This is an advisory drafting rule that the release does not enforce; if no artifact fits the topic, say why in the research brief.
- When image or video work remains, use a visible standalone marker so developers cannot miss it. `/write`, `/rewrite`, and `/optimize` must normalize hidden HTML comments, blockquotes, inline labels, and shorthand media notes into `[IMAGE PLACEHOLDER | source: ... | alt: "..." | render target: ... | resize and compress before upload]` or `[VIDEO PLACEHOLDER | source: ... | title: "..." | placement: ... | embed target: ... | VideoObject: add only after embed]`. Treat unclear media placeholder warnings as LLM repair instructions, not publish blockers.
- If the target query implies a number, range, or template, supply a concrete version in the article with disclaimers as needed. Placeholder-only table cells such as `Enter lender-approved value`, `TBD`, or `varies` withhold the answer; fill tables with concrete sourced values or delete them. This is an advisory drafting rule that the release does not enforce; record any exemption reason in the research brief.
- Use one clear idea per H2/H3 section.
- Integrate claim-fit credible external sources naturally inside sentences; evidence needs determine the count.
- Place each link where it directly supports the sentence and reader task. Do not impose a per-paragraph quota.
- Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough.
- Context files are not a source of truth for Simpro voice, positioning, approved claims, proof candidates, or approved metrics. Use repo context only for SEO/AEO strategy, brand-neutral editorial mechanics, generic CRO, link maps, and source governance. Do not write phrases like "repo context," "Source Map," "PAA artifact," "change summary," or internal proof-path notes in the public article body.
- Use claim- and source-backed metrics only with public-facing source links, such as case-study URLs, review-site URLs, or public research sources.
- 403 replacement rule: if a source URL returns 401, 403, or `manual_review`, do not remove the public citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. DOL, Capterra, G2, Trustpilot, Google Play, and other review or authority-site 403s are URL-validity blockers, not permission to hide the source in the validation sidecar. A replacement source must itself be a BOM fact verified on its live page.
- Place numeric claims only from BOM facts or approved proof, with the BOM URL linked in the same paragraph or table row.
- Include a visible FAQ only when `FAQ policy: required`; otherwise record `not_applicable` with a non-empty rationale and omit FAQ schema.
- When visible FAQs exist, write each answer as a 40-60 word direct answer before supporting context.
- FAQ answer quality is mandatory when visible FAQs exist: lead with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Do not open with `There is no`, `It depends`, `Pricing depends`, `Costs vary`, `We do not know`, `It is unclear`, `No source ranks`, or an equivalent deflection. Put limitations after the direct answer. Replace or remove a question when no defensible answer exists.
- FAQ proof is risk-tiered. Fact-driven or high-risk answers use `inline_required` and place a natural link to a BOM fact or proof URL in the first visible paragraph. A `neutral`, `non_competing_expert`, or `owned_product` source may support an answer when it directly supports it; competitor-owned sources are prohibited; an answer that states compliance, legal, regulatory, statistical, or research-backed claims also needs a resolved non-owned public source. Lower-risk answers follow their assigned mode and do not receive a visible link solely to satisfy a quota. Context file paths do not satisfy an `inline_required` FAQ claim, and owned product links do not count toward the standard-blog non-owned external authority baseline.
- **FAQ Source Policy**: The release renders the `FAQ Proof Map` and `FAQ Source Policy` for the scorer from the BOM facts; writers do not author them.
  - Allowed source classes: neutral, non_competing_expert, owned_product.
  - Competitor-owned FAQ sources: prohibited.
  - Use regulators, standards bodies, universities, trade associations, independent research/editorial, non-competing expert sources, or owned product/resources pages when they directly support the answer.
  - Simpro-owned links can satisfy FAQ support when they directly support the answer and are classified as `owned_product`; they do not count toward the standard-blog non-owned external authority baseline.
  - If no compliant source supports a vendor-specific question, remove or reframe the FAQ and retain vendor evidence in a comparison or vendor-specific body section.

- PAA provenance is required for each FAQ question: every visible FAQ question must be a BOM PAA question, and the release renders the `PAA/FAQ Provenance` view from the BOM.
- Add schema notes for standard blog posts: always require `BlogPosting`, `BreadcrumbList`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`. `FAQPage` and `Question and Answer inside FAQPage` are required only when visible FAQs exist. `Person as author` is required only when a named author exists. Require `VideoObject` if and only if a verified video embed exists. For public Markdown blog artifacts, place `schema_notes` in the top YAML frontmatter block between the opening and closing --- delimiters. If a named author is present, include `author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and leave `Person as author` out of the BOM spec's `schema_notes`.
- Evaluate Fred authority evidence for every new or changed Simpro blog, but add Fred content only when a selected source directly supports the section. Keep `Fred Voccola Authority Selection` in the validation sidecar, not public copy.

## AEO/GEO Map

Every `/write` plan and every moderate, major, or complete `/rewrite` plan, across the research brief and the BOM spec, should cover these; rows marked as private notes are optional:

| Field | Requirement |
|---|---|
| Main answer target | The core question the article answers |
| Capsule targets | H1 plus 60%+ major H2s |
| Selected PAA questions | Complete eligible questions selected by intent, without a fixed count |
| PAA/FAQ provenance | Questions copied from the PAA capture (AnswerSocrates, or the Google SERP fallback) recorded under the production run id on the article date |
| BOM facts | Claim, URL, exact quote, priority, and target section |
| Metrics | Numbers only from BOM facts or approved proof; search log and rejected candidates as private notes |
| E-E-A-T Proof Map | Experience proof, Expertise proof, Authority/Trust proof, case-study candidates, review-site VoC candidates, omitted unsupported claims |
| Customer Proof Pack | Pack status, Quote Matrix candidates, Case-study proof paths, Review-site experience evidence, Approved metrics, Use in copy, Claims excluded, approval status |
| E-E-A-T Strength Decision | Optional private note for commercial-investigation blogs when no positive signal is selected: Applicability, Intent, Positive signals, Decision, Reason, Public copy boundary, Status, and optional approved SME review note |
| Fred Voccola Authority Selection | Optional private note for connector-bound work: selector evaluation, ranked FVMI candidates, explicit selected-or-none decision, topical fit, intended use, source verification, embed decision, and VideoObject decision |
| Named Feature Status and Commercial Treatment | Optional private note: one current claim-status row per detected Lightning, RAIN, role-agent, scheduler, or roadmap specialist name |
| Review Story Selection | Optional private note when public copy paraphrases a review-derived E-E-A-T story: identity-backed selected story, public review URL, same paragraph link requirement, and exact quote boundary |
| Review Site Theme Selection | Optional private note when public copy paraphrases a Capterra review-site theme without using an E-E-A-T story: Capterra tab row, public Capterra review-site URL, approved workflow theme, same paragraph link requirement, and exact quote/rating boundary |
| Early usable artifact | Filled data table, download link, checklist deliverable, or calculator reference planned within the first 300 words of body copy, or a documented not-applicable reason |
| AI citation target | Snippet, PAA, FAQ, comparison table, definition, or list |

## Publish Gates

A blog is publish-ready only when its latest release record passed for the exact article bytes. The release blocks on any of these:

- General content quality score below 85/100.
- SEO quality below the 90/100 release floor, or any critical SEO issue. The 95/100 optimization target is advisory when honest, source-safe improvements exist.
- AEO/GEO score below 90/100.
- Truth: a link that does not resolve (a fact page that is merely unreachable warns and keeps its earlier verification); a claim that cites a source outside the BOM; a fact whose page no longer carries its verified quote, or is gone; a material number that is not in a BOM fact quote or proof item linked in the same paragraph; a customer or review claim with no BOM proof URL linked; a quoted customer or review passage that does not match a BOM proof item verbatim; a visible FAQ question that is not a BOM PAA question; or an `editorial_process_leakage` finding from the AI copy linter.
- Coverage: a missing `must` section, `must` fact citation, `must` proof item, `must` PAA question, or other `must` link; the commercial pillar link missing or using a different anchor than planned; or the primary keyword missing from the title, H1, or first 100 words.
- A refused BOM rebuild: a fact quote lost from its page, a gone page, or proof no longer approved or selected.

The release reports these as warnings: other AI copy linter findings, links that are not BOM links, facts, or proof URLs, missing `should` items, unreachable fact pages, and scorer priority fixes. `/optimize` works from them.

Public artifacts must not contain an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, `Fred Voccola Authority Selection`, `Hindsight Strategy Selection`, `Named Feature Status and Commercial Treatment`, `Vault Brand Language Alignment`, `Early Artifact Plan`, `Concrete Answer Check`, bracketed editorial labels, publication confirmation notes, unresolved availability notes, standalone TODO/TBD/TK markers, or a structured data plan. Fenced examples, quoted source text, reader instructions, and canonical standalone media placeholders remain allowed. Hidden, blockquoted, inline, or shorthand media placeholders should be normalized by `/write`, `/rewrite`, or `/optimize` before handoff.

The release renders the scorers' proof view (PAA provenance, customer proof slate and pack, Source Map, and FAQ Proof Map) only from the BOM. Writers never author it, and proof maps never appear in public copy.

## AEO/GEO Recovery Loop

A blocked release or an AEO/GEO score below 90/100 is a repair trigger, not a reporting endpoint. Unless the user explicitly requested a read-only audit, the LLM must continue in the same workflow:

1. Review every blocking finding in the latest release record, every failed AEO/GEO check in `scores.gates.aeo_geo`, and the scorer's `priority_fixes`.
2. Classify each failure as a public-copy gap, a BOM gap (a needed fact, proof item, PAA question, section, or link is missing or refused), or a scorer or parser false negative.
3. If the article visibly satisfies the written requirement but scoring misses it, add a regression test and fix the scorer or parser false negative. Do not distort accurate, brief-approved copy to satisfy brittle matching.
4. Apply the blocking fixes and the top 3-5 priority fixes that address root causes. Route BOM gaps to `/research`, which fixes the spec and rebuilds the BOM. Do not invent PAA questions, claims, proof, metrics, quotes, or customer experience to gain points.
5. Rerun `/scrub` after any article-byte change, then release again through `/publish-readiness`.
6. Repeat once if needed. If the release is still blocked after 2 iterations, leave the article in place and report the latest record's blocking findings, scores, attempted fixes, and any external evidence or authority blocker.

`/optimize` runs this loop for public-copy gaps and below-threshold scores; BOM gaps go to `/research`. Final handoff still requires content quality of at least 85/100, SEO quality release floor of at least 90/100 with zero critical SEO issues, AEO/GEO of at least 90/100, and zero blocking findings. When SEO is 90-94 after one target-safe pass or no honest SEO fix is recommended, record `release-pass, below-target` and keep the artifact publishable.
