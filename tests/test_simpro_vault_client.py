from tests.fixture_text import fixture_text

import json
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest

from data_sources.modules import simpro_vault_client as compatibility
from data_sources.modules.simpro_vault_client import (
    RECOVERY_HINTS,
    SimproVaultClient,
    VaultClientError,
    VaultOperationResult,
)
from simpro_vault import VaultClient


def test_compatibility_module_reexports_the_standalone_client() -> None:
    assert SimproVaultClient is VaultClient
    assert compatibility.VaultClientError is importlib.import_module(
        "simpro_vault"
    ).VaultClientError
    assert compatibility.VaultOperationResult is importlib.import_module(
        "simpro_vault"
    ).VaultOperationResult


def test_client_contract_contains_all_operations_and_recoverable_methods() -> None:
    methods = (
        "dispatch",
        "status",
        "describe",
        "search",
        "read",
        "expand",
        "claims",
        "build_context",
        "validate_context",
        "try_dispatch",
        "try_status",
        "try_describe",
        "try_search",
        "try_read",
        "try_expand",
        "try_claims",
        "try_build_context",
        "try_validate_context",
    )

    def _plugin(self, name: str) -> Path:
        plugin = self.root / name
        (plugin / "scripts").mkdir(parents=True)
        (plugin / "scripts" / "vault_cli.py").write_text("", encoding="utf-8")
        return plugin

    def test_root_resolution_prefers_explicit_then_plugin_config_then_environment(self):
        explicit = self.root / "explicit-vault"
        configured = self.root / "configured-vault"
        environment = self.root / "environment-vault"
        for candidate in (explicit, configured, environment):
            candidate.mkdir()
        settings = self.root / "settings.json"
        settings.write_text(
            json.dumps(
                {
                    "pluginConfigs": {
                        "simpro-context@simpro": {
                            "options": {"authority_root": str(configured)}
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        with patch.dict(
            "os.environ",
            {"SIMPRO_VAULT_ROOT": str(environment)},
            clear=False,
        ):
            self.assertEqual(
                SimproVaultClient(
                    vault_root=explicit,
                    settings_path=settings,
                ).vault_root,
                explicit.resolve(),
            )
            self.assertEqual(
                SimproVaultClient(settings_path=settings).vault_root,
                configured.resolve(),
            )

        settings.write_text("{}", encoding="utf-8")
        with patch.dict(
            "os.environ",
            {"SIMPRO_VAULT_ROOT": str(environment)},
            clear=False,
        ):
            self.assertEqual(
                SimproVaultClient(settings_path=settings).vault_root,
                environment.resolve(),
            )

    def test_discovery_prefers_canonical_simpro_plugin_and_ignores_other_projects(self):
        canonical = self._plugin("canonical")
        other = self._plugin("other-project")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": False,
                    "version": "1.3.0",
                    "installPath": str(other),
                    "projectPath": str(self.root / "other-worktree"),
                },
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.3.0",
                    "installPath": str(canonical),
                    "projectPath": str(Path.cwd()),
                },
            ]
        )
        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            return_value=Completed(stdout=inventory),
        ):
            discovered = discover_plugin()

        self.assertEqual(discovered, canonical.resolve() / "scripts" / "vault_cli.py")

    def test_discovery_uses_owning_repo_when_called_from_nested_directory(self):
        canonical = self._plugin("canonical-nested")
        repo_root = Path(__file__).resolve().parents[1]
        nested = repo_root / "data_sources" / "modules"
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.3.0",
                    "installPath": str(canonical),
                    "projectPath": str(repo_root),
                }
            ]
        )
        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            return_value=Completed(stdout=inventory),
        ), patch("pathlib.Path.cwd", return_value=nested):
            discovered = discover_plugin()

        self.assertEqual(discovered, canonical.resolve() / "scripts" / "vault_cli.py")
    def test_discovery_rejects_single_canonical_plugin_scoped_to_other_project(self):
        foreign = self._plugin("foreign-project")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.3.0",
                    "installPath": str(foreign),
                    "projectPath": str(self.root / "other-worktree"),
                }
            ]
        )

        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            return_value=Completed(stdout=inventory),
        ):
            with self.assertRaises(VaultClientError) as raised:
                discover_plugin()

        self.assertEqual(raised.exception.code, "plugin_missing")

    def test_discovery_rejects_disabled_canonical_plugin_even_when_legacy_exists(self):
        canonical = self._plugin("canonical")
        legacy = self._plugin("legacy")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": False,
                    "version": "1.3.0",
                    "installPath": str(canonical),
                    "projectPath": str(Path.cwd()),
                },
                {
                    "id": "simpro-context@marketingskills",
                    "enabled": True,
                    "version": "1.1.2",
                    "installPath": str(legacy),
                    "projectPath": str(Path.cwd()),
                },
            ]
        )
        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            return_value=Completed(stdout=inventory),
        ):
            with self.assertRaises(VaultClientError) as raised:
                discover_plugin()

        self.assertEqual(raised.exception.code, "plugin_disabled")
        self.assertIn("simpro-context@simpro", str(raised.exception))

    def test_discovery_rejects_missing_enabled_plugin(self):
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": False,
                    "version": "1.3.0",
                    "installPath": str(self.root / "plugin"),
                    "projectPath": str(Path.cwd()),
                }
            ]
        )
        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            return_value=Completed(stdout=inventory),
        ):
            with self.assertRaises(VaultClientError) as raised:
                discover_plugin()

        self.assertEqual(raised.exception.code, "plugin_disabled")

    def test_discovery_timeout_is_stable_and_recoverable(self):
        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["claude"], 15),
        ):
            with self.assertRaises(VaultClientError) as raised:
                discover_plugin()
        self.assertEqual(raised.exception.code, "plugin_discovery_timeout")

    def test_discovery_uses_bounded_strict_utf8_subprocess(self):
        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            return_value=Completed(stdout="[]"),
        ) as run:
            with self.assertRaises(VaultClientError):
                discover_plugin()
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["errors"], "strict")
        self.assertGreater(kwargs["timeout"], 0)

    def test_discovery_uses_current_project_canonical_regardless_of_version(self):
        plugin = self._plugin("plugin")
        legacy = self._plugin("legacy")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.5",
                    "installPath": str(plugin),
                    "projectPath": str(Path.cwd()),
                },
                {
                    "id": "simpro-context@marketingskills",
                    "enabled": True,
                    "version": "1.1.2",
                    "installPath": str(legacy),
                    "projectPath": str(Path.cwd()),
                },
            ]
        )
        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            return_value=Completed(stdout=inventory),
        ):
            discovered = discover_plugin()

        self.assertEqual(discovered, plugin.resolve() / "scripts" / "vault_cli.py")

    def test_discovery_accepts_canonical_without_a_version_field(self):
        plugin = self._plugin("plugin-without-version")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "installPath": str(plugin),
                    "projectPath": str(Path.cwd()),
                }
            ]
        )
        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            return_value=Completed(stdout=inventory),
        ):
            discovered = discover_plugin()

        self.assertEqual(discovered, plugin.resolve() / "scripts" / "vault_cli.py")

    def test_discovery_accepts_canonical_1_3_0(self):
        plugin = self._plugin("plugin")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.3.0",
                    "installPath": str(plugin),
                    "projectPath": str(Path.cwd()),
                }
            ]
        )
        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            return_value=Completed(stdout=inventory),
        ):
            discovered = discover_plugin()

        self.assertEqual(discovered, plugin.resolve() / "scripts" / "vault_cli.py")

    def test_status_rejects_unhealthy_or_incomplete_connector(self):
        vault = self.root / "vault"
        vault.mkdir()
        client = SimproVaultClient(vault_root=vault)
        with patch.object(
            client,
            "dispatch",
            return_value={
                "status": "ready",
                "root_configured": True,
                "revisions": {
                    "claim_registry_revision": "claims",
                    "content_revision": "content",
                    "contract_revision": "contract",
                    "inventory_revision": "inventory",
                    "manifest_revision": "manifest",
                },
            },
        ):
            with self.assertRaises(VaultClientError) as raised:
                client.status()

        self.assertEqual(raised.exception.code, "plugin_unhealthy")

    def _ready_status(self):
        return {
            "status": "ready",
            "root_configured": True,
            "revisions": {
                "approval_policy_revision": "policy",
                "claim_registry_revision": "claims",
                "content_revision": "content",
                "contract_revision": "contract",
                "inventory_revision": "inventory",
                "manifest_revision": "manifest",
            },
            "claim_health": {
                "claim_count": 12,
                "proof_retrieval_state": "available",
                "approved_brand_scope_counts": {"Simpro": 4},
            },
            "resource_access": {
                "manifest_resources": 10,
                "searchable_resources": 10,
                "indexed_resources": 9,
                "declared_unindexed_resources": 1,
                "context_readable_resources": 10,
            },
        }

    def test_status_rejects_zero_approved_simpro_claims(self):
        vault = self.root / "vault-zero-claims"
        vault.mkdir()
        status = self._ready_status()
        status["claim_health"]["approved_brand_scope_counts"]["Simpro"] = 0
        client = SimproVaultClient(vault_root=vault)
        with patch.object(client, "dispatch", return_value=status):
            with self.assertRaises(VaultClientError) as raised:
                client.status()

        self.assertEqual(raised.exception.code, "vault_claims_unavailable")

    def test_status_rejects_partial_manifest_discovery(self):
        vault = self.root / "vault-partial-search"
        vault.mkdir()
        status = self._ready_status()
        status["resource_access"]["searchable_resources"] = 9
        client = SimproVaultClient(vault_root=vault)
        with patch.object(client, "dispatch", return_value=status):
            with self.assertRaises(VaultClientError) as raised:
                client.status()

        self.assertEqual(raised.exception.code, "vault_discovery_incomplete")

    def test_status_accepts_complete_discovery_and_claim_health(self):
        vault = self.root / "vault-healthy"
        vault.mkdir()
        status = self._ready_status()
        client = SimproVaultClient(vault_root=vault)
        with patch.object(client, "dispatch", return_value=status):
            self.assertIs(client.status(), status)
    def test_recoverable_dispatch_returns_stable_hint_instead_of_raising(self):
        vault = self.root / "vault"
        vault.mkdir()
        client = SimproVaultClient(vault_root=vault)
        with patch.object(
            client,
            "dispatch",
            side_effect=VaultClientError("resource_missing", "Resource moved"),
        ):
            result = client.try_read("res-moved")

        self.assertFalse(result.ok)
        self.assertEqual(result.operation, "vault_read")
        self.assertEqual(result.error, {"code": "resource_missing", "message": "Resource moved"})
        self.assertIn("search", result.recovery_hint.lower())

    def test_dispatch_executes_the_discovered_shared_cli(self):
        plugin = self.root / "plugin"
        scripts = plugin / "scripts"
        scripts.mkdir(parents=True)
        cli = scripts / "vault_cli.py"
        cli.write_text(
            fixture_text("sealed_workflows:test_simpro_vault_client-470-1").strip(),
            encoding="utf-8",
        )
        vault = self.root / "renamed-vault"
        vault.mkdir()
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.3.0",
                    "installPath": str(plugin),
                    "projectPath": str(Path.cwd()),
                }
            ]
        )
        real_run = __import__("subprocess").run

        def run(command, **kwargs):
            if command[:3] == ["claude", "plugin", "list"]:
                return Completed(stdout=inventory)
            return real_run(command, **kwargs)

        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            side_effect=run,
        ):
            client = SimproVaultClient(
                vault_root=vault,
                python_executable=sys.executable,
            )
            result = client.search("field service scheduling", limit=4)
            expanded = client.expand(
                "res-alpha",
                relation_types=["links_to"],
                purpose="context",
            )
            proof = client.find_proof(
                {
                    "task": "Find homepage trust proof",
                    "scope": {"brand": "Simpro"},
                    "query": "field service management metrics",
                },
                count=7,
                source_type_counts={"case_study": 5, "review": 2},
                metric_classes=["customer_outcome"],
                required_fields=["industry", "public_url"],
                max_per_subject=1,
            )

        self.assertEqual(result["operation"], "vault_search")
        self.assertEqual(
            result["payload"],
            {"query": "field service scheduling", "limit": 4},
        )
        self.assertEqual(Path(result["vault_root"]).resolve(), vault.resolve())
        self.assertEqual(expanded["operation"], "vault_expand")
        self.assertEqual(
            expanded["payload"],
            {
                "resource_id": "res-alpha",
                "relation_types": ["links_to"],
                "purpose": "context",
            },
        )
        self.assertEqual(proof["operation"], "vault_find_proof")
        self.assertEqual(
            proof["payload"],
            {
                "request": {
                    "task": "Find homepage trust proof",
                    "scope": {"brand": "Simpro"},
                    "query": "field service management metrics",
                },
                "count": 7,
                "source_type_counts": {"case_study": 5, "review": 2},
                "metric_classes": ["customer_outcome"],
                "required_fields": ["industry", "public_url"],
                "max_per_subject": 1,
            },
        )

    def test_dispatch_preserves_connector_error_code(self):
        plugin = self.root / "plugin"
        scripts = plugin / "scripts"
        scripts.mkdir(parents=True)
        cli = scripts / "vault_cli.py"
        cli.write_text(
            fixture_text("sealed_workflows:test_simpro_vault_client-545-2").strip(),
            encoding="utf-8",
        )
        vault = self.root / "vault"
        vault.mkdir()
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.3.0",
                    "installPath": str(plugin),
                    "projectPath": str(Path.cwd()),
                }
            ]
        )
        real_run = __import__("subprocess").run

        def run(command, **kwargs):
            if command[:3] == ["claude", "plugin", "list"]:
                return Completed(stdout=inventory)
            return real_run(command, **kwargs)

        with patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            side_effect=run,
        ):
            with self.assertRaises(VaultClientError) as raised:
                SimproVaultClient(vault_root=vault).status()

        self.assertEqual(raised.exception.code, "pack_stale")
        self.assertEqual(str(raised.exception), "stale")

    def test_dispatch_timeout_returns_stable_recovery_result_and_cleans_tempdir(self):
        vault = self.root / "vault-timeout"
        vault.mkdir()
        cli = self.root / "vault_cli.py"
        cli.write_text("", encoding="utf-8")
        client = SimproVaultClient(vault_root=vault)
        client._cli = cli
        temporary_parent = self.root / "temporary"
        temporary_parent.mkdir()
        with patch("tempfile.tempdir", str(temporary_parent)), patch(
            "data_sources.modules.simpro_vault_client.subprocess.run",
            side_effect=subprocess.TimeoutExpired([sys.executable], 45),
        ):
            result = client.try_search("scheduling")
        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "connector_timeout")
        self.assertEqual(list(temporary_parent.iterdir()), [])

    def test_connector_timeout_is_operation_aware(self):
        plugin = self.root / "plugin"
        scripts = plugin / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "vault_cli.py").write_text("", encoding="utf-8")
        vault = self.root / "vault"
        vault.mkdir()
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.3.0",
                    "installPath": str(plugin),
                    "projectPath": str(Path.cwd()),
                }
            ]
        )
        cases = (
            ("search", lambda client: client.search("scheduling"), 45),
            (
                "find_proof",
                lambda client: client.find_proof(
                    {
                        "task": "Find homepage proof",
                        "scope": {"brand": "Simpro"},
                        "query": "metrics",
                    }
                ),
                180,
            ),
            (
                "validate",
                lambda client: client.validate_context(
                    {"task": "t"}, {"schema": "p"}, {"schema": "r"}
                ),
                180,
            ),
        )
        for name, call_client, expected_timeout in cases:
            with self.subTest(name=name):
                calls = []

                def run(command, **kwargs):
                    calls.append((command, kwargs))
                    if command[:3] == ["claude", "plugin", "list"]:
                        return Completed(stdout=inventory)
                    result = {"valid": True, "errors": []} if name == "validate" else []
                    return Completed(stdout=json.dumps({"ok": True, "result": result}))

                with patch(
                    "data_sources.modules.simpro_vault_client.subprocess.run",
                    side_effect=run,
                ):
                    call_client(SimproVaultClient(vault_root=vault))

                self.assertEqual(calls[-1][1]["timeout"], expected_timeout)

    def test_moved_descriptor_and_resource_keep_stable_resource_id(self):
        vault = self.root / "fixture-vault"
        (vault / "protocol").mkdir(parents=True)
        (vault / "content-a").mkdir()
        descriptor = vault / "descriptor-a.json"
        manifest = vault / "protocol" / "manifest.json"
        resource = vault / "content-a" / "guide.md"
        descriptor.write_text(json.dumps({"schema": "simpro-retrieval-bootstrap/v1", "manifest": "protocol/manifest.json"}), encoding="utf-8")
        resource.write_text("# Scheduling guidance\n\nCoordinate field work.", encoding="utf-8")
        manifest.write_text(json.dumps({"resources": [{"resource_id": "res-stable-scheduling", "title": "Scheduling guidance", "locator": "content-a/guide.md"}]}), encoding="utf-8")
        cli = self.root / "fixture_vault_cli.py"
        cli.write_text(
            fixture_text("sealed_workflows:test_simpro_vault_client-613-3").strip(),
            encoding="utf-8",
        )
        client = SimproVaultClient(vault_root=vault, python_executable=sys.executable)
        client._cli = cli
        self.assertEqual(client.search("scheduling")[0]["resource_id"], "res-stable-scheduling")
        self.assertEqual(client.read("res-stable-scheduling")["resource_id"], "res-stable-scheduling")

        (vault / "metadata-renamed").mkdir()
        descriptor.rename(vault / "metadata-renamed" / "bootstrap-any-name.json")
        (vault / "content-b").mkdir()
        moved_resource = resource.rename(vault / "content-b" / "renamed-anything.md")
        manifest.write_text(json.dumps({"resources": [{"resource_id": "res-stable-scheduling", "title": "Scheduling guidance", "locator": str(moved_resource.relative_to(vault)).replace("\\", "/")}]}), encoding="utf-8")

        self.assertEqual(client.search("scheduling")[0]["resource_id"], "res-stable-scheduling")
        self.assertEqual(client.read("res-stable-scheduling")["resource_id"], "res-stable-scheduling")


