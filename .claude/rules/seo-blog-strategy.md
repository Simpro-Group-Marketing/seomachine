# Production SEO Blog Strategy Contract

All new or changed Simpro blogs, rewrites, and optimizations are planned in the research brief and the production BOM spec (`simpro-production-bom-spec/v1`), built into the production BOM (`simpro-production-bom/v1`) by `python -m data_sources.modules.production.bom_build`, and released by `python -m data_sources.modules.production.release`. The BOM build and the release are the executable record. Earlier plan and sidecar artifacts (`simpro-blog-editorial-plan/v2` objects and `blog-strategy-contract/v1` blocks) remain readable history only and gate nothing. Canonical policy lives in `context/aeo-geo-blog-strategy.md`.

## Verified Commercial Destination

`context/commercial-pillar-index.json` is the only executable source for approved commercial pillar destinations. Validate it before planning:

```powershell
python data_sources/modules/commercial_pillar_index.py validate --index context/commercial-pillar-index.json
```

Every connector-bound Simpro blog requires exactly 1 commercial pillar. Select a specific industry page for a vertical topic, a solution page for a category or cross-workflow topic, or a feature page for a capability-led topic. Use the industries hub only when no specific verified destination fits, and record why in the research brief. A blog or blog hub cannot be the commercial pillar; it may be an optional informational supporting link.

The BOM build enforces the destination. The spec carries the pillar as a `links` entry with `kind: commercial_pillar`, `priority: must`, and a `destination_id`. The build refuses the BOM unless a connector-bound spec has exactly one such link (a nonconnector spec has at most one), the `destination_id` resolves to a record for the spec's `brand` and `market` that passes index validation, the link `url` equals that record's canonical URL exactly, and the planned anchor contains the record's main keyword as one contiguous phrase.

At release, coverage blocks when the article does not link the canonical URL in its body or when no occurrence uses the planned anchor after whitespace, emphasis, punctuation, case, and HTML-entity normalization. Additional natural anchor variants remain allowed after the planned occurrence. Hidden links do not count: links in comments, code, and frontmatter are blanked before checking, and an image link never counts as the pillar link. The commercial pillar counts toward the internal-link total. It never overrides vault brand language, availability, named-feature, proof, FAQ, or source-routing rules.

Editorial guidance that no gate checks, recorded in the research brief:

- Link the exact canonical URL: no tracking parameters, fragments, or redirects, and never a bare URL or a generic anchor such as "click here". Coverage compares link identities after `canonicalize_link_identity` drops tracking parameters and fragments, so no gate catches a tracked or fragment variant of the canonical URL.
- The article primary keyword must differ from the destination main keyword. Exact collisions are a planning defect. Containment needs SERP evidence showing different intent and content type.
- Place the pillar link in the H2 the brief plans for it.
- The Semrush database and its freshness, the canonical domain, and the destination's title evidence must agree with the article brand and market. Current US evidence supports US decisions only. Do not infer missing feature keywords or regional metrics.
- `update_existing` and `consolidate` cannibalization decisions prevent a new article.

## Research Brief

The research brief carries the search strategy, commercial strategy, and lifecycle decisions that `/research` (or `/analyze-existing` findings for a rewrite) makes: searcher task, intent class, funnel stage, dominant and selected content type, format decision, the commercial pillar and cannibalization decision with the overlapping URLs checked, and the lifecycle. The SERP evidence, page-1 coverage map, PAA artifact, and Semrush keyword decision are bound into the BOM by path and sha256; the build refuses the BOM when a required artifact is missing.

### Lifecycle

Record the volatility and the next review date in the brief. High-volatility pricing, regulation, product-status, comparison, and statistics-led articles should be reviewed within 90 days. Standard articles should be reviewed within 180 days. Keep the GSC, GA4, Semrush, and AI-citation evidence lanes separate. Use `unavailable: reason` or `not_applicable: reason`; never convert unavailable data to zero or claim improvement without dated evidence. These review windows are editorial guidance; no gate checks them.

## Claim-Level Source Quality

A public fact reaches the article only as a BOM fact. The build admits a fact only when its exact quote is on the live page at build time, the quote supports the claim, and every number in the claim appears in the quote. The release re-verifies every linked fact quote, blocks a material number that no BOM fact or proof item linked in the same paragraph supports, and blocks a claim that cites a source outside the BOM.

Editorial guidance for choosing facts: statistics need an original source; regulations and standards need official sources; competitor-owned evidence cannot support a neutral verdict, recommendation, or FAQ; historical or undated evidence needs a scoped freshness decision in the brief. The release enforces the FAQ part: the AEO scorer's FAQ proof check prohibits competitor-owned FAQ sources. BOM facts never bypass approved customer proof, vault receipts, or named-feature requirements.

## Metadata and Schema Handoff

The article frontmatter needs a valid `last_updated: YYYY-MM-DD` that is not later than the release date; the AEO scorer's metadata check blocks a missing, invalid, or future date. Missing author passes. A verified author is an optional Expertise signal; any author, reviewer, or credential claim remains proof-gated.

`schema_notes` is a checked CMS handoff, not rendered implementation. The BOM spec's `schema_notes` must use the allowed vocabulary, and the AEO scorer's schema check reads the article frontmatter `schema_notes`: both use the exact entries in `.claude/rules/blog-schema.md` (always `BlogPosting`, `BreadcrumbList`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`; `FAQPage` plus `Question and Answer inside FAQPage` only when visible FAQs exist; `Person as author` only when a named author exists; `VideoObject` if and only if a supported video is embedded). The scorer also accepts one optional canonical `ItemList` note for a comparison of tools (`data_sources/modules/schema_item_list.py`), with `item_list_entries` listing the same count; it goes in the article frontmatter only, because the BOM spec vocabulary does not carry it. Frontmatter `title` is effectively required: coverage blocks a title it cannot read and a title without the primary keyword. Schema notes must never be reported as rendered JSON-LD implementation.

## Protected Gates and Scope

The production release is the only release gate: BOM rebuild, truth, coverage, and the three score gates. WordPress and Grav publishing remain downstream of publish readiness. There is no permanent warning-only or publisher bypass. The context binding, URL, proof, vault, FAQ, PAA, capsule, early-artifact, answer-withholding, internal-link-count, Fred authority, and 85/90 score policies in `context/aeo-geo-blog-strategy.md` still apply; the release enforces each one its BOM build, truth, coverage, or scorer checks cover.

This contract does not add `llms.txt`, universal IndexNow, fixed AI-citation targets, publishing quotas, speculative ranking guarantees, rendered-schema automation, an Original Contribution Plan, or media accessibility work.
