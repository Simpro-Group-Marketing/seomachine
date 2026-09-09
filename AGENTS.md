# Agent Instructions

This repo is proof-sensitive. Never synthesize data, customer claims, review claims, metrics, rankings, PAA questions, or quotes.

## Repository Development Rules

These rules apply to code, tests, configuration, scripts, commands, and developer documentation. They supplement the proof-sensitive content and workflow rules elsewhere in this file.

### Before Editing

- Inspect the relevant implementation, tests, configuration, and current working-tree diff before editing.
- State material assumptions. Do not invent repository behavior, test results, data, or requirements.
- Resolve materially different interpretations before editing. For low-risk, reversible ambiguity, choose the simplest interpretation and disclose it.
- Define concise, verifiable success criteria and a verification plan for non-trivial work.

### Implementation Scope

- Make the smallest complete change that satisfies the verified requirement.
- Do not add speculative features, abstractions, configuration, or handling for impossible scenarios.
- Match surrounding repository style and preserve unrelated user changes.
- Do not refactor, reformat, rename, or clean up unrelated code.
- Remove imports, variables, functions, or files only when the current change makes them unused.
- Every changed line must trace directly to the requested outcome or its verification.

### Testing and Verification

- For a bug fix, reproduce the failure with a focused test when practical, then make that test pass.
- For new behavior, test the expected path and relevant invalid inputs.
- Run the narrowest relevant checks first, followed by broader applicable checks.
- Report the commands run, their results, and any checks not run. Never claim validation that was not performed.
- Continue until the success criteria pass or a concrete blocker is proven.

## Simpro Vault Source Rule

Use the Simpro vault connector as the active context source only when the final artifact is Simpro-owned or contains a Simpro signal. A Simpro signal is the name `Simpro` or an official `simprogroup.com` URL, including schemeless URLs and subdomains. AroFlo, BigChange, and ClockShark owned artifacts with no Simpro signal are nonconnector workflows. Missing, unknown, or malformed brand metadata fails closed into the connector workflow. The only configured connector content location is the vault root; prompts, guards, selectors, and workflow docs must not prescribe vault hubs, filenames, or internal directories.

For connector-bound workflows, run vault health first, describe available roles/topics/entities, search in the task's natural language, read and expand results by `resource_id`, query approved claims only when public proof-sensitive language is needed, then build and validate a context pack. Evidence in validation sidecars must be bound to connector output: `context_pack_hash`, `receipt_hash`, `resource_id`, `claim_id`, use mode, public URL when required, and relevant manifest/revision values. Use the one enabled `simpro-context@simpro` installation whose `projectPath` matches this repository, regardless of its reported version. Never select a connector installation whose `projectPath` belongs to another repository, worktree, or branch checkout. Determine compatibility from `vault_status` and the required operation contracts, not the version label. If the vault MCP operations are not surfaced in the active tool catalog, invoke the same installed connector through `data_sources.modules.simpro_vault_client.SimproVaultClient`; missing MCP exposure is not evidence that the vault is unavailable.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault connector exposes them as source evidence.

The repo-local context files are downstream operational state only and must never serve as the active or fallback source for a Simpro workflow. If both the surfaced MCP operations and the current-project `SimproVaultClient` path fail, stop the connector-bound workflow, document the exact vault blocker in the validation sidecar, and do not draft unsupported public claims.

