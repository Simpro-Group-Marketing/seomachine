# Rewrite Command

Use `/rewrite [existing article or analysis]` to revise an existing blog from a production BOM while preserving proof boundaries and source traceability.

## Ownership

The command/agent rewrites public Markdown. Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

Python may write governance artifacts only: selector evidence, context packs and receipts, the recorded Semrush keyword decision, SERP and PAA artifacts, the production BOM, the release record, and publisher transport payloads.

Consume `context/blog-editorial-strategy.md` for editorial execution and the canonical AEO and proof source, `context/aeo-geo-blog-strategy.md`. Author metadata controls public identity, Person schema, and whether first-person author voice is allowed; it provides zero Expertise and zero Experience credit without selected, source-visible evidence that satisfies the corresponding proof boundary. Expertise proof requires source-visible expert evidence alongside product/workflow support.

Consume the `/analyze-existing` findings and the production BOM for the rewrite path. Do not edit the BOM or its spec while rewriting. The BOM defines the sections, facts, approved proof, PAA questions, and links; `/rewrite` independently chooses the final prose. A BOM defect returns to the BOM build step below.

## Required workflow

1. Read the existing article and the `/analyze-existing` findings.
2. Resolve topic, title, objective, audience, target keyword, target URL, and the rewrite path `rewrites/[slug]-[YYYY-MM-DD].md`, dated today.
3. Build the production BOM for the rewrite path with the `/research` process: run the layout command, the parallel research lanes, the single Semrush lane, the BOM spec, and `bom_build`, all against `rewrites/[slug]-[YYYY-MM-DD].md`. Use the analysis to decide which sections, facts, links, and proof to preserve, update, add, or remove. Keep original image placeholders, useful sections, internal links, and proof only when the BOM still carries them: an existing citation survives only as a BOM fact whose quote the builder verified on the live page, and existing customer proof survives only as a selected, approved BOM proof item.
4. Proof comes only from the BOM. For a connector-bound article it was selected from vault claims. For a nonconnector AroFlo, BigChange, or ClockShark article under the separate approved non-vault proof-eligibility contract it was selected by `nonvault_customer_proof_selector.py`; keep out exact quotes, metrics, ratings, and named-person attribution beyond an approved Capterra `review_site` row's `approved_quotes` on the brand's listed product page.
5. FAQ questions come only from the run's PAA capture (AnswerSocrates, or the Google SERP fallback when AnswerSocrates is blocked): the BOM admits questions only from it, so there is no pre-picked brief precedence and no CSV fallback. Remove existing FAQ questions that the capture does not contain, or turn their useful content into body sections. Do not invent questions.
6. If the research brief records Hindsight-informed strategy with `public_claim_use: prohibited`, use it only to understand the planned reader angle, section emphasis, section purposes, objections, and commercial framing. Do not quote, cite, disclose, paraphrase, metricize, or convert Hindsight or deal-intelligence data into public claims. If the Hindsight-informed angle is missing or wrong, route the plan defect back to the BOM build step.
7. Run the Reader-Facing Copy Firewall before rewriting. Convert brief instructions, source-fit notes, claim-selection logic, feature-omission rationale, command results, schema notes, and readiness status into article-ready guidance or frontmatter. Public body copy must read only as a blog for the ICP and must not explain how or why the article was assembled, including phrases such as "this article uses," "the brief asks," "right editorial lane," or "does not name a specific feature." Any `editorial_process_leakage` finding is a public-copy blocker owned by `/rewrite`.
8. Rewrite with one writer, so the article keeps one voice. Claude writes the Markdown section by section in BOM order through `/rewrite`, following the same BOM rules as `/write`: every `must` section, facts only as their BOM claims allow with the BOM URL linked in the same paragraph, customer and review proof by `kind` (quote a `quote` item verbatim inside quotation marks, use a `metric` item's numbers exactly, paraphrase `theme` and `experience_story` items without quotation marks, and link the proof URL in the same paragraph), FAQ questions only from the BOM, the commercial pillar link with its exact planned anchor, and the primary keyword in the title, H1, and first 100 words.
9. Freeze the article bytes and dispatch the advisory reviewers as parallel subagents against that exact snapshot and the BOM path: **Editor** (`editor`), **SEO** (`seo-optimizer`, using the `meta-creator`, `internal-linker`, and `keyword-mapper` checklists), **AEO** (`content-analyzer`), and **Fact-check** (a general-purpose subagent that checks every factual sentence, number, and quote against the BOM facts and proof). Reviewers return advisory findings only and must preserve existing required links unless the BOM replaces them.
10. The writer applies the findings in one consolidated edit batch. A finding that needs a new fact, source, or proof item goes back to the BOM build step; the writer never adds it directly.
11. Run `/scrub [article]` as read-only diagnostics. Apply any required edits through `/rewrite` and rerun `/scrub`.
12. Run `/publish-readiness [article]`, which runs `python -m data_sources.modules.production.release [article]`. On exit `1`, revise from the record's blocking findings, rerun `/scrub` if the bytes changed, and run the release again. On exit `1` with `bom_refused` findings, or exit `2` whose message names a `.refused` BOM from an earlier refused build, the BOM is the problem: go back to the BOM build step (step 3), which fixes the spec or the research inputs and rebuilds. On any other exit `2`, fix the operational cause named in the message and run it again.
13. Run `/optimize [article]` for every rewrite after the first release record. When the release passed and no source-safe fix exists, it makes no edits and the passing record stands.
14. Stop unless the latest release record passed for the current article bytes and reports separate Content, SEO, and AEO/GEO scores. The command runs `python -m data_sources.modules.production.record verify <article>`; it must exit 0. After 2 unsuccessful repair loops, leave the article in place and report the latest record's blocking findings.

## Score requirements

`/publish-readiness` reports separate gates from the release record:

- Content quality: 85/100 or higher.
- SEO quality: 90/100 release floor with zero critical SEO issues; 95/100 honest optimization target when source-safe improvements exist.
- AEO/GEO: 90/100 or higher.

If scoring does not run because the release stopped first, report `scores: unavailable` with the exact stop reason. Missing scores are a workflow blocker unless the release stopped before scoring.

## Link policy

Standard blog rewrites use 3 to 5 internal links and never more than 7 below 3,000 visible words. Existing useful links can remain when the BOM carries them, and the commercial pillar link counts toward that total. URL fragments and `mailto:` or `tel:` links do not count. Two distinct authoritative non-owned external sources pass; do not add a third source only to meet a quota, while claim-fit evidence exceptions remain uncapped.

Every proof-sensitive claim falls under one citation mode: `inline_required`, `section_source_allowed`, `sidecar_only`, or `proof_not_required`. `inline_required` covers legal, regulatory, licensing, compliance, safety, fees, deadlines, pricing, status, material numeric, causal, comparative, benchmark, quote, customer, review, Fred, and fact-driven FAQ claims; link the BOM fact or proof URL naturally in the same paragraph or row and in the FAQ's first visible paragraph. A claim that cites a source outside the BOM blocks the release.

Reviewers return advisory findings only; `/publish-readiness` is the sole verdict and no human approval step applies.

For detailed proof, E-E-A-T, FAQ, PAA, review story, named feature, schema, and vault language rules, use `context/aeo-geo-blog-strategy.md`.
