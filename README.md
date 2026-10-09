# SEO Machine (Simpro Group)

Simpro Marketing's Claude Code workspace for **SEO and AEO/GEO blog posts** - research, write, optimize, and publish long-form articles for field-service and trades audiences, with Simpro-specific brand context, first-party analytics, and generative-engine optimization built in.

Fork of [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine), customized for proof-governed Simpro SEO and AEO workflows.

## Where policy lives

This README covers setup and the command index. Every workflow rule has one canonical home:

- [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md) - steering files for Claude Code and Codex, with the full pointer table and non-negotiables
- [context/aeo-geo-blog-strategy.md](context/aeo-geo-blog-strategy.md) - AEO/GEO, proof, vault, citation, link, FAQ, PAA, E-E-A-T, Fred authority, publish-gate, and recovery-loop policy
- [context/blog-editorial-strategy.md](context/blog-editorial-strategy.md) - Reader Contract, editorial plan ownership, story safety, CTA profiles, and Reviewed Humanizer governance
- [.claude/rules/](.claude/rules/) - rule-sized contracts (SEO blog strategy, customer proof, FAQ answer quality, blog schema, repository development, agent governance), mirrored to `.agents/rules/` and `.cursor/rules/` by `python tools/sync_rule_mirrors.py`
- [.claude/commands/](.claude/commands/) - per-command workflow steps; [.claude/agents/](.claude/agents/) - advisory specialist reviewers

## Blog workflow at a glance

Blog writing is native-first. `/write`, `/rewrite`, and `/optimize` create or edit public Markdown. Python modules do not draft, rewrite, or patch article copy in `drafts/`, `rewrites/`, or `published/`; they provide selector evidence, context binding, keyword and SERP evidence, BOM assembly, readiness output, and publisher transport.

`/publish-readiness` is the release owner. Its scorecard is independent:

- Content quality must be 85/100 or higher for blogs.
- SEO quality must clear the 90/100 release floor with zero critical SEO issues.
- SEO quality should target 95/100 when honest, source-safe optimization can improve the artifact.
- AEO/GEO must be 90/100 or higher.

The mandatory scrub, readiness, optimize, and final readiness loop, plus every gate, is defined in `context/aeo-geo-blog-strategy.md` and `.claude/commands/publish-readiness.md`.

## Getting Started

