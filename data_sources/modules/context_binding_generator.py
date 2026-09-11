"""Generate and install machine-owned blog context sidecar bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import uuid4

try:
    from .context_binding_guard import (
        build_binding,
        normalize_public_body,
        normalize_public_text,
        render_generated_blocks,
        requires_context,
        validate_claim_map,
        validate_request_article,
    )
    from .simpro_vault_client import RECOVERY_HINTS, SimproVaultClient, VaultClientError
    from .blog_assembly_stage_receipt import (
        StageReceiptError,
        build_stage_receipt,
        load_stage_receipt,
        stage_evidence_path,
        write_stage_evidence,
        write_stage_receipt,
    )
    from .blog_assembly_contract import (
        load_json_object_snapshot,
        normalized_text_sha256,
        validate_governance_output_path,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from context_binding_guard import (
        build_binding,
        normalize_public_body,
        normalize_public_text,
        render_generated_blocks,
        requires_context,
        validate_claim_map,
        validate_request_article,
    )
    from simpro_vault_client import RECOVERY_HINTS, SimproVaultClient, VaultClientError
    from blog_assembly_stage_receipt import (
        StageReceiptError,
        build_stage_receipt,
        load_stage_receipt,
        stage_evidence_path,
        write_stage_evidence,
        write_stage_receipt,
    )
    from blog_assembly_contract import (
        load_json_object_snapshot,
        normalized_text_sha256,
        validate_governance_output_path,
    )


GENERATED_BLOCK_RE = re.compile(
    r"(?:^##\s+(?:Context Binding|Context Claim Use Map)\s*$\s*```json\s*.*?\s*```\s*)+",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
NOT_APPLICABLE_BINDING_SCHEMA = "seomachine-context-binding-not-applicable/v1"
GENERATOR_RECOVERY_HINTS = {
    "context_artifact_set_incomplete": (
        "Provide all three connector artifacts: context request, pack, and receipt."
    ),
    "context_binding_mode_conflict": (
        "Choose either connector artifacts or explicit not-applicable mode, not both."
    ),
    "context_binding_required": (
        "Use connector mode and provide a validated context request, pack, and receipt."
    ),
    "context_not_applicable_reason_missing": (
        "Provide a specific non-empty reason for the connector not-applicable decision."
    ),
    "stage_receipt_output_required": (
        "Provide a stage receipt output path with --stage-receipt-output."
    ),
}


class ContextBindingGenerationError(RuntimeError):
    """Stable recoverable generation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.recovery_hint = GENERATOR_RECOVERY_HINTS.get(
            code,
            RECOVERY_HINTS.get(
                code,
                "Refresh vault_status, rebuild the context artifacts, and retry binding generation.",
            ),
        )


