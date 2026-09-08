# Production SEO Blog Strategy Contract

All new or changed Simpro blogs, rewrites, optimizations, analyze-existing passes, and the next publish-readiness pass for an existing blog use `blog-strategy-contract/v1`. The validation sidecar is the executable record. Instructions without a passing guard do not authorize publishing.

## Verified Commercial Destination

`context/commercial-pillar-index.json` is the only executable source for approved commercial pillar destinations. Validate it before planning:

```powershell
python data_sources/modules/commercial_pillar_index.py validate --index context/commercial-pillar-index.json
```

Every Simpro blog requires exactly 1 commercial pillar. Select a specific industry page for a vertical topic, a solution page for a category or cross-workflow topic, or a feature page for a capability-led topic. Use the industries hub only when no specific verified destination fits and document why. A blog or blog hub cannot be the commercial pillar; it may be an optional informational supporting link.

The article `Brand`, `Market`, destination record, canonical domain, title evidence, Semrush database, and Semrush freshness must agree. Current US evidence approves US decisions only. Do not infer missing feature keywords or regional metrics. The article primary keyword must differ from the destination main keyword. Exact collisions fail. Containment requires verified SERP evidence proving different intent and content type. `update_existing` and `consolidate` prevent a new article.

The exact canonical URL must appear as a visible Markdown body link in the planned H2. At least 1 occurrence must use the planned anchor text exactly after whitespace, emphasis, punctuation, case, and HTML-entity normalization; that anchor must contain the indexed main keyword as one contiguous phrase. Bare URLs, comments, code, images, frontmatter, sidecars, tracking parameters, fragments, redirects, unsupported synonyms, and generic anchors do not pass. Additional natural anchor variants remain allowed after the approved occurrence. The commercial pillar counts toward the existing internal-link total. It never overrides vault brand language, availability, named-feature, proof, FAQ, or source-routing rules.

## Required Sidecar Contract

Each section and field appears exactly once. Duplicate sections, duplicate fields, conflicting values, placeholders, unknown enums, stale evidence, and unsupported versions fail closed.

Both the SERP evidence artifact and related-query/PAA artifact must resolve to nonempty files inside this repository; a path string in the sidecar is not evidence by itself.

### Search Intent and Format Decision

- Contract version: blog-strategy-contract/v1
- Primary query or prompt:
- Searcher task:
- Intent class:
- Funnel stage:
- SERP evidence artifact:
- Dominant content type:
- Selected content type:
- Observed SERP features:
- Related-query/PAA artifact:
- Format decision:
- Exception reason:
- Status: ready | blocked

### Commercial Pillar and Anchor Decision

- Contract version: blog-strategy-contract/v1
- Article title:
- Article primary keyword:
- Article intent:
- Destination ID:
- Commercial pillar URL:
- Planned anchor text:
- Planned H2 section:
- Existing overlapping URLs checked:
- Pillar-versus-blog intent difference:
- Cannibalization decision:
- Incoming-link candidates:
- Status: aligned | blocked

Do not copy Semrush metrics into this block. The guard resolves `Destination ID` against the verified index.

### Lifecycle Refresh Record

- Contract version: blog-strategy-contract/v1
- Last-updated date:
- Volatility: high | standard
- Next review date:
- Review command:
- GSC lane:
- GA4 lane:
- Semrush lane:
- AI-citation lane:
- Decision:
- Status:

High-volatility pricing, regulation, product-status, comparison, and statistics-led articles must be reviewed within 90 days. Standard articles must be reviewed within 180 days. Each evidence lane stays separate. Use `unavailable: reason` or `not_applicable: reason`; never convert unavailable data to zero or claim improvement without dated evidence.

## Claim-Level Source Quality

Each public `Source Map` claim row requires `Claim`, `Claim type`, `URL`, `Evidence`, `Source class`, `Original-source status`, `Source date`, `Checked date`, `Claim fit`, `Freshness decision`, `Freshness reason`, `Status`, and `Intended use`. Public claim fit must be `direct`. Statistics require an original source; regulations and standards require official sources. Competitor-owned evidence cannot support a neutral verdict, recommendation, or FAQ. Historical or undated evidence needs a scoped freshness decision. Source Map never bypasses Customer Proof Pack, Metric Proof Pack, FAQ Proof Map, vault receipts, or named-feature requirements.

## Metadata and Schema Handoff

A valid `Last Updated: YYYY-MM-DD` is required and cannot be future-dated. Missing author passes. A verified author is an optional Expertise signal; any author, reviewer, or credential claim remains proof-gated.

`schema_notes` is a checked CMS handoff, not rendered implementation. Always include `BlogPosting`, `BreadcrumbList`, `ImageObject`, and Organization as publisher reference. Include `FAQPage` plus nested Question/Answer only when visible FAQs exist. Include Person only when a verified author exists. Include `VideoObject` if and only if a video is embedded. Schema notes must never be reported as rendered JSON-LD implementation.

## Protected Gates and Scope

`source_quality_guard.py`, `blog_strategy_guard.py`, and `schema_handoff_guard.py` are blocking publish-readiness gates. WordPress and Grav publishing remain downstream of publish readiness. There is no permanent warning-only or publisher bypass. Existing context binding, URL, proof, vault, FAQ, PAA, capsule, early-artifact, answer-withholding, internal-link-count, Fred authority, and 85/90 score rules stay active.

This change does not add `llms.txt`, universal IndexNow, fixed AI-citation targets, publishing quotas, speculative ranking guarantees, rendered-schema automation, an Original Contribution Plan, or media accessibility work.
