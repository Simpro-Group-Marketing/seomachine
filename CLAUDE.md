# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SEO Machine is an open-source Claude Code workspace for creating SEO-optimized blog content. It combines custom commands, specialized agents, and Python-based analytics to research, write, optimize, and publish articles for any business.

## Setup

```bash
pip install -r data_sources/requirements.txt
```

API credentials are configured in `.env` for repo-root scripts and `data_sources/config/.env` for legacy data-source scripts.

MCP credentials are repo-local and intentionally separate from the Python module service-account paths:
- GA4 MCP: `credentials/adc.json`, referenced by `GOOGLE_APPLICATION_CREDENTIALS`
- GSC MCP: `credentials/gsc_client_secrets.json`, referenced by `GSC_OAUTH_CLIENT_SECRETS_FILE`

Local Python modules still expect service-account paths when used directly:
- GA4 Python module: `GA4_CREDENTIALS_PATH`
- GSC Python module: `GSC_CREDENTIALS_PATH`

Do not point `GSC_CREDENTIALS_PATH` at the OAuth client secret. Do not add `ADK_DISABLE_PLUGGABLE_AUTH` for this MCP setup.

## MCP Setup

This repo uses two project-scoped MCP servers:
- `gsc`
- `analytics-mcp`

Codex reads `.codex/config.toml`; Claude-compatible clients can read `.mcp.json`. Both should point to `C:\Users\patrick.grueschow\Desktop\Repos\seomachine-main`, not to another local repo.

## Commands

All commands are defined in `.claude/commands/` and invoked as slash commands. These command docs are the shared workflow contract for Claude Code and Codex execution:

- `/research [topic]` - Keyword/competitor research, generates brief in `research/`
- `/write [topic]` - Create full article in `drafts/`, auto-triggers optimization agents
- `/rewrite [topic]` - Update existing content with SEO plus AEO/GEO rewrite gates, saves to `rewrites/`
- `/optimize [file]` - Final SEO polish pass
- `/analyze-existing [URL or file]` - Content health and AEO/GEO rewrite-readiness audit
- `/performance-review` - Analytics-driven content priorities
- `/publish-draft [file]` - Publish to WordPress via REST API
- `/article [topic]` - Simplified article creation
- `/cluster [topic]` - Build complete topic cluster strategy with pillar + supporting articles + linking map
- `/priorities` - Content prioritization matrix
- `/research-serp`, `/research-gaps`, `/research-trending`, `/research-performance`, `/research-topics` - Specialized research commands
- `/research-ai-citations [topic]` - AI citation audit: generates prompts, clusters them, audits which sources AI cites
- `/repurpose [file]` - Adapts article for LinkedIn, Medium, Reddit, Quora distribution
- `/landing-write`, `/landing-audit`, `/landing-research`, `/landing-publish`, `/landing-competitor` - Landing page commands

## Architecture

### Command-Agent Model

**Commands** (`.claude/commands/`) orchestrate workflows. **Agents** (`.claude/agents/`) are specialized roles invoked by commands. After `/write`, these agents auto-run: SEO Optimizer, Meta Creator, Internal Linker, Keyword Mapper.

Key agents: `content-analyzer.md`, `seo-optimizer.md`, `meta-creator.md`, `internal-linker.md`, `keyword-mapper.md`, `editor.md`, `headline-generator.md`, `cro-analyst.md`, `performance.md`, `cluster-strategist.md`.

### Python Analysis Pipeline

Located in `data_sources/modules/`. The Content Analyzer chains:
1. `search_intent_analyzer.py` - Query intent classification
2. `keyword_analyzer.py` - Density, distribution, stuffing detection
3. `content_length_comparator.py` - Benchmarks against top 10 SERP results
4. `readability_scorer.py` - Flesch Reading Ease, grade level
5. `seo_quality_rater.py` - Comprehensive 0-100 SEO score

### Data Integrations

- `google_analytics.py` - GA4 traffic/engagement data
- `google_search_console.py` - Rankings and impressions
- `dataforseo.py` - SERP positions, keyword metrics
- `data_aggregator.py` - Combines all sources into unified analytics
- `wordpress_publisher.py` - Publishes to WordPress with Yoast SEO metadata

### Opportunity Scoring

`opportunity_scorer.py` uses 8 weighted factors: Volume (25%), Position (20%), Intent (20%), Competition (15%), Cluster (10%), CTR (5%), Freshness (5%), Trend (5%).

## Running Python Scripts

```bash
# Research & analysis scripts (run from repo root)
python3 scripts/research_quick_wins.py
python3 scripts/research_competitor_gaps.py
python3 scripts/research_performance_matrix.py
python3 scripts/research_priorities_comprehensive.py
python3 scripts/research_serp_analysis.py
python3 scripts/research_topic_clusters.py
python3 scripts/research_trending.py
python3 scripts/seo_baseline_analysis.py
python3 scripts/seo_bofu_rankings.py
python3 scripts/seo_competitor_analysis.py

# Test API connectivity
python3 tests/test_dataforseo.py
```

## Content Pipeline

`topics/` (ideas) → `research/` (briefs) → `drafts/` (articles) → `review-required/` (pending review) → `published/` (final)

Rewrites go to `rewrites/`. Landing pages go to `landing-pages/`. Audits go to `audits/`. Repurposed content goes to `repurposed/`.

Blog rewrites must follow the same AEO/GEO evidence boundaries as new articles: sourced PAA/FAQ provenance, source mapping, E-E-A-T Proof Map inputs, direct-answer structure, schema notes, AI copy lint, `content_scorer.py`, and the 85/100 general quality plus 90/100 AEO/GEO gates before `/optimize`.

Context files are the internal source of truth for voice, positioning, approved claims, proof candidates, and approved metrics. Draft bodies may use public sources and context-backed proof, but must not mention repo context, context file paths, Source Maps, PAA artifacts, change summaries, schema notes, or internal proof-path instructions.

E-E-A-T proof must resolve Experience and Expertise before writing. Pull case-study URLs from `context/internal-links-map.md`, approved metrics/proof candidates from `context/features.md`, and review-site VoC or competitor experience themes from `context/competitor-analysis.md` or future review-context files. Context-backed metrics require public-facing source links in the article body.

## Context Files

`context/` contains brand guidelines that inform all content generation:
- `brand-voice.md` - Tone, messaging pillars
- `style-guide.md` - Grammar, formatting standards
- `seo-guidelines.md` - Keyword and structure rules
- `aeo-geo-blog-strategy.md` - Blog-specific AEO/GEO workflow for research, articles, analysis, and rewrites: AnswerSocrates PAA rules, Capsule Method, source mapping, E-E-A-T Proof Map, and 85/90 quality gates
- `internal-links-map.md` - Key pages for internal linking
- `features.md` - Product features
- `competitor-analysis.md` - Competitive intelligence
- `cro-best-practices.md` - Conversion optimization guidelines
- `ai-citation-targets.md` - Directories/platforms where your brand should be cited by AI tools
- `reddit-strategy.md` - Reddit engagement strategy for AI SEO and community visibility

## WordPress Integration

Publishing uses the WordPress REST API with a custom MU-plugin (`wordpress/seo-machine-yoast-rest.php`) that exposes Yoast SEO fields. Articles are published in WordPress block format (HTML comments in Markdown files).
