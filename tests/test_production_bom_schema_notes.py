"""The BOM spec's schema_notes vocabulary is the AEO scorer's canonical list."""

from __future__ import annotations

from data_sources.modules.content_scoring.aeo_metadata_schema import CANONICAL_SCHEMA_ENTITIES
from data_sources.modules.production import bom


def _errors(notes):
    return [e for e in bom.validate_spec({"schema": bom.SPEC_SCHEMA, "schema_notes": notes}) if "schema_notes" in e]


def test_spec_accepts_every_scorer_canonical_schema_entity():
    assert _errors(sorted(CANONICAL_SCHEMA_ENTITIES)) == []


def test_spec_rejects_short_names_the_scorer_does_not_accept():
    assert _errors(["ImageObject"]) and _errors(["Organization as publisher reference"])
