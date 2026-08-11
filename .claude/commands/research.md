# Research Command

Use this command to conduct comprehensive SEO keyword research and competitive analysis before writing new content.

## Usage
`/research [topic]`

## What This Command Does
1. Performs keyword research for your industry-related topics
2. Analyzes top-ranking competitor content
3. Identifies content gaps and opportunities
4. Develops unique angle for your company perspective
5. Creates detailed research brief for writing

## Process

### Obsidian Vault Source Rule

For every blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decision, use the Simpro vault connector as the active context source. The only configured content location is the vault root; do not prescribe vault hubs, filenames, or internal directories.

Required connector workflow: run vault health first, describe available roles/topics/entities, search in the task's natural language, read and expand results by `resource_id`, query approved claims only when public proof-sensitive language is needed, then build and validate a context pack.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault connector exposes them as source evidence.

The repo-local context files are downstream mirrors or operational state only. They cannot override the vault connector when the vault is available. If fallback is used because the vault is unavailable, document the explicit vault-unavailable blocker in the validation sidecar.

Required validation sidecar evidence: generated vault context binding for every workflow; `Vault Brand Language Alignment` when product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` for competitor-aware posts; `Named Feature/Add-On Link Check` when named Simpro features/add-ons appear. These sections must cite connector `context_pack_hash`, `receipt_hash`, `resource_id`, `claim_id`, use mode, public URL when required, and relevant revisions. Missing required evidence blocks `/publish-readiness`, `/optimize`, and dev-ready handoff.

### Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: competitor-aware posts must document selected competitors, rejected competitors, connector-discovered competitive-context resources, approved claim IDs where public proof is used, and why the shortlist fits the article objective.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified through the claim registry. Keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked through connector-discovered product and feature resources before link decisions. Document the selected `resource_id` values, link decision, and reason in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from connector-discovered vault guidance first. Use semantic search/read/expand for messaging, positioning, feature, solution, and vertical context. When a named feature/add-on appears, include feature-specific `resource_id` evidence; when solution/industry language is used, include solution or vertical `resource_id` evidence. Document connector evidence, language applied, fallback context use, source-verification boundary, and `Status: aligned` in `Vault Brand Language Alignment`. The `vault_brand_language_guard.py` publish gate runs inside `/publish-readiness`; keep this block in the validation sidecar, not public copy. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

### Keyword Research
- **Primary Keyword**: Identify main target keyword for the topic
- **Search Volume & Difficulty**: Research estimated monthly searches and competition level
- **Keyword Variations**: Find semantic variations and long-tail opportunities
- **Related Questions**: Discover what people are actually asking (People Also Ask, forums, Reddit)
- **Search Intent**: Determine if intent is informational, navigational, commercial, or transactional
- **Topic Cluster**: Identify how this topic fits into your company content clusters

### Competitive Analysis
- **Top 10 SERP Review**: Analyze the top 10 ranking articles for target keyword
- **Content Length**: Note competitor word counts as context only; do not derive the article target from them
- **Common Themes**: What topics/sections do all top articles cover?
- **Content Gaps**: What's missing from competitor coverage?
- **Unique Angles**: What perspectives or insights are underexplored?
- **Featured Snippets**: Identify if there's a featured snippet opportunity
- **Domain Authority**: Note which competitors rank (indie blogs vs. major publications)

### Context Integration
- **Vault first**: Complete the generated vault context binding before drafting the brief, then use repo-local context only as fallback/mirror guidance.
- **Must-read fallback context before drafting the brief**:
  - @context/brand-voice.md for Simpro voice, FY26 positioning, audience maturity archetypes, and best-fit targeting boundaries only as a fallback mirror when the vault is unavailable
  - @context/features.md for Simpro capabilities, add-ons, AI positioning, implementation, integrations, security, proof candidates, and fit boundaries only as a fallback mirror when the vault connector is unavailable
  - @context/style-guide.md for terminology, product-name rules, tone, regional language, and forbidden phrasing only as a fallback mirror when the vault is unavailable
  - @context/internal-links-map.md for sitemap-backed internal links
  - @context/target-keywords.md for sitemap-derived topic clusters, first-party GSC/GA4 performance signals, and remaining metric boundaries
  - @context/competitor-analysis.md for competitive differentiation and objections
  - @context/cro-best-practices.md for proof-source workflow and CTA/trust-signal guidance
  - @context/aeo-geo-blog-strategy.md for AEO/GEO variable resolution, Capsule Method, PAA/FAQ selection, source mapping, and quality gates
- **Lightning overlay**: If the topic mentions Simpro Lightning, AroFlo Lightning, BigChange Lightning, Simpro Group Lightning, JustAsk, Cooper, FieldReady, JobReady, JobScribe, JobBrief, Price Lock, AI tax, TrueTime, DirectLine, Coming Specialists, or any named roadmap specialist, search the vault connector in the task's natural language, read and expand the selected Lightning `resource_id` values, and apply that guidance as a scoped overlay. Use @context/lightning-positioning.md only as a fallback mirror when the connector is unavailable and the sidecar records the blocker.
- **Simpro advantage**: Identify relevant Simpro product features, best-fit use cases, and customer proof through connector semantic search and current `resource_id` reads. Query approved claims before planning any public proof-sensitive language.
- **Customer proof routing**: After the customer-proof selector identifies candidates, query connector-approved claims for the intended public use mode and read the supporting `resource_id` values. Bind each public metric, quote, or proof theme to its `claim_id` and public URL. Use @context/internal-links-map.md and @context/features.md only as downstream fallback mirrors when the connector is unavailable; never treat either file as public proof.
- **Proof-index health**: Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates or selector slates.
- **Customer proof selection governance**: Before selecting or drafting proof, resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and write the generated selector-first `Customer Proof Slate` to the validation sidecar. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the sidecar and do not invent proof. experience_story consideration is required and E-E-A-T story usage is optional. If no story fits, use `Selected: [none]` with section-specific rejection reasons. Edit selected/rejected rows only when editorial judgment requires it. Treat any `recent_uses_90d` value above 0 as a proof-diversity warning. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. If a recently used or overused proof source is still selected, the sidecar needs a selector-backed, source-specific `Reuse reason` proving no stronger underused approved proof fits. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **Fred Voccola authority evaluation**: Resolve `topic`, `title`, and `objective`, then automatically run `python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5` and write the complete `Fred Voccola Authority Selection` block from `context/aeo-geo-blog-strategy.md` to the validation sidecar. Evaluation is mandatory and public use is optional. The selector defaults to `Selected: none`; make any selection explicitly only after reviewing the source and confirming direct topical fit. If the selector, connector, context pack, or receipt validation fails, record `Evaluation status: blocked` and the blocker; do not invent Fred evidence or continue to Fred public use.
- **Proof-index intake**: Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.
- **Customer proof diversity gate**: Plan for `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json` before scoring or `/optimize`. The brief and sidecar must include non-case-study proof search evidence when case studies are selected.
- **Review proof routing**: For review-site experience evidence, use Playwright MCP for live collection, run the selector with `--require-eeat-story --proof-role experience_story` when Review Story Selection is needed, and let `/publish-readiness` run the review story identity gate before scoring. Keep detailed Review Site Theme Selection, Capterra, exact-quote, rating, and metric boundaries in `context/aeo-geo-blog-strategy.md`.
- **Optional proof-backed customer/review POV**: Use a proof-backed customer/review POV only when it improves the article objective. If no actual person or business POV fits, omit the story. Fictional named personas are prohibited; unnamed workflow scenarios are explanatory only and do not count as E-E-A-T.
- **Brand alignment**: Apply Simpro's authoritative, ambitious, trades-focused, practical, outcomes-driven voice.
- **Evidence boundaries**: Do not present search volume, ranking, conversion priority, or live SERP findings as verified unless checked with GSC, GA4, DataForSEO, Ahrefs/Semrush, or live SERP review in this run.
- **Lightning evidence boundary**: Do not use time-sensitive Lightning pricing, roadmap, or competitor claims publicly unless they are verified in the current run or explicitly sourced from approved current material.

### Simpro Industry Focus
- **Trade operator angle**: Explain how this topic affects residential and commercial trade service businesses, especially low voltage, HVAC, plumbing, electrical/data, mechanical, and multi-trade operators.
- **Best-fit boundaries**: Use the Product Marketing Best-Fit Targeting Framework. Simpro is strongest for residential, light commercial, and medium commercial work involving small jobs, recurring contracts, inspections, maintenance, repairs, installations, and mid-sized projects. Be cautious with mostly residential North America, heavy commercial, industrial, general contractors, and complex-project-dominant businesses.
- **Customer maturity**: When useful, map pain points through connector semantic search and audience `resource_id` reads; use Empower, Elevate, and Excel archetypes from @context/brand-voice.md only as fallback mirror context when the connector is unavailable.
- **Product specificity**: Discover relevant Simpro capabilities through connector product, feature, solution, and vertical searches, then read and expand the selected `resource_id` values before drafting. Use @context/features.md only as a fallback mirror when the connector is unavailable; public product status, security, pricing, implementation, metric, and proof language requires approved claims where applicable.
- **Pain points**: Anchor recommendations in margin visibility, cash flow, admin reduction, field adoption, recurring maintenance, asset compliance, quoting speed, inventory, and scaling without chaos.

### Content Planning
- **Reader-Guided Structure Context**: Outline H2 and H3 headings from the Reader Contract, verified research, and reader-payoff gaps
- **Content Depth**: Determine an intent/evidence-complete word target from search intent, SERP context, and proof depth
- **Supporting Evidence**: Identify statistics, studies, or data to include
- **Expert Sources**: Find industry experts or quotes to reference
- **Visual Opportunities**: Suggest images, screenshots, or graphics needed
- **Internal Links**: Map intent-appropriate company pages to link to, based on the article objective, reader journey, and connector-backed product or solution context
- **External Authority**: Identify 2-3 authoritative external sources to link
- **AEO/GEO Variables**: Resolve `topic`, `audience`, `main_question`, `related_questions`, `tone`, `expertise`, and `length` where possible from connector context binding, repo context fallback, and research evidence
- **Source Mapping**: For each credible external source, document the claim it supports, the natural anchor phrase, and the target section
- **Metric Proof Pack**: For software, comparison, guide, pricing, cost, ROI, KPI, profit, margin, or vs topics, extract usable numbers before writing. Record `Search log`, each `Approved metric`, public proof URL or local proof artifact, source-visible Evidence, Status: approved, and intended Use. Plan for `/publish-readiness` before writing or scoring.
- **Validation sidecar**: Store proof-only blocks in `research/validation-[topic-slug]-[YYYY-MM-DD].md`, not in the public draft. The sidecar can contain `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, and structured data notes. Do not add an `Editorial Validation Appendix` to blog copy. Preferred publish check: `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json`.
- **FAQ Source Policy**: For each visible non-owned FAQ URL, add an exact `FAQ Proof Map` row with `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`. Allowed classes: `neutral`, `non_competing_expert`. Competitor-owned FAQ sources: prohibited.
- **FAQ evidence selection**: Use regulators, standards bodies, universities, trade associations, independent research/editorial, or non-competing experts. Simpro-owned links may be additive reader resources only.
- **Vendor questions**: Reframe or remove an FAQ if compliant evidence is unavailable; preserve vendor evidence for the comparison or vendor-specific body section.
- **PAA/FAQ Inputs**: If AnswerSocrates or a PAA/FAQ CSV has been used, identify the 3-5 closest questions, intent labels, and suggested article placement