### Prerequisites
- [Claude Code](https://claude.com/claude-code) installed
- Anthropic API account
- Python 3.11 or newer
- Access to the internal `simpro-context-connector` v2.2.0 release

### Installation

1. Clone this repository:
```bash
git clone https://github.com/Simpro-Group-Marketing/seomachine.git
cd seomachine
git status --short
```

2. Install Python dependencies (vault client and MCP adapter, GA4/GSC integrations, DataForSEO client, text analysis, optional clustering, and scraping tools):
```bash
pip install -r data_sources/requirements.txt
```

3. Configure credentials and MCP (Simpro setup):
   - Copy `.env.example` to `.env` and set GA4/GSC/DataForSEO paths (see `CLAUDE.md` for MCP vs Python module credential boundaries)
   - Copy `.mcp.json.template` to `.mcp.json` and adjust paths for your machine
   - Configure `simpro-context@simpro` with its root-only `authority_root`; the Python client and MCP adapter read that plugin authority configuration by default
   - Copy `.claude/settings.local.template.json` to `.claude/settings.local.json`
   - Place GA4 ADC at `credentials/adc.json` and GSC OAuth client secret at `credentials/gsc_client_secrets.json` (see `credentials/.gitkeep` - secrets are gitignored)
   - For the bundled GSC MCP server: `cd mcp-gsc && pip install -r requirements.txt` (see `mcp-gsc/README.md`)

4. Open in Claude Code:
```bash
claude
```

Project-scoped MCP servers feed live data into research and performance workflows:

| Server | Purpose | Credentials |
|--------|---------|-------------|
| `gsc` | Search Console queries, pages, performance overview | `credentials/gsc_client_secrets.json` + OAuth token (`mcp-gsc/`) |
| `analytics-mcp` | GA4 reports and account summaries | `credentials/adc.json` via `GOOGLE_APPLICATION_CREDENTIALS` |

Python module integrations and analysis modules are documented in `data_sources/README.md`. Allowed `context/` files and their categories are registered in `context/context-policy.json`; Simpro brand and proof context comes from the vault connector, as `context/aeo-geo-blog-strategy.md` defines.

### WordPress Integration

Publishing uses the WordPress REST API with a custom MU-plugin that exposes Yoast SEO fields for **simprogroup.com** (or your staging site).

1. Install `wordpress/seo-machine-yoast-rest.php` as an MU-plugin on the WordPress site, or add `wordpress/functions-snippet.php` to the theme's `functions.php`
2. Configure WordPress credentials in `.env`:
   ```
   WORDPRESS_URL=https://www.simprogroup.com
   WORDPRESS_USERNAME=your_username
   WORDPRESS_APP_PASSWORD=your_application_password
   ```

See `wordpress/README.md` and `data_sources/README.md` for setup details.

## Commands Reference

Use slash commands; scripts and MCP calls are implementation details the command runner executes internally. Each command's steps live in `.claude/commands/[command].md`.

| Command | Purpose |
|---------|---------|
| `/research [topic]` | Keyword and competitor research, research brief, and frozen editorial plan in `research/` |
| `/write [topic]` | Native draft in `drafts/` with specialist machine reviews |
| `/rewrite [topic]` | Native rewrite in `rewrites/` with SEO plus AEO/GEO rewrite gates |
| `/analyze-existing [URL or file]` | Content health and AEO/GEO rewrite-readiness audit |
| `/optimize [file]` | Required post-preflight SEO/AEO repair or recorded no-op pass |
| `/scrub [file]` | Read-only diagnostics for invisible Unicode marks, em dashes, and whitespace artifacts |
| `/publish-readiness [file]` | Complete source-artifact gate stack and the sole release verdict |
| `/publish-draft [file]` | Publish an article to WordPress via REST API with Yoast SEO metadata after readiness passes |
| `/performance-review [days]` | Analytics-driven content-work queue |
| `/priorities` | Content prioritization matrix |
| `/content-calendar` | Month-long content calendar mapped to clusters, keywords, and cadence |
| `/cluster [topic]` | Topic cluster strategy with pillar, supporting articles, and linking map |
| `/research-serp [keyword]` | SERP analysis for a target keyword |
| `/research-gaps` | Competitor content gap analysis |
| `/research-trending` | Trending topic opportunities |
| `/research-topics` | Topic cluster research |
| `/research-performance` | No-argument performance queue; `/research-performance [URL-or-path]` writes the target report-and-receipt pair |
| `/research-ai-citations [topic]` | Evidence-bound AI citation audit; it does not predict citation outcomes. Repurposing is optional manual distribution work, not an AI-citation mechanism |
| `/repurpose [article] --final-readiness [attestation] [--canonical-url URL]` | Optional manual, evidence-bound distribution handoff from a sealed article; never posts externally or adds unsupported claims |
| `/landing-write [topic]` | Create a conversion-optimized landing page |
| `/landing-audit [file]` | Audit a landing page for CRO issues |
| `/landing-research [topic]` | Research competitors and positioning for a landing page |
| `/landing-competitor [URL]` | Deep competitor landing page analysis |
| `/landing-publish [file]` | Publish a landing page to WordPress |

The `grav-publish` skill publishes a finished article to Grav CMS on the GitHub `dev` branch. Marketing skills (copywriting, CRO, strategy, channels, SEO, analytics) live in `.claude/skills/`.

## Authors

See [AUTHORS.md](AUTHORS.md) for the current Simpro Group Marketing repo authors and maintainers.

## Contributing (Simpro fork)

- Internal work: use the active repository branch shown by `git branch --show-current` on [Simpro-Group-Marketing/seomachine](https://github.com/Simpro-Group-Marketing/seomachine)
- Upstream fixes: consider PRs to [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine) when generic
- `examples/castos/` shows the original Castos template pattern from the open-source repo

## License

MIT License - see [LICENSE](LICENSE). Original development by Castos; Simpro Group Marketing maintains this fork for trades/FSM blog workflows.

## Credits

Built with [Claude Code](https://claude.com/claude-code) by Anthropic.

Upstream project: [TheCraigHewitt/seomachine](https://github.com/TheCraigHewitt/seomachine) (originally developed for Castos). This fork is maintained by Simpro Group Marketing for trades and field-service SEO/AEO content.
