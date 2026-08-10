import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RUNTIME_AND_INSTRUCTION_ROOTS = (
    Path(".agents"),
    Path(".claude"),
    Path(".claude-plugin"),
    Path(".codex"),
    Path(".cursor"),
    Path("config"),
    Path("data_sources"),
    Path("docs"),
    Path("mcp-gsc"),
    Path("scripts"),
    Path("tools"),
    Path("wordpress"),
)

GENERATED_PREFIXES = (
    Path(".codex/tmp"),
    Path("data_sources/cache"),
)

GENERATED_DIRECTORY_NAMES = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
}

TEXT_SUFFIXES = {
    ".cfg",
    ".conf",
    ".example",
    ".ini",
    ".json",
    ".jsonl",
    ".lock",
    ".md",
    ".mdc",
    ".php",
    ".ps1",
    ".py",
    ".pyi",
    ".sh",
    ".template",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

ROOT_RUNTIME_FILES = {
    Path(".claude/settings.local.json"),
    Path(".claude/settings.local.template.json"),
    Path(".codex/config.toml"),
    Path(".env.example"),
    Path(".mcp.json"),
    Path(".mcp.json.template"),
}

EXPLICIT_MIGRATION_PREFIXES = (Path("docs/superpowers/plans"),)
EXPLICIT_TEST_FIXTURES = (Path("tests/vault_context_fixture.py"),)

BANNED_TOPOLOGY_PATTERNS = (
    (
        "legacy LLM-wiki label",
        re.compile(r"\bSimpro Brand Context LLM wiki\b", re.IGNORECASE),
    ),
    ("vault wiki route", re.compile(r"\bwiki[\\/]", re.IGNORECASE)),
    ("vault index route", re.compile(r"\bindexes[\\/]", re.IGNORECASE)),
    (
        "vault raw-source route",
        re.compile(
            r"\braw[\\/](?:drive|source-intake|imported-content|extracted)[\\/]",
            re.IGNORECASE,
        ),
    ),
    (
        "legacy vault environment variable",
        re.compile(r"\bSIMPRO_BRAND_CONTEXT_VAULT\b"),
    ),
    (
        "hard-coded Obsidian vault root",
        re.compile(r"[A-Za-z]:[\\/][^\n\"']*Obsidian[\\/]", re.IGNORECASE),
    ),
    (
        "known vault hub or authority title",
        re.compile(
            r"\b(?:Brand Graph Index|Tone Voice and Localization Rules|"
            r"Simpro Core Messaging Repository|Feature Library|Vertical Profile Library)\b"
            r"|\b(?:Voice and Tone|Message House|Core Value Pillars|"
            r"Product Positioning|Competitive Context)\.md\b",
            re.IGNORECASE,
        ),
    ),
    (
        "known vault protocol filename",
        re.compile(
            r"\b(?:agent-(?:claim-registry|retrieval-manifest|"
            r"(?:retrieval-)?search-index)(?:-v\d+)?\.jsonl|"
            r"resource-policy\.json)\b",
            re.IGNORECASE,
        ),
    ),
)

LEGACY_SIDECAR_CONTRACTS = (
    "Vault Context Read Path",
    "Source Routing Decision",
)

MOJIBAKE_SEQUENCES = (
    "\u00c3",
    "\u00c2 ",
    "\u00c2\u00b7",
    "\u00c2\u00a9",
    "\u00c2\u00ae",
    "\u00c2\u00b0",
    "\u00e2\u20ac",
    "\u00e2\u2020",
    "\u00e2\u20ac\u00a2",
    "\u00e2\u2030",
    "\u00ce\u201d",
    "\u00f0\u0178",
    "\u00ef\u00bf\u00bd",
    "\ufffd",
)


@dataclass(frozen=True)
class TextViolation:
    path: Path
    line: int
    label: str
    value: str

    def __str__(self) -> str:
        return f"{self.path.as_posix()}:{self.line}: {self.label}: {self.value}"


def _repository_paths() -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return tuple(Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw)


def _is_under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _is_generated(path: Path) -> bool:
    if any(_is_under(path, prefix) for prefix in GENERATED_PREFIXES):
        return True
    return any(part.lower() in GENERATED_DIRECTORY_NAMES for part in path.parts)


def _is_instruction(path: Path) -> bool:
    if len(path.parts) == 1 and path.suffix.lower() == ".md":
        return True
    if path.parent == Path("context") and path.suffix.lower() == ".md":
        return True
    return any(
        _is_under(path, root)
        for root in (Path(".agents"), Path(".claude"), Path(".cursor"), Path("docs"))
    )


def _is_runtime_or_instruction(path: Path) -> bool:
    if _is_generated(path):
        return False
    if path in ROOT_RUNTIME_FILES:
        return True
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    if _is_instruction(path):
        return True
    return any(_is_under(path, root) for root in RUNTIME_AND_INSTRUCTION_ROOTS)


def _is_explicit_exception(path: Path) -> bool:
    return path in EXPLICIT_TEST_FIXTURES or any(
        _is_under(path, prefix) for prefix in EXPLICIT_MIGRATION_PREFIXES
    )


def _repository_scan_paths() -> tuple[Path, ...]:
    candidates = dict.fromkeys((*_repository_paths(), *ROOT_RUNTIME_FILES))
    return tuple(
        path
        for path in candidates
        if (_is_runtime_or_instruction(path) or path in EXPLICIT_TEST_FIXTURES)
        and (ROOT / path).is_file()
    )


def _read_text(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def _is_allowed_root_configuration(
    label: str, path: Path, text: str, match: re.Match[str]
) -> bool:
    if label != "hard-coded Obsidian vault root" or path not in ROOT_RUNTIME_FILES:
        return False
    line_start = text.rfind("\n", 0, match.start()) + 1
    line_end = text.find("\n", match.end())
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end]
    return bool(
        re.search(
            r"\b(?:authority_root|SIMPRO_VAULT_ROOT)\b|--vault-root\b",
            line,
            re.IGNORECASE,
        )
    )


def _topology_violations_in_text(path: Path, text: str) -> list[TextViolation]:
    violations = []
    for label, pattern in BANNED_TOPOLOGY_PATTERNS:
        for match in pattern.finditer(text):
            if _is_allowed_root_configuration(label, path, text, match):
                continue
            violations.append(
                TextViolation(
                    path=path,
                    line=text.count("\n", 0, match.start()) + 1,
                    label=label,
                    value=match.group(0),
                )
            )
    return violations


def _topology_violations(paths: tuple[Path, ...]) -> list[TextViolation]:
    violations = []
    for path in paths:
        violations.extend(_topology_violations_in_text(path, _read_text(path)))
    return violations


def _mojibake_violations(paths: tuple[Path, ...]) -> list[TextViolation]:
    violations = []
    for path in paths:
        text = _read_text(path)
        for sequence in MOJIBAKE_SEQUENCES:
            start = 0
            while True:
                index = text.find(sequence, start)
                if index < 0:
                    break
                violations.append(
                    TextViolation(
                        path=path,
                        line=text.count("\n", 0, index) + 1,
                        label="mojibake sequence",
                        value=sequence,
                    )
                )
                start = index + len(sequence)
    return violations


def test_repository_runtime_and_instruction_files_do_not_prescribe_vault_topology():
    violations = _topology_violations(_repository_scan_paths())
    unexpected = [
        violation
        for violation in violations
        if not _is_explicit_exception(violation.path)
    ]
    assert unexpected == [], "\n".join(str(violation) for violation in unexpected)


def test_repository_inventory_includes_untracked_runtime_files(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                b"data_sources/modules/tracked.py\0"
                b"data_sources/modules/new_connector.py\0"
            ),
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _repository_paths() == (
        Path("data_sources/modules/tracked.py"),
        Path("data_sources/modules/new_connector.py"),
    )
    assert calls == [
        (
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            {"cwd": ROOT, "check": True, "capture_output": True},
        )
    ]


def test_scan_scope_covers_nested_runtime_prompt_plugin_and_config_surfaces():
    assert _is_runtime_or_instruction(Path("data_sources/modules/nested/connector.py"))
    assert _is_runtime_or_instruction(Path(".claude/skills/example/SKILL.md"))
    assert _is_runtime_or_instruction(Path(".codex/config.toml"))
    assert _is_runtime_or_instruction(Path("config/nested/plugin.json"))


def test_repository_scan_includes_active_ignored_connector_configuration():
    scan_paths = _repository_scan_paths()

    assert Path(".claude/settings.local.json") in scan_paths
    assert Path(".codex/config.toml") in scan_paths
    assert Path(".mcp.json") in scan_paths


def test_known_generated_protocol_filenames_are_topology_violations():
    text = (
        "agent-retrieval-manifest-v2.jsonl\n"
        "agent-retrieval-search-index.jsonl\n"
        "agent-claim-registry.jsonl\n"
        "resource-policy.json\n"
    )

    violations = _topology_violations_in_text(Path("runtime.py"), text)

    assert [violation.line for violation in violations] == [1, 2, 3, 4]
    assert all(
        violation.label == "known vault protocol filename" for violation in violations
    )


def test_allowed_vault_root_configuration_does_not_allow_internal_routes():
    root_only = 'authority_root = "C:\\Users\\example\\Obsidian\\Simpro Brand Context"'
    internal_route = 'authority_root = "C:\\Users\\example\\Obsidian\\Simpro Brand Context\\wiki\\hub.md"'

    assert _topology_violations_in_text(Path(".codex/config.toml"), root_only) == []
    violations = _topology_violations_in_text(
        Path(".codex/config.toml"), internal_route
    )
    assert any(violation.label == "vault wiki route" for violation in violations)


def test_root_configuration_exception_is_not_available_to_runtime_source():
    source = 'authority_root = "C:\\Users\\example\\Obsidian\\Simpro Brand Context"'

    violations = _topology_violations_in_text(
        Path("data_sources/modules/connector.py"), source
    )

    assert [violation.label for violation in violations] == [
        "hard-coded Obsidian vault root"
    ]


def test_scan_scope_excludes_user_content_and_generated_artifacts():
    excluded = (
        Path("published/user-article.md"),
        Path("drafts/user-draft.md"),
        Path("research/generated-report.md"),
        Path("output/generated.json"),
        Path("data_sources/cache/generated.json"),
        Path(".codex/tmp/generated.json"),
        Path("data_sources/modules/__pycache__/connector.pyc"),
    )

    assert all(not _is_runtime_or_instruction(path) for path in excluded)


def test_active_instructions_do_not_require_legacy_route_sidecars():
    violations = []
    for path in _repository_scan_paths():
        if not _is_instruction(path) or _is_explicit_exception(path):
            continue
        text = _read_text(path)
        for contract in LEGACY_SIDECAR_CONTRACTS:
            if contract in text:
                violations.append(
                    f"{path.as_posix()}: legacy sidecar contract: {contract}"
                )
    assert violations == [], "\n".join(violations)


def test_topology_exceptions_are_narrow_and_only_cover_migrations_or_fixtures():
    violations = _topology_violations(_repository_scan_paths())
    allowed = [
        violation for violation in violations if _is_explicit_exception(violation.path)
    ]

    assert allowed, (
        "Expected at least one historical migration example to exercise the exception boundary."
    )
    assert all(
        violation.path in EXPLICIT_TEST_FIXTURES
        or any(
            _is_under(violation.path, prefix) for prefix in EXPLICIT_MIGRATION_PREFIXES
        )
        for violation in allowed
    )
    assert all(
        prefix.parts == ("docs", "superpowers", "plans")
        for prefix in EXPLICIT_MIGRATION_PREFIXES
    )
    assert all(path.parts[:1] == ("tests",) for path in EXPLICIT_TEST_FIXTURES)


def test_repository_runtime_and_instruction_files_are_free_of_mojibake():
    paths = tuple(
        path for path in _repository_scan_paths() if not _is_explicit_exception(path)
    )
    violations = _mojibake_violations(paths)
    assert violations == [], "\n".join(str(violation) for violation in violations)
