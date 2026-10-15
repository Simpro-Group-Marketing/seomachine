"""The client vocabulary every self-declared browser capture records."""

from __future__ import annotations

import pytest
from data_sources.modules.capture_client import CLIENTS, UNRECORDED, client_error, declared_client


def test_vocabulary():
    assert CLIENTS == {"claude_code", "codex"}
    assert UNRECORDED == "unrecorded"


@pytest.mark.parametrize("value", ["claude_code", "codex"])
def test_known_clients_are_valid(value):
    assert client_error(value) == ""


@pytest.mark.parametrize("value", ["", "claude", "Codex", None, 3])
def test_unknown_clients_are_refused(value):
    assert client_error(value)


def test_codex_is_refused_inside_claude_code():
    with pytest.raises(ValueError, match="Claude Code"):
        declared_client("codex", {"CLAUDECODE": "1"})
    assert declared_client("claude_code", {"CLAUDECODE": "1"}) == "claude_code"


@pytest.mark.parametrize("value", ["claude_code", "codex"])
def test_either_client_is_accepted_without_the_marker(value):
    assert declared_client(value, {}) == value


def test_declared_client_refuses_an_unknown_value():
    with pytest.raises(ValueError, match="client"):
        declared_client("cursor", {})
