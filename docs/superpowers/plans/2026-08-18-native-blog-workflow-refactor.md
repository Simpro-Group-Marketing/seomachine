# Native-Core Blog Workflow Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the original native blog commands and specialist-agent handoffs while keeping connector proof, BOM v1, scoring, readiness, receipts, and publisher transport as Python-owned governance.

**Architecture:** `/research` to `/write` is the canonical new-blog route and `/analyze-existing` to `/rewrite` is the canonical rewrite route. Only `/write`, `/rewrite`, and `/optimize` persist public Markdown. Specialist agents return findings against immutable snapshots, Python validates and attests the workflow without authoring copy, and `/publish-readiness` alone decides release status.

**Tech Stack:** Claude command and agent Markdown, Python 3, pytest, existing BOM v1 and readiness modules.

**Spec:** User-approved in-chat plan dated 2026-08-18.

## Global Constraints

- Work only in `.worktrees/native-blog-workflow-refactor-20260818`.
- Preserve unrelated dirty work and never reset the main checkout.
- Never synthesize customer proof, claims, metrics, rankings, PAA questions, quotes, or vault evidence.
- Python must not create, edit, move, or delete public Markdown under `drafts/`, `rewrites/`, `published/`, or `review-required/`.
- Keep `simpro-blog-assembly-bom/v1`, its guard, stage receipts, context binding, proof gates, readiness attestation, and publisher readback.
- Content quality passes at 85 or higher.
- SEO quality passes at 90 or higher with zero critical SEO issues.
- AEO/GEO passes at 90 or higher.
- Default tests must not require live connectors, browsers, or CMS services.
- Final Python test LOC must not exceed 27,000.

---

### Task 1: Restore the Native Command and Agent Contract

**Files:** `.claude/commands/`, `.claude/agents/`, compact workflow contract tests.

- [ ] Write failing tests for the canonical command routes, `/article` removal, original-agent handoffs, and advisory-only agent status.
- [ ] Remove `/article`; change all active command and documentation references to `/research` followed by `/write`.
- [ ] Make `/write`, `/rewrite`, and `/optimize` the only public Markdown owners.
- [ ] Restore compact handoffs to `content-analyzer`, `editor`, `seo-optimizer`, `meta-creator`, `internal-linker`, and `keyword-mapper`.
- [ ] Keep `performance` upstream and exclude later landing/cluster/CRO agents from the blog route.
- [ ] Run the command and agent contract tests.

### Task 2: Preserve BOM v1 Without Python Copy Mutation

**Files:** `data_sources/modules/blog_assembly_stage_receipt.py`, BOM modules, stage-receipt tests.

- [ ] Write failing tests for `begin-native-edit` and `finish-native-edit` against absent drafts and existing optimization inputs.
- [ ] Move the minimal start/finish attestation behavior into the existing stage-receipt module.
- [ ] Record an absent new draft without creating it; require a changed final hash before writing the detached receipt.
- [ ] Preserve draft and optimization mutation receipts, evidence hashes, previous-receipt chaining, and BOM v1 validation.
- [ ] Keep `blog_assembly_mutation_recorder.py` deleted.
- [ ] Run stage-receipt and BOM tests.

### Task 3: Enforce Governance-Only Output Paths

**Files:** shared BOM contract helper and every Python module with a caller-controlled output path.

- [ ] Write failing parameterized tests proving governance writers reject destinations under all public article roots.
- [ ] Add one resolved-path guard that also rejects collisions with bound inputs.
- [ ] Apply it to edit state/receipts, scrub receipts, context binding, selector evidence, PAA evidence, BOM outputs, readiness outputs, and other caller-controlled governance destinations.
- [ ] Keep research sidecars, context JSON, caches, and remote publisher transport valid.
- [ ] Run focused path and governance tests.

### Task 4: Complete Scrub, Scorecard, and Publisher Boundaries

**Files:** scrubber, readiness/scoring modules, Grav publisher, focused tests.

- [ ] Write failing tests proving dirty scrub runs cannot mint completed receipts and Grav CLI dry-run does not read `preview_path`.
- [ ] Keep scrub read-only; issue a completed receipt only after a clean scan.
- [ ] Make `seo_quality_rater.PUBLISHING_THRESHOLD` the authoritative SEO threshold consumed by scoring and readiness.
- [ ] Keep independent content, SEO, and AEO/GEO gates in readiness and reject any failed component.
- [ ] Allow deterministic transport serialization but no local Markdown preview or semantic rewrite.
- [ ] Run scrub, scorer, readiness, and publisher tests.

### Task 5: Delete Dead Workflow Code and Centralize Policy

**Files:** dead modules, command docs, strategy, README, quick start, dependency manifests.

- [ ] Delete `article_planner.py`, `section_writer.py`, `competitor_gap_analyzer.py`, `social_research_aggregator.py`, and `engagement_analyzer.py` after a final reference scan.
- [ ] Keep detailed connector, proof, BOM, and recovery policy only in `AGENTS.md` and `context/aeo-geo-blog-strategy.md`.
- [ ] Keep commands to usage, ownership, sequence, handoff, and score thresholds; keep their combined blog workflow documentation below 500 lines.
- [ ] Replace repeated README and quick-start prose with the canonical route table.
- [ ] Remove only dependencies with no retained imports.
- [ ] Run import, reference, and documentation checks.

### Task 6: Reduce Test Duplication Without Reducing Safety

**Files:** `tests/fixtures/` and oversized guard, BOM, proof, scorer, and publisher suites.

- [ ] Create three focused fixture modules for content evidence, sealed workflows, and publisher contracts.
- [ ] Replace copied article, context, proof, PAA, readiness, and BOM fixtures with shared builders.
- [ ] Parameterize equivalent malformed, stale, forged, collision, threshold, and hash-tamper cases.
- [ ] Retain distinct context, proof, BOM, readiness, publisher, and native-ownership failure classes.
- [ ] Confirm total Python test LOC is no more than 27,000.

### Task 7: Final Verification

- [ ] Run `python -m pytest tests --collect-only -q`.
- [ ] Run the focused native workflow, BOM, readiness, and publisher suites.
- [ ] Run `python -m pytest tests -q`.
- [ ] Run the deleted-module reference scan, retained dependency import scan, test LOC check, and `git diff --check`.
- [ ] Review the complete diff against this plan before reporting completion.
