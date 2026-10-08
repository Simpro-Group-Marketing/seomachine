"""Guard against force-added research artifacts, secrets, and plugin scratch."""

import fnmatch
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# research/ is gitignored working state. Only these paths may be tracked:
# the placeholder that keeps the directory, and the benchmarks that the
# root MEMORY.md links (tools/check_memory_contract.py requires them tracked).
TRACKED_RESEARCH_ALLOWLIST = {
    "research/.gitkeep",
    "research/performance/p2-offline-release-benchmark-v3.json",
    "research/performance/p2-test-sharding-benchmark.json",
}


def _tracked(*pathspec: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", *pathspec],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_only_allowlisted_research_paths_are_tracked():
    unexpected = sorted(set(_tracked("research")) - TRACKED_RESEARCH_ALLOWLIST)
    assert unexpected == [], f"research/ artifacts must stay untracked: {unexpected[:10]}"


def test_no_secrets_are_tracked():
    offenders = []
    for path in _tracked():
        name = path.rsplit("/", 1)[-1]
        if fnmatch.fnmatch(name, "client_secret_*"):
            offenders.append(path)
        elif path.startswith("credentials/") and path != "credentials/.gitkeep":
            offenders.append(path)
        elif name.startswith(".env") and name != ".env.example":
            offenders.append(path)
        elif fnmatch.fnmatch(name, "*.env") and name != ".env.example":
            offenders.append(path)
    assert offenders == [], f"secret-like files are tracked: {offenders}"


def test_plugin_scratch_is_not_tracked():
    assert _tracked(".superpowers") == []
