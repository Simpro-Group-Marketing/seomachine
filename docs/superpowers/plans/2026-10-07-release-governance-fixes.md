# Blog Release Governance Fixes (1, 4, 5, 6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut wasted hours from the governed blog workflow by making the vault context build resumable, letting Humanizer evidence resolve at release, removing two formatting-only blockers, and reporting every release blocker in one fast pass.

**Architecture:** Four independent changes on one branch. Fix 4 widens the release's resolvable-evidence set with two repository policy files. Fix 5 adds one shared FAQ match key and an opt-in selector-emitted decision block. Fix 6 keeps full finding messages in construction errors and adds a `blog_release_sweep` CLI that runs every check once and collects all findings. Fix 1 adds a `context_build` package (declarative spec, checkpoint store, resumable runner, CLI) that replaces hand-written per-topic context scripts.

**Tech Stack:** Python 3.14, pytest/unittest, argparse CLIs (`python -m data_sources.modules.<name>`), `simpro_vault` client.

**Spec:** Approved governance proposal from the 2026-10-07 session (fixes 1, 4, 5, 6). Plan copy is saved to `docs/superpowers/plans/2026-10-07-release-governance-fixes.md` in Task 0.

## Context

The "What Is Simpro?" blog run (2026-10-02 to 10-05) took about 3 hours of wall-clock work after drafting. Root causes seen in that run:
- **Fix 1:** the vault context build writes files only at the end. Three low-memory kills lost every pack each time (about 1.5 hours).
- **Fix 4:** `.claude/commands/write.md:45`, `rewrite.md:45` and `optimize.md:64` tell writers to pass `--evidence humanizer_policy=...` and `humanizer_upstream=...`. `_resolvable_receipt_evidence_hashes` (`data_sources/modules/blog_assembly/preflight.py:229-271`) never resolves those files, so the release fails with `stage_receipt_evidence_unresolved`.
- **Fix 5a:** `construction_support.py:255` and `blog_bom_validation/content_policy.py:183` compare `paa_policy.selected_questions` to FAQ headings case-sensitively. The PAA provenance guard already matches case-insensitively (`paa_provenance/matching.py:103`).
- **Fix 5b:** writers hand-type the `Customer Proof Selection Decision` "Selected proof" line. A mismatch with the slate fails `customer_proof_selected_not_in_slate` (`customer_proof/diversity_slate.py:83-95`).
- **Fix 6:** `--precheck-only` stops at the first `ValueError`, collapses findings to rule IDs (`blog_assembly/stage_receipts.py:65-67`), and runs none of the 32 readiness gates. Each blocker cost one 15-30 minute wrapper run.

## Global Constraints

- New production files under `data_sources/`, `scripts/`, `tools/` stay under 500 lines (`tools/check_python_structure.py`); new tests stay under 500 lines.
- No new function above McCabe complexity 10; no import cycles (`tools/python_import_architecture.py`).
- Module imports use the repo pattern: relative import inside `try`, plain import in `except ImportError` fallback.
- CLIs: `def main(argv: Sequence[str] | None = None) -> int`, argparse, runnable as `python -m data_sources.modules.<name>`; every documented command must pass `tests/test_guard_cli_module_invocation.py` (`--help` must load).
- Do not edit `AGENTS.md` or `CLAUDE.md` (`.claude/rules/agent-governance.md`). Mirror any `.claude/rules/*.md` change in `.cursor/rules/*.mdc` and `.agents/rules/*.md` where the same rule exists.
- Never weaken proof gates: matching changes may ignore case and punctuation only; `brief_paa` stays exact.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Work on branch `fix/release-governance-1-4-5-6` in a git worktree created from `main` (95c8d11).

## Review Focus

1. Resuming a context build after a vault revision change or after 24 hours must rebuild, never reuse a stale pack → test `test_resume_rebuilds_when_saved_pack_no_longer_validates` (Task 7).
2. Resuming with a changed spec or request must refuse, never mix old packs with a new request → test `test_resume_refuses_changed_request` (Task 7).
3. A Humanizer policy edited between draft and release must still fail resolution → test `test_edited_humanizer_policy_no_longer_resolves_old_digest` (Task 1).
4. FAQ headings differing only by curly apostrophes, spacing or case must pass; different wording and `brief_paa` case changes must still fail → tests in Task 2.
5. One guard crashing during the sweep must not hide the others → test `test_sweep_records_crash_and_continues` (Task 5).

---

### Task 0: Workspace setup

**Files:**
- Create: `docs/superpowers/plans/2026-10-07-release-governance-fixes.md`

- [ ] **Step 1:** Use superpowers:using-git-worktrees to create a worktree on new branch `fix/release-governance-1-4-5-6` from `main`.
- [ ] **Step 2:** Copy this plan file to `docs/superpowers/plans/2026-10-07-release-governance-fixes.md`.
- [ ] **Step 3:** Run the baseline: `python -m pytest tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_guard.py tests/test_paa_provenance_guard.py tests/test_customer_proof_selector.py tests/test_customer_proof_diversity_guard.py tests/test_blog_release_precheck.py tests/test_context_trace_store.py -q`. Record pass/fail counts so later failures are attributable.
- [ ] **Step 4:** Commit the plan copy.

```bash
git add docs/superpowers/plans/2026-10-07-release-governance-fixes.md
git commit -m "docs: add release governance fixes plan

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 1: Resolve Humanizer policy evidence at release (Fix 4)

**Files:**
- Modify: `data_sources/modules/blog_assembly_capabilities.py` (add registry + resolver after `AGENT_PATHS`, ~line 74)
- Modify: `data_sources/modules/blog_assembly/preflight.py:229-271` (`_resolvable_receipt_evidence_hashes`)
- Test: `tests/test_policy_definition_evidence.py` (new)

**Interfaces:**
- Produces: `blog_assembly_capabilities.POLICY_DEFINITION_PATHS: dict[str, str]`, `blog_assembly_capabilities.resolvable_policy_definition_hashes(*, workspace_root: str | Path) -> set[str]`.

- [ ] **Step 1: Write the failing tests**

```python
"""Humanizer policy files resolve as repository definitions at release."""
from __future__ import annotations

import hashlib
from pathlib import Path

from data_sources.modules import blog_assembly_capabilities as capabilities
from data_sources.modules.blog_assembly.preflight import _resolvable_receipt_evidence_hashes


