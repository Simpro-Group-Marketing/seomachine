# Research Command

Use this command to research a new blog and build its production BOM before writing.

## Usage
`/research [topic]`

## Ownership
`/research` owns the research brief, the production BOM spec, and the production BOM. It does not draft, rewrite, patch, move, or publish public blog Markdown.

The new-blog route is `/research [topic]` followed by `/write [topic]`. `/write` owns the public draft. Python owns governance artifacts only: context packs and receipts, selector evidence, the recorded Semrush keyword decision, SERP evidence and the page-1 coverage map, the PAA artifact, the production BOM, the release record, and publishing transport.

Use `context/blog-editorial-strategy.md` for editorial planning, reader value, originality, structure, and narrative throughlines. Use `context/aeo-geo-blog-strategy.md` for AEO, proof, vault, citation, schema, production BOM, score-gate, and recovery-loop policy.

`/research` creates and freezes the production BOM for a new article. The BOM is the only list of facts, approved proof, PAA questions, sections, and links the article may use. It defines what the article must accomplish without prescribing final sentences. A BOM defect found later returns here: fix the spec or the research inputs and rebuild.

## Process

### 1. Resolve the article and its run id
- Resolve the topic, title, objective, audience, region, brand, market, working target query, and search intent.
- Choose the article path `drafts/[slug]-[YYYY-MM-DD].md`, dated with today's UTC date. AnswerSocrates records the UTC capture date as `collection_date`, and the BOM build requires it to equal the article date, so a local-date filename (for example an Australian morning) makes the PAA lane fail. Use the slug of the working target query so collected SERP evidence lands on the layout path. The path stays fixed for the run.
- The command runs `python -m data_sources.modules.production.layout "drafts/[slug]-[YYYY-MM-DD].md"`. It prints the slug, date, workflow mode, every artifact path, and the production `run_id`, minting and storing the run id in `research/runs/[slug]-[YYYY-MM-DD].json` when none exists. Every later lane uses these paths and this run id.
- Classify the binding branch from the brand metadata: Simpro-owned or Simpro-signal work is connector-bound; AroFlo, BigChange, and ClockShark work with no Simpro signal is nonconnector (see `context/aeo-geo-blog-strategy.md`). The builder decides the branch from the BOM spec (`bom_build.is_nonconnector`): a nonconnector brand stays nonconnector only when no Simpro name or official `simprogroup.com` URL appears anywhere in the spec, including facts, links, and the CTA; any Simpro signal makes the spec connector-bound.

### 2. Semrush keyword decision (runs first, one lane)
Semrush runs in one Chrome session, so it is a single sequential lane, never parallel. It runs before the parallel lanes: the context-build spec needs `primary_keyword` and the commercial pillar, and the SERP and PAA lanes need the target query.
- Use the authenticated Semrush UI in the main Chrome profile, the default database from the canonical strategy, and the connector report sequence it lists.
- Choose by intent fit first, then page ownership and cannibalization risk, then volume, difficulty, CPC, trend, SERP shape, and competitor feasibility.
- Save the verbatim captured Semrush page text as `research/semrush-transcript-[slug]-[date].txt` and the decision input as `research/semrush-keyword-input-[slug]-[date].json`. The input is one JSON object with exactly these keys (`keyword_record._INPUT_KEYS`): `brand`, `market`, `database`, `collection_date`, `source_boundary`, `seed_terms`, `connector_reports`, `candidate_metrics`, `serp_finalists`, `question_candidates`, `related_candidates`, `selected_primary_keyword`, `selected_secondary_keywords`, `rejected_keywords`, `selection_rationale`, and `decision_rule`. Any other key is refused.
- The command runs `python -m data_sources.modules.production.keyword_record --decision "research/semrush-keyword-input-[slug]-[date].json" --transcript "research/semrush-transcript-[slug]-[date].txt" --output "[layout keyword_decision path]" --shortlist-output "[layout keyword_shortlist path]"`. It refuses any candidate metric that the transcript does not show next to its keyword. Never type Semrush numbers.
- Choose the commercial pillar for the selected primary keyword from `context/commercial-pillar-index.json`. The parallel lanes use the selected primary keyword as their target query, so the context-build spec, the SERP evidence query, and the PAA query all carry the same keyword.
- A Semrush UI timeout or reset is `blocked_semrush_ui_refresh`: stop before the BOM build. Do not substitute Semrush API, MCP, stale exports, or estimates.

### 3. Parallel research lanes
Once the keyword decision is recorded, dispatch these lanes as parallel subagents. Each lane writes only its own artifacts and returns a short summary. Subagents never write public copy and never add a BOM entry the builder has not verified; they return candidates, and the builder decides.

