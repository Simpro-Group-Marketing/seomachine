# Analyze Existing Command

Use this command to review an existing blog post for SEO opportunities, content gaps, AEO/GEO readiness, and rewrite or optimization routing.

## Usage
`/analyze-existing [URL or file path]`

## Ownership
`/analyze-existing` owns the analysis report and rewrite routing. It does not draft, rewrite, patch, move, or publish public blog Markdown.

The original rewrite route remains `/analyze-existing [URL or file path]` followed by `/rewrite [topic]` for substantial work or `/optimize [file]` for light polish. `/rewrite` and `/optimize` own public Markdown edits. Python owns governance artifacts only: scoring, guards, Semrush keyword decision JSON, receipts, BOM assembly, scrub/readiness diagnostics, and publishing transport.

Use `context/aeo-geo-blog-strategy.md` and repo instructions as the canonical governance source for vault context, Customer Proof Pack, Fred Voccola Authority Selection, feature/competitor guardrails, FAQ/PAA policy, source maps, BOM, score gates, and recovery loops.

## What This Command Does
1. Reads the existing URL or local article file and captures current structure.
2. Evaluates content health, SEO quality, and AEO/GEO rewrite readiness.
3. Identifies outdated claims, unsupported proof, structural gaps, and intent mismatches.
4. Creates a validation sidecar plan for proof, context, source, FAQ, and BOM requirements.
5. Recommends `/rewrite`, `/optimize`, or archive with evidence-bound reasoning.

## Process

### 1. Inputs and Context
- Resolve source URL or file path, post slug, topic, title, objective, audience, region, current target keyword, and intended reader task.
- Classify Context Binding from the brand metadata and content before making product, competitor, proof, or workflow decisions. Run the vault connector workflow only for Simpro-owned or cross-brand-triggered work.
- Save context request/pack/receipt only for connector-bound work. For qualifying AroFlo, BigChange, and ClockShark work, save the nonconnector decision and omit vault-dependent Fred and customer-proof artifacts.
- Use repo-local context files only as downstream mirrors or fallback context when the vault is unavailable, and record that blocker in the validation sidecar.

### 2. Content Analysis
- Extract article text, headings, metadata, links, schema notes, media references, and publication/update dates.
- Check current relevance, completeness, reader payoff, actionability, and whether the conclusion fits the reader task.
- Flag stale, unsupported, risky, duplicated, thin, or off-intent sections.

### 3. SEO Audit
- Classify search intent and compare it to the existing article format.
- Review target keyword use in the H1, H2s, introduction, meta title, meta description, and body copy.
- Report keyword coverage, semantic gaps, and stuffing risk without forcing density targets unless a target was supplied.
- When rewrite or optimization is recommended, run or require the live Semrush keyword decision workflow and save `research/semrush-keyword-decision-[topic-slug]-[YYYY-MM-DD].json`; do not treat existing repo keyword tables as current evidence.
- Review internal links, external evidence links, headings, readability, and metadata.
- Include SEO quality release floor 90/100+ with zero critical SEO issues and optimization target 95/100 as the later publish-readiness target.

### 4. AEO/GEO and Proof Readiness
- Audit direct-answer intro, early artifact, key takeaways, Capsule Method coverage, FAQ/PAA structure, schema notes, source-backed claims, and one-idea-per-section structure.
- Identify missing Source Map, Metric Proof Pack, FAQ Proof Map, E-E-A-T strength decision, and branch-applicable proof evidence. Require Customer Proof Pack, Vault Brand Language Alignment, Named Feature/Add-On Link Check, and Fred Voccola Authority Selection only when Context Binding requires the connector. For commercial-investigation rewrites, `no_fit_customer_proof` is anti-invention only; plan a positive signal or the internal `proof_unavailable_safe_to_publish` sidecar decision.
- Treat content quality 85/100+, SEO quality release floor 90/100+ and optimization target 95/100, and AEO/GEO 90/100+ as rewrite or optimization acceptance targets.
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
- Larger changes suitable for `/rewrite`, including intent realignment, proof rebuilding, new sections, FAQ/PAA replacement, source-map work, or major structure changes.

### 4. Detailed Analysis Reports
- Search intent, keyword coverage, observed competitor context, readability, source support, proof gaps, and AEO/GEO readiness.

### 5. Rewrite Recommendations
- Priority level, estimated effort, route decision, required evidence artifacts, and acceptance checklist.
- Expected impact stated as evidence-bound reader value or search alignment direction, not unsupported ranking or traffic forecasts.

### 6. Research Brief
If a rewrite is recommended, include the Semrush keyword decision artifact path, selected/rejected keyword rationale, competitor observations, source needs, internal links, PAA/FAQ provenance needs, proof requirements, Simpro angle, and required artifacts before `/rewrite`.

## File Management
Save the report to `research/analysis-[post-slug]-[YYYY-MM-DD].md`.

Save proof-only planning in `research/validation-[topic-slug]-[YYYY-MM-DD].md`; do not put governance blocks in public blog copy.

## Next Steps
Based on the report, route to:
1. `/rewrite [topic]` for substantial content changes.
2. `/optimize [file]` for light SEO/AEO polish.
3. Archive when the post no longer has a defensible role.
