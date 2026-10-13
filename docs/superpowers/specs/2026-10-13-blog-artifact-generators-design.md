# Blog Artifact Generators and Release Contract v5 Design

Date: 2026-10-13
Status: approved in brainstorming; awaiting written-spec review
Parent plan: `~/.claude/plans/plan-fixes-use-superpowers-glittery-journal.md`, Phase 5 sub-project 5B

## Problem

A blog release needs about 25 input artifacts. Only the context artifacts, SERP evidence (DataForSEO and Playwright collectors), the PAA artifact, and stage receipts have a generic generator. Everything else was produced by per-blog `scripts/build_<slug>_*.py` files in which Claude wrote judgment as Python literals and hand-computed hashes and bindings. Those scripts were deleted from `main` on 2026-10-08 (Task 14), so a new blog currently has no supported way to produce its release inputs. Two required artifacts are ceremony: agent-output files are hashed but never validated, and the old builders filled machine reviews from guard results ("completed, 0 findings").

## Goal and success criteria

- A new or rewritten blog reaches `final_readiness` with zero new Python files: Claude writes judgment-only data files and runs generic generators, then `python -m data_sources.modules.blog_release <article>`.
- No generator emits a claim that code did not verify.
- Every guard, proof boundary, the stage-receipt chain, the 85/90/90 thresholds, and `/publish-readiness` as the sole verdict are unchanged.
- Existing v4 releases stay archive-readable without rewriting any artifact.

## Out of scope

- Sub-project 5A (honest capture recorder): keyword decision, Semrush and Chrome-connector SERP captures, Chrome-connector PAA captures.
- Sub-project 5C (one-pass release for the no-edit path).
- Research-artifact contents and retention; CI (connector-free by design).

## Section 1: release contract v5

- New schema `simpro-blog-assembly-bom/v5`; `BOM_SCHEMA` becomes v5 and new releases write only v5. `ARCHIVED_BOM_SCHEMAS` adds v5; readiness `require_current_schema` accepts v5 only for new releases.
- v5 removes the plan-review and article-review bindings (`simpro-blog-machine-review/v1`) and all `agent_output.*` execution evidence.
- The v5 optimization stage receipt requires the optimize command-definition hash only; `agent_definition.*` and `agent_output.*` evidence are no longer required.
- `release_cli` no longer accepts `--plan-review`, `--article-review`, or `--agent-output`; passing one is an argument error (exit 2) naming the retired flag. The release CLI only creates new releases; v4 archives are validated by the BOM validators, not by re-running the CLI.
- The specialist agents remain advisory in `/write`, `/rewrite`, and `/optimize`; Claude acts on their findings but no artifact records them. Readiness already records every guard result.
- `machine_review.py`, `machine_review_workflow`, and the review-validation modules remain, used only to validate v4 archives.

## Section 2: convention-based layout and discovery

- New module `data_sources/modules/release_layout.py` is the single source of truth for artifact paths. Interface: `ReleaseLayout.for_article(article_path, workspace_root) -> ReleaseLayout` with one attribute per artifact path and `required()` / `optional()` mappings of artifact label to path.
- Slug and date come from the article filename `<slug>-<YYYY-MM-DD>.md`; workflow mode comes from the folder (`drafts/` is `new`, `rewrites/` is `rewrite`). Any other folder or filename shape is exit 2.
- Conventional paths (all under `research/` unless noted):

| Artifact | Path |
|---|---|
| Validation sidecar | `validation-<slug>-<date>.md` |
| Editorial plan v2 | `editorial-plan-<slug>-<date>.json` |
| Keyword decision | `semrush-keyword-decision-<slug>-<date>.json` |
| SERP evidence | `serp-evidence-<slug>-<date>.json` |
| Plan fulfillment (generated) | `blog-plan-fulfillment-<slug>-<date>.json` |
| Fulfillment picks (authored) | `fulfillment-picks-<slug>-<date>.json` |
| Optimizer decision (authored) | `optimizer-decision-<slug>-<date>.json` |
| Sidecar authored blocks | `sidecar-authored-<slug>-<date>.md` |
| Context request, pack, receipt | `context-request-<slug>.json`, `context-pack-<slug>.json`, `context-receipt-<slug>.json` |
| Customer proof selector evidence | `customer-proof-selector-evidence-<slug>.json` |
| Fred authority selection | `fred-authority-selector-<slug>-<date>.md` |
| Hindsight strategy evidence | `hindsight-strategy-evidence-<slug>-<date>.json` |
| PAA artifact | `paa-evidence-<slug>-<date>.json` |
| Content brief | `brief-<slug>-<date>.md` |
| Run state | `runs/<slug>-<date>.json` |
| Stage receipts | `stage-receipts/<slug>/<date>-<run8>-<stage>.json` |
| Release output | `releases/<slug>-<date>-<run8>-<phase>-<n>` |
| Commercial pillar index | `context/commercial-pillar-index.json` (repo root) |

