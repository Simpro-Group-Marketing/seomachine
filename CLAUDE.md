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

Codex reads `.codex/config.toml`; Claude-compatible clients can read `.mcp.json`. Both should point to this repo root, not to another local repo.

## Commands

All commands are defined in `.claude/commands/` and invoked as slash commands. These command docs are the shared workflow contract for Claude Code and Codex execution:

- `/research [topic]` - Keyword/competitor research, generates brief in `research/`
- `/write [topic]` - Create full article in `drafts/`, auto-triggers optimization agents
- `/rewrite [topic]` - Update existing content with SEO plus AEO/GEO rewrite gates, saves to `rewrites/`
- `/optimize [file]` - Final SEO polish pass
- `/analyze-existing [URL or file]` - Content health and AEO/GEO rewrite-readiness audit
- `/performance-review` - Analytics-driven content priorities
- `/publish-draft [file]` - Publish to WordPress via REST API
- `grav-publish` (skill) - Publish a finished `drafts/`/`rewrites/` article to Grav CMS by committing `blogs/<slug>/article.en.md` to the GitHub `dev` branch via the `gh` Contents API (text only; images deferred). Config: `GRAV_REPO`, `GRAV_BRANCH`, `GRAV_BLOG_PATH`, `GRAV_DEFAULT_LANG` in `.env`.
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
6. `url_validator.py` - URL validation guardrail for Markdown links and bare URLs
7. `metric_proof_pack_guard.py` - Metric Proof Pack guardrail requiring a Search log and at least one Approved metric with source-visible Evidence for metric-sensitive topics
8. `numeric_claim_source_guard.py` - Metric/stat proof guardrail for public numeric business claims
9. `faq_answer_quality_guard.py` - Blocking answer-first FAQ guardrail for generic deflections, missing answers, and unexplained binary responses
10. `faq_proof_guard.py` - FAQ proof guardrail requiring an authoritative non-owned public evidence link inside every visible FAQ answer; sidecar-only proof does not pass
11. `paa_provenance_guard.py` - PAA provenance guardrail requiring FAQ questions to match saved AnswerSocrates, SERP, Reddit, YouTube, or user PAA/FAQ CSV artifacts
12. `source_support_guard.py` - Strict source support guard requiring approved proof rows with source-visible Evidence snippets
13. `customer_proof_selector.py` - Customer proof selector automatically run by slash workflows with `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10` to choose the most relevant approved proof
14. `customer_proof_index_health.py` - Read-only proof inventory health report for source mix, approvals, overuse, and public-copy gaps
15. `customer_proof_index_intake.py` - Customer proof intake validator/merger for `context/customer-proof-intake-template.csv`
16. `customer_proof_diversity_guard.py` - Customer proof diversity guard requiring non-case-study proof search evidence, a `Customer Proof Selection Decision`, and source-specific `Reuse reason` plus selector-backed proof that no stronger underused approved proof fits the same role
17. `review_story_identity_guard.py` - Review story identity guard requiring identity-backed Review Story Selection, a public review URL, and same paragraph article link for review-derived E-E-A-T stories

### Data Integrations

- `google_analytics.py` - GA4 traffic/engagement data
- `google_search_console.py` - Rankings and impressions
- `dataforseo.py` - SERP positions, keyword metrics
- `data_aggregator.py` - Combines all sources into unified analytics
- `wordpress_publisher.py` - Publishes to WordPress with Yoast SEO metadata

### Opportunity Scoring

`opportunity_scorer.py` uses 8 weighted factors: Volume (25%), Position (20%), Intent (20%), Competition (15%), Cluster (10%), CTR (5%), Freshness (5%), Trend (5%).

## Research Command Workflows

Use slash commands for research and optimization workflows. Do not hand Python script calls back to the user as required steps; scripts and MCP calls are implementation details for the command runner.

```text
/research-performance
/research-performance [blog URL or path]
/research-gaps
/research-serp
/research-topics
/research-trending
/analyze-existing [blog URL]
/rewrite [blog URL]
/optimize [draft or rewrite file]
```

## Content Pipeline


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

`topics/` (ideas) → `research/` (briefs) → `drafts/` (articles) → `review-required/` (pending review) → `published/` (final)

Rewrites go to `rewrites/`. Landing pages go to `landing-pages/`. Audits go to `audits/`. Repurposed content goes to `repurposed/`.

