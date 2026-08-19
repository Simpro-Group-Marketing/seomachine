# Agent Instructions

This repo is proof-sensitive. Never synthesize data, customer claims, review claims, metrics, rankings, PAA questions, or quotes.

## Simpro Vault Source Rule

Use the Simpro vault connector as the active context source only when the final artifact is Simpro-owned or contains a Simpro signal. A Simpro signal is the name `Simpro` or an official `simprogroup.com` URL, including schemeless URLs and subdomains. AroFlo, BigChange, and ClockShark owned artifacts with no Simpro signal are nonconnector workflows. Missing, unknown, or malformed brand metadata fails closed into the connector workflow. The only configured connector content location is the vault root; prompts, guards, selectors, and workflow docs must not prescribe vault hubs, filenames, or internal directories.

For connector-bound workflows, run vault health first, describe available roles/topics/entities, search in the task's natural language, read and expand results by `resource_id`, query approved claims only when public proof-sensitive language is needed, then build and validate a context pack. Evidence in validation sidecars must be bound to connector output: `context_pack_hash`, `receipt_hash`, `resource_id`, `claim_id`, use mode, public URL when required, and relevant manifest/revision values.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault connector exposes them as source evidence.

The repo-local context files are downstream mirrors or operational state only. They cannot override the vault connector when the vault is available. If repo-local fallback is used because the vault is unavailable, document the explicit vault-unavailable blocker in the validation sidecar and do not make unsupported public claims.

Every workflow requires a generated Context Binding decision. Connector-bound workflows require vault context evidence. AroFlo, BigChange, and ClockShark workflows with no Simpro signal require an explicit nonconnector binding and must omit context request/pack/receipt, Fred evidence, and vault-dependent customer-proof selector evidence. `Vault Brand Language Alignment` applies when connector-bound product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` applies to competitor-aware posts; `Named Feature/Add-On Link Check` applies when named Simpro features/add-ons appear. Connector evidence sections must cite resource IDs and claim IDs rather than fixed vault routes. Missing required evidence blocks `/publish-readiness`, `/optimize`, and dev-ready handoff.

## Author-Led Blog Voice

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

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

For nonconnector AroFlo, BigChange, and ClockShark workflows, do not run the vault-dependent customer-proof selector and do not publish customer stories, testimonials, review-derived anecdotes, ratings, or quotes unless a separate approved non-vault proof-eligibility contract is available.

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

When content quality is below 85/100 or AEO/GEO is below 90/100, continue automatically through the AEO/GEO Recovery Loop in `context/aeo-geo-blog-strategy.md`. Review `aeo_geo.checks`, distinguish copy or proof gaps from a scorer or parser false negative, apply the top 3-5 fixes, and rerun `/scrub` plus `/publish-readiness`. Do not stop at reporting a low score. After 2 unsuccessful iterations, route to `review-required/` with exact failed checks and attempted fixes.

## FAQ Answer Quality

Every FAQ answer must use a 40-60 word first visible paragraph and lead with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Generic openers such as `There is no`, `It depends`, `Pricing depends`, `Costs vary`, `We do not know`, `It is unclear`, and `No source ranks` block publish readiness. Put limitations after the direct answer.

Every FAQ answer must also contain at least 1 authoritative non-owned public evidence link in the visible answer. A Source Map or FAQ Proof Map can document the same evidence but cannot replace that reader-facing link. If no defensible evidence-backed answer exists, replace or remove the question. The `faq_answer_quality_guard.py` and `faq_proof_guard.py` gates both run inside `/publish-readiness`.
## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert.
- Competitor-owned FAQ sources: prohibited.
- Every visible non-owned FAQ URL requires its own exact `FAQ Proof Map` row in the validation sidecar: `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`.
- Permitted evidence includes regulators, standards bodies, universities, trade associations, independent research or editorial sources, and non-competing experts.
- Simpro-owned links may be additional reader resources but never satisfy the non-owned FAQ-proof requirement.
- If compliant evidence cannot support a vendor-specific question, remove or reframe the FAQ and retain vendor evidence in the comparison or vendor-specific body section.

Use `context/aeo-geo-blog-strategy.md` as the canonical policy for Review Story Selection, Review Site Theme Selection, and approved quote/rating boundaries.

## Blog Schema Notes

For standard blog posts with FAQs, schema notes must list `BlogPosting`, `BreadcrumbList`, and `FAQPage`; nested entities must include `Question and Answer inside FAQPage`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`. For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. If a named author is present, include `author` in frontmatter and map it to `Person as author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and record the no-author decision in the blog assembly BOM and validation sidecar. Use `VideoObject` only when a video is embedded. Keep this aligned with `context/aeo-geo-blog-strategy.md`.