- Run identity: the first invocation for an article writes `runs/<slug>-<date>.json` with a new UUID run id; later invocations reuse it. `--run-id` overrides and is recorded.
- Discovery: required artifacts must exist at their conventional path, else exit 2 listing each missing path; `--precheck-only` lists all missing paths in one report. Optional artifacts are passed only when present at their exact path. Gates still decide whether an optional artifact is required or forbidden (for example, context artifacts on a nonconnector article remain a blocker).
- Every existing explicit flag keeps working and overrides discovery.

## Section 3: generators

Principle: Claude writes judgment as small data files; code performs every hash, binding, and schema detail.

- **Plan fulfillment.** Authored `fulfillment-picks` maps each plan `contribution_id` to an excerpt (schema `simpro-blog-fulfillment-picks/v1`). On every run the wrapper builds `simpro-blog-plan-fulfillment/v1` from the picks with the current article and plan SHA-256, then runs the existing `check_fulfillment`. Missing or extra contribution ids, or an excerpt not visible in its `target_section`, block with the contribution id.
- **Optimizer output.** Authored `optimizer-decision` holds `decision` (`no_op` or `edited`), `reason`, `applied_fixes`, and `not_applied` (schema `simpro-optimizer-decision/v1`). On the final run the wrapper builds `simpro-optimizer-output/v2` with `status: completed` and the five `input_bindings` from the current files and the prior preflight readiness it was given. `edited` with an unchanged article hash blocks.
- **Sidecar assembler.** New CLI `python -m data_sources.modules.sidecar_assemble <article>` writes the validation sidecar from:
  - Generated blocks: Customer Proof Slate and its selector-evidence line, the prefilled Customer Proof Selection Decision (from the selector's `--decision-block` output), the Fred authority block copied byte-for-byte from its selection file, PAA/FAQ Provenance from the PAA artifact, and the fixed FAQ Source Policy rows.
  - Authored blocks: everything in `sidecar-authored` (Source Map, Metric and Customer Proof Packs, brand-language alignment, named-feature status and link check, competitive shortlist, E-E-A-T strength decision, early artifact plan, concrete answer check, review story selections, the product-claim read-path block, author policy line).
  - Rules: a generated heading appearing in the authored file is exit 2 naming the heading; duplicate headings are exit 2; generated blocks state only facts code computed. Context binding runs after assembly and installs its own block, as today.
- **Editorial plan.** Remains fully authored. New CLI `python -m data_sources.modules.editorial_plan_guard validate <plan> [--serp-evidence P] [--commercial-pillar-index P]` runs the existing v2 checks and prints findings; exit 1 on findings.
- **Hindsight evidence.** `context_build` specs gain an optional `internal_strategy` stage that calls the existing internal-strategy client methods and writes `hindsight-strategy-evidence-<slug>-<date>.json` in the shape `blog_bom_validation/hindsight.py` validates.

## Section 4: docs, errors, testing, migration

- Command docs `write.md`, `rewrite.md`, `optimize.md`, `research.md`, `scrub.md`, `publish-readiness.md` describe the new flow and fix four defects: `rewrite.md` draft receipt binds `editorial_plan`; "six machine reviewers" becomes advisory agents with no artifact; `scrub.md` shows `--stage-receipt-output`, `--run-id`, `--previous-receipt`, `--stage`; `context/aeo-geo-blog-strategy.md` stops saying native prose needs no receipt.
- Exit codes unchanged: 0 pass or phase advanced, 1 policy blocker, 2 operational or argument error. Malformed judgment files report the file and field path.
- Testing (TDD throughout): unit tests per generator and for `release_layout`; v4 archive tests stay green unchanged as the compatibility proof; acceptance test builds a fixture blog in a temp workspace from judgment files only and reaches `optimization_started` then `final_readiness` through `blog_release <article>` with no other release flags.
- Migration: no v4 artifact is rewritten. In-flight drafts finish under v5 with a fresh run.

## Implementation phasing

1. Contract v5 (BOM, receipts, precheck, release CLI), v4 archive tests green.
2. `release_layout` and wrapper discovery, run state.
3. Wrapper-built plan fulfillment and optimizer output.
4. Sidecar assembler, plan `validate` CLI, Hindsight stage in `context_build`.
5. Command docs and the acceptance test.
