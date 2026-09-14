"""Focused blog assembly BOM validation routines."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .. import blog_assembly_contract, context_binding_guard
from ..blog_assembly_contract import canonical_artifact, load_json_object_snapshot
from ..guard_common import Finding
from ..publishable_markdown import FrontmatterError, read_publishable_markdown
from .artifacts import (
    _check_artifact_inventory,
    _check_supplied_path,
    _is_workspace_file,
)
from . import snapshot_adapters as blog_assembly_bom_snapshot
from .hindsight import _check_hindsight_strategy_policy
from .common import _check_topology, _finding, _sorted
from .content_policy import (
    _check_author,
    _check_connector,
    _check_identity,
    _check_paa_policy,
    _check_schema_and_faq,
)
from .header import (
    check_archived_artifact_shape,
    check_archived_header,
    check_current_artifact_shape,
    check_current_header,
)
from .dependencies import BomValidationDependencies
from .editorial import _check_research_provenance, _load_bound_editorial_plan
from .preflight import _check_preflight
from .reviews import _check_machine_reviews
from .workflow import _check_workflow

def missing_bom_finding() -> Finding:
    """Return the stable blocker for a blog without its execution record."""
    return _finding("bom_missing", "Blog artifacts require --assembly-bom.")


def check_archived_final_bom(
    bom: Mapping[str, Any],
    *,
    article_path: str | Path,
    workspace_root: str | Path,
) -> list[Finding]:
    """Validate an existing final BOM without imposing today's assembly date.

    Post-publish consumers need the closed BOM shape, current artifact hashes,
    stage chain, and preflight seal, but must not rerun date-sensitive release
    policy after publication.
    """
    root = Path(workspace_root).resolve()
    findings: list[Finding] = []
    if not isinstance(bom, Mapping):
        return [_finding("bom_archive_invalid", "Archived final BOM must be an object.")]
    header_findings, assembly_date = check_archived_header(bom)
    findings.extend(header_findings)

    artifacts = bom.get("artifacts")
    if not isinstance(artifacts, Mapping):
        findings.append(
            _finding("bom_artifacts_missing", "BOM requires a strict artifacts inventory.")
        )
        return _sorted(findings)
    findings.extend(check_archived_artifact_shape(bom, artifacts))

    findings.extend(_check_topology(bom))
    findings.extend(_check_artifact_inventory(bom, artifacts, root))
    findings.extend(_check_hindsight_strategy_policy(bom, artifacts, root))
    findings.extend(
        _check_machine_reviews(
            bom,
            artifacts,
            root,
            proof_sidecar_path=None,
        )
    )
    findings.extend(_check_supplied_path(artifacts, "article", article_path, root))
    if _is_workspace_file(article_path, root):
        try:
            article = read_publishable_markdown(article_path)
        except (OSError, UnicodeError, FrontmatterError) as error:
            findings.append(
                _finding("bom_article_unreadable", f"Article cannot be read: {error}")
            )
        else:
            findings.extend(
                finding
                for finding in _check_identity(bom, article, assembly_date)
                if finding.get("rule_id")
                != "blog_identity_assembly_date_not_current"
            )
            findings.extend(_check_schema_and_faq(bom, article))
    findings.extend(_check_workflow(bom, artifacts, root))
    findings.extend(_check_preflight(bom, artifacts, root))
    return _sorted(findings)


def check_bom_file(
    path: str | Path,
    *,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    context_request_path: str | Path | None = None,
    context_pack_path: str | Path | None = None,
    context_receipt_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
    expected_lifecycle_state: str | None = None,
    require_current_schema: bool = False,
    context_result: context_binding_guard.ContextValidationResult | None = None,
    context_client: Any = None,
    vault_root: str | Path | None = None,
    dependencies: BomValidationDependencies | None = None,
) -> list[Finding]:
    """Read and validate one strict BOM against current workflow files."""
    source = Path(path)
    root = Path(workspace_root).resolve() if workspace_root else source.resolve().parent.parent
    if workspace_root is not None:
        try:
            canonical_artifact(source, workspace_root=root)
        except ValueError as error:
            return [_finding("bom_path_invalid", f"Blog assembly BOM path is invalid: {error}")]
    try:
        payload = load_json_object_snapshot(source, field="blog assembly BOM").payload
    except ValueError as error:
        return [_finding("bom_invalid", f"Blog assembly BOM is invalid: {error}")]
    if not isinstance(payload, Mapping):
        return [_finding("bom_invalid", "Blog assembly BOM must be a JSON object.")]
    return check_bom(
        payload,
        article_path=article_path,
        validation_sidecar_path=validation_sidecar_path,
        context_request_path=context_request_path,
        context_pack_path=context_pack_path,
        context_receipt_path=context_receipt_path,
        workspace_root=root,
        expected_lifecycle_state=expected_lifecycle_state,
        require_current_schema=require_current_schema,
        context_result=context_result,
        context_client=context_client,
        vault_root=vault_root,
        dependencies=dependencies,
    )


def check_bom(
    bom: Mapping[str, Any],
    *,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    context_request_path: str | Path | None = None,
    context_pack_path: str | Path | None = None,
    context_receipt_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
    expected_lifecycle_state: str | None = None,
    require_current_schema: bool = False,
    context_result: context_binding_guard.ContextValidationResult | None = None,
    context_client: Any = None,
    vault_root: str | Path | None = None,
    captured: Any = None,
    dependencies: BomValidationDependencies | None = None,
) -> list[Finding]:
    """Return deterministic blocking findings for one BOM object."""
    dependencies = dependencies or BomValidationDependencies()
    root = Path(workspace_root or Path.cwd()).resolve()
    findings: list[Finding] = []
    header_findings, assembly_date = check_current_header(
        bom,
        expected_lifecycle_state=expected_lifecycle_state,
        require_current_schema=require_current_schema,
    )
    findings.extend(header_findings)

    findings.extend(_check_topology(bom))
    artifacts = bom.get("artifacts")
    if not isinstance(artifacts, Mapping):
        findings.append(_finding("bom_artifacts_missing", "BOM requires a strict artifacts inventory."))
        return _sorted(findings)
    findings.extend(check_current_artifact_shape(bom, artifacts))

    article = None
    sidecar_content = ""
    findings.extend(_check_artifact_inventory(bom, artifacts, root, captured=captured))
    findings.extend(
        _check_machine_reviews(
            bom,
            artifacts,
            root,
            proof_sidecar_path=validation_sidecar_path,
            captured=captured,
            dependencies=dependencies,
        )
    )
    article_path_findings = _check_supplied_path(
        artifacts,
        "article",
        article_path,
        root,
        captured=captured,
    )
    sidecar_path_findings = _check_supplied_path(
        artifacts,
        "validation_sidecar",
        validation_sidecar_path,
        root,
        captured=captured,
    )
    findings.extend(article_path_findings)
    findings.extend(sidecar_path_findings)
    (
        article, sidecar_content, bound_editorial_plan,
        article_input_safe, sidecar_input_safe, primary_findings,
    ) = blog_assembly_bom_snapshot.load_primary_artifacts(
        _snapshot_dependencies(dependencies),
        captured=captured,
        artifacts=artifacts,
        article_path=article_path, validation_sidecar_path=validation_sidecar_path,
        root=root,
    )
    findings.extend(primary_findings)

    safe_context_inputs: dict[str, str | Path | None] = {}
    for label, supplied in (
        ("context_request", context_request_path),
        ("context_pack", context_pack_path),
        ("context_receipt", context_receipt_path),
    ):
        if supplied is not None:
            findings.extend(
                _check_supplied_path(
                    artifacts, label, supplied, root, captured=captured,
                )
            )
            safe_context_inputs[label] = (
                supplied
                if (
                    captured is not None
                    and captured.optional_snapshot(label) is not None
                ) or _is_workspace_file(supplied, root)
                else None
            )
        else:
            safe_context_inputs[label] = None

    if article is not None:
        findings.extend(_check_identity(bom, article, assembly_date))
        findings.extend(_check_author(bom, article, sidecar_content))
        findings.extend(_check_schema_and_faq(bom, article))
        findings.extend(_check_paa_policy(bom, article))
        findings.extend(
            _check_connector(
                bom,
                article,
                validation_sidecar_path=(
                    validation_sidecar_path if sidecar_input_safe else None
                ),
                context_request_path=safe_context_inputs["context_request"],
                context_pack_path=safe_context_inputs["context_pack"],
                context_receipt_path=safe_context_inputs["context_receipt"],
                context_result=context_result,
                context_client=context_client,
                editorial_plan=bound_editorial_plan,
                vault_root=vault_root,
                dependencies=dependencies,
            )
        )
    connector = bom.get("connector_binding")
    for rule_id, message in blog_assembly_bom_snapshot.sidecar_binding_errors(
        blog_assembly_contract,
        sidecar_content,
        artifacts,
        captured=captured,
        root=root,
        required=(
            isinstance(connector, Mapping)
            and connector.get("status") == "required"
        ),
    ):
        findings.append(_finding(rule_id, message))
    findings.extend(
        _check_research_provenance(
            bom,
            artifacts,
            root,
            article_path,
            captured=captured,
            dependencies=dependencies,
        )
    )
    findings.extend(
        _check_workflow(
            bom,
            artifacts,
            root,
            captured=captured,
            dependencies=dependencies,
        )
    )
    findings.extend(
        _check_preflight(
            bom,
            artifacts,
            root,
            captured=captured,
            dependencies=dependencies,
        )
    )
    return _sorted(findings)


def _snapshot_dependencies(
    dependencies: BomValidationDependencies,
) -> BomValidationDependencies:
    return dependencies.bind(
        FrontmatterError=FrontmatterError,
        _finding=_finding,
        _is_workspace_file=_is_workspace_file,
        _load_bound_editorial_plan=_load_bound_editorial_plan,
        read_publishable_markdown=read_publishable_markdown,
    )
