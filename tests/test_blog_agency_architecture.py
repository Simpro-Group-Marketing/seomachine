import re
import shlex
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CANONICAL_COMMANDS = {
    "analyze-existing",
    "article",
    "cluster",
    "content-calendar",
    "landing-audit",
    "landing-competitor",
    "landing-publish",
    "landing-research",
    "landing-write",
    "optimize",
    "performance-review",
    "priorities",
    "publish-draft",
    "publish-readiness",
    "repurpose",
    "research-ai-citations",
    "research-gaps",
    "research-performance",
    "research-serp",
    "research-topics",
    "research-trending",
    "research",
    "rewrite",
    "scrub",
    "write",
}

CANONICAL_AGENTS = {
    "cluster-strategist",
    "content-analyzer",
    "cro-analyst",
    "editor",
    "headline-generator",
    "internal-linker",
    "keyword-mapper",
    "landing-page-optimizer",
    "meta-creator",
    "performance",
    "seo-optimizer",
}

CUSTOMER_PROOF_RULE_PATHS = (
    ROOT / ".agents" / "rules" / "customer-proof.md",
    ROOT / ".claude" / "rules" / "customer-proof.md",
    ROOT / ".cursor" / "rules" / "customer-proof.mdc",
)

SEAL_OWNER = ROOT / ".claude" / "commands" / "publish-readiness.md"
STEERING_SURFACES = (
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "README.md",
    ROOT / "context" / "aeo-geo-blog-strategy.md",
)

SELECTOR = "data_sources/modules/customer_proof_selector.py"
REQUIRED_SELECTOR_FLAGS = frozenset(
    {
        "--title",
        "--objective",
        "--context-pack",
        "--context-receipt",
        "--evidence-output",
        "--slate",
        "--roles",
        "--require-eeat-story",
        "--limit",
    }
)


