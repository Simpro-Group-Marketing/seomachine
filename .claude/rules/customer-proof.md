# Customer Proof Rule

Apply this selector-first rule to connector-bound blog drafts, rewrites, and research proof sidecars.

AroFlo, BigChange, and ClockShark owned workflows with no Simpro name or official `simprogroup.com` URL are nonconnector. Do not run the vault-dependent selector for those workflows. Under a separate approved non-vault proof-eligibility contract, run `python data_sources/modules/nonvault_customer_proof_selector.py "[topic]" --brand "[brand]" --title "[title]" --objective "[objective]" --article-slug "[slug]" --evidence-output "research/nonvault-customer-proof-selector-evidence-[topic-slug]-[YYYY-MM-DD].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`. Require `simpro-nonvault-customer-proof-selector-evidence/v1` bound to the approved proof index and usage ledger. V1 allows approved brand-owned customer stories, case studies, and references only; it excludes review-platform stories, exact quotes, customer metrics, ratings, star claims, and named-person attribution.

Apply this selector-first rule to blog drafts, rewrites, and research proof sidecars. Before selecting customer proof, resolve `topic`, `title`, and `objective`, then automatically run:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10
```

For review-derived public E-E-A-T stories, automatically run:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles experience_story --require-eeat-story --limit 10
```

Write the generated selector-first `Customer Proof Slate` to the validation sidecar before drafting customer proof. "Consult" means reviewing generated selector output, not skipping execution. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the validation sidecar and do not invent proof. experience_story consideration is required and E-E-A-T story usage is optional; if no story fits, use `Selected: [none]` with section-specific rejection reasons. Edit selected/rejected rows only when editorial judgment requires it.

## Selection and reuse

Use `context/customer-proof-index.json` for curated proof routes and `context/customer-proof-usage-ledger.json` for reuse. Choose the most relevant approved proof, not the easiest mapped case study. Treat any `recent_uses_90d` value above 0 as a proof-diversity warning. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. If a recently used or overused source remains the best fit, add a `Customer Proof Selection Decision` and source-specific `Reuse reason` proving no stronger underused approved proof fits the same role.

## Public-copy use

When selected customer proof appears in public copy, add `Selected Customer Proof Mining` to the validation sidecar. Selector chooses candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. Review-derived E-E-A-T stories require `Review Story Selection` in the validation sidecar and same-paragraph public review links. Use a proof-backed customer/review POV only when it improves the article objective. If no actual person or business POV fits, omit the story. Fictional named personas are prohibited; unnamed workflow scenarios are explanatory only and do not count as E-E-A-T. Use `context/aeo-geo-blog-strategy.md` as the canonical policy.

## Proof inventory

Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates. Add new proof candidates through `context/customer-proof-intake-template.csv` and validate them with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.

## Publish handoff

Run `/publish-readiness` before handoff. Its complete gate and seal contract is the only publication-readiness authority.
