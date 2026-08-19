# Cluster Command

Build an evidence-backed topic-cluster strategy with one pillar, distinct supporting articles, an internal-link map, and a creation sequence.

## Usage

`/cluster [topic]`

Examples:

- `/cluster 'field service scheduling'`
- `/cluster 'job costing for trades'`

## Workflow

### 1. Resolve Context

- Resolve the topic, brand, domain, audience, objective, funnel role, and region.
- Use the vault connector workflow only for Simpro-owned or cross-brand-triggered clusters. For AroFlo, BigChange, and ClockShark clusters with no Simpro signal, record the nonconnector reason and use current owning-brand sources.
- Review relevant existing artifacts in `research/`, `context/target-keywords.md`, and `context/internal-links-map.md`.
- Record missing inputs as blockers. Do not inherit a brand, topic, keyword, or metric from examples.

### 2. Gather Search Evidence

- Use current, attributable keyword and SERP evidence from configured sources.
- Record source, query, region, date, and freshness.
- Separate observed metrics from editorial judgment.
- Do not invent search volume, difficulty, rankings, questions, traffic forecasts, or competitors.

### 3. Define Intent Ownership

Adopt the `cluster-strategist` agent role and define:

- one pillar query and Reader Contract
- distinct supporting queries and Reader Contracts
- the reader task and search intent owned by every page
- overlap risks with existing and proposed pages
- merge, differentiate, or reject decisions for conflicting ideas

The number of supporting articles must follow verified opportunity and reader usefulness. Do not create pages to reach a quota.

### 4. Build the Cluster

For the pillar and each accepted supporting article, provide:

- working title
- primary query and verified metrics, when available
- search intent and funnel role
- reader problem and article objective
- evidence-backed content angle
- relationship to the pillar
- required internal links and natural anchor concepts
- priority with stated evidence and assumptions

Use a caller-supplied, intent- and evidence-complete word target only. Never derive a target mechanically from competitor length.

### 5. Create the Link Map and Roadmap

- Map pillar-to-supporting, supporting-to-pillar, and genuinely useful cross-links.
- Include relevant existing pages from the approved inventory.
- Prevent orphan pages, repetitive anchors, and links to unverified routes.
- Sequence work by prerequisite, reader value, evidence strength, and business priority.
- Provide copy-ready `/research` and `/write` commands for accepted pages.

## Output

Save to `research/cluster-strategy-[topic-slug]-[YYYY-MM-DD].md` with:

1. resolved context and evidence ledger
2. executive summary
3. keyword and intent landscape
4. pillar Reader Contract and outline direction
5. supporting-article table
6. cannibalization decisions
7. internal-link matrix
8. phased creation roadmap
9. measurement plan
10. blockers and unresolved evidence

Every numeric value must cite its source and observation date. Every public-facing Simpro, product, proof, or competitor decision must remain within the connector evidence and canonical governance policy.
