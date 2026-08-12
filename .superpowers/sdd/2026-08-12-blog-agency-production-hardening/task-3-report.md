# Task 3 Report: Shared Artifact and Receipt Integrity

## Scope

Implemented Task 3 only. The BOM remains `simpro-blog-assembly-bom/v1`; no public command, agent, human gate, publishing mutation, or Task 2/4+ behavior was added.

## Red evidence

- `python -m pytest -q tests/test_blog_assembly_integrity_hardening.py`
  - RED at collection because `canonical_article_run_id`, `is_json_number`, and `load_json_object_snapshot` did not exist.
- `python -m pytest -q tests/test_blog_assembly_integrity_hardening.py::test_mutation_start_can_derive_the_canonical_run_id`
  - RED because `start_mutation()` had no deterministic workspace/article/date derivation interface.
- `python -m pytest -q tests/test_blog_assembly_bom.py::test_builder_detects_stage_receipt_replacement_after_immutable_snapshot`
  - RED because a receipt replaced after its immutable read was not revalidated before the builder returned.
- Integration RED runs also proved that opaque scrub/context evidence hashes, non-canonical fixture run IDs, and wall-clock-crossed receipt dates were accepted by the old test fixtures. Fixtures were changed to use current path/hash-bound evidence artifacts and canonical article run IDs rather than weakening the new checks.

## Implementation

- Added one-read, bounded strict UTF-8 JSON object snapshots with duplicate-key, non-finite number, invalid UTF-8, and configurable size rejection.
- Centralized finite numeric validation excluding Boolean values, canonical gate inventory, and normal/optimized stage sequences.
- Derived workflow run IDs from canonical workspace-relative article path plus assembly date. Mutation start can derive the ID through existing CLI options `--assembly-date` and `--workspace-root`; downstream producers inherit it from predecessor receipts.
- Bound BOM article, editorial-plan, and stage-receipt hashes to the exact snapshots used for parsing, then reverified the complete artifact inventory before returning or finalizing.
- Enforced canonical run ID, assembly-date freshness, future-time rejection, global monotonicity, and closed stage order at BOM builder and guard boundaries with current time supplied explicitly.
- Materialized scrub statistics and Context Binding evidence as `simpro-blog-stage-evidence/v1` sidecars. Receipts bind each sidecar hash, and BOM v1 inventories the current evidence artifacts.
- Enforced universal receipt evidence resolution in both the BOM builder and guard. Every evidence digest must resolve to a current BOM artifact, a validated stage-evidence manifest, a prior preflight input snapshot, or an injected current repository-definition hash.
- Added an ignored `.seomachine/` local consumed-state ledger keyed by existing `state_hash`. Exclusive reservation makes concurrent finishes one-winner; copied/restored states cannot replay; ordinary pre-commit failures remove only their own uncommitted reservation.
- Routed BOM, receipt, mutation-state, readiness, and context control-plane JSON reads through the strict loader, and routed scrub/context producer hashing and parsing through immutable byte snapshots.
- Preserved execution attestation as workspace-local integrity evidence. No external-truth claim was introduced.

## Verification

- Focused Task 3 and adjacent runtime/docs suite:
  - `python -m pytest -q tests/test_blog_assembly_contract.py tests/test_blog_assembly_stage_receipt.py tests/test_blog_assembly_mutation_recorder.py tests/test_blog_assembly_integrity_hardening.py tests/test_blog_assembly_bom_input_types.py tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_guard.py tests/test_content_scrubber.py tests/test_context_binding_guard.py tests/test_publish_readiness.py tests/test_aeo_geo_workflow_docs.py tests/test_blog_agency_architecture.py tests/test_vault_topology_neutrality.py`
  - `456 passed, 219 subtests passed in 37.09s`
- Complete repository suite, Task 3 tool result:
  - `python -m pytest -q`
  - `1492 passed, 3 skipped, 434 subtests passed in 65.87s`
- `python -m compileall -q` over every changed Python module: exit 0.
- `git diff --check`: exit 0.

## Review notes

- Historical BOMs without path/hash-bound stage evidence now fail closed and must be regenerated, as the plan permits.
- The local consumed-state ledger is deliberately ignored and machine-local. It prevents replay within the workspace integrity boundary; it is not an external transparency log.
