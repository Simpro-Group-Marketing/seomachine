# Task 8 Report: PM-12 Score-Report Status Language

## Status

Implemented and verified. The formatter now reports content quality, hard-gate, and overall statuses independently. A composite score above its threshold is never labeled `BELOW THRESHOLD` solely because a hard gate failed.

## RED Evidence

Added `tests/test_content_scoring_reporting.py` before changing the formatter. The focused test failed against the original implementation:

```text
F                                                                        [100%]
____ test_report_separates_content_quality_hard_gates_and_overall_statuses ____
E       AssertionError: assert 'Composite Score: 92/100 (PASSED)' in '... Composite Score: 92/100 (BELOW THRESHOLD) ...'
1 failed in 0.11s
```

Command:

```text
python -m pytest -q tests/test_content_scoring_reporting.py
```

## Implementation

`ScoringReportingMixin.format_report` now derives:

- `Content Quality` from `composite_score >= threshold`.
- `Hard Gates` from the non-content entries in `quality_gates`, with an `aeo_geo` fallback for legacy result shapes.
- `Overall` from the aggregate `result['passed']` value.

Existing dimensions, readable score details, AEO/GEO details, and priority fixes remain in the report.

## GREEN Evidence

Focused regression test:

```text
python -m pytest -q tests/test_content_scoring_reporting.py
.                                                                        [100%]
1 passed in 0.05s
```

Related scoring and gate tests:

```text
python -m pytest -q tests/test_content_scorer_aeo_geo_gate.py tests/test_content_scorer_minimum_word_gate.py tests/test_readiness_lazy_scoring.py
..........................................                          [100%]
42 passed, 5 subtests passed in 7.34s
```

Changed-Python line check:

```text
python tools/check_changed_python_lines.py --base 69471e5 --limit 500
```

Result: exit code `0`; no oversized changed Python files were reported.

Rendered 92-point failed-gate report:

```text
Composite Score: 92/100 (PASSED)
Content Quality: PASSED
Hard Gates: FAILED
Overall: FAILED
Content Quality Threshold: 90
AEO/GEO Score: 88/100 (threshold: 90)

Priority Fixes:
  1. [aeo_geo] Add proof
     Fix: Cite source
```

## Changed Files

- `data_sources/modules/content_scoring/reporting.py`
- `tests/test_content_scoring_reporting.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-8-report.md`

## Self-Review

- The regression test uses the required 92-point composite and failed AEO/GEO hard gate.
- The composite status no longer depends on aggregate pass/fail state.
- Aggregate failure remains visible as `Overall: FAILED`.
- Hard-gate status includes all configured gates except the content-quality score gate.
- Priority-fix rendering remains covered by the regression test.
- No articles, proof data, or unrelated workflows were edited.
- Python files changed by this task are below 500 physical lines: `reporting.py` is 74 lines and the new test is 27 lines.
- `git diff --check` passed.

## Concerns

No blocking concerns. The legacy fallback marks hard gates from `aeo_geo` when a result has no `quality_gates` mapping; current scorer results provide the full mapping.

## Fix Round 1: Empty Hard-Gate Evidence

### Finding Addressed

An empty `quality_gates` mapping with no `aeo_geo` fallback previously passed through `all([])`, which incorrectly rendered `Hard Gates: PASSED`. The formatter now renders `Hard Gates: UNKNOWN` when no hard-gate result is available. `Overall` continues to reflect `result['passed']`.

### RED Evidence

Added `test_report_marks_missing_hard_gate_evidence_unknown` to the existing reporting test module before changing the implementation. The required focused command failed:

```text
pytest -q tests/test_content_scoring_reporting.py
.F                                                                       [100%]
____________ test_report_marks_missing_hard_gate_evidence_unknown ____________
E       AssertionError: assert 'Hard Gates: UNKNOWN' in '... Overall: PASSED ...'
1 failed, 1 passed in 0.09s
```

### GREEN Evidence

Required focused test command:

```text
pytest -q tests/test_content_scoring_reporting.py
..                                                                       [100%]
2 passed in 0.05s
```

Required line-limit command:

```text
python tools/check_changed_python_lines.py --base 69471e5 --limit 500
```

Result: exit code `0`; no oversized changed Python files were reported.

`git diff --check` also passed. The original 92-point failed-AEO regression remains passing in the focused suite.

### Round 1 Files

- `data_sources/modules/content_scoring/reporting.py`
- `tests/test_content_scoring_reporting.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-8-report.md`

### Round 1 Self-Review

- Empty hard-gate evidence now fails closed to an explicit `UNKNOWN` status.
- The above-threshold composite still reports `Content Quality: PASSED`.
- The supplied aggregate result still controls `Overall` status.
- The original failed-AEO behavior remains covered by the first regression test.
- No articles, proof data, or unrelated workflows were edited.
