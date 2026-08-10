# Repository Reliability Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development` for every behavioral change, `superpowers:systematic-debugging` for unexpected failures, and `superpowers:verification-before-completion` before any completion claim. Parallel workers must own disjoint files.

**Goal:** Remove the production defects found by the repository-wide review while preserving proof-governed, topology-agnostic vault retrieval and all user-owned content changes.

**Architecture:** Keep the Simpro vault as the only brand/proof authority, with repo consumers using root configuration plus connector resource and claim IDs. Normalize publishable Markdown through one parser, seal source bytes across readiness and publishing, validate every external boundary, and make orchestration reports derive only from executed work and returned evidence.

**Tech Stack:** Python 3.11+, pytest, requests, Markdown, WordPress REST, GitHub CLI/Grav, Claude local plugin connector, PowerShell.

## Global Constraints

- Do not edit the user-owned article or validation sidecar currently modified under `published/` and `research/`.
- Do not restore legacy hub, filename, internal-route, repo-local factual, or marketingskills-plugin fallbacks.
- Public claims remain fail-closed and receipt-bound. Never weaken exact-quote, brand-scope, source-verification, or approval checks to make a test pass.
- Run each new regression test once red against the old behavior, then implement the smallest production fix and rerun green.
- Network, subprocess, and plugin boundaries need stable errors, finite timeouts, and negative tests.
- Bulk lint changes must be behavior-preserving and must not obscure the behavioral fixes.

---

### Task 1: Canonical connector discovery and error integrity

**Files:**
- Modify: `data_sources/modules/simpro_vault_client.py`
- Modify: `tests/test_simpro_vault_client.py`

- [ ] Add a failing test proving a legacy-only `simpro-context@marketingskills` install is rejected.
- [ ] Add a failing test proving a sole foreign-project canonical plugin is rejected while a global canonical install is permitted.
- [ ] Add a failing test proving a JSON error on stdout retains its stable connector error code even when stderr contains a warning.
- [ ] Remove legacy plugin discovery/config fallback, always enforce project scope, and parse structured error envelopes before generic stderr text.
- [ ] Run the focused connector suite.

### Task 2: Receipt-backed proof contract repair

**Files:**
- Modify: `data_sources/modules/vault_claim_receipts.py`
- Modify: `data_sources/modules/customer_proof_selector.py`
- Modify: `data_sources/modules/customer_proof_diversity_guard.py`
- Modify: `data_sources/modules/context_binding_guard.py`
- Modify: `data_sources/modules/fred_authority_guard.py`
- Modify: corresponding `tests/test_*.py`
- If required by the live contract: patch the authoritative Simpro connector source and deploy a versioned plugin build; never treat the cache copy as source.

- [ ] Capture real connector pack/receipt shapes for a customer proof, exact quote, and Fred source.
- [ ] Add real-contract regression fixtures without synthetic `selector_id` or `verbatim_evidence` fields.
- [ ] Establish a strict one-to-one proof join using connector-projected stable identity; reject missing or ambiguous joins.
- [ ] Treat missing pack/receipt inputs as a selector blocker with a nonzero CLI exit; distinguish that from a valid empty approved set and update command surfaces to pass the current artifacts.
- [ ] Preserve exact-quote text and source-verification metadata in approved evidence; do not weaken quote matching.
- [ ] Require the exact single public scope `Simpro`; mixed scopes must fail closed.
- [ ] Reject selected customer-proof overrides absent from receipt-validated candidates, both at generation and guard layers.
- [ ] Derive Fred verification requirements from approved source metadata rather than a sidecar-authored method.
- [ ] Run proof selector, receipt, binding, Fred, and diversity suites plus live claim canaries.

### Task 3: Context binding and brand-language enforcement

**Files:**
- Modify: `data_sources/modules/context_binding_guard.py`
- Modify: `data_sources/modules/vault_brand_language_guard.py`
- Modify: `data_sources/modules/publish_readiness.py`
- Modify: `data_sources/modules/named_feature_status_guard.py`
- Add/modify corresponding tests.