def _write(root: Path, relative: str, text: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tail_receipts(evidence: dict[str, str]) -> list[dict]:
    return [
        {"stage": "post_optimization_scrub", "output_artifact_hashes": {}, "evidence_hashes": evidence},
        {"stage": "post_optimization_context_binding", "output_artifact_hashes": {}, "evidence_hashes": {}},
    ]


def test_policy_definition_hashes_cover_both_humanizer_files(tmp_path: Path) -> None:
    policy = _write(tmp_path, "config/humanizer-policy.json", "{}")
    upstream = _write(tmp_path, "vendor/blader-humanizer/UPSTREAM.json", '{"x": 1}')
    assert capabilities.resolvable_policy_definition_hashes(workspace_root=tmp_path) == {policy, upstream}


def test_policy_definition_hashes_skip_missing_files(tmp_path: Path) -> None:
    assert capabilities.resolvable_policy_definition_hashes(workspace_root=tmp_path) == set()


def test_humanizer_receipt_evidence_resolves_against_current_files(tmp_path: Path) -> None:
    digest = _write(tmp_path, "config/humanizer-policy.json", "{}")
    resolvable = _resolvable_receipt_evidence_hashes(
        _tail_receipts({"humanizer_policy": digest}), artifacts={}, workspace_root=tmp_path
    )
    assert digest in resolvable


def test_edited_humanizer_policy_no_longer_resolves_old_digest(tmp_path: Path) -> None:
    old = _write(tmp_path, "config/humanizer-policy.json", "{}")
    _write(tmp_path, "config/humanizer-policy.json", '{"changed": true}')
    resolvable = _resolvable_receipt_evidence_hashes(
        _tail_receipts({"humanizer_policy": old}), artifacts={}, workspace_root=tmp_path
    )
    assert old not in resolvable
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_policy_definition_evidence.py -v`
Expected: the first two tests fail with `AttributeError: ... has no attribute 'resolvable_policy_definition_hashes'`; the third fails its `in` assertion. If the tail-receipt fixture is rejected by `_required_mapping` for empty `output_artifact_hashes`, add `{"article": "0" * 64}` to each receipt's `output_artifact_hashes` and rerun.

- [ ] **Step 3: Implement**

In `blog_assembly_capabilities.py`, add `import hashlib` and after `AGENT_PATHS`:

```python
POLICY_DEFINITION_PATHS = {
    "humanizer_policy": "config/humanizer-policy.json",
    "humanizer_upstream": "vendor/blader-humanizer/UPSTREAM.json",
}


def resolvable_policy_definition_hashes(*, workspace_root: str | Path) -> set[str]:
    """Return current hashes of policy files that native edits cite as evidence.

    These files are resolvable only; they never enter the BOM execution evidence.
    A stale digest (file edited after the receipt) stays unresolved.
    """
    root = Path(workspace_root).resolve()
    hashes: set[str] = set()
    for stored_path in POLICY_DEFINITION_PATHS.values():
        path = root.joinpath(*PurePosixPath(stored_path).parts)
        if path.is_file():
            hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    return hashes
```

In `_resolvable_receipt_evidence_hashes`, directly after the `resolvable = {...}` set comprehension:

```python
    resolvable |= blog_assembly_capabilities.resolvable_policy_definition_hashes(
        workspace_root=workspace_root
    )
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_policy_definition_evidence.py tests/test_blog_assembly_bom.py tests/test_blog_assembly_stage_receipt.py tests/test_aeo_geo_workflow_docs.py -q`
Expected: all pass (the docs test keeps requiring the Humanizer flags, which now resolve).

- [ ] **Step 5: Commit**

```bash
git add data_sources/modules/blog_assembly_capabilities.py data_sources/modules/blog_assembly/preflight.py tests/test_policy_definition_evidence.py
git commit -m "fix: resolve Humanizer policy evidence on native-edit receipts

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Case-insensitive FAQ question binding (Fix 5a)

**Files:**
- Modify: `data_sources/modules/faq_structure.py` (add two functions)
- Modify: `data_sources/modules/paa_provenance/matching.py:103-109` (delegate `_normalize_for_match`)
- Modify: `data_sources/modules/blog_assembly/construction_support.py:255-256`
- Modify: `data_sources/modules/blog_bom_validation/content_policy.py:183-190`
- Test: `tests/test_faq_question_match.py` (new); add one test to `tests/test_blog_assembly_bom_guard.py`

**Interfaces:**
- Produces: `faq_structure.faq_question_match_key(text: str) -> str`, `faq_structure.faq_questions_match(selected: Sequence[str], visible: Sequence[str], *, source_kind: str) -> bool`.

- [ ] **Step 1: Write failing tests** (`tests/test_faq_question_match.py`)

```python
from data_sources.modules.faq_structure import faq_question_match_key, faq_questions_match


def test_key_ignores_case_spacing_and_apostrophe_style() -> None:
    assert faq_question_match_key("Is simpro a CRM system?") == faq_question_match_key("Is Simpro a CRM  system?")
    assert faq_question_match_key("What’s Simpro?") == faq_question_match_key("What's Simpro?")


def test_questions_match_in_order_only() -> None:
    assert faq_questions_match(
        ["Is simpro a CRM system?", "Is simpro a good system?"],
        ["Is Simpro a CRM system?", "Is Simpro a good system?"],
        source_kind="answersocrates",
    )
    assert not faq_questions_match(["A one?", "B two?"], ["B two?", "A one?"], source_kind="answersocrates")


def test_different_wording_still_fails() -> None:
    assert not faq_questions_match(["Is Simpro a CRM?"], ["Is Simpro a CRM system?"], source_kind="answersocrates")


def test_brief_paa_stays_exact_except_outer_whitespace() -> None:
    assert not faq_questions_match(["is simpro a crm system?"], ["Is Simpro a CRM system?"], source_kind="brief_paa")
    assert faq_questions_match([" Is Simpro a CRM system? "], ["Is Simpro a CRM system?"], source_kind="brief_paa")
```

Append to `tests/test_blog_assembly_bom_guard.py`:

```python
def test_paa_selected_questions_match_visible_headings_case_insensitively(tmp_path: Path):
    paths = _fixture(tmp_path, visible_faq=True)
    bom = _build(tmp_path, paths)
    bom["paa_policy"]["selected_questions"] = [
        question.lower() for question in bom["paa_policy"]["selected_questions"]
    ]

    rules = _rules(tmp_path, bom, paths)

    assert "bom_paa_questions_mismatch" not in rules
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_faq_question_match.py tests/test_blog_assembly_bom_guard.py -k "faq_question or case_insensitively or questions_match or brief_paa_stays" -v`
Expected: ImportError for the new functions; the BOM guard test reports `bom_paa_questions_mismatch`.

- [ ] **Step 3: Implement**

`faq_structure.py` (add `import unicodedata` and `from typing import Sequence`):

```python
def faq_question_match_key(text: str) -> str:
    """Return the shared FAQ match key: NFKC, casefold, punctuation as spaces."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(
        "".join(character if character.isalnum() else " " for character in normalized).split()
    )


def faq_questions_match(
    selected: Sequence[str], visible: Sequence[str], *, source_kind: str
) -> bool:
    """Compare planned and visible FAQ questions in order.

    brief_paa questions are pre-picked verbatim, so they compare exactly
    apart from outer whitespace.
    """
    if source_kind == "brief_paa":
        return [q.strip() for q in selected] == [q.strip() for q in visible]
    return [faq_question_match_key(q) for q in selected] == [
        faq_question_match_key(q) for q in visible
    ]
```

`paa_provenance/matching.py`: import `faq_question_match_key` with the module's existing relative/fallback import pattern and replace the body of `_normalize_for_match` with `return faq_question_match_key(text)` (keep the name; other modules import it).

`construction_support.py:255`:

```python
    if not faq_questions_match(
        policy["selected_questions"],
        _visible_faq_questions(article.raw),
        source_kind=str(policy["source_kind"]),
    ):
        raise ValueError(
            "paa_policy.selected_questions must match visible FAQ headings in order "
            "(case and punctuation are ignored except for brief_paa)"
        )
```

`content_policy.py:183` (the `source_kind` local is already defined above):

```python
        if not faq_questions_match(selected, visible, source_kind=str(source_kind)):
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_faq_question_match.py tests/test_blog_assembly_bom_guard.py tests/test_blog_assembly_bom.py tests/test_paa_provenance_guard.py -q`
Expected: all pass, including the existing `bom_paa_questions_mismatch` shape test (empty list still mismatches).

- [ ] **Step 5: Commit**

```bash
git add data_sources/modules/faq_structure.py data_sources/modules/paa_provenance/matching.py data_sources/modules/blog_assembly/construction_support.py data_sources/modules/blog_bom_validation/content_policy.py tests/test_faq_question_match.py tests/test_blog_assembly_bom_guard.py
git commit -m "fix: match planned FAQ questions to headings case-insensitively

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Selector-emitted selection decision block (Fix 5b)

**Files:**
- Create: `data_sources/modules/customer_proof/decision_block.py`
- Modify: `data_sources/modules/customer_proof/selector_cli.py` (new `--decision-block` flag; emit inside the `with snapshot_context` block)
- Modify docs: `.claude/rules/customer-proof.md`, mirrors `.cursor/rules/customer-proof.mdc`, `.agents/rules/customer-proof.md`; `.claude/commands/write.md` and `rewrite.md` selector command lines
- Test: `tests/test_customer_proof_decision_block.py` (new)

**Interfaces:**
- Produces: `decision_block.selected_proof_rows(role_evidence, lookup) -> list[dict[str, str]]`, `decision_block.selection_decision_block(rows, *, selector_command: str) -> str`.
- Consumes: `role_evidence` rows from `build_customer_proof_slate(..., _role_evidence=...)` (`role`, `selected_id`), candidates from `select_customer_proofs` (`proof_id`, `customer`, `public_url`, `claim_id`).

- [ ] **Step 1: Write failing tests**

```python
"""The selector can prefill a Customer Proof Selection Decision that matches its slate."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

from data_sources.modules.customer_proof.diversity_parsing import (
    _extract_customer_proof_slate,
    _extract_selection_decision,
    _parse_slate_roles,
    _selected_proof_ids,
    _slate_selected_ids,
)
from data_sources.modules.customer_proof.selector_cli import _main
from tests.test_customer_proof_selector import proof_claims, write_ledger
from tests.vault_context_fixture import write_connector_context_fixture


def _run(tmp_path: Path, *extra: str) -> tuple[int, str]:
    ledger = write_ledger(tmp_path)
    pack, receipt = write_connector_context_fixture(tmp_path, proof_claims())
    out = StringIO()
    with redirect_stdout(out):
        code = _main([
            "quoting invoicing review story", "--ledger", str(ledger),
            "--context-pack", str(pack), "--context-receipt", str(receipt),
            "--slate", "--roles", "metric,quote,theme,experience_story",
            "--require-eeat-story", "--evidence-output", str(tmp_path / "evidence.json"),
            *extra,
        ])
    return code, out.getvalue()


def test_decision_block_selected_proof_is_in_slate(tmp_path: Path) -> None:
    code, text = _run(tmp_path, "--decision-block")
    assert code == 0
    selected = _selected_proof_ids(_extract_selection_decision(text))
    slate_ids = _slate_selected_ids(_parse_slate_roles(_extract_customer_proof_slate(text)))
    assert selected and set(selected) <= slate_ids
    assert "- Selected proof: claim-bwe-quote | Customer: " in text
    assert "- Selector command: python data_sources/modules/customer_proof_selector.py" in text


def test_decision_block_is_opt_in(tmp_path: Path) -> None:
    code, text = _run(tmp_path)
    assert code == 0
    assert "## Customer Proof Selection Decision" not in text


def test_decision_block_requires_slate(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        _main(["topic", "--decision-block"])
```

If `write_ledger`/`proof_claims` are methods rather than module functions in `tests/test_customer_proof_selector.py`, move them to module level there first (no behavior change) and keep the existing tests passing.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_customer_proof_decision_block.py -v`
Expected: `--decision-block` unrecognized (exit 2 / SystemExit) in the first test.

- [ ] **Step 3: Implement** `decision_block.py`

```python
"""Prefilled Customer Proof Selection Decision block for the selector CLI.

Only fields the selector knows are emitted. Writers still add Reuse reason,
zero-use comparison, and Final use in copy directly under these bullets
(no blank line), because the guard reads one contiguous bullet list.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from .contracts import CustomerProofDataError

HEADING = "## Customer Proof Selection Decision"


def selected_proof_rows(
    role_evidence: Sequence[Mapping[str, Any]],
    lookup: Callable[[str], Sequence[Mapping[str, Any]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for role_row in role_evidence:
        selected_id = str(role_row.get("selected_id") or "").strip()
        if not selected_id or selected_id.casefold() == "none":
            continue
        role = str(role_row.get("role") or "")
        match = next(
            (c for c in lookup(role) if str(c.get("proof_id")) == selected_id), None
        )
        if match is None:
            raise CustomerProofDataError(
                f"Selected {role} proof {selected_id} is missing from verified candidates"
            )
        rows.append({
            "role": role,
            "proof_id": selected_id,
            "customer": str(match.get("customer") or "unknown"),
            "public_url": str(match.get("public_url") or ""),
            "claim_id": str(match.get("claim_id") or selected_id),
        })
    return rows


def selection_decision_block(
    rows: Sequence[Mapping[str, str]], *, selector_command: str
) -> str:
    lines = [HEADING, "", f"- Selector command: {selector_command}"]
    for row in rows:
        lines.append(
            f"- Selected proof: {row['proof_id']} | Customer: {row['customer']} "
            f"| URL: {row['public_url']} | Role: {row['role']} | Claim ID: {row['claim_id']}"
        )
    return "\n".join(lines)
```

In `selector_cli.py`: add

```python
    parser.add_argument(
        "--decision-block",
        action="store_true",
        help="Also print a prefilled Customer Proof Selection Decision block (requires --slate).",
    )
```

after the `--allow-no-proof` argument; after `args = parser.parse_args(argv)` add `if args.decision_block and not args.slate: parser.error("--decision-block requires --slate")`. Inside the `with snapshot_context as input_snapshot:` block, after the evidence-output branch:

```python
                if args.decision_block:
                    claim_lookup = (
                        input_snapshot.claim_lookup if input_snapshot is not None else claim_lookup_payload
                    )

                    def _role_candidates(role: str) -> list[FindingDict]:
                        return select_customer_proofs(
                            args.topic, ledger_path=args.ledger,
                            context_pack=args.context_pack, context_receipt=args.context_receipt,
                            article_slug=args.article_slug, title=args.title, objective=args.objective,
                            require_eeat_story=args.require_eeat_story and role == "experience_story",
                            proof_role=role, limit=args.limit, reference_date=reference_date,
                            claim_lookup_evidence=claim_lookup, _input_snapshot=input_snapshot,
                        )

                    command_line = next(
                        line for line in slate.splitlines() if line.startswith("- Selector command: ")
                    )
                    slate = slate + "\n\n" + selection_decision_block(
                        selected_proof_rows(role_evidence, _role_candidates),
                        selector_command=command_line.removeprefix("- Selector command: "),
                    )
```

with `from .decision_block import selected_proof_rows, selection_decision_block`. Keep `_main` complexity ≤ 10 by moving the new block into a helper `_append_decision_block(args, slate, role_evidence, input_snapshot, claim_lookup_payload, reference_date) -> str` if the structure check flags it.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_customer_proof_decision_block.py tests/test_customer_proof_selector.py tests/test_customer_proof_diversity_guard.py tests/test_guard_cli_module_invocation.py -q`
Expected: all pass.

- [ ] **Step 5: Update docs**

In `.claude/rules/customer-proof.md` (and both mirrors), after the selector command block, add:

```markdown
Add `--decision-block` to print a prefilled `Customer Proof Selection Decision` whose `Selected proof` lines match the slate. Paste it after the slate and append `Reuse reason`, the zero-use comparison, and `Final use in copy` directly under its bullets with no blank line.
```

Append `--decision-block` to the selector command lines in `.claude/commands/write.md` and `rewrite.md`. Rerun `python -m pytest tests/test_aeo_geo_workflow_docs.py tests/test_editorial_strategy_wiring.py -q`.

- [ ] **Step 6: Commit**

```bash
git add data_sources/modules/customer_proof/decision_block.py data_sources/modules/customer_proof/selector_cli.py tests/test_customer_proof_decision_block.py .claude/rules/customer-proof.md .cursor/rules/customer-proof.mdc .agents/rules/customer-proof.md .claude/commands/write.md .claude/commands/rewrite.md
git commit -m "feat: let the selector prefill the customer proof selection decision

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Keep finding messages in construction errors (Fix 6, part 1)

**Files:**
- Modify: `data_sources/modules/blog_assembly/contracts.py` (add helper)
- Modify: `data_sources/modules/blog_assembly/stage_receipts.py:65-67`, `blog_assembly/construction_support.py:118-120` and `:272-274`
- Test: `tests/test_construction_finding_messages.py` (new)

**Interfaces:**
- Produces: `blog_assembly.contracts.findings_error_text(prefix: str, findings: Sequence[Mapping[str, Any]], *, limit: int = 5) -> str`.

- [ ] **Step 1: Write failing test**

```python
from data_sources.modules.blog_assembly.contracts import findings_error_text


def test_findings_error_text_keeps_rule_ids_and_messages() -> None:
    findings = [
        {"rule_id": "stage_receipt_evidence_unresolved", "message": "Receipt evidence humanizer_policy does not resolve to a current artifact or repository definition."},
        {"rule_id": "stage_receipt_previous_hash_mismatch", "message": "Receipt predecessor hash chain is broken."},
    ]
    text = findings_error_text("stage receipt chain is invalid", findings)
    assert text.startswith("stage receipt chain is invalid: stage_receipt_evidence_unresolved, stage_receipt_previous_hash_mismatch")
    assert "humanizer_policy does not resolve" in text
    assert "predecessor hash chain is broken" in text


def test_findings_error_text_limits_messages() -> None:
    findings = [{"rule_id": f"r{i}", "message": f"m{i}"} for i in range(9)]
    text = findings_error_text("x", findings, limit=3)
    assert "m2" in text and "m3" not in text and "6 more" in text
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_construction_finding_messages.py -v` → ImportError.

- [ ] **Step 3: Implement**

```python
def findings_error_text(
    prefix: str, findings: Sequence[Mapping[str, Any]], *, limit: int = 5
) -> str:
    """Return '<prefix>: <sorted rule ids> | <first messages>' for ValueError text."""
    rules = ", ".join(sorted({str(row.get("rule_id")) for row in findings}))
    messages = [str(row.get("message") or row.get("rule_id")) for row in findings[:limit]]
    extra = len(findings) - limit
    if extra > 0:
        messages.append(f"{extra} more")
    return f"{prefix}: {rules} | " + " ; ".join(messages)
```

Replace the three collapsed raises with `raise ValueError(findings_error_text("<same prefix text>", findings))`. The rule-ID list stays first, so existing tests asserting `"stage receipt chain is invalid: stage_receipt_..."` substrings still pass.

- [ ] **Step 4: Run tests** — `python -m pytest tests/test_construction_finding_messages.py tests/test_blog_assembly_bom.py tests/test_blog_release_precheck.py tests/test_release_chain_decision.py -q` → all pass.

- [ ] **Step 5: Commit** (`fix: keep finding messages in blog assembly construction errors`).

---

### Task 5: One-pass release sweep CLI (Fix 6, part 2)

**Files:**
- Create: `data_sources/modules/release_workflow/precheck_sweep.py` (checks + runner, < 400 lines)
- Create: `data_sources/modules/blog_release_sweep.py` (CLI wrapper)
- Modify docs: `.claude/commands/publish-readiness.md` (new "Fast sweep" section), one line each in `.claude/commands/write.md`, `rewrite.md`, `optimize.md`
- Test: `tests/test_release_sweep.py` (new)

**Interfaces:**
- Produces: `precheck_sweep.SWEEP_SCHEMA = "simpro-blog-release-sweep/v1"`, `precheck_sweep.run_check(name: str, check: Callable[[], Iterable[Mapping[str, Any]]]) -> list[dict[str, Any]]`, `precheck_sweep.sweep_article_gates(gates, *, article: str, kwargs: Mapping[str, Any], skip: Mapping[str, str]) -> list[dict[str, Any]]`, `precheck_sweep.scorer_findings(result: Mapping[str, Any]) -> list[dict[str, Any]]`, `precheck_sweep.run_release_sweep(args: argparse.Namespace, *, workspace_root: Path, offline: bool, include_slow: bool) -> dict[str, Any]`.
- Consumes: `readiness.release_cli._parser()` (same arguments as the release wrapper), `readiness.common.ARTICLE_GATES`, `faq_structure.faq_questions_match` (Task 2), `blog_creation_preflight.build_preflight_report`, `editorial_plan.orchestration.check_file`, `semrush_keyword_decision_guard.check_file`, `content_scoring.scorer.ContentScorer`.

Design rules:
- Every check runs inside `run_check`; an exception becomes one `sweep_check_crashed` error finding and the sweep continues.
- Each finding row: `{"check", "rule_id", "severity", "line", "message"}`.
- Article gates come from `ARTICLE_GATES` so new gates join automatically. Call `module.check_file(article, **kw)` passing only keyword arguments the function accepts (`inspect.signature`), from: `proof_sidecar`, `fail_on="error"`, `context_request`, `context_pack`, `context_receipt`, `require_strategy=True`.
- Skipped gates are listed with a reason, never silently dropped: `editorial_plan` and `semrush_keyword_decision` (run as dedicated checks), `customer_proof_diversity` unless `--include-slow` (8-28 minutes per release today), and `url_validator`, `source_support`, `public_research_links` when `--offline`.
- Dedicated checks: pre-BOM report blockers (no early return), editorial plan, keyword decision, FAQ question binding (Task 2 key), PAA provenance, content scorer (AEO/GEO checks with `passed: False` become findings).
- The report: `{"schema", "passed", "findings", "skipped", "checks_run", "elapsed_seconds"}`; exit 1 when any error finding exists.

- [ ] **Step 1: Write failing tests**

```python
"""The release sweep reports every blocker in one pass."""
from __future__ import annotations

from types import SimpleNamespace

from data_sources.modules.release_workflow import precheck_sweep


def test_sweep_records_crash_and_continues() -> None:
    def boom():
        raise RuntimeError("guard exploded")

    rows = precheck_sweep.run_check("broken", boom) + precheck_sweep.run_check(
        "ok", lambda: [{"rule_id": "r1", "severity": "error", "message": "m"}]
    )
    assert [(r["check"], r["rule_id"]) for r in rows] == [
        ("broken", "sweep_check_crashed"), ("ok", "r1"),
    ]
    assert "guard exploded" in rows[0]["message"]


def test_article_gates_receive_only_supported_kwargs() -> None:
    seen = {}

    def check_file(path, proof_sidecar=None, fail_on="error"):
        seen.update(path=path, proof_sidecar=proof_sidecar, fail_on=fail_on)
        return [{"rule_id": "x", "severity": "error", "message": "bad", "line": 3}]

    gates = (("demo_gate", "Demo", SimpleNamespace(check_file=check_file)),)
    rows = precheck_sweep.sweep_article_gates(
        gates, article="a.md",
        kwargs={"proof_sidecar": "s.md", "fail_on": "error", "context_pack": "p.json"},
        skip={},
    )
    assert seen == {"path": "a.md", "proof_sidecar": "s.md", "fail_on": "error"}
    assert rows[0]["check"] == "demo_gate" and rows[0]["line"] == 3


def test_skipped_gates_are_reported_not_run() -> None:
    called = []
    gates = (("url_validator", "URL", SimpleNamespace(check_file=lambda path: called.append(path) or [])),)
    rows = precheck_sweep.sweep_article_gates(
        gates, article="a.md", kwargs={}, skip={"url_validator": "offline"}
    )
    assert called == [] and rows == []


def test_scorer_findings_turn_failed_checks_into_errors() -> None:
    result = {"aeo_geo": {"checks": {
        "capsule_coverage": {"passed": False, "issue": "First paragraph must contain 50-60 words."},
        "schema": {"passed": True},
    }}}
    rows = precheck_sweep.scorer_findings(result)
    assert [r["rule_id"] for r in rows] == ["aeo_geo.capsule_coverage"]
    assert rows[0]["severity"] == "error"
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_release_sweep.py -v` → ImportError.

- [ ] **Step 3: Implement the core helpers** in `precheck_sweep.py`:

```python
"""One-pass release sweep: run every release check and collect all findings."""
from __future__ import annotations

import argparse
import inspect
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

SWEEP_SCHEMA = "simpro-blog-release-sweep/v1"
GATE_KWARG_NAMES = (
    "proof_sidecar", "fail_on", "context_request", "context_pack",
    "context_receipt", "require_strategy",
)
DEDICATED_GATES = {"editorial_plan": "dedicated check", "semrush_keyword_decision": "dedicated check"}
SLOW_GATES = {"customer_proof_diversity": "slow; pass --include-slow"}
NETWORK_GATES = {"url_validator": "offline", "source_support": "offline", "public_research_links": "offline"}


def _row(check: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "check": check,
        "rule_id": str(raw.get("rule_id") or raw.get("code") or "finding"),
        "severity": str(raw.get("severity") or "error"),
        "line": raw.get("line"),
        "message": str(raw.get("message") or raw.get("issue") or ""),
    }


def run_check(name: str, check: Callable[[], Iterable[Mapping[str, Any]] | None]) -> list[dict[str, Any]]:
    try:
        return [_row(name, raw) for raw in (check() or [])]
    except Exception as error:  # noqa: BLE001 - the sweep must survive any guard failure.
        return [{
            "check": name, "rule_id": "sweep_check_crashed", "severity": "error",
            "line": None, "message": f"{type(error).__name__}: {error}",
        }]


def _supported_kwargs(function: Callable[..., Any], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    parameters = inspect.signature(function).parameters
    return {name: value for name, value in kwargs.items() if name in parameters}


def sweep_article_gates(
    gates: Sequence[tuple[str, str, Any]], *, article: str,
    kwargs: Mapping[str, Any], skip: Mapping[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, _label, module in gates:
        if name in skip:
            continue
        check_file = module.check_file
        rows += run_check(name, lambda f=check_file: f(article, **_supported_kwargs(f, kwargs)))
    return rows


def scorer_findings(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks = (result.get("aeo_geo") or {}).get("checks") or {}
    return [
        {"rule_id": f"aeo_geo.{name}", "severity": "error", "line": None,
         "message": str(check.get("issue") or check.get("fix") or "check failed")}
        for name, check in checks.items()
        if isinstance(check, Mapping) and check.get("passed") is False
    ]
```

- [ ] **Step 4: Run the four tests** → pass.

- [ ] **Step 5: Implement `run_release_sweep` and the dedicated checks.** Add these, each a small function returning finding rows:
  - `_pre_bom_rows(args, root)`: call `blog_creation_preflight.build_preflight_report` with the same keyword arguments `release_workflow/precheck.py` passes (copy that call block), return `report["blockers"]`.
  - `_plan_rows(args, root)`: `editorial_plan.orchestration.check_file(args.editorial_plan, article_path=args.article, serp_evidence_path=args.serp_evidence, assembly_date=args.assembly_date, expected_run_id=args.run_id, workspace_root=root)`.
  - `_keyword_rows(args)`: `semrush_keyword_decision_guard.check_file(args.keyword_decision, article_path=args.article, editorial_plan_path=args.editorial_plan, assembly_date=args.assembly_date)`.
  - `_faq_binding_rows(args, root)`: derive the policy with `blog_assembly.policy._derive_paa_policy` (same arguments as `construction_support.py:245`) and compare with `faq_questions_match`; then `check_paa_provenance_file(...)` (same arguments as `construction_support.py:262-272`).
  - `_scorer_rows(args)`: `ContentScorer().score(Path(args.article).read_text(encoding="utf-8"), source_path=str(args.article), proof_sidecar=str(args.proof_sidecar), paa_workflow_mode=args.workflow_mode, paa_artifact=args.paa_artifact, paa_content_brief=args.content_brief, paa_expected_run_id=args.run_id, paa_expected_collection_date=args.assembly_date, assembly_date=args.assembly_date)` → `scorer_findings(result)`.
  - `run_release_sweep` runs every dedicated check through `run_check`, then `sweep_article_gates(ARTICLE_GATES, ...)` with `skip = {**DEDICATED_GATES, **({} if include_slow else SLOW_GATES), **(NETWORK_GATES if offline else {})}`, and returns the report dict with `"passed": not any(r["severity"] == "error" for r in findings)`, `"skipped"` as `[{"check": k, "reason": v}]`, and `"elapsed_seconds"` from `time.monotonic()`.

Add this test to `tests/test_release_sweep.py`:

```python
def test_report_collects_every_check_in_one_pass(monkeypatch, tmp_path) -> None:
    names = ["_pre_bom_rows", "_plan_rows", "_keyword_rows", "_faq_binding_rows", "_scorer_rows"]
    for name in names:
        monkeypatch.setattr(
            precheck_sweep, name,
            lambda *a, _n=name, **k: [{"rule_id": _n, "severity": "error", "message": _n}],
        )
    gate = SimpleNamespace(check_file=lambda path: [{"rule_id": "gate_rule", "severity": "error", "message": "g"}])
    monkeypatch.setattr(precheck_sweep, "ARTICLE_GATES", (("demo_gate", "Demo", gate),))
    args = SimpleNamespace(article="a.md", proof_sidecar="s.md", context_request=None,
                           context_pack=None, context_receipt=None)
    report = precheck_sweep.run_release_sweep(args, workspace_root=tmp_path, offline=True, include_slow=False)
    rules = {row["rule_id"] for row in report["findings"]}
    assert rules == set(names) | {"gate_rule"}
    assert report["passed"] is False and report["schema"] == precheck_sweep.SWEEP_SCHEMA
```

`run_release_sweep` must look up `ARTICLE_GATES` as a module attribute (import it at module level from `..readiness.common`) so the test can patch it.

- [ ] **Step 6: CLI** `data_sources/modules/blog_release_sweep.py`:

```python
"""Run every release check once and report all blockers together."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

try:
    from .blog_assembly_contract import atomic_write_json
    from .readiness.release_cli import _parser
    from .release_workflow.precheck_sweep import run_release_sweep
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import atomic_write_json
    from readiness.release_cli import _parser
    from release_workflow.precheck_sweep import run_release_sweep


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    parser.description = "Run every release check once and report all blockers together."
    for action in parser._actions:  # the sweep writes no release directory
        if action.dest == "output_dir":
            action.required = False
    parser.add_argument("--sweep-output", required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--include-slow", action="store_true")
    args = parser.parse_args(argv)
    report = run_release_sweep(
        args, workspace_root=Path.cwd(), offline=args.offline, include_slow=args.include_slow
    )
    atomic_write_json(Path(args.sweep_output), report)
    for row in report["findings"]:
        print(f"{row['severity']}\t{row['check']}\t{row['rule_id']}\t{row['message'][:160]}")
    print(json.dumps({"passed": report["passed"], "findings": len(report["findings"]),
                      "skipped": len(report["skipped"]), "elapsed_seconds": report["elapsed_seconds"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

Add the CLI test (in `tests/test_release_sweep.py`):

```python
from data_sources.modules import blog_release_sweep


@pytest.mark.parametrize("passed, code", [(True, 0), (False, 1)])
def test_cli_exit_code_and_optional_output_dir(monkeypatch, tmp_path, passed, code) -> None:
    captured = {}

    def fake_sweep(args, **kwargs):
        captured["args"] = args
        return {"schema": "simpro-blog-release-sweep/v1", "passed": passed, "findings": [],
                "skipped": [], "checks_run": [], "elapsed_seconds": 0.1}

    monkeypatch.setattr(blog_release_sweep, "run_release_sweep", fake_sweep)
    argv = [
        "drafts/a.md", "--run-id", "r", "--proof-sidecar", "s.md", "--editorial-plan", "p.json",
        "--plan-review", "pr.json", "--article-review", "ar.json", "--keyword-decision", "k.json",
        "--scrub-receipt", "sc.json", "--serp-evidence", "se.json", "--plan-fulfillment", "pf.json",
        "--commercial-pillar-index", "context/commercial-pillar-index.json",
        "--workflow-mode", "new", "--assembly-date", "2026-10-07",
        "--sweep-output", str(tmp_path / "sweep.json"),
    ]
    assert blog_release_sweep.main(argv) == code
    assert (tmp_path / "sweep.json").is_file()
```

(Add `import pytest` at the top of the test file. If `_parser()` requires further arguments, append them to `argv` exactly as `tests/test_blog_release.py::_inputs` builds them.)

- [ ] **Step 7: Docs.** In `.claude/commands/publish-readiness.md`, before the wrapper usage, add:

```markdown
## Fast sweep (run first)

Before the release wrapper, run the sweep with the same arguments to see every blocker in one pass:

python -m data_sources.modules.blog_release_sweep [article] [same wrapper arguments] --sweep-output research/prechecks/[slug]-[date]-sweep.json [--offline] [--include-slow]

The sweep never writes a release directory and never grants readiness. Fix every reported blocker, rerun the sweep until it passes, then run the wrapper. `customer_proof_diversity` runs only with `--include-slow`; network gates are skipped with `--offline`.
```

Add one line to `write.md`, `rewrite.md` and `optimize.md` where they first call the wrapper: "Run the fast sweep from `/publish-readiness` first."

- [ ] **Step 8: Run tests** — `python -m pytest tests/test_release_sweep.py tests/test_guard_cli_module_invocation.py tests/test_aeo_geo_workflow_docs.py tests/test_blog_release_precheck.py -q && python tools/check_python_structure.py` → pass.

- [ ] **Step 9: Commit** (`feat: add one-pass release sweep that reports every blocker`).

---

### Task 6: Context build spec and checkpoint store (Fix 1, part 1)

**Files:**
- Create: `data_sources/modules/context_build/__init__.py`, `spec.py`, `checkpoints.py`
- Create: `config/context-build-spec.example.json` (tracked example built from `scripts/build_what_is_simpro_context.py` constants)
- Test: `tests/test_context_build_spec.py` (new)

**Interfaces:**
- Produces:
  - `spec.SPEC_SCHEMA = "simpro-context-build-spec/v1"`, `spec.ContextBuildSpecError(ValueError)`.
  - `spec.StageSpec(stage_id: str, pack_path: str, receipt_path: str, claim_requests: tuple[dict[str, str], ...])`.
  - `spec.ContextBuildSpec(slug, date, request: dict, request_path, trace_path, search_queries: tuple[str, ...], resource_purposes: dict[str, str], expand_resource_ids: tuple[str, ...], constraints: tuple[str, ...], claim_lookups: tuple[dict[str, Any], ...], claim_lookup_path: str | None, stages: tuple[StageSpec, ...], digest: str)`.
  - `spec.load_spec(path: str | Path) -> ContextBuildSpec`.
  - `checkpoints.CheckpointStore(workspace_root: Path, spec: ContextBuildSpec, *, resume: bool)` with `.get(key: str) -> Any | None`, `.put(key: str, value: Any) -> None`; `checkpoints.ContextBuildResumeError(ValueError)`.

Spec JSON shape (also the example file):

```json
{
  "schema": "simpro-context-build-spec/v1",
  "slug": "what-is-simpro",
  "date": "2026-10-05",
  "request": {"schema": "simpro-context-request/v1", "task": "...", "scope": {"brand": "Simpro", "title": "...", "objective": "...", "audience": "...", "region": "US", "artifact_type": "blog", "intended_public_use_modes": ["exact_quote"]}, "requested_at": "2026-10-05"},
  "outputs": {"request": "research/context-request-what-is-simpro.json", "trace": "research/context-refresh-what-is-simpro-2026-10-05.json", "claim_lookup": "research/customer-proof-claim-lookup-what-is-simpro-2026-10-05.json"},
  "discovery": {"search_queries": ["COD Editorial Blog Voice"], "resource_purposes": {"res-...": "guidance"}, "expand_resource_ids": ["res-..."]},
  "constraints": ["Simpro only: no competitor names ..."],
  "claim_lookups": [{"query": "Simpro one system quoting", "use_mode": "exact_quote", "limit": 50}],
  "stages": [
    {"id": "customer_selector", "pack": "research/context-pack-what-is-simpro-customer-selector-2026-10-05.json", "receipt": "research/context-receipt-what-is-simpro-customer-selector-2026-10-05.json", "claim_requests": [{"claim_id": "claim-metric-MET-1809", "query": "...", "use_mode": "exact_quote", "brand_scope": "Simpro"}]},
    {"id": "fred_evaluation", "pack": "...", "receipt": "...", "claim_requests": []},
    {"id": "public", "pack": "research/context-pack-what-is-simpro.json", "receipt": "research/context-receipt-what-is-simpro.json", "claim_requests": []}
  ]
}
```

Validation rules (each raises `ContextBuildSpecError` with the field path): schema matches; 1-20 unique `search_queries`, each ≤ 500 characters (connector limit); every `claim_requests` row has exactly `{claim_id, query, use_mode, brand_scope}`; stage ids unique; every output path is relative, uses `/`, and starts with `research/`; every `expand_resource_ids` entry is a key of `resource_purposes`. `digest` = `canonical_json_sha256(raw_spec)` from `blog_assembly_contract`.

Checkpoint rules: store under `.seomachine/context-build/<slug>/<date>/` (gitignored, outside `research/` so the retention planner never parses it). `manifest.json` records `spec_digest`. `resume=False` deletes that directory first. `resume=True` with a different stored digest raises `ContextBuildResumeError("spec changed since the saved checkpoints; rerun without --resume")`. Each value is written atomically with `bounded_io.writers.atomic_write_canonical_json` to `<sha256(key)>.json`.

- [ ] **Step 1: Write failing tests** (`tests/test_context_build_spec.py`):

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules.context_build.checkpoints import CheckpointStore, ContextBuildResumeError
from data_sources.modules.context_build.spec import ContextBuildSpecError, load_spec


def _spec_payload(**overrides):
    payload = {
        "schema": "simpro-context-build-spec/v1",
        "slug": "demo",
        "date": "2026-10-07",
        "request": {"schema": "simpro-context-request/v1", "task": "t", "scope": {"title": "Demo"}},
        "outputs": {"request": "research/context-request-demo.json",
                    "trace": "research/context-refresh-demo-2026-10-07.json",
                    "claim_lookup": None},
        "discovery": {"search_queries": ["q1"], "resource_purposes": {"res-a": "guidance"},
                      "expand_resource_ids": ["res-a"]},
        "constraints": ["c1"],
        "claim_lookups": [],
        "stages": [{"id": "public", "pack": "research/context-pack-demo.json",
                    "receipt": "research/context-receipt-demo.json",
                    "claim_requests": [{"claim_id": "claim-1", "query": "q", "use_mode": "exact_quote",
                                        "brand_scope": "Simpro"}]}],
    }
    payload.update(overrides)
    return payload


def _write(tmp_path: Path, payload) -> Path:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_valid_spec_loads(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, _spec_payload()))
    assert spec.slug == "demo" and spec.stages[0].stage_id == "public" and len(spec.digest) == 64


def test_example_spec_loads() -> None:
    assert load_spec(Path("config/context-build-spec.example.json")).stages


@pytest.mark.parametrize("mutate", [
    lambda p: p["discovery"].update(search_queries=[f"q{i}" for i in range(21)]),
    lambda p: p["stages"][0]["claim_requests"][0].update(extra="x"),
    lambda p: p["stages"].append(dict(p["stages"][0])),
    lambda p: p["stages"][0].update(pack="drafts/context-pack-demo.json"),
    lambda p: p["discovery"].update(expand_resource_ids=["res-missing"]),
])
def test_invalid_specs_are_rejected(tmp_path: Path, mutate) -> None:
    payload = _spec_payload()
    mutate(payload)
    with pytest.raises(ContextBuildSpecError):
        load_spec(_write(tmp_path, payload))


def test_checkpoint_round_trip_and_fresh_run_clears(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, _spec_payload()))
    store = CheckpointStore(tmp_path, spec, resume=False)
    store.put("search:q1", [{"resource_id": "res-a"}])
    assert CheckpointStore(tmp_path, spec, resume=True).get("search:q1") == [{"resource_id": "res-a"}]
    assert CheckpointStore(tmp_path, spec, resume=False).get("search:q1") is None


def test_resume_with_changed_spec_is_refused(tmp_path: Path) -> None:
    CheckpointStore(tmp_path, load_spec(_write(tmp_path, _spec_payload())), resume=False)
    changed = load_spec(_write(tmp_path, _spec_payload(constraints=["different"])))
    with pytest.raises(ContextBuildResumeError):
        CheckpointStore(tmp_path, changed, resume=True)
```
- [ ] **Step 2: Run** `python -m pytest tests/test_context_build_spec.py -v` → ImportError.
- [ ] **Step 3: Implement** `spec.py` (frozen dataclasses + `load_spec` that parses with `bounded_io.parse_json_object` and validates field by field in small helper functions) and `checkpoints.py` as specified above.
- [ ] **Step 4: Run tests** → pass; `python tools/check_python_structure.py` → pass.
- [ ] **Step 5: Commit** (`feat: add context build spec and checkpoint store`).

---

### Task 7: Resumable context build runner and CLI (Fix 1, part 2)

**Files:**
- Create: `data_sources/modules/context_build/runner.py`, `cli.py`, `__main__.py`
- Modify docs: `.claude/commands/research.md` step 2, `.claude/commands/write.md` and `rewrite.md` context steps, `context/aeo-geo-blog-strategy.md` context-build paragraph
- Test: `tests/test_context_build_runner.py` (new)

**Interfaces:**
- Consumes: Task 6 `ContextBuildSpec`, `CheckpointStore`; `artifact_runtime.content_store.write_context_trace`; any client with `status, describe, search, expand, read, claims, build_context, validate_context` (`SimproVaultClient` in production).
- Produces: `runner.StageOutcome(stage_id: str, action: str, pack_sha256: str, receipt_sha256: str)` with `action` in `{"built", "reused"}`, `runner.ContextBuildResult(stages: tuple[StageOutcome, ...], trace_path: Path)`, `runner.ContextBuildError(RuntimeError)`, `runner.run_context_build(spec, *, client, workspace_root: Path, resume: bool, now: datetime | None = None) -> ContextBuildResult`.

Runner behavior:
1. Open `CheckpointStore(root, spec, resume=resume)`.
2. Request: if `resume` and the request file exists with content different from `spec.request`, raise `ContextBuildResumeError("request changed ...")`; otherwise write it (pretty JSON, `ensure_ascii=False`, trailing newline, atomic).
3. Discovery (`status` must be `"ready"`, `describe`, each `search(q, limit=50)`, `expand`, rediscovery check that every resource id appears in search or expansion results, then `read`) — each call goes through `store.get`/`store.put` so a resumed run skips completed calls.
4. Claim lookups through the store; write the `simpro-customer-proof-claim-lookup/v1` artifact when `claim_lookup_path` is set (copy the payload shape from `build_lookup_artifact` in `scripts/build_what_is_simpro_context.py:559-593`).
5. For each stage in order: if `resume` and both output files exist, call `client.validate_context(spec.request, pack, receipt)`; when `valid is True`, record `"reused"` and never rewrite the files (bindings pin their bytes). Otherwise call `build_context` with `{"request", "search_queries", "resource_ids", "resource_purposes", "constraints", "task_satisfaction": "satisfied", "unresolved_gaps": [], "claim_requests"}`, validate, and write pack then receipt immediately, before the next stage.
6. Write the trace last with `write_context_trace(root / spec.trace_path, {...compact discovery, stage outcomes, validations...}, workspace_root=root, generated_at=now)`.

- [ ] **Step 1: Write failing tests** with this fake client:

```python
class FakeVaultClient:
    def __init__(self, *, fail_on_build: int | None = None, valid: bool = True) -> None:
        self.calls: list[str] = []
        self.build_count = 0
        self.fail_on_build = fail_on_build
        self.valid = valid

    def status(self):
        self.calls.append("status")
        return {"status": "ready", "revisions": {"manifest_revision": "m1"}}

    def describe(self):
        self.calls.append("describe")
        return {"schema": "fake"}

    def search(self, query, limit=20):
        self.calls.append(f"search:{query}")
        return [{"resource_id": "res-a"}, {"resource_id": "res-b"}]

    def expand(self, resource_id, purpose="guidance"):
        self.calls.append(f"expand:{resource_id}")
        return []

    def read(self, resource_id, purpose="guidance"):
        self.calls.append(f"read:{resource_id}")
        return {"resource_id": resource_id, "content": "text"}

    def claims(self, query, *, use_mode, brand_scope, limit=20):
        self.calls.append(f"claims:{query}")
        return [{"claim_id": "claim-1", "public_url": "https://example.com/1"}]

    def build_context(self, build_input):
        self.build_count += 1
        if self.fail_on_build == self.build_count:
            raise RuntimeError("killed mid-build")
        ids = [row["claim_id"] for row in build_input["claim_requests"]]
        return {"pack": {"claims": ids, "build": self.build_count},
                "receipt": {"pack_sha256": f"p{self.build_count}", "receipt_sha256": f"r{self.build_count}"}}

    def validate_context(self, request, pack, receipt):
        self.calls.append("validate")
        return {"valid": self.valid, "errors": []}
```

Tests:
- `test_fresh_build_writes_every_stage_and_trace`: three stages → `build_count == 3`, all pack/receipt files and the trace exist, actions all `"built"`.
- `test_resume_after_crash_reuses_finished_stages`: first run with `fail_on_build=3` raises; stage 1 and 2 files exist, stage 3 does not. Second run with a fresh client and `resume=True` → actions `("reused", "reused", "built")`, `build_count == 1`, and stage 1 and 2 file bytes are unchanged (compare sha256 before and after).
- `test_resume_skips_completed_discovery_calls`: after a full run, a resumed run makes no `search:` or `read:` calls.
- `test_resume_rebuilds_when_saved_pack_no_longer_validates`: resumed run with `valid=False` → every stage rebuilt (`build_count == 3`). This is how 24-hour staleness and vault revision changes are handled: the connector's `validate_context` rejects them.
- `test_resume_refuses_changed_request`: change `request.scope.title` in the spec → `ContextBuildResumeError`.
- `test_rediscovery_failure_raises`: `resource_purposes` includes `res-missing` → `ContextBuildError`.

- [ ] **Step 2: Run** `python -m pytest tests/test_context_build_runner.py -v` → ImportError.
- [ ] **Step 3: Implement** `runner.py` with one helper per behavior step above (`_write_request`, `_discover`, `_claim_lookups`, `_run_stage`, `_write_trace`), each under complexity 10.
- [ ] **Step 4: CLI** `cli.py` + `__main__.py`:

```python
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build connector-bound context packs from a spec, resumably.")
    parser.add_argument("spec", help="Path to a simpro-context-build-spec/v1 JSON file.")
    parser.add_argument("--resume", action="store_true", help="Reuse checkpoints and packs that still validate.")
    args = parser.parse_args(argv)
    try:
        spec = load_spec(args.spec)
        result = run_context_build(spec, client=SimproVaultClient(), workspace_root=Path.cwd(), resume=args.resume)
    except (ContextBuildSpecError, ContextBuildResumeError, ContextBuildError, VaultClientError) as error:
        print(json.dumps({"ok": False, "error": {"code": type(error).__name__, "message": str(error)},
                          "recovery_hint": "Fix the spec or rerun with --resume after a crash."}))
        return 1
    print(json.dumps({"ok": True, "result": {"stages": [asdict(s) for s in result.stages],
                                             "trace": result.trace_path.as_posix()}}))
    return 0
```

`__main__.py`: `from .cli import main; raise SystemExit(main())`.
- [ ] **Step 5: Docs.** In `.claude/commands/research.md` step 2, replace the per-topic script guidance with: write `research/context-build-spec-[slug]-[date].json` from `config/context-build-spec.example.json`, then run `python -m data_sources.modules.context_build research/context-build-spec-[slug]-[date].json`. Add: "If the run stops (memory pressure, timeout), rerun with `--resume`; finished packs that still validate are reused and never rewritten." Mirror the same two sentences in `write.md`, `rewrite.md` and the context-build paragraph of `context/aeo-geo-blog-strategy.md`. Update selector examples there to name the `-customer-selector-` and `-fred-evaluation-` packs.
- [ ] **Step 6: Run tests** — `python -m pytest tests/test_context_build_runner.py tests/test_context_build_spec.py tests/test_context_trace_store.py tests/test_guard_cli_module_invocation.py tests/test_aeo_geo_workflow_docs.py tests/test_editorial_strategy_wiring.py -q && python tools/check_python_structure.py` → pass.
- [ ] **Step 7: Commit** (`feat: add resumable spec-driven vault context build`).

---

### Task 8 (optional, measured): Stop the customer-proof gate from re-opening the vault

Only start after Tasks 1-7 pass. Use superpowers:systematic-debugging.

**Files (expected):** `data_sources/modules/customer_proof/diversity_reuse.py:80-128`, `customer_proof/connector_inputs.py:73-120`, `vault_claim_receipts.py:104-153`; tests in `tests/test_customer_proof_diversity_guard.py`.

- [ ] **Step 1: Measure.** In the main checkout (which has the gitignored what-is-simpro artifacts), profile the gate: `python -m cProfile -o .seomachine/diversity.prof -m data_sources.modules.customer_proof_diversity_guard drafts/what-is-simpro-2026-10-05.md --proof-sidecar research/validation-what-is-simpro-2026-10-05.md`, then list the top 20 cumulative entries. Record wall time (release telemetry showed 479-1677 seconds).
- [ ] **Step 2: Decide.** Proceed only if the profile shows the time inside `load_validated_claim_set` / `SimproVaultClient` construction or `validate_context`. If it shows something else, stop and report the profile instead of changing code.
- [ ] **Step 3: Failing test.** Assert that one diversity check over two overused sources constructs the vault client at most once (count constructor calls through a patched `SimproVaultClient` in `vault_claim_receipts`).
- [ ] **Step 4: Implement** a process-level shared client in `connector_inputs._load_receipt_claims_cached` (pass `client=` to `load_validated_claim_set`), reusing the readiness session's `validated_claim_set` when its pack and receipt digests equal the comparison inputs.
- [ ] **Step 5: Verify** the test passes, the full diversity suite passes, and a re-measured wall time is under 60 seconds. Commit (`perf: reuse one vault client in customer proof diversity checks`).

---

### Task 9: Final verification and handoff

- [ ] **Step 1:** `python -m pytest tests/test_policy_definition_evidence.py tests/test_faq_question_match.py tests/test_customer_proof_decision_block.py tests/test_construction_finding_messages.py tests/test_release_sweep.py tests/test_context_build_spec.py tests/test_context_build_runner.py tests/test_blog_assembly_bom.py tests/test_blog_assembly_bom_guard.py tests/test_paa_provenance_guard.py tests/test_customer_proof_selector.py tests/test_customer_proof_diversity_guard.py tests/test_blog_release_precheck.py tests/test_release_chain_decision.py tests/test_context_trace_store.py tests/test_guard_cli_module_invocation.py tests/test_aeo_geo_workflow_docs.py tests/test_editorial_strategy_wiring.py -q` → all pass; compare against the Task 0 baseline.
- [ ] **Step 2:** `python tools/check_python_structure.py` → pass.
- [ ] **Step 3: End-to-end smoke (main checkout, after checking out the branch there).** Run the sweep against the passed what-is-simpro release inputs (same arguments as `scripts/run_what_is_simpro_release.sh final`, plus `--sweep-output research/prechecks/what-is-simpro-sweep-smoke.json --offline`). Expect `passed: true` and an elapsed time under 5 minutes. Then copy `research/validation-what-is-simpro-2026-10-05.md` to a temp name, delete its `## FAQ Source Policy` block, point `--proof-sidecar` at the copy, and confirm the sweep reports that blocker together with every other failure in one run.
- [ ] **Step 4:** Use superpowers:requesting-code-review on the branch, then superpowers:finishing-a-development-branch.

## Out of scope (flagged, not fixed)

- `.claude/commands/optimize.md:64` lists only Humanizer evidence for the optimization receipt, but `_validate_optimization_receipt` also requires `command_definition.optimize-command`, `agent_definition.*` and `agent_output.*` rows. A follow-up should correct that doc.
- Fixes 2 (owned product sentences) and 3 (lightweight edit receipts) and 7 (one release job per machine) were not approved for this plan.

## Execution

Recommended: **Subagent-driven** (superpowers:subagent-driven-development). Tasks 1-4 are independent and small, Tasks 6-7 and 5 are larger and benefit from a fresh reviewer each, and a shipped mistake in proof gates is costly.