### Hook Development
- **Introduction Angle**: Compelling way to open the article
- **Value Proposition**: Clear benefit reader will get from article
- **Contrarian Elements**: Any unexpected perspectives to explore
- **Story Opportunities**: Real examples or case studies to feature

## Output
Provides a comprehensive research brief with:

### 1. SEO Foundation
- **Primary Keyword**: [keyword] (volume, difficulty)
- **Secondary Keywords**: 3-5 related keywords and variations
- **Target Word Count**: Caller-supplied intent/evidence-complete target derived from the Reader Contract
- **Featured Snippet Opportunity**: Yes/No, format (paragraph, list, table)
- **AEO/GEO Variables**: topic, audience, main_question, related_questions, tone, expertise, length
- **PAA/FAQ Questions**: 3-5 closest questions with intent labels and article section mapping
- **Source Map**: source, supported claim, anchor text, target section
- **Metric Proof Pack**:
  - **Metric requirement**: required / not applicable
  - **Search log**: [public sources and local proof artifacts checked for usable numbers]
  - **Approved metric**: [metric claim, public proof URL or local proof artifact, source-visible Evidence, Status: approved, intended Use]
  - **Rejected metrics**: [candidate metric and missing proof reason]
- **Customer Proof Pack**:
  - **Pack status**: ready / partial / blocked
  - **Topic or page fit**: [topic, audience, region, trade, funnel stage]
  - **Customer Proof Slate**: [selector command plus metric, quote, theme, and experience_story role rows; story usage optional]
  - **Quote Matrix candidates**: [customer, trade, region, theme, exact quote or summary, source row/link, approval status]
  - **Case-study proof paths**: [customer, public URL, supported metric/theme]
  - **Review-site experience evidence**: [platform, URL, date checked, product/competitor, experience pattern, evidence summary, exact quote/rating approval status]
  - **Customer Proof Selection Decision**: [selector command, selected proof IDs, rejected stronger candidates, final use in copy]
  - **Reuse reason**: [source-specific; required when customer-proof-usage-ledger.json marks the selected proof as recently used or overused; must prove no stronger underused approved proof fits the same role]
  - **Approved quotes**: [exact quote/testimonial, customer/brand/reviewer, source type, public proof URL, Evidence, approval status]
  - **Approved metrics**: [metric, customer, source file, public proof URL]
  - **Use in copy**: [exact quote / paraphrased theme / named metric / omit]
  - **Claims excluded**: [claim and missing proof reason]

