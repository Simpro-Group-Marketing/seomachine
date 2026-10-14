# Agent Instructions

This repo is proof-sensitive. Never synthesize data, customer claims, review claims, metrics, rankings, PAA questions, or quotes.

This is a pointer file for Codex and other agents: each rule lives in exactly one canonical home listed under "Where policy lives". Read the canonical doc before acting; do not restate its policy here.

## Project Overview

SEO Machine is a proof-governed workspace for researching, writing, optimizing, and publishing SEO and AEO/GEO blog content. Commands orchestrate workflows, specialist agents return advisory findings, and Python modules provide governance, evidence, and release gates. Python never drafts or patches public article copy.

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

Workflow contracts live in `.claude/commands/` and are shared by Claude Code and Codex. When asked to run a command, execute the steps in its command doc.

- `/research [topic]` - Parallel research lanes, brief, and the production BOM for a new article
- `/write [topic]` - Native draft in `drafts/` from the production BOM, then parallel advisory reviewers
- `/rewrite [topic]` - Native rewrite in `rewrites/` from a production BOM
- `/optimize [file]` - Revise from the latest release record's blocking findings and priority fixes, then release again
- `/scrub [file]` - Read-only diagnostics for invisible Unicode marks, em dashes, and whitespace artifacts
- `/publish-readiness [file]` - One-pass release (truth, coverage, and the three scores) that writes the release record; the sole release verdict
- `/analyze-existing [URL or file]` - Content health and AEO/GEO rewrite-readiness audit
- `/performance-review` - Analytics-driven content priorities
- `/publish-draft [file]` - Publish to WordPress via REST API after readiness passes
- `grav-publish` (skill) - Publish a finished article to Grav CMS on the GitHub `dev` branch
- `/cluster [topic]` - Topic cluster strategy with pillar, supporting articles, and linking map
- `/content-calendar` - Month-long content calendar mapped to clusters, keywords, and cadence
- `/priorities` - Content prioritization matrix
- `/research-serp`, `/research-gaps`, `/research-trending`, `/research-topics` - Specialized research commands
- `/research-performance` - No-argument performance queue; `/research-performance [URL-or-path]` writes the target report-and-receipt pair
- `/research-ai-citations [topic]` - Evidence-bound AI citation research without citation predictions
- `/repurpose [article] [--canonical-url URL]` - Optional manual, evidence-bound distribution handoff; it is not an AI-citation mechanism
- `/landing-write`, `/landing-audit`, `/landing-research`, `/landing-publish`, `/landing-competitor` - Landing page commands

## Pipeline directories

`topics/` (ideas) -> `research/` (briefs, production BOM specs and BOMs, research artifacts, release records) -> `drafts/` or `rewrites/` (articles) -> `published/` (final)

Rewrites go to `rewrites/`. Landing pages go to `landing-pages/`. Audits go to `audits/`. Repurposed content goes to `repurposed/`.

## Where policy lives

Command docs carry per-command steps and the selector, guard, and release commands they run; detailed policy stays in the canonical doc they point to.

| Canonical home | Governs |
|---|---|
| `context/aeo-geo-blog-strategy.md` | AEO/GEO and proof policy: Simpro vault source rule and nonconnector branch, author voice, competitor and feature guardrails, native workflow, production BOM, and the mandatory scrub/release/optimize loop, score thresholds, PAA, Metric and Customer Proof Packs, E-E-A-T, Fred authority, citation modes and link counts, reader-facing copy boundary, drafting rules, publish gates, and the recovery loop |
| `context/blog-editorial-strategy.md` | The production BOM as the editorial plan of record, Reader Contract, story safety, specificity, headline integrity, continuity, CTA profiles, and Reviewed Humanizer governance |
| `.claude/commands/publish-readiness.md` | One-pass release phases, truth and coverage checks, score thresholds, exit codes, and the release record |
| `.claude/commands/*.md` | Per-command workflow steps |
| `.agents/rules/seo-blog-strategy.md` | Commercial pillar destination, claim-level source quality, lifecycle, and schema and metadata guidance for the production BOM |
| `.agents/rules/customer-proof.md` | Selector-first customer proof, reuse ledger, nonconnector proof selector |
| `.agents/rules/faq-answer-quality.md` | FAQ answer shape and FAQ evidence-link requirements |
| `.agents/rules/blog-schema.md` | `schema_notes` frontmatter and author mapping |
| `.agents/rules/repository-development.md` | Rules for code, tests, configuration, scripts, and developer docs |
| `.agents/rules/agent-governance.md` | Changing agent, rule, skill, command, MCP, or steering docs; evidence status |
| `.claude/agents/*.md` | Advisory specialist reviewer roles used by the commands |
| `context/commercial-pillar-index.json`, `context/internal-links-map.md`, `context/seo-guidelines.md` | Commercial destinations, internal-link inventory, and SEO structure mechanics |
| `MEMORY.md` | Durable architecture, proof invariants, and resource limits |

Follow `.agents/rules/repository-development.md` for every code, test, configuration, script, command, or developer-documentation change. `.agents/rules/*` are generated mirrors of `.claude/rules/*`; edit the `.claude/rules` source and run `python tools/sync_rule_mirrors.py`.

## Non-negotiables

- Simpro work uses the current-project Simpro vault connector as its only brand and proof context source; repo-local context files are never an active or fallback source. AroFlo, BigChange, and ClockShark artifacts with no Simpro signal follow the nonconnector branch. If both connector paths (MCP and `SimproVaultClient`) fail, stop and record the blocker in the research brief.
- Never synthesize proof-sensitive data, customer claims, review claims, metrics, rankings, PAA questions, quotes, or source support.
- Public body copy reads as an article for the ICP. Workflow rationale, proof selection, and release status stay out of the body.
- `/publish-readiness` is the sole release verdict. Specialist reviewers are advisory, and no human approval step exists. Every new or changed blog runs the mandatory scrub, release, optimize, and re-release loop.
- Proof (verified facts, approved customer proof, and selector evidence) lives in the production BOM and research artifacts, never in public copy.
- Do not hand Python script calls back to the user as required steps; slash commands run scripts and MCP calls internally.
