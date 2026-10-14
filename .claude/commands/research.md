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
- Choose the article path `drafts/[slug]-[YYYY-MM-DD].md`, dated today. Use the slug of the working target query so collected SERP evidence lands on the layout path. The path stays fixed for the run.
- The command runs `python -m data_sources.modules.production.layout "drafts/[slug]-[YYYY-MM-DD].md"`. It prints the slug, date, workflow mode, every artifact path, and the production `run_id`, minting and storing the run id in `research/runs/[slug]-[YYYY-MM-DD].json` when none exists. Every later lane uses these paths and this run id.
- Classify the binding branch from the brand metadata: Simpro-owned or Simpro-signal work is connector-bound; AroFlo, BigChange, and ClockShark work with no Simpro signal is nonconnector (see `context/aeo-geo-blog-strategy.md`).

### 2. Parallel research lanes
Dispatch these lanes as parallel subagents. Each lane writes only its own artifacts and returns a short summary. Subagents never write public copy and never add a BOM entry the builder has not verified; they return candidates, and the builder decides.

- **Vault context and approved proof.** For connector-bound work, the command writes `research/context-build-spec-[slug]-[date].json` from `config/context-build-spec.example.json` and runs `python -m data_sources.modules.context_build research/context-build-spec-[slug]-[date].json`; if the run stops (memory pressure, timeout), rerun with `--resume`. Its public stage must write the layout's `context_pack` and `context_receipt` paths. Stage `claim_requests`, claim lookups, and proof-boundary text come from this topic only. Then the command runs the connector customer-proof selector selector-first, exactly as `.claude/rules/customer-proof.md` prescribes, with `--evidence-output` set to the layout's `customer_proof_evidence` path. For nonconnector work, it skips the vault and runs the nonvault selector from the same rule with `--evidence-output` set to the layout's `nonvault_customer_proof_evidence` path. Return the selected claim IDs per role, or the no-fit outcome. If both vault connector paths fail, stop and record the blocker in the research brief.
- **SERP evidence and page-1 coverage.** Collect SERP evidence for the working target query through the `/research-serp` collector order (DataForSEO, then the Playwright fallback). If the evidence file name differs from the layout's `serp_evidence` path, copy it there byte for byte. Once the PAA lane has finished, the command runs `python -m data_sources.modules.production.serp_coverage "[article]"`; it fetches the top 10 results, extracts their H2/H3 outlines, and writes the page-1 coverage map with suggested `must` and `should` topics and the PAA questions no page covers.
- **PAA capture.** The command runs `python data_sources/modules/paa_provenance_guard.py record --query "[working target query]" --collection-date "[article date]" --run-id "[run_id from the layout command]" --raw-capture-output "research/answersocrates-playwright-raw-[slug]-[date].json" --workspace-root "." --output "[layout paa_artifact path]"`. The `--run-id` value must be the production run id and `--collection-date` must be the article date, or the BOM build refuses the artifact. Never hand-author PAA questions.
- **Source facts.** Find authoritative public pages for every factual, numeric, regulatory, or comparative point the article will need. For each, return the page URL, an exact quote of at least 6 words copied from the visible page text, and the claim the quote supports. Numbers in a claim must appear in its quote. Prefer primary and independent sources; competitor-owned pages cannot support a neutral verdict, recommendation, or FAQ. For connector-bound Simpro work, also evaluate Fred Voccola authority under the canonical policy; a Fred observation reaches the article only as a fact whose quote the builder verifies on its public page.

When Hindsight internal-strategy evidence is relevant, use it to shape only the private reader angle, section emphasis, section purposes, objections, and commercial framing. Record it in the brief with `public_claim_use: prohibited` and `claim_support_allowed: false`. It never becomes a BOM fact, proof item, PAA question, or link.

### 3. Semrush keyword decision (one lane)
Semrush runs in one Chrome session, so it is a single sequential lane, never parallel.
- Use the authenticated Semrush UI in the main Chrome profile, the default database from the canonical strategy, and the connector report sequence it lists.
- Choose by intent fit first, then page ownership and cannibalization risk, then volume, difficulty, CPC, trend, SERP shape, and competitor feasibility.
- Save the verbatim captured Semrush page text as `research/semrush-transcript-[slug]-[date].txt` and the decision input as `research/semrush-keyword-input-[slug]-[date].json`.
- The command runs `python -m data_sources.modules.production.keyword_record --decision "research/semrush-keyword-input-[slug]-[date].json" --transcript "research/semrush-transcript-[slug]-[date].txt" --output "[layout keyword_decision path]" --shortlist-output "[layout keyword_shortlist path]"`. It refuses any candidate metric that the transcript does not show next to its keyword. Never type Semrush numbers.
- If the selected primary keyword changes the search intent of the working target query, rerun the SERP and coverage lane for the primary keyword.
- A Semrush UI timeout or reset is `blocked_semrush_ui_refresh`: stop before the BOM build. Do not substitute Semrush API, MCP, stale exports, or estimates.

### 4. Research brief and BOM spec
- Save the research brief to `research/brief-[slug]-[date].md`: searcher task, intent, Reader Contract, the commercial pillar and cannibalization decision, the competitor and gap notes, the planned early artifact, and the meta title and description drafts.
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
