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
- Enforced universal receipt evidence resolution in both the BOM builder and guard. Every evidence digest must resolve to a current BOM artifact, a validated stage-evidence manifest, or a prior preflight input snapshot. Caller-supplied repository-definition digests are not authorized.
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

## Controller review remediation

### Reproduced RED findings

- Mutation start accepted caller-selected run IDs and omitted signed workspace/date fields; finish accepted a caller ledger override or derived the ledger from CWD. Three canonical-start tests and three ledger-boundary tests failed before remediation.
- Embedded sidecar JSON accepted duplicate keys and non-finite numbers. The strict embedded-loader regression initially failed at collection because the API did not exist; five strict embedded/sidecar cases passed after implementation.
- BOM guard editorial-plan loader failures disappeared, while editorial plan, readiness output, and historical provisional BOM used permissive reopen paths. Duplicate-key and `NaN` regressions failed at each boundary before the shared bound-snapshot path was applied.
- BOM builder and guard publicly accepted arbitrary `repository_definition_hashes`. Three public-signature regressions failed before removal.
- Receipt validation with no injected clock skipped future checks, and preflight receipt binding omitted canonical article/workspace/date inputs. One clock-default test and three required-boundary-input tests failed before remediation.
- BOM builder duplicated provisional stage tuples, and readiness inventory ordering was duplicated between the contract and executor. Behavioral centralization tests failed before shared stage constants and gate descriptors were wired into both consumers.

### Remediation

- Active mutation state now signs canonical `workspace_root`, `assembly_date`, article identity, and derived run ID. Workspace/date are mandatory on every start API/CLI call; a supplied run ID is only an equality assertion. Finish derives the replay ledger exclusively from the signed workspace and rejects state, receipt, or evidence paths outside it.
- Added strict embedded JSON parsing with the same duplicate-key and non-finite-number behavior as file snapshots. Context Binding sidecar blocks use it.
- BOM guard now hashes and parses bound editorial plan, readiness output, and historical provisional BOM from one immutable snapshot. Editorial-plan validation accepts that preloaded payload instead of reopening the plan; loader failures produce blockers.
- Removed caller definition-digest injection. Opaque receipt evidence remains unresolved until a closed internal registry exists in a later task.
- Receipt-chain validation uses current UTC by default and rejects invalid injected clocks. Preflight and readiness receipt boundaries derive and require canonical run identity plus assembly-date freshness.
- BOM builder consumes shared normal/optimized provisional stage constants. One ordered conditional gate descriptor now generates expected inventory and orders complete executor results.

### Remediation verification

- Serialized focused and adjacent Task 3 suite: `505 passed, 219 subtests passed in 35.36s`.
- Single complete repository suite: `1520 passed, 3 skipped, 434 subtests passed in 65.22s`.
