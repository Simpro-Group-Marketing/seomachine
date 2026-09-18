# Site Architecture Inputs

## Purpose

Use these files when an LLM needs to understand Simpro site structure for content clustering around the homepage, industry pages, solution pages, and feature pages.

## Source Files

- Raw sitemap source: `data_sources/site_inventory/sitemaps/simprogroup-sitemap.xml`
- LLM-readable site inventory: `context/site-architecture-map.json`
- Commercial pillar routing: `context/commercial-pillar-index.json`
- Editorial internal-link strategy: `context/internal-links-map.md`

## Ownership

`data_sources/site_inventory/sitemaps/simprogroup-sitemap.xml` owns the raw URL inventory.

`context/site-architecture-map.json` owns the normalized page-type and cluster grouping derived from the raw sitemap. It is market-scoped to AUS based on operator input.

`context/commercial-pillar-index.json` remains the canonical source for verified commercial pillar ownership, keyword routing, market, Semrush evidence, and publish workflow decisions.

`context/internal-links-map.md` remains the editorial guidance layer for link use, anchor examples, and priority flows. It includes older sitemap-derived evidence and should be refreshed before treating its performance notes as current.

## Blog Writing Workflow

Use `context/site-architecture-map.json` during new Simpro blog research, rewrites, optimizations, and cluster or internal-link planning when the article needs homepage, industry, solution, or feature page context.

Read the relevant `content_clusters` group first, then shortlist candidate homepage, industry, solution, or feature URLs and nearby supporting pages from `pages`. After shortlisting, defer final commercial pillar ownership to `context/commercial-pillar-index.json` and final editorial link treatment to `context/internal-links-map.md`.

Do not use the site architecture map for public claims, page performance inference, keyword ownership, Semrush evidence, product claims, customer proof, source mapping, scoring, or publish-readiness decisions.

## Boundary

Do not use the sitemap-derived cluster map as proof of page performance, keyword ownership, product claims, customer proof, or publish readiness. It is a site inventory and clustering input only.
