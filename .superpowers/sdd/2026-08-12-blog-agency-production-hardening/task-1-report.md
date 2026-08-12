# Task 1 Report: Agency Ownership and Drift Locks

## Implementation

- Added behavioral architecture coverage for the canonical command matrix, the existing agent set, command-declared repository agents, customer-proof semantic parity, and the exclusive four-step seal owner.
- Normalized `.agents/rules/customer-proof.md`, `.claude/rules/customer-proof.md`, and `.cursor/rules/customer-proof.mdc` to one rule body. Cursor frontmatter is the only wrapper difference.
- Added `--context-pack`, `--context-receipt`, and `--evidence-output` to both mandatory customer-proof selector commands on every platform rule.
- Moved all executable build -> preflight -> finalize -> final recipes out of non-owner command and steering documents. `/publish-readiness` remains the only executable seal owner; other surfaces retain route-specific receipts and reference it for sealing.
- Replaced affected older workflow-document expectations with owner-focused behavior assertions.

## RED Evidence

Command:

```powershell
python -m unittest tests.test_blog_agency_architecture
```

Output summary:

```text
FAILED (failures=7)
```

Expected failures:

- Customer-proof rules had two normalized bodies rather than one.
- `README.md`, `context/aeo-geo-blog-strategy.md`, and `/article`, `/write`, `/rewrite`, and `/optimize` each owned the four-step recipe in addition to `/publish-readiness`.

## GREEN Evidence

Focused command:

```powershell
python -m pytest tests/test_blog_agency_architecture.py tests/test_aeo_geo_workflow_docs.py -q --durations=10
```

Output summary:

```text
111 passed, 81 subtests passed in 1.97s
```

The slowest focused test was 0.92s. No Task 1 architecture or workflow-document test showed pathological timing.

Full-suite command run before the later pytest diagnostic:

```powershell
python -m unittest discover -s tests
```

Output summary:

```text
Ran 1002 tests in 27.679s
OK (skipped=1)
```

Bounded pytest diagnostic command:

```powershell
python -m pytest -q --durations=20
```

Output summary:

```text
command timed out after 63190 milliseconds
```

The timeout emitted no test-progress or duration output. Process inspection showed concurrent non-Task-1 pytest processes in the shared workspace, including other focused tests and a separate full `python -m pytest -q` process, so this timeout does not identify a Task 1 test regression. No test-performance code change was justified by the focused evidence.

## Files Changed

- `.agents/rules/customer-proof.md`
- `.claude/rules/customer-proof.md`
- `.cursor/rules/customer-proof.mdc`
- `.claude/commands/article.md`
- `.claude/commands/write.md`
- `.claude/commands/rewrite.md`
- `.claude/commands/optimize.md`
- `README.md`
- `context/aeo-geo-blog-strategy.md`
- `tests/test_blog_agency_architecture.py`
- `tests/test_aeo_geo_workflow_docs.py`

## Self-Review

- The command matrix and agent-set assertions use exact repository definitions, so renamed workflow drivers, replacement commands, reviewer agents, and unresolved declared agent capabilities fail architecture tests.
- Customer-proof parity compares normalized rule bodies and parsed selector flags/roles, rather than relying on isolated substrings.
- Only `/publish-readiness` retains all four executable seal operations; route documents retain their mutation, scrub, and Context Binding behavior without duplicating the seal.
- `git diff --check` completed without whitespace errors before this report was added.

## Concerns

- The focused Task 1 suite is green and fast. The later full pytest diagnostic exceeded its 60-second bound under concurrent shared-workspace pytest activity. The earlier full unittest suite passed in 27.679s. A clean, serialized full pytest timing run is still needed to establish a reliable pytest baseline, but is outside this narrowly scoped Task 1 change.

## Review Remediation

- Made `/publish-readiness` decision-complete for the existing research-input variants. The central recipe now has mutually exclusive new/rewrite-without-pre-picked-PAA and rewrite-with-pre-picked-PAA build variants. The optimized reseal specifies `--optimizer-output` and `--prior-preflight-readiness` without duplicating the full recipe in route commands.
- Expanded route-matrix assertions from file existence to route behavior for article, research-to-write, analysis-to-rewrite, cleanup, optional optimization, readiness, WordPress handoff, and Grav handoff.
- Expanded sole-owner coverage to all `.claude/commands`, root steering files, canonical strategy, and all three rule directories. The parser recognizes multiline Python seal commands and only rejects a complete four-step recipe outside the owner, leaving route delegation and invocations valid.
- Restored the identical selected/rejected-row editorial-judgment policy to all three customer-proof rule surfaces.
- Changed selector parsing to retain every command for a role. A duplicate role can no longer overwrite and hide an earlier malformed selector command.

### Review RED Evidence

Command:

```powershell
python -m pytest tests/test_blog_agency_architecture.py -q
```

Output summary:

```text
26 failed, 7 passed, 27 subtests passed in 0.40s
```

The initial failures exposed the missing central rewrite/optimization build variants and missing customer-proof row-edit policy. The first expanded surface assertion also showed that unrelated steering rules do not need to mention `/publish-readiness`; that expectation was removed before production changes because it would reject valid non-workflow rules.

### Review GREEN Evidence

Command:

```powershell
python -m pytest tests/test_blog_agency_architecture.py tests/test_aeo_geo_workflow_docs.py -q
```

Output summary:

```text
114 passed, 118 subtests passed in 1.87s
```

## Final Re-Review Remediation

- Added the third mutually exclusive BOM research-input variant to the central `/publish-readiness` recipe: `--user-paa-csv` with `--answersocrates-blocker`. The optimization reseal instruction now applies to the PAA-artifact, rewrite-brief, and CSV-plus-blocker variants.
- Replaced marker checks for build variants with semantic parsing that asserts the precise eligible research-input flag sets.
- Expanded sole-owner scanning to every root Markdown file, all commands, all three rule directories, and the canonical strategy. The scanner dynamically finds future root Markdown steering files and parses `python`, `python.exe`, and `py` launch forms, path separators, optional relative prefixes, and multiline commands.
- Replaced route marker checks with parsed command-delegation relationships, receipt-driver checks, and a derived repository-capability check for command, agent, and skill references in route surfaces.
- Strengthened customer-proof selector parsing to retain duplicate role commands and to reject required flags that lack a value.

### Final Re-Review RED Evidence

Command:

```powershell
python -m pytest tests/test_blog_agency_architecture.py -q
```

Output summary:

```text
3 failed, 8 passed, 32 subtests passed in 0.17s
```

The failures showed the absent CSV-plus-blocker owner variant and an initial scanner bug that allowed the preflight command block to consume a later final phase. The scanner was corrected by splitting at each repository module-launch boundary before classifying operations.

### Final Re-Review GREEN Evidence

Command:

```powershell
python -m pytest tests/test_blog_agency_architecture.py tests/test_aeo_geo_workflow_docs.py -q
```

Output summary:

```text
117 passed, 143 subtests passed in 1.30s
```
