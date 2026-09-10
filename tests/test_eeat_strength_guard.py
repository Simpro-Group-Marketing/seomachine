from __future__ import annotations

import json
from pathlib import Path

from data_sources.modules import eeat_strength_guard


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _article(path: Path, *, title: str = "7 Best CRM Platforms", author: str | None = None, body: str | None = None) -> Path:
    lines = [
        "---",
        "artifact_type: blog",
        "brand: Simpro",
        f"title: {title}",
        "objective: Help contractors compare CRM software.",
        "audience: Field service leaders",
        "region: US",
        "last_updated: 2026-08-25",
    ]
    if author:
        lines.append(f"author: {author}")
    lines.extend(
        [
            "schema_notes:",
            "  - BlogPosting",
            "  - BreadcrumbList",
            "  - ImageObject for the featured image or logo",
            "  - Organization as publisher reference only, not a separate full schema block",
            "---",
            f"# {title}",
            "",
            body or "Compare platforms by workflow fit, pricing model and buyer needs.",
        ]
    )
    return _write(path, "\n".join(lines) + "\n")


def _editorial_plan(path: Path, *, commercial: bool = True) -> Path:
    payload = {
        "schema": "simpro-blog-editorial-plan/v1",
        "topic": "CRM for electricians" if commercial else "Electrical scheduling guide",
        "meta": {
            "primary_keyword": "best crm for electricians" if commercial else "electrical scheduling guide",
            "title_options": ["7 Best CRM Platforms"] if commercial else ["Electrical scheduling guide"],
        },
        "reader_contract": {
            "funnel_stage": "mofu" if commercial else "tofu",
            "decision_task_helped": (
                "Compare CRM platforms and build a shortlist."
                if commercial
                else "Plan scheduling work."
            ),
        },
        "sections": [
            {
                "type": "body_comparison" if commercial else "body_how_to",
                "heading": "Best CRM Platforms" if commercial else "Scheduling guide",
                "cta": "commercial_comparison" if commercial else None,
            }
        ],
        "engagement_map": {
            "ctas": {"commercial_comparison": 1} if commercial else {},
        },
        "serp_strategy": {
            "content_type": {
                "selected": "comparison list" if commercial else "guide",
            },
            "serp_structure": {
                "comparison table": "included",
            } if commercial else {},
        },
        "query_ownership": {
            "rationale": (
                "The page serves commercial-investigation comparison intent."
                if commercial
                else "The page serves educational planning intent."
            )
        },
    }
    return _json(path, payload)


def _no_fit_selector(path: Path) -> Path:
    reason = "No customer proof selected because public copy must omit customer proof."
    return _json(
        path,
        {
            "schema": "simpro-customer-proof-selector-evidence/v1",
            "selection_outcome": "no_fit_customer_proof",
            "roles": [
                {
                    "role": role,
                    "candidate_ids": [],
                    "claim_ids": [],
                    "selected_id": "none",
                    "no_fit_reason": reason,
                }
                for role in ("metric", "quote", "theme", "experience_story")
            ],
        },
    )


def _selected_selector(path: Path) -> Path:
    return _json(
        path,
        {
            "schema": "simpro-customer-proof-selector-evidence/v1",
            "roles": [
                {
                    "role": "experience_story",
                    "candidate_ids": ["proof-123"],
                    "claim_ids": ["claim-123"],
                    "selected_id": "proof-123",
                }
            ],
        },
    )


def _rejected_selector(path: Path, *, complete: bool = True) -> Path:
    candidates = ["proof-123", "proof-456"]
    rejected = {
        "proof-123": "This proof addresses estimating speed rather than the article's AI economics decision framework.",
    }
    if complete:
        rejected["proof-456"] = (
            "This proof addresses invoicing throughput rather than the article's AI economics decision framework."
        )
    return _json(
        path,
        {
            "schema": "simpro-customer-proof-selector-evidence/v1",
            "selection_outcome": "customer_proof_candidates_available",
            "inputs": {"rejected_overrides": {"metric": rejected}},
            "roles": [
                {
                    "role": "metric",
                    "candidate_ids": candidates,
                    "claim_ids": ["claim-123", "claim-456"],
                    "selected_id": "none",
                }
            ],
        },
    )


def _fred(path: Path, *, selected: bool = False) -> Path:
    selected_value = "FVMI-0003" if selected else "none"
    return _write(
        path,
        "\n".join(
            [
                "## Fred Voccola Authority Selection",
                "- Evaluation status: completed",
                f"- Selected: [{selected_value}]",
                "- Evidence status: receipt_approved" if selected else "- Evidence status: not applicable",
            ]
        )
        + "\n",
    )


def _fallback_sidecar(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "## Customer Proof Slate",
                "- Selection outcome: no_fit_customer_proof",
                "",
                "## E-E-A-T Strength Decision",
                "- Applicability: required",
                "- Intent: commercial_investigation",
                "- Positive signals: [none]",
                "- Decision: proof_unavailable_safe_to_publish",
                "- Reason: Customer proof and Fred authority selectors returned no directly relevant approved evidence for this comparison.",
                "- Public copy boundary: public copy omits customer proof, named customer claims, review stories, exact quotes, testimonials, customer metrics, and unsupported SME claims.",
                "- Status: approved",
            ]
        )
        + "\n",
    )


def _finding_ids(findings: list[dict[str, object]]) -> set[str]:
    return {str(finding["rule_id"]) for finding in findings}


