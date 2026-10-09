# Quick Start Guide

Get SEO Machine running with the current Simpro vault-only source boundary.

## Step 1: Install Dependencies

```bash
pip install -r data_sources/requirements.txt
```

## Step 2: Confirm Source Boundaries

Every file under `context/` must be registered in `context/context-policy.json` and belong to one of the allowed local categories:

- SEO/AEO strategy and evidence
- Brand-neutral editorial mechanics
- Generic CRO best practices
- Link maps, site architecture, and commercial SEO routing
- Source and URL governance

Simpro brand voice, messaging, product language, proof, customer stories, reviews, ebooks, E-E-A-T sources, competitors, approved claims, and writing exemplars come from the Brand Vault connector, not local context files.

Useful local setup files:

- `context/internal-links-map.md` - link-routing data only
- `context/target-keywords.md` - keyword and market records only
- `context/aeo-geo-blog-strategy.md` - SEO/AEO workflow and proof-gate mechanics
- `context/cro-best-practices.md` - generic CRO framework guidance

## Step 3: Create Your First Article

```bash
# Open in Claude Code
claude-code .

# Research a topic
/research [your topic]

# Review the research brief in /research/

# Write the article
/write [your topic]

# Check /drafts/ for the article and validation artifacts
```

## To Publish

1. Review the article and validation sidecar.
2. Run `/scrub`, `/publish-readiness`, `/optimize`, a post-edit `/scrub`, and final `/publish-readiness`.
3. Confirm final readiness evidence before CMS handoff.

## To Improve Quality

- Refresh SEO/AEO and link-routing records when evidence changes.
- Retrieve current brand, proof, product, and writing-exemplar guidance from the Brand Vault connector.
- Map more internal links in `context/internal-links-map.md`.

## Common Commands

```bash
/research [topic]
/write [topic]
/rewrite [topic]
/analyze-existing [URL]
/optimize [file]
/scrub [file]
/publish-readiness [file]
/research-serp [keyword]
/performance-review
/priorities
```

## Health Checks

```bash
python -m data_sources.modules.context_boundary_guard --workspace-root . --fail-on error
python tools/humanizer_upstream.py verify
```
