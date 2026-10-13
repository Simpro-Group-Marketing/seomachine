import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
RUNTIME_WITHOUT_CONNECTOR = "grep -v simpro-vault-connector data_sources/requirements.txt"


def _read(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def _job(content: str, job: str) -> str:
    match = re.search(rf"^  {re.escape(job)}:\n(.*?)(?=^  \S|\Z)", content, re.M | re.S)
    assert match, f"job {job!r} not found"
    return match.group(1)


def test_ci_never_needs_the_local_vault_connector():
    """The blog writer reaches the vault through a locally installed connector; CI must not."""
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        content = workflow.read_text(encoding="utf-8")
        assert "SIMPRO_CONNECTOR_TOKEN" not in content, workflow.name
        assert "insteadOf" not in content, workflow.name
        if "data_sources/requirements.txt" in content:
            assert RUNTIME_WITHOUT_CONNECTOR in content, workflow.name


def test_full_suite_runs_locally_not_in_ci():
    """Vault-dependent tests need the local connector, so no workflow runs the whole suite."""
    assert not (WORKFLOWS / "tests.yml").exists()
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        jobs = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]
        for job in jobs.values():
            for step in job.get("steps", []):
                run = step.get("run", "")
                if "python -m pytest" in run:
                    assert "tests/" in run, f"{workflow.name}: {step.get('name')} runs an unscoped suite"


def test_p2_runs_the_connector_free_repository_gates():
    """check_memory_contract imports requests; lint and mirror drift must be gated in CI."""
    p2 = _read("p2-runtime-quality.yml")

    assert RUNTIME_WITHOUT_CONNECTOR in p2
    for gate in (
        "python -m ruff check .",
        "python tools/check_python_structure.py",
        "python tools/sync_rule_mirrors.py --check",
        "python tools/check_memory_contract.py",
    ):
        assert gate in p2


def test_humanizer_compatibility_installs_connector_free_runtime():
    compatibility = _job(_read("humanizer-upstream.yml"), "compatibility")

    assert RUNTIME_WITHOUT_CONNECTOR in compatibility
    assert "-r requirements-dev.txt" in compatibility
    for vault_dependent in ("tests/test_publish_readiness.py", "tests/test_content_scorer_aeo_geo_gate.py"):
        assert vault_dependent not in compatibility


def test_all_workflows_pin_official_actions_to_full_shas():
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        uses = re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@([^\s]+)", workflow.read_text(encoding="utf-8"))
        assert uses, workflow.name
        for action, revision in uses:
            assert re.fullmatch(r"[0-9a-f]{40}", revision), f"{workflow.name}: {action}@{revision}"
