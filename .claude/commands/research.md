# Research Command

Use this command to conduct SEO keyword research, competitor review, and evidence planning before writing new blog content.

## Usage
`/research [topic]`

## Ownership
`/research` owns the research brief and validation sidecar planning. It does not draft, rewrite, patch, move, or publish public blog Markdown.

The original new-blog route remains `/research [topic]` followed by `/write [topic]`. `/write` owns the public draft. Python owns governance artifacts only: context packs and receipts, selector evidence, verified SERP/PAA artifacts, BOM assembly, scrub/readiness diagnostics, receipts, and publishing transport.

Use `context/aeo-geo-blog-strategy.md` and repo instructions as the canonical governance source for vault context, Customer Proof Pack, Fred Voccola Authority Selection, feature/competitor guardrails, FAQ/PAA policy, source maps, BOM, score gates, and recovery loops.

## What This Command Does
1. Resolves topic, title, objective, audience, region, target keyword, and article intent.
2. Builds the connector-backed research context when required, or an explicit nonconnector decision for qualifying AroFlo, BigChange, and ClockShark work.
3. Performs keyword, SERP, competitor, PAA/FAQ, proof, source, and internal-link research.
4. Identifies reader-payoff gaps, Simpro angle, proof needs, and article structure.
5. Saves a research brief for `/write`.

## Process

### 1. Inputs and Context
- Resolve the working topic slug, target reader, search intent, main question, and article objective.
- Classify Context Binding from the brand metadata and content. Run the vault connector workflow only for Simpro-owned or cross-brand-triggered work.
- Save context request, context pack, and context receipt under `research/` only when connector-bound. Save an explicit nonconnector binding reason for qualifying AroFlo, BigChange, and ClockShark work.
- Use repo-local context files only as downstream mirrors or fallback context when the vault is unavailable, and record that blocker in the validation sidecar.

### 2. Keyword Research
- Identify the primary keyword, supporting keywords, semantic variants, and long-tail opportunities.
- Record search volume, difficulty, ranking, or live SERP data only when verified in the current run.
- Classify search intent as informational, commercial, transactional, navigational, or mixed.
- Map the topic to the most relevant Simpro content cluster and funnel stage.

### 3. SERP and Competitive Analysis
- Review an intent-representative SERP set until the dominant format, recurring structure, and meaningful gaps are clear.
- Use public competitor pages for format and gap analysis only.
- Document selected/rejected competitors through the canonical `Competitive Shortlist Decision` policy when competitor-aware public copy is planned.
- Treat competitor word count as context, not as the article target.

### 4. Brand Context and Proof Planning
- For connector-bound work, identify relevant Simpro product, solution, industry, feature, add-on, and internal-link context through connector-backed research. For nonconnector work, use task-approved brand sources and current public evidence.
- Plan only the validation sidecar evidence applicable to the binding branch. Omit Vault Brand Language Alignment, Named Feature/Add-On Link Check, Customer Proof Pack selector evidence, and Fred Voccola Authority Selection from nonconnector workflows.
- Do not select, quote, paraphrase, or metricize customer proof unless the required governance evidence exists.

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
