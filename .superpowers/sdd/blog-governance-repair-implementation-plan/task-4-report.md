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
