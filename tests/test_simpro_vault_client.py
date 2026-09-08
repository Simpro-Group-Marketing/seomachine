from tests.fixture_text import fixture_text

import json
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch

from data_sources.modules.simpro_vault_client import (
    SimproVaultClient,
    VaultClientError,
    discover_plugin,
)


class Completed:
    def __init__(self, *, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class SimproVaultClientTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

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
                    "version": "1.2.10",
                    "installPath": str(other),
                    "projectPath": str(self.root / "other-worktree"),
                },
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.10",
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
                    "version": "1.2.10",
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
                    "version": "1.2.10",
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
                    "version": "1.2.10",
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
                    "version": "1.2.10",
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

    def test_discovery_rejects_canonical_1_2_5_even_when_legacy_is_valid(self):
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
            with self.assertRaises(VaultClientError) as raised:
                discover_plugin()

        self.assertEqual(raised.exception.code, "plugin_outdated")

    def test_discovery_rejects_canonical_1_2_6(self):
        plugin = self._plugin("plugin")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.6",
                    "installPath": str(plugin),
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

        self.assertEqual(raised.exception.code, "plugin_outdated")

    def test_discovery_rejects_canonical_1_2_7(self):
        plugin = self._plugin("plugin")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.7",
                    "installPath": str(plugin),
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

        self.assertEqual(raised.exception.code, "plugin_outdated")

    def test_discovery_rejects_canonical_1_2_8(self):
        plugin = self._plugin("plugin-1-2-8")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.8",
                    "installPath": str(plugin),
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

        self.assertEqual(raised.exception.code, "plugin_outdated")
    def test_discovery_rejects_canonical_1_2_9(self):
        plugin = self._plugin("plugin-1-2-9")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.9",
                    "installPath": str(plugin),
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

        self.assertEqual(raised.exception.code, "plugin_outdated")
    def test_discovery_accepts_canonical_1_2_10(self):
        plugin = self._plugin("plugin")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.10",
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
                    "version": "1.2.10",
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
                    "version": "1.2.10",
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


if __name__ == "__main__":
    unittest.main()
