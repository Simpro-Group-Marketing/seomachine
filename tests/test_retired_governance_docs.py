"""Rules, reviewer agents, and the remaining commands describe the production BOM flow, not the retired stack."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RULES = ("seo-blog-strategy.md", "customer-proof.md", "faq-answer-quality.md", "blog-schema.md")
REVIEWERS = (
    "content-analyzer.md",
    "editor.md",
    "seo-optimizer.md",
    "meta-creator.md",
    "internal-linker.md",
    "keyword-mapper.md",
    "public-copy-boundary-reviewer.md",
)
COMMANDS = ("analyze-existing.md", "research-serp.md", "repurpose.md", "research-performance.md")
RETIRED = (
    "validation sidecar",
    "validation-sidecar",
    "editorial-plan v2",
    "v2 plan",
    "plan-fulfillment",
    "plan hash",
    "machine-review collector",
    "optimizer output",
    "assembly BOM",
    "stage receipts",
    "blog_release",
    "source_quality_guard",
    "blog_strategy_guard",
    "schema_handoff_guard",
    "inside `/publish-readiness`",
    "pre-picked brief section",
    "pre-picked brief section takes precedence",
    "fail readiness",
    "Vault Context Read Path",
    "Source Routing Decision",
)
DOCS = (
    *(f".claude/rules/{name}" for name in RULES),
    *(f".claude/agents/{name}" for name in REVIEWERS),
    *(f".claude/commands/{name}" for name in COMMANDS),
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


@pytest.mark.parametrize("path", DOCS)
def test_doc_carries_no_retired_governance_reference(path: str) -> None:
    content = _read(path)
    assert [phrase for phrase in RETIRED if phrase in content] == []


@pytest.mark.parametrize("name", REVIEWERS)
def test_reviewers_read_the_production_bom_and_never_edit_it(name: str) -> None:
    content = _read(f".claude/agents/{name}")
    if name == "public-copy-boundary-reviewer.md":
        assert "Do not edit the article file" in content
        return
    assert "production BOM" in content
    assert "never edit the article, the BOM, or its spec" in content


def test_rules_state_what_the_release_enforces() -> None:
    strategy = _read(".claude/rules/seo-blog-strategy.md")
    assert "simpro-production-bom-spec/v1" in strategy
    assert "primary keyword must differ from the destination main keyword" in strategy
    assert "editorial guidance; no gate checks them" in strategy
    assert "`canonicalize_link_identity`" in strategy and "image link never counts" in strategy
    assert "always runs its FAQ policy check" in _read(".claude/rules/faq-answer-quality.md")
    for path in (".claude/commands/research-performance.md", ".claude/agents/performance.md"):
        assert "archived pre-production final BOM" in _read(path)
    faq = _read(".claude/rules/faq-answer-quality.md")
    assert "What the release enforces" in faq
    assert "not a BOM PAA question" in faq
    proof = _read(".claude/rules/customer-proof.md")
    assert "The production BOM build binds it by path and sha256" in proof
    schema = _read(".claude/rules/blog-schema.md")
    assert "production BOM spec's `schema_notes` choice" in schema


def test_analyze_existing_feeds_the_research_bom_and_faq_comes_only_from_the_capture() -> None:
    content = _read(".claude/commands/analyze-existing.md")
    assert "production BOM spec" in content
    assert "no pre-picked brief precedence" in content
    serp = _read(".claude/commands/research-serp.md")
    assert "a user CSV cannot supply FAQ questions" in serp


def test_readme_and_seo_guidelines_follow_the_production_flow() -> None:
    readme = _read("README.md")
    assert "machine reviews" not in readme
    assert "frozen editorial plan" not in readme
    guidelines = _read("context/seo-guidelines.md")
    assert "pre-picked" not in guidelines
    assert "Machine reviewers" not in guidelines
