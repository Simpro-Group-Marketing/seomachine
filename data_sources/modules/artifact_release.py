"""Unified release entry point for governed blogs and landing pages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import blog_release, context_binding_guard, publish_readiness, release_authorization
from .artifact_runtime.limits import ARTICLE_MAX_BYTES, SIDECAR_MAX_BYTES, validate_text_artifact
from .blog_assembly_contract import load_json_object_snapshot, validate_sha256
from .publishable_markdown import read_publishable_markdown
from .readiness.telemetry import ReadinessTelemetry


ReleaseInvocationError = blog_release.ReleaseInvocationError
ReleaseResult = blog_release.ReleaseResult


def run_artifact_release(
    *,
    article: str | Path,
    run_id: str,
    proof_sidecar: str | Path,
    output_dir: str | Path,
    workspace_root: str | Path,
    artifact_kind: str | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    vault_root: str | Path | None = None,
    **blog_options: Any,
) -> ReleaseResult:
    """Derive artifact kind and run its single governed release lifecycle."""
    root = _workspace_root(workspace_root)
    try:
        article_path = validate_text_artifact(
            article,
            label="article",
            workspace_root=root,
            max_bytes=ARTICLE_MAX_BYTES,
        )
        sidecar_path = validate_text_artifact(
            proof_sidecar,
            label="proof_sidecar",
            workspace_root=root,
            max_bytes=SIDECAR_MAX_BYTES,
        )
        detected = context_binding_guard.require_artifact_kind(
            read_publishable_markdown(article_path).raw,
            article_path=article_path,
        )
    except ValueError as error:
        raise ReleaseInvocationError(str(error)) from error
    if artifact_kind is not None and artifact_kind != detected:
        raise ReleaseInvocationError("artifact_kind conflicts with the article")
    if detected == "blog":
        return blog_release._run_blog_release(
            article=article_path,
            run_id=run_id,
            proof_sidecar=sidecar_path,
            output_dir=output_dir,
            workspace_root=root,
            context_request=context_request,
            context_pack=context_pack,
            context_receipt=context_receipt,
            vault_root=vault_root,
            **blog_options,
        )
    if blog_options:
        names = ", ".join(sorted(blog_options))
        raise ReleaseInvocationError(f"landing-page release received blog-only options: {names}")
    return _run_landing_release(
        article=article_path,
        run_id=_required_run_id(run_id),
        proof_sidecar=sidecar_path,
        output_dir=output_dir,
        workspace_root=root,
        context_request=context_request,
        context_pack=context_pack,
        context_receipt=context_receipt,
        vault_root=vault_root,
    )


def _run_landing_release(
    *,
    article: Path,
    run_id: str,
    proof_sidecar: Path,
    output_dir: str | Path,
    workspace_root: Path,
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    vault_root: str | Path | None,
) -> ReleaseResult:
    destination = _new_output_dir(output_dir, workspace_root=workspace_root)
    paths = _landing_paths(destination)
    telemetry = ReadinessTelemetry(
        run_id=run_id,
        phase="release",
        failure_output=paths["release_telemetry"],
    )
    try:
        with telemetry.stage("preflight_readiness"):
            preflight = publish_readiness.run_publish_readiness(
                article,
                proof_sidecar=proof_sidecar,
                context_request=context_request,
                context_pack=context_pack,
                context_receipt=context_receipt,
                assembly_bom=None,
                phase="preflight",
                workspace_root=workspace_root,
                artifact_kind="landing_page",
                run_id=run_id,
                vault_root=vault_root,
                telemetry=telemetry,
            )
        with telemetry.stage("preflight_persistence"):
            preflight_receipt = publish_readiness.write_readiness_result(
                paths["preflight_readiness"],
                preflight,
                receipt_path=paths["preflight_receipt"],
                workspace_root=workspace_root,
            )
        if preflight.get("passed") is not True or preflight_receipt is None:
            return _finish(
                telemetry,
                paths,
                ReleaseResult(1, destination, "preflight_readiness", "preflight readiness blocked release"),
            )
        receipt = load_json_object_snapshot(
            preflight_receipt,
            field="preflight readiness receipt",
        ).payload
        previous_hash = validate_sha256(
            receipt.get("receipt_hash"),
            field="preflight readiness receipt hash",
        )
        with telemetry.stage("final_attestation"):
            final = publish_readiness.build_final_readiness_attestation(
                preflight,
                final_bom=None,
                run_id=run_id,
                workspace_root=workspace_root,
                telemetry=telemetry,
            )
            final = release_authorization.prepare_final_release_result(
                final,
                release_manifest_path=paths["release_manifest"],
                previous_receipt_hash=previous_hash,
                workspace_root=workspace_root,
            )
        with telemetry.stage("final_persistence"):
            publish_readiness.write_readiness_result(
                paths["final_readiness"],
                final,
                receipt_path=paths["final_receipt"],
                workspace_root=workspace_root,
            )
            release_authorization.load_publish_authorization(
                final_readiness_path=paths["final_readiness"],
                final_receipt_path=paths["final_receipt"],
                release_manifest_path=paths["release_manifest"],
                workspace_root=workspace_root,
            )
        return _finish(
            telemetry,
            paths,
            ReleaseResult(0, destination, "final_readiness", "final readiness passed"),
        )
    except Exception:
        telemetry.finish("operational_error")
        telemetry.write(paths["release_telemetry"])
        raise


def _landing_paths(destination: Path) -> dict[str, Path]:
    return {
        "preflight_readiness": destination / "preflight-readiness.json",
        "preflight_receipt": destination / "preflight-readiness-stage-receipt.json",
        "release_manifest": destination / "release-manifest.json",
        "final_readiness": destination / "final-readiness.json",
        "final_receipt": destination / "final-readiness-stage-receipt.json",
        "release_telemetry": destination / "release-telemetry.json",
    }


def _finish(
    telemetry: ReadinessTelemetry,
    paths: dict[str, Path],
    result: ReleaseResult,
) -> ReleaseResult:
    telemetry.finish("passed" if result.exit_code == 0 else "blocked")
    telemetry.write(paths["release_telemetry"])
    return result


def _workspace_root(value: str | Path) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except OSError as error:
        raise ReleaseInvocationError(f"workspace_root is unavailable: {error}") from error
    if not root.is_dir():
        raise ReleaseInvocationError("workspace_root must be a directory")
    return root


def _new_output_dir(value: str | Path, *, workspace_root: Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    destination = candidate.resolve(strict=False)
    try:
        destination.relative_to(workspace_root)
    except ValueError as error:
        raise ReleaseInvocationError("output_dir must stay inside the workspace") from error
    if destination.exists():
        raise ReleaseInvocationError("output_dir must not already exist")
    destination.mkdir(parents=True)
    return destination


def _required_run_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseInvocationError("run_id is required")
    return value.strip()


__all__ = ["ReleaseInvocationError", "ReleaseResult", "run_artifact_release"]