def _check(tmp_path: Path, *, article: Path | None = None, sidecar: Path | None = None, plan: Path | None = None, selector: Path | None = None, fred: Path | None = None) -> list[dict[str, object]]:
    article = article or _article(tmp_path / "article.md")
    sidecar = sidecar or _write(tmp_path / "validation.md", "Author policy: not_provided\n")
    plan = plan or _editorial_plan(tmp_path / "editorial-plan.json")
    selector = selector or _no_fit_selector(tmp_path / "selector.json")
    fred = fred or _fred(tmp_path / "fred.md")
    return eeat_strength_guard.check_file(
        article,
        proof_sidecar=sidecar,
        editorial_plan=plan,
        customer_proof_selector_evidence=selector,
        fred_authority_evidence=fred,
    )


def test_commercial_comparison_without_signal_or_fallback_fails(tmp_path: Path):
    findings = _check(tmp_path)

    assert "eeat_strength_decision_missing" in _finding_ids(findings)
    assert any(finding["severity"] == "error" for finding in findings)


def test_no_fit_with_explicit_safe_to_publish_decision_warns(tmp_path: Path):
    sidecar = _fallback_sidecar(tmp_path / "validation.md")

    findings = _check(tmp_path, sidecar=sidecar)

    assert _finding_ids(findings) == {"eeat_strength_safe_but_weak"}
    assert findings[0]["severity"] == "warning"


def test_named_author_is_positive_signal_for_commercial_page(tmp_path: Path):
    article = _article(tmp_path / "article.md", author="Corey O'Donnell")

    findings = _check(tmp_path, article=article)

    assert findings == []


def test_selected_customer_proof_is_positive_signal(tmp_path: Path):
    selector = _selected_selector(tmp_path / "selector.json")

    findings = _check(tmp_path, selector=selector)

    assert findings == []


def test_source_specific_rejections_satisfy_available_proof_decision(tmp_path: Path):
    selector = _rejected_selector(tmp_path / "selector.json")
    sidecar = _fallback_sidecar(tmp_path / "validation.md")

    findings = _check(tmp_path, selector=selector, sidecar=sidecar)

    assert _finding_ids(findings) == {"eeat_strength_safe_but_weak"}


def test_incomplete_rejections_leave_available_proof_blocker(tmp_path: Path):
    selector = _rejected_selector(tmp_path / "selector.json", complete=False)
    sidecar = _fallback_sidecar(tmp_path / "validation.md")

    findings = _check(tmp_path, selector=selector, sidecar=sidecar)

    assert "eeat_strength_available_proof_omitted" in _finding_ids(findings)


def test_selected_fred_authority_is_positive_signal(tmp_path: Path):
    fred = _fred(tmp_path / "fred.md", selected=True)

    findings = _check(tmp_path, fred=fred)

    assert findings == []


def test_approved_review_theme_with_visible_public_link_is_positive_signal(tmp_path: Path):
    review_url = "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/"
    article = _article(
        tmp_path / "article.md",
        body=(
            "A Capterra review theme can add a customer review perspective when it is "
            f"linked in the same paragraph: [Capterra review theme evidence]({review_url})."
        ),
    )
    sidecar = _write(
        tmp_path / "validation.md",
        "\n".join(
            [
                "## Review Site Theme Selection",
                "- Platform: Capterra",
                "- Source row ref: Capterra tab row 12",
                f"- Public review-site URL: {review_url}",
                "- Workflow theme: customer review perspective on job lifecycle workflows",
                "- Status: approved for paraphrased review-theme use",
            ]
        )
        + "\n",
    )

    findings = _check(tmp_path, article=article, sidecar=sidecar)

    assert findings == []


def test_approved_sme_review_note_is_positive_signal(tmp_path: Path):
    sidecar = _write(
        tmp_path / "validation.md",
        "\n".join(
            [
                "## E-E-A-T Strength Decision",
                "- Applicability: required",
                "- Intent: commercial_investigation",
                "- Positive signals: SME review note",
                "- Decision: positive_eeat_signal_present",
                "- Reason: A named SME reviewed the comparison logic before release.",
                "- Public copy boundary: public copy omits customer proof, named customer claims, review stories, exact quotes, testimonials, customer metrics, and unsupported SME claims.",
                "- SME review note: Reviewer name: Jane Smith; Role/title: Electrical operations SME; Review date: 2026-08-25; Source of review: Asana task comment; Status: approved",
                "- Status: approved",
            ]
        )
        + "\n",
    )

    findings = _check(tmp_path, sidecar=sidecar)

    assert findings == []


def test_informational_blog_does_not_require_strength_decision(tmp_path: Path):
    article = _article(
        tmp_path / "article.md",
        title="Electrical scheduling guide",
        body="Plan electrical scheduling around crew availability and job constraints.",
    )
    plan = _editorial_plan(tmp_path / "editorial-plan.json", commercial=False)

    findings = _check(tmp_path, article=article, plan=plan)

    assert findings == []


def test_summarize_policy_records_safe_but_weak_state(tmp_path: Path):
    article = _article(tmp_path / "article.md")
    sidecar = _fallback_sidecar(tmp_path / "validation.md")
    plan = _editorial_plan(tmp_path / "editorial-plan.json")
    selector = _no_fit_selector(tmp_path / "selector.json")
    fred = _fred(tmp_path / "fred.md")

    summary = eeat_strength_guard.summarize_policy(
        article,
        proof_sidecar=sidecar,
        editorial_plan=plan,
        customer_proof_selector_evidence=selector,
        fred_authority_evidence=fred,
    )

    assert summary["applicability"] == "required"
    assert summary["intent"] == "commercial_investigation"
    assert summary["positive_signals"] == []
    assert summary["decision"] == "proof_unavailable_safe_to_publish"
    assert summary["status"] == "warning"
    assert summary["findings"] == ["eeat_strength_safe_but_weak"]