- [ ] Add a failing test for a landing-page request bound to a kindless blog artifact.
- [ ] Require or deterministically derive artifact kind, and reject conflicts between path, frontmatter, request, pack, and receipt.
- [ ] Bind brand-language hashes, revisions, resource IDs, and claim IDs to the actual validated context artifacts rather than accepting shape-only text.
- [ ] Add receipt-bound enforcement for the required Named Feature/Add-On Link Check.
- [ ] Replace static feature-name blind spots with connector/sidecar-declared evidence plus an unknown-feature fail-closed path; include the current AI CSR Agent regression without editing the user artifact.
- [ ] Add a realistic publish-readiness integration test that mocks only live vault/network boundaries.

### Task 4: Safe canonical Markdown publishing

**Files:**
- Add: `data_sources/modules/publishable_markdown.py`
- Modify: `data_sources/modules/wordpress_publisher.py`
- Modify: `data_sources/modules/grav_publisher.py`
- Modify: `tests/test_wordpress_publisher.py`
- Modify: `tests/test_grav_publisher.py`

- [ ] Add failing tests using realistic snake_case YAML, quoted scalars, list keywords, `target_url`, H1, and body content.
- [ ] Implement one normalized YAML-plus-legacy parser used by both publishers; strip private metadata from public body.
- [ ] Seal source bytes across readiness and publishing, recheck hashes after the gate, and publish only the sealed snapshot.
- [ ] Validate WordPress post type as one safe endpoint segment before any readiness or network call.
- [ ] Add finite WordPress request timeouts and bounded pagination.
- [ ] Make post-created/meta-failed outcomes explicit and idempotent rather than silently creating duplicates.
- [ ] Add a Grav subprocess timeout, explicit GET for SHA lookup, and distinguish 404 absence from other lookup errors.
- [ ] Make explicit and implicit Grav preview semantics consistent.

### Task 5: Landing-page and publishing workflow contract

**Files:**
- Modify: `.claude/commands/article.md`
- Modify: `.claude/commands/write.md`
- Modify: `.claude/commands/rewrite.md`
- Modify: `.claude/commands/optimize.md`
- Modify: `.claude/commands/publish-draft.md`
- Modify: `.claude/commands/landing-write.md`
- Modify: `.claude/commands/landing-publish.md`
- Modify: `wordpress/seo-machine-yoast-rest.php`
- Modify: workflow/publisher tests.

- [ ] Require context-binding generation or regeneration after the final content mutation and immediately before readiness.
- [ ] Route readiness/scoring by artifact kind so landing pages receive context/proof gates and their own scorer contract.
- [ ] Either implement and verify advertised page template/noindex behavior end to end or remove the unsupported command promises.
- [ ] Register and verify required Yoast REST fields for supported post types.
- [ ] Add a landing-page E2E fixture from write handoff through readiness and publisher payload.

### Task 6: Safe public evidence retrieval

**Files:**
- Add: `data_sources/modules/public_url_safety.py`
- Modify: `data_sources/modules/url_validator.py`
- Modify: `data_sources/modules/source_support_guard.py`
- Modify: `data_sources/modules/content_length_comparator.py`
- Add/modify focused tests.

- [ ] Add failing tests for localhost, loopback, RFC1918, link-local, reserved, non-HTTP schemes, and public-to-private redirects.
- [ ] Centralize hostname normalization, DNS resolution, public-IP checks, redirect limits, and request timeouts.
- [ ] Reject unsafe destinations before each request and each redirect while preserving normal public HTTPS evidence retrieval.
- [ ] Return stable blocker diagnostics rather than performing unsafe or unbounded requests.

### Task 7: DataForSEO and ranking correctness

