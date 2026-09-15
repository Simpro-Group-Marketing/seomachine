# Research Command

Use this command to conduct SEO keyword research, competitor review, and evidence planning before writing new blog content.

## Usage
`/research [topic]`

## Ownership
`/research` owns the research brief and validation sidecar planning. It does not draft, rewrite, patch, move, or publish public blog Markdown.

The original new-blog route remains `/research [topic]` followed by `/write [topic]`. `/write` owns the public draft. Python owns governance artifacts only: context packs and receipts, selector evidence, verified Semrush keyword decisions, verified SERP/PAA artifacts, BOM assembly, scrub/readiness diagnostics, receipts, and publishing transport.

Use `context/blog-editorial-strategy.md` for editorial planning, reader value, originality, structure, and narrative throughlines. Use `context/aeo-geo-blog-strategy.md` for AEO, proof, vault, citation, schema, BOM, score-gate, and recovery-loop policy.

`/research` creates and freezes the complete `simpro-blog-editorial-plan/v2` for a new article. The plan owns metadata plus structured search, commercial-pillar, anchor, cannibalization, and lifecycle decisions. It defines what the article must accomplish without prescribing final sentences. A plan-level reviewer finding returns here and produces a new plan hash.

## What This Command Does
1. Resolves topic, title, objective, audience, region, target keyword, and article intent.
2. Builds the connector-backed research context when required, or an explicit nonconnector decision for qualifying AroFlo, BigChange, and ClockShark work.
3. Performs keyword, SERP, competitor, PAA/FAQ, proof, source, and internal-link research.
4. Identifies reader-payoff gaps, Simpro angle, proof needs, optional Hindsight-informed private reader angle, and article structure.
5. Saves a research brief and frozen editorial-plan v2 for `/write`.

## Process

### 1. Inputs and Context
- Resolve the working topic slug, target reader, search intent, main question, and article objective.
- Classify Context Binding from the brand metadata and content. Run the vault connector workflow only for Simpro-owned or cross-brand-triggered work.
- Save context request, context pack, and context receipt under `research/` only when connector-bound. Save an explicit nonconnector binding reason for qualifying AroFlo, BigChange, and ClockShark work.
- Use repo-local context files only as downstream mirrors or fallback context when the vault is unavailable, and record that blocker in the validation sidecar.

### 2. Semrush Keyword Decision
- Use live Semrush connector evidence for current optimization decisions; do not use repo keyword tables as current evidence.
- Run `_keyword_research`, `_get_report_schema`, `phrase_these`, `phrase_related`, `phrase_questions`, `phrase_organic`, and `phrase_this` when exact final-primary confirmation is needed.
- Use the default database from the canonical strategy unless the brief gives a stronger market requirement.
- Choose by intent fit first, then page ownership/cannibalization risk, then volume, difficulty, CPC, trend, SERP shape, and competitor feasibility.
- Save `research/semrush-keyword-decision-[topic-slug]-[YYYY-MM-DD].json` using `simpro-semrush-keyword-decision/v1`.
- Record the selected primary keyword, secondary keywords, rejected keywords with reasons, connector report parameters, collection date, and the source boundary that Semrush is third-party opportunity/SERP context while GSC remains first-party performance truth.

### 3. SERP and Competitive Analysis
- Review an intent-representative SERP set until the dominant format, recurring structure, and meaningful gaps are clear.
- Use public competitor pages for format and gap analysis only.
- Document selected/rejected competitors through the canonical `Competitive Shortlist Decision` policy when competitor-aware public copy is planned.
- Treat competitor word count as context, not as the article target.

### 4. Brand Context and Proof Planning
- For connector-bound work, identify relevant Simpro product, solution, industry, feature, add-on, and internal-link context through connector-backed research. For nonconnector work, use task-approved brand sources and current public evidence.
- When Hindsight internal-strategy evidence is relevant to the topic, use the connector internal-strategy lane to shape only the private reader angle, section emphasis, planned contribution purposes, objections, and commercial framing. Record `Hindsight Strategy Selection` in the validation sidecar with `public_claim_use: prohibited` and `claim_support_allowed: false`, bind `hindsight_strategy_evidence`, and keep Hindsight out of public proof, claims, citations, metrics, quotes, rankings, and source links. If it is not relevant, record `Status: not_applicable` or omit the block.
- Plan only the validation sidecar evidence applicable to the binding branch. Omit Vault Brand Language Alignment, Named Feature/Add-On Link Check, Customer Proof Pack selector evidence, and Fred Voccola Authority Selection from nonconnector workflows.
- Do not select, quote, paraphrase, or metricize customer proof unless the required governance evidence exists.
- For commercial-investigation topics, plan E-E-A-T strength early: use a positive signal when available, or the internal `proof_unavailable_safe_to_publish` sidecar decision when no approved signal fits.

### 5. AEO/GEO Planning
- Resolve AEO/GEO variables: topic, audience, main question, related questions, tone, expertise, and target length.
- Collect or document PAA/FAQ provenance according to the canonical strategy.
- Plan the early artifact, direct-answer intro, key takeaways, Capsule Method coverage, FAQ shape, schema notes, and evidence-backed source map.
- Treat content quality 85/100+, SEO quality release floor 90/100+ and optimization target 95/100, and AEO/GEO 90/100+ as handoff targets for the later writing/readiness workflow.

## Output
Provide a research brief with:

### 1. SEO Foundation
- Primary keyword, verified metrics if available, and search intent.
- Secondary keywords and semantic variants.
- Semrush keyword decision artifact path, selected/rejected keyword rationale, and database used.
- Target word count derived from intent, reader task, and evidence depth.
- Featured snippet and SERP feature opportunities.
- AEO/GEO variable summary and PAA/FAQ plan.

### 2. Competitive Landscape
- Competitor evidence set with URLs, observed format, common sections, and gaps.
- Differentiation strategy for Simpro.
- Required competitor-proof or shortlist notes for the validation sidecar.

### 3. Recommended Outline
```markdown
H1: [optimized headline with primary keyword]

Introduction
- Hook
- Problem statement
- Value proposition

H2: [main section]
H3: [supporting point]

Conclusion
- Key takeaways
- Reader next step
```

### 4. Supporting Elements
- Source Map needs and candidate authoritative sources.
- Metric Proof Pack needs and verified/rejected metric candidates.
- Customer Proof Pack needs and selected/rejected proof paths.
- Fred Voccola Authority Selection result or blocker.
- Visual, screenshot, video, table, checklist, calculator, or template opportunities.

### 5. Internal Linking Strategy
- Pillar page, related posts, product/solution pages, and resource links that advance the reader task.
- Named feature/add-on link decisions that need sidecar evidence.

### 6. Meta Elements Preview
- Meta title draft.
- Meta description draft.
- URL slug recommendation.

## File Management
Save the brief to `research/brief-[topic-slug]-[YYYY-MM-DD].md`.

Save proof-only planning in `research/validation-[topic-slug]-[YYYY-MM-DD].md`; do not put governance blocks in public blog copy.

## Next Steps
1. Run `/write [topic]` to create the public draft from the research brief.
2. Run `/scrub` and `/publish-readiness` after the public draft, sidecar, context artifacts, BOM, and receipts exist.
3. If scores miss thresholds, follow the recovery loop in `context/aeo-geo-blog-strategy.md`.