Blog rewrites must follow the same AEO/GEO evidence boundaries as new articles: sourced PAA/FAQ provenance, answer-first FAQ quality, inline non-owned FAQ evidence links, source mapping, Metric Proof Pack inputs, E-E-A-T Proof Map inputs, direct-answer structure, schema notes, AI copy lint, URL validation, proof gates, source support, and the 85/100 general quality plus 90/100 AEO/GEO gates before final handoff. After all non-scoring gates pass, a sub-threshold score triggers the automatic AEO/GEO Recovery Loop and may use `/optimize`; it does not end at reporting.

Every FAQ must use a 40-60 word first paragraph and lead with a supported number/range, named recommendation, definition, concrete action, or explained yes/no response. Generic deflections block `faq_answer_quality_guard.py`. Every FAQ answer also needs at least 1 authoritative non-owned public evidence link in visible copy; a Source Map or FAQ Proof Map cannot substitute for that link.

For standard blog posts with FAQs, schema notes must list `BlogPosting`, `BreadcrumbList`, and `FAQPage`; nested entities must be `Person as author`, `Question and Answer inside FAQPage`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`. For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. Use `VideoObject` only when a video is embedded.

Use a validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md` for proof-only infrastructure. Public blog drafts and rewrites must not include an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan. Preferred publish readiness command: `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md`.

