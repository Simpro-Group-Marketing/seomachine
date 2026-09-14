from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from data_sources.modules import (
    blog_assembly_bom_guard,
    blog_assembly_bom_preflight_session,
    blog_assembly_bom_reviews,
    blog_assembly_bom_session,
    blog_assembly_bom_snapshot,
)
from data_sources.modules.blog_bom_validation import (
    BomValidationDependencies,
    check_archived_final_bom,
    check_bom,
    check_bom_file,
    missing_bom_finding,
)
from data_sources.modules.blog_bom_validation.content_policy import _check_connector
from data_sources.modules.blog_bom_validation import (
    preflight_session,
    review_validation,
    session_validation,
    snapshot_adapters,
)
from data_sources.modules.blog_assembly_bom import (
    BomValidationDependencies as BuilderBomValidationDependencies,
)
from data_sources.modules.context_binding_guard import ContextValidationResult


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "data_sources" / "modules"


def test_compatibility_facade_exports_exact_package_callables():
    assert blog_assembly_bom_guard.check_bom is check_bom
    assert blog_assembly_bom_guard.check_bom_file is check_bom_file
    assert (
        blog_assembly_bom_guard.check_archived_final_bom
        is check_archived_final_bom
    )
    assert blog_assembly_bom_guard.missing_bom_finding is missing_bom_finding
    assert BomValidationDependencies is BuilderBomValidationDependencies


def test_validation_package_has_no_globals_dispatch_and_respects_size_budget():
    files = list((PACKAGE_ROOT / "blog_bom_validation").glob("*.py"))
    files.append(PACKAGE_ROOT / "blog_assembly_bom_guard.py")
    assert files
    for path in files:
        source = path.read_text(encoding="utf-8")
        assert "globals()" not in source
        assert len(source.splitlines()) < 500


def test_session_helpers_are_explicit_facades_over_package_owners():
    assert blog_assembly_bom_snapshot.json_artifact is snapshot_adapters.json_artifact
    assert (
        blog_assembly_bom_session.check_editorial_plan
        is session_validation.check_editorial_plan
    )
    assert (
        blog_assembly_bom_reviews.check_machine_reviews
        is review_validation.check_machine_reviews
    )
    assert (
        blog_assembly_bom_preflight_session.load_preflight
        is preflight_session.load_preflight
    )


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
