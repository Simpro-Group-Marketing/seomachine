# Task 9 Report: PM-13 - Rank hard gates before soft recommendations

## Outcome

Completed the priority-construction extraction and made hard-gate fixes deterministic.
The priority list now places independent AEO/GEO, source support, PAA provenance,
FAQ proof, metric-proof, review-story, customer-proof, URL, and minimum-word
blockers ahead of dimension-level recommendations. The existing five-item cap remains.

## Assumptions and Success Criteria

- The requested deterministic order is the operator remediation order encoded in
  `content_scoring/priorities.py`.
- Aggregate AEO/GEO failure should be surfaced only for an independent AEO/GEO
  issue. Its FAQ, PAA, and E-E-A-T proof failures already have dedicated,
  more actionable gate fixes.
- Success required an extracted builder, a RED behavioral test, all failed hard
  gates ahead of readability or metadata advice, preserved priority-fix fields,
  and all changed Python files at or below 500 physical lines.

## RED Evidence

Added `tests/test_content_scoring_priorities.py` before implementation.

Command:

```powershell
python -m pytest tests/test_content_scoring_priorities.py -q
```

Result:

```text
ModuleNotFoundError: No module named 'data_sources.modules.content_scoring.priorities'
1 error in 0.14s
```

## Implementation

- Added `data_sources/modules/content_scoring/priorities.py` with the pure
  `build_priority_fixes()` entry point and explicit hard-gate ordering.
- Routed `ScoringOrchestrationMixin.score()` through that builder.
- Removed `_build_priority_fixes()` and `_add_gate_priority_fixes()` from
  `quality_gates.py`.
- Retained legacy fix fields: `issue`, `fix`, `severity`, `dimension`,
  `dimension_score`, and `impact`.
- Retained the maximum list length of five entries.

## GREEN Evidence

Focused behavioral and regression checks:

```powershell
python -m pytest tests/test_content_scoring_priorities.py tests/test_content_scorer_aeo_geo_gate.py tests/test_content_scorer_minimum_word_gate.py -q
```

Result:

```text
40 passed, 5 subtests passed in 3.13s
```

Syntax check:

```powershell
python -m compileall -q data_sources/modules/content_scoring/priorities.py data_sources/modules/content_scoring/orchestration.py data_sources/modules/content_scoring/quality_gates.py
```

Result: exit 0.

Changed-Python-file guard:

```powershell
python tools/check_changed_python_lines.py --base eb42738 --limit 500
```

Result: exit 0 with no findings.

## Files Changed

- `data_sources/modules/content_scoring/priorities.py`
- `data_sources/modules/content_scoring/orchestration.py`
- `data_sources/modules/content_scoring/quality_gates.py`
- `tests/test_content_scoring_priorities.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-9-report.md`

## Self-Review

- The focused test asserts the first five dimensions are exactly `aeo_geo`,
  `source_support`, `paa_provenance`, `faq_proof`, and `url_validation` when
  those gates fail alongside readability and metadata advice.
- It asserts the five-item cap and verifies no soft dimension recommendation
  displaces a hard blocker.
- Existing AEO/GEO and minimum-word gate tests remain green.
- `quality_gates.py` is 283 lines, `priorities.py` is 186 lines, and the new
  test is 60 lines.

## Concerns

No functional concerns. The full repository test suite was not run because the
task requested focused tests; the directly related regression suites and the
required changed-line guard passed.
