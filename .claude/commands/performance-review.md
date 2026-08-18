# Performance Review Command

Turn verified analytics and search evidence into a prioritized content-work queue.

## Usage

`/performance-review [days]`

If `days` is omitted, use 30 days and compare it with the immediately preceding equal-length period. State the final date ranges explicitly.

## Workflow

### 1. Resolve Scope

- Confirm brand, domain, GA4 property, GSC property, region, business objective, conversion definition, and reporting period.
- Use the required vault connector workflow when recommendations affect Simpro blog, product, audience, proof, or competitor decisions.
- Stop or narrow the report when access or scope cannot be verified.

### 2. Retrieve Evidence

Retrieve current observations from the configured sources:

- GA4 for on-site behavior and approved conversions
- Google Search Console for clicks, impressions, CTR, position, pages, and queries
- current keyword or SERP sources only when competitive or market context is required

Record source identifiers, filters, ranges, retrieval time, freshness, and limitations. Never substitute fabricated examples for missing data.

### 3. Run the Performance Agent

Use `.claude/agents/performance.md` to:

- compare like-for-like periods
- identify defensible opportunities and declines
- separate measurement issues from content issues
- prioritize actions using visible inputs and assumptions
- route each action to its owning native command

### 4. Create the Work Queue

For each accepted opportunity include:

- page or query
- observed evidence and source
- interpretation and uncertainty
- action and priority rationale
- workflow handoff
- success measure and review date

Use `/analyze-existing` before prescribing changes to an existing article. Route approved work through `/optimize`, `/rewrite`, `/research`, or `/write` as appropriate. Content changes still require `/scrub` and `/publish-readiness`.

## Output

Save the report to `research/performance-review-[YYYY-MM-DD].md` with:

1. scope and evidence ledger
2. executive findings
3. prioritized opportunity queue
4. page and query detail
5. data-quality and causality limits
6. command handoffs
7. measurement plan

Do not include unsupported forecasts, typical-result claims, guaranteed impact, or invented sample metrics.
