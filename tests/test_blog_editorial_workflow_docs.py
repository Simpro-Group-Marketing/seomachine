from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
EDITORIAL_CONTRACT = ROOT / "context" / "blog-editorial-strategy.md"


def test_canonical_editorial_contract_defines_reader_and_proof_safe_story_rules():
    content = EDITORIAL_CONTRACT.read_text(encoding="utf-8")

    required = [
        "## Reader Contract",
        "- Brand:",
        "- Author mode: named_author | brand_editorial",
        "- Primary reader:",
        "- Sophistication:",
        "- Entry situation or problem:",
        "- Existing belief:",
        "- Desired decision or action:",
        "- Distinctive angle:",
        "- Promised payoff:",
        "- Intentionally out of scope:",
        "- Funnel stage: tofu | mofu | bofu | thought_leadership",
        "Stories and scenes are optional.",
        "approved customer proof",
        "source-supported author experience",
        "unnamed explanatory workflows",
        "Specificity hierarchy",
        "Stakes and Relevance",
        "Promise Integrity",
        "does not approve claims, proof, product language, or competitive assertions",
    ]

    for text in required:
        assert text in content, f"canonical editorial contract missing {text}"


def test_shared_blog_workflows_reference_editorial_contract():
    paths = [
        ROOT / ".claude" / "commands" / "research.md",
        ROOT / ".claude" / "commands" / "write.md",
        ROOT / ".claude" / "commands" / "rewrite.md",
        ROOT / ".claude" / "commands" / "article.md",
        ROOT / ".claude" / "commands" / "analyze-existing.md",
        ROOT / ".claude" / "commands" / "optimize.md",
    ]

    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "context/blog-editorial-strategy.md" in content, (
            f"{path.name} missing canonical editorial contract"
        )


def test_research_and_article_planning_include_reader_contract_fields():
    paths = [
        ROOT / ".claude" / "commands" / "research.md",
        ROOT / ".claude" / "commands" / "article.md",
    ]
    required = [
        "## Reader Contract",
        "Author mode: named_author | brand_editorial",
        "Primary reader:",
        "Entry situation or problem:",
        "Desired decision or action:",
        "Distinctive angle:",
        "Promised payoff:",
        "Funnel stage: tofu | mofu | bofu | thought_leadership",
    ]

    for path in paths:
        content = path.read_text(encoding="utf-8")
        for text in required:
            assert text in content, f"{path.name} missing Reader Contract field {text}"


def test_article_plan_and_assembly_require_section_throughline_and_continuity_pass():
    content = (ROOT / ".claude" / "commands" / "article.md").read_text(
        encoding="utf-8"
    )
    required = [
        "Reader question:",
        "Section answer or payoff:",
        "Bridge from previous section:",
        "Bridge to next section:",
        "Mandatory Continuity Pass",
        "Every section advances the headline promise.",
        "Sections do not restart the article or repeat prior setup.",
        "Transitions express the actual logical relationship",
        "Introduction tensions, questions, and open loops are resolved.",
        "The conclusion completes the introduction",
        "A removable section is removed unless it provides a documented payoff.",
    ]

    for text in required:
        assert text in content, f"article workflow missing continuity rule {text}"


def test_blog_workflows_do_not_require_named_or_fabricated_scenarios():
    paths = [
        ROOT / ".claude" / "commands" / "write.md",
        ROOT / ".claude" / "commands" / "rewrite.md",
        ROOT / ".claude" / "commands" / "article.md",
        ROOT / ".claude" / "agents" / "editor.md",
    ]
    forbidden = re.compile(
        r"(?:must|required|should|include|have|use).{0,60}"
        r"(?:mini[- ]stor(?:y|ies)|scenario(?:s)?).{0,60}"
        r"(?:names?|dates?|numbers?|outcomes?)",
        re.IGNORECASE,
    )

    for path in paths:
        content = path.read_text(encoding="utf-8")
        match = forbidden.search(content)
        assert match is None, f"{path.name} requires fabricated specificity: {match.group()}"
        assert "Stories and scenes are optional" in content, (
            f"{path.name} missing optional story rule"
        )


def test_editorial_agents_pair_specificity_with_proof_and_promise_integrity():
    write_content = (ROOT / ".claude" / "commands" / "write.md").read_text(
        encoding="utf-8"
    )
    editor_content = (ROOT / ".claude" / "agents" / "editor.md").read_text(
        encoding="utf-8"
    )
    headline_content = (
        ROOT / ".claude" / "agents" / "headline-generator.md"
    ).read_text(encoding="utf-8")
    editing_content = (
        ROOT / ".claude" / "skills" / "copy-editing" / "SKILL.md"
    ).read_text(encoding="utf-8")

    for content in [write_content, editor_content, headline_content]:
        assert "Promise Integrity" in content
        assert "fabricated precision" in content

    assert "Sweep 6: Stakes and Relevance" in editing_content
    assert "Heightened Emotion" not in editing_content
    assert "manufactured fear or urgency" in editing_content


def test_cta_rules_are_selected_by_funnel_stage():
    contract = (ROOT / "context" / "blog-editorial-strategy.md").read_text(
        encoding="utf-8"
    )
    paths = [
        ROOT / ".claude" / "commands" / "write.md",
        ROOT / ".claude" / "commands" / "article.md",
        ROOT / ".claude" / "agents" / "editor.md",
    ]

    for profile in ["tofu", "mofu", "bofu", "thought_leadership"]:
        assert f"`{profile}`" in contract

    assert "earliest stage" in contract
    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "CTA profile" in content, f"{path.name} does not apply a CTA profile"
        assert "tofu" in content
        assert "mofu" in content
        assert "bofu" in content
        assert "thought_leadership" in content
