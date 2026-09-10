"""Project-aware compatibility wrapper for the standalone Simpro vault client.

The canonical engine, Python client, CLI, and MCP adapters live in the
``simpro-vault-connector`` distribution. Seomachine keeps this module so
existing workflow imports can resolve the current repo's configured
``simpro-context@simpro`` authority root without relying on shell env fallbacks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

from simpro_vault import (
    OPERATIONS,
    RECOVERY_HINTS,
    VaultClient,
    VaultClientError,
    VaultOperationResult,
    VaultPackInternalStrategyArguments,
    VaultPackInternalStrategyResult,
)


PLUGIN_ID = "simpro-context@simpro"


def _settings_candidates(environ: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    environment = os.environ if environ is None else environ
    home_value = (
        environment.get("USERPROFILE")
        or (
            str(Path(environment["HOMEDRIVE"]) / environment["HOMEPATH"].lstrip("\\/"))
            if environment.get("HOMEDRIVE") and environment.get("HOMEPATH")
            else ""
        )
        or environment.get("HOME")
        or str(Path.home())
    )
    home = Path(home_value).expanduser()
    home_candidates = (
        home / ".claude" / "settings.local.json",
        home / ".claude" / "settings.json",
        home / ".codex" / "settings.json",
    )
    if environ is not None:
        return home_candidates
    current = Path.cwd()
    return (
        current / ".claude" / "settings.local.json",
        current / ".claude" / "settings.json",
        *home_candidates,
    )


def _configured_authority_root(
    environ: Mapping[str, str] | None = None,
) -> Path | None:
    configured: list[Path] = []
    seen: set[str] = set()
    for settings_path in _settings_candidates(environ):
        try:
            payload = json.loads(settings_path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        plugin_configs = payload.get("pluginConfigs")
        if not isinstance(plugin_configs, dict):
            continue
        plugin_config = plugin_configs.get(PLUGIN_ID)
        if not isinstance(plugin_config, dict):
            continue
        options = plugin_config.get("options")
        if not isinstance(options, dict):
            continue
        authority_root = options.get("authority_root")
        if not isinstance(authority_root, str) or not authority_root.strip():
            continue
        root = Path(authority_root).expanduser()
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        configured.append(root)
    if len(configured) > 1:
        raise VaultClientError(
            "root_ambiguous",
            f"Multiple {PLUGIN_ID} authority roots are configured",
            "Keep exactly one project-matching plugin authority_root, then retry vault_status.",
        )
    return configured[0] if configured else None


class SimproVaultClient(VaultClient):
    """Resolve seomachine's configured connector root, then use VaultClient."""

    def __init__(
        self,
        vault_root: str | Path | None = None,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        root = vault_root if vault_root is not None else _configured_authority_root(environ)
        if root is None:
            raise VaultClientError(
                "root_unset",
                f"No {PLUGIN_ID} authority_root is configured for this repository",
                "Configure pluginConfigs.simpro-context@simpro.options.authority_root, then retry vault_status.",
            )
        super().__init__(root, environ=environ)


__all__ = [
    "OPERATIONS",
    "RECOVERY_HINTS",
    "SimproVaultClient",
    "VaultClientError",
    "VaultOperationResult",
    "VaultPackInternalStrategyArguments",
    "VaultPackInternalStrategyResult",
]
