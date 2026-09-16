# Task 2 Report: PM-05

## Status

Complete.

## Requirement

Make `data_sources.modules.source_support.cli` executable with `python -m` while preserving `_main()` compatibility and existing JSON and exit-code behavior.

## Changes

- Added `main(argv=None)` as a public delegate to `_main(argv)`.
- Retained `_main()` unchanged as the compatibility entry point.
- Exported both `_main` and `main` through `__all__`.
- Added the `if __name__ == "__main__":` guard using `raise SystemExit(main())`.
- Added a real subprocess test using a temporary Markdown input. The test verifies successful exit, empty stderr, JSON output, the input path, the default `fail_on` value, and an empty findings list.

## TDD Evidence

RED was captured with:

```text
python -m pytest -q tests/test_source_support_cli.py
```

The test failed because module execution produced an empty stdout stream, causing `json.decoder.JSONDecodeError` while parsing the expected JSON.

GREEN was verified with:

```text
python -m pytest -q tests/test_source_support_cli.py
```

Result: `1 passed`.

The relevant source-support suite was verified with:

```text
python -m pytest -q tests/test_source_support_guard.py tests/test_source_support_batch.py
```

Result: `75 passed, 44 subtests passed`.

## Review

- `cli.py` is 40 physical lines.
- `test_source_support_cli.py` is 22 physical lines.
- `git show --check` passed.
- The commit contains only the source-support CLI, its subprocess test, and this required report.
- No article files were modified.

## Concerns

No known concerns. The test covers the successful subprocess path requested by PM-05. Existing `_main()` callers remain supported, and the guard propagates its integer result as the process exit code.

## Commit

Subject: `PM-05 make source-support CLI executable`
