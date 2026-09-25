# Task 14 Report: PM-16 - Genuine Machine-Review Collection

## Status

Implemented and verified. The new workflow collects six real, unique,
hash-bound `simpro-machine-review-agent-response/v1` artifacts and writes the
existing `simpro-blog-machine-review/v1` artifact only when the complete roster
is valid. Invalid collections write a machine-readable report with status
`draft_ready_not_release_ready` and return nonzero.

## Assumptions and Success Criteria

- Agent response artifacts use `artifact_hash` as the canonical payload hash,
  matching existing repository artifact conventions.
- The established final-review contract requires `completed` status with no
  unresolved findings before a response can enter a final review artifact.
- A successful collection must pass the existing `check_machine_review_file`
  validator against the current plan, article, proof sidecar, run ID, and phase.
- Missing, duplicate, stale, mismatched, malformed, blocked, or
  changes-requested responses must not be replaced with generated responses.

## RED Evidence

The behavioral test module was added before implementation.

```powershell
python -m pytest tests/test_machine_review_workflow.py -q
```

Result before the package existed:

```text
ModuleNotFoundError: No module named 'data_sources.modules.machine_review_workflow'
1 error in 0.33s
```

## Implementation

- Added a package CLI at
  `python -m data_sources.modules.machine_review_workflow`.
- Added canonical agent-response construction, persistence, and validation.
- Bound each response to run metadata and SHA-256 hashes for the editorial
  plan, article, and proof sidecar.
- Reused the existing machine-review roster, phase, status, response-field,
  and finding-field constants.
- Added deterministic collection reports for success and fail-closed outcomes.
- Routed successful collections exclusively through `build_machine_review`,
  `check_machine_review`, and `write_machine_review`.
- Preserved existing BOM construction and did not add PM-02, PM-03, or PM-17
  behavior.

## Behavioral Coverage

The tests verify:

- Six valid role artifacts produce a valid existing review artifact in roster
  order.
- A missing role produces `draft_ready_not_release_ready`, nonzero exit, and no
  review artifact.
- A duplicate role produces missing-role and duplicate-role diagnostics without
  a review artifact.
- A stale article hash and wrong run ID produce fail-closed diagnostics, exclude
  the invalid response from collected agents, and never create a substitute.

## Verification

Focused workflow and existing machine-review suites:

```powershell
python -m pytest tests/test_machine_review_workflow.py tests/test_machine_review.py -q
```

Result: `9 passed in 0.33s`.

Affected BOM review suites:

```powershell
python -m pytest tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_v2.py tests/test_blog_bom_validation_package.py tests/test_bom_snapshot_store.py -q
```

Result: `81 passed in 27.06s`.

Additional checks:

```powershell
python tools/check_changed_python_lines.py --base d53f960 --limit 500
git diff --check
python -m compileall -q data_sources/modules/machine_review_workflow
python -m data_sources.modules.machine_review_workflow --help
```

All returned exit code `0`. The CLI help lists all metadata, current-input,
output, report, and response-file arguments.

## Changed Files

- `data_sources/modules/machine_review_workflow/__init__.py`
- `data_sources/modules/machine_review_workflow/__main__.py`
- `data_sources/modules/machine_review_workflow/validation.py`
- `tests/test_machine_review_workflow.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-14-report.md`

## Line Limits

- `machine_review_workflow/__init__.py`: 382 lines
- `machine_review_workflow/validation.py`: 140 lines
- `machine_review_workflow/__main__.py`: 6 lines
- `tests/test_machine_review_workflow.py`: 176 lines

## Concerns

No functional concerns identified. The working tree contains pre-existing
unrelated modifications in `tests/test_content_scorer_aeo_geo_gate.py` and
`tests/test_publish_readiness.py`; they were not edited or included in this
task. Git also reports an unrelated permission warning for
`.testtmp-retention-final/` during status scans.

## Fix Round 1

### Status

Implemented and verified the reviewer-requested fail-closed protections.

### Changes

- The collector removes any existing output review before reading current
  bindings, so no failed collection path can leave a previous successful review
  available to downstream BOM validation.
- The collector compares the final review's editorial-plan, article, and proof-
  sidecar hashes with the bindings captured before response validation. A
  mismatch writes `draft_ready_not_release_ready`, reports
  `machine_review_input_changed_during_collection`, returns nonzero, and leaves
  no review output.
- Added focused coverage for a pre-existing successful review followed by a
  missing-role failure, input mutation between response validation and final
  build, a blocked response, and an invalid response artifact hash.

### RED Evidence

Before the implementation change:

```powershell
python -m pytest tests/test_machine_review_workflow.py -q
```

Result: `2 failed, 6 passed in 0.47s`. The failures proved that a prior review
survived a missing-role collection and that an article mutation before final
build still returned success.

### Verification

```powershell
python -m pytest tests/test_machine_review_workflow.py tests/test_machine_review.py -q
```

Result: `13 passed in 0.46s`.

```powershell
python -m pytest tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_v2.py tests/test_blog_bom_validation_package.py tests/test_bom_snapshot_store.py -q
```

Result: `81 passed in 28.73s`.

```powershell
python -m data_sources.modules.machine_review_workflow --help
```

Result: exit code `0`; all collection arguments were listed.

```powershell
python tools/check_changed_python_lines.py --base d53f960 --limit 500
git diff --check
```

Result: both commands returned exit code `0` with no validation errors.

### Scope and Concerns

- No BOM construction, PM-02, PM-03, or PM-17 behavior changed.
- Changed Python files remain under 500 physical lines:
  `machine_review_workflow/__init__.py` is 396 lines and
  `test_machine_review_workflow.py` is 282 lines.
- The unrelated working-tree modifications and permission warning documented
  above remain unchanged.
