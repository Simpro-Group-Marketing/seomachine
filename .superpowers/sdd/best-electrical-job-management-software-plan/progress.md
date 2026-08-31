# SDD ledger — plan: .superpowers/sdd/best-electrical-job-management-software-plan.md

## Preflight

BASE: 887522eed6507b033d9cafc57a0f730b5cb11905

| Scope | Produces / consumes | Conflict scan | Ruling |
|---|---|---|---|
| Task 1 ↔ Task 2 | Task 1 evidence, brief, sidecar, and plan feed Task 2 rewrite | Task 2 must not draft Simpro-specific language before Task 1 has a validated pack | Ruling: enforce the connector gate and use generic placeholders only in private planning artifacts; public copy waits for validation. Cost if wrong: drafting may be delayed by connector recovery. |
| Task 1 ↔ Task 3 | Task 1 sidecar and selectors feed Task 3 receipts/readiness | Task 3 must bind exact final bytes and cannot repair stale receipts | Ruling: any sidecar/context change reseals dependent receipts before release. Cost if wrong: release artifacts may need regeneration. |
| Task 2 ↔ Task 3 | Task 2 article bytes feed reviews, scrub, BOM, and publish readiness | Any article edit invalidates downstream reviews and receipts | Ruling: treat the rewrite as immutable between each gate and rerun the complete dependent chain after edits. Cost if wrong: stale evidence could falsely pass. |
| Task 1 | Analysis, context, research, source maps, selectors, editorial plan | Self-consistent; all outputs are required inputs to Task 2/3 | Ruling: preserve `Selected: [none]` for customer/Fred public use unless evidence proves otherwise, per approved plan. Cost if wrong: lost optional E-E-A-T enrichment. |
| Task 2 | Dated rewrite with metadata, matrices, FAQs, links, assets, schema | Self-consistent; exact nine-tool order and seven FAQ headings are locked | Ruling: retain the existing URL and create a rewrite artifact because no checked-in target article exists. Cost if wrong: CMS handoff remains external to this repo. |
| Task 3 | Reviews, receipts, BOM, readiness, release result | Self-consistent; release is blocked by unresolved proof or author/reviewer gates | Ruling: no external publish or merge is authorized by this request; stop at verified local handoff if gates remain blocked. Cost if wrong: additional release coordination is required. |

## Task status

- Baseline targeted governance tests: 603 passed, 139 subtests passed in 45.27s. Full default suite timed out after 124s without assertion output; deterministic collection succeeded (1,755 tests).
- Task 1: partial - context and planning artifacts committed; external research and release blockers are recorded in task-1-report.md
- Task 2: pending
- Task 3: pending
