# Simpro Source Routing Map

**Purpose:** Decide which content inputs must come from the Simpro vault connector and which inputs may come from repo-local `context/` files.
**Use when:** Planning, writing, rewriting, optimizing, or validating Simpro blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decisions.
**Owns:** Source-routing decisions between the Simpro vault connector, public sources, and repo-local context.
**Does not own:** Public proof approval, metric support, PAA provenance, URL resolution, brand-language wording, or publish scoring.
**Source boundary:** This is a routing contract. It does not make any claim publishable unless the relevant approved claim, public source, or connector receipt also approves it.
**Refresh cadence:** Review when the connector contract, claim registry, or publish-readiness gates change.
**Reference detail:** No separate reference file; routing guidance remains here.

## Routing Matrix

| Data type | Primary source | Repo `context/` role |
|---|---|---|
| Brand voice, audience, ICP, message pillars, tone | Simpro vault connector context resources | `brand-voice.md` and `style-guide.md` are fallback mirrors only, except style mechanics |
| Product, feature, add-on, solution, industry, Lightning language | Simpro vault connector context resources and approved claims when public proof is used | `features.md`, `lightning-positioning.md`, and FSM FAQ files are fallback or seed inputs only |
| Competitor shortlist, Hindsight boundary, battlecard claims | Simpro vault connector context resources and approved claims when public proof is used | `competitor-analysis.md` and battlecard imports are point-in-time fallback or SEO context only |
| Customer proof, quotes, metrics, review stories, approval status | Simpro vault connector claim registry plus public proof URLs | `customer-proof-index.json`, ledger, and intake CSV are operational selector inputs and cannot override the vault |
| SEO mechanics, AEO/GEO workflow, schema notes, publish gates | Repo `context/` | `aeo-geo-blog-strategy.md`, `seo-guidelines.md`, and guard modules are the active workflow policy |
| Internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples | Repo `context/` | Dated strategic evidence or calibration only; refresh before treating as current performance truth |
| Public factual/statistical claims | Current public primary source | Sidecar maps proof; neither vault nor repo context alone is enough for public copy unless mapped to public evidence |

## Enforcement Notes

- This matrix is policy guidance, not a second sidecar schema. No separate routing sidecar block is required.
- Enforcement comes from Context Binding plus claim-specific gates. Context Binding validates the request, context pack, receipt, and sidecar binding; claim-specific gates validate public proof, product language, named-feature status, customer evidence, and other governed uses.
- Repo context may own workflow policy, dated SEO evidence, internal-link routing, writing examples, style mechanics, and operational proof selector inputs.
- Repo context cannot override current connector guidance for brand, audience, ICP, product, feature, add-on, solution, industry, Lightning, competitor, Hindsight, customer proof, review-story, quote, metric, or approval-status data.
- Public factual/statistical claims require current public primary sources and a proof map. The vault and repo context can route the work, but neither one alone proves the public claim.
- If the vault connector is unavailable, document the exact blocker in the validation sidecar and generated context binding. Repo-local brand, product, feature, proof, and competitor files may supply labeled editorial fallback context, but they cannot approve public claims; omit unsupported proof until the connector is healthy.
