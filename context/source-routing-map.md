# Source Routing Map

**Category:** source_governance
**Purpose:** Define which work may use repo-local `context/` inputs and which work must use the Simpro Brand Vault connector.
**Use when:** Deciding source authority for Simpro brand work, SEO/AEO inputs, editorial mechanics, CRO mechanics, link routing, proof, or claims.
**Owns:** Source routing boundaries for repo-local context versus vault connector evidence.
**Does not own:** Brand language, product descriptions, proof, approved claims, customer stories, competitor positioning, or article copy.
**Source boundary:** This governance map limits local files to allowed operational categories. It does not create local authority for any Simpro brand or proof content.
**Refresh cadence:** Review when connector contracts, context categories, or publish-readiness gates change.
**Reference detail:** Machine-readable policy lives in `context/context-policy.json`.

## Boundary

The Simpro Brand Vault connector is the exclusive source for Simpro brand-related information, including voice, tone, audience, ICP, messaging, terminology, product and feature language, solution and industry language, competitor positioning, proof, reviews, metrics, ebooks, customer stories, E-E-A-T sources, approved claims, and writing exemplars.

Repo-local `context/` files may support only these functions:

- SEO/AEO strategy and evidence
- Brand-neutral editorial strategy and article mechanics
- Generic CRO best practices
- Link maps, site architecture, and commercial SEO routing
- Source and URL governance for those functions

Local files may identify Simpro URLs, keywords, markets, measurement dimensions, internal-link destinations, or commercial SEO anchors. They do not authorize wording that describes Simpro, its products, its proof, or its customers.

## Routing Matrix

| Work type | Active source | Repo-local role |
|---|---|---|
| Brand voice, tone, ICP, audience, messaging, terminology | Brand Vault connector | No local fallback |
| Product, feature, add-on, solution, industry, and Lightning language | Brand Vault connector resources plus approved claims when proof-sensitive | URL and link-route discovery only |
| Competitor positioning or comparative product claims | Brand Vault connector plus approved claim/public-source mapping | Dated SEO/SERP evidence only |
| Customer proof, quotes, metrics, reviews, ebooks, customer stories, E-E-A-T, approved claims | Brand Vault connector claim search, context pack, and receipt | Operational usage ledger only, stored outside `context/` |
| SEO/AEO strategy, keywords, intent, FAQ/PAA inventory, citation targeting | Repo-local `context/` plus dated external evidence | Active workflow input |
| Internal links, site architecture, commercial pillar routing | Repo-local `context/` | May choose destination and anchor; cannot supply product description |
| Generic CRO mechanics | Repo-local `context/` | Framework guidance only; no brand-specific test/result claims |

## Failure Behavior

For Simpro-owned or Simpro-signal artifacts, connector unavailability is a blocker. The workflow must not read deleted local brand/proof mirrors or treat any repo-local file as a fallback authority.
