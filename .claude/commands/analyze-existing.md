# Analyze Existing Command

Use this command to review an existing blog post for SEO opportunities, content gaps, AEO/GEO readiness, and rewrite or optimization routing.

## Usage
`/analyze-existing [URL or file path]`

## Ownership
`/analyze-existing` owns the analysis report and rewrite routing. It does not draft, rewrite, patch, move, or publish public blog Markdown.

The original rewrite route remains `/analyze-existing [URL or file path]` followed by `/rewrite [topic]` for substantial work or `/optimize [file]` for light polish. `/rewrite` and `/optimize` own public Markdown edits. Python owns governance artifacts only: context packs and receipts, selector evidence, the recorded Semrush keyword decision, SERP evidence and the page-1 coverage map, the PAA artifact, the production BOM, the release record, and publishing transport.

Use `context/blog-editorial-strategy.md` for editorial planning, reader value, originality, structure, and narrative throughlines. Use `context/aeo-geo-blog-strategy.md` for AEO, proof, vault, citation, schema, BOM, score-gate, and recovery-loop policy.

When routing to `/rewrite`, `/analyze-existing` produces the rewrite findings that the `/research` BOM process turns into the rewrite's production BOM spec and production BOM. The findings record evidence-bound preserve, update, add, and remove decisions for sections, facts, links, proof, and FAQs, plus the search, commercial-pillar, anchor, cannibalization, and lifecycle observations the research brief needs. They are inputs, not a frozen plan: only facts, proof, PAA questions, and links the BOM build admits reach the rewrite. A BOM defect found later returns to the BOM build step in `/rewrite`.

## What This Command Does
1. Reads the existing URL or local article file and captures current structure.
2. Evaluates content health, SEO quality, and AEO/GEO rewrite readiness.
3. Identifies outdated claims, unsupported proof, structural gaps, and intent mismatches.
4. Records rewrite findings for the `/research` BOM process, including an optional Hindsight-informed private reader angle when applicable.
5. Recommends `/rewrite`, `/optimize`, or archive with evidence-bound reasoning.

## Process

### 1. Inputs and Context
- Resolve source URL or file path, post slug, topic, title, objective, audience, region, current target keyword, and intended reader task.
- Classify Context Binding from the brand metadata and content before making product, competitor, proof, or workflow decisions. Run the vault connector workflow only for Simpro-owned or cross-brand-triggered work.
- Save context request/pack/receipt only for connector-bound work. For qualifying AroFlo, BigChange, and ClockShark work, save the nonconnector decision and omit vault-dependent Fred and customer-proof artifacts.
- Use repo-local context files only for allowed SEO/AEO, editorial, CRO, link-map, or source-governance inputs. If vault evidence is unavailable for Simpro brand or proof work, record the blocker and stop that brand/proof use.

### 2. Content Analysis
- Extract article text, headings, metadata, links, schema notes, media references, and publication/update dates.
- Check current relevance, completeness, reader payoff, actionability, and whether the conclusion fits the reader task.
- Flag stale, unsupported, risky, duplicated, thin, or off-intent sections.

### 3. SEO Audit
- Classify search intent and compare it to the existing article format.
- Review target keyword use in the H1, H2s, introduction, meta title, meta description, and body copy.
- Report keyword coverage, semantic gaps, and stuffing risk without forcing density targets unless a target was supplied.
- When rewrite or optimization is recommended, require the live Semrush keyword decision from the `/research` single Semrush lane (`python -m data_sources.modules.production.keyword_record`) when the rewrite BOM is built; do not treat existing repo keyword tables as current evidence.
- Review internal links, external evidence links, headings, readability, and metadata.
- Include SEO quality release floor 90/100+ with zero critical SEO issues and optimization target 95/100 as the later publish-readiness target.

