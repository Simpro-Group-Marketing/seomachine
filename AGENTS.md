# Agent Instructions

This repo is proof-sensitive. Never synthesize data, customer claims, review claims, metrics, rankings, PAA questions, or quotes.

## Obsidian Vault Source Rule

For every blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decision, use the Obsidian vault as the active context source: `C:\Users\patrick.grueschow\Desktop\Obsidian\Simpro Brand Context`.

Required read order: `AGENTS.md -> wiki/cache/hot.md -> wiki/Brand Graph Index.md -> smallest relevant wiki/source/raw pages`.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault already exposes a local source route.

The repo-local context files are downstream mirrors/fallbacks only and cannot override the vault when the vault is available. If a repo-local fallback is used because the vault is unavailable, document that in `Vault Context Read Path` in the validation sidecar.

Required validation sidecar sections: `Vault Context Read Path` for every workflow; `Vault Brand Language Alignment` when product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` for competitor-aware posts; `Named Feature/Add-On Link Check` when named Simpro features/add-ons appear. Missing required sections block `/publish-readiness`, `/optimize`, and dev-ready handoff until documented.

## Author-Led Blog Voice

For every Simpro blog, read `wiki/messaging/Voice and Tone.md` and `wiki/messaging/Tone Voice and Localization Rules.md` from the vault. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

## Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: competitor-aware posts must document selected competitors, rejected competitors, `wiki/competitors/Competitive Context.md`, `wiki/sources/simpro-battlecards-direct-competitors-1bzgf9r8.md`, and linked source/raw files in the validation sidecar, plus why the shortlist fits the article objective.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified. Route Hindsight context through `wiki/sources/hindsight-copy-of-simpro-battlecards-1elcobgn.md` and keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked against vault product routes before link decisions. Start with `wiki/concepts/payments-and-add-ons.md` and `wiki/features/Feature Library`; document each vault route checked, link decision, and reason in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from the vault first. Read `wiki/messaging/Simpro Core Messaging Repository.md`, `wiki/messaging/Message House.md`, `wiki/messaging/Core Value Pillars.md`, `wiki/product/Product Positioning.md`, and `wiki/features/Feature Library.md`; when a named feature/add-on appears, add the relevant `wiki/features/source-docs/` route or specific source/raw route; when solution/industry language is used, also read `wiki/verticals/Vertical Profile Library.md` and the relevant vertical/source page. Document routes checked, language applied, fallback context use, source-verification boundary, and `Status: aligned` in `Vault Brand Language Alignment`. The `vault_brand_language_guard.py` publish gate runs inside `/publish-readiness`; keep this block in the validation sidecar, not public copy. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.


## Customer Proof Selection

Before selecting customer proof for a blog, article, rewrite, or optimization pass, the command workflow must resolve `topic`, `title`, and `objective`, automatically run:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10
```

Use `context/customer-proof-index.json` for curated proof routes and `context/customer-proof-usage-ledger.json` for reuse. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live scan finds public-copy usage missing from the ledger, update `context/customer-proof-usage-ledger.json` before selecting proof, rerun the proof health/selector checks, and document the backfill in the validation sidecar. Write the generated selector-first `Customer Proof Slate` to the validation sidecar before drafting customer proof; "consult" means reviewing generated selector output, not skipping execution. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the validation sidecar and do not invent proof. Edit selected/rejected rows only when editorial judgment requires it. experience_story consideration is required and E-E-A-T story usage is optional; if no story fits, use `Selected: [none]` with section-specific rejection reasons. Choose the most relevant approved proof, not the easiest mapped case study. If a repeated proof source is still the best fit, document a `Customer Proof Selection Decision` and a source-specific `Reuse reason` proving no stronger underused approved proof fits the same role.

Treat any `recent_uses_90d` value above 0 as a proof-diversity warning, not only sources marked `overused`. Prefer an approved zero-recent-use source when one fits the same role. If a recently used or overused proof source is still selected, the validation sidecar must explain why no stronger underused approved proof fits.

When selected customer proof appears in public copy, add `Selected Customer Proof Mining` to the validation sidecar and add a matching entry to `context/customer-proof-usage-ledger.json` before final handoff. Selector chooses candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. Use `context/aeo-geo-blog-strategy.md` as the canonical policy.

Use `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` to inspect proof inventory gaps, recent use, and overuse before adding new proof or running selector slates.

Add new proof candidates through `context/customer-proof-intake-template.csv` and validate them with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.

