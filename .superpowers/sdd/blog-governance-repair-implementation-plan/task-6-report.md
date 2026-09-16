# Task 6 Report: PM-10 - Improve AI-Lint Repetition Diagnostics

## Status

Completed and committed independently.

## Scope and Assumptions

- The requested public API is limited to the existing `lint_content`, `lint_file`, and `should_fail` imports. These remain available from `data_sources.modules.ai_copy_linter`.
- A repeated-opener cluster is represented by one `repeated_sentence_start` finding. The finding retains the normalized two-word opener in `match` and adds a `lines` list containing every occurrence line.
- PM-08's `instructional_line_numbers` and `INSTRUCTIONAL_VERB_RE` define recognized imperative instructional context. A cluster is downgraded only when every occurrence is instructional and the opener is imperative.

## RED Evidence

Added the focused behavior tests before implementation, then ran:

```text
python -m pytest tests/test_ai_copy_linter.py -k "repeated_sentence_starts_report_every_cluster_and_all_lines or repeated_instructional_imperative_starts_are_warnings" -q
```

Result: `2 failed, 56 deselected in 0.12s`.

- `test_repeated_sentence_starts_report_every_cluster_and_all_lines` failed with `KeyError: 'lines'` because the old diagnostic did not expose cluster lines.
- `test_repeated_instructional_imperative_starts_are_warnings` failed because the old finding severity was `error`, not `warning`.

## Implementation

- Split the oversized linter into `data_sources/modules/ai_copy_lint/` by responsibility:
  - `rules.py`: static patterns and rule definitions.
  - `scanning.py`: active markdown-line detection and span masking.
  - `diagnostics.py`: structured finding creation, repeated-opener diagnostics, sentence length, and title-case checks.
  - `core.py`: lint orchestration and public API behavior.
- Kept `data_sources/modules/ai_copy_linter.py` as a 33-line compatibility facade and CLI entry point.
- Added `tests/test_ai_copy_linter_repetition.py` for the new behavior without modifying the pre-existing 647-line test file.
- Repeated opener findings now include every cluster, the normalized opener, every source line, and a message naming those lines.
- Repeated imperative openers in recognized instructional context now produce warnings; non-instructional repetition remains an error.

## GREEN Evidence

```text
python -m pytest tests/test_ai_copy_linter.py tests/test_ai_copy_linter_repetition.py tests/test_source_support_instructional_context.py tests/test_changed_python_line_guard.py -q
```

Result: `78 passed in 0.56s`.

```text
python -m pytest tests/test_publish_readiness.py tests/test_humanizer_quality_corpus.py -q
```

Result: `79 passed in 77.99s`.

```text
python tools/check_changed_python_lines.py --base main
```

Result: exit `0`; no changed Python file exceeded 500 physical lines.

```text
python data_sources/modules/ai_copy_linter.py --help
```

Result: exit `0`; direct script execution remains available.

```text
python -c "from data_sources.modules.ai_copy_linter import lint_content; print(lint_content('Add the job ID.\nAdd the approval date.\nAdd the owner name.')[0])"
```

Result included `severity: 'warning'`, `match: 'add the'`, and `lines: [1, 2, 3]`.

```text
git diff --check
```

Result: exit `0`.

## Fix Round 2

### RED Evidence

Added regression tests for declarative repeated openers in both recognized instructional forms, then ran:

```text
python -m pytest tests/test_ai_copy_linter_repetition.py -k "table_declarative or checklist_declarative" -q
```

Result: `2 failed, 4 deselected in 0.16s`.

- `Status remains...` repetitions in a `What to write` table incorrectly returned `warning`.
- `Status remains...` repetitions in a recognized checklist incorrectly returned `warning`.

### Fix

The repetition diagnostic now requires both shared instructional context and an imperative opener. It normalizes leading table and checklist syntax before matching a deliberately broad instructional-verb set that includes `Add` and `Review`, while declarative openers such as `Status remains` stay errors.

### GREEN Evidence

```text
python -m pytest -q tests/test_ai_copy_linter_repetition.py tests/test_ai_copy_linter.py tests/test_source_support_instructional_context.py
```

Result: `80 passed in 0.74s`.

```text
python tools/check_changed_python_lines.py --base d43c124 --limit 500
```

Result: exit `0`; no changed Python file exceeded 500 physical lines.

```text
git diff --check
```

Result: exit `0`.

## Files Changed

- `data_sources/modules/ai_copy_linter.py`
- `data_sources/modules/ai_copy_lint/__init__.py`
- `data_sources/modules/ai_copy_lint/rules.py`
- `data_sources/modules/ai_copy_lint/scanning.py`
- `data_sources/modules/ai_copy_lint/diagnostics.py`
- `data_sources/modules/ai_copy_lint/core.py`
- `tests/test_ai_copy_linter_repetition.py`

## Self-Review

- Verified existing public imports and direct CLI execution after the split.
- Preserved existing exception handling, masking behavior, Humanizer handling, sort order, and generic rule execution through the existing suite and dependent readiness tests.
- Confirmed all changed and new Python files are below 500 lines. The prior monolithic module is now 33 lines.
- The new `lines` field is additive, so existing finding consumers retain their established keys and behavior.

## Concerns

None. The `git diff --no-index` inspection command used during final review returned exit code 1 by Git design when showing a new file; it was not a test or implementation failure.

## Fix Round 1

### RED Evidence

Added regression tests for both recognized instructional forms before changing implementation, then ran:

```text
python -m pytest tests/test_ai_copy_linter_repetition.py -k "what_to_write_table or checklist_imperative" -q
```

Result: `2 failed, 2 deselected in 0.12s`.

- Repeated `Add the...` rows in a `What to write` table returned `error` instead of `warning`.
- Repeated `Review the...` checklist items returned `error` instead of `warning`.

### Fix

`_repeated_opener_severity` now derives warning severity from the shared PM-08 recognized instructional-line context for every occurrence in a cluster. It no longer tries to match the raw sentence, which retains table-row prefixes and excludes valid checklist imperatives such as `Review`.

### GREEN Evidence

```text
python -m pytest tests/test_ai_copy_linter_repetition.py tests/test_ai_copy_linter.py tests/test_source_support_instructional_context.py -q
```

Result: `78 passed in 0.48s`.

```text
python tools/check_changed_python_lines.py --base d43c124 --limit 500
```

Result: exit `0`; no changed Python file exceeded 500 physical lines.

```text
git diff --check
```

Result: exit `0`.