### 4. AEO/GEO and Proof Readiness
- Audit direct-answer intro, early artifact, key takeaways, Capsule Method coverage, FAQ/PAA structure, schema notes, source-backed claims, and one-idea-per-section structure.
- Identify every existing claim, number, quote, customer story, and source link, and decide whether it survives: an existing citation survives only as a BOM fact whose quote the builder verifies on the live page, and existing customer proof survives only as a selected, approved BOM proof item. Note the facts and proof the rewrite needs, the E-E-A-T strength, and branch-applicable proof needs. Vault brand language, named feature and add-on checks, connector customer proof, and Fred Voccola authority apply only when Context Binding requires the connector. For commercial-investigation rewrites, `no_fit_customer_proof` is anti-invention only; plan a positive signal or record a private `proof_unavailable_safe_to_publish` note in the findings.
- When Hindsight internal-strategy evidence is relevant to the rewrite angle, use the connector internal-strategy lane to shape only the private reader angle, section emphasis, planned contribution purposes, objections, and commercial framing. Record `Hindsight Strategy Selection` in the findings for the research brief with `public_claim_use: prohibited` and `claim_support_allowed: false`, and keep Hindsight out of public proof, claims, citations, metrics, quotes, rankings, and source links. Hindsight never becomes a BOM fact, proof item, PAA question, or link. If it is not relevant, record `Status: not_applicable` or omit the block.
- Treat content quality 85/100+, SEO quality release floor 90/100+ and optimization target 95/100, and AEO/GEO 90/100+ as rewrite or optimization acceptance targets.
- FAQ questions come only from the PAA capture recorded for the rewrite's production run (AnswerSocrates, or the Google SERP fallback): there is no pre-picked brief precedence and no CSV fallback. Flag existing FAQ questions for removal, or for conversion into body sections, when the capture does not contain them.
- Do not invent replacement PAA questions, customer proof, author names, reviewer names, search-volume data, ranking data, traffic forecasts, or external claims.

### 5. Competitive Context
- Review an intent-representative SERP set if current rankings or target keywords are part of the analysis.
- Use competitor pages for format, coverage, and gap analysis only.
- Document whether a rewrite should match the dominant observed format or justify a Reader Contract exception.

## Output
Provide an analysis report with:

### 1. Content Health Score
- Content quality, SEO quality, AEO/GEO readiness, freshness, readability, intent alignment, and user experience findings.
- Clear separation between verified findings, unresolved blockers, and recommendations.

### 2. Quick Wins
- Top 3-5 fixes suitable for `/optimize`, such as metadata, headings, internal links, readability, stale references, or missing evidence links.

### 3. Strategic Improvements
- Larger changes suitable for `/rewrite`, including intent realignment, proof rebuilding, new sections, FAQ replacement from the run's PAA capture, source-fact work, or major structure changes.

### 4. Detailed Analysis Reports
- Search intent, keyword coverage, observed competitor context, readability, source support, proof gaps, and AEO/GEO readiness.

### 5. Rewrite Recommendations
- Priority level, estimated effort, route decision, the research inputs the rewrite BOM needs, and acceptance checklist.
- Expected impact stated as evidence-bound reader value or search alignment direction, not unsupported ranking or traffic forecasts.

### 6. Rewrite Findings for the BOM
If a rewrite is recommended, list the inputs `/rewrite` carries into the `/research` BOM process: preserve, update, add, and remove decisions per section; candidate facts with their public source pages; existing links to keep; proof needs; FAQ questions to re-check against the run's PAA capture; the current and candidate target keywords for the Semrush lane; competitor observations; the commercial pillar candidate; and the Simpro angle.

## File Management
Save the report to `research/analysis-[post-slug]-[YYYY-MM-DD].md`.

The rewrite findings live in the analysis report. Do not put governance blocks in public blog copy.

## Next Steps
Based on the report, route to:
1. `/rewrite [topic]` for substantial content changes.
2. `/optimize [file]` for light SEO/AEO polish.
3. Archive when the post no longer has a defensible role.