def _rule_body(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    if content.startswith("---\n"):
        _, _, content = content.split("---\n", 2)
    return content.strip()


def _normalized_markdown(content: str) -> str:
    return "\n".join(
        re.sub(r"\s+", " ", line).strip()
        for line in content.splitlines()
        if line.strip()
    )


def _selector_contracts(content: str) -> dict[str, list[frozenset[str]]]:
    contracts: dict[str, list[frozenset[str]]] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith(f"python {SELECTOR} "):
            continue
        tokens = shlex.split(stripped, posix=True)
        flags = frozenset(token for token in tokens if token.startswith("--"))
        role_index = tokens.index("--roles")
        contracts.setdefault(tokens[role_index + 1], []).append(flags)
    return contracts


def _seal_surfaces() -> tuple[Path, ...]:
    return (
        *STEERING_SURFACES,
        *(ROOT / ".claude" / "commands").glob("*.md"),
        *(ROOT / ".agents" / "rules").glob("*.md"),
        *(ROOT / ".claude" / "rules").glob("*.md"),
        *(ROOT / ".cursor" / "rules").glob("*.mdc"),
    )


def _seal_steps(content: str) -> list[str]:
    steps: list[str] = []
    command_blocks = re.findall(
        r"python\s+data_sources/modules/.*?(?=\n\s*python\s+data_sources/modules/|\Z)",
        content,
        flags=re.DOTALL,
    )
    for command in command_blocks:
        if re.search(r"blog_assembly_bom\.py\s+build\b", command):
            steps.append("build")
        elif re.search(
            r"publish_readiness\.py\b.*?--phase\s+preflight\b",
            command,
            flags=re.DOTALL,
        ):
            steps.append("preflight")
        elif re.search(r"blog_assembly_bom\.py\s+finalize\b", command):
            steps.append("finalize")
        elif re.search(
            r"publish_readiness\.py\b.*?--phase\s+final\b",
            command,
            flags=re.DOTALL,
        ):
            steps.append("final")
    return steps


class BlogAgencyArchitectureTests(unittest.TestCase):
    def test_canonical_route_matrix_preserves_existing_workflow_drivers(self):
        command_names = {
            path.stem for path in (ROOT / ".claude" / "commands").glob("*.md")
        }
        self.assertSetEqual(CANONICAL_COMMANDS, command_names)

        route_contracts = {
            "/article": ("article.md", 'tool-name "article-command"', "content_scrubber.py", "/publish-readiness"),
            "/research -> /write": ("research.md", "Running `/write [topic]`", "/publish-readiness"),
            "/analyze-existing -> /rewrite": ("analyze-existing.md", "before `/rewrite`", "Running `/rewrite [topic]`"),
            "cleanup and optional optimize": ("scrub.md", "cleanup step"),
            "/optimize": ("optimize.md", 'tool-name "optimize-command"', "post_optimization_scrub", "/publish-readiness"),
            "/publish-readiness": ("publish-readiness.md", "--phase preflight", "--phase final", "gate summary"),
            "handoff": ("publish-draft.md", "before any WordPress API call", "/publish-readiness"),
        }
        for route, (command, *markers) in route_contracts.items():
            with self.subTest(route=route):
                content = (ROOT / ".claude" / "commands" / command).read_text(
                    encoding="utf-8"
                )
                for marker in markers:
                    self.assertIn(marker, content)

        grav_publish = (ROOT / ".claude" / "skills" / "grav-publish" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("must pass `/publish-readiness` before any Grav push", grav_publish)

    def test_existing_agent_set_rejects_new_reviewer_roles(self):
        agent_names = {
            path.stem for path in (ROOT / ".claude" / "agents").glob("*.md")
        }
        self.assertSetEqual(CANONICAL_AGENTS, agent_names)
        self.assertFalse(any("reviewer" in name for name in agent_names))

    def test_declared_command_agents_resolve_to_repository_capabilities(self):
        declared_agents: set[str] = set()
        for path in (ROOT / ".claude" / "commands").glob("*.md"):
            for match in re.finditer(r"\*\*Agent\*\*:\s*`([a-z0-9-]+)`", path.read_text(encoding="utf-8")):
                declared_agents.add(match.group(1))
        self.assertSetEqual(
            {
                "content-analyzer",
                "cro-analyst",
                "headline-generator",
                "internal-linker",
                "keyword-mapper",
                "landing-page-optimizer",
                "meta-creator",
                "seo-optimizer",
            },
            declared_agents,
        )
        self.assertTrue(declared_agents <= CANONICAL_AGENTS)

    def test_customer_proof_rules_have_one_semantic_contract(self):
        bodies = {path.name: _rule_body(path) for path in CUSTOMER_PROOF_RULE_PATHS}
        normalized_bodies = {
            name: _normalized_markdown(body) for name, body in bodies.items()
        }
        self.assertEqual(1, len(set(normalized_bodies.values())))

        expected_contracts = {
            "metric,quote,theme,experience_story": [REQUIRED_SELECTOR_FLAGS],
            "experience_story": [REQUIRED_SELECTOR_FLAGS],
        }
        expected_sections = {
            "# Customer Proof Rule",
            "## Selector-first execution",
            "## Selection and reuse",
            "## Public-copy use",
            "## Proof inventory",
            "## Publish handoff",
        }
        for path, body in zip(CUSTOMER_PROOF_RULE_PATHS, bodies.values()):
            with self.subTest(path=path.name):
                self.assertDictEqual(expected_contracts, _selector_contracts(body))
                sections = {
                    line.strip()
                    for line in body.splitlines()
                    if line.startswith("#")
                }
                self.assertSetEqual(expected_sections, sections)

    def test_selector_contracts_preserve_duplicate_roles_for_validation(self):
        malformed_then_valid = "\n".join(
            [
                f'python {SELECTOR} "[topic]" --title "[title]" --objective "[objective]" --context-pack "pack" --context-receipt "receipt" --slate --roles experience_story --require-eeat-story --limit 10',
                f'python {SELECTOR} "[topic]" --title "[title]" --objective "[objective]" --context-pack "pack" --context-receipt "receipt" --evidence-output "evidence" --slate --roles experience_story --require-eeat-story --limit 10',
            ]
        )
        contracts = _selector_contracts(malformed_then_valid)
        self.assertEqual(2, len(contracts["experience_story"]))
        self.assertNotIn("--evidence-output", contracts["experience_story"][0])
        self.assertIn("--evidence-output", contracts["experience_story"][1])

    def test_customer_proof_rules_limit_row_edits_to_editorial_judgment(self):
        required = "Edit selected/rejected rows only when editorial judgment requires it."
        for path in CUSTOMER_PROOF_RULE_PATHS:
            with self.subTest(path=path.name):
                self.assertIn(required, _rule_body(path))

    def test_publish_readiness_is_the_only_complete_four_step_seal_owner(self):
        owner_content = SEAL_OWNER.read_text(encoding="utf-8")
        self.assertEqual(
            ["build", "preflight", "finalize", "final"],
            list(dict.fromkeys(_seal_steps(owner_content))),
        )
        for path in _seal_surfaces():
            if path == SEAL_OWNER:
                continue
            with self.subTest(path=path.name):
                self.assertEqual([], _seal_steps(path.read_text(encoding="utf-8")))

    def test_publish_readiness_declares_route_specific_build_variants(self):
        content = SEAL_OWNER.read_text(encoding="utf-8")
        for marker in (
            "New article or rewrite without a dedicated pre-picked PAA section",
            "--paa-artifact",
            "Rewrite with a dedicated pre-picked PAA section",
            "--content-brief",
            "Optimization Reseal",
            "--optimizer-output",
            "--prior-preflight-readiness",
        ):
            self.assertIn(marker, content)
