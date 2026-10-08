# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. It is a pointer file: each rule lives in exactly one canonical home listed under "Where policy lives". Read the canonical doc before acting; do not restate its policy here.

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

This repo uses two project-scoped MCP servers, `gsc` and `analytics-mcp`. Codex reads `.codex/config.toml`; Claude-compatible clients can read `.mcp.json`. Both should point to this repo root, not to another local repo.

## Commands

Commands live in `.claude/commands/` and are invoked as slash commands. Each command doc is the shared workflow contract for Claude Code and Codex execution.

- `/research [topic]` - Keyword/competitor research, generates brief in `research/`
- `/write [topic]` - Create full article in `drafts/` and run the specialist machine reviewers
- `/rewrite [topic]` - Update existing content with SEO plus AEO/GEO rewrite gates, saves to `rewrites/`
- `/optimize [file]` - Required post-preflight SEO/AEO repair or recorded no-op pass
- `/scrub [file]` - Read-only diagnostics for invisible Unicode marks, em dashes, and whitespace artifacts
- `/publish-readiness [file]` - Complete source-artifact gate stack and the sole release verdict
- `/analyze-existing [URL or file]` - Content health and AEO/GEO rewrite-readiness audit
- `/performance-review` - Analytics-driven content priorities
- `/publish-draft [file]` - Publish to WordPress via REST API (Yoast setup in `wordpress/README.md`)
- `grav-publish` (skill) - Publish a finished `drafts/`/`rewrites/` article to Grav CMS by committing `blogs/<slug>/article.en.md` to the GitHub `dev` branch via the `gh` Contents API (text only; images deferred). Config: `GRAV_REPO`, `GRAV_BRANCH`, `GRAV_BLOG_PATH`, `GRAV_DEFAULT_LANG` in `.env`.
- `/cluster [topic]` - Build complete topic cluster strategy with pillar + supporting articles + linking map
- `/content-calendar` - Month-long content calendar mapped to clusters, keywords, and cadence
- `/priorities` - Content prioritization matrix
- `/research-serp`, `/research-gaps`, `/research-trending`, `/research-topics` - Specialized research commands
- `/research-performance` - No-argument performance queue; `/research-performance [URL-or-path]` writes the target report-and-receipt pair
- `/research-ai-citations [topic]` - Evidence-bound AI citation research: generates prompts, clusters them, and records observed sources without citation predictions
- `/repurpose [article] --final-readiness [attestation] [--canonical-url URL]` - Prepares an optional manual, evidence-bound distribution handoff from a sealed article; it never posts externally or adds unsupported claims, and it is not an AI-citation mechanism
- `/landing-write`, `/landing-audit`, `/landing-research`, `/landing-publish`, `/landing-competitor` - Landing page commands

## Pipeline directories

`topics/` (ideas) -> `research/` (briefs, machine reviews, validation sidecars, release evidence) -> `drafts/` or `rewrites/` (articles) -> `published/` (final)

Rewrites go to `rewrites/`. Landing pages go to `landing-pages/`. Audits go to `audits/`. Repurposed content goes to `repurposed/`.

## Where policy lives

Command docs carry per-command steps and the selector, guard, and release commands they run; detailed policy stays in the canonical doc they point to.

| Canonical home | Governs |
|---|---|
| `context/aeo-geo-blog-strategy.md` | AEO/GEO and proof policy: Simpro vault source rule and nonconnector branch, author voice, competitor and feature guardrails, native workflow and BOM, the mandatory scrub/readiness/optimize loop, score thresholds, PAA, Metric and Customer Proof Packs, E-E-A-T, Fred authority, citation modes and link counts, reader-facing copy boundary, drafting rules, publish gates, and the recovery loop |
| `context/blog-editorial-strategy.md` | Editorial plan ownership, Reader Contract, story safety, specificity, headline integrity, continuity, CTA profiles, and Reviewed Humanizer governance |
| `.claude/commands/publish-readiness.md` | Gate stack, release wrapper phases (`optimization_started`, `final_readiness`), exit codes, and final handoff |
| `.claude/commands/*.md` | Per-command workflow steps |
| `.claude/rules/seo-blog-strategy.md` | Editorial plan v2 strategy objects, commercial pillar destination, claim-level source quality, lifecycle, metadata handoff |
| `.claude/rules/customer-proof.md` | Selector-first customer proof, reuse ledger, nonconnector proof selector |
| `.claude/rules/faq-answer-quality.md` | FAQ answer shape and FAQ evidence-link requirements |
| `.claude/rules/blog-schema.md` | `schema_notes` frontmatter and author mapping |
| `.claude/rules/repository-development.md` | Rules for code, tests, configuration, scripts, and developer docs |
| `.claude/rules/agent-governance.md` | Changing agent, rule, skill, command, MCP, or steering docs; evidence status |
| `.claude/agents/*.md` | Advisory specialist reviewer roles used by the commands |
| `context/commercial-pillar-index.json`, `context/internal-links-map.md`, `context/seo-guidelines.md` | Commercial destinations, internal-link inventory, and SEO structure mechanics |
| `MEMORY.md` | Durable architecture, proof invariants, and resource limits |

`.claude/rules/` is the source of truth for rule files. `.agents/rules/` and `.cursor/rules/` are generated mirrors; run `python tools/sync_rule_mirrors.py` after editing a rule.

## Non-negotiables

- Simpro work uses the current-project Simpro vault connector as its only brand and proof context source; repo-local context files are never an active or fallback source. AroFlo, BigChange, and ClockShark artifacts with no Simpro signal follow the nonconnector branch. If both connector paths (MCP and `SimproVaultClient`) fail, stop and record the blocker in the validation sidecar.
- Never synthesize proof-sensitive data, customer claims, review claims, metrics, rankings, PAA questions, quotes, or source support.
- Public body copy reads as an article for the ICP. Workflow rationale, proof selection, and readiness status stay out of the body.
- `/publish-readiness` is the sole release verdict. Machine reviewers are advisory, and no human approval step exists. Every new or changed blog runs the mandatory scrub, readiness, optimize, and final readiness loop.
- Proof maps and proof packs live in the validation sidecar `research/validation-[topic-slug]-[YYYY-MM-DD].md`, never in public copy.
- Do not hand Python script calls back to the user as required steps; slash commands run scripts and MCP calls internally.
