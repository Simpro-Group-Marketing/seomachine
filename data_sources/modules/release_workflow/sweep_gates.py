"""Release gates outside ``ARTICLE_GATES`` that the sweep also runs once.

Each function mirrors the call the readiness pipeline makes
(``readiness/pipeline_tail.py`` and ``readiness/runner.py``) and returns rows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

try:
    from .. import (
        ai_copy_linter,
        blog_identity_guard,
        chrome_review_evidence,
        context_binding_guard,
        public_artifact_guard,
        public_research_link_guard,
    )
    from ..readiness.adapters import _gate_from_url_summary
    from ..readiness.runtime_policy import _no_fit_customer_proof_findings
    from ..url_validator import validate_content_urls
except ImportError:  # pragma: no cover - supports direct script execution.
    import ai_copy_linter
    import blog_identity_guard
    import chrome_review_evidence
    import context_binding_guard
    import public_artifact_guard
    import public_research_link_guard
    from readiness.adapters import _gate_from_url_summary
    from readiness.runtime_policy import _no_fit_customer_proof_findings
    from url_validator import validate_content_urls

AI_PROFILE = "simpro-web"
Rows = list[Mapping[str, Any]]


def identity_rows(article_text: str, assembly_date: Any) -> Rows:
    """Mirror the ``artifact_identity`` call in ``readiness/runner.py``."""
    return list(blog_identity_guard.check_article(
        article_text, assembly_date=assembly_date or None
    ))


def public_artifact_rows(article_text: str) -> Rows:
    return list(public_artifact_guard.check_content(article_text))


def ai_copy_rows(article_text: str) -> Rows:
    return list(ai_copy_linter.lint_content(article_text, profile=AI_PROFILE))


class UrlState:
    """Compute the URL summary once; share it between url_validator and its consumers."""

    def __init__(self, article_text: str | None, sidecar: Any, root: Path) -> None:
        self._text, self._sidecar, self._root = article_text, sidecar, root
        self._summary: Any = None
        self._error: Exception | None = None
        self._done = False

    def get(self) -> Any:
        if not self._done:
            self._done = True
            try:
                summary = validate_content_urls(self._text or "")
                self._summary = chrome_review_evidence.apply_chrome_review_evidence_fallbacks(
                    summary,
                    proof_sidecar=None if self._sidecar is None else str(self._sidecar),
                    workspace_root=self._root,
                )
            except Exception as error:  # noqa: BLE001 - reported by the caller's run_check.
                self._error = error
        if self._error is not None:
            raise self._error
        return self._summary

    def peek(self) -> Any:
        """Return the summary when it was computed successfully, else None."""
        return self._summary if self._done and self._error is None else None


def url_validator_rows(state: UrlState) -> Rows:
    return list(_gate_from_url_summary(state.get())["findings"])


def research_link_rows(article_text: str, sidecar: Any, state: UrlState) -> Rows:
    proof = None if sidecar is None else Path(sidecar).read_text(encoding="utf-8")
    return list(public_research_link_guard.check_content(
        article_text, proof_content=proof, url_summary=state.peek()
    ))


def context_binding_rows(args: Any, policy: Mapping[str, Any]) -> Rows:
    """Mirror ``runner._run_context_gate``; the sweep supplies no connector client."""
    result = context_binding_guard.validate_context_artifacts(
        str(args.article),
        fail_on="error",
        proof_sidecar=getattr(args, "proof_sidecar", None),
        context_request=getattr(args, "context_request", None),
        context_pack=getattr(args, "context_pack", None),
        context_receipt=getattr(args, "context_receipt", None),
        editorial_plan=policy.get("editorial_plan"),
        vault_root=None,
        client=None,
    )
    return list(result.findings)


def no_fit_rows(article_text: str, policy: Mapping[str, Any]) -> Rows:
    return list(_no_fit_customer_proof_findings(article_text, runtime_policy=policy, inputs=None))
