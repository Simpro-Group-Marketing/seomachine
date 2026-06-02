# SEO Machine (Simpro Group)

Simpro Marketing's Claude Code workspace for **SEO and AEO/GEO blog posts** — research, write, optimize, and publish long-form articles for field-service and trades audiences, with Simpro-specific brand context, first-party analytics, and generative-engine optimization built in.

Fork of [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine), customized on branch `custom/local-context` for [simprogroup.com](https://www.simprogroup.com).

## Overview

SEO Machine is built on Claude Code and provides:
- **Custom Commands**: `/research`, `/write`, `/rewrite`, `/article`, `/analyze-existing`, `/optimize`, `/performance-review`, `/publish-draft`, `/priorities`, `/research-ai-citations`, plus SERP, gap, trending, cluster, and landing-page commands
- **Specialized Agents**: Content analyzer, SEO optimization, meta element creation, internal linking, keyword mapping, editor, performance analysis, headline generator, CRO analyst, landing page optimizer
- **Marketing Skills**: 26+ marketing skills for copywriting, CRO, A/B testing, email sequences, pricing strategy, and more
- **AEO/GEO Workflow**: Capsule Method structure, PAA/FAQ integration, source mapping, E-E-A-T Proof Map checks, and `aeo_geo_rater` scoring (90+ target) via `context/aeo-geo-blog-strategy.md`
- **Advanced SEO Analysis**: Search intent detection, keyword density & clustering, content length comparison, readability scoring, SEO quality rating (0-100)
- **Data Integrations**: GA4 and GSC via project MCP servers; DataForSEO, Ahrefs, and Semrush context in keyword/competitor files; PEEC AI citation tracking
- **Simpro Context Pack**: Pre-filled brand voice, style guide, features, 40+ competitor battlecards, writing examples, internal links, target keywords, AI citation register, Reddit strategy, and scoped Lightning positioning overlay
- **Workflow Organization**: Structured directories for topics, research, drafts, audits, and published content

## Getting Started

### Prerequisites
- [Claude Code](https://claude.com/claude-code) installed
- Anthropic API account

### Installation

1. Clone this repository:
```bash
git clone https://github.com/Simpro-Group-Marketing/seomachine.git
cd seomachine
git checkout custom/local-context
```

2. Install Python dependencies for analysis modules:
```bash
pip install -r data_sources/requirements.txt
```

This installs:
- Google Analytics/Search Console integrations
- DataForSEO API client
- NLP libraries (nltk, textstat)
- Machine learning (scikit-learn)
- Web scraping tools (beautifulsoup4)

3. Configure credentials and MCP (Simpro setup):

   - Copy `.env.example` to `.env` and set GA4/GSC/DataForSEO paths (see `CLAUDE.md` for MCP vs Python module credential boundaries)
   - Copy `.mcp.json.template` to `.mcp.json` and adjust paths for your machine
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
- Analyzes top 10 competitors
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
- Creates 2000-3000+ word SEO-optimized article
- Applies `context/aeo-geo-blog-strategy.md` (Capsule Method, PAA/FAQ, source mapping, schema notes)
- Maintains Simpro brand voice from `context/brand-voice.md` (and `lightning-positioning.md` when relevant)
- Integrates keywords from `context/target-keywords.md`
- Includes internal and external links per `context/internal-links-map.md`
- Uses only 1 link per paragraph, moving any second link to a separate paragraph or removing it
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
- Uses only 1 link per paragraph, moving any second link to a separate paragraph or removing it
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
- Competitor analysis (top 10)
- Content gaps and opportunities
- Recommended outline
- Internal linking strategy
- Meta elements preview

---

### `/write [topic]`
Create long-form SEO-optimized blog post (2000-3000+ words).

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
- Keyword density and clustering with topic detection
- Content length comparison vs top SERP competitors
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
- Exact metrics and benchmarks for improvements

**Powered by**:
- `search_intent_analyzer.py` - Search intent detection
- `keyword_analyzer.py` - Keyword density, clustering, LSI keywords
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
- 3-5 specific internal link suggestions
- Exact placement locations
- Anchor text recommendations
- User journey mapping
- SEO impact prediction

**References**: `context/internal-links-map.md`

---

### Keyword Mapper
**Purpose**: Keyword placement and integration analysis

**Analyzes**:
- Keyword density and distribution
- Critical placement checklist
- Natural language integration quality
- LSI keyword coverage
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

Copy `.mcp.json.template` → `.mcp.json` and `.claude/settings.local.template.json` → `.claude/settings.local.json`. See `CLAUDE.md` and `mcp-gsc/README.md`.

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
- Calculates exact keyword density and distribution
- Detects keyword stuffing risk with warnings
- Performs topic clustering using TF-IDF and K-means
- Generates distribution heatmap by section
- Identifies LSI (semantically related) keywords

**SEO Quality Rater** (`seo_quality_rater.py`):
- Rates content against SEO best practices (0-100 score)
- Category breakdowns: content, keywords, meta, structure, links, readability
- Identifies critical issues, warnings, and suggestions
- Determines publishing readiness

**Content Length Comparator** (`content_length_comparator.py`):
- Fetches and analyzes top 10-20 SERP competitor word counts
- Calculates median, 75th percentile, and optimal length
- Shows competitive positioning and gap to target
- Provides data-driven expansion recommendations

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
- `content_scrubber.py` - Removes invisible Unicode marks, em dashes, and whitespace artifacts before publish
- `ai_copy_linter.py` - Deterministic AI copy detection gate with line-level findings
- `engagement_analyzer.py` - Content engagement pattern analysis
- `competitor_gap_analyzer.py` - Competitive content gap identification
- `article_planner.py` - Data-driven article planning
- `section_writer.py` - Section-level content guidance
- `social_research_aggregator.py` - Social media research aggregation

### Python Research Scripts

Run from repo root:

```bash
# Content research
python3 scripts/research_quick_wins.py
python3 scripts/research_competitor_gaps.py
python3 scripts/research_performance_matrix.py
python3 scripts/research_priorities_comprehensive.py
python3 scripts/research_serp_analysis.py
python3 scripts/research_topic_clusters.py
python3 scripts/research_trending.py

# SEO analysis (config-driven - set up config/competitors.json first)
python3 scripts/seo_baseline_analysis.py
python3 scripts/seo_bofu_rankings.py
python3 scripts/seo_competitor_analysis.py

# Test API connectivity
python3 tests/test_dataforseo.py
```

**Note**: SEO analysis scripts can use `config/competitors.json` (copy from `config/competitors.example.json`). Simpro's primary competitor intel lives in `context/competitor-analysis.md` (40+ battlecards).

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
├── .claude/
│   ├── commands/              # Slash commands (research, write, article, landing, etc.)
│   ├── agents/                # SEO, meta, internal link, editor, CRO, performance agents
│   ├── skills/                  # Marketing skills (copywriting, CRO, seo-audit, …)
│   ├── settings.local.template.json
│   └── settings.local.json    # Local only (gitignored)
├── mcp-gsc/                   # Bundled GSC MCP server (venv/ and token.json gitignored)
├── tools/mcp/                 # analytics-mcp stdio wrapper
├── credentials/             # adc.json, gsc secrets (gitignored except .gitkeep)
├── .mcp.json.template         # Copy to .mcp.json (gitignored)
├── data_sources/
│   ├── modules/               # GA4, GSC, analyzers, aeo_geo_rater, content_scrubber, …
│   └── config/.env.example
├── context/                   # Simpro brand + SEO/AEO context (see _coverage-report.md)
│   ├── brand-voice.md
│   ├── style-guide.md
│   ├── features.md
│   ├── competitor-analysis.md
│   ├── target-keywords.md
│   ├── internal-links-map.md
│   ├── writing-examples.md
│   ├── seo-guidelines.md
│   ├── aeo-geo-blog-strategy.md
│   ├── ai-citation-targets.md
│   ├── reddit-strategy.md
│   ├── cro-best-practices.md
│   ├── lightning-positioning.md   # Scoped Lightning overlay only
│   └── _coverage-report.md
├── config/competitors.example.json
├── wordpress/                 # Yoast REST MU-plugin
├── examples/castos/           # Upstream template reference
├── topics/                    # Blog topic ideas
├── research/                  # Briefs and SERP research (gitignored content)
├── drafts/                    # Blog drafts in progress
├── rewrites/                  # Updated blog posts
├── published/                 # Final blog markdown
├── review-required/
├── landing-pages/
├── audits/                    # Landing/page audits (e.g. FSM software page)
├── repurposed/
├── tests/                     # Unit tests (aeo_geo_rater, content_scrubber, …)
├── scripts/                   # Batch research and SEO scripts
└── README.md
```

## Context Files (Simpro)

Blog quality depends on these context files. Most are **pre-filled** for Simpro; see `context/_coverage-report.md` for status, sources, and refresh cadence.

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
- [ ] Minimum 2,000 words (2,500-3,000+ preferred for pillar posts)
- [ ] Unique angle vs. ServiceTitan, Jobber, Housecall Pro, and listicle competitors
- [ ] Factually accurate — verify stats, customer names, and product claims
- [ ] Actionable for **trade and field service leaders** (not generic SMB advice)
- [ ] Simpro voice: authoritative, trades-focused, outcomes-driven (`brand-voice.md`)

### SEO
- [ ] Primary keyword density ~1-2% per `seo-guidelines.md`
- [ ] Keyword in H1, first 100 words, 2-3 H2s, conclusion, meta, and slug
- [ ] 3-5 internal links from `internal-links-map.md` (performance-prioritized pages where relevant)
- [ ] At least 1 down-funnel internal link to `https://www.simprogroup.com/industries`, `/industries/...`, `/solutions/...`, or `/features/...`; Anchor text must match the destination keyword
- [ ] 2-3 credible external sources with natural in-sentence attribution
- [ ] Meta title 50-60 characters with `| Simpro` when space allows
- [ ] Meta description 150-160 characters with a clear CTA
- [ ] Proper H1 → H2 → H3 hierarchy

### AEO / GEO (generative engines)
- [ ] Capsule Method: 50-60 word direct answer under H1 and on 60%+ major H2s
- [ ] 3-5 PAA/FAQ questions answered (from research brief or `/article` AnswerSocrates pass)
- [ ] E-E-A-T Proof Map resolved with Experience proof and Expertise proof, including review-site experience evidence when reviews show first-hand customer experience
- [ ] Named author, last-updated date, and customer or expert proof where applicable
- [ ] Schema notes: BlogPosting, FAQPage (if FAQ), Author, VideoObject (if embedded)
- [ ] Target **90+** on `aeo_geo_rater` when run through `content_scorer`

### Readability
- [ ] 8th-10th grade reading level (trades audience)
- [ ] Short sentences; active voice; no vendor clichÃ©s (`style-guide.md` avoid list)
- [ ] Subheadings every 300-400 words; scannable lists

### Structure
- [ ] Hook → problem → promise intro
- [ ] Demo- or trial-aligned CTA matched to funnel stage
- [ ] Lightning topics only: also pass `lightning-positioning.md` naming rules

## Best Practices

### Before Writing a Blog Post
1. **Research first**: `/research` or `/research-serp` — confirm intent and gaps vs. top SERP
2. **PAA when needed**: Use `/article` or supply a FAQ CSV if the brief lacks People Also Ask questions
3. **Check context**: `brand-voice.md`, `writing-examples.md`, and `aeo-geo-blog-strategy.md`
4. **Lightning only if on-topic**: Load `lightning-positioning.md` for Cooper/JustAsk/agent posts
5. **Keywords and links**: `target-keywords.md` + `internal-links-map.md` for cluster and URL targets
6. **E-E-A-T proof**: Build the E-E-A-T Proof Map from `internal-links-map.md`, `features.md`, `competitor-analysis.md`, public research, review-site experience evidence, and public-facing source links before drafting. Review narratives can support first-hand customer experience; star ratings, badges, rankings, aggregate ratings, and category claims require current source verification and brief-level approval.
7. **Customer Proof Pack**: Resolve Pack status, Quote Matrix candidates, Case-study proof paths, Review-site experience evidence, Approved metrics, Use in copy, Claims excluded, and approval status before drafting. Keep the Quote Matrix external and verify direct quotes or named metrics through Customer Stories, References, or public case-study paths.

### During Writing
1. **Follow the brief**: Outline from `research/brief-*.md`
2. **Trades language**: job costing, dispatch, PM, quotes — not generic "solutions" copy
3. **Named proof**: Customer outcomes from approved case studies and mapped metrics in `features.md`; use public-facing source links in the article body
4. **Source mapping**: At least three external claims with clear attribution
5. **Down-funnel link**: Add 1 contextual down-funnel internal link to an industry, solution, or feature page. Use `https://www.simprogroup.com/industries` for broad trades topics when no single industry page fits.
6. **Context boundary**: Use `context/` files as the internal source of truth for voice, positioning, approved claims, proof candidates, and approved metrics. Draft bodies may use public sources and context-backed proof, but must not mention repo context, context file paths, Source Maps, PAA artifacts, change summaries, schema notes, internal proof-path instructions, or source/proof meta-commentary. Translate proof into audience-facing takeaways, outcomes, or workflow lessons.
7. **Competitive framing**: Use `competitor-analysis.md` — differentiate, do not disparage

### After Writing
1. **Agent passes**: SEO Optimizer, Meta Creator, Internal Linker, Keyword Mapper
2. **Scrub punctuation artifacts**: `/scrub` or `content_scrubber.py` before human review
3. **Lint AI copy**: `python data_sources/modules/ai_copy_linter.py [file] --profile simpro-web --fail-on error`
4. **Optimize**: `/optimize` for final SEO polish
5. **Score**: Run content through scorer + AEO/GEO gate when publishing high-priority posts
6. **Publish**: `/publish-draft` to WordPress when approved

### For Blog Rewrites
1. **`/analyze-existing`** on the live simprogroup.com URL or `published/` file
2. **Confirm AEO/GEO inputs**: main answer target, PAA/FAQ provenance, source map, E-E-A-T Proof Map, schema notes, and missing strategy inputs
3. **Run the quality loop**: `/scrub`, AI copy linter, `content_scorer.py`, then `/optimize`
4. **Refresh metrics** in intro/CTA if GSC/GA4 shows new quick-win queries
5. **Preserve strong sections**; expand thin H2s vs. SERP leaders
6. **Re-check AI citations** if the post targets AI-intent queries

## Workflow Examples

### Example 1: New FSM Blog Post

```
# Topic in topics/field-service-management-software.md

/research field service management software
# → research/brief-field-service-management-software-[date].md

/write field service management software
# → drafts/…md (auto agent passes)

/optimize drafts/field-service-management-software-[date].md
/publish-draft drafts/field-service-management-software-[date].md
```

### Example 2: Article with Full PAA Collection

```
/article best hvac software
# AnswerSocrates PAA → brief → draft with FAQ schema notes
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
- **Lead with outcomes**: margin, time-to-paid, named customers (Shaffer Beacon, Foster Plumbing, etc.)
- **Capsule answers**: Put the direct answer in the first 50-60 words under each major H2
- **PAA coverage**: Pull questions from AnswerSocrates, SERP, `reddit-strategy.md` monitoring queries, YouTube, or a user CSV; do not invent missing questions

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
- ❌ Generic SaaS voice instead of trades-leader tone
- ❌ Using *Lightning* without brand prefix (Simpro Lightning, etc.)
- ❌ Skipping PAA/FAQ on informational posts
- ❌ Publishing Lightning pricing or roadmap without verification
- ❌ Empty competitor differentiation (name + outcome, not trash talk)

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
- Re-read `brand-voice.md` and `writing-examples.md`; compare to a published simprogroup.com post
- For Lightning posts, confirm `lightning-positioning.md` is loaded and Cooper/JustAsk rules are followed
- Run `/scrub`, then `ai_copy_linter.py`, then Editor agent for robotic phrasing

### "AEO/GEO score below 90"
- Add Capsule blocks under missing H2s (`aeo-geo-blog-strategy.md`)
- Ensure 3-5 PAA questions are answered and FAQ schema is noted
- Add named proof (customer, date, reviewer) and three source-mapped external links

### "MCP / GSC / GA4 not connecting"
- Confirm `.mcp.json` paths match your machine (from `.mcp.json.template`)
- GSC: OAuth via `mcp-gsc/` — do not point `GSC_CREDENTIALS_PATH` at the OAuth client secret
- GA4: `GOOGLE_APPLICATION_CREDENTIALS` → `credentials/adc.json`
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
- Internal work: branch `custom/local-context` on [Simpro-Group-Marketing/seomachine](https://github.com/Simpro-Group-Marketing/seomachine)
- Upstream fixes: consider PRs to [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine) when generic

## License

MIT License — see [LICENSE](LICENSE). Original development by Castos; Simpro Group Marketing maintains this fork for trades/FSM blog workflows.

## Credits

Built with [Claude Code](https://claude.com/claude-code) by Anthropic.

Upstream project: [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine) (originally developed for Castos). This fork is maintained by Simpro Group Marketing for trades and field-service SEO/AEO content.

## Examples & Community

**Simpro context**: Start with `context/_coverage-report.md` and the filled files listed in Getting Started.

**Upstream example**: `examples/castos/` shows the original Castos template pattern from the open-source repo.

**Contributions**: Internal Simpro Marketing changes go to `custom/local-context`. Upstream improvements may be contributed back to TheCraigHewitt/seomachine where appropriate.

---

**Ready to start creating?**

1. Copy `.env.example`, `.mcp.json.template`, and credential files for your machine
2. Run `/research [your topic]` (or `/research-serp` for SERP-first work)
3. Review the brief in `research/`
4. Run `/write [your topic]` or `/article [your topic]` for full PAA collection
5. Check AEO/GEO score and publish via `/publish-draft` when ready

Happy writing!
