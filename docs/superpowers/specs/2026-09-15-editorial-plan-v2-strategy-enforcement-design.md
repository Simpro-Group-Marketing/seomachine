# Editorial Plan v2 and Strategy Enforcement

## Objective

Make the editorial plan the authoritative pre-writing contract while preserving
the repository's native `/write`, `/rewrite`, and `/optimize` commands as the
only public-copy writers:

`research -> frozen plan -> native writing -> fulfillment evidence -> BOM -> publish readiness`

Python validates contracts, provenance, and release evidence. It does not draft
or semantically rewrite article copy.

## Contract Model

New work uses `simpro-blog-editorial-plan/v2`. Version 1 remains parseable only
as archived evidence and cannot authorize a current BOM or release.

Each v2 contribution contains `contribution_id`, `planned_contribution`,
`purpose`, `evidence_source`, and `target_section`. The plan does not prescribe
the final wording. Each section also records `reader_question`,
`section_payoff`, `bridge_from_previous`, and `bridge_to_next` so the writer
receives a coherent argument rather than independent guardrails.

The plan owns current structured `search_strategy`, `commercial_strategy`, and
`lifecycle` decisions. `evidence_source` is planning provenance only and cannot
satisfy Source Map, claim-registry, vault, or public-citation requirements.

## Metadata

The final title and H1 must match one planned `title_options` value. Meta title
and description must exactly match their planned values. Primary and secondary
keywords and the slug must match after deterministic normalization.

`url_slug` is canonical in v2. The shared metadata reader recognizes legacy
`slug` and `target_url` aliases for archived content, but conflicting aliases
fail release validation. Existing SEO scoring remains authoritative; this work
does not add arbitrary metadata-length rules.

## Fulfillment

After every article-byte change, the native writing command writes
`simpro-blog-plan-fulfillment/v1`. The artifact binds the immutable editorial
plan hash and current article hash, then records one verbatim visible article
excerpt for every planned contribution.

Deterministic validation checks hashes, exact ID coverage, duplicate/extra IDs,
visible text, substantive excerpts, and placement inside the planned section.
Content Analyzer and Editor reviewers assess whether those excerpts fulfill the
planned purposes. Python does not make that semantic judgment.

## BOM and Readiness

`simpro-blog-assembly-bom/v4` binds the fulfillment artifact and commercial
pillar index in addition to existing artifacts. Its editorial-plan summary is
recomputed from the bound plan and includes metadata and structured strategies.
Its editorial fulfillment is recomputed by joining plan contributions to
fulfillment excerpts. Hand-edited summaries, stale hashes, or legacy BOMs fail
current release authorization.

Readiness executes `blog_strategy` and `schema_handoff` through the canonical
ordered gate inventory. The strategy gate receives the captured v2 plan,
article, URL-validation result, context request, and immutable commercial index
bytes. Every declared gate must have an executor.

## Command Ownership

`/research` owns new-article plans and `/analyze-existing` owns rewrite plans.
Writers consume an immutable plan. Plan-level reviewer findings route back to
the owning planning command and create a newly hashed plan instead of silently
mutating it.

All six native workflow commands and their reviewers explicitly consume
`context/blog-editorial-strategy.md`. `context/aeo-geo-blog-strategy.md`
remains authoritative for AEO and proof policy.

## Engineering Constraints

Oversized strategy, source-quality, and BOM modules are split behind compatible
facades. Every added or modified Python source or test file remains at or below
500 physical lines. A diff-aware check enforces that ceiling without claiming
untouched legacy debt is part of this change.

## Verification

Focused tests cover v2 plans, metadata aliases, fulfillment, BOM v4, readiness
gates, and command contracts. Final verification includes the full unit suite,
relevant integration tests, Humanizer snapshot verification, reference scans,
the line-count guard, and `git diff --check`.

