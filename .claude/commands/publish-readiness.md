# Publish Readiness Command

Run the complete source-artifact gate stack for a blog draft, rewrite, published article artifact, or landing page.

## Ownership

`/publish-readiness` is the release owner. It validates, scores, assembles readiness evidence, and writes readiness/BOM governance artifacts. It must not draft, rewrite, or patch public blog Markdown.

For public copy changes, return the failed gates and priority fixes to `/write`, `/rewrite`, or `/optimize`.

## Usage

```powershell
python data_sources/modules/blog_release.py "[article]" --run-id "[uuid]" --proof-sidecar "[sidecar]" --editorial-plan "[plan]" --plan-review "[plan-review]" --article-review "[article-review]" --keyword-decision "[keyword-decision]" --scrub-receipt "[scrub-receipt]" --serp-evidence "[serp-evidence]" --stage-receipt "[receipt]" --workflow-mode "[new|rewrite]" --assembly-date "[YYYY-MM-DD]" --output-dir "research/releases/[slug]-[date]-[run-id]"
```

The first wrapper run intentionally omits optimizer evidence. After it writes `pre-bom-report.json`, `provisional-bom.json`, and `preflight-readiness.json`, it starts an `/optimize` recovery handoff and returns `0` with phase `optimization_started`. When preflight readiness passes, the wrapper also writes `preflight-readiness-stage-receipt.json` and opens `optimization-state.json` from that predecessor receipt. When preflight readiness blocks before a passed receipt exists, the wrapper writes `optimization-recovery.json` without minting a fake stage receipt; `/optimize` repairs the blocker, then the wrapper runs again for the required initial scorecard. This is not final release approval.

After `/optimize`, rerun the wrapper with the post-optimization scrub receipt, post-optimization stage receipts, the optimizer artifact, and the prior preflight readiness output:

```powershell
python data_sources/modules/blog_release.py "[article]" --run-id "[uuid]" --proof-sidecar "[sidecar]" --editorial-plan "[plan]" --plan-review "[plan-review]" --article-review "[article-review]" --keyword-decision "[keyword-decision]" --scrub-receipt "[post-optimization-scrub-receipt]" --serp-evidence "[serp-evidence]" --stage-receipt "[receipt]" --optimizer-output "[optimizer-output]" --prior-preflight-readiness "[preflight-readiness]" --workflow-mode "[new|rewrite]" --assembly-date "[YYYY-MM-DD]" --output-dir "research/releases/[slug]-[date]-[run-id]-final"
```

The final wrapper run writes `pre-bom-report.json`, `provisional-bom.json`, `preflight-readiness.json`, `preflight-readiness-stage-receipt.json`, `final-bom.json`, `final-readiness.json`, and `final-readiness-stage-receipt.json` in a new run-specific release directory. Exit `0` with phase `final_readiness` means final readiness passed and its receipt persisted. Exit `0` with phase `optimization_started` means the wrapper began the required optimization recovery run and final readiness is still pending. Exit `1` means a policy, evidence, score, optimization, or readiness blocker that could not be advanced automatically. Exit `2` means invalid arguments, partial optimizer evidence, reused output directory, collision, unreadable input, or operational failure.

A Semrush UI timeout/reset is `blocked_semrush_ui_refresh`; rerun the authenticated main Chrome Semrush UI workflow and do not substitute Semrush API, MCP, stale exports, or estimates.

Omit context request/pack/receipt and Fred authority evidence when Context Binding classifies the final article as nonconnector and the sidecar records the not-applicable rationale. For nonconnector AroFlo, BigChange, and ClockShark articles with no Simpro signal, supplied vault-dependent customer-proof or Fred artifacts are blockers rather than supporting evidence. If approved non-vault customer proof appears, require matching `simpro-nonvault-customer-proof-selector-evidence/v1`; otherwise omit customer-proof selector evidence.

## Gate stack

The runner enforces artifact identity, Context Binding, Blog Assembly BOM, public artifact checks, AI copy linting, URL validation, public research link checks, Metric Proof Pack, numeric claim source, conditional FAQ answer quality and FAQ proof, PAA provenance, editorial plan, Semrush keyword decision, source support, branch-applicable customer proof diversity, review story identity, E-E-A-T strength, early artifact, answer withholding, vault brand language, named feature status, branch-applicable Fred authority, input seal, and content scoring.

The AI copy linting gate treats `editorial_process_leakage` as a hard public-copy blocker. Final handoff is invalid when body copy contains brief rationale, source-fit notes, feature-omission reasoning, command status, or workflow explanation, even if Content, SEO, and AEO/GEO scores otherwise pass. Return the blocker to `/write`, `/rewrite`, or `/optimize`; `/publish-readiness` must not patch the article.

## Scorecard

The readiness output must include a `scorecard` with independent pass/fail records:

- `content_quality`: score, threshold 85 for blogs, threshold 75 for landing pages, passed.
- `seo_quality`: score, release-floor threshold 90, advisory target 95, passed, `target_met`, `target_status`, and `critical_issue_count` of 0. Blog readiness fails if the release-floor gate fails.
- `aeo_geo`: score, threshold 90 for blogs, passed. Blog readiness fails if this gate fails.

A passed blog readiness result is invalid if any scorecard gate fails, if SEO has critical issues, or if the top-level content/AEO scores disagree with the scorecard.

If an upstream gate blocks scoring, report `scorecard: unavailable` and the exact blocking gate instead of leaving the score field ambiguous. Missing scores are a workflow blocker unless a pre-scoring gate blocked readiness.

## Output

Report:

- Overall pass/fail.
- One row per gate with error and warning counts.
- Content score and threshold.
- SEO score, release floor, advisory target, target status, and critical issue count.
- AEO/GEO score and threshold.
- Priority fixes and the next owning command.

If readiness fails, do not mutate article copy inside this command. Return the root cause to `/optimize`, `/write`, or `/rewrite`.

For new or changed blogs, the caller must run `/optimize` after the first readiness scorecard or exact non-scoring blocker, then rerun `/scrub` and `/publish-readiness` after any article-byte change. Final handoff must include the final scrub result and separate Content, SEO, and AEO/GEO scores or the exact pre-scoring blocker.

For detailed proof, PAA, FAQ, schema, customer proof, E-E-A-T strength, Fred authority, named feature, and vault language policy, use `context/aeo-geo-blog-strategy.md`.
