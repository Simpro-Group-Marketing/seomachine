# LLM Wiki Connector Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore production-ready topology-agnostic Simpro vault retrieval so the connector returns approved Simpro-scoped claims and repo publishing workflows require validated context packs and receipts.

**Architecture:** The vault owns bootstrap discovery, manifests, indexes, policies, and claim registry generation. The repo owns the connector client, publish gates, public artifact guards, and plugin installation for the current working project. The plugin cache is deployment output only, not the source of truth.

**Tech Stack:** Python, pytest, PowerShell, Git worktrees, Claude local plugin CLI, JSONL vault protocol artifacts.

## Global Constraints

- Only the vault root may be configured; no consumer may hard-code vault hubs, filenames, or internal directories.
- Public brand scope for this connector and repo is `Simpro`.
- Human-reviewed source approval statuses remain authority; generator metadata cannot create new public-use approval.
- Existing dirty files in `C:\Users\patrick.grueschow\Desktop\Repos\seomachine-main` are user-owned and must be preserved.
- Work must happen in `C:\Users\patrick.grueschow\Desktop\Repos\seomachine-llm-wiki-fix` unless the specific file is a vault-owned protocol source or generated artifact.
- Vault backup exists at `C:\Users\patrick.grueschow\Desktop\vault-protocol-backups\20260805-152705-llm-wiki-connector-fix`.

---

### Task 1: Vault Claim Approval Generation

**Files:**
- Modify: `C:\Users\patrick.grueschow\Desktop\Obsidian\Simpro Brand Context\system\scripts\build-agent-retrieval-protocol.py`
- Modify: `C:\Users\patrick.grueschow\Desktop\Obsidian\Simpro Brand Context\system\scripts\tests\test_build_agent_retrieval_protocol.py`
- Generated later: `C:\Users\patrick.grueschow\Desktop\Obsidian\Simpro Brand Context\indexes\agent-claim-registry.jsonl`
- Generated later: vault manifest, catalog, search index, bootstrap hashes

**Interfaces:**
- Produces claim records where approved Simpro rows have `approval_status: "approved"`, `brand_scope: ["Simpro"]`, and non-empty `permitted_use_modes`.
- Keeps receipt requirements out of registry generation and leaves receipt enforcement to context validation and publish gates.

- [ ] Write failing pytest assertions showing approved Simpro authority, Fred, metric, review-theme, case-study paraphrase, and Lightning rows are approved.
- [ ] Write negative pytest assertions for unverified, unsupported brand, mixed public brand, quoted metric without exact quote authorization, missing evidence URL, stale Fred join, and internal-only rows.
- [ ] Run the vault test file and confirm the new assertions fail for the existing zero-approved behavior.
- [ ] Remove unconditional `connector_context_receipt_required` from claim generation.
- [ ] Add Simpro default scope normalization for blank-scope rows while preserving explicit unsupported or internal-only blocks.
- [ ] Preserve source verification, allowed use, exact quote, public URL, expiration, superseded, and Fred join blockers.
- [ ] Run the vault test file and confirm it passes.

### Task 2: Repo Connector Recovery

**Files:**
- Restore/modify: `data_sources/modules/simpro_vault_client.py`
- Restore/modify: `data_sources/modules/context_binding_guard.py`
- Restore/modify: `data_sources/modules/public_artifact_guard.py`
- Restore/modify: `data_sources/modules/publish_readiness.py`
- Restore/modify corresponding tests from recovered commits `83968d6` and `23c7bd1`

**Interfaces:**
- `simpro_vault_client` resolves only explicit test roots or the configured `simpro-context@simpro` plugin `authority_root`.
- Publish readiness consumes current context pack and receipt inputs and blocks stale, tampered, missing, or invalid claim evidence.

- [ ] Cherry-pick `83968d6` into the isolated worktree and resolve conflicts by preserving current main behavior unless it weakens context enforcement.
- [ ] Cherry-pick `23c7bd1` into the isolated worktree and resolve conflicts by preferring the canonical connector client.
- [ ] Run targeted tests for the restored connector and publish gates.
- [ ] Search runtime code for hard-coded vault hub or filename references and remove any consumer-side dependency outside tests/migration fixtures.

### Task 3: Plugin Enablement

**Files/State:**
- Current repo path: `C:\Users\patrick.grueschow\Desktop\Repos\seomachine-main`
- Vault root: `C:\Users\patrick.grueschow\Desktop\Obsidian\Simpro Brand Context`
- Installed plugin cache: `C:\Users\patrick.grueschow\.claude\plugins\cache\simpro\simpro-context\1.2.2`

**Interfaces:**
- Exactly one enabled local `simpro-context@simpro` entry must point at the current repo path.
- Stale disabled entries pointing at deleted worktrees must not be used as active connector state.

- [ ] Inspect available `claude plugin` install/enable/config commands.
- [ ] Install or enable `simpro-context@simpro` for the current repo path with only `authority_root` configured.
- [ ] Verify `claude plugin list --json` shows the current repo entry enabled.
- [ ] Verify direct CLI and MCP entrypoints can call `vault_status` using the configured vault root.

### Task 4: Vault Artifact Rebuild and E2E Verification

**Files:**
- Generated vault protocol artifacts under `indexes\` and `system\retrieval\`
- Repo tests under `tests\`

**Interfaces:**
- `vault_status` returns `ready` and includes a non-zero approved Simpro claim count or equivalent usable-claim health.
- `vault_claims` returns approved records for valid Simpro proof-sensitive queries.

- [ ] Run the vault protocol builder from the vault root.
- [ ] Verify rebuilt bootstrap artifact hashes match generated file hashes.
- [ ] Run `vault_status`.
- [ ] Run `vault_claims` for authority, Fred, review-theme, case-study, and metric queries.
- [ ] Run `vault_search`, `vault_read`, `vault_expand`, `vault_build_context`, and `vault_validate_context` canaries.
- [ ] Run repo targeted tests: connector client, context binding guard, public artifact guard, publish readiness, customer proof selector, Fred authority selector, named feature status guard.
- [ ] Run a static regression search for hard-coded vault routes in runtime consumers.
- [ ] Report all changed files, rebuilt vault artifacts, plugin state, and verification output.