Every workflow requires a generated Context Binding decision. Connector-bound workflows require vault context evidence. AroFlo, BigChange, and ClockShark workflows with no Simpro signal require an explicit nonconnector binding and must omit context request/pack/receipt, Fred evidence, and vault-dependent customer-proof selector evidence. `Vault Brand Language Alignment` applies when connector-bound product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` applies to competitor-aware posts; `Named Feature/Add-On Link Check` applies when named Simpro features/add-ons appear. Connector evidence sections must cite resource IDs and claim IDs rather than fixed vault routes. Missing required evidence blocks `/publish-readiness`, `/optimize`, and dev-ready handoff.

## Author-Led Blog Voice

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

## Reader-Facing Public Copy Boundary

Public blog body copy must read as an article for the ICP, not as a workflow explanation for the operator. Keep brief instructions, editorial rationale, command results, claim-selection decisions, source-fit reasoning, product-mention omissions, schema notes, and publish-readiness status out of the body. Put that material in YAML frontmatter when it is public metadata, and in the validation sidecar, editorial plan, optimizer output, release BOM, or command receipt when it is workflow evidence.

When image or video work remains, keep the marker reader-visible and standalone. `/write`, `/rewrite`, and `/optimize` must normalize hidden HTML comments, blockquotes, inline labels, and shorthand media notes into these formats: `[IMAGE PLACEHOLDER | source: ... | alt: "..." | render target: ... | resize and compress before upload]` or `[VIDEO PLACEHOLDER | source: ... | title: "..." | placement: ... | embed target: ... | VideoObject: add only after embed]`. Unclear media placeholder warnings are repair instructions for the LLM, not publish blockers.

Never write public body sentences such as "this article uses," "the brief asks," "that is the right editorial lane," "it does not name a specific feature," or similar commentary that explains why the draft was assembled a certain way. Translate the decision into reader-facing guidance, or omit it. The AI copy linter's `editorial_process_leakage` rule is a release blocker for this class of mistake.

## Reviewed Humanizer Governance

The Editor reviews `/write`, `/rewrite`, and `/optimize` snapshots against the pinned Humanizer snapshot recorded in `vendor/blader-humanizer/UPSTREAM.json`, the local decisions in `config/humanizer-policy.json`, and current vault voice context. Humanizer is style advice only. It never edits public copy directly, does not approve claims, and has no runtime network access. Only policy entries explicitly marked for deterministic enforcement may enter the existing AI-copy linter. `/publish-readiness` remains the sole release owner.

Validate the vendored snapshot offline with `python tools/humanizer_upstream.py verify`. Use `check-upstream`, `stage`, and `adopt` for reviewed upgrades. The weekly workflow may open a draft vendor-only PR, but a maintainer must review pattern changes and update the local policy before CI can pass. Never modify `config/humanizer-policy.json` automatically from upstream content.

## Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: connector-bound competitor-aware posts must document selected competitors, rejected competitors, connector-discovered competitive-context resources, approved claim IDs where public proof is used, and why the shortlist fits the article objective. Nonconnector AroFlo, BigChange, and ClockShark posts document the task-approved shortlist and public official-source basis without vault resource or claim IDs.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified through the claim registry. Keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked through connector-discovered product and feature resources before link decisions. Document the selected `resource_id` values, link decision, and reason in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from connector-discovered vault guidance first. Use semantic search/read/expand for messaging, positioning, feature, solution, and vertical context. When a named feature/add-on appears, include feature-specific `resource_id` evidence; when solution/industry language is used, include solution or vertical `resource_id` evidence. Document connector evidence, language applied, fallback context use, source-verification boundary, and `Status: aligned` in `Vault Brand Language Alignment`. The `vault_brand_language_guard.py` publish gate runs inside `/publish-readiness`; keep this block in the validation sidecar, not public copy. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.


## Customer Proof Selection

Before selecting customer proof for a connector-bound blog, article, rewrite, or optimization pass, the command workflow must resolve `topic`, `title`, and `objective`, automatically run:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10
```

For nonconnector AroFlo, BigChange, and ClockShark workflows, do not run the vault-dependent customer-proof selector. When a separate approved non-vault proof-eligibility contract applies, run `data_sources/modules/nonvault_customer_proof_selector.py` and require hash-bound `simpro-nonvault-customer-proof-selector-evidence/v1` for the matching brand, topic, article slug, proof index, and usage ledger. V1 permits approved brand-owned customer stories, case studies, and references only. It does not permit review-platform stories, exact quotes, customer metrics, ratings, star claims, or named-person attribution. Without this evidence, do not publish customer stories, testimonials, review-derived anecdotes, ratings, or quotes.

