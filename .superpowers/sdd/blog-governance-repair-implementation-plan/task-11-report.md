# Task 11 Report: PM-06

## Status

Implemented explicit PAA transport for the standalone content scorer CLI.

## Success Criteria

- `data_sources/modules/content_scoring/cli.py` owns standalone scorer parsing and execution.
- `data_sources/modules/content_scorer.py` remains the compatibility facade for module and direct-script invocation.
- The CLI accepts and forwards all required PAA and assembly-date inputs to `ContentScorer.score()`.
- `python -m data_sources.modules.content_scorer --help` remains available.
- No modified Python file exceeds 500 physical lines.

## RED Evidence

Command:

```powershell
python -m unittest tests.test_content_scorer_cli.ContentScorerCliTests.test_bound_paa_fixture_passes_guard_and_standalone_scorer
```

Result: failed before implementation. The standalone PAA guard exited `0`; the scorer exited `2` with:

```text
error: unrecognized arguments: --paa-workflow-mode new --paa-expected-query hvac scheduling software --paa-expected-collection-date 2026-05-22 --paa-expected-run-id content-scorer-fixture --paa-artifact ... --assembly-date 2026-05-22
```

## GREEN Evidence

Implemented `content_scoring.cli.main(argv)` with these options:

- `--paa-workflow-mode`
- `--paa-content-brief`
- `--paa-answersocrates-blocker`
- `--paa-expected-query`
- `--paa-expected-collection-date`
- `--paa-expected-run-id`
- `--paa-artifact`
- `--assembly-date`

The facade now delegates to the extracted CLI and preserves direct-script imports.

Commands run:

```powershell
python -m unittest tests.test_content_scorer_cli tests.test_paa_provenance_guard tests.test_content_scorer_aeo_geo_gate
python -m data_sources.modules.content_scorer --help
python data_sources/modules/content_scorer.py --help
python tools/check_changed_python_lines.py --base 6ca8de6 --limit 500
git diff --check
```

Results:

- Focused suite: `Ran 103 tests ... OK`.
- Module and direct-script help both exited `0` and listed all required new options.
- The changed-Python-line check exited `0`.
- `git diff --check` exited `0`.
- The subprocess test runs the standalone PAA guard with the same bound artifact and receives exit `0`. It then invokes the scorer with explicit PAA inputs and receives `AEO/GEO Score: 90/100`, confirming the scorer reaches a passing AEO result with the binding.

## Files Changed

- `data_sources/modules/content_scorer.py`
- `data_sources/modules/content_scoring/cli.py`
- `tests/test_content_scorer_cli.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-11-report.md`

## Self-Review

- Argument names exactly match the task brief.
- Every parsed PAA value is forwarded by keyword to `ContentScorer.score()`.
- Existing `ContentScorer` exports stay available from the compatibility facade.
- No articles, proof data, or unrelated workflows were changed.
- The pre-existing line-ending-only modifications to `tests/test_content_scorer_aeo_geo_gate.py` and `tests/test_publish_readiness.py` were not edited or staged.

## Concern

The requested subprocess fixture cannot produce the scorer's global exit `0` without a test-only vault claim-set patch used by existing in-process scorer tests. The real subprocess correctly reports a passing AEO score but exits `1` because the separate customer-proof diversity gate cannot validate that test-only claim fixture. This task does not change that unrelated gate or its dependency contract.

## Fix Round 1 RED

Updated the subprocess contract locally to assert scorer exit `0`, then ran:

```powershell
pytest -q tests/test_content_scorer_cli.py
```

Result: failed as required for RED. The standalone PAA provenance guard exited `0`; the scorer exited `1` despite `AEO/GEO Score: 90/100`.

The scorer reported independent release failures for review-story identity and content quality. Removing the review-derived paragraph removes the review gate but activates the required first-hand-experience path. A valid connector no-fit selector artifact must use all selector roles and a `reference_date` equal to the current date. Repository evidence is historical and intentionally fails this freshness validation. The only deterministic generator available in the test suite uses a test-only claim-set patch, which Fix Round 1 prohibits.

