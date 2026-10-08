"""A fully failing URL transport is a URL-gate blocker, never a readiness crash."""
from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import Mock, patch

import requests

from data_sources.modules import publish_readiness
from data_sources.modules.public_http import PublicHttpTransport
from tests.test_publish_readiness import (
    CURRENT_GATES,
    _write_non_connector_bom,
    files,  # noqa: F401  (pytest fixture)
    score,
)


def _offline(*_args, **_kwargs):
    raise requests.ConnectionError("network unreachable")


def test_every_url_request_failing_blocks_at_the_url_gate(files):  # noqa: F811
    article, sidecar = files
    article.write_text(
        article.read_text(encoding="utf-8")
        + "\n\nSee [the guidance](https://www.example.org/guidance) and "
        "[the report](https://www.example.org/report).\n",
        encoding="utf-8",
    )
    bom = _write_non_connector_bom(article, sidecar)
    scorer = Mock()
    scorer.score.return_value = score(True)
    with ExitStack() as stack:
        for name, target in CURRENT_GATES:
            if name == "context_binding":
                stack.enter_context(patch(
                    f"data_sources.modules.publish_readiness.{target}",
                    return_value=publish_readiness.context_binding_guard.ContextValidationResult(
                        required=True, findings=(),
                    ),
                ))
                continue
            stack.enter_context(patch(
                f"data_sources.modules.publish_readiness.{target}", return_value=[]
            ))
        stack.enter_context(patch(
            "data_sources.modules.publish_readiness.blog_assembly_bom_guard.check_bom",
            return_value=[],
        ))
        stack.enter_context(patch(
            "data_sources.modules.readiness.adapters.ContentScorer", return_value=scorer
        ))
        stack.enter_context(patch.object(PublicHttpTransport, "request_many", _offline))
        stack.enter_context(patch.object(PublicHttpTransport, "request", _offline))
        result = publish_readiness.run_publish_readiness(
            article,
            proof_sidecar=sidecar,
            assembly_bom=bom,
            workspace_root=article.parent,
        )

    url_gate = next(gate for gate in result["gates"] if gate["name"] == "url_validator")
    assert result["passed"] is False
    assert url_gate["errors"] == 2
    assert {f["rule_id"] for f in url_gate["findings"]} == {"url_unresolved"}
    assert url_gate["passed"] is False