def generate_and_install(
    article_path: str | Path,
    request_path: str | Path,
    pack_path: str | Path,
    receipt_path: str | Path,
    sidecar_path: str | Path,
    *,
    repo_context: Sequence[Mapping[str, str]],
    vault_root: str | Path | None = None,
    client: Any | None = None,
    stage_receipt_output: str | Path | None = None,
    run_id: str | None = None,
    previous_receipt: str | Path | None = None,
    stage: str = "context_binding",
) -> dict[str, Any]:
    """Live-validate artifacts, derive exact claim uses, and update a sidecar."""
    if stage not in {"context_binding", "post_optimization_context_binding"}:
        raise StageReceiptError(
            "stage_receipt_stage_invalid",
            "context binding stage must be context_binding or post_optimization_context_binding",
        )
    path_inputs: dict[str, str | Path] = {
        "article": article_path,
        "request": request_path,
        "pack": pack_path,
        "receipt": receipt_path,
        "sidecar": sidecar_path,
    }
    if stage_receipt_output is not None:
        path_inputs["stage_receipt"] = stage_receipt_output
        path_inputs["stage_evidence"] = stage_evidence_path(stage_receipt_output)
    if previous_receipt is not None:
        if stage_receipt_output is None:
            raise StageReceiptError(
                "stage_receipt_previous_without_output",
                "previous_receipt requires stage_receipt_output",
            )
        path_inputs["previous_receipt"] = previous_receipt
    resolved = _resolve_distinct_paths(**path_inputs)
    started_at = datetime.now(timezone.utc) if stage_receipt_output is not None else None
    resolved_stage_receipt = resolved.get("stage_receipt")
    resolved_previous_receipt = resolved.get("previous_receipt")
    resolved_run_id = ""
    previous_hash = ""
    try:
        article_bytes = resolved["article"].read_bytes()
        article_content = article_bytes.decode("utf-8", errors="strict")
        request_snapshot = load_json_object_snapshot(
            resolved["request"], field="context request"
        )
        pack_snapshot = load_json_object_snapshot(
            resolved["pack"], field="context pack"
        )
        receipt_snapshot = load_json_object_snapshot(
            resolved["receipt"], field="context receipt"
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise ContextBindingGenerationError(
            "binding_input_invalid",
            f"Context binding inputs are invalid: {error}",
        ) from error
    receipt_input_hashes = {
        "article": hashlib.sha256(article_bytes).hexdigest(),
        "context_request": request_snapshot.sha256,
        "context_pack": pack_snapshot.sha256,
        "context_receipt": receipt_snapshot.sha256,
    }
    if resolved_stage_receipt is not None:
        resolved_run_id, previous_hash = _receipt_identity(
            run_id,
            resolved_previous_receipt,
            started_at=started_at,
            expected_previous_stage=_context_predecessor_stage(stage),
            article_hash=receipt_input_hashes["article"],
            previous_required=True,
        )
        _preflight_receipt_destination(resolved_stage_receipt)
    article = resolved["article"]
    request_path = resolved["request"]
    pack_path = resolved["pack"]
    receipt_path = resolved["receipt"]
    sidecar = resolved["sidecar"]
    request = request_snapshot.payload
    pack = pack_snapshot.payload
    receipt = receipt_snapshot.payload
    request_findings = validate_request_article(
        request,
        article_content,
        article_path=article,
    )
    if request_findings:
        first = request_findings[0]
        raise ContextBindingGenerationError(first["rule_id"], first["message"])
    try:
        validator = client or SimproVaultClient(vault_root=vault_root)
        validation = validator.validate_context(request, pack, receipt)
    except VaultClientError as error:
        raise ContextBindingGenerationError(error.code, str(error)) from error
    if not isinstance(validation, dict) or validation.get("valid") is not True or validation.get("errors"):
        raise ContextBindingGenerationError(
            "context_validation_failed",
            "The shared connector did not validate the request, pack, and receipt.",
        )
    claim_map = _derive_claim_map(article_content, pack, receipt)
    claim_findings = validate_claim_map(article_content, pack, receipt, claim_map)
    if claim_findings:
        first = claim_findings[0]
        raise ContextBindingGenerationError(first["rule_id"], first["message"])
    try:
        binding = build_binding(
            article,
            request_path,
            pack_path,
            receipt_path,
            repo_context=repo_context,
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise ContextBindingGenerationError(
            "binding_input_invalid",
            f"Context binding inputs are invalid: {error}",
        ) from error
    current_hashes = {
        "article": _file_sha256(article),
        "context_request": _file_sha256(request_path),
        "context_pack": _file_sha256(pack_path),
        "context_receipt": _file_sha256(receipt_path),
    }
    if current_hashes != receipt_input_hashes:
        raise ContextBindingGenerationError(
            "binding_input_changed",
            "Context binding inputs changed during generation.",
        )
    generated = render_generated_blocks(binding, claim_map).strip()
    try:
        sidecar_existed = sidecar.is_file()
        previous_sidecar = sidecar.read_bytes() if sidecar_existed else None
        existing = previous_sidecar.decode("utf-8") if previous_sidecar is not None else ""
        retained = GENERATED_BLOCK_RE.sub("", existing).strip()
        updated = (retained + "\n\n" if retained else "") + generated + "\n"
        _atomic_write_text(sidecar, updated)
    except (OSError, UnicodeError) as error:
        raise ContextBindingGenerationError(
            "sidecar_write_failed",
            f"Context sidecar could not be updated: {error}",
        ) from error
    stage_receipt: dict[str, Any] | None = None
    if resolved_stage_receipt is not None:
        evidence_payload = json.dumps(
            {"binding": binding, "claim_use_map": claim_map},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        context_evidence_hash = hashlib.sha256(evidence_payload).hexdigest()
        evidence_path = stage_evidence_path(resolved_stage_receipt)
        evidence_written = False
        try:
            _, evidence_artifact_hash = write_stage_evidence(
                resolved_stage_receipt,
                evidence_hashes={"context_binding": context_evidence_hash},
                payload={"binding": binding, "claim_use_map": claim_map},
            )
            evidence_written = True
            stage_receipt = build_stage_receipt(
                run_id=resolved_run_id,
                stage=stage,
                tool_name="context_binding_generator",
                tool_version="1.0.0",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                mutation=False,
                input_artifact_hashes=receipt_input_hashes,
                output_artifact_hashes={
                    "article": _file_sha256(article),
                    "validation_sidecar": _file_sha256(sidecar),
                    "stage_evidence": evidence_artifact_hash,
                },
                evidence_hashes={
                    "context_binding": context_evidence_hash,
                },
                previous_receipt_hash=previous_hash,
            )
            write_stage_receipt(resolved_stage_receipt, stage_receipt)
        except Exception:
            if evidence_written:
                evidence_path.unlink(missing_ok=True)
            _restore_file(
                sidecar,
                existed=sidecar_existed,
                previous_bytes=previous_sidecar,
            )
            raise
    result: dict[str, Any] = {
        "binding": binding,
        "claim_use_map": claim_map,
        "sidecar": str(sidecar),
    }
    if resolved_stage_receipt is not None and stage_receipt is not None:
        result["stage_receipt"] = stage_receipt
    return result


def generate_not_applicable_receipt(
    article_path: str | Path,
    sidecar_path: str | Path,
    reason: str,
    *,
    stage_receipt_output: str | Path | None,
    run_id: str | None = None,
    previous_receipt: str | Path | None = None,
    stage: str = "context_binding", workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    """Attest that Context Binding is inapplicable without mutating inputs."""
    if stage not in {"context_binding", "post_optimization_context_binding"}:
        raise StageReceiptError(
            "stage_receipt_stage_invalid",
            "context binding stage must be context_binding or post_optimization_context_binding",
        )
    normalized_reason = reason.strip() if isinstance(reason, str) else ""
    if not normalized_reason:
        raise ContextBindingGenerationError(
            "context_not_applicable_reason_missing",
            "Non-connector Context Binding requires a non-empty explicit reason.",
        )
    if stage_receipt_output is None:
        raise ContextBindingGenerationError(
            "stage_receipt_output_required",
            "Non-connector Context Binding requires a stage receipt output path.",
        )
    started_at = datetime.now(timezone.utc)
    path_inputs: dict[str, str | Path] = {
        "article": article_path,
        "sidecar": sidecar_path,
        "stage_receipt": stage_receipt_output,
        "stage_evidence": stage_evidence_path(stage_receipt_output),
    }
    if previous_receipt is not None:
        path_inputs["previous_receipt"] = previous_receipt
    resolved = _resolve_distinct_paths(**path_inputs)
    try:
        article_bytes = resolved["article"].read_bytes()
        article_content = article_bytes.decode("utf-8")
        sidecar_bytes = resolved["sidecar"].read_bytes()
        sidecar_bytes.decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise ContextBindingGenerationError(
            "binding_input_invalid",
            f"Non-connector Context Binding inputs are invalid: {error}",
        ) from error
    if requires_context(article_content):
        raise ContextBindingGenerationError(
            "context_binding_required",
            "The article contains Simpro connector signals and cannot be marked not applicable.",
        )

    article_hash = hashlib.sha256(article_bytes).hexdigest()
    sidecar_hash = hashlib.sha256(sidecar_bytes).hexdigest()
    resolved_run_id, previous_hash = _receipt_identity(
        run_id,
        resolved.get("previous_receipt"),
        started_at=started_at,
        expected_previous_stage=_context_predecessor_stage(stage),
        article_hash=article_hash,
        previous_required=True, workspace_root=workspace_root,
    )
    receipt_path = resolved["stage_receipt"]
    _preflight_receipt_destination(receipt_path)
    evidence = {
        "article_sha256": article_hash,
        "reason": normalized_reason,
        "schema": NOT_APPLICABLE_BINDING_SCHEMA,
        "status": "not_applicable",
        "validation_sidecar_sha256": sidecar_hash,
    }
    evidence_payload = json.dumps(
        evidence,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    context_evidence_hash = hashlib.sha256(evidence_payload).hexdigest()
    reason_hash = normalized_text_sha256(
        normalized_reason,
        field="not_applicable_reason",
    )
    evidence_path, evidence_artifact_hash = write_stage_evidence(
        receipt_path,
        evidence_hashes={
            "context_binding": context_evidence_hash,
            "not_applicable_reason": reason_hash,
        },
        payload=evidence,
    )
    try:
        stage_receipt = build_stage_receipt(
            run_id=resolved_run_id,
            stage=stage,
            tool_name="context_binding_generator",
            tool_version="1.0.0",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            mutation=False,
            input_artifact_hashes={
                "article": article_hash,
                "validation_sidecar": sidecar_hash,
            },
            output_artifact_hashes={
                "article": article_hash,
                "validation_sidecar": sidecar_hash,
                "stage_evidence": evidence_artifact_hash,
            },
            evidence_hashes={
                "context_binding": context_evidence_hash,
                "not_applicable_reason": reason_hash,
            },
            previous_receipt_hash=previous_hash, workspace_root=workspace_root,
        )
        write_stage_receipt(receipt_path, stage_receipt, workspace_root=workspace_root)
    except Exception:
        evidence_path.unlink(missing_ok=True)
        raise
    return {
        "connector_binding": {
            "status": "not_applicable",
            "reason": normalized_reason,
        },
        "sidecar": str(resolved["sidecar"]),
        "stage_receipt": stage_receipt,
    }


def _file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _receipt_identity(
    run_id: str | None,
    previous_receipt: str | Path | None,
    *,
    started_at: datetime | None = None,
    expected_previous_stage: str | None = None,
    article_hash: str | None = None,
    previous_required: bool = False, workspace_root: str | Path | None = None,
) -> tuple[str, str]:
    if previous_receipt is None:
        if previous_required:
            raise StageReceiptError(
                "stage_receipt_previous_required",
                "Context Binding requires the immediately preceding scrub receipt.",
            )
        return run_id or str(uuid4()), ""
    previous = load_stage_receipt(previous_receipt, workspace_root=workspace_root)
    previous_run_id = str(previous["run_id"])
    if run_id is not None and run_id != previous_run_id:
        raise StageReceiptError(
            "stage_receipt_run_id_mismatch",
            "run_id must match the previous receipt",
        )
    if started_at is not None:
        previous_completed = datetime.fromisoformat(
            str(previous["completed_at"]).replace("Z", "+00:00")
        )
        if started_at <= previous_completed:
            raise StageReceiptError(
                "stage_receipt_timestamps_not_monotonic",
                "Context Binding must start after the previous receipt completed.",
            )
    if (
        expected_previous_stage is not None
        and previous.get("stage") != expected_previous_stage
    ):
        raise StageReceiptError(
            "stage_receipt_predecessor_stage_invalid",
            f"Context Binding requires {expected_previous_stage} as its predecessor.",
        )
    if article_hash is not None:
        outputs = previous.get("output_artifact_hashes")
        previous_article_hash = (
            outputs.get("article") if isinstance(outputs, Mapping) else None
        )
        if previous_article_hash != article_hash:
            raise StageReceiptError(
                "stage_receipt_article_chain_broken",
                "The predecessor receipt does not bind the current article hash.",
            )
    return run_id or previous_run_id, str(previous["receipt_hash"])


def _context_predecessor_stage(stage: str) -> str:
    return (
        "post_optimization_scrub"
        if stage == "post_optimization_context_binding"
        else "scrub"
    )


def _derive_claim_map(
    article_content: str,
    pack: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> list[dict[str, str]]:
    sections = pack.get("sections")
    evidence_rows = sections.get("Approved Claim Evidence") if isinstance(sections, dict) else None
    decisions = receipt.get("claim_decisions")
    if not isinstance(evidence_rows, list) or not isinstance(decisions, list):
        raise ContextBindingGenerationError("claim_binding_input_invalid", "Claim evidence and decisions must be arrays.")
    evidence_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in evidence_rows:
        if isinstance(row, dict) and isinstance(row.get("claim_id"), str):
            evidence_by_id.setdefault(row["claim_id"], []).append(row)
    normalized_article = normalize_public_body(article_content)
    claim_map: list[dict[str, str]] = []
    for decision in decisions:
        if not isinstance(decision, dict) or decision.get("approved") is not True:
            raise ContextBindingGenerationError("claim_decision_invalid", "Every receipt claim decision must be approved and structured.")
        claim_id = str(decision.get("claim_id", "")).strip()
        matches = evidence_by_id.get(claim_id, [])
        if len(matches) != 1:
            raise ContextBindingGenerationError("claim_evidence_ambiguous", f"Claim {claim_id} must resolve to exactly one evidence row.")
        evidence = matches[0]
        use_mode = str(decision.get("use_mode", "")).strip()
        if use_mode == "exact_quote":
            public_text = _exact_quote_public_text(article_content, evidence)
        else:
            public_text = evidence.get("assertion")
        if not isinstance(public_text, str) or not public_text.strip():
            raise ContextBindingGenerationError("claim_passage_unbound", f"Claim {claim_id} has no source-bound public passage for {use_mode}.")
        normalized = normalize_public_text(public_text)
        if normalized_article.count(normalized) != 1:
            raise ContextBindingGenerationError("claim_passage_unbound", f"Claim {claim_id} passage must occur exactly once in the final article.")
        public_url = str(evidence.get("public_url", "")).strip()
        if not public_url.startswith(("http://", "https://")):
            raise ContextBindingGenerationError("claim_public_url_invalid", f"Claim {claim_id} has no public evidence URL.")
        claim_map.append(
            {
                "claim_id": claim_id,
                "use_mode": use_mode,
                "brand_scope": str(decision.get("brand_scope", "")).strip(),
                "public_url": public_url,
                "public_text": normalized,
                "public_text_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            }
        )
    return claim_map


def _exact_quote_public_text(
    article_content: str,
    evidence: Mapping[str, Any],
) -> str | None:
    """Return the exact quote passage that is source-visible and public-used.

    Some approved review claims store the full source-visible field while policy
    allows a shorter attributed snippet. Bind the full passage when it appears
    in the article; otherwise bind the longest quoted article excerpt that is
    an exact substring of the approved source-visible text.
    """
    verbatim = evidence.get("verbatim_evidence")
    source_text = verbatim.get("text") if isinstance(verbatim, dict) else None
    if not isinstance(source_text, str) or not source_text.strip():
        return None
    normalized_source = normalize_public_text(source_text)
    normalized_article = normalize_public_body(article_content)
    if normalized_article.count(normalized_source) == 1:
        return source_text
    quoted_passages = re.findall(r'"([^"]+)"', normalize_public_text(article_content))
    candidates = [
        passage
        for passage in quoted_passages
        if passage.strip()
        and normalize_public_text(passage) in normalized_source
        and normalized_article.count(normalize_public_text(passage)) == 1
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda passage: (len(normalize_public_text(passage)), passage))


def _read_object(path: Path) -> dict[str, Any]:
    try:
        return load_json_object_snapshot(path, field="context artifact").payload
    except ValueError as error:
        raise ContextBindingGenerationError(
            "context_artifact_invalid", f"Invalid context artifact {path}: {error}"
        ) from error


def _resolve_distinct_paths(**paths: str | Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    identities: dict[str, str] = {}
    try:
        for name, raw_path in paths.items():
            path = Path(raw_path).resolve(strict=False)
            identity = os.path.normcase(str(path))
            if identity in identities:
                raise ContextBindingGenerationError(
                    "context_artifact_path_collision",
                    f"Context artifact paths must be distinct: {identities[identity]} and {name} resolve to {path}.",
                )
            identities[identity] = name
            resolved[name] = path
    except ContextBindingGenerationError:
        raise
    except (OSError, RuntimeError, ValueError) as error:
        raise ContextBindingGenerationError(
            "context_artifact_path_invalid",
            f"Context artifact path could not be resolved: {error}",
        ) from error
    return resolved


def _atomic_write_text(path: Path, content: str) -> None:
    path = validate_governance_output_path(path)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _preflight_receipt_destination(path: Path) -> None:
    """Verify the detached receipt destination before changing the sidecar."""
    probe: Path | None = None
    try:
        if path.exists() and not path.is_file():
            raise OSError("receipt destination is not a file")
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".preflight",
            delete=False,
        ) as handle:
            probe = Path(handle.name)
            handle.write("{}\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        raise ContextBindingGenerationError(
            "stage_receipt_destination_invalid",
            f"Stage receipt destination is not writable: {error}",
        ) from error
    finally:
        if probe is not None:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass


def _restore_file(
    path: Path,
    *,
    existed: bool,
    previous_bytes: bytes | None,
) -> None:
    if not existed:
        path.unlink(missing_ok=True)
        return
    if previous_bytes is None:  # pragma: no cover - invariant.
        raise RuntimeError("rollback bytes are unavailable")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".rollback.tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(previous_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _repo_context(value: str) -> dict[str, str]:
    path, separator, role = value.partition("=")
    if not separator or not path.strip() or not role.strip():
        raise argparse.ArgumentTypeError("--repo-context requires context/path=role")
    return {"path": path.strip(), "role": role.strip()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the machine-owned context binding and claim-use map.")
    parser.add_argument("article")
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--context-request")
    parser.add_argument("--context-pack")
    parser.add_argument("--context-receipt")
    parser.add_argument("--not-applicable-reason")
    parser.add_argument("--repo-context", action="append", default=[], type=_repo_context)
    parser.add_argument("--vault-root")
    parser.add_argument("--stage-receipt-output")
    parser.add_argument("--run-id")
    parser.add_argument("--previous-receipt")
    parser.add_argument(
        "--stage",
        choices=("context_binding", "post_optimization_context_binding"),
        default="context_binding",
    )
    args = parser.parse_args(argv)
    try:
        connector_artifacts = (
            args.context_request,
            args.context_pack,
            args.context_receipt,
        )
        if args.not_applicable_reason is not None:
            if any(value is not None for value in connector_artifacts):
                raise ContextBindingGenerationError(
                    "context_binding_mode_conflict",
                    "Not-applicable mode cannot include connector request, pack, or receipt arguments.",
                )
            if args.repo_context or args.vault_root:
                raise ContextBindingGenerationError(
                    "context_binding_mode_conflict",
                    "Not-applicable mode cannot include connector-only repository or vault arguments.",
                )
            result = generate_not_applicable_receipt(
                args.article,
                args.proof_sidecar,
                args.not_applicable_reason,
                stage_receipt_output=args.stage_receipt_output,
                run_id=args.run_id,
                previous_receipt=args.previous_receipt,
                stage=args.stage,
            )
        else:
            if not all(value is not None for value in connector_artifacts):
                raise ContextBindingGenerationError(
                    "context_artifact_set_incomplete",
                    "Connector mode requires context request, pack, and receipt arguments together.",
                )
            result = generate_and_install(
                args.article,
                args.context_request,
                args.context_pack,
                args.context_receipt,
                args.proof_sidecar,
                repo_context=args.repo_context,
                vault_root=args.vault_root,
                stage_receipt_output=args.stage_receipt_output,
                run_id=args.run_id,
                previous_receipt=args.previous_receipt,
                stage=args.stage,
            )
    except ContextBindingGenerationError as error:
        print(json.dumps({"ok": False, "error": {"code": error.code, "message": str(error)}, "recovery_hint": error.recovery_hint}, indent=2))
        return 1
    except StageReceiptError as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": {"code": error.code, "message": str(error)},
                    "recovery_hint": (
                        "Use the current run_id and previous receipt, then rerun "
                        "Context Binding without editing receipt JSON."
                    ),
                },
                indent=2,
            )
        )
        return 1
    except Exception:
        print(json.dumps({"ok": False, "error": {"code": "binding_generation_internal_error", "message": "Context binding generation failed"}, "recovery_hint": "Run vault_status, inspect the supplied artifact paths, and retry without hand-editing generated blocks."}, indent=2))
        return 1
    print(json.dumps({"ok": True, "result": result}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
