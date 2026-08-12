"""Compatibility contract for seomachine's standalone vault client import."""

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

    assert all(callable(getattr(SimproVaultClient, name)) for name in methods)


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
