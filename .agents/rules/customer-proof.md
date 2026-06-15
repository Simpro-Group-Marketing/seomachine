# Customer Proof Rule

Apply this selector-first rule to blog drafts, rewrites, and research proof sidecars.

Before drafting customer proof, run or consult:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme --limit 10
```

Generate a `Customer Proof Slate` in the validation sidecar with metric, quote, and theme roles. Add `experience_story` when review-derived copy is considered. Edit selected/rejected rows only when editorial judgment requires it. Use `context/aeo-geo-blog-strategy.md` as the canonical policy.

Use a proof-backed customer/review POV only when it improves the article objective. If no actual person or business POV fits, omit the story. Fictional named personas are prohibited; unnamed workflow scenarios are explanatory only and do not count as E-E-A-T.

Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates.

Add new proof candidates through `context/customer-proof-intake-template.csv` and validate them with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.

Run publish readiness before handoff:

```powershell
python data_sources/modules/publish_readiness.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```