### 2. Competitive Landscape
- **Top 3 Competitor Articles**: URLs and key takeaways from each
- **Common Sections**: Must-cover topics based on SERP analysis
- **Content Gaps**: Opportunities to provide unique value
- **Differentiation Strategy**: How your company can stand out

### 3. Recommended Outline
```
H1: [Optimized headline with primary keyword]

Introduction
- Hook
- Problem statement
- Value proposition

H2: [Main section 1]
H3: [Subsection]
H3: [Subsection]

H2: [Main section 2]
...

Conclusion
- Key takeaways
- Call to action
```

### 4. Supporting Elements
- **Statistics to Include**: 5-7 relevant data points with sources
- **Expert Quotes**: Potential sources or existing quotes
- **Examples/Case Studies**: Real Simpro customer outcomes or relevant trade-service scenarios to feature
- **Visual Suggestions**: Screenshots, charts, or graphics needed

### 5. Internal Linking Strategy
- **Pillar Page**: Main your company pillar content to link to
- **Related Articles**: 2-4 relevant blog posts to link
- **Product Pages**: your company features to naturally mention
- **Resource Pages**: Tools or guides to reference

### 6. Meta Elements Preview
- **Meta Title**: Draft optimized title (50-60 characters)
- **Meta Description**: Draft compelling description (150-160 characters)
- **URL Slug**: Recommended URL structure

## File Management
After completing the research, automatically save the brief to:
- **File Location**: `research/brief-[topic-slug]-[YYYY-MM-DD].md`
- **File Format**: Markdown with clear sections and structured data
- **Naming Convention**: Use lowercase, hyphenated topic slug and current date

Example: `research/brief-podcast-editing-software-2025-10-15.md`

## Next Steps
The research brief serves as the foundation for:
1. Running `/write [topic]` to create the optimized article
2. Reference material for maintaining SEO focus throughout writing
3. Checklist to ensure all competitive gaps are addressed

This ensures every article is built on solid SEO research and strategic competitive positioning.
