"""Derivation responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _optional_artifact(path: str | Path | None, root: Path) -> dict[str, str] | None:
    return canonical_artifact(path, workspace_root=root) if path is not None else None


def _inactive_hindsight_policy(status: str, rationale: str) -> dict[str, Any]:
    return {
        "status": status,
        "public_claim_use": "prohibited",
        "claim_support_allowed": False,
        "evidence_required": False,
        "rationale": rationale,
    }


def _validated_hindsight_evidence(path: str | Path) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    evidence = _read_json_object(path, "hindsight_strategy_evidence")
    pack = _required_mapping(evidence.get("pack"), "hindsight_strategy_evidence.pack")
    receipt = _required_mapping(evidence.get("receipt"), "hindsight_strategy_evidence.receipt")
    sidecar = _required_mapping(evidence.get("sidecar"), "hindsight_strategy_evidence.sidecar")
    expected = {
        "pack": (pack.get("schema"), "simpro-internal-strategy-pack/v1", "Hindsight evidence pack schema is invalid"),
        "receipt": (receipt.get("schema"), "simpro-internal-strategy-receipt/v1", "Hindsight evidence receipt schema is invalid"),
        "sidecar": (sidecar.get("schema"), "simpro-content-validation-sidecar/v1", "Hindsight evidence sidecar schema is invalid"),
    }
    for actual, required, message in expected.values():
        if actual != required:
            raise ValueError(message)
    if sidecar.get("public_claim_use") != "prohibited":
        raise ValueError("Hindsight evidence sidecar must prohibit public claim use")
    if sidecar.get("claim_support_allowed") is not False:
        raise ValueError("Hindsight evidence sidecar cannot allow claim support")
    return pack, receipt


def _hindsight_strategy_policy(
    *,
    validation_sidecar_path: str | Path,
    hindsight_strategy_evidence_path: str | Path | None,
) -> dict[str, Any]:
    try:
        sidecar_content = Path(validation_sidecar_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"validation sidecar is unreadable for Hindsight policy: {error}") from error
    block = _hindsight_strategy_block(sidecar_content)
    if block is None:
        if hindsight_strategy_evidence_path is not None:
            raise ValueError(
                "hindsight_strategy_evidence_path requires Hindsight Strategy Selection in the validation sidecar"
            )
        return _inactive_hindsight_policy(
            "not_applicable",
            "No Hindsight Strategy Selection block was used for this article.",
        )
    status = str(block["fields"].get("status", "")).strip().casefold()
    if status not in {"internal_strategy_only", "not_applicable", "blocked"}:
        raise ValueError(
            "Hindsight Strategy Selection status must be internal_strategy_only, not_applicable, or blocked"
        )
    normalized = _normalize_hindsight_block_text(str(block["text"]))
    if status in {"not_applicable", "blocked"}:
        if hindsight_strategy_evidence_path is not None:
            raise ValueError(
                "hindsight_strategy_evidence_path is allowed only when Hindsight status is internal_strategy_only"
            )
        return _inactive_hindsight_policy(
            status,
            str(
                block["fields"].get("reason")
                or block["fields"].get("rationale")
                or "Hindsight internal strategy was not selected for public-copy support."
            ),
        )
    if hindsight_strategy_evidence_path is None:
        raise ValueError(
            "Hindsight internal_strategy_only selection requires hindsight_strategy_evidence_path"
        )
    for marker in (
        "public_claim_use: prohibited",
        "claim_support_allowed: false",
    ):
        if marker not in normalized:
            raise ValueError(
                f"Hindsight Strategy Selection is missing required boundary marker: {marker}"
            )
    pack, receipt = _validated_hindsight_evidence(hindsight_strategy_evidence_path)
    return {
        "status": "internal_strategy_only",
        "public_claim_use": "prohibited",
        "claim_support_allowed": False,
        "evidence_required": True,
        "evidence_schema": "simpro-internal-strategy-pack/v1",
        "receipt_schema": "simpro-internal-strategy-receipt/v1",
        "sidecar_schema": "simpro-content-validation-sidecar/v1",
        "pack_sha256": canonical_json_sha256(pack),
        "receipt_sha256": canonical_json_sha256(receipt),
    }

def _hindsight_strategy_block(content: str) -> dict[str, Any] | None:
    lines = content.splitlines()
    heading_re = re.compile(
        r"^\s*(?:#{1,6}\s+)?Hindsight Strategy Selection:?\s*$",
        re.IGNORECASE,
    )
    field_re = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")
    heading_line_re = re.compile(r"^\s*#{1,6}\s+\S")
    for index, line in enumerate(lines):
        if not heading_re.match(line.strip()):
            continue
        block_lines: list[str] = []
        fields: dict[str, str] = {}
        for block_line in lines[index + 1 :]:
            if heading_line_re.match(block_line):
                break
            block_lines.append(block_line)
            match = field_re.match(block_line)
            if match:
                key = re.sub(r"\s+", " ", match.group("key").strip().casefold())
                fields[key] = match.group("value").strip()
        return {"fields": fields, "text": "\n".join(block_lines)}
    return None

def _normalize_hindsight_block_text(value: str) -> str:
    normalized = value.casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*:\s*", ": ", normalized)
    return normalized

def _execution_evidence_from_prior_preflight(
    prior_preflight_readiness_path: str | Path | None,
    *,
    workspace_root: Path,
) -> dict[str, dict[str, str]]:
    if prior_preflight_readiness_path is None:
        raise blog_assembly_capabilities.CapabilityRegistryError(
            "optimized-tail workflow requires prior preflight readiness evidence"
        )
    try:
        readiness = _read_json_object(
            prior_preflight_readiness_path,
            "prior_preflight_readiness",
        )
        inputs = _required_mapping(
            readiness.get("input_hashes"),
            "prior_preflight_readiness.input_hashes",
        )
        prior_bom_row = _required_mapping(
            inputs.get("assembly_bom"),
            "prior_preflight_readiness.input_hashes.assembly_bom",
        )
        prior_bom_path = verify_artifact(
            prior_bom_row,
            workspace_root=workspace_root,
            field="prior_preflight_readiness.input_hashes.assembly_bom",
        )
        prior_bom = _read_json_object(prior_bom_path, "prior_preflight_bom")
        prior_artifacts = _required_mapping(
            prior_bom.get("artifacts"),
            "prior_preflight_bom.artifacts",
        )
        evidence = _required_mapping(
            prior_artifacts.get("execution_evidence"),
            "prior_preflight_bom.artifacts.execution_evidence",
        )
        copied: dict[str, dict[str, str]] = {}
        for label, row in evidence.items():
            if not isinstance(label, str):
                raise ValueError("execution evidence labels must be strings")
            copied[label] = dict(
                _required_mapping(
                    row,
                    f"prior_preflight_bom.artifacts.execution_evidence.{label}",
                )
            )
        return copied
    except ValueError as error:
        raise blog_assembly_capabilities.CapabilityRegistryError(str(error)) from error


__all__ = ['_execution_evidence_from_prior_preflight', '_hindsight_strategy_block', '_hindsight_strategy_policy', '_normalize_hindsight_block_text', '_optional_artifact']