Before `/optimize` or any publish path, run the command-system gate:
```bash
/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

The slash command runs the public artifact, AI copy, URL, proof, source support, customer proof, review story, early artifact, answer withholding, content score, and AEO/GEO gates internally. Use individual guard modules only when debugging a failed gate from `context/aeo-geo-blog-strategy.md`.

Every standard blog draft and rewrite needs a usable artifact — a filled data table, download link, checklist deliverable, or calculator reference — within the first 300 words of body copy, and must supply a concrete number, range, or template when the target query implies one. Placeholder table scaffolds block publish. Policy lives in `context/aeo-geo-blog-strategy.md`.

URL validation confirms destinations resolve; it does not prove the page supports the claim, so Source Map and E-E-A-T proof review still verify claim support.

Metric Proof Pack guard confirms metric-sensitive articles have documented metric research before writing or publish readiness. It requires a Search log and at least one Approved metric with public URL or local proof artifact, source-visible Evidence, Status: approved, and intended Use unless `Metric requirement: not applicable` is documented with a reason.

Every metric, statistic, or numeric business claim must have a same-paragraph public link or a matching Source Map / Customer Proof Pack entry with a public URL or local proof artifact. Treat "industry standard," "FDD conventions," and "no anchor" as insufficient proof for numeric public claims.

FAQ proof requires every FAQ answer to include at least 1 authoritative non-owned public evidence link in visible copy. A question-specific Source Map / FAQ Proof Map row can document the same evidence but cannot replace the reader-facing link.

PAA provenance requires every FAQ question to match a saved PAA/FAQ source artifact when an FAQ section is present. Use `PAA/FAQ Provenance` with Source, Artifact, and Selected questions; see `context/aeo-geo-blog-strategy.md` for the full source-label and proof-boundary policy.

The source support guard requires strict proof rows with Claim, URL, Evidence, and Status: approved. The Evidence snippet must be visible in the cited public source or local proof artifact. Case-study proof paths and Review-site experience evidence may support non-metric E-E-A-T PoV and paraphrased themes only. Exact quotes or testimonial wording must appear in Customer Proof Pack Approved quotes with customer/brand or reviewer, source type, public URL, Evidence, and approved status. A named customer metric must appear in Customer Proof Pack Approved metrics with customer/brand, public URL, Evidence, and approved status; Source Map alone is insufficient for quotes, testimonials, or named metrics.

Before selecting customer proof, the command workflow must resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and add the generated selector-first `Customer Proof Slate` to the validation sidecar before drafting. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the sidecar and do not invent proof. Review generated selector output before choosing proof; do not skip execution. Edit selected/rejected rows only when editorial judgment requires it. experience_story consideration is required and E-E-A-T story usage is optional; if no story fits, use `Selected: [none]` with section-specific rejection reasons. Choose the most relevant approved proof, not the easiest mapped case study. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. If selected proof is recently used or overused, the validation sidecar needs a selector-backed, source-specific `Reuse reason`.

## Fred Voccola Authority Selection

For every new or changed Simpro blog and every rewrite, analysis, optimization, or publish-readiness pass, automatically run:

```powershell
python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5
```

Write the complete `Fred Voccola Authority Selection` block to the validation sidecar. Evaluation is mandatory; public use is optional. The vault connector and claim registry are the sole eligibility source, and the selector fails closed unless current connector revisions, resource hashes, and claim decisions validate. Fred evidence supports Expertise and Authority by default and counts as Experience only when the source explicitly supports first-hand personal or operating experience. It is additive to customer Experience proof, customer stories, and independent evidence.

Exact article quotes require `source_visible_article_text`; exact video/audio quotes require `transcript_and_playback`, a timestamp, and playback verification; paraphrases require `paraphrase_evidence`. Exact quotes and paraphrased observations need a contextual public link in the same paragraph. A playlist-only row supports discovery or an eligible embed, never independent earned-media authority. Use only a selected, public, embeddable YouTube source in a responsive 16:9 `youtube-nocookie.com` handoff with a visible fallback link, descriptive title, lazy loading, no autoplay, and verified metadata. Require `VideoObject` if and only if embedded. No usage ledger or frequency penalty applies in v1. Existing content is evaluated when next rewritten, optimized, or passed through publish readiness.

Treat any `recent_uses_90d` value above 0 as a proof-diversity warning, not only sources marked `overused`. Prefer an approved zero-recent-use source when one fits the same role. If a recently used or overused proof source is still selected, the validation sidecar must explain why no stronger underused approved proof fits.

When selected customer proof appears in public copy, add `Selected Customer Proof Mining` to the validation sidecar. Selector chooses candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. Full details live in `context/aeo-geo-blog-strategy.md`.

Use `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` to check source mix, public-copy gaps, recent use, and overuse before adding proof candidates.

Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.

For review-derived public E-E-A-T stories, automatically run `customer_proof_selector.py` with `--slate --roles experience_story --require-eeat-story`, then run the review story identity gate from the command stack above. Use `context/aeo-geo-blog-strategy.md` as the canonical policy for Review Story Selection, Review Site Theme Selection, and approved quote/rating boundaries.

Use a proof-backed customer/review POV only when it improves the article objective. If no actual person or business POV fits, omit the story. Fictional named personas are prohibited; unnamed workflow scenarios are explanatory only and do not count as E-E-A-T.

When the vault is unavailable, context files may provide clearly labeled editorial fallback context, but they do not become approval authority. Record the connector-unavailable blocker and omit unsupported public claims. Draft bodies may use independently verified public sources and receipt-bound approved proof, but must not mention repo context, context file paths, Source Maps, PAA artifacts, change summaries, schema notes, internal proof-path instructions, or source/proof meta-commentary. Translate proof into audience-facing takeaways, outcomes, or workflow lessons.

Blog drafts and rewrites should use only 1 link per paragraph. Move the second link to a separate paragraph or remove it.

E-E-A-T proof must resolve Experience and Expertise before writing. Discover customer, product, review, competitor, and expert evidence through connector search/read/expand by `resource_id`, and use only approved `vault_claims` records for public proof-sensitive passages. Repo-local proof indexes, link maps, and usage ledgers remain operational selection state and cannot approve a claim or override the connector. Review narratives count as first-hand customer experience when reviewers describe product use, implementation, support, switching, pains, outcomes, or workflows, but generic review-site themes remain VoC research unless a `Review Story Selection` is identity-backed, claim-backed, and link-backed. Capterra theme paragraphs may use `Review Site Theme Selection` only when an approved paraphrase claim and public review URL in the validated receipt support that use. Exact quotes, named reviewers, star ratings, badges, rankings, aggregate ratings, category claims, and metrics require a permitted claim use mode, current source verification, and a public-facing source link in the article body.

Blog research, article planning, writing, analysis, and rewrite workflows must include a Metric Proof Pack for metric-sensitive software, comparison, pricing, cost, ROI, KPI, profit, margin, guide, and vs topics. Resolve the Search log, Approved metric rows, public proof URL or local proof artifact, source-visible Evidence, Status: approved, intended Use, rejected candidates, and not-applicable reason before drafting or publishing.

Blog research, article planning, writing, analysis, and rewrite workflows must include a Customer Proof Pack in the validation sidecar. Keep detailed proof policy in `context/aeo-geo-blog-strategy.md`; command docs should carry the selector command, guard command, and source-specific overuse rule only.

Every writer and rewriter output must include at least 1 contextual down-funnel internal link to `https://www.simprogroup.com/industries`, `/industries/...`, `/solutions/...`, or `/features/...` from `context/internal-links-map.md`. Prefer a specific industry page when the intent is clear, the industries hub for broad trades topics, a solution page for category/workflow topics, and a feature page for feature/workflow topics. Anchor text must match the destination keyword or an approved anchor example.

Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough; use "accounts receivable follow-up with Fast Cash" instead of "Fast Cash."

## Context Files

`context/` contains downstream mirror/fallback guidelines for content generation when the Obsidian vault is unavailable:
- `brand-voice.md` - Fallback mirror for tone and messaging pillars when the vault is unavailable
- `style-guide.md` - Fallback mirror for grammar and formatting standards when the vault is unavailable
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
