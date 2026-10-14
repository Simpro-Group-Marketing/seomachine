# Publish Readiness Command

Use `/publish-readiness [article]` to release-check a blog in `drafts/` or `rewrites/`. The command runs the one-pass production release and reports its verdict. Consume `context/blog-editorial-strategy.md` for editorial policy and `context/aeo-geo-blog-strategy.md` for AEO, proof, production BOM, and release policy.

## Ownership

`/publish-readiness` is the release owner and the sole release verdict. It validates, scores, and writes the release record. It must not draft, rewrite, or patch public blog Markdown, and it never edits the production BOM spec. Machine reviewers are advisory; no human approval step exists.

For public copy changes, return the blocking findings and priority fixes to `/write`, `/rewrite`, or `/optimize`. For a refused BOM rebuild, return the refusal lines to `/research`, which fixes the BOM spec or the research inputs.

## Inputs

The command needs only the article path. Every other input derives from it (see `data_sources/modules/production/layout.py`):

- the article `drafts/<slug>-<date>.md` or `rewrites/<slug>-<date>.md`;
- the run state `research/runs/<slug>-<date>.json`, which holds the production `run_id` and the hash of the BOM the pipeline last wrote;
- the BOM spec `research/production-bom-spec-<slug>-<date>.json`, written by `/research`;
- the production BOM `research/production-bom-<slug>-<date>.json` (schema `simpro-production-bom/v1`), built by `/research`;
- the research artifacts the BOM binds: Semrush keyword decision and shortlist, SERP evidence and page-1 coverage map, PAA artifact when the spec selects questions, customer-proof selector evidence, and the context pack and receipt for connector-bound work.

A missing article, spec, or BOM is an operational stop (exit `2`) that names the expected path. When the last build refused the BOM, the message names the `.refused` file and the build command `/research` runs.

## Usage

The command runs:

```powershell
python -m data_sources.modules.production.release "[article]" [--workers N] [--workspace-root DIR]
```

`--workers N` overrides the `SEOMACHINE_RELEASE_WORKERS` environment variable, which defaults to `2`. With `1` worker everything runs sequentially in one process with no pools. Keep the default on low-memory machines.

## Phases

1. **Refresh selector evidence.** When the spec names proof or this article's selector evidence exists, the release re-runs the selector that wrote it, with the inputs recorded in the evidence, so the evidence is same-day. The BOM's current selections are pinned, so a moved usage ledger cannot re-choose the proof; a pinned proof the selector no longer offers (it lost approval or eligibility) refuses the BOM (exit `1`, check `bom_refused`). A connector article refreshes the vault-bound selector evidence; a nonconnector AroFlo, BigChange, or ClockShark article refreshes `simpro-nonvault-customer-proof-selector-evidence/v1` and never runs the vault-dependent customer-proof selector. A refresh failure, such as a vault outage, is exit `2`.
2. **Rebuild the BOM.** The builder re-verifies every fact quote on its live page and re-checks every proof item against approved claims and the selector evidence. A fact whose page is merely unreachable keeps its earlier verification only when the previous BOM is the file the pipeline wrote; truth then warns. A fact verified from a Chrome capture never carries forward this way. A fact page that blocks the live check (403, 429, 503, timeout, or connection error) and carries a Chrome capture in the spec is verified from that capture, dated by its `captured_at`; truth warns with the capture date (`captured_at`) and `link_resolution` only warns for that URL. An edited capture file, or one older than 90 days, refuses the rebuild; re-capture the page in Chrome. A lost quote, a gone page, or unapproved proof refuses the rebuild (exit `1`, check `bom_refused`). An operational rebuild failure, such as an unusable commercial pillar index or vault, stops with exit `2` (check `bom_build_failed`). Both move the BOM aside as `.refused`, so it cannot be released until `/research` builds it again.
3. **Check and score concurrently.** Truth and coverage run in a thread pool while the scorer runs:
   - **Truth (blocking):** links resolve; every claim that needs a citation cites a BOM fact URL whose quote is still on the page; numbers in a claim appear in its fact's quote; customer and review quotes match a BOM proof item verbatim; every FAQ question is a BOM PAA question; and the AI copy linter's `editorial_process_leakage` rule finds nothing. Other lint findings and off-BOM links are warnings.
   - **Coverage:** every `must` item is present (section headings, the commercial pillar link with its planned anchor, `must` facts and proof, `must` PAA questions in the FAQ, and the primary keyword in the title, H1, and first 100 words). A missing `must` item blocks; a missing `should` item warns.
   - **Scores (blocking):** the existing content scorer, fed a proof view rendered only from the BOM, yields the three gates below.
