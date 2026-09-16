# Task 13 Report: PM-15 - Validate Copied Execution Evidence

## Status

Implemented and verified. Optimized-tail BOM construction now validates copied
`agent_output.*` evidence against the current paths and bytes supplied by the
caller. A mismatch returns a named stale-artifact result and construction fails
closed with `normal_chain_required` plus the stale label and path.

## Scope

- Added the narrow execution-evidence decision interface required by PM-15.
- Preserved copied prior-preflight evidence when current agent output rows match.
- Did not add the PM-02 release-chain decider, PM-03 error framework, or PM-17
  precheck.

## RED Evidence

The mutated-output behavioral test was added before implementation and run with:

```powershell
python -m pytest tests/test_blog_assembly_bom.py::test_optimized_bom_requires_normal_chain_for_stale_agent_output -q
```

Result: `1 failed in 1.37s`. The old path copied stale evidence and failed only
later in generic artifact verification:

```text
ValueError: artifacts.execution_evidence.agent_output.content-analyzer.sha256 does not match current file contents
```

The expected `normal_chain_required` decision and stale artifact label were
absent. The focused tests were subsequently moved to a new file so the existing
2,444-line BOM test module would not violate the changed-Python-file limit.

## Implementation

- Added `blog_assembly/execution_evidence.py` with:
  - `ExecutionEvidenceResolution`
  - `StaleExecutionArtifact`
  - `NORMAL_CHAIN_REQUIRED`
  - optimized-tail prior-evidence loading and current-byte comparison
- Moved `_execution_evidence_from_prior_preflight` out of `derivation.py` while
  preserving its compatibility export through `blog_assembly_bom.py`.
- Updated construction support to consume the result and reject stale evidence
  before BOM assembly with a message naming the decision, label, and path.
- Added focused fresh and mutated optimized-tail tests in
  `tests/test_blog_assembly_execution_evidence.py`.

## GREEN Evidence

Focused PM-15 tests:

```powershell
python -m pytest tests/test_blog_assembly_execution_evidence.py -q
```

Result: `2 passed in 0.47s`.

Affected BOM and BOM-guard suites:

```powershell
python -m pytest tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_guard.py -q
```

Result: `110 passed in 50.78s`.

Optimized BOM subset:

```powershell
python -m pytest tests/test_blog_assembly_bom.py -k "optimized_bom or optimized_tail" -q
```

Final result after moving the two PM-15 tests into their focused module:
`5 passed, 59 deselected in 5.54s`.

Static checks:

```powershell
python -m ruff check data_sources/modules/blog_assembly/execution_evidence.py data_sources/modules/blog_assembly/derivation.py data_sources/modules/blog_assembly/construction_support.py data_sources/modules/blog_assembly_bom.py tests/test_blog_assembly_execution_evidence.py
python tools/check_changed_python_lines.py --base 1f4a5ff --limit 500
git diff --check
```

Ruff and the changed-Python-file guard passed. `git diff --check` also passed;
Git emitted only routine LF-to-CRLF working-copy warnings.

## Files Changed

- `data_sources/modules/blog_assembly/execution_evidence.py`
- `data_sources/modules/blog_assembly/construction_support.py`
- `data_sources/modules/blog_assembly/derivation.py`
- `data_sources/modules/blog_assembly_bom.py`
- `tests/test_blog_assembly_execution_evidence.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-13-report.md`

## Concerns

No functional concerns. Existing unrelated working-tree edits in
`tests/test_content_scorer_aeo_geo_gate.py` and `tests/test_publish_readiness.py`
were not modified or staged for this task.

## Fix Round 1

### Reviewer Finding Addressed

Optimized-tail resolution no longer skips a copied `agent_output.*` row when
its ID is absent from `agent_output_paths`. For an omitted ID, the resolver now
uses the copied row's recorded path and compares its current canonical path and
SHA-256 against the copied row. A changed, missing, or otherwise unavailable
current file returns `normal_chain_required` with the copied label and path.
Caller-supplied agent-output paths retain their existing comparison behavior.

### Regression Evidence

Added
`test_optimized_tail_validates_copied_output_omitted_from_current_paths`, which
mutates the copied output after prior preflight, supplies an empty
`agent_output_paths` mapping, and asserts both resolver and construction paths
identify `agent_output.content-analyzer` and its copied path.

Before the production change:

```powershell
python -m pytest tests/test_blog_assembly_execution_evidence.py::test_optimized_tail_validates_copied_output_omitted_from_current_paths -q
```

Result: `1 failed in 0.53s`; the resolver incorrectly returned
`evidence_ready` instead of `normal_chain_required`.

After the production change:

```powershell
python -m pytest tests/test_blog_assembly_execution_evidence.py -q
```

Result: `3 passed in 0.44s`.

Affected optimized BOM subset:

```powershell
python -m pytest tests/test_blog_assembly_bom.py -k "optimized_bom or optimized_tail" -q
```

Result: `5 passed, 59 deselected in 7.45s`.

Focused static check:

```powershell
python -m ruff check data_sources/modules/blog_assembly/execution_evidence.py tests/test_blog_assembly_execution_evidence.py
```

Result: passed.

Scope remained limited to PM-15. PM-02, PM-03, and PM-17 were not changed.
