# Customer Proof Rule

Apply this selector-first rule to blog drafts, rewrites, and research proof sidecars.

Before drafting customer proof, run or consult:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme --limit 10
```

Generate a `Customer Proof Slate` in the validation sidecar with metric, quote, and theme roles. Add `experience_story` when review-derived copy is considered. Edit selected/rejected rows only when editorial judgment requires it. Use `context/aeo-geo-blog-strategy.md` as the canonical policy.

Run publish readiness before handoff:

```powershell
python data_sources/modules/publish_readiness.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```