- **Vault context and approved proof.** For connector-bound work, the command writes `research/context-build-spec-[slug]-[date].json` from `config/context-build-spec.example.json` and runs `python -m data_sources.modules.context_build research/context-build-spec-[slug]-[date].json`; if the run stops (memory pressure, timeout), rerun with `--resume`. Its public stage must write the layout's `context_pack` and `context_receipt` paths. Stage `claim_requests`, claim lookups, and proof-boundary text come from this topic only. Then the command runs the connector customer-proof selector selector-first, exactly as `.claude/rules/customer-proof.md` prescribes, against the layout's public `context_pack` and `context_receipt` (the pack the BOM build approves proof from), with `--evidence-output` set to the layout's `customer_proof_evidence` path. For nonconnector work, it skips the vault and runs `python data_sources/modules/nonvault_customer_proof_selector.py "[topic]" --brand "[brand]" --title "[title]" --objective "[objective]" --article-slug "[slug]" --index config/nonvault-customer-proof-index.json --ledger config/customer-proof-usage-ledger.json --evidence-output "research/nonvault-customer-proof-selector-evidence-[slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`; the evidence path is the layout's undated `nonvault_customer_proof_evidence` path. Return the selected claim IDs per role, or the no-fit outcome. If both vault connector paths fail, stop and record the blocker in the research brief.
- **SERP evidence and page-1 coverage.** Collect SERP evidence for the selected primary keyword (the SERP evidence `query` is the query every other lane uses) through the `/research-serp` collector order (DataForSEO, then the Playwright fallback). If the evidence file name differs from the layout's `serp_evidence` path, copy it there byte for byte. Once the PAA lane has finished, the command runs `python -m data_sources.modules.production.serp_coverage "[article]"`; it fetches the top 10 results, extracts their H2/H3 outlines, and writes the page-1 coverage map with suggested `must` and `should` topics and the PAA questions no page covers.
- **PAA capture.** The command runs `python data_sources/modules/paa_provenance_guard.py record --query "[the exact SERP evidence query]" --collection-date "[article date]" --run-id "[run_id from the layout command]" --raw-capture-output "research/answersocrates-playwright-raw-[slug]-[date].json" --workspace-root "." --output "[layout paa_artifact path]"`. The `--run-id` value must be the production run id, `--collection-date` must be the article date (today's UTC date), and `--query` must equal the SERP evidence query the scorer expects, or the build or the release refuses the artifact. Never hand-author PAA questions.
- **Source facts.** Find authoritative public pages for every factual, numeric, regulatory, or comparative point the article will need. For each, return the page URL, an exact quote copied from the visible page text, and the claim the quote supports. The builder admits the fact only when the quote supports the claim: the quote has at least 6 words; at least half of the claim's content words appear in the quote; every number in the claim appears in the quote; comparator, quantifier, and negation words the claim leans on (more, fewer, less, over, under, most, least, only, all, every, not, no, never, without, at least, at most, up to) also appear in the quote; and the quote adds no narrowing or reversing word (fewer, less, under, below, least, only, not, no, never, at least, at most, up to) that the claim lacks. Prefer primary and independent sources; competitor-owned pages cannot support a neutral verdict, recommendation, or FAQ. For connector-bound Simpro work, also evaluate Fred Voccola authority under the canonical policy; a Fred observation reaches the article only as a fact whose quote the builder verifies on its public page.

When Hindsight internal-strategy evidence is relevant, use it to shape only the private reader angle, section emphasis, section purposes, objections, and commercial framing. Record it in the brief with `public_claim_use: prohibited` and `claim_support_allowed: false`. It never becomes a BOM fact, proof item, PAA question, or link.

### 4. Research brief and BOM spec
- Save the research brief to `research/brief-[slug]-[date].md`: searcher task, intent class, funnel stage, content type and format decision, Reader Contract, section throughlines, at least 1 original contribution and the section that delivers it, entity coverage, the commercial pillar and cannibalization decision, the lifecycle (volatility and next review date), `FAQ policy: required | not_applicable` with its rationale, the competitor and gap notes, the planned early artifact, and the meta title and description drafts.
- Claude writes `research/production-bom-spec-[slug]-[date].json` (schema `simpro-production-bom-spec/v1`; see `data_sources/modules/production/bom.py` for every field):
  - `brand`, `market`, `title`, `objective`, `audience`, `cta` (`text`, `url`), and `schema_notes` from the allowed list;
  - `sections`: heading, purpose, and `must` or `should`. Choose them from the coverage map: confirm or override its suggestions and add the sections that give the article its own value;
  - `facts`: id, claim, url, exact quote, priority, from the source-facts lane;
  - `proof`: id, `claim_id`, `kind` (`metric`, `quote`, `theme`, or `experience_story`), priority, using only claim IDs the selector selected;
  - `paa_questions`: question and priority, copied from the PAA artifact's eligible questions;
  - `links`: url, anchor, kind (`commercial_pillar`, `internal`, `external`), priority. Connector-bound work needs exactly one `must` commercial pillar link whose `destination_id` and canonical URL match `context/commercial-pillar-index.json` and whose anchor contains that destination's main keyword;
  - for nonconnector work only, `not_applicable_context_reason`.

### 5. Build the BOM
The command runs `python -m data_sources.modules.production.bom_build "drafts/[slug]-[date].md"`. It admits a fact only if its quote is on the live page now and supports the claim, a proof item only if its claim is approved and selected by the selector, and a PAA question only if it is in the PAA artifact for this run. Exit `1` lists every refusal reason: fix the spec or the research inputs and rebuild. Exit `2` is an operational error. The BOM build must succeed before `/write`.

## Output
Report the article path, run id, BOM path, the selected primary keyword with its Semrush numbers from the shortlist, the `must` and `should` sections, the facts and proof admitted, the PAA questions selected, and any refusal or blocker.

The release thresholds the article must meet later are content quality 85/100+, SEO quality release floor 90/100+ and optimization target 95/100, and AEO/GEO 90/100+.

## Next Steps
1. Run `/write [topic]` to draft the article from the production BOM.
2. `/write` runs `/scrub` and `/publish-readiness`, which runs the one-pass release.
3. If the release blocks, follow the recovery loop in `context/aeo-geo-blog-strategy.md`.
