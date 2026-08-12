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
SEAL_SURFACES = (
    ROOT / "README.md",
    ROOT / "context" / "aeo-geo-blog-strategy.md",
    ROOT / ".claude" / "commands" / "article.md",
    ROOT / ".claude" / "commands" / "write.md",
    ROOT / ".claude" / "commands" / "rewrite.md",
    ROOT / ".claude" / "commands" / "optimize.md",
    SEAL_OWNER,
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


def _selector_contracts(content: str) -> dict[str, frozenset[str]]:
    contracts: dict[str, frozenset[str]] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith(f"python {SELECTOR} "):
            continue
        tokens = shlex.split(stripped, posix=True)
        flags = frozenset(token for token in tokens if token.startswith("--"))
        role_index = tokens.index("--roles")
        contracts[tokens[role_index + 1]] = flags
    return contracts


def _seal_steps(content: str) -> list[str]:
    steps: list[str] = []
    for line in content.splitlines():
        normalized = line.strip()
        if not normalized.startswith("python data_sources/modules/"):
            continue
        if "blog_assembly_bom.py build" in normalized:
            steps.append("build")
        elif "publish_readiness.py" in normalized and "--phase preflight" in normalized:
            steps.append("preflight")
        elif "blog_assembly_bom.py finalize" in normalized:
            steps.append("finalize")
        elif "publish_readiness.py" in normalized and "--phase final" in normalized:
            steps.append("final")
    return steps


class BlogAgencyArchitectureTests(unittest.TestCase):
    def test_canonical_route_matrix_preserves_existing_workflow_drivers(self):
        command_names = {
            path.stem for path in (ROOT / ".claude" / "commands").glob("*.md")
        }
        self.assertSetEqual(CANONICAL_COMMANDS, command_names)

        for route, command in {
            "/article": "article.md",
            "/research -> /write": "research.md",
            "/analyze-existing -> /rewrite": "analyze-existing.md",
            "/scrub": "scrub.md",
            "/optimize": "optimize.md",
            "/publish-readiness": "publish-readiness.md",
            "/publish-draft": "publish-draft.md",
        }.items():
            with self.subTest(route=route):
                self.assertTrue((ROOT / ".claude" / "commands" / command).is_file())

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
            "metric,quote,theme,experience_story": REQUIRED_SELECTOR_FLAGS,
            "experience_story": REQUIRED_SELECTOR_FLAGS,
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

    def test_publish_readiness_is_the_only_complete_four_step_seal_owner(self):
        self.assertEqual(
            ["build", "preflight", "finalize", "final"],
            _seal_steps(SEAL_OWNER.read_text(encoding="utf-8")),
        )
        for path in SEAL_SURFACES:
            if path == SEAL_OWNER:
                continue
            with self.subTest(path=path.name):
                self.assertEqual([], _seal_steps(path.read_text(encoding="utf-8")))
                self.assertIn("/publish-readiness", path.read_text(encoding="utf-8"))
