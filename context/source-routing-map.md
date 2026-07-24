# Simpro Source Routing Map

**Purpose:** Decide which content inputs must come from the Simpro Brand Context LLM wiki and which inputs may come from repo-local `context/` files.
**Use when:** Planning, writing, rewriting, optimizing, or validating Simpro blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decisions.
**Owns:** Source-routing decisions between the Obsidian vault, public sources, and repo-local context.
**Does not own:** Public proof approval, metric support, PAA provenance, URL resolution, brand-language wording, or publish scoring.
**Source boundary:** This is a routing contract. It does not make any claim publishable unless the relevant proof, public source, or vault route also approves it.
**Refresh cadence:** Review when the vault structure, proof indexes, or publish-readiness gates change.
**Reference detail:** No separate reference file; routing guidance remains here.

## Routing Matrix

| Data type | Primary source | Repo `context/` role |
|---|---|---|
| Brand voice, audience, ICP, message pillars, tone | LLM wiki vault | `brand-voice.md` and `style-guide.md` are fallback mirrors only, except style mechanics |
| Product, feature, add-on, solution, industry, Lightning language | LLM wiki vault | `features.md`, `lightning-positioning.md`, and FSM FAQ files are fallback or seed inputs only |
| Competitor shortlist, Hindsight boundary, battlecard claims | LLM wiki vault | `competitor-analysis.md` and battlecard imports are point-in-time fallback or SEO context only |
| Customer proof, quotes, metrics, review stories, approval status | LLM wiki vault plus public proof URLs | `customer-proof-index.json`, ledger, and intake CSV are operational selector inputs and cannot override the vault |
| SEO mechanics, AEO/GEO workflow, schema notes, publish gates | Repo `context/` | `aeo-geo-blog-strategy.md`, `seo-guidelines.md`, and guard modules are the active workflow policy |
| Internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples | Repo `context/` | Dated strategic evidence or calibration only; refresh before treating as current performance truth |
| Public factual/statistical claims | Current public primary source | Sidecar maps proof; neither vault nor repo context alone is enough for public copy unless mapped to public evidence |

## Required Sidecar Block

Every Simpro blog, rewrite, optimization, or publish-readiness workflow must add `Source Routing Decision` to the validation sidecar. The `source_routing_guard.py` publish gate fails when the block is missing, incomplete, or lists repo context as the primary source for vault-first data.

```markdown
## Source Routing Decision
- Article title: [title]
- Vault-sourced data types: [Brand voice, audience, ICP, message pillars, tone; product/feature/add-on/solution/industry language; competitor shortlist or Hindsight boundary; customer proof, quotes, metrics, review stories, approval status; or none]
- Repo-context-sourced data types: [SEO mechanics, AEO/GEO workflow, schema notes, publish gates; internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples; style mechanics; operational proof indexes]
- Vault routes checked: AGENTS.md; wiki/cache/hot.md; wiki/Brand Graph Index.md; [smallest relevant wiki/source/raw pages]
- Repo context files checked: [context files used, or none]
- Fallback context use: none | [repo-local fallback plus vault-unavailable blocker]
- Conflicts found: none | [conflict and resolution]
- Status: aligned
```

## Enforcement Notes

- Repo context may own workflow policy, dated SEO evidence, internal-link routing, writing examples, style mechanics, and operational proof selector inputs.
- Repo context cannot override current vault guidance for brand, audience, ICP, product, feature, add-on, solution, industry, Lightning, competitor, Hindsight, customer proof, review-story, quote, metric, or approval-status data.
- Public factual/statistical claims require current public primary sources and a proof map. The vault and repo context can route the work, but neither one alone proves the public claim.
- If the vault is unavailable, document the exact blocker in `Fallback context use`; otherwise, repo-local brand, product, feature, proof, and competitor files remain fallback mirrors or seed inputs only.
