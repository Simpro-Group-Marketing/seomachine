import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _read(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def _job(content: str, job: str) -> str:
    match = re.search(rf"^  {re.escape(job)}:\n(.*?)(?=^  \S|\Z)", content, re.M | re.S)
    assert match, f"job {job!r} not found"
    return match.group(1)


def test_full_suite_workflow_runs_every_test_with_runtime_dependencies():
    """Dropping the full suite, the runtime install, or a repo gate must make this fail."""
    content = _read("tests.yml")

    assert "pull_request:" in content
    assert "branches:\n      - main" in content
    assert "pip install -r data_sources/requirements.txt -r requirements-dev.txt" in content
    assert "python -m ruff check ." in content
    assert "python tools/check_python_structure.py" in content
    assert "python tools/sync_rule_mirrors.py --check" in content
    assert "python tools/check_memory_contract.py" in content
    suite = re.search(r"python -m pytest -q -n 4 -p no:cacheprovider\s*$", content, re.M)
    assert suite, "full suite must run without a test-file allowlist"


def test_full_suite_workflow_fails_loudly_without_connector_token():
    """A fork or missing secret must not pass with the vault-dependent tests uncollected."""
    content = _read("tests.yml")

    assert "SIMPRO_CONNECTOR_TOKEN: ${{ secrets.SIMPRO_CONNECTOR_TOKEN }}" in content
    assert 'echo "missing SIMPRO_CONNECTOR_TOKEN"' in content
    assert "exit 1" in content
    assert "insteadOf" in content
    assert "${{ secrets.SIMPRO_CONNECTOR_TOKEN }}@" not in content


def test_contract_and_humanizer_jobs_install_runtime_dependencies():
    """check_memory_contract imports requests; pytest jobs need their runtime deps."""
    p2 = _read("p2-runtime-quality.yml")
    compatibility = _job(_read("humanizer-upstream.yml"), "compatibility")

    assert "data_sources/requirements.txt" in p2
    assert "grep -v simpro-vault-connector data_sources/requirements.txt" in p2
    assert "pip install -r data_sources/requirements.txt -r requirements-dev.txt" in compatibility
    assert "SIMPRO_CONNECTOR_TOKEN" in compatibility


def test_all_workflows_pin_official_actions_to_full_shas():
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        uses = re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@([^\s]+)", workflow.read_text(encoding="utf-8"))
        assert uses, workflow.name
        for action, revision in uses:
            assert re.fullmatch(r"[0-9a-f]{40}", revision), f"{workflow.name}: {action}@{revision}"
