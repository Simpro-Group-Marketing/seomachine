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

## Fix Round 1: Independent Review Remediation

This section supersedes the earlier implementation descriptions where they conflict. The independent review found that the first implementation still allowed caller-prepared PAA captures, used a permissive SERP compatibility fallback, and treated any current canonical-registry bytes as authoritative even when they were not the Git `HEAD` blob.

### RED evidence

- The original report retained the exact baseline command and exact first RED result, but it did not retain the first RED node invocation. That missing command is not reconstructed or invented here. The retained first RED result remains `11 failed, 2 passed, 4 subtests passed`.
- Exact Fix Round 1 RED command:

```powershell
python -m pytest tests/test_paa_provenance_guard.py::StrictPaaSourceTests::test_record_runs_fixed_collector_and_persists_exact_stdout_before_parsing tests/test_paa_provenance_guard.py::StrictPaaSourceTests::test_record_rejects_caller_supplied_capture_and_requires_canonical_inputs tests/test_paa_provenance_guard.py::StrictPaaSourceTests::test_answersocrates_builder_requires_query_date_and_run_expectations tests/test_research_serp_playwright_fallback.py::ResearchSerpPlaywrightFallbackTests::test_production_serp_path_requires_raw_response_method_and_never_labels_normalized_compat_data_raw tests/test_research_serp_playwright_fallback.py::ResearchSerpPlaywrightFallbackTests::test_production_serp_path_uses_raw_response_method_not_combined_capture_method tests/test_editorial_plan_guard.py::test_serp_raw_capture_rejects_wrong_approved_collector_version tests/test_editorial_plan_guard.py::test_editorial_serp_validation_requires_and_matches_expected_run_id tests/test_source_support_guard.py::SourceSupportGuardTests::test_source_classification_rejects_untracked_canonical_registry tests/test_source_support_guard.py::SourceSupportGuardTests::test_source_classification_rejects_worktree_registry_modified_after_commit tests/test_aeo_geo_workflow_docs.py::AeoGeoWorkflowDocsTests::test_article_runs_fixed_answersocrates_producer_without_caller_capture_route -q
```

- Exact result: `10 failed, 1 passed, 1 subtests passed in 1.86s`.
- Exact failing contracts:
  - the PAA module did not own a fixed collector subprocess and accepted the old caller-supplied `--raw-capture` route;
  - the AnswerSocrates builder did not require query, collection-date, and run expectations;
  - production SERP collection called normalized or combined compatibility methods instead of an exact raw-response method;
  - a wrong but non-empty collector version passed;
  - editorial validation had no canonical expected-run parameter;
  - untracked and worktree-modified decision registries were accepted;
  - workflow documentation did not name the exact fixed producer inputs and identity.

### Remediation

- PAA `record` now owns the bounded repository collector. It requires `--query`, `--collection-date`, `--run-id`, `--raw-capture-output`, `--workspace-root`, and `--output`; invokes fixed `answersocrates_playwright_collector` version `1.0.0` against the fixed AnswerSocrates URL; persists exact subprocess stdout, stderr, and return code before interpretation; then reopens the attested capture and derives questions or a closed blocker. Tests fake only executable lookup and `subprocess.run`.
- AnswerSocrates build and validation require exact query, date, and canonical run ID. The BOM builder, independent BOM guard, readiness gates, content scorer, and AEO/GEO rater all forward or independently derive the same canonical article run. Added builder regressions reject both cross-run PAA and cross-run SERP evidence.
- DataForSEO production collection requires `get_serp_raw_response()`. The raw provider object is written first, strictly reopened, and only then normalized. Production no longer falls back to `get_serp_data()` or the combined compatibility seam. Playwright stdout follows the same persist-before-parse sequence.
- Approved SERP collectors are exact name/version pairs. Both raw capture and evidence validation reject any other version.
- Repository source decisions are authoritative only when `context/source-classification-decisions.json` is Git tracked and its current bytes exactly equal the committed `HEAD` blob. Both classification emission and later validation enforce this independently. Temp-Git regressions cover untracked and post-commit worktree changes while existing cases retain unapproved, URL/hostname mismatch, arbitrary path, and tamper coverage.
- Existing article and strategy documentation now names the fixed PAA producer, exact version and URL, mandatory producer arguments, exact raw-before-interpretation behavior, canonical run binding, and Git `HEAD` byte requirement.
- The review's Minor request to add the emitter version to each classification registry binding was explicitly deferred and is not addressed in this round.

### GREEN evidence

- The exact Fix Round 1 RED command above became GREEN: `10 passed, 2 subtests passed in 2.04s`.
- Expanded focused regression command, adding the blocked producer and both BOM cross-run cases: `13 passed, 2 subtests passed in 3.50s`.
- Direct scorer/rater migration and production-blocker set: `110 passed, 26 subtests passed in 9.71s`.
- BOM builder, independent BOM guard, and readiness: `161 passed in 60.36s`.
- PAA, SERP, DataForSEO, editorial, source support, workflow docs, scorer, rater, and architecture: `403 passed, 262 subtests passed in 22.91s`.
- One complete repository suite after all remediation:
  - `python -m pytest -q`
  - `1572 passed, 3 skipped, 479 subtests passed in 102.65s`.
- `python -m compileall -q data_sources/modules/aeo_geo_rater.py data_sources/modules/blog_assembly_bom.py data_sources/modules/blog_assembly_bom_guard.py data_sources/modules/content_scorer.py data_sources/modules/dataforseo.py data_sources/modules/editorial_plan_guard.py data_sources/modules/paa_provenance_guard.py data_sources/modules/publish_readiness.py data_sources/modules/source_support_guard.py scripts/research_serp_analysis.py`: exit 0.
- `git diff --check`: exit 0. Line-ending notices are informational Windows checkout warnings; no whitespace errors were reported.

### Final self-review

- No live collector, network publication, external write, alternate SERP emitter, slash command, reviewer role, or BOM schema change was introduced.
- Raw evidence is persisted before normalization or eligibility interpretation on every production path changed in this round.
- The canonical run is independently recomputed at BOM build/guard boundaries; readiness consumes the already guard-validated receipt run and forwards it through editorial, PAA, scorer, and AEO checks.
- Local execution attestation and Git `HEAD` equality establish repository-local integrity only. They do not establish that an external page or provider response is truthful.
- Historical weak or cross-run PAA, SERP, and classification artifacts fail closed and must be regenerated.
