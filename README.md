# SEO Machine (Simpro Group)

Simpro Marketing's Claude Code workspace for **SEO and AEO/GEO blog posts** — research, write, optimize, and publish long-form articles for field-service and trades audiences, with Simpro-specific brand context, first-party analytics, and generative-engine optimization built in.

Fork of [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine), maintained by Simpro Group Marketing for [simprogroup.com](https://www.simprogroup.com).

## Obsidian Vault Source Rule

For every blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decision, use the Simpro vault connector as the active context source. The only configured content location is the vault root; prompts, guards, selectors, and workflow docs must not prescribe vault hubs, filenames, or internal directories.

Required connector workflow: run vault health first, describe available roles/topics/entities, search in the task's natural language, read and expand results by `resource_id`, query approved claims only when public proof-sensitive language is needed, then build and validate a context pack.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault connector exposes them as source evidence.

The repo-local context files are downstream mirrors or operational state only. They cannot override the vault connector when the vault is available. If fallback is used because the vault is unavailable, document the explicit vault-unavailable blocker in the validation sidecar.

Required validation sidecar evidence: generated vault context binding for every workflow; `Vault Brand Language Alignment` when product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` for competitor-aware posts; `Named Feature/Add-On Link Check` when named Simpro features/add-ons appear. These sections must cite connector `context_pack_hash`, `receipt_hash`, `resource_id`, `claim_id`, use mode, public URL when required, and relevant revisions. Missing required evidence blocks `/publish-readiness`, `/optimize`, and dev-ready handoff.

## Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: competitor-aware posts must document selected competitors, rejected competitors, connector-discovered competitive-context resources, approved claim IDs where public proof is used, and why the shortlist fits the article objective.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified through the claim registry. Keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked through connector-discovered product and feature resources before link decisions. Document the selected `resource_id` values, link decision, and reason in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from connector-discovered vault guidance first. Use semantic search/read/expand for messaging, positioning, feature, solution, and vertical context. When a named feature/add-on appears, include feature-specific `resource_id` evidence; when solution/industry language is used, include solution or vertical `resource_id` evidence. Document connector evidence, language applied, fallback context use, source-verification boundary, and `Status: aligned` in `Vault Brand Language Alignment`. The `vault_brand_language_guard.py` publish gate runs inside `/publish-readiness`; keep this block in the validation sidecar, not public copy. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

## Fred Voccola Authority Selection

Every new or changed Simpro blog and every rewrite, analysis, optimization, or publish-readiness pass automatically runs:

```powershell
python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5 --output "research/fred-authority-selection-[topic-slug].md"
```

Write the complete `Fred Voccola Authority Selection` block to the validation sidecar. Evaluation is mandatory; public use is optional and requires direct topical support. The vault connector and claim registry are the sole eligibility source, and selection fails closed unless current connector revisions, resource hashes, and claim decisions validate. Fred observations support Expertise and Authority by default and count as Experience only when a source explicitly supports first-hand personal or operating experience. They supplement, never replace, customer Experience proof, customer stories, or independent evidence.

Exact article quotes require `source_visible_article_text`; exact video/audio quotes require `transcript_and_playback`, a timestamp, and playback verification; paraphrases require `paraphrase_evidence`. Exact quotes and paraphrased observations need a contextual public link in the same paragraph. A playlist-only row supports discovery or an eligible embed, not independent earned-media authority. Embed only a selected public YouTube source through a responsive 16:9 `youtube-nocookie.com` handoff with a visible fallback link, descriptive title, lazy loading, no autoplay, and verified metadata. Include `VideoObject` if and only if embedded. No usage ledger or frequency penalty applies in v1. Existing content is evaluated when next rewritten, optimized, or passed through publish readiness. Full policy and the exact sidecar fields live in `context/aeo-geo-blog-strategy.md`.


## Authors

See [AUTHORS.md](AUTHORS.md) for the current Simpro Group Marketing repo authors and maintainers.

## Overview

SEO Machine is built on Claude Code and provides:
- **Custom Commands**: `/research`, `/write`, `/rewrite`, `/article`, `/analyze-existing`, `/optimize`, `/performance-review`, `/publish-draft`, `/priorities`, `/research-ai-citations`, plus SERP, gap, trending, cluster, and landing-page commands
- **Specialized Agents**: Content analyzer, SEO optimization, meta element creation, internal linking, keyword mapping, editor, performance analysis, headline generator, CRO analyst, landing page optimizer
- **Marketing Skills**: 26+ marketing skills for copywriting, CRO, A/B testing, email sequences, pricing strategy, and more
- **AEO/GEO Workflow**: Capsule Method structure, PAA/FAQ integration, source mapping, E-E-A-T Proof Map checks, and `aeo_geo_rater` scoring (90+ target) via `context/aeo-geo-blog-strategy.md`
- **Source-Proof Guardrails**: Metric-sensitive articles require a Metric Proof Pack before writing or publish readiness, including a Search log and at least one Approved metric with public URL or local proof artifact, source-visible Evidence, Status: approved, and intended Use. Every metric, statistic, or numeric business claim must be supported by a public URL or local proof artifact through the body link, Source Map, or Customer Proof Pack. When visible FAQs exist, answers must lead with a concrete extractable answer and include at least 1 authoritative non-owned public evidence link in visible copy; a Source Map or FAQ Proof Map can document but cannot replace that link. PAA provenance follows the strict AnswerSocrates/brief policy below. The source support guard requires strict proof rows with source-visible Evidence. The 403 replacement rule requires blocked 401, 403, or `manual_review` public research/source URLs to be replaced with an equivalent resolved public source link in public copy or the supported claim removed; Source Map notes must document the rejected 403 URL and replacement URL. Exact quotes/testimonials must be approved in Customer Proof Pack Approved quotes, and any named customer metric must be approved in Customer Proof Pack Approved metrics. Review-derived public E-E-A-T stories require identity-backed `Review Story Selection`, a public review URL, and a same paragraph article link. experience_story consideration is required and E-E-A-T story usage is optional when customer proof appears; use a proof-backed customer/review POV only when it improves the article objective. Fictional named personas are prohibited. Capterra review themes may use `Review Site Theme Selection` with `Source row ref: Capterra tab row [n]`, `Public review-site URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`, and `Status: approved for paraphrased review-theme use`; public copy must link the Capterra review-site URL in the same paragraph and use no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **Advanced SEO Analysis**: Search intent detection, keyword distribution and clustering, content scope comparison, readability scoring, SEO quality rating (0-100)
- **Data Integrations**: GA4 and GSC via project MCP servers; DataForSEO, Ahrefs, and Semrush context in keyword/competitor files; PEEC AI citation tracking
- **Simpro Context Pack**: connector-discovered vault resources selected by semantic search and stable `resource_id`, with receipt-approved claims for proof-sensitive public language; repo-local files remain workflow policy or non-authoritative operational state
- **Workflow Organization**: Structured directories for topics, research, drafts, audits, and published content

## Blog Assembly BOM and Readiness Seal

Every new or changed blog requires a strict JSON `simpro-blog-assembly-bom/v1`. The vault remains the knowledge graph and discovery/proof source; the BOM is the article-specific execution record.

Complete inventory: final article, validation sidecar, context request/pack/receipt plus customer-proof selector and Fred authority evidence when connector-bound, `simpro-blog-editorial-plan/v1`, verified SERP evidence, PAA artifact or rewrite brief plus conditional CSV/blocker evidence, every `simpro-blog-stage-receipt/v1`, conditional optimizer evidence, provisional/final BOM, preflight result, and detached final-readiness attestation.

Tool-emitted machine artifacts carry an `execution_attestation`, a keyed local execution-integrity attestation. It is required on every `simpro-blog-stage-receipt/v1`, verified `simpro-serp-evidence/v1`, nested `simpro-answersocrates-run-receipt/v1`, `simpro-source-classification/v1`, and `simpro-source-capture-receipt/v1`. Readiness verifies the attestation and canonical hash; a handwritten or merely rehashed replacement does not qualify.

This local control binds the exact payload to the configured repository emitter. It does not provide a remote/provider signature and does not prove that external observations are true. Source metadata, visible evidence, freshness, eligible PAA questions, and semantic claim fit remain separate validation requirements. For rewrites, a dedicated pre-picked PAA brief section still takes precedence and remains bound by its exact path and hash; it is not recast as AnswerSocrates output.

Trust-key operations are part of the workflow. On a developer workstation, the emitter creates the ignored local key at `.cache/seomachine-execution-attestation.key`. Managed runners must configure the same secret for emission and validation through `SEOMACHINE_ARTIFACT_ATTESTATION_KEY`; use at least 32 UTF-8 bytes and keep it outside the repository. Losing or rotating either trust source invalidates existing attestations, so regenerate the affected machine artifacts before readiness.

Stage receipts come from the tools that do the work. After creating the article scaffold, start the mutation recorder before drafting, finish it after saving, then run the deterministic receipt-emitting stages:

```powershell
python data_sources/modules/blog_assembly_mutation_recorder.py start --article "[article]" --state "research/stage-receipts/[topic-slug]/draft-state.json" --run-id "[run-id]" --stage draft --tool-name "[draft-tool]" --tool-version "[version]" --input "editorial_plan=research/editorial-plan-[topic-slug]-[YYYY-MM-DD].json"
# Draft and save the article here.
python data_sources/modules/blog_assembly_mutation_recorder.py finish --article "[article]" --state "research/stage-receipts/[topic-slug]/draft-state.json" --receipt "research/stage-receipts/[topic-slug]/draft.json" --evidence "serp_evidence=research/serp-evidence-[topic-slug]-[YYYY-MM-DD].json"
python data_sources/modules/content_scrubber.py "[article]" --stage scrub --run-id "[run-id]" --previous-receipt "research/stage-receipts/[topic-slug]/draft.json" --stage-receipt-output "research/stage-receipts/[topic-slug]/scrub.json"
python data_sources/modules/context_binding_generator.py "[article]" --proof-sidecar "[sidecar]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --stage context_binding --run-id "[run-id]" --previous-receipt "research/stage-receipts/[topic-slug]/scrub.json" --stage-receipt-output "research/stage-receipts/[topic-slug]/context-binding.json"
```

For a blog that the shared applicability guard classifies as non-connector, use the real no-context receipt instead of the connector command:

```powershell
python data_sources/modules/context_binding_generator.py "[article]" --proof-sidecar "[sidecar]" --not-applicable-reason "Final article contains no Simpro brand, URL, or connector-sensitive language." --stage context_binding --run-id "[run-id]" --previous-receipt "research/stage-receipts/[topic-slug]/scrub.json" --stage-receipt-output "research/stage-receipts/[topic-slug]/context-binding.json"
```

In that branch, omit context request/pack/receipt, customer-proof selector, and Fred evidence arguments from the BOM build, and omit context request/pack/receipt arguments from both readiness runs. The builder derives connector applicability from the final article and rejects this branch when Simpro branding, an official Simpro URL (including a schemeless hostname), or connector-sensitive language is present.

Use this exact non-circular order. Add the applicable artifact arguments and repeat `--stage-receipt` for every closed stage:

```powershell
python data_sources/modules/blog_assembly_bom.py build "[article]" --validation-sidecar "[sidecar]" --editorial-plan "[editorial-plan]" --serp-evidence "[serp-evidence]" --paa-artifact "[paa-artifact]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --customer-proof-selector-evidence "[selector-evidence]" --fred-authority-evidence "[fred-evidence]" --stage-receipt "[closed-stage-receipt]" --workflow-mode "[new|rewrite]" --assembly-date "[YYYY-MM-DD]" --output "[provisional-bom]"
python data_sources/modules/publish_readiness.py "[article]" --proof-sidecar "[sidecar]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --assembly-bom "[provisional-bom]" --phase preflight --output "[preflight-readiness]"
python data_sources/modules/blog_assembly_bom.py finalize --bom "[provisional-bom]" --preflight-readiness "[preflight-readiness]" --output "[final-bom]"
python data_sources/modules/publish_readiness.py "[article]" --proof-sidecar "[sidecar]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --assembly-bom "[final-bom]" --phase final --output "[final-readiness-attestation]" --stage-receipt-output "[final-readiness-stage-receipt]"
```

Preflight must pass before finalization. Final readiness reruns every source-artifact gate and writes a detached final-readiness attestation tied to the final BOM and final input hashes. It is not hashed back into the BOM. Both results declare `verification_scope: source_artifact`; CMS payload and rendered-page verification are outside this scope.

When preflight writes `research/preflight-readiness-[topic-slug]-[YYYY-MM-DD].json`, it automatically emits `research/preflight-readiness-[topic-slug]-[YYYY-MM-DD]-stage-receipt.json`. Keep every preflight-bound provisional BOM immutable. Use `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json` for the initial provisional BOM and `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-final.json` for its finalized form. The closed post-optimization sequence is `optimization` -> `post_optimization_scrub` -> `post_optimization_context_binding` -> `final_preflight_readiness`; rebuild to the distinct provisional path `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization.json`, then finalize to `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization-final.json`. Include every receipt, optimizer evidence, and `--prior-preflight-readiness`. Do not overwrite the BOM referenced by the prior preflight. The guard rejects that collision because it would destroy the historical input seal.

PAA and FAQ policy:

- Every new article requires a receipt-bound `simpro-answersocrates-artifact/v1` JSON artifact emitted by `paa_provenance_guard.py record`, even when no FAQ is useful. Handwritten collection labels do not qualify.
- For a rewrite, PAA pre-picked in a dedicated brief section takes precedence. Bind the brief path/hash, do not rerun AnswerSocrates, and use those exact questions as visible FAQ headings.
- A rewrite without pre-picked brief PAA requires a structured AnswerSocrates artifact.
- A user CSV is allowed only when a saved AnswerSocrates artifact records a genuine blocked state: login, CAPTCHA, quota, or unavailability.
- SERP, Reddit, and YouTube are supplemental research and cannot satisfy PAA provenance.
- Record `FAQ policy: required | not_applicable`. `not_applicable` requires a non-empty rationale. FAQ answer/proof/schema/scoring checks run only when visible FAQs exist.

For rewrites only, the dedicated brief section must be:

```markdown
## Pre-picked PAA Questions
- [Exact complete question?]
```

## Getting Started

### Prerequisites
- [Claude Code](https://claude.com/claude-code) installed
- Anthropic API account
- Python 3.11 or newer
- Access to the internal `simpro-context-connector` v2.0.0 release

### Installation

1. Clone this repository:
```bash
git clone https://github.com/Simpro-Group-Marketing/seomachine.git
cd seomachine
```

2. Install Python dependencies for analysis modules:
```bash
pip install -r data_sources/requirements.txt
```

This installs:
- The standalone Simpro vault Python client, CLI, and MCP adapter
- Google Analytics/Search Console integrations
- DataForSEO API client
- NLP libraries (nltk, textstat)
- Machine learning (scikit-learn)
- Web scraping tools (beautifulsoup4)

3. Configure credentials and MCP (Simpro setup):

   - Copy `.env.example` to `.env` and set GA4/GSC/DataForSEO paths (see `CLAUDE.md` for MCP vs Python module credential boundaries)
   - Copy `.mcp.json.template` to `.mcp.json` and adjust paths for your machine
   - Set `SIMPRO_VAULT_ROOT` to the authorized vault root; the connector does not read Claude plugin inventory or internal vault routes
   - Copy `.claude/settings.local.template.json` to `.claude/settings.local.json`
   - Place GA4 ADC at `credentials/adc.json` and GSC OAuth client secret at `credentials/gsc_client_secrets.json` (see `credentials/.gitkeep` — secrets are gitignored)
   - For the bundled GSC MCP server: `cd mcp-gsc && pip install -r requirements.txt` (see `mcp-gsc/README.md`)

4. Open in Claude Code:
```bash
claude-code .
```

5. **Context Files** (pre-filled for Simpro):

   Most `context/` files are already populated from the Simpro Marketing Portal, Voice Style Guide, battlecards, GSC/GA4 US metrics, Semrush/Ahrefs benchmarks, PEEC AI citation exports, and public Reddit research. See `context/_coverage-report.md` for file-by-file status and remaining gaps.

   | File | Purpose |
   |------|---------|
   | `brand-voice.md` | FY26 messaging + Voice Style Guide tone |
   | `style-guide.md` | Editorial rules, terminology, Lightning naming |
   | `features.md` | Product/value props and add-ons |
   | `competitor-analysis.md` | 40+ battlecards + SERP/backlink overlays |
   | `target-keywords.md` | Topic clusters + GSC/GA4/Semrush metrics |
   | `internal-links-map.md` | Sitemap URLs + performance-prioritized linking |
   | `writing-examples.md` | Four simprogroup.com blog exemplars |
   | `seo-guidelines.md` | Simpro SEO structure requirements |
   | `aeo-geo-blog-strategy.md` | Capsule Method, PAA, schema, E-E-A-T |
   | `ai-citation-targets.md` | AI citation evidence register + PEEC insight |
   | `reddit-strategy.md` | Community targets and engagement rules |
   | `cro-best-practices.md` | CRO overlay + experiment/KPI source map |
   | `lightning-positioning.md` | Scoped overlay for Simpro Group Lightning only |

   **Upstream reference**: `examples/castos/` still shows the original Castos template pattern from the open-source repo.

## Workflows

### Creating New Content

#### 1. Start with Research
```
/research [topic]
```

**What it does**:
- Performs keyword research
- Samples competitor pages until search intent, recurring structure, and meaningful evidence gaps are clear
- Identifies content gaps
- Creates comprehensive research brief
- Saves to `/research/` directory

**Example**:
```
/research field service management software
```

#### 2. Write the Article
```
/write [topic or research brief]
```

**What it does**:
- Creates a complete SEO-optimized article sized to the Reader Contract, search intent, and available evidence
- Applies `context/aeo-geo-blog-strategy.md` (Capsule Method, PAA/FAQ, source mapping, schema notes)
- Maintains Simpro brand voice from the vault first; `context/brand-voice.md` and `lightning-positioning.md` are fallback mirrors when the vault is unavailable
- Integrates keywords from `context/target-keywords.md`
- Includes internal and external links per `context/internal-links-map.md`
- Places each link where it directly supports the sentence and reader task, without a per-paragraph quota
- Uses function-bearing anchor text for feature and solution links; a feature or solution name alone is not enough
- Provides meta elements (title, description, keywords)
- Automatically triggers optimization agents
- Saves to `/drafts/` directory

**Example**:
```
/write hvac scheduling software
```

**Agent Auto-Execution**:
After writing, these agents automatically analyze the content:
- **SEO Optimizer**: On-page SEO recommendations
- **Meta Creator**: Multiple meta title/description options
- **Internal Linker**: Specific internal linking suggestions
- **Keyword Mapper**: Keyword placement and density analysis

#### 3. Final Optimization
```
/optimize [article file]
```

**What it does**:
- Comprehensive SEO audit
- Validates all elements meet requirements
- Runs URL validation through `/publish-readiness`
- Runs the publish-readiness guard stack listed in the After Writing checklist
- Provides final polish recommendations
- Generates publishing readiness score
- Creates optimization report

**Example**:
```
/optimize drafts/hvac-scheduling-software-2026-05-22.md
```

### Updating Existing Content

#### 1. Analyze Existing Post
```
/analyze-existing [URL or file path]
```

**What it does**:
- Fetches and analyzes current content
- Evaluates SEO performance
- Audits AEO/GEO readiness for rewrite
- Identifies outdated information
- Assesses competitive positioning
- Provides content health score (0-100)
- Recommends update priority and scope
- Saves analysis to `/research/` directory

**Examples**:
```
/analyze-existing https://www.simprogroup.com/blog/what-is-field-service-management/
/analyze-existing published/what-is-field-service-management-2025-04-15.md
```

#### 2. Rewrite/Update Content
```
/rewrite [topic or analysis file]
```

**What it does**:
- Updates content based on analysis findings
- Refreshes statistics and examples
- Improves SEO optimization
- Applies `context/aeo-geo-blog-strategy.md` for sourced PAA/FAQ provenance, source mapping, E-E-A-T proof, direct-answer capsules, schema notes, and 85/90 quality gates
- Places each link where it directly supports the sentence and reader task, without a per-paragraph quota
- Uses function-bearing anchor text for feature and solution links; a feature or solution name alone is not enough
- Adds new sections to fill gaps
- Maintains what works from original
- Tracks changes made
- Saves to `/rewrites/` directory

**Example**:
```
/rewrite field service management software
```

## Commands Reference

### `/research [topic]`
Comprehensive keyword and competitive research for new content.

**Output**: Research brief in `/research/brief-[topic]-[date].md`

**Includes**:
- Primary and secondary keywords
- Intent- and evidence-dependent competitor analysis
- Content gaps and opportunities
- Recommended outline
- Internal linking strategy
- Meta elements preview

---

### `/write [topic]`
Create an SEO-optimized blog post with scope set by reader intent, evidence, and source depth.

**Output**: Article in `/drafts/[topic]-[date].md`

**Includes**:
- Complete article with H1/H2/H3 structure
- AEO/GEO structure from `context/aeo-geo-blog-strategy.md` (Capsule Method, PAA/FAQ, schema notes)
- SEO-optimized content aligned with Simpro voice and `internal-links-map.md`
- Internal and external links with source mapping
- Meta elements (title, description, keywords)
- SEO + AEO/GEO checklists (90+ target on `aeo_geo_rater` when scored)

**Auto-Triggers**:
- SEO Optimizer agent
- Meta Creator agent
- Internal Linker agent
- Keyword Mapper agent

---

### `/rewrite [topic]`
Update and improve existing content.

**Output**: Updated article in `/rewrites/[topic]-rewrite-[date].md`

**Includes**:
- Rewritten/updated content
- Change summary
- Before/after comparison
- Updated SEO elements
- AEO/GEO rewrite inputs: PAA/FAQ provenance, selected questions, source map, E-E-A-T proof, schema notes, and quality-gate notes

---

### `/analyze-existing [URL or file]`
Analyze existing blog posts for improvement opportunities.

**Output**: Analysis report in `/research/analysis-[topic]-[date].md`

**Includes**:
- Content health score (0-100)
- Quick wins (immediate improvements)
- Strategic improvements
- Rewrite priority and scope
- Research brief for rewrite
- AEO/GEO readiness audit with missing strategy inputs and required PAA/source/proof artifacts

---

### `/optimize [file]`
Final SEO optimization pass before publishing.

**Output**: Optimization report in `/drafts/optimization-report-[topic]-[date].md`

**Includes**:
- SEO score (0-100)
- Priority fixes
- Quick wins
- Meta element options
- Link enhancement suggestions
- Publishing readiness assessment

---

### `/publish-draft [file]`
Publish article to WordPress via REST API with Yoast SEO metadata.

---

### `/article [topic]`
Full blog workflow with AnswerSocrates PAA collection via Playwright MCP, then research and draft steps.

---

### `/research-ai-citations [topic]`
AI citation audit: prompt clusters, cited sources, Simpro visibility gaps, and updates to `context/ai-citation-targets.md`.

---

### `/priorities`
Content prioritization matrix using analytics data to identify highest-impact content tasks.

---

### `/scrub [file]`
Remove invisible Unicode marks, em dashes, and whitespace artifacts. Run the AI copy linter after scrub for AI-writing detection.

---

### Research Commands

| Command | Description |
|---------|-------------|
| `/research-serp [keyword]` | SERP analysis for a target keyword |
| `/research-gaps` | Competitor content gap analysis |
| `/research-trending` | Trending topic opportunities |
| `/research-performance` | Performance-based content priorities |
| `/research-topics` | Topic cluster research |
| `/research-ai-citations` | AI engine citation audit for a topic cluster |

---

### Landing Page Commands

| Command | Description |
|---------|-------------|
| `/landing-write [topic]` | Create conversion-optimized landing page |
| `/landing-audit [file]` | Audit landing page for CRO issues |
| `/landing-research [topic]` | Research competitors and positioning |
| `/landing-competitor [URL]` | Deep competitor landing page analysis |
| `/landing-publish [file]` | Publish landing page to WordPress |

## Agents

Specialized agents that automatically analyze content and provide expert recommendations.

### Content Analyzer (NEW!)
**Purpose**: Comprehensive, data-driven content analysis using 5 specialized modules

**Analyzes**:
- Search intent classification (informational/navigational/transactional/commercial)
- Keyword distribution, terminology coverage, and clustering with topic detection
- Content scope comparison vs top SERP competitors
- Readability scoring (Flesch Reading Ease, Flesch-Kincaid Grade Level)
- SEO quality rating (0-100 score with category breakdowns)
- Keyword stuffing risk detection
- Passive voice ratio and sentence complexity
- Distribution heatmap showing keyword placement by section

**Output**:
- Executive summary with publishing readiness assessment
- Priority action plan (critical/high priority/optimization)
- Competitive positioning analysis
- Detailed recommendations for each analysis area
- Observed metrics and context-bound benchmarks for improvements

**Powered by**:
- `search_intent_analyzer.py` - Search intent detection
- `keyword_analyzer.py` - Keyword distribution, stuffing-risk checks, clustering, and semantic terminology coverage
- `content_length_comparator.py` - SERP competitor analysis
- `readability_scorer.py` - Multiple readability metrics
- `seo_quality_rater.py` - Comprehensive SEO scoring

---

### SEO Optimizer
**Purpose**: On-page SEO analysis and optimization recommendations

**Analyzes**:
- Keyword optimization and density
- Content structure and headings
- Internal and external links
- Meta elements
- Readability and user experience
- Featured snippet opportunities

**Output**: SEO score (0-100) with specific improvement recommendations

---

### Meta Creator
**Purpose**: Generate high-converting meta titles and descriptions

**Creates**:
- 5 meta title variations (50-60 chars)
- 5 meta description variations (150-160 chars)
- Testing recommendations
- SERP preview
- Conversion-optimized copy

**Output**: Multiple options with recommendation and reasoning

---

### Internal Linker
**Purpose**: Strategic internal linking recommendations

**Provides**:
- Intent-appropriate internal link suggestions, including the required down-funnel path
- Exact placement locations
- Anchor text recommendations
- User journey mapping
- SEO impact prediction

**References**: `context/internal-links-map.md`

---

### Keyword Mapper
**Purpose**: Keyword placement and integration analysis

**Analyzes**:
- Keyword distribution and stuffing-risk checks
- Critical placement checklist
- Natural language integration quality
- Semantic terminology coverage
- Cannibalization risk

**Output**: Distribution map, gap analysis, specific revision suggestions

---

### Editor
**Purpose**: Transform technically accurate content into human-sounding, engaging articles

**Analyzes**:
- Voice and personality
- Specificity of examples
- Readability and flow
- Robotic vs. human patterns
- Engagement and storytelling

**Provides**:
- Humanity score (0-100)
- Critical edits with before/after
- Pattern analysis
- Specific rewrites to inject personality
- Readability improvements

**Output**: Editorial report with specific improvements to make content sound human

---

### Performance
**Purpose**: Data-driven content prioritization using real analytics

**Analyzes**:
- Google Analytics traffic and trends
- Google Search Console rankings and CTR
- DataForSEO competitive data
- Quick wins (position 11-20)
- Declining content
- Low CTR opportunities
- Trending topics

**Provides**:
- Priority queue of content tasks
- Opportunity scores (0-100)
- Impact and effort estimates
- Week-by-week roadmap
- Success metrics

**Output**: Comprehensive performance report with actionable priorities

---

### Headline Generator
**Purpose**: Generate high-converting headline variations and A/B testing recommendations

**Provides**:
- 10+ headline variations using proven formulas
- Conversion potential scoring
- A/B testing strategies
- Audience-specific headline options

---

### CRO Analyst
**Purpose**: Conversion rate optimization analysis for landing pages

**Analyzes**:
- Above-the-fold effectiveness
- CTA quality and distribution
- Trust signal presence
- Friction points
- Page structure

---

### Landing Page Optimizer
**Purpose**: Comprehensive landing page optimization recommendations

**Provides**:
- CRO scoring (0-100) with category breakdowns
- Above-fold, CTA, trust signal, structure, and SEO analysis
- A/B testing recommendations
- Priority action list

## Marketing Skills

SEO Machine includes 26 marketing skills accessible as slash commands:

| Category | Skills |
|----------|--------|
| **Copywriting** | `/copywriting`, `/copy-editing` |
| **CRO** | `/page-cro`, `/form-cro`, `/signup-flow-cro`, `/onboarding-cro`, `/popup-cro`, `/paywall-upgrade-cro` |
| **Strategy** | `/content-strategy`, `/pricing-strategy`, `/launch-strategy`, `/marketing-ideas` |
| **Channels** | `/email-sequence`, `/social-content`, `/paid-ads` |
| **SEO** | `/seo-audit`, `/schema-markup`, `/programmatic-seo`, `/competitor-alternatives` |
| **Analytics** | `/analytics-tracking`, `/ab-test-setup` |
| **Other** | `/referral-program`, `/free-tool-strategy`, `/marketing-psychology` |

## Data Sources

### MCP Servers (Simpro setup — recommended for commands)

Project-scoped MCP servers feed live data into research and performance workflows:

| Server | Purpose | Credentials |
|--------|---------|-------------|
| `gsc` | Search Console queries, pages, performance overview | `credentials/gsc_client_secrets.json` + OAuth token (`mcp-gsc/`) |
| `analytics-mcp` | GA4 reports and account summaries | `credentials/adc.json` via `GOOGLE_APPLICATION_CREDENTIALS` |

Copy `.mcp.json.template` to `.mcp.json` and `.claude/settings.local.template.json` to `.claude/settings.local.json`. See `CLAUDE.md` and `mcp-gsc/README.md`.

### Python module integrations

Legacy and batch scripts use `data_sources/modules/`:

**Google Analytics 4** (Python module + MCP):
- US property `309907809` referenced in `target-keywords.md` and `internal-links-map.md`
- Landing-page sessions and key events for internal-link priority

**Google Search Console** (Python module + MCP):
- `sc-domain:simprogroup.com` US query and page metrics in context files
- Quick-win and performance commands

**DataForSEO**:
- SERP and keyword scripts in `scripts/`
- Dashboard competitor layer documented in `competitor-analysis.md`

**Semrush / Ahrefs / PEEC** (context-enriched, not all wired as Python modules):
- Semrush MCP and Ahrefs Free metrics embedded in `target-keywords.md` and `competitor-analysis.md`
- PEEC AI citation exports in `ai-citation-targets.md`

### Advanced SEO Analysis Modules (NEW!)

SEO Machine includes 5 specialized Python modules for comprehensive content analysis:

**Search Intent Analyzer** (`search_intent_analyzer.py`):
- Classifies queries into informational, navigational, transactional, or commercial intent
- Analyzes SERP features and content patterns
- Provides confidence scores and content alignment recommendations

**Keyword Analyzer** (`keyword_analyzer.py`):
- Reports exact keyword density for context and analyzes distribution
- Detects keyword stuffing risk with warnings
- Performs topic clustering using TF-IDF and K-means
- Generates distribution heatmap by section
- Identifies semantically related terms

**SEO Quality Rater** (`seo_quality_rater.py`):
- Rates content against SEO best practices (0-100 score)
- Category breakdowns: content, keywords, meta, structure, links, readability
- Identifies critical issues, warnings, and suggestions
- Determines publishing readiness

**Content Length Comparator** (`content_length_comparator.py`):
- Samples enough relevant SERP competitors to establish intent and content-scope context
- Reports median, 75th percentile, and range as context without setting the article target
- Shows observed positioning and the difference from an optional caller-supplied target
- Leaves the target unresolved when Reader Contract planning has not supplied one; expansion still requires a reader-payoff, evidence, or task gap

**Readability Scorer** (`readability_scorer.py`):
- Flesch Reading Ease and Flesch-Kincaid Grade Level
- Sentence and paragraph structure analysis
- Passive voice detection and ratio calculation
- Complex word identification
- Transition word usage analysis
- Overall readability score (0-100)

All modules can be used directly in Python or through the Content Analyzer agent.

### CRO Analysis Modules

Six Python modules for landing page conversion optimization:

- `above_fold_analyzer.py` - Above-the-fold content analysis (headline, value prop, CTA, trust)
- `cta_analyzer.py` - CTA effectiveness scoring (quality, distribution, goal alignment)
- `trust_signal_analyzer.py` - Trust signal detection (testimonials, social proof, risk reversals)
- `landing_page_scorer.py` - Overall landing page scoring (0-100 with category breakdowns)
- `landing_performance.py` - Landing page performance tracking via GA4/GSC
- `cro_checker.py` - CRO best practices checklist validation

### Additional Analysis Modules

- `opportunity_scorer.py` - 8-factor opportunity scoring for content prioritization
- `content_scorer.py` - 5-dimension content quality scoring (humanity, specificity, structure, SEO, readability) with AEO/GEO gate
- `aeo_geo_rater.py` - Capsule Method, PAA, source mapping, and E-E-A-T scoring (90+ publish target)
- `url_validator.py` - URL validation guardrail for Markdown links and bare URLs; runs inside `/publish-readiness`
- `public_research_link_guard.py` - Public research link guardrail for the 403 replacement rule; blocks sidecar-only research/compliance/legal/regulatory/statistical proof and requires visible resolved non-owned public research links in public copy
- `metric_proof_pack_guard.py` - Metric Proof Pack guardrail; use the After Writing command stack before scoring or `/optimize`
- `numeric_claim_source_guard.py` - Metric/stat proof guardrail; use the After Writing command stack before scoring or `/optimize`
- `faq_answer_quality_guard.py` - Blocking answer-first FAQ guardrail; use the After Writing command stack before scoring or `/optimize`
- `faq_proof_guard.py` - Requires an authoritative non-owned public evidence link inside every FAQ answer; sidecar-only proof does not pass
- `paa_provenance_guard.py` - PAA provenance guardrail; use the After Writing command stack before scoring or `/optimize`
- `source_support_guard.py` - Strict source support guard; use the After Writing command stack before scoring or `/optimize`
- `customer_proof_selector.py` - Customer proof selector; slash workflows automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10` before selecting proof and record the generated selector-first `Customer Proof Slate`
- `customer_proof_index_health.py` - Read-only proof inventory health report; run it before proof-index intake when checking source mix, approvals, overuse, and public-copy gaps
- `customer_proof_index_intake.py` - Customer proof intake validator/merger; add new candidates through `context/customer-proof-intake-template.csv` and validate before relying on them in selector slates
- `customer_proof_diversity_guard.py` - Customer proof diversity guard; use the After Writing command stack and `context/aeo-geo-blog-strategy.md` for full reuse policy
- `review_story_identity_guard.py` - Review story identity guard; use the After Writing command stack and `context/aeo-geo-blog-strategy.md` for full review story/theme policy
- `content_scrubber.py` - Removes invisible Unicode marks, em dashes, and whitespace artifacts before publish
- `ai_copy_linter.py` - Deterministic AI copy detection gate with line-level findings
- `engagement_analyzer.py` - Content engagement pattern analysis
- `competitor_gap_analyzer.py` - Competitive content gap identification
- `article_planner.py` - Data-driven article planning
- `section_writer.py` - Section-level content guidance
- `social_research_aggregator.py` - Social media research aggregation

### Research Command Entry Points

Use slash commands for research workflows. Scripts and MCP calls are implementation details the command runner should execute internally.

```text
# Content research
/research-performance
/research-performance [blog URL or path]
/research-gaps
/research-serp
/research-topics
/research-trending

# Follow-up analysis
/analyze-existing [blog URL]
/rewrite [blog URL]
/optimize [draft or rewrite file]
```

**Note**: Low-level scripts remain available for maintainers, but user-facing workflows should be run through slash commands. Simpro's primary competitor intel lives in `context/competitor-analysis.md` (40+ battlecards).

### WordPress Integration

Publishing uses the WordPress REST API with a custom MU-plugin that exposes Yoast SEO fields for **simprogroup.com** (or your staging site).

**Setup**:
1. Install `wordpress/seo-machine-yoast-rest.php` as an MU-plugin on the WordPress site
2. Add `wordpress/functions-snippet.php` to the theme's `functions.php`
3. Configure WordPress credentials in `.env`:
   ```
   WP_URL=https://www.simprogroup.com
   WP_USERNAME=your_username
   WP_APP_PASSWORD=your_application_password
   ```

See `wordpress/README.md` and `data_sources/README.md` for setup details.

## Directory Structure

```
seomachine/
+-- .claude/
|   +-- commands/              # Slash commands (research, write, article, landing, etc.)
|   +-- agents/                # SEO, meta, internal link, editor, CRO, performance agents
|   +-- skills/                # Marketing skills (copywriting, CRO, seo-audit, etc.)
|   +-- settings.local.template.json
|   +-- settings.local.json    # Local only (gitignored)
+-- mcp-gsc/                   # Bundled GSC MCP server (venv/ and token.json gitignored)
+-- tools/mcp/                 # analytics-mcp stdio wrapper
+-- credentials/               # adc.json, gsc secrets (gitignored except .gitkeep)
+-- .mcp.json.template         # Copy to .mcp.json (gitignored)
+-- data_sources/
|   +-- modules/               # GA4, GSC, analyzers, aeo_geo_rater, content_scrubber, etc.
|   +-- config/.env.example
+-- context/                   # Simpro brand + SEO/AEO context (see _coverage-report.md)
|   +-- brand-voice.md
|   +-- style-guide.md
|   +-- features.md
|   +-- competitor-analysis.md
|   +-- target-keywords.md
|   +-- internal-links-map.md
|   +-- writing-examples.md
|   +-- seo-guidelines.md
|   +-- aeo-geo-blog-strategy.md
|   +-- ai-citation-targets.md
|   +-- reddit-strategy.md
|   +-- cro-best-practices.md
|   +-- lightning-positioning.md   # Scoped Lightning overlay only
|   +-- _coverage-report.md
+-- config/competitors.example.json
+-- wordpress/                 # Yoast REST MU-plugin
+-- examples/castos/           # Upstream template reference
+-- topics/                    # Blog topic ideas
+-- research/                  # Briefs and SERP research (gitignored content)
+-- drafts/                    # Blog drafts in progress
+-- rewrites/                  # Updated blog posts
+-- published/                 # Final blog markdown
+-- review-required/
+-- landing-pages/
+-- audits/                    # Landing/page audits (e.g. FSM software page)
+-- repurposed/
+-- tests/                     # Unit tests (aeo_geo_rater, content_scrubber, …)
+-- scripts/                   # Batch research and SEO scripts
+-- README.md
```

## Context Files (Simpro)

Blog quality depends on the Obsidian vault first. These `context/` files are downstream mirrors/fallbacks for cloned routines without vault access; see `context/_coverage-report.md` for status, sources, and refresh cadence.

| File | Status | Use when |
|------|--------|----------|
| `brand-voice.md` | Filled | Every blog — FY26 pillars, Voice Style Guide tone, Lightning pointer |
| `style-guide.md` | Filled | Editorial rules, product names, 24/6 support, regional terms |
| `features.md` | Filled | Product copy, add-ons, proof points |
| `writing-examples.md` | Filled | Voice calibration — four simprogroup.com articles |
| `seo-guidelines.md` | Filled | On-page SEO structure for Simpro blogs |
| `aeo-geo-blog-strategy.md` | Filled | AEO/GEO — Capsule Method, PAA, schema, E-E-A-T |
| `target-keywords.md` | Filled + metrics | Clusters + GSC/GA4/Semrush US data |
| `internal-links-map.md` | Filled + metrics | Sitemap URLs + performance-prioritized links |
| `competitor-analysis.md` | Filled | 40+ battlecards + SERP/backlink overlays |
| `ai-citation-targets.md` | Filled | AI citation register + PEEC insight |
| `reddit-strategy.md` | Filled | Community targets and engagement rules |
| `cro-best-practices.md` | Source-aligned | CRO overlay + experiment/KPI/HubSpot map |
| `lightning-positioning.md` | Scoped overlay | **Only** Lightning/Cooper/JustAsk blog topics |
| `_coverage-report.md` | Meta | Coverage log and remaining gaps |

**Refreshing context**: Re-pull GSC/GA4 quarterly into keywords and internal links; re-run `/research-ai-citations` before major campaigns; verify Lightning and pricing claims before publish.

## Blog Quality Standards

Every Simpro blog post should meet these requirements:

### Content
- [ ] Word count fits the Reader Contract, search intent, and available evidence
- [ ] Unique angle vs. ServiceTitan, Jobber, Housecall Pro, and listicle competitors
- [ ] Factually accurate — verify stats, customer names, and product claims
- [ ] Metric Proof Pack passes for metric-sensitive topics: Search log complete, at least one Approved metric included, and each metric has public URL or local proof artifact plus source-visible Evidence
- [ ] Every metric, statistic, or numeric business claim has same-paragraph proof or a Source Map / Customer Proof Pack entry with a public URL or local proof artifact
- [ ] Source support guard passes: strict proof rows include Claim, URL, Evidence, and Status: approved; any named customer metric appears in Customer Proof Pack Approved metrics
- [ ] Customer proof diversity guard passes: Customer Proof Pack includes Quote Matrix, Reference, Customer Story, or review-site search evidence when case studies are used, a `Customer Proof Selection Decision`, and a source-specific `Reuse reason` plus selector-backed proof that no stronger underused approved proof fits the same role when selected proof is recently used or overused
- [ ] Review story identity guard passes when review-derived story copy appears: the sidecar includes identity-backed `Review Story Selection`, the selected story has a public review URL, and the public article links that URL in the same paragraph as the paraphrase
- [ ] Actionable for **trade and field service leaders** (not generic SMB advice)
- [ ] Simpro voice: authoritative, trades-focused, outcomes-driven from the vault first (`brand-voice.md` is fallback mirror context only)

### SEO
- [ ] Natural terminology coverage, semantic variations, and keyword-stuffing detection checked per `seo-guidelines.md`
- [ ] Keyword in H1, first 100 words, at least one relevant H2 where natural, conclusion, meta, and slug
- [ ] Intent-appropriate internal links from `internal-links-map.md` (performance-prioritized pages where relevant)
- [ ] At least 1 down-funnel internal link to `https://www.simprogroup.com/industries`, `/industries/...`, `/solutions/...`, or `/features/...`; Anchor text must match the destination keyword
- [ ] Claim-fit credible external sources with natural in-sentence attribution; evidence needs determine the count
- [ ] Meta title 50-60 characters with `| Simpro` when space allows
- [ ] Meta description 150-160 characters with accurate value or action language suited to search intent
- [ ] Proper H1 -> H2 -> H3 hierarchy

### AEO / GEO (generative engines)
- [ ] Capsule Method: 50-60 word direct answer under H1 and on 60%+ major H2s
- [ ] FAQ policy is intent-driven: `required` when useful or brief-selected; otherwise `not_applicable` with a non-empty rationale
- [ ] When visible FAQs exist, answer quality passes: every answer leads with a supported number/range, named recommendation, definition, concrete action, or explained yes/no response; limitations follow the direct answer
- [ ] When visible FAQs exist, FAQ proof passes: every answer contains at least 1 authoritative non-owned public evidence link in visible copy. A Source Map or FAQ Proof Map cannot replace the link
- [ ] PAA provenance passes against the exact eligible questions in the bound structured AnswerSocrates artifact or rewrite brief section
- [ ] E-E-A-T Proof Map resolved with Experience proof and Expertise proof, including review-site experience evidence when reviews show first-hand customer experience
- [ ] Author policy: If a named author is present, include `author` and map it to `Person as author`; If no named author is available, omit `author`, omit `Person as author`, and record the no-author decision in the blog assembly BOM and validation sidecar
- [ ] Schema notes: BlogPosting and BreadcrumbList for standard blog posts; add FAQPage and Question and Answer inside FAQPage only when visible FAQs exist; ImageObject for the featured image or logo; Organization as publisher reference only, not a separate full schema block; for public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters; VideoObject only if embedded
- [ ] Target **90+** on `aeo_geo_rater` when run through `content_scorer`

### Readability
- [ ] 8th-10th grade reading level (trades audience)
- [ ] Short sentences; active voice; no vendor cliches (`style-guide.md` avoid list)
- [ ] Subheadings follow topic and reader-question changes; lists remain scannable

### Structure
- [ ] Hook -> problem -> promise intro
- [ ] Intent-appropriate next action matched to the Reader Contract and funnel stage; no CTA added when none is called for
- [ ] Lightning topics only: also pass `lightning-positioning.md` naming rules

## Best Practices

### Before Writing a Blog Post
1. **Research first**: `/research` or `/research-serp` — confirm intent and gaps vs. top SERP
2. **Bind PAA provenance**: New articles require a structured AnswerSocrates artifact. Rewrites use a dedicated pre-picked brief section when present; otherwise they require AnswerSocrates. Use a CSV only with a bound genuine blocked-state artifact.
3. **Check context**: run connector health and discovery, search in the task's natural language, read and expand results by `resource_id`, then build and validate the generated context binding; use `brand-voice.md`, `writing-examples.md`, and `aeo-geo-blog-strategy.md` only as fallback mirrors where applicable
4. **Lightning only if on-topic**: Load `lightning-positioning.md` for Cooper/JustAsk/agent posts
5. **Keywords and links**: `target-keywords.md` + `internal-links-map.md` for cluster and URL targets
6. **E-E-A-T proof**: Build the E-E-A-T Proof Map before drafting. Use `context/aeo-geo-blog-strategy.md` for review-story, Capterra-theme, exact-quote, rating, and metric boundaries.
7. **Metric Proof Pack**: For software, comparison, pricing, cost, ROI, KPI, profit, margin, guide, and vs topics, complete metric research before drafting and record approved metrics in the validation sidecar.
8. **Customer Proof Pack**: Before selecting or drafting proof, resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and add the generated selector-first `Customer Proof Slate` to the validation sidecar. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the sidecar and do not invent proof. experience_story consideration is required and E-E-A-T story usage is optional. Use a proof-backed customer/review POV only when it improves the article objective. If no story fits, use `Selected: [none]` with section-specific rejection reasons. Treat any `recent_uses_90d` value above 0 as a proof-diversity warning. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. If selected proof appears in public copy, add `Selected Customer Proof Mining` so the selected URL is checked for quotes, metrics, POV/story, and workflow themes before final use. If selected proof is recently used or overused, add a selector-backed, source-specific `Reuse reason` in the validation sidecar proving no stronger underused approved proof fits. Use `context/aeo-geo-blog-strategy.md` as the full policy.
9. **Proof-index health and intake**: Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates, then use `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json`.

### During Writing
1. **Follow the brief**: Outline from `research/brief-*.md`
2. **Trades language**: job costing, dispatch, PM, quotes — not generic "solutions" copy
3. **Named proof**: Customer outcomes from approved case studies and mapped metrics in `features.md`; use public-facing source links in the article body
4. **Metric Proof Pack**: Do not add numbers first and source them later. Add only Approved metric rows from the Search log, and use the source-visible Evidence exactly as the public URL or local proof artifact supports it.
5. **Metric/stat proof**: Every metric, statistic, or numeric business claim must map to evidence that proves it, either through a same-paragraph public link or a Source Map / Customer Proof Pack entry with a public URL or local proof artifact
6. **FAQ quality and proof**: When visible FAQs exist, every answer must use a 40-60 word first paragraph, lead with a concrete extractable answer, and contain at least 1 authoritative non-owned public evidence link in visible copy. A Source Map or FAQ Proof Map cannot replace the link.
7. **Source support proof**: Add strict proof rows with Claim, Approved quote, or Approved metric plus URL, Evidence, and Status: approved for high-risk claims. Evidence must be visible in the cited public source or local proof artifact.
8. **Source mapping**: Map every general or proof-sensitive claim to a claim-fit source. General claim rows require exact claim/type/relation fields plus a hash-bound `simpro-source-classification/v1` artifact. PDF or unreachable-HTML fallback requires a hash-bound `simpro-source-capture-receipt/v1`; evidence needs determine source/link count
9. **Down-funnel link**: Add 1 contextual down-funnel internal link to an industry, solution, or feature page. Use `https://www.simprogroup.com/industries` for broad trades topics when no single industry page fits.
10. **Context boundary**: Use `context/` files as the internal source of truth for voice, positioning, approved claims, proof candidates, and approved metrics only when the Obsidian vault is unavailable; otherwise treat them as repo-local mirrors/fallbacks. Draft bodies may use public sources and context-backed proof, but must not mention repo context, context file paths, Source Maps, PAA artifacts, change summaries, schema notes, internal proof-path instructions, or source/proof meta-commentary. Translate proof into audience-facing takeaways, outcomes, or workflow lessons.
11. **Competitive framing**: Use `Competitive Shortlist Decision` from the validation sidecar and `competitor-analysis.md` only as a fallback mirror; differentiate, do not disparage

### After Writing
1. **Agent passes**: SEO Optimizer, Meta Creator, Internal Linker, Keyword Mapper
2. **Scrub punctuation artifacts**: `/scrub` or `content_scrubber.py` before human review
3. **Seal readiness**: Follow the exact build -> preflight -> finalize -> detached final readiness commands in Blog Assembly BOM and Readiness Seal.
4. **Optimize or repair**: Run `/optimize` after non-scoring gates pass when quality is below 85/100 or AEO/GEO is below 90/100. Treat optimization as a mutation, then rerun scrub and Context Binding and restart the two-phase seal.
5. **Final readiness**: Accept only a passed detached attestation bound to the final BOM hash and all final inputs.
6. **Publish**: `/publish-draft` to WordPress when approved

The `/publish-readiness` command runs Context Binding, blog assembly BOM, public artifact, AI copy, URL, FAQ answer quality, FAQ proof, source support, customer proof, review story, early artifact, answer withholding, vault brand language, content score, and AEO/GEO gates internally. Use individual Python guard modules only when debugging a specific failed gate from the canonical policy in `context/aeo-geo-blog-strategy.md`.

Use a validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md` for non-public proof blocks. Blog copy must not contain an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan.

### For Blog Rewrites
1. **`/analyze-existing`** on the live simprogroup.com URL or `published/` file
2. **Confirm AEO/GEO inputs**: main answer target, PAA/FAQ provenance, source map, E-E-A-T Proof Map, schema notes, and missing strategy inputs
3. **Run the quality loop**: scrub, regenerate Context Binding, build the provisional BOM, run preflight, finalize, and run detached final readiness. If optimization mutates content, restart from the mutation receipt.
4. **Refresh supported metrics** where GSC/GA4 identifies a relevant reader or task opportunity
5. **Preserve strong sections**; expand an H2 only when reader payoff, evidence, or task coverage is missing
6. **Re-check AI citations** if the post targets AI-intent queries

URL validation confirms destinations resolve; it does not prove the page supports the claim, so Source Map and E-E-A-T proof review still verify claim support.

Numeric claim source guard confirms every metric, statistic, or numeric business claim has a same-paragraph public link or a matching Source Map / Customer Proof Pack entry with a public URL or local proof artifact. It does not prove semantic support; it blocks unmapped numbers before scoring and `/optimize`.

Metric Proof Pack guard confirms metric-sensitive articles have documented metric research before writing or publish readiness. It requires a Search log and at least one Approved metric with public URL or local proof artifact, source-visible Evidence, Status: approved, and intended Use, unless `Metric requirement: not applicable` is documented with a reason. It blocks metric-free software, comparison, pricing, cost, ROI, KPI, profit, margin, guide, and vs topics before scoring and `/optimize`.

FAQ answer quality guard blocks generic deflections, missing answers, and unexplained binary responses. FAQ proof guard separately confirms every FAQ answer contains an authoritative non-owned public evidence link in visible copy. Sidecar-only proof does not pass. Both guards run before scoring and `/optimize`.

PAA provenance guard always runs for blogs. It validates the bound structured AnswerSocrates artifact or rewrite brief section, then confirms every visible FAQ heading matches the eligible selected-question set exactly. Supplemental sources and proof links cannot replace PAA provenance.

Source support guard confirms high-risk claims have strict proof rows with source-visible Evidence. Case-study proof paths and Review-site experience evidence may support non-metric E-E-A-T PoV and paraphrased themes only. Exact quotes/testimonials must appear in Customer Proof Pack Approved quotes with customer/brand or reviewer, source type, public URL, Evidence, and approved status. A named customer metric must appear in Customer Proof Pack Approved metrics with customer/brand, public URL, Evidence, and approved status; Source Map alone is insufficient for quotes, testimonials, or named metrics.

Customer proof diversity guard confirms proof selection is not defaulting to recently used or overused case studies. It requires Quote Matrix, Reference, Customer Story, or review-site search evidence when case-study proof is selected, a `Customer Proof Slate`, `Selected Customer Proof Mining`, a `Customer Proof Selection Decision`, and a source-specific `Reuse reason` plus selector-backed proof that no stronger underused approved proof fits the same role when `customer-proof-usage-ledger.json` shows repeated use. Before claiming a source is underused, inspect `recent_uses_90d`, run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/`, and backfill missing public-copy usage in `context/customer-proof-usage-ledger.json`. Use `customer-proof-index.json` plus `customer-proof-usage-ledger.json` through `customer_proof_selector.py` to choose the most relevant approved proof.

## Workflow Examples

### Example 1: New FSM Blog Post

```
# Topic in topics/field-service-management-software.md

/research field service management software
# -> research/brief-field-service-management-software-[date].md

/write field service management software
# -> drafts/...md (automatic agent passes)

/optimize drafts/field-service-management-software-[date].md
/publish-draft drafts/field-service-management-software-[date].md
```

### Example 2: Article with Full PAA Collection

```
/article best hvac software
# AnswerSocrates PAA -> brief -> draft with conditional FAQ schema notes
```

### Example 3: Rewrite an Existing Simpro Blog

```
/analyze-existing https://www.simprogroup.com/blog/what-is-field-service-management/
/rewrite field service management
# Rewrite keeps the slug and must carry PAA/FAQ provenance, source map, E-E-A-T Proof Map, and 85/90 quality gates
/optimize rewrites/field-service-management-rewrite-[date].md
```

### Example 4: AI Citation Gap Campaign

```
/research-ai-citations best field service management software
# Updates context/ai-citation-targets.md outreach list
# Then brief + /write listicle or comparison post targeting cited sources
```

### Example 5: Lightning Launch Blog (scoped)

```
/research Simpro Lightning job costing
# Commands auto-load lightning-positioning.md when Lightning entities detected
/write Simpro Lightning job costing
# Verify Cooper/JustAsk naming and time-sensitive claims before publish
```

## Tips & Tricks

### Maximizing Blog Quality
- **Read `writing-examples.md`** before each session — match rhythm and proof density
- **Lead with reader payoff**: prefer relevant approved named customer proof over generic examples when it materially supports the objective; if no approved proof fits, use an unnamed explanatory scene or omit the story
- **Use strong SERP defaults**: match the dominant observed content type, target every applicable SERP feature, and fill recurring reader-critical evidence-supported gaps unless the Reader Contract documents an exception
- **Capsule answers**: Put the direct answer in the first 50-60 words under each major H2
- **PAA coverage**: Use the structured AnswerSocrates artifact, or a rewrite's dedicated pre-picked brief section. Treat SERP, Reddit, and YouTube as supplemental only; use a CSV only with a genuine bound blocker artifact.

### SEO + AEO for simprogroup.com
- **Internal links**: Prefer URLs flagged high in `internal-links-map.md` (GSC/GA4 priority)
- **AI-intent posts**: Cross-check `ai-citation-targets.md` before "best FSM software" listicles
- **Avoid**: *all-in-one*, *tradies* as buyer label, *24/7 live support* (use **24/6**)
- **Refresh winners**: Re-optimize posts with quick-win GSC positions (11-20) quarterly

### Workflow Efficiency
- **`/performance-review`** and `/priorities` for what to write or rewrite next
- **`/scrub` + `ai_copy_linter.py`** before editorial handoff
- **MCP first** for live GSC/GA4 pulls; Python scripts for batch reports
- **Reuse battlecard plays** from `competitor-analysis.md` in comparison posts

### Avoiding Common Mistakes
- Avoid generic SaaS voice instead of trades-leader tone.
- Avoid using *Lightning* without a brand prefix such as Simpro Lightning.
- Do not skip mandatory PAA provenance or add an FAQ when the intent-driven policy is `not_applicable`.
- Do not publish Lightning pricing or roadmap language without verification.
- Avoid empty competitor differentiation; state a supported outcome without disparagement.

## Maintenance

### Weekly
- Add blog ideas to `topics/`
- Run `/performance-review` or check GSC MCP for quick wins
- Monitor priority threads per `reddit-strategy.md` (F5Bot queries)

### Monthly
- Refresh top blog posts losing CTR or position in GSC
- Add new simprogroup.com URLs to `internal-links-map.md`
- Spot-check `ai-citation-targets.md` outreach statuses

### Quarterly
- Re-pull US GSC/GA4 into `target-keywords.md` and `internal-links-map.md`
- Review `context/_coverage-report.md` and update stale battlecard/SERP data
- Re-run `/research-ai-citations` on core FSM prompt families
- Sync Voice Style Guide / Message House if FY messaging changes
- Full pass on `competitor-analysis.md` when new battlecards ship

## Troubleshooting

### "Blog doesn't sound like Simpro"
- Re-run connector semantic search and read the current messaging and style results by `resource_id`, then use `brand-voice.md` and `writing-examples.md` only as fallback mirrors; compare to a published simprogroup.com post
- For Lightning posts, confirm `lightning-positioning.md` is loaded and Cooper/JustAsk rules are followed
- Run `/scrub`, then `ai_copy_linter.py`, then Editor agent for robotic phrasing

### "AEO/GEO score below 90"
- Treat the result as a repair trigger, not a reporting endpoint. Review `aeo_geo.checks`, classify each failure as a copy gap, proof/sidecar gap, or scorer or parser false negative, and apply the top 3-5 fixes.
- Fix a scorer or parser false negative with regression coverage instead of changing accurate copy to satisfy brittle matching.
- Rerun `/scrub`, AI copy lint, URL validation, regenerate Context Binding with `context_binding_generator.py`, update the blog assembly BOM, and rerun `/publish-readiness`; repeat once if needed, then route to `review-required/` if the score remains below 90/100 after 2 iterations.

### "MCP / GSC / GA4 not connecting"
- Confirm `.mcp.json` paths match your machine (from `.mcp.json.template`)
- GSC: OAuth via `mcp-gsc/` — do not point `GSC_CREDENTIALS_PATH` at the OAuth client secret
- GA4: set `GOOGLE_APPLICATION_CREDENTIALS` to `credentials/adc.json`
- See `CLAUDE.md` credential boundaries

### "Internal links are wrong or stale"
- Refresh sitemap-backed URLs in `internal-links-map.md`
- Re-pull GSC page metrics for US priority pages

### "Keyword or volume data missing"
- Priority set: Semrush MCP metrics in `target-keywords.md` (15 terms)
- Expansion: run `/research-serp` or DataForSEO scripts for new clusters

### "Too similar to ServiceTitan / Jobber listicles"
- Use battlecard **Quick Competitive Plays** in `competitor-analysis.md`
- Lead with Simpro outcomes (multi-trade, job costing, recurring maintenance) not feature tables alone

## Support & Contributions

### Getting Help
- `context/_coverage-report.md` — what is filled vs. still gap
- `CLAUDE.md` — commands, MCP, and Python paths
- [Claude Code documentation](https://docs.claude.com/claude-code)

### Contributing (Simpro fork)
- Internal work: use feature branches targeting `main` on [Simpro-Group-Marketing/seomachine](https://github.com/Simpro-Group-Marketing/seomachine)
- Upstream fixes: consider PRs to [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine) when generic

## License

MIT License — see [LICENSE](LICENSE). Original development by Castos; Simpro Group Marketing maintains this fork for trades/FSM blog workflows.

## Credits

Built with [Claude Code](https://claude.com/claude-code) by Anthropic.

Upstream project: [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine) (originally developed for Castos). This fork is maintained by Simpro Group Marketing for trades and field-service SEO/AEO content.

## Examples & Community

**Simpro context**: Start with `context/_coverage-report.md` and the filled files listed in Getting Started.

**Upstream example**: `examples/castos/` shows the original Castos template pattern from the open-source repo.

**Contributions**: Internal Simpro Marketing changes use feature branches targeting `main`. Upstream improvements may be contributed back to TheCraigHewitt/seomachine where appropriate.

---

**Ready to start creating?**

1. Copy `.env.example`, `.mcp.json.template`, and credential files for your machine
2. Run `/research [your topic]` (or `/research-serp` for SERP-first work)
3. Review the brief in `research/`
4. Run `/write [your topic]` or `/article [your topic]` for full PAA collection
5. Check AEO/GEO score and publish via `/publish-draft` when ready

Happy writing!
