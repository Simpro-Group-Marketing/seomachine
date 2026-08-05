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

    def test_discovery_prefers_canonical_simpro_plugin_and_ignores_other_projects(self):
        canonical = self._plugin("canonical")
        other = self._plugin("other-project")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": False,
                    "version": "1.2.2",
                    "installPath": str(other),
                    "projectPath": str(self.root / "other-worktree"),
                },
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.2",
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

    def test_discovery_rejects_disabled_canonical_plugin_even_when_legacy_exists(self):
        canonical = self._plugin("canonical")
        legacy = self._plugin("legacy")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": False,
                    "version": "1.2.2",
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
                    "version": "1.2.2",
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

    def test_discovery_rejects_outdated_plugin(self):
        plugin = self._plugin("plugin")
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.1",
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
            """
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("operation")
parser.add_argument("--input-file")
parser.add_argument("--vault-root")
args = parser.parse_args()
payload = json.loads(open(args.input_file, encoding="utf-8").read())
print(json.dumps({"ok": True, "result": {
    "operation": args.operation,
    "payload": payload,
    "vault_root": args.vault_root,
}}))
""".strip(),
            encoding="utf-8",
        )
        vault = self.root / "renamed-vault"
        vault.mkdir()
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.2",
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
            result = SimproVaultClient(
                vault_root=vault,
                python_executable=sys.executable,
            ).search("field service scheduling", limit=4)

        self.assertEqual(result["operation"], "vault_search")
        self.assertEqual(
            result["payload"],
            {"query": "field service scheduling", "limit": 4},
        )
        self.assertEqual(Path(result["vault_root"]).resolve(), vault.resolve())

    def test_dispatch_preserves_connector_error_code(self):
        plugin = self.root / "plugin"
        scripts = plugin / "scripts"
        scripts.mkdir(parents=True)
        cli = scripts / "vault_cli.py"
        cli.write_text(
            """
import json
import sys
print(json.dumps({"ok": False, "error": {"code": "pack_stale", "message": "stale"}}), file=sys.stderr)
raise SystemExit(1)
""".strip(),
            encoding="utf-8",
        )
        vault = self.root / "vault"
        vault.mkdir()
        inventory = json.dumps(
            [
                {
                    "id": "simpro-context@simpro",
                    "enabled": True,
                    "version": "1.2.2",
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
            """
import argparse, json
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('operation'); p.add_argument('--input-file'); p.add_argument('--vault-root'); a=p.parse_args()
root=Path(a.vault_root); payload=json.loads(Path(a.input_file).read_text(encoding='utf-8'))
descriptors=[]
for candidate in root.rglob('*.json'):
    try: value=json.loads(candidate.read_text(encoding='utf-8'))
    except Exception: continue
    if isinstance(value,dict) and value.get('schema')=='simpro-retrieval-bootstrap/v1': descriptors.append(value)
if len(descriptors)!=1: print(json.dumps({'ok':False,'error':{'code':'bootstrap_ambiguous','message':'bootstrap count'}})); raise SystemExit(1)
manifest=json.loads((root/descriptors[0]['manifest']).read_text(encoding='utf-8')); rows=manifest['resources']
if a.operation=='vault_search':
    query=payload['query'].casefold(); result=[{'resource_id':r['resource_id']} for r in rows if query in (r['title']+' '+(root/r['locator']).read_text(encoding='utf-8')).casefold()]
elif a.operation=='vault_read':
    row=next(r for r in rows if r['resource_id']==payload['resource_id']); result={'resource_id':row['resource_id'],'content':(root/row['locator']).read_text(encoding='utf-8')}
else: result={}
print(json.dumps({'ok':True,'result':result}))
""".strip(),
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