Use `context/customer-proof-index.json` for curated proof routes and `context/customer-proof-usage-ledger.json` for reuse. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live scan finds public-copy usage missing from the ledger, update `context/customer-proof-usage-ledger.json` before selecting proof, rerun the proof health/selector checks, and document the backfill in the validation sidecar. Write the generated selector-first `Customer Proof Slate` to the validation sidecar before drafting customer proof; "consult" means reviewing generated selector output, not skipping execution. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the validation sidecar and do not invent proof. Edit selected/rejected rows only when editorial judgment requires it. experience_story consideration is required and E-E-A-T story usage is optional; if no story fits, use `Selected: [none]` with section-specific rejection reasons. Choose the most relevant approved proof, not the easiest mapped case study. If a repeated proof source is still the best fit, document a `Customer Proof Selection Decision` and a source-specific `Reuse reason` proving no stronger underused approved proof fits the same role.

Treat any `recent_uses_90d` value above 0 as a proof-diversity warning, not only sources marked `overused`. Prefer an approved zero-recent-use source when one fits the same role. If a recently used or overused proof source is still selected, the validation sidecar must explain why no stronger underused approved proof fits.

When selected customer proof appears in public copy, add `Selected Customer Proof Mining` to the validation sidecar and add a matching entry to `context/customer-proof-usage-ledger.json` before final handoff. Selector chooses candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. Use `context/aeo-geo-blog-strategy.md` as the canonical policy.

Use `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` to inspect proof inventory gaps, recent use, and overuse before adding new proof or running selector slates.

Add new proof candidates through `context/customer-proof-intake-template.csv` and validate them with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.

