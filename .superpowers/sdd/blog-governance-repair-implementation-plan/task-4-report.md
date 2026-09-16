# Task 4 Report: PM-08

## Status

Complete. Source support now recognizes imperative writing advice, checklist items, and rows in `What to write` tables as contextual instructional content.

## TDD Evidence

- RED: `pytest -q tests/test_source_support_instructional_context.py` initially reported 3 failing instructional-content tests and 5 passing high-risk counter-tests.
- RED expansion: the added waived-fee counter-test failed before the commercial claim pattern was extended.
- GREEN: the focused instructional-content suite passed with 9 tests.

## Safety Boundary

The contextual exemption applies only after existing extraction identifies a general candidate. Numeric, causal, commercial, comparative, absolute, guarantee, legal/regulatory, and product-status or availability content remains source-supported or fails closed. Fee language now enters the existing commercial claim classification.

## Verification

- `pytest -q tests/test_source_support_instructional_context.py`: 9 passed.
- `pytest -q tests/test_source_support_guard.py tests/test_source_support_batch.py tests/test_source_support_cli.py tests/test_proof_link_policy.py tests/test_numeric_claim_source_guard.py`: 144 passed, 44 subtests passed.
- `python tools/check_changed_python_lines.py --base 1a2809e`: passed.
- `git diff --check`: passed.

## Self-Review

No article or unrelated files changed. The new detector is limited to markdown-context identification, and policy decisions remain in the existing claim extraction and matching flow. All changed and new Python files are below the 500-line ceiling.

## Fix Round 1/5: Eligibility Boundary

### RED

- Command: `pytest -q tests/test_source_support_instructional_context.py`
- Output: `1 failed, 9 passed in 0.50s`.
- Failure: `State that customers are eligible for the add-on.` in a checklist context returned no findings.

### GREEN

- Command: `pytest -q tests/test_source_support_instructional_context.py`
- Output: `10 passed in 0.38s`.
- Command: `pytest -q tests/test_source_support_guard.py tests/test_source_support_batch.py tests/test_source_support_cli.py tests/test_proof_link_policy.py tests/test_numeric_claim_source_guard.py`
- Output: `144 passed, 44 subtests passed in 7.44s`.
- Command: `python tools/check_changed_python_lines.py --base 1a2809e`
- Output: passed.
- Command: `git diff --check`
- Output: passed.

### Files Changed

- `data_sources/modules/source_support/common.py`
- `tests/test_source_support_instructional_context.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-4-report.md`

## Fix Round 2/5: Subject-Neutral Eligibility and Access

### RED

- Command: `pytest -q tests/test_source_support_instructional_context.py`
- Output: `2 failed, 10 passed in 0.44s`.
- Failures: reader eligibility and add-on access restricted to enterprise plans produced no `commercial` candidate.

### GREEN

- Command: `pytest -q tests/test_source_support_instructional_context.py`
- Output: `12 passed in 0.37s`.
- Command: `pytest -q tests/test_source_support_guard.py tests/test_source_support_batch.py tests/test_source_support_cli.py tests/test_proof_link_policy.py tests/test_numeric_claim_source_guard.py`
- Output: `144 passed, 44 subtests passed in 6.59s`.
- Command: `python tools/check_changed_python_lines.py --base 1a2809e`
- Output: passed.
- Command: `git diff --check`
- Output: passed.

### Files Changed

- `data_sources/modules/source_support/common.py`
- `tests/test_source_support_instructional_context.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-4-report.md`

## Fix Round 3/5: Concept-Level Eligibility and Access

### RED

- Command: `pytest -q tests/test_source_support_instructional_context.py`
- Output: `4 failed, 12 passed in 0.51s`.
- Failures: every-customer eligibility, reader eligibility, eligible-reader access, and user access produced no `commercial` candidate.

### GREEN

- Command: `pytest -q tests/test_source_support_instructional_context.py`
- Output: `16 passed in 0.41s`.
- Command: `pytest -q tests/test_source_support_guard.py tests/test_source_support_batch.py tests/test_source_support_cli.py tests/test_proof_link_policy.py tests/test_numeric_claim_source_guard.py`
- Output: `144 passed, 44 subtests passed in 7.40s`.
- Command: `python tools/check_changed_python_lines.py --base 1a2809e`
- Output: passed.
- Command: `git diff --check`
- Output: passed.

### Files Changed

- `data_sources/modules/source_support/common.py`
- `tests/test_source_support_instructional_context.py`
- `.superpowers/sdd/blog-governance-repair-implementation-plan/task-4-report.md`