## Fix Round 1 Decision

No production proof rule, customer-proof artifact, or subprocess internals were changed. The test was restored to its passing assertion that verifies explicit PAA transport reaches a passing AEO result, while accurately retaining the scorer's global exit `1` for independent gates.

## Fix Round 4

### RED Evidence

Changed the scorer subprocess assertion from exit `1` to the required exit `0` before replacing the fixture, then ran:

```powershell
python -m pytest tests/test_content_scorer_cli.py -q
```

Result: failed as required for RED. The standalone PAA guard returned `0`, while the existing connector-backed Capterra fixture made the scorer return `1` with composite `84.8`, AEO/GEO `90`, and a review-story identity blocker.

### Fixture Correction

- Replaced the connector-backed customer-proof setup with `write_nonvault_proof_inputs` and `nonvault_customer_proof_selector._main`.
- Generated hash-bound `simpro-nonvault-customer-proof-selector-evidence/v1` with all four roles, `--require-eeat-story`, `experience_story=none`, and substantive rejections for both ClockShark timekeeping stories.
- Built the sidecar from the selector slate and evidence binding, an explicit no-fit E-E-A-T decision, and the existing FAQ and metric proof blocks.
- Removed the customer-proof block and customer-story paragraph from the article fixture, refreshed `Last Updated`, and inserted the controller-proven prose and commercial link before the FAQ heading.
- Kept both standalone PAA guard and scorer subprocess assertions at exit `0`. No production gate or scorer behavior changed.

### GREEN Evidence

Commands run:

```powershell
python -m pytest tests/test_content_scorer_cli.py tests/test_content_scorer_aeo_geo_gate.py tests/test_paa_provenance_guard.py -q
python -m data_sources.modules.content_scorer --help
python tools/check_changed_python_lines.py --base 6ca8de6 --limit 500
git diff --check
```

Results:

- Focused suite: `103 passed, 20 subtests passed`.
- The shared fixture passed the standalone PAA guard and scorer subprocesses with exit `0`.
- Scorer output: composite `86.6`, SEO `92`, AEO/GEO `100`, hard gates passed.
- Module help exited `0` and listed all required PAA and assembly-date options.
- Changed-Python-line check and `git diff --check` exited `0`.

## Fix Round 5

### TDD Characterization

Added a focused unit-style CLI test that invokes `content_scoring.cli.main(...)` with all eight required options and mocks `ContentScorer`. The test asserts the complete `ContentScorer.score()` keyword contract for:

- `paa_workflow_mode`
- `paa_content_brief`
- `paa_answersocrates_blocker`
- `paa_expected_query`
- `paa_expected_collection_date`
- `paa_expected_run_id`
- `paa_artifact`
- `assembly_date`

It also verifies that `main(...)` returns `0` when the mocked scorer returns `passed: True` and that the result is sent to `format_report(...)`.

Command:

```powershell
python -m pytest tests/test_content_scorer_cli.py::ContentScorerCliTests::test_main_forwards_all_paa_and_assembly_options_to_scorer -q
```

Result: `1 passed`. The new assertion passed immediately against the existing implementation, proving this reviewer finding was a test-coverage gap only. No production code changed.

### GREEN Evidence

Commands run:

```powershell
python -m pytest tests/test_content_scorer_cli.py tests/test_content_scorer_aeo_geo_gate.py tests/test_paa_provenance_guard.py -q
python -m data_sources.modules.content_scorer --help
python tools/check_changed_python_lines.py --base 6ca8de6 --limit 500
git diff --check
```

Results:

- Focused suite: `104 passed, 20 subtests passed`.
- Module help exited `0` and listed all eight required PAA and assembly-date options.
- Changed-Python-line check exited `0`.
- `git diff --check` exited `0`.
- The existing passing subprocess guard-and-scorer test remains intact.
