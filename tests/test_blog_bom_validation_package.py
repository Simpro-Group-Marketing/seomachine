from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from data_sources.modules.blog_bom_validation import (
    BomValidationDependencies,
)
from data_sources.modules.blog_bom_validation.content_policy import _check_connector
from data_sources.modules.context_binding_guard import ContextValidationResult


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "data_sources" / "modules"


def test_validation_package_has_no_globals_dispatch_and_respects_size_budget():
    files = list((PACKAGE_ROOT / "blog_bom_validation").glob("*.py"))
    assert files
    for path in files:
        source = path.read_text(encoding="utf-8")
        assert "globals()" not in source
        assert len(source.splitlines()) < 500


def test_connector_validation_uses_injected_dependency(tmp_path: Path):
    result = ContextValidationResult(required=True, findings=())
    calls: list[dict[str, object]] = []

    def validate(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return result

    article_path = tmp_path / "article.md"
    article = SimpleNamespace(raw="Simpro", path=article_path)
    bom = {
        "connector_binding": {
            "status": "required",
            "context": result.context_summary(),
        }
    }

    findings = _check_connector(
        bom,
        article,
        validation_sidecar_path=tmp_path / "validation.md",
        context_request_path=tmp_path / "request.json",
        context_pack_path=tmp_path / "pack.json",
        context_receipt_path=tmp_path / "receipt.json",
        context_result=None,
        context_client=object(),
        editorial_plan={"schema": "test-plan"},
        vault_root=tmp_path,
        dependencies=BomValidationDependencies(
            validate_context_artifacts=validate,
        ),
    )

    assert findings == []
    assert len(calls) == 1
    assert calls[0]["args"] == (article_path,)
    assert calls[0]["kwargs"]["editorial_plan"] == {"schema": "test-plan"}
