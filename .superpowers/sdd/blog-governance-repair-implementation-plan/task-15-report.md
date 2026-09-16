# Task 15 Report: PM-02 - Release-Chain Decider

## Status

Implemented and verified. The new pure decision module returns the stable
decisions `normal_chain_required`, `optimized_tail_allowed`, and
`draft_ready_not_release_ready` without creating release directories or
performing PM-17 precheck work.

## Assumptions and Success Criteria

- Machine-review collection statuses are precomputed PM-16 metadata keyed by
  `plan` and `article`; PM-17 can consume this API after validating invocation
  inputs and reading collection reports.
- Both collection phases must have `review_collected` status and both review
  artifacts must validate against the current plan, article, proof sidecar, run
  ID, and phase before either release chain is available.
- A fresh rewrite with no optimizer output and no prior preflight must use the
  normal chain.
- Optimized-tail authorization requires optimizer v2 evidence, prior preflight,
  the exact optimized-tail receipt stages, fresh copied execution evidence, and
  valid current machine reviews.
- Stale optimizer or copied execution evidence must return a stable normal-chain
  reason code rather than raise or authorize the tail.

## RED Evidence

The table-driven test module was added before implementation.

```powershell
python -m pytest tests/test_release_chain_decision.py -q
```

Result before the package existed:

```text
ModuleNotFoundError: No module named 'data_sources.modules.release_workflow'
1 error in 0.48s
```

## Implementation

- Added `release_workflow.chain_decision.ReleaseChainDecision` with stable
  `decision`, `code`, `reason`, and `blockers` fields.
- Reused `validate_optimizer_outputs(...)` for current optimizer bindings.
- Reused `resolve_execution_evidence(...)` and
  `ExecutionEvidenceResolution.normal_chain_required` for copied execution
  evidence.
- Reused `check_machine_review_file(...)` and
  `check_machine_review_pair(...)` for current hash and provenance validation.
- Made machine-review readiness the fail-closed first decision, so incomplete
  review collection can never authorize the optimized tail.
- Kept the module pure and omitted PM-03 persistence, PM-17 integration, and
  release-directory creation.

## Behavioral Coverage

The table-driven tests verify:

- Fresh rewrites without optimizer/prior-preflight evidence return
  `normal_chain_required`.
- Fully current optimized-tail evidence returns `optimized_tail_allowed`.
- Stale optimizer evidence returns `normal_chain_required` with
  `optimizer_output_stale`.
- Stale copied agent output returns `normal_chain_required` with
  `execution_evidence_stale`.
- Incomplete or missing collection status returns
  `draft_ready_not_release_ready`.
- A review artifact whose bound article hash is stale returns
  `draft_ready_not_release_ready` with the underlying review blocker.

## Verification

Focused and adjacent PM-14/15/16 suites:

```powershell
python -m pytest tests/test_release_chain_decision.py tests/test_blog_release.py tests/test_blog_assembly_execution_evidence.py tests/test_machine_review_workflow.py tests/test_machine_review.py -q
```

Result: `39 passed in 1.63s`.

Static and required checks:

```powershell
python -m ruff check data_sources/modules/release_workflow tests/test_release_chain_decision.py
python -m compileall -q data_sources/modules/release_workflow tests/test_release_chain_decision.py
python tools/check_changed_python_lines.py --base 3479caf --limit 500
git diff --check
```

All returned exit code `0` with no validation errors.

## Changed Files

- `data_sources/modules/release_workflow/__init__.py`
- `data_sources/modules/release_workflow/chain_decision.py`
- `tests/test_release_chain_decision.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-15-report.md`

## Line Limits

- `release_workflow/__init__.py`: 17 lines
- `release_workflow/chain_decision.py`: 214 lines
- `tests/test_release_chain_decision.py`: 208 lines

## Concerns

No functional concerns identified. PM-17 still needs to load and validate the
collection-report artifacts before passing their statuses to this pure decider.
The pre-existing unrelated modifications in
`tests/test_content_scorer_aeo_geo_gate.py` and
`tests/test_publish_readiness.py` were not edited or included. Git status also
continues to report an unrelated permission warning for
`.testtmp-retention-final/`.
