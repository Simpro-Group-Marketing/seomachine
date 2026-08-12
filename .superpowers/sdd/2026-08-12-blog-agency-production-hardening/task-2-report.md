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

## Review Round 1 Remediation

- Designated the existing `preflight_readiness` stage receipt as the completion owner for non-optimized diagnostic reports without adding a stage or mutation. `validate_preflight_stage_receipt_binding` now requires `evidence_hashes` to equal every readiness input hash except `article` and `assembly_bom` exactly. This includes all flattened command definitions, agent definitions, route agent outputs, and any future declared skill definitions.
- The final BOM guard already consumes `validate_preflight_stage_receipt_binding`; a final-BOM regression now proves swapped agent output evidence fails through that guard path.
- Replaced all five later `write.md` Automatic Agent Execution `drafts/*` destinations with the canonical `research/agent-outputs/<agent-id>-[topic-slug]-[YYYY-MM-DD].md` destinations.
- Added a semantic route-document regression that extracts both `--agent-output` mappings and agent-associated `File` destinations across article, write, rewrite, and optimize. Each invoked agent must resolve to exactly one canonical destination anywhere in the command.

### Review Round 1 RED Evidence

Receipt-boundary command:

```powershell
python -m pytest -q tests/test_blog_assembly_bom.py -k "preflight_receipt_requires_exact_route_execution_evidence"
```

Result before the production fix:

```text
9 failed, 53 deselected in 7.65s
```

All article, write, and rewrite missing/extra/swapped cases failed because the validator did not raise.

Final-guard command:

```powershell
python -m pytest -q tests/test_blog_assembly_bom_guard.py -k "swapped_agent_outputs"
```

Result before the production fix:

```text
1 failed, 43 deselected in 6.70s
```

The final guard returned no finding for a re-attested readiness receipt with two agent output hashes swapped.

Route-document command:

```powershell
python -m pytest -q tests/test_blog_agency_architecture.py -k "route_agent_output_paths_have_no_conflicting_destinations"
```

Result before the documentation fix:

```text
5 failed, 1 passed, 14 deselected, 14 subtests passed in 0.16s
```

Only the five `write` agent destinations conflicted. Article, rewrite, and optimize were already canonical.

### Review Round 1 GREEN Evidence

Exact regression commands after the fixes:

```powershell
python -m pytest -q tests/test_blog_assembly_bom.py -k "preflight_receipt_requires_exact_route_execution_evidence"
python -m pytest -q tests/test_blog_assembly_bom_guard.py -k "swapped_agent_outputs"
python -m pytest -q tests/test_blog_agency_architecture.py -k "route_agent_output_paths_have_no_conflicting_destinations"
```

Results:

```text
9 passed, 53 deselected in 8.36s
1 passed, 43 deselected in 3.21s
1 passed, 14 deselected, 19 subtests passed in 0.06s
```

Focused covering command:

```powershell
python -m pytest -q tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_guard.py tests/test_publish_readiness.py tests/test_blog_agency_architecture.py tests/test_aeo_geo_workflow_docs.py
```

Result:

```text
280 passed, 199 subtests passed in 67.54s
```