**Files:**
- Modify: `data_sources/modules/dataforseo.py`
- Add: `data_sources/modules/domain_identity.py`
- Modify: `scripts/seo_bofu_rankings.py`
- Modify: `scripts/seo_competitor_analysis.py`
- Modify: `tests/test_dataforseo_correctness.py`
- Add focused script tests.

- [ ] Add lookalike-host failures and normalized exact-host successes for both consumers.
- [ ] Use shared hostname equality rather than substring matching.
- [ ] Make `months_back` affect the ranking-history request and validate its bounds.
- [ ] Replace bare exception handling with precise failure semantics that never swallow cancellation.
- [ ] Verify Windows redirected CLI output does not fail under CP1252.

### Task 8: Honest research orchestration and bounded browser fallback

**Files:**
- Modify: `scripts/research_priorities_comprehensive.py`
- Modify: `scripts/research_serp_analysis.py`
- Add behavioral tests under `tests/`.

- [ ] Add failing orchestration tests proving every enabled module must execute and produce read-back evidence before it is marked complete.
- [ ] Remove the fixed unsupported roadmap and generate actions only from returned module evidence.
- [ ] Exit nonzero with lane-specific diagnostics when required research fails.
- [ ] Add finite Playwright subprocess timeouts and best-effort cleanup tests.

### Task 9: AEO direct-answer and selector-evidence integrity

**Files:**
- Modify: `data_sources/modules/aeo_geo_rater.py`
- Modify: `tests/test_aeo_geo_rater.py`

- [ ] Add a failing test showing unresolved prose containing the keyword is not a direct answer.
- [ ] Require a real definition/action/number/yes-no predicate at the beginning of the answer, while retaining legitimate supported variants.
- [ ] Add a failing test showing handwritten selector command/slate prose cannot count as executed Experience evidence.
- [ ] Require machine-generated, receipt-bound selector evidence for the empty-slate outcome.

### Task 10: Optional dependency isolation and GSC packaging

**Files:**
- Modify: `data_sources/modules/data_aggregator.py`
- Modify: `mcp-gsc/pyproject.toml`
- Modify: `mcp-gsc/gsc_server.py`
- Add focused import and packaging tests.

- [ ] Add a failing test proving a missing optional GA dependency does not prevent GSC/DataForSEO initialization.
- [ ] Lazy-load providers within their own error boundary and report the exact unavailable dependency.
- [ ] Add a failing build/install test for `mcp-gsc`, then package the actual `gsc_server.py` module and modernize license metadata.
- [ ] Replace broad/bare exception handling at important GSC boundaries with explicit exceptions and stable diagnostics.
- [ ] Build a wheel without network/dependency installation and smoke-import it in an isolated target.

### Task 11: Mechanical quality cleanup

**Files:**
- Modify only reviewed Python files under `data_sources/modules`, `scripts`, `mcp-gsc`, and tests.

- [ ] Apply behavior-preserving Ruff fixes for unused imports and placeholder-free f-strings.
- [ ] Fix focused type errors where doing so improves runtime clarity; do not repackage the whole repo merely to satisfy import-mode noise.
- [ ] Run `compileall`, `ruff` fatal checks, `pip check`, and `git diff --check`.

### Task 12: Production verification and independent review

- [ ] Run the full pytest suite with warnings as errors using an isolated `--basetemp`.
- [ ] Run focused blog, landing, selector, context, publisher, DataForSEO, GSC, and workflow suites.
- [ ] Run all eight connector operations through `SimproVaultClient` against the real vault.
- [ ] Run the installed stdio MCP canary and negative boundary cases for unsupported scope, missing/duplicate plugin, tampered pack, stale revision, unsafe URL, and invalid publish type.
- [ ] Verify connector coverage remains `550/550`, approved Simpro claims remain nonzero, and source/cache plugin hashes match if the plugin contract changed.
- [ ] Request an independent code review against this plan and resolve every critical/important finding.
- [ ] Preserve the user-owned article and sidecar byte-for-byte relative to the starting diff.
