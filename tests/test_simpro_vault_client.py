"""Compatibility contract for seomachine's standalone vault client import."""

from __future__ import annotations

import importlib
import inspect
import json
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
    assert issubclass(SimproVaultClient, VaultClient)
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
        "search_internal_strategy",
        "read",
        "read_internal_strategy",
        "expand",
        "claims",
        "build_context",
        "pack_internal_strategy",
        "validate_context",
        "try_dispatch",
        "try_status",
        "try_describe",
        "try_search",
        "try_search_internal_strategy",
        "try_read",
        "try_read_internal_strategy",
        "try_expand",
        "try_claims",
        "try_build_context",
        "try_pack_internal_strategy",
        "try_validate_context",
    )

    assert all(callable(getattr(SimproVaultClient, name)) for name in methods)


def test_v13_internal_strategy_operations_are_advertised() -> None:
    assert "vault_search_internal_strategy" in compatibility.OPERATIONS
    assert "vault_read_internal_strategy" in compatibility.OPERATIONS
    assert "vault_pack_internal_strategy" in compatibility.OPERATIONS


def test_internal_strategy_client_methods_dispatch_separate_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object], Path]] = []

    def fake_dispatch(
        operation: str,
        arguments: dict[str, object],
        *,
        vault_root: Path,
        **_kwargs: object,
    ) -> object:
        calls.append((operation, arguments, vault_root))
        if operation == "vault_search_internal_strategy":
            return [{"resource_id": "res-internal-plumbing"}]
        if operation == "vault_read_internal_strategy":
            return {"resource_id": "res-internal-plumbing", "content": "internal only"}
        if operation == "vault_pack_internal_strategy":
            return {
                "pack": {"schema": "simpro-internal-strategy-pack/v1"},
                "sidecar": {"schema": "simpro-content-validation-sidecar/v1"},
                "receipt": {"schema": "simpro-internal-strategy-receipt/v1"},
            }
        raise AssertionError(operation)

    monkeypatch.setattr("simpro_vault.client.engine_dispatch", fake_dispatch)
    monkeypatch.setattr(
        "simpro_vault.client.RetrievalProtocol.open",
        lambda *, explicit_root, clock=None: object(),
    )

    client = SimproVaultClient(tmp_path)

    assert client.search_internal_strategy("plumbing", limit=3) == [
        {"resource_id": "res-internal-plumbing"}
    ]
    assert client.read_internal_strategy("res-internal-plumbing") == {
        "resource_id": "res-internal-plumbing",
        "content": "internal only",
    }
    assert client.pack_internal_strategy(
        {
            "request": {"task": "blog angle", "scope": {}},
            "resource_ids": ["res-internal-plumbing"],
            "search_queries": ["plumbing"],
            "constraints": ["Do not use internal strategy as publishable proof."],
            "unresolved_gaps": [],
            "task_satisfaction": "satisfied",
        }
    )["pack"]["schema"] == "simpro-internal-strategy-pack/v1"

    assert calls == [
        (
            "vault_search_internal_strategy",
            {"query": "plumbing", "limit": 3},
            tmp_path.resolve(),
        ),
        (
            "vault_read_internal_strategy",
            {"resource_id": "res-internal-plumbing"},
            tmp_path.resolve(),
        ),
        (
            "vault_pack_internal_strategy",
            {
                "request": {"task": "blog angle", "scope": {}},
                "resource_ids": ["res-internal-plumbing"],
                "search_queries": ["plumbing"],
                "constraints": ["Do not use internal strategy as publishable proof."],
                "unresolved_gaps": [],
                "task_satisfaction": "satisfied",
            },
            tmp_path.resolve(),
        ),
    ]


def test_client_resolves_explicit_root_before_plugin_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit = tmp_path / "explicit"
    configured = tmp_path / "configured"
    explicit.mkdir()
    configured.mkdir()
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
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

    client = SimproVaultClient(explicit, environ={"USERPROFILE": str(tmp_path)})

    assert client.vault_root == explicit.resolve()


def test_client_resolves_plugin_authority_root_without_environment_variable(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "configured"
    vault.mkdir()
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(
        json.dumps(
            {
                "pluginConfigs": {
                    "simpro-context@simpro": {
                        "options": {"authority_root": str(vault)}
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    client = SimproVaultClient(environ={"USERPROFILE": str(tmp_path)})

    assert client.vault_root == vault.resolve()


def test_client_fails_closed_when_root_is_unset(
    tmp_path: Path,
) -> None:
    with pytest.raises(VaultClientError) as raised:
        SimproVaultClient(environ={"USERPROFILE": str(tmp_path)})

    assert raised.value.code == "root_unset"
    assert "simpro-context@simpro" in str(raised.value)


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


def test_runtime_module_has_no_legacy_inventory_or_environment_dispatch() -> None:
    source = inspect.getsource(compatibility).casefold()

    assert "discover_plugin" not in source
    assert "subprocess" not in source
    assert "tempfile" not in source
    assert "simpro_context_authority_root" not in source
    assert "simpro_vault_root" not in source
    assert ".getenv" not in source
    assert ".environ[" not in source


def test_dependency_is_pinned_to_immutable_v2_release() -> None:
    root = Path(__file__).resolve().parents[1]
    requirements = (root / "data_sources" / "requirements.txt").read_text(
        encoding="utf-8"
    )

    assert (
        "simpro-vault-connector @ "
        "git+https://github.com/Simpro-Group-Marketing/"
        "simpro-context-connector.git@v2.2.0"
    ) in requirements


def test_mcp_template_invokes_the_standalone_module() -> None:
    root = Path(__file__).resolve().parents[1]
    template = (root / ".mcp.json.template").read_text(encoding="utf-8")

    assert "simpro-vault" in template
    assert "simpro_vault.mcp" in template
    assert "CLAUDE_PLUGIN_ROOT" not in template


def test_readme_uses_the_current_default_branch_workflow() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")

    assert "custom/local-context" not in readme
    assert "feature branches targeting `main`" not in readme
    assert "one codebase" in readme.casefold() or "main" in readme.casefold()
