"""Thin client for the installed topology-agnostic Simpro vault connector.

This module discovers the enabled Claude plugin and delegates every operation
to its shared ``vault_cli.py`` implementation. It contains no vault topology
or retrieval implementation of its own.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


CANONICAL_PLUGIN_ID = "simpro-context@simpro"
LEGACY_PLUGIN_ID = "simpro-context@marketingskills"
MINIMUM_PLUGIN_VERSIONS = {
    CANONICAL_PLUGIN_ID: (1, 3, 0),
    LEGACY_PLUGIN_ID: (1, 1, 2),
}
ROOT_ENVIRONMENT_VARIABLE = "SIMPRO_VAULT_ROOT"
CLAUDE_SETTINGS_RELATIVE_PATH = Path(".claude") / "settings.json"
REQUIRED_STATUS_REVISIONS = (
    "approval_policy_revision",
    "claim_registry_revision",
    "content_revision",
    "contract_revision",
    "inventory_revision",
    "manifest_revision",
)
OPERATIONS = (
    "vault_status",
    "vault_describe",
    "vault_search",
    "vault_read",
    "vault_expand",
    "vault_claims",
    "vault_find_proof",
    "vault_build_context",
    "vault_validate_context",
)
PLUGIN_DISCOVERY_TIMEOUT_SECONDS = 15
CONNECTOR_TIMEOUT_SECONDS = 45
LONG_CONNECTOR_TIMEOUT_SECONDS = 180
LONG_CONNECTOR_TIMEOUT_OPERATIONS = frozenset(
    {"vault_find_proof", "vault_build_context", "vault_validate_context"}
)
OWNING_REPO_ROOT = Path(__file__).resolve().parents[2]


class VaultClientError(RuntimeError):
    """Stable error raised when connector discovery or dispatch fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VaultOperationResult:
    """Non-throwing connector result for recovery-capable agent workflows."""

    ok: bool
    operation: str
    result: Any = None
    error: dict[str, str] | None = None
    recovery_hint: str | None = None


RECOVERY_HINTS = {
    "plugin_discovery_failed": "Check that the Claude CLI is installed, then retry plugin discovery.",
    "plugin_discovery_timeout": "Retry plugin discovery; if it repeats, run the one-root plugin setup and health check.",
    "plugin_inventory_encoding_invalid": "Repair or reinstall the plugin inventory, then retry discovery.",
    "plugin_inventory_invalid": "Repair the Claude plugin inventory, then retry discovery.",
    "plugin_missing": "Run the canonical one-root configure_simpro_context.ps1 -VaultRoot <vault-root> setup, then retry.",
    "plugin_disabled": "Run the canonical one-root configure_simpro_context.ps1 -VaultRoot <vault-root> setup, then retry.",
    "plugin_ambiguous": "Remove duplicate simpro-context installations, then retry.",
    "plugin_outdated": "Run the canonical one-root configure_simpro_context.ps1 -VaultRoot <vault-root> setup to update the plugin, then retry.",
    "plugin_cli_missing": "Run the canonical one-root configure_simpro_context.ps1 -VaultRoot <vault-root> setup to reinstall the plugin, then retry.",
    "plugin_unhealthy": "Run vault_status after rebuilding the vault-owned protocol artifacts.",
    "vault_claims_unavailable": "Restore approved Simpro claim health, rebuild vault artifacts, and retry vault_status.",
    "vault_discovery_incomplete": "Rebuild the vault manifest and search index until every manifest resource is discoverable.",
    "root_unset": "Configure only the vault root with --vault-root or SIMPRO_VAULT_ROOT.",
    "root_unavailable": "Restore access to the configured vault root, then retry vault_status.",
    "resource_missing": "Run vault_search again and read a current result by resource ID.",
    "resource_not_allowed": "Search for an eligible resource with the same semantic purpose.",
    "unsupported_media": "Search for a supported text resource or follow a declared relationship.",
    "resource_too_large": "Search for a smaller related resource or use a more specific result.",
    "claim_missing": "Refine vault_claims and omit the unsupported public passage if no claim exists.",
    "claim_not_approved": "Omit the unsupported public passage and search for approved evidence.",
    "claim_scope_mismatch": "Search claims again with the intended supported brand scope.",
    "proof_profile_invalid": "Repair proof-source-profile-matrix.csv, rebuild vault artifacts, and retry proof retrieval.",
    "invalid_arguments": "Correct the operation arguments using vault_describe, then retry.",
    "manifest_stale": "Rebuild vault-owned protocol artifacts, then retry vault_status.",
    "revision_changed": "Restart discovery from vault_status and rebuild the context pack.",
    "pack_stale": "Rebuild and revalidate the context pack against current vault revisions.",
    "connector_timeout": "Retry the operation; if it repeats, run vault_status and rebuild stale vault-owned indexes.",
    "connector_response_encoding_invalid": "Repair or reinstall the shared connector, then retry vault_status.",
}


