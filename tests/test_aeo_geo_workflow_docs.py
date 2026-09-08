import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMAND_DIR = ROOT / ".claude" / "commands"
BLOG_WRITING_COMMANDS = ("write.md", "rewrite.md", "optimize.md")
RESEARCH_AND_ANALYSIS_COMMANDS = ("research.md", "analyze-existing.md")
BLOG_COMMANDS = (*BLOG_WRITING_COMMANDS, "scrub.md", "publish-readiness.md")
DELETED_AUTHORING_TOOLS = (
    "article_planner.py",
    "section_writer.py",
    "blog_assembly_mutation_recorder.py",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_blog_writing_commands_keep_public_copy_native_owned():
    for name in BLOG_WRITING_COMMANDS:
        content = _read(COMMAND_DIR / name)

        assert "Python must not draft, rewrite, or patch public blog Markdown" in content
        assert "/publish-readiness" in content
        assert "context/aeo-geo-blog-strategy.md" in content
        for deleted_tool in DELETED_AUTHORING_TOOLS:
            assert deleted_tool not in content


def test_original_new_blog_route_replaces_the_redundant_article_command():
    assert not (COMMAND_DIR / "article.md").exists()

    active_workflow_docs = (
        ROOT / ".claude" / "commands" / "cluster.md",
        ROOT / ".claude" / "commands" / "content-calendar.md",
        ROOT / ".claude" / "commands" / "research-ai-citations.md",
        ROOT / "README.md",
        ROOT / "QUICK-START.md",
        ROOT / "CLAUDE.md",
        ROOT / "context" / "aeo-geo-blog-strategy.md",
    )
    for path in active_workflow_docs:
        assert not re.search(r"(?:^|[\s`])/article(?:\s|\[|`)", _read(path))


def test_writing_commands_restore_original_specialist_handoffs():
    write = _read(COMMAND_DIR / "write.md")
    rewrite = _read(COMMAND_DIR / "rewrite.md")
    optimize = _read(COMMAND_DIR / "optimize.md")

    for agent in (
        "content-analyzer",
        "seo-optimizer",
        "meta-creator",
        "internal-linker",
        "keyword-mapper",
    ):
        assert agent in write
    for agent in (
        "content-analyzer",
        "editor",
        "seo-optimizer",
        "meta-creator",
        "internal-linker",
        "keyword-mapper",
    ):
        assert agent in rewrite
        assert agent in optimize


def test_writing_commands_attest_native_edits_without_python_copy_writers():
    expectations = {
        "write.md": "--stage draft",
        "rewrite.md": "--stage draft",
        "optimize.md": "--stage optimization",
    }
    for name, stage_argument in expectations.items():
        content = _read(COMMAND_DIR / name)
        assert "blog_assembly_stage_receipt.py begin-native-edit" in content
        assert "blog_assembly_stage_receipt.py finish-native-edit" in content
        assert stage_argument in content
        assert "blog_assembly_mutation_recorder.py" not in content


def test_specialist_agents_return_findings_and_defer_release_status():
    agent_dir = ROOT / ".claude" / "agents"
    forbidden = (
        "Structured Output for Automation",
        "apply revisions programmatically",
        "Final publishing recommendation",
        "Publishing Recommendation",
    )
    for name in ("content-analyzer.md", "editor.md", "seo-optimizer.md"):
        content = _read(agent_dir / name)
        assert "advisory findings" in content
        for phrase in forbidden:
            assert phrase not in content


def test_optimize_is_findings_and_targeted_edit_loop_not_finalizer():
    content = _read(COMMAND_DIR / "optimize.md")

    assert "Optimization is a findings and targeted edit loop" in content
    assert "not a separate finalization path" in content
    assert "/publish-readiness" in content
    for deleted_tool in DELETED_AUTHORING_TOOLS:
        assert deleted_tool not in content


def test_scrub_command_is_read_only_diagnostics():
    content = _read(COMMAND_DIR / "scrub.md")

    assert "read-only diagnostics" in content
    assert "must not overwrite article Markdown" in content
    assert "Do not claim the article changed" in content
    for deleted_tool in DELETED_AUTHORING_TOOLS:
        assert deleted_tool not in content


def test_publish_readiness_documents_independent_scorecard():
    content = _read(COMMAND_DIR / "publish-readiness.md")

    assert "`/publish-readiness` is the release owner" in content
    assert "`scorecard`" in content
    assert "`content_quality`: score, threshold 85 for blogs" in content
    assert "`seo_quality`: score, threshold 90" in content
    assert "`critical_issue_count` of 0" in content
    assert "`aeo_geo`: score, threshold 90 for blogs" in content
    for deleted_tool in DELETED_AUTHORING_TOOLS:
        assert deleted_tool not in content


def test_strategy_keeps_native_boundary_and_score_thresholds():
    content = _read(ROOT / "context" / "aeo-geo-blog-strategy.md")

    assert "Python does not draft, rewrite, or patch Markdown" in content
    assert "`/research` owns the research brief and validation sidecar planning" in content
    assert "`/analyze-existing` owns the analysis report and rewrite routing" in content
    assert "`/scrub` is read-only diagnostics" in content
    assert "`/publish-readiness` owns the scorecard" in content
    assert "Content quality score of 85/100 or higher" in content
    assert "SEO quality score of 90/100 or higher with zero critical SEO issues" in content
    assert "AEO/GEO score of 90/100 or higher" in content
    assert "use the Simpro vault connector as the active context source" in content
    for deleted_tool in DELETED_AUTHORING_TOOLS:
        assert deleted_tool not in content

def test_research_and_analyze_existing_are_lean_command_skeletons():
    forbidden_embedded_policy = (
        "### Obsidian Vault Source Rule",
        "### Vault-Backed Competitor and Feature Guardrails",
        "Customer Proof Selection Decision",
        "Selected Customer Proof Mining",
        "python data_sources/modules/customer_proof_selector.py",
        "python data_sources/modules/fred_authority_selector.py",
    )

    for name in RESEARCH_AND_ANALYSIS_COMMANDS:
        content = _read(COMMAND_DIR / name)

        assert "context/aeo-geo-blog-strategy.md" in content
        assert "validation sidecar" in content
        assert "Customer Proof Pack" in content
        assert "Fred Voccola Authority Selection" in content
        assert "SEO quality 90/100+" in content
        assert "AEO/GEO 90/100+" in content
        assert "content quality 85/100+" in content
        for phrase in forbidden_embedded_policy:
            assert phrase not in content

def test_readme_no_longer_lists_deleted_authoring_modules():
    content = _read(ROOT / "README.md")

    assert "Blog writing is native-first" in content
    assert "Python modules do not draft, rewrite, or patch article copy" in content
    assert "SEO quality must be 90/100 or higher with zero critical SEO issues" in content
    for deleted_tool in DELETED_AUTHORING_TOOLS:
        assert deleted_tool not in content
