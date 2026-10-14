# Write Command

Use `/write [topic or article path]` to draft a new blog from its production BOM.

## Ownership

The command/agent writes the public Markdown. Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

Python may write governance artifacts only: selector evidence, context packs and receipts, the recorded Semrush keyword decision, SERP and PAA artifacts, the production BOM, the release record, and publisher transport payloads.

Consume `context/blog-editorial-strategy.md` for editorial execution and the canonical AEO and proof source, `context/aeo-geo-blog-strategy.md`. Author metadata controls public identity, Person schema, and whether first-person author voice is allowed; it provides zero Expertise and zero Experience credit without selected, source-visible evidence that satisfies the corresponding proof boundary. Expertise proof requires source-visible expert evidence alongside product/workflow support.

Consume the production BOM `research/production-bom-[slug]-[YYYY-MM-DD].json` that `/research` built. Do not edit the BOM or its spec. The BOM lists the sections, facts, approved proof, PAA questions, links, CTA, and schema notes; `/write` independently chooses the public language. A missing BOM, or a BOM defect such as a missing fact or section, returns to `/research`, which fixes the spec and rebuilds.

## Required workflow

1. Resolve the article path `drafts/[slug]-[YYYY-MM-DD].md` and read its production BOM. If the BOM does not exist, run `/research` first.
2. Read the identity, keyword, sections, facts, proof, PAA questions, links, CTA, and schema notes from the BOM. Proof comes only from the BOM: for a connector-bound article it was selected from vault claims; for a nonconnector AroFlo, BigChange, or ClockShark article under the separate approved non-vault proof-eligibility contract it was selected by `nonvault_customer_proof_selector.py`. For a connector-bound article, take vault voice, tone, and product language from the context pack the BOM binds (`research/context-pack-[slug].json`), never from repo-local context files.
3. If the research brief records Hindsight-informed strategy with `public_claim_use: prohibited`, use it only to understand the planned reader angle, section emphasis, section purposes, objections, and commercial framing. Do not quote, cite, disclose, paraphrase, metricize, or convert Hindsight or deal-intelligence data into public claims. If the Hindsight-informed angle is missing or wrong, route the plan defect back to `/research`.
4. Run the Reader-Facing Copy Firewall before drafting. Convert brief instructions, source-fit notes, claim-selection logic, feature-omission rationale, command results, schema notes, and readiness status into article-ready guidance or frontmatter. Public body copy must read only as a blog for the ICP and must not explain how or why the article was assembled, including phrases such as "this article uses," "the brief asks," "right editorial lane," or "does not name a specific feature." Any `editorial_process_leakage` finding is a public-copy blocker owned by `/write`.
5. Draft with one writer, so the article keeps one voice. Claude writes the Markdown section by section in BOM order using the command, not a Python writer, and not parallel subagents:
   - cover every `must` section and as many `should` sections as serve the reader;
   - state a fact only as its BOM claim allows, and link its BOM URL in the same paragraph; never add a number, statistic, quote, or source that is not in the BOM;
   - use customer and review proof only from BOM proof items, each by its `kind`: quote a `quote` item verbatim inside quotation marks; use a `metric` item's numbers exactly as its approved text states them; paraphrase `theme` and `experience_story` items without quotation marks; and link the item's proof URL in the same paragraph;
   - ask FAQ questions only from the BOM PAA questions, using their exact wording;
   - place the commercial pillar link with its exact planned anchor, and put the primary keyword in the title, H1, and first 100 words;
   - follow the drafting rules in `context/aeo-geo-blog-strategy.md`: direct answer first, capsules, Key Takeaways, early usable artifact, FAQ answer shape, and `schema_notes` frontmatter.
6. Freeze the article bytes and dispatch the advisory reviewers as parallel subagents against that exact snapshot and the BOM path:
   - **Editor** (`editor`): voice, clarity, rhythm, and reviewed Humanizer patterns;
   - **SEO** (`seo-optimizer`, using the `meta-creator`, `internal-linker`, and `keyword-mapper` checklists): title and meta, headings, keyword placement, and links;
   - **AEO** (`content-analyzer`): direct answers, capsules, FAQ answer shape, and extractability;
   - **Fact-check**: a general-purpose subagent that checks every factual sentence, number, and quote against the BOM facts and proof, and flags anything the BOM does not support.
   Reviewers return advisory findings only. They never edit the article or the BOM.
7. The writer applies the findings in one consolidated edit batch. A finding that needs a new fact, source, or proof item routes to `/research` to add it to the spec and rebuild the BOM; the writer never adds it directly.
8. Run `/scrub [article]` for diagnostics only. Make any needed edits through `/write` and rerun `/scrub`.
9. Run `/publish-readiness [article]`, which runs `python -m data_sources.modules.production.release [article]`. On exit `1`, revise from the record's blocking findings, rerun `/scrub` if the bytes changed, and run the release again. On exit `1` with `bom_refused` findings, or exit `2` whose message names a `.refused` BOM from an earlier refused build, the BOM is the problem: go back to `/research`, which fixes the spec or the research inputs and rebuilds. On any other exit `2`, fix the operational cause named in the message and run it again.
10. Run `/optimize [article]` for every new blog after the first release record. It works from the record's blocking findings and `priority_fixes`; when the release passed and no source-safe fix exists, it makes no edits and the passing record stands.
11. Do not hand off as ready until the latest release record passed for the current article bytes and reports separate Content, SEO, and AEO/GEO scores. The command runs `python -m data_sources.modules.production.record verify <article>`; it must exit 0. After 2 unsuccessful repair loops, leave the article in place and report the latest record's blocking findings.

## Score requirements

`/publish-readiness` is the release owner and reports these independent gates from the release record:

- Content quality: 85/100 or higher.
- SEO quality: 90/100 release floor with zero critical SEO issues; 95/100 honest optimization target when source-safe improvements exist.
- AEO/GEO: 90/100 or higher.

Do not treat an overall score as a substitute for the SEO or AEO/GEO gates. If scoring does not run because the release stopped first, report `scores: unavailable` with the exact stop reason. Missing scores are a workflow blocker unless the release stopped before scoring.

## Link policy

Standard blog posts use 3 to 5 internal links and never more than 7 below 3,000 visible words. The commercial pillar link counts toward that total. URL fragments and `mailto:` or `tel:` links do not count. Two distinct authoritative non-owned external sources pass; do not add a third source only to meet a quota, while claim-fit evidence exceptions remain uncapped.

Every proof-sensitive claim falls under one citation mode: `inline_required`, `section_source_allowed`, `sidecar_only`, or `proof_not_required`. `inline_required` covers legal, regulatory, licensing, compliance, safety, fees, deadlines, pricing, status, material numeric, causal, comparative, benchmark, quote, customer, review, Fred, and fact-driven FAQ claims; link the BOM fact or proof URL naturally in the same paragraph or row and in the FAQ's first visible paragraph. A claim that cites a source outside the BOM blocks the release.

Reviewers must protect required links and flag duplicate support, repeated destinations, and quota-only sources. They return advisory findings only; `/publish-readiness` is the sole verdict and no human approval step applies.

## Output

Return the draft path, BOM path, release record path, the three scores, blocking findings, and priority fixes. Keep proof infrastructure out of public copy.

For detailed proof, E-E-A-T, and AEO/GEO policy, use `context/aeo-geo-blog-strategy.md`.
