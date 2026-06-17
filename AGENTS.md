# Agent Instructions

This repo is proof-sensitive. Never synthesize data, customer claims, review claims, metrics, rankings, PAA questions, or quotes.

## Customer Proof Selection

Before selecting customer proof for a blog, article, rewrite, or optimization pass, run or consult:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme --limit 10
```

Use `context/customer-proof-index.json` for curated proof routes and `context/customer-proof-usage-ledger.json` for reuse. Generate a selector-first `Customer Proof Slate` before drafting customer proof; edit selected/rejected rows only when editorial judgment requires it. Choose the most relevant approved proof, not the easiest mapped case study. If a repeated proof source is still the best fit, document a `Customer Proof Selection Decision` and a source-specific `Reuse reason` proving no stronger underused approved proof fits the same role.

Use `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` to inspect proof inventory gaps and overuse before adding new proof or running selector slates.

Add new proof candidates through `context/customer-proof-intake-template.csv` and validate them with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.

For review-derived public E-E-A-T stories, run or consult:

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

Use `context/aeo-geo-blog-strategy.md` as the canonical policy for Review Story Selection, Review Site Theme Selection, and approved quote/rating boundaries.
