"""Regression coverage for the advisory target-performance receipt workflow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / ".claude" / "commands" / "research-performance.md"
AGENT = ROOT / ".claude" / "agents" / "performance.md"
POLICY = ROOT / "context" / "aeo-geo-blog-strategy.md"
README = ROOT / "README.md"
CLAUDE = ROOT / "CLAUDE.md"


def section(path: Path, heading: str) -> str:
    """Return one Markdown H2 section without relying on unrelated prose."""
    text = path.read_text(encoding="utf-8")
    marker = f"## {heading}\n"
    start = text.index(marker)
    next_heading = text.find("\n## ", start + len(marker))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def test_all_content_mode_keeps_its_legacy_markdown_only_output() -> None:
    all_content = section(COMMAND, "All-Content Mode")

    assert "research/performance-review-[YYYY-MM-DD].md" in all_content
    assert "or the closest existing performance artifact pattern" in all_content
    assert "does not create a target receipt" in all_content
    assert "performance-receipt-[slug]-[YYYY-MM-DD].json" not in all_content


def test_all_content_agent_retains_the_legacy_report_and_opportunity_contract() -> None:
    output_contract = section(AGENT, "Output Contract")

    assert "All-content reports retain the seven-section and per-opportunity contract below" in output_contract
    assert "For all-content reports and observed target-specific reports, include:" in output_contract
    for heading in (
        "Scope and evidence",
        "Executive findings",
        "Prioritized opportunity queue",
        "Page and query evidence",
        "Data-quality and causality limits",
        "Recommended workflow handoffs",
        "Measurement plan",
    ):
        assert f"`{heading}`" in output_contract
    for field in (
        "page or query",
        "observed change and source",
        "interpretation with uncertainty",
        "priority and rationale",
        "recommended action",
        "owning command",
        "success measure and comparison period",
    ):
        assert field in output_contract


def test_target_specific_mode_requires_the_matched_report_and_receipt_pair() -> None:
    target = section(COMMAND, "Target-Specific Mode")

    assert "research/performance-review-[slug]-[YYYY-MM-DD].md" in target
    assert "research/performance-receipt-[slug]-[YYYY-MM-DD].json" in target


def test_target_receipt_hashes_the_report_before_a_strict_build_and_check() -> None:
    target = section(COMMAND, "Target-Specific Mode")

    assert "Write and finalize the Markdown performance report first" in target
    assert "post_publish_measurement_receipt.py build --metadata" in target
    assert "--performance-report" in target
    assert "post_publish_measurement_receipt.py check" in target
    assert "--fail-on error" in target
    assert "validator checks the report's exact H2 contract against receipt status" in target
    assert "reproduces every blocked source identity, property, blocker code, and blocker detail verbatim" in target
    assert "rejects metrics from a blocked first-party lane" in target
    assert "Only rendered Markdown can satisfy headings, blocker evidence, or observed metrics" in target
    assert "non-empty observed values" in target
    assert "Blocked reports use only the documented data-only status and source rows" in target


def test_target_binding_modes_are_explicit_about_current_release_artifacts_and_legacy_pages() -> None:
    target = section(COMMAND, "Target-Specific Mode")

    assert "release_artifact" in target
    assert "final BOM" in target
    assert "live_url" in target
    assert "no local release artifact was available" in target
    assert "sealed editorial-plan URL slug" in target


def test_target_source_lanes_keep_first_party_observation_separate_from_context() -> None:
    target = section(COMMAND, "Target-Specific Mode")

    assert "GSC is search-performance truth" in target
    assert "GA4 is behavior/conversion evidence" in target
    assert "third-party tools are optional opportunity/SERP context" in target
    assert "never satisfy first-party observation" in target


def test_target_status_blocks_optimization_handoffs_without_first_party_observation() -> None:
    target = section(COMMAND, "Target-Specific Mode")

    assert "observed" in target
    assert "blocked" in target
    assert "at least one observed first-party lane" in target
    assert "A blocked target report contains no opportunity queue, diagnosis, recommendation of any kind, verdict, recommended action, owning-command or other workflow handoff, or success claim" in target


def test_performance_agent_keeps_blocked_targets_out_of_observed_opportunity_contract() -> None:
    output_contract = section(AGENT, "Output Contract")

    assert "For all-content analysis, return one Markdown queue report" in output_contract
    assert "For all-content reports and observed target-specific reports, include:" in output_contract
    assert "A blocked target report is limited to `Scope and evidence`" in output_contract
    assert "exact per-source blockers and limitations" in output_contract
    assert "A blocked target report contains no opportunity queue, diagnosis, recommendation of any kind, verdict, recommended action, owning-command or other workflow handoff, or success claim" in output_contract
    assert "not Customer Proof Pack or validation-sidecar proof" in output_contract
    assert "not external analytics truth or causal correlation" in output_contract
    assert "machine-checks the exact report headings against receipt status" in output_contract
    assert "blocked source identity, property, blocker code, and blocker detail verbatim" in output_contract
    assert "rejects metrics from a blocked first-party lane" in output_contract
    assert "Only rendered Markdown satisfies the contract" in output_contract
    assert "non-empty observed values" in output_contract
    assert "sealed editorial-plan URL slug" in output_contract


def test_required_evidence_keeps_blocked_reports_free_of_diagnosis_and_handoffs() -> None:
    required_evidence = section(COMMAND, "Required Evidence")

    assert "Observed target reports must include" in required_evidence
    assert "Blocked reports must instead include exact per-source blockers and limitations" in required_evidence
    assert "A blocked target report contains no opportunity queue, diagnosis, recommendation of any kind, verdict, recommended action, owning-command or other workflow handoff, or success claim" in required_evidence


def test_observed_report_evidence_is_conditioned_on_each_available_lane() -> None:
    required_evidence = section(COMMAND, "Required Evidence")

    assert "Every target receipt must record the GSC and GA4 source/property, filters, status, retrieval time, limitations, and blockers" in required_evidence
    assert "Blocked reports reproduce only exact source-specific blocker and limitation evidence" in required_evidence
    assert "For an observed GSC lane" in required_evidence
    assert "clicks, impressions, CTR, average position, and relevant queries" in required_evidence
    assert "For an observed GA4 lane" in required_evidence
    assert "sessions, views, active users, engagement, bounce rate, average session duration, and key events" in required_evidence
    assert "For a blocked lane, include its exact source-specific blockers and omit that lane's metrics" in required_evidence
    assert "Do not fabricate unavailable lane evidence" in required_evidence


def test_blocked_contract_is_scoped_consistently_across_command_agent_and_policy() -> None:
    command_target = section(COMMAND, "Target-Specific Mode")
    agent_mission = section(AGENT, "Core Mission")
    agent_analysis = section(AGENT, "Analysis")
    agent_quality = section(AGENT, "Quality Rules")
    policy = section(POLICY, "Post-Publish Performance Measurement")
    agent_text = AGENT.read_text(encoding="utf-8")

    assert "All-content and observed target-specific runs produce a prioritized optimization or rewrite recommendation" in COMMAND.read_text(encoding="utf-8")
    assert "blocked target-specific runs produce only an evidence-and-blocker report" in COMMAND.read_text(encoding="utf-8")
    assert "For all-content and observed target-specific runs, return prioritized advisory findings" in agent_mission
    assert "For blocked target-specific runs, return only the evidence scope, limitations, and exact source-specific blockers" in agent_mission
    assert "Apply the analysis below only to all-content and observed target-specific runs" in agent_analysis
    assert "Do not apply it to blocked target-specific runs" in agent_analysis
    assert "a focused content-work queue for all-content and observed target-specific runs" in agent_text
    assert "blocked target-specific runs produce only the restricted evidence-and-blocker report" in agent_text
    assert "Apply queue selection and monitoring-versus-intervention judgments only to all-content and observed target-specific runs" in agent_quality
    assert "never to blocked target-specific runs" in agent_quality
    blocked_allowlist = "A blocked target report is limited to `Scope and evidence`, `Data-quality and causality limits`, and exact per-source blockers and limitations"
    blocker_sentence = "A blocked target report contains no opportunity queue, diagnosis, recommendation of any kind, verdict, recommended action, owning-command or other workflow handoff, or success claim"
    for text in (command_target, section(AGENT, "Output Contract"), policy):
        assert blocked_allowlist in text
        assert blocker_sentence in text


def test_target_pair_is_not_described_as_a_public_output() -> None:
    target = section(COMMAND, "Target-Specific Mode").casefold()

    assert "durable public outputs" not in target
    assert "not public outputs" in target


def test_receipt_contract_is_advisory_not_public_proof_or_release_governance() -> None:
    command_target = section(COMMAND, "Target-Specific Mode")
    agent_output = section(AGENT, "Output Contract")
    policy = section(POLICY, "Post-Publish Performance Measurement")

    for text in (command_target, agent_output, policy):
        assert "advisory" in text
        assert "public-claim proof" in text
        assert "not an assembly BOM" in text
        assert "not a `/publish-readiness` input or gate" in text
        assert "not a release requirement" in text

    for text in (command_target, policy):
        assert "not Customer Proof Pack or validation-sidecar proof" in text


def test_summaries_identify_the_target_report_and_receipt_pair() -> None:
    for path in (README, CLAUDE):
        text = path.read_text(encoding="utf-8")
        assert "/research-performance [URL-or-path]" in text
        assert "report-and-receipt pair" in text


def test_docs_never_label_the_measurement_receipt_as_readiness_stage_proof_or_release() -> None:
    summary_lines = []
    for path in (README, CLAUDE):
        summary_lines.extend(
            line for line in path.read_text(encoding="utf-8").splitlines()
            if "/research-performance" in line
        )

    scoped_texts = (
        section(COMMAND, "Target-Specific Mode"),
        section(AGENT, "Output Contract"),
        section(POLICY, "Post-Publish Performance Measurement"),
        *summary_lines,
    )
    for text in scoped_texts:
        text = text.casefold()
        assert "final-readiness receipt" not in text
        assert "stage receipt" not in text
        assert "proof receipt" not in text
        assert "release receipt" not in text
