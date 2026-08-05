from pathlib import Path


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