def test_client_resolves_explicit_root_before_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit = tmp_path / "explicit"
    environment = tmp_path / "environment"
    explicit.mkdir()
    environment.mkdir()
    monkeypatch.setenv("SIMPRO_VAULT_ROOT", str(environment))

    client = SimproVaultClient(explicit)

    assert client.vault_root == explicit.resolve()


def test_client_resolves_environment_without_claude_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vault = tmp_path / "environment"
    vault.mkdir()
    monkeypatch.setenv("SIMPRO_VAULT_ROOT", str(vault))

    client = SimproVaultClient()

    assert client.vault_root == vault.resolve()


def test_client_fails_closed_when_root_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIMPRO_VAULT_ROOT", raising=False)

    with pytest.raises(VaultClientError) as raised:
        SimproVaultClient()

    assert raised.value.code == "root_unset"
    assert "SIMPRO_VAULT_ROOT" in str(raised.value)


def test_recoverable_result_preserves_stable_error_and_hint(
    tmp_path: Path,
) -> None:
    client = SimproVaultClient(tmp_path)

    result = client.try_status()

    assert isinstance(result, VaultOperationResult)
    assert result.ok is False
    assert result.operation == "vault_status"
    assert result.error and result.error["code"] == "bootstrap_not_found"
    assert result.recovery_hint == RECOVERY_HINTS["bootstrap_not_found"]


def test_runtime_module_has_no_claude_inventory_or_subprocess_dispatch() -> None:
    source = inspect.getsource(compatibility).casefold()

    assert "discover_plugin" not in source
    assert "claude" not in source
    assert "subprocess" not in source
    assert "tempfile" not in source
    assert "settings.json" not in source


def test_dependency_is_pinned_to_immutable_v2_release() -> None:
    root = Path(__file__).resolve().parents[1]
    requirements = (root / "data_sources" / "requirements.txt").read_text(
        encoding="utf-8"
    )

    assert (
        "simpro-vault-connector @ "
        "git+https://github.com/Simpro-Group-Marketing/"
        "simpro-context-connector.git@v2.0.0"
    ) in requirements


def test_mcp_template_invokes_the_standalone_module() -> None:
    root = Path(__file__).resolve().parents[1]
    template = (root / ".mcp.json.template").read_text(encoding="utf-8")

    assert "simpro-vault" in template
    assert "simpro_vault.mcp" in template
    assert "SIMPRO_VAULT_ROOT" in template
    assert "CLAUDE_PLUGIN_ROOT" not in template


def test_readme_uses_the_current_default_branch_workflow() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")

    assert "custom/local-context" not in readme
    assert "feature branches targeting `main`" in readme
