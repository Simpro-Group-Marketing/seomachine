"""The client vocabulary every self-declared browser capture records."""

from __future__ import annotations

import pytest
from data_sources.modules.capture_client import (
    CLIENT_FIELD_SINCE,
    CLIENTS,
    UNRECORDED,
    client_error,
    client_required,
    declared_client,
    fields_with_client_ok,
)

FIELDS = frozenset({"schema", "query"})
BEFORE = "2026-10-14T08:00:00Z"
AFTER = "2026-10-16T08:00:00Z"


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


def test_the_field_shipped_at_a_fixed_instant():
    assert CLIENT_FIELD_SINCE == "2026-10-15T18:38:35Z"


@pytest.mark.parametrize(("stamp", "required"), [
    (BEFORE, False), ("2026-10-15T18:38:34Z", False), (CLIENT_FIELD_SINCE, True), (AFTER, True),
    ("not a time", True), (None, True),
])
def test_a_record_made_after_the_field_shipped_must_name_its_client(stamp, required):
    assert client_required(stamp) is required


def test_fields_with_client_ok_applies_the_cutoff():
    legacy = {"schema": "x", "query": "q"}
    assert fields_with_client_ok(legacy, FIELDS)
    assert fields_with_client_ok(legacy, FIELDS, recorded_at=BEFORE)
    assert not fields_with_client_ok(legacy, FIELDS, recorded_at=AFTER)
    assert fields_with_client_ok({**legacy, "client": "codex"}, FIELDS, recorded_at=AFTER)
    assert not fields_with_client_ok({**legacy, "client": "cursor"}, FIELDS, recorded_at=BEFORE)
    assert not fields_with_client_ok({**legacy, "extra": 1}, FIELDS)


def test_declared_client_refuses_an_unknown_value():
    with pytest.raises(ValueError, match="client"):
        declared_client("cursor", {})