4. **Record.** The release writes one `release-record.json` in the next unused directory `research/releases/<slug>-<date>-<run8>-<n>/`, where `<run8>` is the first 8 characters of the run id. Every run that fails after the refresh also writes a failing record, so an older pass never stays the latest record.

The AI copy linting check treats `editorial_process_leakage` as a hard public-copy blocker. Body copy that contains brief rationale, source-fit notes, feature-omission reasoning, command status, or workflow explanation blocks the release even if Content, SEO, and AEO/GEO scores otherwise pass. Return the blocker to `/write`, `/rewrite`, or `/optimize`; `/publish-readiness` must not patch the article.

## Score thresholds

The record's `scores.gates` holds one independent pass/fail gate per score:

- `content_quality`: score, threshold 85, passed.
- `seo_quality`: score, release-floor threshold 90, passed, and `critical_issue_count`, which must be 0. The 95/100 SEO optimization target is advisory and never blocks.
- `aeo_geo`: score, threshold 90, passed, plus `failed_checks` and `failed_rules`.

`scores.passed` is true only when all three gates pass. `scores.priority_fixes` lists the scorer's fixes for `/optimize`.

## Exit codes

- `0`: passed. The latest record has `passed: true`.
- `1`: blocked. The BOM rebuild was refused, a truth or coverage finding blocks, or a score gate failed. A release-time 403 or 429 on a proof or pillar URL (Capterra often refuses automated clients) blocks as `link_resolution`; resolve it by loading the page through the Chrome connector and adding that exact URL to `context/url-verification-allowlist.json` (an entry with `verified_via: chrome_connector`, the page title, and an on-page snippet), which the URL validator reads, then release again. Never allowlist a 404 or 410. A fact page that blocks at release is handled by its Chrome capture (see `/research`), not by the allowlist.
- `2`: operational or argument error: missing BOM or spec, bad article path, selector refresh failure, stale evidence at scoring, the article edited during the run, or an unexpected error.

## Release record

`release-record.json` uses schema `simpro-release-record/v1` and holds:

- `run_id` and `created_at`;
- `article` and `bom`: path and sha256 of the exact bytes checked;
- `spec` and `evidence`: path and sha256 of the BOM spec and every artifact the BOM binds;
- `findings`: one row per finding with `check`, `severity` (`block` or `warn`), `message`, and `line`;
- `blocks` and `warns` counts;
- `scores`: `content`, `seo`, `seo_critical`, `aeo_geo`, `priority_fixes`, `passed`, and `gates` (null when the run stopped before scoring);
- `passed`: true only with zero blocking findings and all three score gates passed;
- `workers`.

## Latest record

Only the latest release record counts: it must have passed, and the article, BOM, spec, and every bound artifact, including each fact's Chrome capture receipt, must still match the hashes it recorded. Any edit after a pass therefore needs a new release.

## Usage ledger

Release never writes `config/customer-proof-usage-ledger.json`; record the customer-proof use in `config/customer-proof-usage-ledger.json` before final handoff, as `.claude/rules/customer-proof.md` requires.

## Output

Report:

- Overall pass or blocked, with the exit code and the record path.
- Every blocking finding with its check, line, and message.
- Content score and threshold 85.
- SEO score, release floor 90, critical issue count, and whether the advisory 95 target is met.
- AEO/GEO score, threshold 90, and failed checks.
- Warning count, scorer priority fixes, and the next owning command.

If the run stopped before scoring, report `scores: unavailable` and the exact stop reason. Missing scores are a workflow blocker unless the release stopped before scoring.

If the release blocks, do not mutate article copy inside this command. Return the root cause to `/optimize`, `/write`, or `/rewrite`, then release again. Final handoff must include the final `/scrub` result and separate Content, SEO, and AEO/GEO scores from the latest release record.

For detailed proof, PAA, FAQ, schema, customer proof, E-E-A-T, named feature, and vault language policy, use `context/aeo-geo-blog-strategy.md`.
