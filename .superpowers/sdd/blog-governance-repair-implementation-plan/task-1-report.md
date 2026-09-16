# Task 1 Report: PM-04 - Protect the BOM Adapter Contract

## Status

Implemented and verified.

## Scope

Added a behavioral integration test for the captured-snapshot path of `sidecar_binding_errors()`. The test supplies customer-proof selector evidence and Fred Voccola authority evidence, then verifies that both bindings are accepted without errors and that the Fred evidence is read through the captured adapter.

The existing compatibility exports were preserved exactly in `data_sources/modules/blog_assembly_contract.py`:

- `FRED_SELECTION_SECTION_RE`
- `SELECTOR_EVIDENCE_LINE_RE`

No second parser was introduced. All modified Python files remain below 500 physical lines.

## TDD Evidence

After adding the test, the two compatibility imports were temporarily masked. The focused test failed as expected with:

`AttributeError: module 'data_sources.modules.blog_assembly_contract' has no attribute 'SELECTOR_EVIDENCE_LINE_RE'`

The exact compatibility imports were then restored. The focused test passed.

## Verification

- `python -m pytest -q tests/test_blog_bom_snapshot_sidecar.py` -> `1 passed`
- `python -m pytest -q tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_guard.py tests/test_blog_assembly_bom_input_types.py tests/test_blog_assembly_bom_v2.py tests/test_blog_assembly_bom_v4.py tests/test_blog_bom_validation_package.py` -> `130 passed`
- Compatibility export import check -> passed
- `git diff --check` -> passed

## Changed Files

- `tests/test_blog_bom_snapshot_sidecar.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-1-report.md`

`data_sources/modules/blog_assembly_contract.py` was used for the RED demonstration and restored byte-for-byte to its pre-task state; it is not a committed change.

## Concerns

No known concerns. The unrelated pre-existing `.testtmp-retention-final/` permission warning appeared during Git status inspection and was not modified.
