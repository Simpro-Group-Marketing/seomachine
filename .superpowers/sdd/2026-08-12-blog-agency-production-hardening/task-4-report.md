# Task 4 Report: Genuine Research and Source Provenance

## Scope

Implemented Task 4 only. The existing `/article`, `/research` to `/write`, and `/publish-readiness` routes remain in place; the BOM schema remains unchanged; `scripts/research_serp_analysis.py` remains the sole production SERP evidence emitter. No slash command, orchestrator, reviewer role, human approval, live collector run, external write, or publication was added.

## Red evidence

- Baseline before Task 4 changes:
  - `python -m pytest tests/test_paa_provenance_guard.py tests/test_research_serp_playwright_fallback.py tests/test_editorial_plan_guard.py tests/test_source_support_guard.py -q`
  - `153 passed, 35 subtests passed in 17.62s`
- The first focused Task 4 contract run produced `11 failed, 2 passed, 4 subtests passed`.
- The failures established that:
  - PAA `record` still accepted caller-authored eligible questions, ineligible fragments, blocker kinds, and blocker reasons instead of requiring a raw capture.
  - PAA artifacts had no exact raw path/hash binding and could not rederive questions or blockers.
  - the SERP CLI and emitter did not require an explicit agency run ID or bind exact raw provider/browser output;
  - source-classification callers still supplied `source_class` and `publisher_relationship` instead of resolving an approved decision.

## Implementation

### PAA capture and derivation

- `record` now requires one raw AnswerSocrates Playwright capture. The removed authored flags are rejected by the CLI.
- The capture schema fixes the collector identity/version and AnswerSocrates page URL, and requires query, run ID, start/end UTC timestamps, page context, visible capture sections, and local execution attestation.
- The guard derives eligible questions only from the exact `People Also Ask` section. Suggestions, navigation, non-question fragments, and caller-authored arrays do not qualify.
- Blockers are derived from captured visible output through a closed mapping for login, CAPTCHA, quota, and unavailability. Blocked captures cannot contribute eligible questions.
- Both the AnswerSocrates artifact and its receipt bind the exact workspace-relative raw path and SHA-256. Validation reopens the raw capture, verifies its attestation, collector, URL, query, run ID, timestamp order/freshness, and hash, then rederives all questions and blocker state. Historical weak artifacts fail closed.

### SERP raw capture and evidence

- `--run-id` is now an explicit production input and flows unchanged through raw capture and `simpro-serp-evidence/v1`.
- The existing DataForSEO client exposes a narrow `get_serp_capture()` seam returning the exact API response plus its existing normalized view. `get_serp_data()` delegates to it and preserves its public normalized return contract.
- The production emitter persists the exact DataForSEO response or exact Playwright CLI stdout before evidence normalization. The wrapper binds collector, query, timestamp, run ID, request URL/locale, and local execution attestation without altering the raw response.
- SERP evidence v1 now binds the workspace-relative raw path and SHA-256 without changing its schema identifier. The builder derives organic rows, content types, and SERP features from the bound raw capture.
- Validation uses strict immutable JSON snapshots, verifies raw/evidence attestations and metadata, rejects missing/changed/unsigned/stale/future/mismatched captures, and rederives directly observable rows/features to detect evidence/raw divergence.
- Blocked or empty captures do not mint verified evidence. Planning reuses its immutable evidence snapshot instead of permissively reparsing the file.

### Approved source decisions

- `write_source_classification_artifact` now accepts source URL, decision ID, canonical decision path, and workspace root only. Caller classification overrides are no longer part of its API.
- Repository authority resolves exactly one approved decision from `context/source-classification-decisions.json` and binds authority mode, decision ID/revision, exact URL/hostname, registry path/hash, and fixed `source_registry_export` emitter identity.
- Validation strictly reloads and rehashes both classification and decision snapshots and rejects missing, changed, unapproved, stale-revision, URL/hostname-mismatched, unsupported-authority, arbitrary-path, or re-attested divergent mappings.
- No speculative decision registry was populated. Repository decisions fail closed until governance supplies approved rows. Vault connector authority remains reserved; the required vault workflow and vault-unavailable fallback rule were not weakened or replaced.

### Documentation and fixtures

- Updated the existing command and strategy documents to use raw PAA captures, explicit SERP run IDs, and approved source-decision bindings.
- Added one shared test fixture module for creating genuine attested research captures; downstream BOM/rater/scorer fixtures now use bound artifacts rather than weakening production validation.
- Execution attestation is described only as workspace-local integrity evidence, not proof that an external page or provider is truthful.

## Verification

- Focused PAA suite during implementation: `59 passed, 14 subtests passed`.
- Primary provenance plus semantic documentation suite during implementation: `283 passed, 243 subtests passed`.
- Adjacent BOM/readiness/rater/scorer suite during implementation: `265 passed, 26 subtests passed`.
- One complete repository suite before the final narrow self-review tightening:
  - `python -m pytest -q`
  - `1562 passed, 3 skipped, 486 subtests passed in 152.52s`
- Post-self-review affected suite, including the production DataForSEO exact-response contract:
  - `python -m pytest tests/test_dataforseo_correctness.py tests/test_research_serp_playwright_fallback.py tests/test_editorial_plan_guard.py tests/test_source_support_guard.py tests/test_paa_provenance_guard.py tests/test_aeo_geo_workflow_docs.py::AeoGeoWorkflowDocsTests::test_research_provenance_docs_remove_caller_authored_paa_and_bind_run_and_decision tests/test_blog_assembly_bom.py::test_builder_snapshots_actual_files_as_workspace_relative_paths -q`
  - `171 passed, 44 subtests passed in 7.91s`
- `python -m compileall -q data_sources/modules scripts tests/research_provenance_fixtures.py`: exit 0.
- `git diff --check`: exit 0.

## Review notes

- Exact raw capture plus local attestation proves repository-local integrity and derivation, not external truthfulness.
- Existing weak PAA/SERP/classification artifacts must be regenerated through the hardened paths.
- The approved repository source-decision file is canonical but intentionally not synthesized or prepopulated in this task; classification remains fail closed in its absence.
