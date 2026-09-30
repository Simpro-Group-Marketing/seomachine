# Customer Proof Rule

Apply this selector-first rule to connector-bound blog drafts, rewrites, and research proof sidecars.

## Connector-bound Simpro workflows

Before selecting customer proof, resolve `topic`, `title`, and `objective`, then run:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10
```

For review-derived public E-E-A-T stories, also run:

```powershell
python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles experience_story --require-eeat-story --limit 10
```

Simpro candidates come exclusively from approved claim results bound to the current context pack and receipt. The selector requires complete, non-truncated task-specific claim searches for `public_metric`, `exact_quote`, and `public_paraphrase`, uses `claim_id` as the candidate identifier, and fails closed on legacy local `--index` use.

Write the generated selector-first `Customer Proof Slate` to the validation sidecar before drafting customer proof. If inputs are missing or the selector fails, write the blocker into the validation sidecar and do not invent proof.

## Selection and reuse

Choose the most relevant approved claim, not the easiest searchable case study. Treat any `recent_uses_90d` value above 0 as a proof-diversity warning. Before claiming a proof source is underused, inspect `config/customer-proof-usage-ledger.json` and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the claim ID, public URL, and customer name. If public-copy usage is missing from the ledger, backfill `config/customer-proof-usage-ledger.json`, rerun selector checks, and document the backfill.

When selected proof is recently used or overused, add a `Customer Proof Selection Decision` and source-specific `Reuse reason` proving no stronger underused approved claim fits the same role.

## Nonconnector workflows

AroFlo, BigChange, and ClockShark owned workflows with no Simpro name or official `simprogroup.com` URL are nonconnector. Do not run the vault-dependent selector. When the separate non-vault proof contract applies, run the nonvault selector against `config/nonvault-customer-proof-index.json` and require `simpro-nonvault-customer-proof-selector-evidence/v1`.

Run `python data_sources/modules/nonvault_customer_proof_selector.py "[topic]" --brand "[brand]" --title "[title]" --objective "[objective]" --proof-index config/nonvault-customer-proof-index.json --ledger config/customer-proof-usage-ledger.json --evidence-output "research/nonvault-customer-proof-selector-evidence-[topic-slug].json" --slate` for eligible nonconnector proof workflows. V1 permits approved brand-owned customer stories, case studies, and references, plus approved Capterra `review_site` rows on the brand's listed product page. Review-derived stories are paraphrased with a same-paragraph review link; exact snippets are allowed only when stored in that row's `approved_quotes` and live-captured. It does not permit ratings, stars, aggregate ratings, rankings, review metrics, or named-person attribution beyond the approved review row; avoid the words "reviewer", "rated", and "stars" in public copy.

Run `python data_sources/modules/customer_proof_index_health.py --index config/nonvault-customer-proof-index.json --ledger config/customer-proof-usage-ledger.json` only for nonconnector inventory health. Add new nonconnector proof candidates through an intake CSV and validate them with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index config/nonvault-customer-proof-index.json`.

## Public-copy use

When selected customer proof appears in public copy, add `Selected Customer Proof Mining` to the validation sidecar and add the final public use to `config/customer-proof-usage-ledger.json`. Review-derived E-E-A-T stories require `Review Story Selection` and same-paragraph public review links. Use `context/aeo-geo-blog-strategy.md` as the canonical policy.
