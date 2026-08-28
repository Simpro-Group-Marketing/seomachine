import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / '.claude' / 'agents'
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
        "editor",
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


def test_writing_commands_bind_reviewed_humanizer_evidence_to_native_edits():
    """Removing Humanizer provenance from a native edit must make this fail."""
    for name in BLOG_WRITING_COMMANDS:
        content = _read(COMMAND_DIR / name)
        assert '--evidence "humanizer_policy=config/humanizer-policy.json"' in content
        assert '--evidence "humanizer_upstream=vendor/blader-humanizer/UPSTREAM.json"' in content


def test_editor_uses_reviewed_humanizer_as_advisory_style_guidance():
    """Bypassing the local policy or allowing Humanizer mutation must make this fail."""
    content = _read(AGENT_DIR / "editor.md")

    assert "vendor/blader-humanizer/SKILL.md" in content
    assert "config/humanizer-policy.json" in content
    assert "current vault voice context" in content
    assert "upstream guidance cannot approve a claim" in content
    assert "Humanizer never edits the article" in content
    assert "must not lower humanity or composite scores" in content
    assert "manual_editorial_review" not in content
    assert "do not supply rewritten factual wording or request human approval" in content
    assert "proof_routed" in content
    for field in (
        '"rule_id"',
        '"upstream_pattern"',
        '"disposition"',
        '"location"',
        '"evidence"',
        '"recommended_edit"',
        '"severity"',
        '"claim_change_risk"',
        '"protected_span"',
    ):
        assert field in content


def test_repository_docs_describe_humanizer_as_reviewed_style_governance():
    """A future agent must not mistake vendored advice for proof or runtime code."""
    for name in ("README.md", "CLAUDE.md", "AGENTS.md"):
        content = _read(ROOT / name)
        assert "vendor/blader-humanizer/UPSTREAM.json" in content
        assert "config/humanizer-policy.json" in content
        assert "never edits public copy directly" in content
        assert "no runtime network access" in content
        assert "python tools/humanizer_upstream.py verify" in content


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


def test_all_blog_specialists_are_advisory_and_defer_release_status():
    advisory_agents = (
        'content-analyzer.md',
        'editor.md',
        'seo-optimizer.md',
        'meta-creator.md',
        'internal-linker.md',
        'keyword-mapper.md',
    )
    forbidden = (
        'Publishing Ready',
        'Ready to Publish',
        'ready to publish',
        'Publishing Recommendation',
        'prevent publishing',
    )

    for name in advisory_agents:
        content = _read(AGENT_DIR / name)
        assert 'advisory findings' in content
        assert '/publish-readiness' in content
        for phrase in forbidden:
            assert phrase not in content


def test_content_analyzer_returns_a_readiness_handoff_not_a_release_verdict():
    content = _read(AGENT_DIR / 'content-analyzer.md')

    assert '## Readiness Handoff' in content
    assert 'Final release status comes only from `/publish-readiness`' in content
    assert 'SEO quality below 90' in content
    assert 'any critical SEO issue' in content
    assert 'AEO/GEO below 90' in content
    assert '## 8. Publishing Checklist' not in content


def test_active_production_prompts_do_not_carry_legacy_brand_or_topic_defaults():
    legacy_pattern = re.compile(
        r'\b(?:castos|podcast(?:s|er|ers|ing)?)\b',
        re.IGNORECASE,
    )
    violations = []

    for directory in (COMMAND_DIR, AGENT_DIR):
        for path in directory.glob('*.md'):
            for line_number, line in enumerate(
                _read(path).splitlines(),
                start=1,
            ):
                if legacy_pattern.search(line):
                    violations.append(
                        f'{path.relative_to(ROOT)}:{line_number}: {line.strip()}'
                    )

    assert violations == []


def test_optimize_is_findings_and_targeted_edit_loop_not_finalizer():
    content = _read(COMMAND_DIR / "optimize.md")

    assert "Optimization is a findings and targeted edit loop" in content
    assert "not a separate finalization path" in content
    assert "/publish-readiness" in content
    assert "SEO 90-94 is release-pass, below-target" in content
    assert "honest, source-safe optimization pass" in content
    assert "no honest SEO fix recommended" in content
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
    assert "`seo_quality`: score, release-floor threshold 90, advisory target 95" in content
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
    assert "SEO quality release floor of 90/100 or higher with zero critical SEO issues" in content
    assert "SEO quality optimization target is 95/100" in content
    assert "AEO/GEO score of 90/100 or higher" in content
    assert "Use the Simpro vault connector only for Simpro-owned artifacts" in content
    assert "AroFlo, BigChange, and ClockShark owned artifacts" in content
    assert "Missing, unknown, or malformed brand metadata fails closed" in content
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
        assert "SEO quality release floor 90/100+ and optimization target 95/100" in content
        assert "AEO/GEO 90/100+" in content
        assert "content quality 85/100+" in content
        for phrase in forbidden_embedded_policy:
            assert phrase not in content

def test_readme_no_longer_lists_deleted_authoring_modules():
    content = _read(ROOT / "README.md")

    assert "Blog writing is native-first" in content
    assert "Python modules do not draft, rewrite, or patch article copy" in content
    assert "SEO quality must clear the 90/100 release floor with zero critical SEO issues" in content
    assert "SEO quality should target 95/100 when honest, source-safe optimization can improve the artifact" in content
    for deleted_tool in DELETED_AUTHORING_TOOLS:
        assert deleted_tool not in content


def test_seo_guidelines_keep_url_best_practices_evidence_safe():
    content = _read(ROOT / "context" / "seo-guidelines.md")

    assert "Semrush is third-party opportunity/SERP context" in content
    assert "GSC remains first-party performance truth" in content
    assert "source-artifact readiness does not validate rendered CMS output" in content
    for unsupported in (
        "5-15% of website traffic can come from AI sources",
        "90% of buyers consult AI",
        "AI scrapers prioritize content near the top",
        "Every article should include a TL;DR",
        "Video increases time on page",
        "Create companion video content for every major guide",
    ):
        assert unsupported not in content


def test_default_pytest_route_is_the_deterministic_core_suite():
    content = _read(ROOT / 'pytest.ini')

    assert '[pytest]' in content
    assert 'testpaths = tests' in content

    contributing = _read(ROOT / 'CONTRIBUTING.md')
    assert 'python -m pytest -q' in contributing
    assert 'python -m pytest integration_tests -q' in contributing
    assert 'deterministic core suite' in contributing


def test_performance_and_cluster_surfaces_preserve_native_handoffs():
    performance_agent = _read(AGENT_DIR / 'performance.md')
    performance_command = _read(COMMAND_DIR / 'performance-review.md')
    cluster_command = _read(COMMAND_DIR / 'cluster.md')

    assert 'advisory findings' in performance_agent
    assert 'Do not edit content' in performance_agent
    assert 'Native commands own content changes' in performance_agent
    assert '/publish-readiness' in performance_agent

    for command in (performance_command, cluster_command):
        assert '/research' in command
        assert '/write' in command
        assert 'vault connector workflow' in command

    assert '/analyze-existing' in performance_command
    assert '/optimize' in performance_command
    assert '/rewrite' in performance_command
    assert '/scrub' in performance_command
    assert '/publish-readiness' in performance_command
    assert 'cluster-strategist' in cluster_command
