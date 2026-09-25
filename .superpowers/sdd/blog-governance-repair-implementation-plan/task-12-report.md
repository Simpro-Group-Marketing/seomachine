# Task 12 Report: PM-14 Reject Stale Optimizer Output Early

## Status

DONE

## Assumptions

- The optimizer's inspected `scorecard` is a distinct artifact declared by the optimizer output. The release-supplied `prior_preflight_readiness` remains independently bound.
- V1 remains readable through the optimizer evidence parser, but only V2 can authorize a current optimized release.
- PM-14 owns optimizer freshness before release-directory creation. Later execution-evidence and general release precheck behavior remain outside this task.

## Success Criteria

- A valid `simpro-optimizer-output/v2` binds exact current bytes for article, editorial plan, proof sidecar, scorecard, and prior-preflight readiness.
- V1, malformed V2, and any independently stale binding fail before release-directory creation.
- Stale failures expose `optimizer_output_stale` and the expected and observed SHA-256 hashes.

## TDD Evidence

RED command:

```text
python -m pytest tests/test_blog_release.py::test_blog_release_rejects_stale_optimizer_before_creating_output_directory -q
```

RED result: `1 failed`. The failure was `Failed: DID NOT RAISE ReleaseInvocationError`, proving the release flow ignored the mutated article after optimizer evidence creation.

GREEN command:

```text
python -m pytest tests/test_blog_release.py::test_blog_release_rejects_stale_optimizer_before_creating_output_directory -q
```

GREEN result: `1 passed`.

## Implementation

- Added `data_sources/modules/optimizer_evidence.py` with bounded V1/V2 parsing, strict V2 binding validation, workspace-bounded artifact resolution, exact-byte hashing, and stable error codes.
- Integrated optimizer authorization after release invocation validation and before `_new_output_dir(...)`.
- Added behavioral coverage for article, editorial plan, proof sidecar, scorecard, and prior-preflight mutation; V1 rejection/history parsing; malformed V2; and valid V2 release continuation.
- Updated optimizer workflow guidance to require V2 and all five input bindings.

## Verification

- `python -m pytest tests/test_blog_release.py -q` -> `16 passed`
- `python -m pytest tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_guard.py -q` -> `108 passed`
- `python -m pytest tests/test_aeo_geo_workflow_docs.py -q` -> `23 passed`
- `python tools/check_changed_python_lines.py --base 38fc05f --limit 500` -> passed
- `git diff --check` -> passed

## Concerns

None. PM-15 copied execution-evidence validation and PM-17 general precheck extraction were intentionally not implemented.
