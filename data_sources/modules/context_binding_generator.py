"""Generate and install machine-owned blog context sidecar bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .context_binding_guard import (
        build_binding,
        normalize_public_body,
        normalize_public_text,
        render_generated_blocks,
        validate_claim_map,
        validate_request_article,
    )
    from .simpro_vault_client import RECOVERY_HINTS, SimproVaultClient, VaultClientError
except ImportError:  # pragma: no cover - supports direct script execution.
    from context_binding_guard import (
        build_binding,
        normalize_public_body,
        normalize_public_text,
        render_generated_blocks,
        validate_claim_map,
        validate_request_article,
    )
    from simpro_vault_client import RECOVERY_HINTS, SimproVaultClient, VaultClientError


GENERATED_BLOCK_RE = re.compile(
    r"(?:^##\s+(?:Context Binding|Context Claim Use Map)\s*$\s*```json\s*.*?\s*```\s*)+",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)


class ContextBindingGenerationError(RuntimeError):
    """Stable recoverable generation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.recovery_hint = RECOVERY_HINTS.get(
            code,
            "Refresh vault_status, rebuild the context artifacts, and retry binding generation.",
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
) -> dict[str, Any]:
    """Live-validate artifacts, derive exact claim uses, and update a sidecar."""
    resolved = _resolve_distinct_paths(
        article=article_path,
        request=request_path,
        pack=pack_path,
        receipt=receipt_path,
        sidecar=sidecar_path,
    )
    article = resolved["article"]
    request_path = resolved["request"]
    pack_path = resolved["pack"]
    receipt_path = resolved["receipt"]
    sidecar = resolved["sidecar"]
    request = _read_object(request_path)
    pack = _read_object(pack_path)
    receipt = _read_object(receipt_path)
    try:
        article_content = article.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ContextBindingGenerationError(
            "binding_input_invalid",
            f"Article input is invalid: {error}",
        ) from error
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
    generated = render_generated_blocks(binding, claim_map).strip()
    try:
        existing = sidecar.read_text(encoding="utf-8") if sidecar.exists() else ""
        retained = GENERATED_BLOCK_RE.sub("", existing).strip()
        updated = (retained + "\n\n" if retained else "") + generated + "\n"
        _atomic_write_text(sidecar, updated)
    except (OSError, UnicodeError) as error:
        raise ContextBindingGenerationError(
            "sidecar_write_failed",
            f"Context sidecar could not be updated: {error}",
        ) from error
    return {"binding": binding, "claim_use_map": claim_map, "sidecar": str(sidecar)}


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
            verbatim = evidence.get("verbatim_evidence")
            public_text = verbatim.get("text") if isinstance(verbatim, dict) else None
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


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContextBindingGenerationError("context_artifact_invalid", f"Invalid context artifact {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContextBindingGenerationError("context_artifact_invalid", f"Context artifact must be an object: {path}")
    return value


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


def _repo_context(value: str) -> dict[str, str]:
    path, separator, role = value.partition("=")
    if not separator or not path.strip() or not role.strip():
        raise argparse.ArgumentTypeError("--repo-context requires context/path=role")
    return {"path": path.strip(), "role": role.strip()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the machine-owned context binding and claim-use map.")
    parser.add_argument("article")
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--context-request", required=True)
    parser.add_argument("--context-pack", required=True)
    parser.add_argument("--context-receipt", required=True)
    parser.add_argument("--repo-context", action="append", default=[], type=_repo_context)
    parser.add_argument("--vault-root")
    args = parser.parse_args(argv)
    try:
        result = generate_and_install(
            args.article, args.context_request, args.context_pack, args.context_receipt,
            args.proof_sidecar, repo_context=args.repo_context, vault_root=args.vault_root,
        )
    except ContextBindingGenerationError as error:
        print(json.dumps({"ok": False, "error": {"code": error.code, "message": str(error)}, "recovery_hint": error.recovery_hint}, indent=2))
        return 1
    except Exception:
        print(json.dumps({"ok": False, "error": {"code": "binding_generation_internal_error", "message": "Context binding generation failed"}, "recovery_hint": "Run vault_status, inspect the supplied artifact paths, and retry without hand-editing generated blocks."}, indent=2))
        return 1
    print(json.dumps({"ok": True, "result": result}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
