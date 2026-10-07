"""Classify an article edit as wording-only so it can chain a light receipt.

A wording-only edit changes sentence wording and nothing a gate or an earlier
artifact binds by structure: frontmatter, headings, links and anchors, numbers,
FAQ questions, quotes, media placeholders, mapped proof claims, and bound
context-claim passages all stay identical. Every readiness gate still runs on
the edited bytes; this classification only decides whether the expensive
regeneration steps (scrub, context binding, machine reviews) may be carried
forward instead of rerun.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:
    from .blog_assembly_contract import atomic_write_json, canonical_json_sha256
    from .blog_assembly_stage_receipt import (
        StageReceiptError,
        begin_native_edit,
        finish_native_edit,
        load_stage_receipt,
        stage_evidence_path,
        write_stage_evidence,
    )
    from .content_scrubber import scrub_content
    from .context_binding_guard import _json_block, _normalize_public_text, normalize_public_body
    from .faq_structure import detect_faq_structure
    from .frontmatter import FRONTMATTER_RE
    from .image_placeholder import (
        is_production_image_placeholder_line,
        is_production_video_placeholder_line,
    )
    from .numeric_claim_source_guard import (
        _blank_fenced_code,
        _extract_numeric_tokens,
        _strip_frontmatter_preserve_lines,
    )
    from .public_http.markdown_urls import extract_urls
    from .proof_link_policy import STRUCTURED_QUOTE_RE, _normalize_text, _proof_rows
    from .wording_edit_chain import (
        MAX_CUMULATIVE_CHANGED_WORD_RATIO,
        WORDING_EDIT_ANCHOR_STAGES,
        WORDING_EDIT_STAGE,
        WORDING_EDIT_TOOL,
        trailing_edit_indexes,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import atomic_write_json, canonical_json_sha256
    from blog_assembly_stage_receipt import (
        StageReceiptError,
        begin_native_edit,
        finish_native_edit,
        load_stage_receipt,
        stage_evidence_path,
        write_stage_evidence,
    )
    from content_scrubber import scrub_content
    from context_binding_guard import _json_block, _normalize_public_text, normalize_public_body
    from faq_structure import detect_faq_structure
    from frontmatter import FRONTMATTER_RE
    from image_placeholder import (
        is_production_image_placeholder_line,
        is_production_video_placeholder_line,
    )
    from numeric_claim_source_guard import (
        _blank_fenced_code,
        _extract_numeric_tokens,
        _strip_frontmatter_preserve_lines,
    )
    from public_http.markdown_urls import extract_urls
    from proof_link_policy import STRUCTURED_QUOTE_RE, _normalize_text, _proof_rows
    from wording_edit_chain import (
        MAX_CUMULATIVE_CHANGED_WORD_RATIO,
        WORDING_EDIT_ANCHOR_STAGES,
        WORDING_EDIT_STAGE,
        WORDING_EDIT_TOOL,
        trailing_edit_indexes,
    )


WORDING_EDIT_REPORT_SCHEMA = "simpro-blog-wording-edit-report/v1"
HEADING_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)


@dataclass(frozen=True)
class WordingEditReport:
    """The invariant check and word delta for one before/after article pair."""

    before_sha256: str
    after_sha256: str
    changed_words: int
    body_words: int
    violations: tuple[str, ...]

    def as_payload(self) -> dict[str, Any]:
        return {
            "schema": WORDING_EDIT_REPORT_SCHEMA,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "changed_words": self.changed_words,
            "body_words": self.body_words,
            "violations": list(self.violations),
        }


def classify_wording_edit(before: str, after: str, *, sidecar: str = "") -> WordingEditReport:
    """Return which wording-only invariants the edit breaks and its word delta."""
    checks = {
        "frontmatter": _frontmatter,
        "headings": _headings,
        "links": _links,
        "numbers": _numbers,
        "faq_questions": _faq_questions,
        "quotes": _quotes,
        "media_placeholders": _media_placeholders,
    }
    violations = [name for name, extract in checks.items() if extract(before) != extract(after)]
    if _lost_proof_claims(before, after, sidecar):
        violations.append("proof_claims")
    if not _context_claim_passages_intact(after, sidecar):
        violations.append("context_claim_passages")
    before_words = _body_words(before)
    return WordingEditReport(
        before_sha256=_sha256(before),
        after_sha256=_sha256(after),
        changed_words=_changed_words(before_words, _body_words(after)),
        body_words=len(before_words),
        violations=tuple(violations),
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _frontmatter(content: str) -> str:
    match = FRONTMATTER_RE.match(content)
    return match.group(0) if match else ""


def _visible_body(content: str) -> str:
    return _blank_fenced_code(_strip_frontmatter_preserve_lines(content))


def _headings(content: str) -> list[str]:
    return [line.strip() for line in HEADING_RE.findall(_visible_body(content))]


def _links(content: str) -> Counter:
    return Counter((link.url, link.anchor) for link in extract_urls(content))


def _numbers(content: str) -> Counter:
    return Counter(_extract_numeric_tokens(_visible_body(content)))


def _faq_questions(content: str) -> list[str]:
    return [entry.question for entry in detect_faq_structure(content).entries]


def _quotes(content: str) -> Counter:
    return Counter(STRUCTURED_QUOTE_RE.findall(_visible_body(content)))


def _media_placeholders(content: str) -> list[str]:
    return [
        line.strip()
        for line in content.splitlines()
        if is_production_image_placeholder_line(line.strip())
        or is_production_video_placeholder_line(line.strip())
    ]


def _lost_proof_claims(before: str, after: str, sidecar: str) -> bool:
    normalized_before = _normalize_text(before)
    normalized_after = _normalize_text(after)
    return any(
        claim in normalized_before and claim not in normalized_after
        for claim in (_normalize_text(row.claim) for row in _proof_rows(sidecar))
        if claim
    )


def _context_claim_passages_intact(after: str, sidecar: str) -> bool:
    try:
        claim_map = _json_block(sidecar, "Context Claim Use Map")
    except ValueError:
        return True
    if not isinstance(claim_map, list):
        return False
    body = normalize_public_body(after)
    return all(
        isinstance(row, dict)
        and isinstance(row.get("public_text"), str)
        and body.count(_normalize_public_text(row["public_text"])) == 1
        for row in claim_map
    )


def _body_words(content: str) -> list[str]:
    return re.findall(r"\S+", _strip_frontmatter_preserve_lines(content))


def _changed_words(before: list[str], after: list[str]) -> int:
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    return sum(
        max(i2 - i1, j2 - j1)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag != "equal"
    )


def begin_wording_edit(
    *,
    article_path: str | Path,
    state_path: str | Path,
    previous_receipt_path: str | Path,
    workspace_root: str | Path | None = None,
    started_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Open a wording edit chained from context binding or a prior wording edit."""
    previous = load_stage_receipt(previous_receipt_path, workspace_root=workspace_root)
    if previous["stage"] not in WORDING_EDIT_ANCHOR_STAGES | {WORDING_EDIT_STAGE}:
        raise StageReceiptError(
            "wording_edit_predecessor_invalid",
            "a wording edit must follow context binding or another wording edit",
        )
    before = _read_text(article_path)
    if _sha256(before) != previous["output_artifact_hashes"].get("article"):
        raise StageReceiptError(
            "wording_edit_article_changed",
            "the article changed after the previous receipt; start from its output",
        )
    if previous["stage"] == WORDING_EDIT_STAGE:
        prior = _evidence_payload(previous_receipt_path)
        anchor_words, prior_changed = prior["anchor_body_words"], prior["cumulative_changed_words"]
    else:
        anchor_words, prior_changed = len(_body_words(before)), 0
    state = begin_native_edit(
        article_path=article_path,
        state_path=state_path,
        run_id=previous["run_id"],
        stage=WORDING_EDIT_STAGE,
        tool_name=WORDING_EDIT_TOOL[0],
        tool_version=WORDING_EDIT_TOOL[1],
        previous_receipt_hash=previous["receipt_hash"],
        started_at=started_at,
    )
    atomic_write_json(
        _snapshot_path(state_path),
        {
            "before_text": before,
            "anchor_body_words": anchor_words,
            "prior_changed_words": prior_changed,
        },
    )
    return state


