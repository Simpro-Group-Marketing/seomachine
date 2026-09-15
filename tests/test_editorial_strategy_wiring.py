from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = (
    "context/blog-editorial-strategy.md",
    "context/aeo-geo-blog-strategy.md",
)
COMMANDS = (
    ".claude/commands/research.md",
    ".claude/commands/analyze-existing.md",
    ".claude/commands/write.md",
    ".claude/commands/rewrite.md",
    ".claude/commands/optimize.md",
    ".claude/commands/publish-readiness.md",
)
REVIEWERS = (
    ".claude/agents/content-analyzer.md",
    ".claude/agents/editor.md",
    ".claude/agents/seo-optimizer.md",
    ".claude/agents/meta-creator.md",
    ".claude/agents/internal-linker.md",
    ".claude/agents/keyword-mapper.md",
)


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_all_native_commands_and_reviewers_consume_both_strategy_sources() -> None:
    for path in COMMANDS + REVIEWERS:
        content = text(path)
        assert all(strategy in content for strategy in STRATEGIES), path


def test_planning_and_writing_ownership_is_explicit() -> None:
    assert "creates and freezes" in text(".claude/commands/research.md")
    assert "creates and freezes" in text(".claude/commands/analyze-existing.md")
    for path in (
        ".claude/commands/write.md",
        ".claude/commands/rewrite.md",
        ".claude/commands/optimize.md",
    ):
        content = text(path)
        assert "simpro-blog-editorial-plan/v2" in content
        assert "simpro-blog-plan-fulfillment/v1" in content


def test_semantic_fulfillment_review_stays_with_content_reviewers() -> None:
    for path in (
        ".claude/agents/content-analyzer.md",
        ".claude/agents/editor.md",
    ):
        content = text(path)
        assert "actual_excerpt" in content
        assert "planned purpose" in content


def test_current_strategy_docs_name_plan_v2_and_bom_v4() -> None:
    aeo = text("context/aeo-geo-blog-strategy.md")
    editorial = text("context/blog-editorial-strategy.md")
    assert "simpro-blog-editorial-plan/v2" in aeo
    assert "simpro-blog-assembly-bom/v4" in aeo
    assert "simpro-blog-plan-fulfillment/v1" in aeo
    assert "simpro-blog-editorial-plan/v2" in editorial


def test_hindsight_can_shape_private_angle_but_not_public_claims() -> None:
    planning_docs = (
        "context/blog-editorial-strategy.md",
        "context/aeo-geo-blog-strategy.md",
        ".claude/commands/research.md",
        ".claude/commands/analyze-existing.md",
    )
    writing_docs = (
        ".claude/commands/write.md",
        ".claude/commands/rewrite.md",
        ".claude/commands/optimize.md",
    )

    for path in planning_docs:
        content = text(path)
        assert "private" in content
        assert "reader angle" in content
        assert "section emphasis" in content
        assert "commercial framing" in content
        assert "public_claim_use: prohibited" in content
        assert "claim_support_allowed: false" in content

    for path in writing_docs:
        content = text(path)
        assert "Hindsight-informed" in content
        assert "planned reader angle" in content or "reader angle" in content
        assert "Do not quote, cite, disclose, paraphrase, metricize" in content
        assert "public claims" in content
        assert "route the plan defect" in content
