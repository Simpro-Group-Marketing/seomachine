# Agent Instructions

This repo is proof-sensitive. Never synthesize data, customer claims, review claims, metrics, rankings, PAA questions, or quotes.

## Obsidian Vault Source Rule

For every blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decision, use the Obsidian vault as the active context source: `C:\Users\patrick.grueschow\Desktop\Obsidian\Simpro Brand Context`.

Required read order: `AGENTS.md -> wiki/cache/hot.md -> wiki/Brand Graph Index.md -> smallest relevant wiki/source/raw pages`.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault already exposes a local source route.

The repo-local context files are downstream mirrors/fallbacks only and cannot override the vault when the vault is available. If a repo-local fallback is used because the vault is unavailable, document that in `Vault Context Read Path` in the validation sidecar.

Required validation sidecar sections: `Vault Context Read Path` for every workflow; `Competitive Shortlist Decision` for competitor-aware posts; `Named Feature/Add-On Link Check` when named Simpro features/add-ons appear. Missing required sections block `/publish-readiness`, `/optimize`, and dev-ready handoff until documented.

## Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: competitor-aware posts must document selected competitors, rejected competitors, `wiki/competitors/Competitive Context.md`, `wiki/sources/simpro-battlecards-direct-competitors-1bzgf9r8.md`, and linked source/raw files in the validation sidecar, plus why the shortlist fits the article objective.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified. Route Hindsight context through `wiki/sources/hindsight-copy-of-simpro-battlecards-1elcobgn.md` and keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked against vault product routes before link decisions. Start with `wiki/concepts/payments-and-add-ons.md` and `wiki/features/Feature Library`; document each vault route checked, link decision, and reason in the validation sidecar.


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

Use `context/aeo-geo-blog-strategy.md` as the canonical policy for Review Story Selection, Review Site Theme Selection, and approved quote/rating boundaries.

## Blog Schema Notes

For standard blog posts with FAQs, schema notes must list `BlogPosting`, `BreadcrumbList`, and `FAQPage`; nested entities must be `Person as author`, `Question and Answer inside FAQPage`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`. For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. Use `VideoObject` only when a video is embedded. Keep this aligned with `context/aeo-geo-blog-strategy.md`.