For review-derived public E-E-A-T stories, the command workflow must automatically run:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles experience_story --require-eeat-story --limit 10
```

Review-derived E-E-A-T stories require `Review Story Selection` in the sidecar and same-paragraph public review links. Use `context/aeo-geo-blog-strategy.md` for identity and proof boundaries.

Use a proof-backed customer/review POV only when it improves the article objective. If no actual person or business POV fits, omit the story. Fictional named personas are prohibited; unnamed workflow scenarios are explanatory only and do not count as E-E-A-T.

For Capterra theme use, add `Review Site Theme Selection` with `Capterra tab row`, `https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`, and `Status: approved for paraphrased review-theme use`. Same-paragraph link required; no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved.

## Fred Voccola Authority Selection

For every new or changed Simpro blog and every connector-bound rewrite, analysis, optimization, or publish-readiness pass, resolve `topic`, `title`, and `objective`, automatically run:

```powershell
python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5
```

Write the complete `Fred Voccola Authority Selection` block to the validation sidecar. Evaluation is mandatory; public use is optional. The vault connector and claim registry are the sole eligibility source, and the selector must fail closed unless current connector revisions, resource hashes, and claim decisions validate. Do not invent evidence when the vault, manifest, claim registry, inventory, or selector is blocked.

Fred evidence supports Expertise and Authority by default. It counts as Experience only when the source explicitly supports first-hand personal or operating experience, and it remains additive to customer Experience proof, customer stories, and independent evidence. Exact article quotes require `source_visible_article_text`; exact video/audio quotes require `transcript_and_playback`, a timestamp, and playback verification; paraphrases require `paraphrase_evidence`. Exact quotes and paraphrased observations need a contextual public link in the same paragraph. A playlist-only row is for discovery or embedding, never independent earned-media authority.

Embed only a selected, public, embeddable YouTube source that materially supports the section. Use a responsive 16:9 `youtube-nocookie.com` handoff with a visible fallback link, descriptive title, lazy loading, no autoplay, and verified metadata. Require `VideoObject` if and only if a video is embedded. No usage ledger or frequency penalty applies in v1; topical support controls selection. Existing content is not bulk-backfilled, but this evaluation is required when it is next rewritten, optimized, or passed through publish readiness.

## Proof Gates

Proof-only infrastructure belongs in `research/validation-[topic-slug]-[YYYY-MM-DD].md`, not in public blog copy. Run proof-aware gates with `--proof-sidecar`.

Preferred publish readiness command:

```powershell
/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json
```

The customer proof diversity gate is mandatory before scoring or publish readiness and runs inside `/publish-readiness`.

The guard requires Quote Matrix, Reference, Customer Story, or review-site search evidence when case studies are used. Exact quotes, named reviewers, ratings, badges, rankings, and testimonials require approved proof rows with source-visible evidence.

The review story identity gate is mandatory before scoring or publish readiness whenever review-derived story copy appears and runs inside `/publish-readiness`.

The early artifact and answer withholding gates run inside `/publish-readiness`: a usable artifact within the first 300 words of body copy, concrete answers for number/range/template queries, and no placeholder table scaffolds. Policy lives in `context/aeo-geo-blog-strategy.md`.

Mandatory scrub, scorecard, and optimization pass: every new or changed blog run must include `/scrub`, an initial `/publish-readiness` scorecard or exact non-scoring blocker, `/optimize`, a post-optimization `/scrub` when article bytes change, and a final `/publish-readiness` handoff. `/optimize` is required even when no edits are needed; record a no-op optimizer output with the inspected scorecard, AEO/GEO checks, priority fixes, and the reason no source-safe edit was made. Score absence is a workflow blocker unless a pre-scoring gate blocked readiness; in that case, report the blocker exactly and do not present the article as ready.

The first atomic blog-release wrapper run intentionally omits optimizer evidence and must advance the workflow by returning exit `0` with phase `optimization_started` and writing `optimization-recovery.json`; missing optimizer evidence alone must never become a dead-end failure. When initial readiness passes, also persist its scorecard and stage receipt and open `optimization-state.json`. When a pre-scoring gate blocks readiness, preserve the exact blocker without minting a fake passed receipt, begin the `/optimize` recovery handoff, repair the blocker, and rerun the wrapper to obtain the required initial scorecard. Only a later wrapper run supplied with both `--optimizer-output` and `--prior-preflight-readiness` may reach phase `final_readiness`. A passing preflight scorecard or `optimization_started` result is not final approval.

When content quality is below 85/100 or AEO/GEO is below 90/100, continue automatically through the AEO/GEO Recovery Loop in `context/aeo-geo-blog-strategy.md`. Review `aeo_geo.checks`, distinguish copy or proof gaps from a scorer or parser false negative, apply the top 3-5 fixes, and rerun `/scrub` plus `/publish-readiness`. Do not stop at reporting a low score. After 2 unsuccessful iterations, leave the article in place, write a machine-readable blocker under `research/`, and return nonzero with the exact failed checks and attempted fixes.

## Risk-Tiered Citation and Link Policy

Every proof-sensitive claim must be machine-mapped to evidence. The policy engine assigns exactly one citation mode and fails unknown or ambiguous high-risk claims closed to `inline_required`:

- `inline_required`: legal, regulatory, licensing, compliance, safety, fees, deadlines, pricing, status, material numeric, causal, comparative, benchmark, quote, customer, review, Fred, and fact-driven FAQ claims need a natural public link in the same paragraph or table row. In an FAQ, place the link in the first visible answer paragraph.
- `section_source_allowed`: lower-risk body definitions, background, and process explanations may use one mapped source in the same H2 section.
- `sidecar_only`: approved low-risk product or brand language and clearly framed low-risk editorial recommendations may remain mapped in the validation sidecar without a visible public link.
- `proof_not_required`: navigation, explicit opinion, or advice with no externally verifiable factual claim requires no proof. Only the policy engine may generate this mode.

Use natural, descriptive anchor text. Prefer one authority link for a contiguous claim cluster, but allow multiple distinct authority links in one paragraph when separate evidence-triggered claims require them; never split or remove required proof for a per-paragraph link count. Two distinct authoritative non-owned external sources satisfy the standard-blog baseline; never add a third source only to meet a quota. Claim-fit evidence exceptions are uncapped. Standard blogs use 3 to 5 internal links and must not exceed 7. Valid brief-bound exact-count overrides may narrow the brief-selected supporting-link target, but single-trade Simpro posts still require the matching industry page unless the bound brief explicitly prohibits it. URL fragments and `mailto:` or `tel:` links do not count toward internal or external totals.

Machine reviewers must preserve every required public link, report any proposed deletion or relocation that would break its claim mapping, and flag repeated destinations, duplicate support, or a quota-only third external source as redundancy. They remain advisory; `/publish-readiness` is the sole release verdict and no human approval step is part of this workflow.

## FAQ Answer Quality

Every FAQ answer must use a 40-60 word first visible paragraph and lead with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Generic openers such as `There is no`, `It depends`, `Pricing depends`, `Costs vary`, `We do not know`, `It is unclear`, and `No source ranks` block publish readiness. Put limitations after the direct answer.

Fact-driven or high-risk FAQ claims use `inline_required` and must contain a natural authoritative non-owned public evidence link in the first visible answer paragraph. Lower-risk FAQ answers follow their machine-assigned citation mode and do not gain a visible link merely to satisfy a quota. A Source Map or FAQ Proof Map documents the evidence but cannot replace a reader-facing link when `inline_required` applies. If no defensible evidence-backed answer exists, replace or remove the question. The `faq_answer_quality_guard.py` and `faq_proof_guard.py` gates both run inside `/publish-readiness`.
## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert.
- Competitor-owned FAQ sources: prohibited.
- Every visible non-owned FAQ URL requires its own exact `FAQ Proof Map` row in the validation sidecar: `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`. Fact-driven or high-risk answers must place that URL in the first visible paragraph.
- Permitted evidence includes regulators, standards bodies, universities, trade associations, independent research or editorial sources, and non-competing experts.
- Simpro-owned links may be additional reader resources but never satisfy the non-owned FAQ-proof requirement.
- If compliant evidence cannot support a vendor-specific question, remove or reframe the FAQ and retain vendor evidence in the comparison or vendor-specific body section.

Use `context/aeo-geo-blog-strategy.md` as the canonical policy for Review Story Selection, Review Site Theme Selection, and approved quote/rating boundaries.

## Production SEO Blog Strategy Contract

Every new or changed Simpro blog, rewrite, optimization, analyze-existing pass, and existing blog on its next publish-readiness pass must use `blog-strategy-contract/v1`. Research writes exactly 1 `Search Intent and Format Decision`, `Commercial Pillar and Anchor Decision`, and `Lifecycle Refresh Record` to the validation sidecar. Duplicate sections or fields, placeholders, unsupported values, blocked decisions, and stale evidence fail closed. The exact field contract lives in `context/aeo-geo-blog-strategy.md` and the mirrored `seo-blog-strategy` rule files.

`context/commercial-pillar-index.json` is the only executable commercial-destination source. Every Simpro blog requires exactly 1 commercial pillar: a specific industry page for a vertical topic, solution page for a category or cross-workflow topic, or feature page for a capability-led topic. The industries hub requires a documented no-specific-fit reason. A blog cannot be the commercial pillar; an informational hub is only an optional supporting blog link. The article Brand and Market must match the verified record and Semrush database. Current US evidence cannot authorize another market. The article primary keyword must differ from the indexed main keyword; exact collisions fail, and containment requires verified SERP evidence of different intent and format.

The article body must contain the exact indexed canonical URL in the planned H2. At least 1 visible, human-readable Markdown anchor must contain the indexed main keyword as a contiguous case-insensitive phrase. Bare URLs, sidecar/frontmatter-only URLs, comments, code, images, generic anchors, unsupported synonyms, tracking parameters, fragments, and redirects fail. The index approves SEO routing only and never overrides vault product language, feature status, availability, source routing, or proof gates.

Every public `Source Map` claim row must include claim type, source class, original-source status, source and checked dates, direct claim fit, freshness decision/reason, status, and intended use. Statistics require original sources; regulations and standards require official sources. Competitor evidence cannot decide neutral recommendations or FAQs. The Source Map cannot bypass stricter proof, FAQ, vault-receipt, or named-feature gates.

High-volatility pricing, regulation, product-status, comparison, and statistics-led articles require review within 90 days; standard articles within 180 days. GSC, GA4, Semrush, and AI-citation lanes stay separate. Record unavailable or not-applicable lanes with reasons and never convert missing data to zero or claim improvement without dated evidence.

## Blog Schema Notes

For standard blog posts with FAQs, schema notes must list `BlogPosting`, `BreadcrumbList`, and `FAQPage`; nested entities must include `Question and Answer inside FAQPage`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`. For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. If a named author is present, include `author` in frontmatter and map it to `Person as author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and record the no-author decision in the blog assembly BOM and validation sidecar. Use `VideoObject` only when a video is embedded. Keep this aligned with `context/aeo-geo-blog-strategy.md`.
