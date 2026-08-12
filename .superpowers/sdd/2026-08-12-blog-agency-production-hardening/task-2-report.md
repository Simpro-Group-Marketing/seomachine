# Task 2 Report: BOM Route and Repository Execution Provenance

## Implementation

- Added a closed `blog_assembly_capabilities` registry for the current `article-command`, `write-command`, `rewrite-command`, and optional `optimize-command` identities at version `1`.
- Bound canonical current repository bytes for invoked command and agent definitions plus one distinct Markdown diagnostic report per invoked agent. The BOM schema remains `simpro-blog-assembly-bom/v1` and the build -> preflight -> finalize -> final lifecycle is unchanged.
- Made route identity derive only from the signed draft receipt. Unknown routes, wrong command versions, stale definitions, missing or extra agents, external paths, invented capabilities, and undeclared conditional skills fail closed.
- Flattened nested execution evidence into the existing readiness input snapshot so preflight and final-readiness attestations bind each `command_definition.*`, `agent_definition.*`, `agent_output.*`, and declared `skill_definition.*` artifact independently.
- Required draft receipts to bind their route command and exact route agent definitions. Optimization receipts bind the optimize command, the deduplicated route-plus-optimize agent definitions, and every final agent report.
- Removed the aggregate optimizer-report contract. `optimizer_outputs` must exactly mirror the ordered distinct `agent_output.*` rows; one aggregate artifact cannot stand in for five agent executions.
- Hardened mutation recording so callers cannot supply repository definition hashes, draft mutations cannot claim agent outputs, optimization uses only `optimize-command` version `1`, and its five output files must use the canonical `research/agent-outputs/<agent-id>-*.md` convention.
- Updated the four route commands to invoke and save their exact current agent sets: five for article/write/optimize and four for rewrite. Agent reports remain diagnostic and `/publish-readiness` remains the sole handoff authority.

## TDD Evidence

Baseline command before Task 2 production changes:

```powershell
python -m pytest -q tests/test_blog_agency_architecture.py tests/test_blog_assembly_contract.py tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_guard.py tests/test_blog_assembly_mutation_recorder.py tests/test_publish_readiness.py tests/test_aeo_geo_workflow_docs.py
```

Baseline result:

```text
308 passed, 156 subtests passed
```

The new behavioral tests were introduced around the missing registry, nested readiness binding, exact route inventories, repository-definition receipt bindings, optimizer output separation, mutation authority, stale definition rejection, and diagnostic-only authority. Implementation followed those failing expectations in small registry, BOM, guard, mutation, and documentation increments.

Final focused provenance command:

```powershell
python -m pytest -q tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_guard.py tests/test_blog_assembly_capabilities.py tests/test_blog_assembly_mutation_recorder.py
```

Result:

```text
131 passed in 51.71s
```

Final adjacent architecture/readiness command:

```powershell
python -m pytest -q tests/test_blog_agency_architecture.py tests/test_blog_assembly_contract.py tests/test_publish_readiness.py tests/test_aeo_geo_workflow_docs.py
```

Result:

```text
198 passed, 180 subtests passed in 7.00s
```

Final full-suite command:

```powershell
python -m pytest -q
```

Result:

```text
1541 passed, 3 skipped, 458 subtests passed in 142.84s
```

Post-review mutation-path command after adding canonical output-path validation:

```powershell
python -m pytest -q tests/test_blog_assembly_mutation_recorder.py tests/test_blog_assembly_integrity_hardening.py
```

Result:

```text
67 passed in 3.80s
```

Compilation and whitespace checks:

```powershell
python -m compileall -q data_sources/modules/blog_assembly_capabilities.py data_sources/modules/blog_assembly_contract.py data_sources/modules/blog_assembly_bom.py data_sources/modules/blog_assembly_bom_guard.py data_sources/modules/blog_assembly_mutation_recorder.py
git diff --check
```

Both completed successfully. Git emitted only the repository's normal LF-to-CRLF working-copy notices.

## Tests Added or Expanded

- Exact current route inference and command-version enforcement.
- Exact article, write, and rewrite command/agent inventories.
- Deduplicated rewrite-plus-optimize agent union.
- Internally resolved definition evidence and rejection of caller-supplied definition hashes.
- Missing, extra, invented, stale, external, and undeclared skill capability rejection.
- Nested execution-evidence flattening into readiness input hashes, including duplicate-label rejection.
- Draft receipt definition binding and fail-closed handling of historical weak receipts.
- Definition changes after BOM construction invalidate the BOM.
- Optimized and non-optimized flows, including exact distinct optimizer outputs.
- Draft-agent-output rejection, canonical optimization report paths, and retained replay/concurrency safeguards.
- Exact route-document output contracts and diagnostic-only agent authority.

## Self-Review

- Repository evidence proves only local identity and byte integrity. Module documentation explicitly avoids claims of model authorship, execution quality, or external truth.
- Definition paths and hashes are derived internally from the closed registry. No BOM or mutation API accepts caller-selected definition IDs or hashes.
- Execution evidence uses exact-key equality, not subset checks. Historical BOMs lacking the new bindings fail closed at both construction and guard validation.
- The existing BOM schema identifier, lifecycle, source verification, connector, proof, and final-readiness controls remain intact.
- The optimizer compatibility inventory is retained, but it can contain only the same distinct rows already bound as registry agent outputs.

## Files Changed

- `.claude/agents/content-analyzer.md`
- `.claude/agents/internal-linker.md`
- `.claude/agents/keyword-mapper.md`
- `.claude/agents/meta-creator.md`
- `.claude/agents/seo-optimizer.md`
- `.claude/commands/article.md`
- `.claude/commands/optimize.md`
- `.claude/commands/publish-readiness.md`
- `.claude/commands/rewrite.md`
- `.claude/commands/write.md`
- `data_sources/modules/blog_assembly_capabilities.py`
- `data_sources/modules/blog_assembly_bom.py`
- `data_sources/modules/blog_assembly_bom_guard.py`
- `data_sources/modules/blog_assembly_contract.py`
- `data_sources/modules/blog_assembly_mutation_recorder.py`
- `tests/test_aeo_geo_workflow_docs.py`
- `tests/test_blog_agency_architecture.py`
- `tests/test_blog_assembly_bom.py`
- `tests/test_blog_assembly_bom_guard.py`
- `tests/test_blog_assembly_capabilities.py`
- `tests/test_blog_assembly_contract.py`
- `tests/test_blog_assembly_integrity_hardening.py`
- `tests/test_blog_assembly_mutation_recorder.py`

## Concerns

- `optimizer_outputs` remains in BOM v1 for compatibility. It is no longer an independent or aggregate evidence channel; strict equality with the ordered `agent_output.*` rows prevents provenance ambiguity.
- The current registry declares no conditional blog skills. Any `skill_definition.*` row therefore fails closed until a future repository change explicitly adds a skill ID and canonical path.
