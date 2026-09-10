"""Publish-readiness runtime policy responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _load_runtime_bom(
    assembly_bom: str | None,
    *,
    workspace_root: str | Path,
) -> Mapping[str, Any] | None:
    if not assembly_bom:
        return None
    try:
        source = _resolve_workspace_input(
            assembly_bom, workspace_root=workspace_root, field="assembly_bom"
        )
        payload = load_json_object_snapshot(source, field="assembly BOM").payload
    except ValueError:
        return None
    return payload if isinstance(payload, Mapping) else None


def _artifact_path_resolver(
    artifacts: Mapping[str, Any],
    *,
    workspace_root: str | Path,
):
    root = Path(workspace_root).resolve()

    def resolve(label: str) -> str | None:
        row = artifacts.get(label)
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            return None
        try:
            return str(resolve_artifact(row["path"], workspace_root=root))
        except ValueError:
            return None

    return resolve


def _runtime_scoring_metadata(editorial_plan_path: str | None) -> Dict[str, Any]:
    if not editorial_plan_path:
        return {}
    try:
        plan = load_json_object_snapshot(
            editorial_plan_path, field="editorial plan"
        ).payload
    except ValueError:
        return {}
    if not isinstance(plan, Mapping):
        return {}
    meta = plan.get("meta")
    metadata = {
        key: meta.get(key)
        for key in (
            "meta_title", "meta_description", "primary_keyword", "secondary_keywords"
        )
    } if isinstance(meta, Mapping) else {}
    metadata["seo_guidelines"] = editorial_plan_guard.internal_link_guidelines_from_plan(plan)
    return metadata


def _bom_runtime_policy(
    assembly_bom: str | None,
    *,
    workspace_root: str | Path,
) -> Dict[str, Any]:
    default = {
        "visible_faq": True,
        "editorial_plan": None,
        "keyword_decision": None,
        "serp_evidence": None,
        "assembly_date": None,
        "run_id": None,
        "assembly_bom": None,
        "customer_proof_selector_evidence": None,
        "fred_authority_evidence": None,
        "faq_policy_status": "",
        "scoring_metadata": {},
        "paa_kwargs": {},
    }
    bom = _load_runtime_bom(assembly_bom, workspace_root=workspace_root)
    if bom is None:
        return default
    artifacts = bom.get("artifacts")
    paa_policy = bom.get("paa_policy")
    faq_policy = bom.get("faq_policy")
    schema_policy = bom.get("schema_policy")
    if (
        not isinstance(artifacts, Mapping)
        or not isinstance(paa_policy, Mapping)
        or not isinstance(faq_policy, Mapping)
    ):
        return default
    artifact_path = _artifact_path_resolver(artifacts, workspace_root=workspace_root)

    source_kind = paa_policy.get("source_kind")
    if source_kind == "brief_paa":
        paa_artifact = artifact_path("content_brief")
    elif source_kind == "user_csv":
        paa_artifact = artifact_path("user_paa_csv")
    else:
        paa_artifact = artifact_path("paa_artifact")
    editorial_plan_path = artifact_path("editorial_plan")
    scoring_metadata = _runtime_scoring_metadata(editorial_plan_path)
    return {
        "visible_faq": bool(
            isinstance(schema_policy, Mapping) and schema_policy.get("visible_faq") is True
        ),
        "editorial_plan": editorial_plan_path,
        "keyword_decision": artifact_path("keyword_decision"),
        "serp_evidence": artifact_path("serp_evidence"),
        "customer_proof_selector_evidence": artifact_path(
            "customer_proof_selector_evidence"
        ),
        "fred_authority_evidence": artifact_path("fred_authority_evidence"),
        "assembly_date": str(bom.get("assembly_date") or ""),
        "run_id": _canonical_bom_run_id(bom),
        "assembly_bom": bom,
        "faq_policy_status": str(faq_policy.get("status") or ""),
        "scoring_metadata": scoring_metadata,
        "paa_kwargs": {
            "workflow_mode": str(bom.get("workflow_mode") or ""),
            "paa_artifact": paa_artifact,
            "content_brief": artifact_path("content_brief"),
            "answersocrates_blocker": artifact_path("answersocrates_blocker"),
            "expected_query": str(paa_policy.get("query") or ""),
            "expected_collection_date": str(bom.get("assembly_date") or ""),
            "expected_run_id": _canonical_bom_run_id(bom),
        },
    }

def _no_fit_customer_proof_findings(
    article_content: str,
    *,
    runtime_policy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    evidence_path = runtime_policy.get("customer_proof_selector_evidence")
    if not isinstance(evidence_path, str) or not evidence_path:
        return []
    try:
        evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(evidence, Mapping):
        return []
    if evidence.get("selection_outcome") != NO_FIT_CUSTOMER_PROOF_OUTCOME:
        return []
    try:
        _, scan_content, body_start_line = split_frontmatter(article_content)
    except FrontmatterError:
        scan_content = article_content
        body_start_line = 1
    for line_number, line in enumerate(
        scan_content.splitlines(),
        start=body_start_line,
    ):
        lowered = line.lower()
        if not lowered.strip():
            continue
        has_customer_proof_marker = any(
            marker in lowered for marker in CUSTOMER_PROOF_NO_FIT_MARKERS
        )
        has_customer_metric_shape = (
            "%" in line
            and any(
                marker in lowered
                for marker in (
                    "customer",
                    "case study",
                    "review",
                    "testimonial",
                    "reduced",
                    "increased",
                    "saved",
                    "improved",
                )
            )
        )
        has_customer_quote_shape = (
            bool(CUSTOMER_PROOF_EXACT_QUOTE_RE.search(line))
            and bool(CUSTOMER_PROOF_QUOTE_CONTEXT_RE.search(lowered))
        )
        if (
            has_customer_proof_marker
            or has_customer_metric_shape
            or has_customer_quote_shape
        ):
            return [
                {
                    "rule_id": "customer_proof_no_fit_public_claim_present",
                    "severity": "error",
                    "line": line_number,
                    "column": 1,
                    "message": (
                        "The bound selector evidence selected no customer proof, "
                        "but the article contains customer proof-sensitive copy."
                    ),
                    "suggestion": (
                        "Remove the customer proof copy or rerun customer proof "
                        "selection and mining with approved bound evidence."
                    ),
                }
            ]
    return []

def _canonical_bom_run_id(bom: Mapping[str, Any]) -> str:
    workflow = bom.get("workflow")
    receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    if isinstance(receipts, list) and receipts and isinstance(receipts[0], Mapping):
        run_id = receipts[0].get("run_id")
        if isinstance(run_id, str) and run_id.strip():
            return run_id.strip()
    return ""


__all__ = ['_bom_runtime_policy', '_canonical_bom_run_id', '_no_fit_customer_proof_findings']