def discover_plugin(*, claude_command: str = "claude") -> Path:
    """Return the CLI path for the one enabled Simpro context plugin."""
    try:
        result = subprocess.run(
            [claude_command, "plugin", "list", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            check=False,
            timeout=PLUGIN_DISCOVERY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise VaultClientError(
            "plugin_discovery_timeout",
            "Claude plugin discovery timed out",
        ) from error
    except UnicodeError as error:
        raise VaultClientError(
            "plugin_inventory_encoding_invalid",
            "Claude plugin inventory is not valid UTF-8",
        ) from error
    except OSError as error:
        raise VaultClientError(
            "plugin_discovery_failed",
            f"Claude plugin inventory is unavailable: {error}",
        ) from error
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Plugin inventory failed"
        raise VaultClientError("plugin_discovery_failed", message)
    try:
        inventory = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise VaultClientError(
            "plugin_inventory_invalid",
            "Claude plugin inventory is not valid JSON",
        ) from error
    if not isinstance(inventory, list):
        raise VaultClientError(
            "plugin_inventory_invalid",
            "Claude plugin inventory must be an array",
        )
    canonical_matches = _plugin_matches(inventory, CANONICAL_PLUGIN_ID)
    if canonical_matches:
        return _validate_plugin_matches(canonical_matches, CANONICAL_PLUGIN_ID)
    legacy_matches = _plugin_matches(inventory, LEGACY_PLUGIN_ID)
    if not legacy_matches:
        raise VaultClientError(
            "plugin_missing",
            f"Required plugin is not installed: {CANONICAL_PLUGIN_ID}",
        )
    return _validate_plugin_matches(legacy_matches, LEGACY_PLUGIN_ID)


def _plugin_matches(inventory: Sequence[Any], plugin_id: str) -> list[dict[str, Any]]:
    matches = [item for item in inventory if isinstance(item, dict) and item.get("id") == plugin_id]
    current_project_matches = [
        item
        for item in matches
        if _is_current_project_plugin(
            item.get("projectPath"),
            project_root=OWNING_REPO_ROOT,
        )
    ]
    if current_project_matches:
        return current_project_matches
    global_matches = [
        item
        for item in matches
        if "projectPath" not in item or not isinstance(item.get("projectPath"), str)
    ]
    return global_matches


def _is_current_project_plugin(
    project_path: Any,
    *,
    project_root: Path,
) -> bool:
    if not isinstance(project_path, str) or not project_path.strip():
        return False
    try:
        configured = os.path.normcase(str(Path(project_path).expanduser().resolve()))
        owning_root = os.path.normcase(str(project_root.resolve()))
        return configured == owning_root
    except OSError:
        return False


def _validate_plugin_matches(
    matches: Sequence[Mapping[str, Any]],
    plugin_id: str,
) -> Path:
    if len(matches) != 1:
        raise VaultClientError(
            "plugin_ambiguous",
            f"Required plugin resolves more than once: {plugin_id}",
        )
    plugin = matches[0]
    if plugin.get("enabled") is not True:
        raise VaultClientError(
            "plugin_disabled",
            f"Required plugin is disabled: {plugin_id}",
        )
    version = plugin.get("version")
    minimum_version = MINIMUM_PLUGIN_VERSIONS[plugin_id]
    if not isinstance(version, str) or _version_tuple(version) < minimum_version:
        raise VaultClientError(
            "plugin_outdated",
            f"Required plugin {plugin_id} must be version {'.'.join(map(str, minimum_version))} or newer",
        )
    install_path = plugin.get("installPath")
    if not isinstance(install_path, str) or not install_path.strip():
        raise VaultClientError(
            "plugin_inventory_invalid",
            "Enabled plugin has no install path",
        )
    cli = Path(install_path).resolve() / "scripts" / "vault_cli.py"
    if not cli.is_file():
        raise VaultClientError(
            "plugin_cli_missing",
            f"Installed plugin CLI is unavailable: {cli}",
        )
    return cli


def _connector_timeout(operation: str) -> int:
    if operation in LONG_CONNECTOR_TIMEOUT_OPERATIONS:
        return LONG_CONNECTOR_TIMEOUT_SECONDS
    return CONNECTOR_TIMEOUT_SECONDS


class SimproVaultClient:
    """Dispatch read-only operations through the installed shared connector."""

    def __init__(
        self,
        *,
        vault_root: str | Path | None = None,
        settings_path: str | Path | None = None,
        claude_command: str = "claude",
        python_executable: str | Path = sys.executable,
    ) -> None:
        configured = _configured_vault_root(
            vault_root,
            settings_path=settings_path,
        )
        if configured is None or not str(configured).strip():
            raise VaultClientError(
                "root_unset",
                f"Configure the vault root with --vault-root or {ROOT_ENVIRONMENT_VARIABLE}",
            )
        root = Path(configured).expanduser().resolve()
        if not root.is_dir():
            raise VaultClientError(
                "root_unavailable",
                f"Configured vault root is unavailable: {root}",
            )
        self.vault_root = root
        self.claude_command = claude_command
        self.python_executable = str(python_executable)
        self._cli: Optional[Path] = None

    def dispatch(self, operation: str, arguments: Mapping[str, Any] | None = None) -> Any:
        if operation not in OPERATIONS:
            raise VaultClientError("operation_unknown", f"Unknown vault operation: {operation}")
        payload = dict(arguments or {})
        cli = self._cli or discover_plugin(claude_command=self.claude_command)
        self._cli = cli
        with tempfile.TemporaryDirectory(prefix="simpro-vault-client-") as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            input_path.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            try:
                result = subprocess.run(
                    [
                        self.python_executable,
                        str(cli),
                        operation,
                        "--input-file",
                        str(input_path),
                        "--vault-root",
                        str(self.vault_root),
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="strict",
                    check=False,
                    timeout=_connector_timeout(operation),
                )
            except subprocess.TimeoutExpired as error:
                raise VaultClientError(
                    "connector_timeout",
                    f"Shared connector operation timed out: {operation}",
                ) from error
            except UnicodeError as error:
                raise VaultClientError(
                    "connector_response_encoding_invalid",
                    "Shared connector output is not valid UTF-8",
                ) from error
            except OSError as error:
                raise VaultClientError(
                    "connector_unavailable",
                    f"Shared connector could not be started: {error}",
                ) from error
        if result.returncode != 0:
            raise _connector_error(result.stderr, result.stdout)
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise VaultClientError(
                "connector_response_invalid",
                "Shared connector returned invalid JSON",
            ) from error
        if not isinstance(response, dict) or response.get("ok") is not True or "result" not in response:
            raise VaultClientError(
                "connector_response_invalid",
                "Shared connector returned an invalid response envelope",
            )
        return response["result"]

    def status(self) -> Any:
        result = self.dispatch("vault_status")
        if not isinstance(result, dict):
            raise VaultClientError("plugin_unhealthy", "Vault status response is not an object")
        revisions = result.get("revisions")
        if (
            result.get("status") != "ready"
            or result.get("root_configured") is not True
            or not isinstance(revisions, dict)
            or any(
                not isinstance(revisions.get(name), str) or not revisions.get(name)
                for name in REQUIRED_STATUS_REVISIONS
            )
        ):
            raise VaultClientError(
                "plugin_unhealthy",
                "Vault status is not ready with all required protocol revisions",
            )
        claim_health = result.get("claim_health")
        approved_scopes = (
            claim_health.get("approved_brand_scope_counts")
            if isinstance(claim_health, dict)
            else None
        )
        approved_simpro = (
            approved_scopes.get("Simpro")
            if isinstance(approved_scopes, dict)
            else None
        )
        if (
            not isinstance(claim_health, dict)
            or claim_health.get("proof_retrieval_state") != "available"
            or isinstance(approved_simpro, bool)
            or not isinstance(approved_simpro, int)
            or approved_simpro <= 0
        ):
            raise VaultClientError(
                "vault_claims_unavailable",
                "Vault status has no usable approved Simpro claims",
            )
        resource_access = result.get("resource_access")
        required_counts = {
            "manifest_resources",
            "searchable_resources",
            "indexed_resources",
            "declared_unindexed_resources",
            "context_readable_resources",
        }
        counts = {
            name: resource_access.get(name)
            for name in required_counts
        } if isinstance(resource_access, dict) else {}
        if (
            set(counts) != required_counts
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in counts.values()
            )
            or counts["manifest_resources"] <= 0
            or counts["searchable_resources"] != counts["manifest_resources"]
            or counts["context_readable_resources"] != counts["manifest_resources"]
            or counts["indexed_resources"] + counts["declared_unindexed_resources"]
            != counts["manifest_resources"]
        ):
            raise VaultClientError(
                "vault_discovery_incomplete",
                "Vault status does not provide complete manifest discovery coverage",
            )
        return result

    def describe(self) -> Any:
        return self.dispatch("vault_describe")

    def search(self, query: str, *, limit: int = 20) -> Any:
        return self.dispatch("vault_search", {"query": query, "limit": limit})

    def read(self, resource_id: str, *, purpose: str = "guidance") -> Any:
        return self.dispatch(
            "vault_read",
            {"resource_id": resource_id, "purpose": purpose},
        )

    def expand(
        self,
        resource_id: str,
        *,
        relation_types: Sequence[str] | None = None,
        purpose: str = "guidance",
    ) -> Any:
        arguments: dict[str, Any] = {"resource_id": resource_id, "purpose": purpose}
        if relation_types is not None:
            arguments["relation_types"] = list(relation_types)
        return self.dispatch("vault_expand", arguments)

    def claims(
        self,
        query: str,
        *,
        use_mode: str,
        brand_scope: str,
        limit: int = 20,
    ) -> Any:
        return self.dispatch(
            "vault_claims",
            {
                "query": query,
                "use_mode": use_mode,
                "brand_scope": brand_scope,
                "limit": limit,
            },
        )

    def build_context(self, arguments: Mapping[str, Any]) -> Any:
        return self.dispatch("vault_build_context", arguments)

    def find_proof(
        self,
        request: Mapping[str, Any],
        *,
        count: int = 7,
        source_type_counts: Mapping[str, int] | None = None,
        metric_classes: Sequence[str] | None = None,
        required_fields: Sequence[str] | None = None,
        max_per_subject: int = 1,
    ) -> Any:
        arguments: dict[str, Any] = {
            "request": dict(request),
            "count": count,
            "max_per_subject": max_per_subject,
        }
        if source_type_counts is not None:
            arguments["source_type_counts"] = dict(source_type_counts)
        if metric_classes is not None:
            arguments["metric_classes"] = list(metric_classes)
        if required_fields is not None:
            arguments["required_fields"] = list(required_fields)
        return self.dispatch("vault_find_proof", arguments)

    def validate_context(
        self,
        request: Mapping[str, Any],
        pack: Mapping[str, Any],
        receipt: Mapping[str, Any],
    ) -> Any:
        return self.dispatch(
            "vault_validate_context",
            {"request": dict(request), "pack": dict(pack), "receipt": dict(receipt)},
        )

    def try_dispatch(
        self,
        operation: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> VaultOperationResult:
        return self._try(operation, lambda: self.dispatch(operation, arguments))

    def try_status(self) -> VaultOperationResult:
        return self._try("vault_status", self.status)

    def try_describe(self) -> VaultOperationResult:
        return self._try("vault_describe", self.describe)

    def try_search(self, query: str, *, limit: int = 20) -> VaultOperationResult:
        return self._try("vault_search", lambda: self.search(query, limit=limit))

    def try_read(self, resource_id: str, *, purpose: str = "guidance") -> VaultOperationResult:
        return self._try(
            "vault_read",
            lambda: self.read(resource_id, purpose=purpose),
        )

    def try_expand(
        self,
        resource_id: str,
        *,
        relation_types: Sequence[str] | None = None,
        purpose: str = "guidance",
    ) -> VaultOperationResult:
        return self._try(
            "vault_expand",
            lambda: self.expand(
                resource_id,
                relation_types=relation_types,
                purpose=purpose,
            ),
        )

    def try_claims(
        self,
        query: str,
        *,
        use_mode: str,
        brand_scope: str,
        limit: int = 20,
    ) -> VaultOperationResult:
        return self._try(
            "vault_claims",
            lambda: self.claims(
                query,
                use_mode=use_mode,
                brand_scope=brand_scope,
                limit=limit,
            ),
        )

    def try_build_context(self, arguments: Mapping[str, Any]) -> VaultOperationResult:
        return self._try("vault_build_context", lambda: self.build_context(arguments))

    def try_find_proof(
        self,
        request: Mapping[str, Any],
        *,
        count: int = 7,
        source_type_counts: Mapping[str, int] | None = None,
        metric_classes: Sequence[str] | None = None,
        required_fields: Sequence[str] | None = None,
        max_per_subject: int = 1,
    ) -> VaultOperationResult:
        return self._try(
            "vault_find_proof",
            lambda: self.find_proof(
                request,
                count=count,
                source_type_counts=source_type_counts,
                metric_classes=metric_classes,
                required_fields=required_fields,
                max_per_subject=max_per_subject,
            ),
        )

    def try_validate_context(
        self,
        request: Mapping[str, Any],
        pack: Mapping[str, Any],
        receipt: Mapping[str, Any],
    ) -> VaultOperationResult:
        return self._try(
            "vault_validate_context",
            lambda: self.validate_context(request, pack, receipt),
        )

    @staticmethod
    def _try(operation: str, callback: Any) -> VaultOperationResult:
        try:
            return VaultOperationResult(ok=True, operation=operation, result=callback())
        except VaultClientError as error:
            return VaultOperationResult(
                ok=False,
                operation=operation,
                error={"code": error.code, "message": str(error)},
                recovery_hint=RECOVERY_HINTS.get(
                    error.code,
                    "Inspect the connector error, refresh vault_status, and retry with current IDs.",
                ),
            )
        except Exception:
            return VaultOperationResult(
                ok=False,
                operation=operation,
                error={
                    "code": "connector_internal_error",
                    "message": "Connector operation failed",
                },
                recovery_hint="Refresh vault_status and retry; retain the error in the recovery report.",
            )


def _connector_error(stderr: str, stdout: str) -> VaultClientError:
    raw = stderr.strip() or stdout.strip()
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                code = error.get("code")
                message = error.get("message")
                if isinstance(code, str) and isinstance(message, str):
                    return VaultClientError(code, message)
    return VaultClientError("connector_failed", raw or "Shared connector operation failed")


def _version_tuple(value: str) -> tuple[int, int, int]:
    core = value.strip().split("-", 1)[0].split("+", 1)[0]
    parts = core.split(".")
    if not 1 <= len(parts) <= 3 or any(not part.isdigit() for part in parts):
        return (0, 0, 0)
    numbers = [int(part) for part in parts]
    numbers.extend([0] * (3 - len(numbers)))
    return tuple(numbers[:3])


def _configured_vault_root(
    explicit_root: str | Path | None,
    *,
    settings_path: str | Path | None,
) -> str | Path | None:
    if explicit_root is not None and str(explicit_root).strip():
        return explicit_root
    configured = _plugin_authority_root(settings_path)
    if configured:
        return configured
    return os.environ.get(ROOT_ENVIRONMENT_VARIABLE)


def _plugin_authority_root(settings_path: str | Path | None) -> str | None:
    path = (
        Path(settings_path).expanduser()
        if settings_path is not None
        else Path.home() / CLAUDE_SETTINGS_RELATIVE_PATH
    )
    if not path.is_file():
        return None
    try:
        settings = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VaultClientError(
            "plugin_config_invalid",
            f"Claude plugin configuration is unreadable: {path}",
        ) from error
    if not isinstance(settings, dict):
        raise VaultClientError(
            "plugin_config_invalid",
            "Claude plugin configuration must be a JSON object",
        )
    configs = settings.get("pluginConfigs")
    if not isinstance(configs, dict):
        return None
    for plugin_id in (CANONICAL_PLUGIN_ID, LEGACY_PLUGIN_ID):
        plugin = configs.get(plugin_id)
        options = plugin.get("options") if isinstance(plugin, dict) else None
        root = options.get("authority_root") if isinstance(options, dict) else None
        if isinstance(root, str) and root.strip():
            return root.strip()
    return None
