# Blog Agency Production Hardening

## Goal

Harden the existing repository as one automated blog-writing agency while preserving its current slash commands, agents, skills, vault workflow, BOM schema, readiness lifecycle, and publishing entrypoints.

## Global Constraints

- `context/aeo-geo-blog-strategy.md` remains the canonical blog policy.
- `.claude/commands` remains the orchestration contract.
- Existing repository agents and skills are the execution plane; deterministic Python modules are enforcement mechanisms; the BOM is the control plane and execution ledger.
- `/publish-readiness` is the sole publication-readiness authority.
- Preserve `/article`, `/research` -> `/write`, `/analyze-existing` -> `/rewrite`, `/scrub`, `/optimize`, `/publish-readiness`, `/publish-draft`, and `grav-publish`.
- Keep `simpro-blog-assembly-bom/v1`; weak historical artifacts fail closed and are regenerated.
- Add no replacement orchestrator, slash command, reviewer agent, parallel skill stack, human editorial gate, or live publication.
- Use only repository-owned commands, agents, and skills.
- Keep `review-required/` as automated quarantine, not a human editorial queue.
- Preserve unrelated user changes.
- Follow TDD for every production behavior change and retain red/green evidence.

## Task 1: Agency Ownership and Drift Locks

- Add behavioral architecture tests for the canonical route matrix and existing agent set.
- Normalize the customer-proof contract across `.agents/rules`, `.claude/rules`, and `.cursor/rules`; Cursor frontmatter is the only permitted wrapper difference.
- Ensure all three customer-proof rules include `--context-pack`, `--context-receipt`, and `--evidence-output` for both selector commands.
- Replace weak substring-only rule checks with normalized semantic comparisons of command names, flags, and required rule sections.
- Establish `/publish-readiness` as the only owner of the complete four-step seal recipe. Other command and steering surfaces reference it and retain only route-specific behavior.
- Add tests rejecting replacement workflow names, new reviewer roles, and external capability identifiers.

## Task 2: BOM Route and Repository Execution Provenance

- Preserve the BOM v1 schema identifier and existing build -> preflight -> finalize -> final lifecycle.
- Infer route identity from existing draft tool names: `article-command`, `write-command`, or `rewrite-command`, with optional `optimize-command` evidence.
- Bind `command_definition.<id>`, `agent_definition.<id>`, `agent_output.<id>`, and conditional `skill_definition.<id>` through existing receipt evidence hashes.
- Resolve every definition ID to its canonical repository path and current SHA-256; reject missing, stale, extra, invented, or external capabilities.
- Require the exact declared agent set for each route. Any agent-driven public-copy change must enter an optimization mutation and reseal.
- Keep all agent readiness language diagnostic; only `/publish-readiness` may authorize handoff.

## Task 3: Shared Artifact and Receipt Integrity

- Centralize strict JSON loading, artifact byte snapshots, gate inventory, and stage sequences.
- Reject duplicate keys, invalid UTF-8, excessive size, `NaN`, `Infinity`, non-finite values, and Boolean-as-number misuse.
- Hash and parse the same byte snapshot to prevent hash-then-reopen races.
- Bind one run ID to the canonical article identity across every stage receipt.
- Reject future, stale, out-of-order, or cross-run receipt timestamps.
- Require every evidence hash to resolve to a BOM artifact, sidecar binding, or repository capability definition.
- Consume mutation state once using an ignored local ledger keyed by the existing state hash; copied/restored state must not replay.
- Continue describing execution attestation as local integrity, not external truth.

## Task 4: Genuine Research and Source Provenance

- Make `paa_provenance_guard.py record` parse raw Playwright capture or blocker output rather than trust caller-authored questions or blocker facts.
- Keep `scripts/research_serp_analysis.py` as the only production SERP evidence emitter and bind its raw DataForSEO or Playwright capture.
- Bind collector identity, query, timestamp, run ID, raw-capture path, and raw-capture hash.
- Reject fabricated, unsigned, raw-unbound, stale, future, or query-mismatched evidence.
- Derive source class and relationship from approved repository/vault-backed source decisions, not writer-provided labels.
- Preserve the required vault health -> describe -> semantic search -> read/expand -> approved claims -> context-pack workflow and fail-closed fallback rule.

## Task 5: Proof, E-E-A-T, Editorial Plan, and Quality Gates

- Add `competitive_shortlist` to the existing readiness inventory and validate the current `Competitive Shortlist Decision` sidecar block against connector evidence and final copy.
- Make source support cover detected factual, comparative, causal, commercial, absolute, and guarantee claims, with narrow exemptions only for explicit opinion, instructions, and non-outcome scenarios.
- Require FAQ Proof Map support plus attested neutral/non-competing source classification.
- Enforce proof diversity: any recent use warns; repeated selection requires a source-specific reason and comparison with suitable zero-use evidence.
- Expand final plan binding across Reader Contract payoff, headings, must-have sections, gaps, section objectives, original contributions, entities, internal links, FAQ decision, and CTA.
- Do not grant Expertise or Experience for author metadata alone. Experience requires selected, source-visible customer/review evidence.
- Prevent short/incomplete articles and irrelevant answer capsules from receiving passing world-class scores.

## Task 6: Existing Automated Agent and Skill Alignment

- Use the existing `editor`, `content-analyzer`, `seo-optimizer`, `meta-creator`, `internal-linker`, and `keyword-mapper` agents across `/article`, `/write`, `/rewrite`, and `/optimize`.
- Run deterministic preflight gates before agent optimization; every agent mutation restarts the existing optimization -> scrub -> context-binding -> preflight -> finalize -> final sequence.
- Keep keyword density diagnostic, meta lengths intent/truncation guidance, and structured data free of rich-result promises.
- Prevent prompts from encouraging invented people, numbers, outcomes, or unsupported specificity.
- Ensure blog-relevant skills defer to the vault, canonical blog policy, and `/publish-readiness`; local product-marketing context cannot override the vault.
- Define `review-required/` as terminal automated quarantine with machine-generated diagnostics after two unsuccessful repair cycles.

## Task 7: Final-Readiness Publisher Boundary

- Make readiness phase explicit and mandatory for internal API and CLI callers.
- Require `phase="final"`, a final BOM, and matching detached final-readiness attestation before any WordPress, Grav, or GitHub mutation.
- Ensure provisional/preflight-only inputs result in zero network calls.
- Build the CMS payload from the exact verified article snapshot and revalidate the complete input snapshot immediately before mutation.
- Read back WordPress content, metadata, and status; read back Grav commit content; require exact parity.
- Keep source-artifact readiness distinct from CMS/rendered-page verification.

## Task 8: Golden Workflows and Closure

- Add deterministic golden workflows for `/article`, `/research` -> `/write`, and `/analyze-existing` -> `/rewrite`, with and without optimization, for connector-required and non-connector content.
- Fake only external vault/browser/CMS boundaries.
- Run adversarial regressions covering strict JSON, path/hash replay, TOCTOU, mutation replay, run mismatch, fabricated evidence, stale/future evidence, unsupported claims, FAQ source misclassification, missing shortlist/plan payoff, false E-E-A-T, short content, and irrelevant capsules.
- Run one live non-publishing vault/collector canary when the configured integration is available.
- Run the complete Windows test suite and independent whole-branch code review.
- Completion requires every review finding mapped to a passing regression and no publisher network access without final readiness.