def finish_wording_edit(
    *,
    state_path: str | Path,
    article_path: str | Path,
    receipt_path: str | Path,
    sidecar_path: str | Path | None,
    workspace_root: str | Path | None = None,
    completed_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Classify the edit and, only if it is wording-only, write its receipt."""
    snapshot_path = _snapshot_path(state_path)
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StageReceiptError("wording_edit_state_invalid", str(error)) from error
    before = snapshot.get("before_text")
    article_in = (state.get("input_artifact_hashes") or {}).get("article")
    if not isinstance(before, str) or _sha256(before) != article_in:
        raise StageReceiptError(
            "wording_edit_state_invalid",
            "the wording edit snapshot does not match its open state",
        )
    after = _read_text(article_path)
    sidecar = _read_text(sidecar_path) if sidecar_path else ""
    report = classify_wording_edit(before, after, sidecar=sidecar)
    anchor_words = int(snapshot["anchor_body_words"])
    cumulative = int(snapshot["prior_changed_words"]) + report.changed_words
    problem = _edit_problem(report, after, cumulative, anchor_words)
    if problem:
        raise StageReceiptError(*problem)
    payload = {
        **report.as_payload(),
        "before_text": before,
        "anchor_body_words": anchor_words,
        "cumulative_changed_words": cumulative,
    }
    manifest, _ = write_stage_evidence(
        receipt_path,
        evidence_hashes={"wording_edit_report": canonical_json_sha256(payload)},
        payload=payload,
    )
    receipt = finish_native_edit(
        state_path=state_path,
        article_path=article_path,
        receipt_path=receipt_path,
        evidence_artifacts={"wording_edit_report": manifest},
        completed_at=completed_at,
        workspace_root=workspace_root,
    )
    snapshot_path.unlink()
    return receipt


def verify_wording_edits(
    stage_receipt_paths: Sequence[str | Path],
    receipts: Sequence[Mapping[str, Any]],
    *,
    final_article: str,
    sidecar: str,
    evidence_loader: Callable[[int], Mapping[str, Any]] | None = None,
) -> list[str]:
    """Re-check the trailing wording-edit run from its evidence and the final article."""
    edits = trailing_edit_indexes(receipts)
    if not edits:
        return []
    start = edits.start
    load = evidence_loader or (lambda index: _evidence_payload(stage_receipt_paths[index], strict=False))
    befores = [load(index).get("before_text") for index in edits]
    if not all(isinstance(before, str) for before in befores):
        return ["every trailing wording edit receipt needs its wording edit report evidence"]
    errors: list[str] = []
    cumulative = 0
    for offset, before in enumerate(befores):
        after = befores[offset + 1] if offset + 1 < len(befores) else final_article
        receipt = receipts[start + offset]
        if (
            _sha256(before) != receipt["input_artifact_hashes"].get("article")
            or _sha256(after) != receipt["output_artifact_hashes"].get("article")
        ):
            errors.append(f"wording edit {offset + 1} evidence does not match its article hashes")
            continue
        report = classify_wording_edit(before, after, sidecar=sidecar)
        cumulative += report.changed_words
        problem = _edit_problem(report, after, 0, 0)
        if problem:
            errors.append(f"wording edit {offset + 1}: {problem[1]}")
    anchor_words = len(_body_words(befores[0]))
    if cumulative > MAX_CUMULATIVE_CHANGED_WORD_RATIO * anchor_words:
        errors.append(_budget_message(cumulative, anchor_words))
    return errors


def _edit_problem(
    report: WordingEditReport, after: str, cumulative: int, anchor_words: int
) -> tuple[str, str] | None:
    if report.violations:
        return (
            "wording_edit_not_wording_only",
            "the edit changes " + ", ".join(report.violations)
            + "; revert those changes or run the full draft path",
        )
    if scrub_content(after) != after:
        return ("wording_edit_scrub_required", "the edited article needs scrub fixes; apply them first")
    if cumulative > MAX_CUMULATIVE_CHANGED_WORD_RATIO * anchor_words:
        return ("wording_edit_budget_exceeded", _budget_message(cumulative, anchor_words))
    return None


def _budget_message(cumulative: int, anchor_words: int) -> str:
    return (
        f"wording edits changed {cumulative} of {anchor_words} words since context binding, "
        f"over the {MAX_CUMULATIVE_CHANGED_WORD_RATIO:.0%} budget; run the full draft path"
    )


def _snapshot_path(state_path: str | Path) -> Path:
    state = Path(state_path)
    return state.with_name(f"{state.stem}-before.json")


def _read_text(path: str | Path) -> str:
    try:
        return Path(path).read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise StageReceiptError("wording_edit_input_invalid", str(error)) from error


def _evidence_payload(receipt_path: str | Path, *, strict: bool = True) -> dict[str, Any]:
    try:
        manifest = json.loads(stage_evidence_path(receipt_path).read_text(encoding="utf-8"))
        payload = manifest["payload"]
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        return payload
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        if strict:
            raise StageReceiptError("wording_edit_evidence_invalid", str(error)) from error
        return {}


def main(argv: Sequence[str] | None = None) -> int:
    """Open or close one chained wording-only edit receipt."""
    parser = argparse.ArgumentParser(description="Chain a wording-only edit receipt.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    begin = subparsers.add_parser("begin", help="snapshot the article before a wording edit")
    begin.add_argument("--previous-receipt", required=True)
    finish = subparsers.add_parser("finish", help="classify the edit and write its receipt")
    finish.add_argument("--receipt", required=True)
    finish.add_argument("--sidecar", required=True)
    for command in (begin, finish):
        command.add_argument("--article", required=True)
        command.add_argument("--state", required=True)
        command.add_argument("--workspace-root")
    args = parser.parse_args(argv)
    try:
        if args.command == "begin":
            begin_wording_edit(
                article_path=args.article,
                state_path=args.state,
                previous_receipt_path=args.previous_receipt,
                workspace_root=args.workspace_root,
            )
        else:
            receipt = finish_wording_edit(
                state_path=args.state,
                article_path=args.article,
                receipt_path=args.receipt,
                sidecar_path=args.sidecar,
                workspace_root=args.workspace_root,
            )
            print(json.dumps({"receipt": args.receipt, "receipt_hash": receipt["receipt_hash"]}))
    except StageReceiptError as error:
        print(f"{error.code}: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
