from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMAND_DIR = ROOT / ".claude" / "commands"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(content: str, heading: str) -> str:
    """Return one Markdown h2 section without accepting markers elsewhere."""
    _, separator, remainder = content.partition(f"{heading}\n")
    assert separator, f"missing section: {heading}"
    return remainder.partition("\n## ")[0]


def test_repurpose_requires_a_sealed_article_and_final_readiness_attestation():
    """Generating a derivative from an unsealed or mismatched source is blocked."""
    content = _read(COMMAND_DIR / "repurpose.md")

    for required in (
        "/repurpose [article] --final-readiness [attestation] [--canonical-url URL]",
        "existing final-readiness validation",
        "exact article hash",
        "sealed_preview",
        "handoff_prepared",
        "blocked",
        "repurposed/[slug]-repurposed-[YYYY-MM-DD].md",
    ):
        assert required in content
    assert "not an assembly BOM artifact" in content
    assert "not a `/publish-readiness` input or gate" in content
    assert "not a release requirement" in content


def test_repurpose_uses_the_final_readiness_validator_and_exact_bound_input():
    """A lookalike attestation must not be accepted in place of final readiness."""
    content = _read(COMMAND_DIR / "repurpose.md")

    for required in (
        "data_sources.modules.publish_readiness.validate_passed_readiness_result",
        "phase `final`",
        "`passed: true`",
        "`input_hashes.article.sha256`",
        "exact-byte hash",
        "`file` path",
    ):
        assert required in content


def test_repurpose_uses_json_attestation_and_limits_sealed_preview_to_review():
    """A pre-publication preview must not be mistaken for a ready handoff."""
    handoff_states = _section(
        _read(COMMAND_DIR / "repurpose.md"),
        "## Handoff states",
    )

    for required in (
        "`sealed_preview`",
        "pre-publication derivative preview",
        "not a publish-ready handoff",
        "Canonical link: absent/unverified",
        "clearly labeled non-postable",
    ):
        assert required in handoff_states

    for required in (
        "`handoff_prepared`",
        "live check verifies the canonical identity",
        "check/time/evidence",
        "verified owner, account identity, and disclosure",
        "A supplied URL alone is not verification",
        "fall back to `sealed_preview`",
    ):
        assert required in handoff_states


def test_repurpose_example_requires_a_json_final_readiness_attestation():
    content = _read(COMMAND_DIR / "repurpose.md")

    assert (
        "--final-readiness research/final-readiness-field-service-guide-2026-08-21.json"
        in content
    )


def test_repurpose_handoff_is_manual_and_evidence_bound_per_selected_channel():
    """A channel handoff without accountable evidence and review is unsafe."""
    content = _read(COMMAND_DIR / "repurpose.md")

    for required in (
        "select channels rather than force them",
        "Audience/opportunity",
        "Adapted angle",
        "Permitted source passages",
        "Public proof links",
        "Owner",
        "Account identity",
        "Disclosure",
        "Human review required: yes",
        "manual posting",
    ):
        assert required in content


def test_repurpose_prohibits_unsupported_distribution_behavior():
    """Unsupported proof, fabricated voice, or speculative outcomes must be rejected."""
    content = _read(COMMAND_DIR / "repurpose.md")

    for required in (
        "No new proof-sensitive claims",
        "invented personal experience",
        "Automated posting is prohibited",
        "Fixed derivative counts are prohibited",
        "Fixed word quotas are prohibited",
        "Backlink promises are prohibited",
        "platform-algorithm claims are prohibited",
        "AI-citation predictions are prohibited",
        "specific live thread or question",
        "disclosed affiliation",
        "optional directly useful link",
    ):
        assert required in content

    for forbidden in (
        "maximizing AI citation potential",
        "One article should become 4-5 pieces",
        "This command automates the adaptation",
        "LinkedIn penalizes listicle-style posts",
        "Reddit penalizes link-heavy comments",
        "these become backlinks from Medium",
        "Brief personal context (\"I work in [industry], so...\")",
    ):
        assert forbidden not in content


def test_reddit_and_quora_require_live_disclosed_manual_participation_in_section():
    """Community safeguards must stay with the community-channel instructions."""
    reddit_and_quora = _section(
        _read(COMMAND_DIR / "repurpose.md"),
        "## Reddit and Quora",
    )

    for required in (
        "specific live thread or question",
        "disclosed affiliation",
        "optional directly useful link",
        "Manual posting is required",
    ):
        assert required in reddit_and_quora


def test_citation_research_and_repository_index_describe_the_safe_handoff():
    """Related workflow docs must not reintroduce speculative distribution promises."""
    research = _read(COMMAND_DIR / "research-ai-citations.md")
    claude = _read(ROOT / "CLAUDE.md")
    readme = _read(ROOT / "README.md")

    assert "manual, evidence-bound handoff" in research
    assert "does not predict citation outcomes" in research
    assert "Repurposing is optional distribution work, not an AI-citation mechanism" in research
    assert "/repurpose [article] --final-readiness [attestation] [--canonical-url URL]" in claude
    assert "manual, evidence-bound distribution handoff" in claude
    assert "not an AI-citation mechanism" in claude
    assert "/repurpose [article] --final-readiness [attestation] [--canonical-url URL]" in readme
    assert "optional manual distribution work, not an AI-citation mechanism" in readme
    assert "does not predict citation outcomes" in readme
    for forbidden in (
        "where you should appear",
        "competitors winning",
        "[Expected impact]",
        "if the content isn't structured for AI consumption",
        "These trigger AI to search the web and cite sources",
    ):
        assert forbidden not in research
    assert "does not establish why a source was or was not cited" in research