For review-derived public E-E-A-T stories, the command workflow must automatically run:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles experience_story --require-eeat-story --limit 10
```

Review-derived E-E-A-T stories require `Review Story Selection` in the sidecar and same-paragraph public review links. Use `context/aeo-geo-blog-strategy.md` for identity and proof boundaries.

Use a proof-backed customer/review POV only when it improves the article objective. If no actual person or business POV fits, omit the story. Fictional named personas are prohibited; unnamed workflow scenarios are explanatory only and do not count as E-E-A-T.

For Capterra theme use, add `Review Site Theme Selection` with `Capterra tab row`, `https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`, and `Status: approved for paraphrased review-theme use`. Same-paragraph link required; no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved.

## Fred Voccola Authority Selection

For every new or changed Simpro blog and every rewrite, analysis, optimization, or publish-readiness pass, resolve `topic`, `title`, and `objective`, automatically run:

```powershell
python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --limit 5
```

Write the complete `Fred Voccola Authority Selection` block to the validation sidecar. Evaluation is mandatory; public use is optional. The vault is the sole eligibility source, and the selector must fail closed unless the manifest hashes for `fred-voccola-media-inventory.csv` and `authority-signal-matrix.csv` are current. Do not invent evidence when the vault, manifest, inventory, or selector is blocked.

Fred evidence supports Expertise and Authority by default. It counts as Experience only when the source explicitly supports first-hand personal or operating experience, and it remains additive to customer Experience proof, customer stories, and independent evidence. Exact article quotes require `source_visible_article_text`; exact video/audio quotes require `transcript_and_playback`, a timestamp, and playback verification; paraphrases require `paraphrase_evidence`. Exact quotes and paraphrased observations need a contextual public link in the same paragraph. A playlist-only row is for discovery or embedding, never independent earned-media authority.

Embed only a selected, public, embeddable YouTube source that materially supports the section. Use a responsive 16:9 `youtube-nocookie.com` handoff with a visible fallback link, descriptive title, lazy loading, no autoplay, and verified metadata. Require `VideoObject` if and only if a video is embedded. No usage ledger or frequency penalty applies in v1; topical support controls selection. Existing content is not bulk-backfilled, but this evaluation is required when it is next rewritten, optimized, or passed through publish readiness.

## Proof Gates

Proof-only infrastructure belongs in `research/validation-[topic-slug]-[YYYY-MM-DD].md`, not in public blog copy. Run proof-aware gates with `--proof-sidecar`.

Preferred publish readiness command:

```powershell
/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

The customer proof diversity gate is mandatory before scoring or publish readiness and runs inside `/publish-readiness`.

The guard requires Quote Matrix, Reference, Customer Story, or review-site search evidence when case studies are used. Exact quotes, named reviewers, ratings, badges, rankings, and testimonials require approved proof rows with source-visible evidence.

The review story identity gate is mandatory before scoring or publish readiness whenever review-derived story copy appears and runs inside `/publish-readiness`.

The early artifact and answer withholding gates run inside `/publish-readiness`: a usable artifact within the first 300 words of body copy, concrete answers for number/range/template queries, and no placeholder table scaffolds. Policy lives in `context/aeo-geo-blog-strategy.md`.

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

## Production SEO Blog Strategy Contract

Every new or changed Simpro blog, rewrite, optimization, analyze-existing pass, and existing blog on its next publish-readiness pass must use `blog-strategy-contract/v1`. Research writes exactly 1 `Search Intent and Format Decision`, `Commercial Pillar and Anchor Decision`, and `Lifecycle Refresh Record` to the validation sidecar. Duplicate sections or fields, placeholders, unsupported values, blocked decisions, and stale evidence fail closed. The exact field contract lives in `context/aeo-geo-blog-strategy.md` and the mirrored `seo-blog-strategy` rule files.

`context/commercial-pillar-index.json` is the only executable commercial-destination source. Every Simpro blog requires exactly 1 commercial pillar: a specific industry page for a vertical topic, solution page for a category or cross-workflow topic, or feature page for a capability-led topic. The industries hub requires a documented no-specific-fit reason. A blog cannot be the commercial pillar; an informational hub is only an optional supporting blog link. The article Brand and Market must match the verified record and Semrush database. Current US evidence cannot authorize another market. The article primary keyword must differ from the indexed main keyword; exact collisions fail, and containment requires verified SERP evidence of different intent and format.

The article body must contain the exact indexed canonical URL in the planned H2. At least 1 visible, human-readable Markdown anchor must contain the indexed main keyword as a contiguous case-insensitive phrase. Bare URLs, sidecar/frontmatter-only URLs, comments, code, images, generic anchors, unsupported synonyms, tracking parameters, fragments, and redirects fail. The index approves SEO routing only and never overrides vault product language, feature status, availability, source routing, or proof gates.

Every public `Source Map` claim row must include claim type, source class, original-source status, source and checked dates, direct claim fit, freshness decision/reason, status, and intended use. Statistics require original sources; regulations and standards require official sources. Competitor evidence cannot decide neutral recommendations or FAQs. The Source Map cannot bypass stricter proof, FAQ, vault-receipt, or named-feature gates.

High-volatility pricing, regulation, product-status, comparison, and statistics-led articles require review within 90 days; standard articles within 180 days. GSC, GA4, Semrush, and AI-citation lanes stay separate. Record unavailable or not-applicable lanes with reasons and never convert missing data to zero or claim improvement without dated evidence.

## Blog Schema Notes

A valid `Last Updated: YYYY-MM-DD` remains required and cannot be future-dated. Missing author passes. A verified author is an optional Expertise signal; author, reviewer, and credential claims remain proof-gated when present.

For public Markdown blog artifacts, put the checked CMS handoff in `schema_notes` inside the top YAML frontmatter. Always list `BlogPosting`, `BreadcrumbList`, `ImageObject`, and Organization as publisher reference. Add `FAQPage` with nested Question/Answer only when visible FAQs exist. Include Person only when a verified author exists. Add `VideoObject` if and only if a video is embedded. Schema notes must never be reported as rendered JSON-LD implementation.
