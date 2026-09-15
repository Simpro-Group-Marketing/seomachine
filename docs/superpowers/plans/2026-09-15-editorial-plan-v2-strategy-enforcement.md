# Editorial Plan v2 and Strategy Enforcement Implementation Plan

> Execute in the isolated worktree with TDD, focused verification after each
> task, and a scoped review before moving to the next contract boundary.

## Task 1: Versioned Editorial Plan

1. Add focused failing tests for valid v2 plans, archive-readable v1 plans,
   contribution IDs, section throughlines, placeholders, strategy structures,
   statuses, dates, and cross-field agreement.
2. Add v2 constants and version-aware dispatch under `editorial_plan/` while
   preserving v1 parsing.
3. Require v2 in current BOM construction and release-readiness entry points.
4. Run the focused editorial-plan tests.

## Task 2: Metadata Binding

1. Add failing tests for title/H1 options, exact meta values, normalized
   keywords, canonical slug, legacy aliases, and alias conflicts.
2. Add one shared metadata-alias parser and use it from final-article and
   publishable-Markdown validation.
3. Confirm WordPress and Grav payload validation use the shared canonical slug.
4. Run focused metadata and publisher tests.

## Task 3: Plan Fulfillment

1. Add failing tests for valid free wording, stale hashes, missing/extra/
   duplicate IDs, hidden excerpts, and wrong-section excerpts.
2. Implement `simpro-blog-plan-fulfillment/v1` parsing and deterministic
   article validation in a focused module.
3. Add writer/reviewer command contracts requiring regeneration after article
   changes and semantic assessment by Content Analyzer and Editor.
4. Run focused fulfillment and command-reference tests.

## Task 4: BOM v4

1. Split oversized BOM contract responsibilities behind compatibility facades
   before editing their behavior.
2. Add failing tests for v4 construction, immutable index/fulfillment bindings,
   computed summaries, tampering, and legacy release rejection.
3. Implement v4 construction and validation, then thread
   `--plan-fulfillment` through BOM and blog-release CLIs/APIs.
4. Run focused BOM and release tests.

## Task 5: Strategy and Schema Gates

1. Split oversized strategy and source-quality guards into focused packages
   with compatibility facades.
2. Add failing readiness tests for all commercial rules, schema handoff, and
   the invariant that every declared gate has an executor.
3. Adapt the strategy guard to structured v2 plan decisions and immutable
   captured inputs; retain v1 sidecar parsing for archived inspection.
4. Register and execute `blog_strategy` and `schema_handoff` in canonical order.
5. Remove the unused `BLOG_ONLY_GATES` declaration and run focused readiness
   tests.

## Task 6: Workflow Strategy Wiring

1. Add contract tests proving `/research`, `/write`, `/analyze-existing`,
   `/rewrite`, `/optimize`, and six reviewers consume both required strategy
   sources according to their ownership.
2. Update command and agent instructions so planning owns v2, writers preserve
   plan immutability, and fulfillment regenerates after article changes.
3. Add golden new-article and rewrite workflow tests through optimization.
4. Run focused command and integration tests.

## Task 7: Line Ceiling and Final Verification

1. Add a diff-aware physical-line checker for changed Python source and test
   files, with self-tests.
2. Confirm every changed Python file is at or below 500 lines and responsibilities
   remain focused.
3. Run focused suites, all `tests/`, relevant `integration_tests/`, Humanizer
   verification, reference scans, and `git diff --check`.
4. Review the final diff for unrelated churn and complete the feature branch.

