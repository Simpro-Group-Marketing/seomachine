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
SELECTOR_VALUE_FLAGS = REQUIRED_SELECTOR_FLAGS - {
    "--slate",
    "--require-eeat-story",
}
BUILD_RESEARCH_INPUT_FLAGS = frozenset(
    {
        "--paa-artifact",
        "--content-brief",
        "--user-paa-csv",
        "--answersocrates-blocker",
    }
)
LAUNCH = r"(?:python(?:\.exe)?|py(?:\.exe)?)(?:\s+-\d+(?:\.\d+)?)?"
MODULE_PREFIX = (
    rf"{LAUNCH}\s+(?:\.[\\/])?data_sources[\\/]modules[\\/]"
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


def _selector_contracts(content: str) -> dict[str, list[dict[str, str | None]]]:
    contracts: dict[str, list[dict[str, str | None]]] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith(f"python {SELECTOR} "):
            continue
        tokens = shlex.split(stripped, posix=True)
        options: dict[str, str | None] = {}
        for index, token in enumerate(tokens):
            if not token.startswith("--"):
                continue
            if token in SELECTOR_VALUE_FLAGS:
                value = tokens[index + 1] if index + 1 < len(tokens) else None
                options[token] = None if value is None or value.startswith("--") else value
            else:
                options[token] = "present"
        role = options.get("--roles")
        if role:
            contracts.setdefault(role, []).append(options)
    return contracts


def _selector_contract_is_valid(contract: dict[str, str | None]) -> bool:
    return set(contract) == REQUIRED_SELECTOR_FLAGS and all(
        contract[flag] for flag in SELECTOR_VALUE_FLAGS
    )


def _seal_surfaces() -> tuple[Path, ...]:
    return (
        *ROOT.glob("*.md"),
        *(ROOT / ".claude" / "commands").glob("*.md"),
        *(ROOT / ".agents" / "rules").glob("*.md"),
        *(ROOT / ".claude" / "rules").glob("*.md"),
        *(ROOT / ".cursor" / "rules").glob("*.mdc"),
        ROOT / "context" / "aeo-geo-blog-strategy.md",
    )


def _module_command_blocks(content: str) -> list[str]:
    starts = [
        match.start()
        for match in re.finditer(
            rf"{MODULE_PREFIX}(?:blog_assembly_bom|publish_readiness)\.py\b",
            content,
        )
    ]
    return [
        content[start : starts[index + 1] if index + 1 < len(starts) else len(content)]
        for index, start in enumerate(starts)
    ]


def _seal_steps(content: str) -> list[str]:
    steps: list[str] = []
    for command in _module_command_blocks(content):
        if re.search(r"blog_assembly_bom\.py\s+build\b", command):
            steps.append("build")
        elif re.search(r"publish_readiness\.py\b.*?--phase\s+preflight\b", command, re.DOTALL):
            steps.append("preflight")
        elif re.search(r"blog_assembly_bom\.py\s+finalize\b", command):
            steps.append("finalize")
        elif re.search(r"publish_readiness\.py\b.*?--phase\s+final\b", command, re.DOTALL):
            steps.append("final")
    return steps


def _bom_build_research_input_sets(content: str) -> list[frozenset[str]]:
    return [
        frozenset(re.findall(r"--[a-z-]+", command)) & BUILD_RESEARCH_INPUT_FLAGS
        for command in _module_command_blocks(content)
        if re.search(r"blog_assembly_bom\.py\s+build\b", command)
    ]


def _route_capability_references(content: str) -> dict[str, set[str]]:
    return {
        "command": set(
            re.findall(
                r"(?:Running|Run|rerun|invoke|before|after|Executes)\s+`/([a-z][a-z0-9-]*)",
                content,
            )
        ),
        "agent": set(
            re.findall(r"\*\*Agent\*\*:\s*`([a-z][a-z0-9-]*)`", content)
        ),
        "skill": set(
            re.findall(r"\*\*Skill\*\*:\s*`([a-z][a-z0-9-]*)`", content)
        ),
    }


def _repository_capabilities() -> dict[str, set[str]]:
    return {
        "command": {path.stem for path in (ROOT / ".claude" / "commands").glob("*.md")},
        "agent": {path.stem for path in (ROOT / ".claude" / "agents").glob("*.md")},
        "skill": {path.name for path in (ROOT / ".claude" / "skills").glob("*") if path.is_dir()},
    }


class BlogAgencyArchitectureTests(unittest.TestCase):
    def test_canonical_route_matrix_preserves_existing_workflow_drivers(self):
        command_names = {
            path.stem for path in (ROOT / ".claude" / "commands").glob("*.md")
        }
        self.assertSetEqual(CANONICAL_COMMANDS, command_names)

        command_content = {
            path.stem: path.read_text(encoding="utf-8")
            for path in (ROOT / ".claude" / "commands").glob("*.md")
        }
        route_references = {
            name: _route_capability_references(content)["command"]
            for name, content in command_content.items()
        }
        self.assertIn("write", route_references["research"])
        self.assertIn("rewrite", route_references["analyze-existing"])
        self.assertIn("scrub", route_references["write"])
        self.assertIn("publish-readiness", route_references["write"])
        self.assertIn("publish-readiness", route_references["rewrite"])
        self.assertIn("scrub", route_references["optimize"])
        self.assertIn("publish-readiness", route_references["optimize"])
        self.assertIn("optimize", route_references["publish-readiness"])
        self.assertIn("publish-readiness", route_references["publish-draft"])

        for command, driver in {
            "article": "article-command",
            "write": "write-command",
            "rewrite": "rewrite-command",
            "optimize": "optimize-command",
        }.items():
            self.assertRegex(
                command_content[command],
                rf'blog_assembly_mutation_recorder\.py\s+start.*?--tool-name\s+"{driver}"',
            )
        self.assertRegex(command_content["scrub"], r"content_scrubber\.py")
        self.assertRegex(command_content["optimize"], r"--stage\s+post_optimization_scrub")
        self.assertRegex(command_content["publish-readiness"], r"--phase\s+preflight")
        self.assertRegex(command_content["publish-readiness"], r"--phase\s+final")
        self.assertRegex(command_content["publish-draft"], r"before any WordPress API call")

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

        expected_roles = {"metric,quote,theme,experience_story", "experience_story"}
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
                contracts = _selector_contracts(body)
                self.assertSetEqual(expected_roles, set(contracts))
                for role in expected_roles:
                    self.assertEqual(1, len(contracts[role]))
                    self.assertTrue(_selector_contract_is_valid(contracts[role][0]))
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
        self.assertFalse(_selector_contract_is_valid(contracts["experience_story"][0]))
        self.assertTrue(_selector_contract_is_valid(contracts["experience_story"][1]))

    def test_selector_contracts_reject_required_flags_without_values(self):
        missing_title_value = (
            f'python {SELECTOR} "[topic]" --title --objective "[objective]" '
            '--context-pack "pack" --context-receipt "receipt" '
            '--evidence-output "evidence" --slate --roles experience_story '
            '--require-eeat-story --limit 10'
        )
        contract = _selector_contracts(missing_title_value)["experience_story"][0]
        self.assertIsNone(contract["--title"])
        self.assertFalse(_selector_contract_is_valid(contract))

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

    def test_seal_scanner_detects_multiline_windows_and_portable_duplicate(self):
        alternate_duplicate = """
py .\\data_sources\\modules\\blog_assembly_bom.py build ^
  --output "provisional.json"
python.exe ./data_sources/modules/publish_readiness.py "article.md" ^
  --phase preflight
py -3 data_sources/modules/blog_assembly_bom.py finalize ^
  --bom "provisional.json"
python ./data_sources/modules/publish_readiness.py "article.md" ^
  --phase final
"""
        self.assertEqual(
            ["build", "preflight", "finalize", "final"],
            _seal_steps(alternate_duplicate),
        )

    def test_blog_route_capabilities_resolve_to_existing_repository_definitions(self):
        capabilities = _repository_capabilities()
        route_paths = [
            ROOT / ".claude" / "commands" / name
            for name in (
                "article.md",
                "research.md",
                "write.md",
                "analyze-existing.md",
                "rewrite.md",
                "scrub.md",
                "optimize.md",
                "publish-readiness.md",
                "publish-draft.md",
            )
        ]
        for path in route_paths:
            references = _route_capability_references(path.read_text(encoding="utf-8"))
            for kind, values in references.items():
                with self.subTest(path=path.name, kind=kind):
                    self.assertTrue(values <= capabilities[kind])

        external = _route_capability_references(
            "Run `/external-orchestrator`\n**Agent**: `external-reviewer`\n**Skill**: `external-skill`"
        )
        for kind, values in external.items():
            self.assertFalse(values <= capabilities[kind])

    def test_publish_readiness_declares_route_specific_build_variants(self):
        content = SEAL_OWNER.read_text(encoding="utf-8")
        self.assertEqual(
            [
                frozenset({"--paa-artifact"}),
                frozenset({"--content-brief"}),
                frozenset({"--user-paa-csv", "--answersocrates-blocker"}),
            ],
            _bom_build_research_input_sets(content),
        )
        self.assertRegex(content, r"--optimizer-output\s+\"\[optimizer-output\]\"")
        self.assertRegex(
            content,
            r"--prior-preflight-readiness\s+\"\[prior-preflight-readiness\]\"",
        )
