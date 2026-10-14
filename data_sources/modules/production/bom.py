"""Production BOM and BOM-spec schemas with structural validators.

A BOM fact's ``quote`` is the verified text: it was found on the live page at build
time. The ``claim`` is Claude's wording, admitted only because the quote supports it
(see ``claim_support``). Downstream gates rely on the quote, not on the claim.
"""

from __future__ import annotations

import datetime
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.content_scoring.aeo_metadata_schema import CANONICAL_SCHEMA_ENTITIES

BOM_SCHEMA = "simpro-production-bom/v1"
SPEC_SCHEMA = "simpro-production-bom-spec/v1"
PRIORITIES = frozenset({"must", "should"})
FACT_SUPPORT = "quote_overlap"
CHROME_CAPTURE = "chrome_capture"
_SHA256 = re.compile(r"[0-9a-f]{64}")
LINK_KINDS = frozenset({"commercial_pillar", "internal", "external"})

# The AEO scorer's canonical schema entities, so notes copied into frontmatter score.
SCHEMA_NOTES = CANONICAL_SCHEMA_ENTITIES
_SPEC_TEXT_FIELDS = ("brand", "market", "title", "objective", "audience")
_SPEC_OPTIONAL = frozenset({"not_applicable_context_reason"})
_SPEC_REQUIRED = frozenset(
    {"schema", *_SPEC_TEXT_FIELDS, "sections", "facts", "proof", "paa_questions", "links", "cta", "schema_notes"}
)
# list key -> (required item fields, optional item fields)
_SPEC_LISTS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "sections": (frozenset({"heading", "purpose", "priority"}), frozenset()),
    "facts": (frozenset({"id", "claim", "url", "quote", "priority"}), frozenset({"capture"})),
    "proof": (frozenset({"id", "claim_id", "kind", "priority"}), frozenset()),
    "paa_questions": (frozenset({"question", "priority"}), frozenset()),
    "links": (frozenset({"url", "anchor", "kind", "priority"}), frozenset({"destination_id"})),
}
_BOM_REQUIRED = (
    "schema", "identity", "keyword", "serp", "sections", "facts", "proof", "paa", "links", "context",
)
_IDENTITY_REQUIRED = (
    "slug", "date", "run_id", "brand", "market", "workflow_mode", "article_path",
    "title", "objective", "audience", "cta", "schema_notes",
)


class SpecFileError(Exception):
    """Raised when the BOM spec file cannot be read as a JSON object."""


class BuildEnvironmentError(Exception):
    """Raised when the build cannot run: a required index, vault, or file is unusable.

    This is an operational failure, not a refusal of the spec's content.
    """


def load_bom(path: str | Path) -> dict[str, Any]:
    """Read a BOM file as a JSON object."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"BOM {path} is not a JSON object")
    return payload


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _item_errors(label: str, index: int, item: Any, required: frozenset[str], optional: frozenset[str]) -> list[str]:
    where = f"{label}[{index}]"
    if not isinstance(item, Mapping):
        return [f"{where} must be an object"]
    errors = [f"{where} has unknown key: {key}" for key in sorted(set(item) - required - optional)]
    for key in sorted(required):
        if key not in item:
            errors.append(f"{where} is missing {key}")
        elif not _is_text(item[key]):
            errors.append(f"{where} {key} must be non-empty text")
    return errors


def _priority_and_kind_errors(label: str, items: Sequence[Any]) -> list[str]:
    errors = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            continue
        if item.get("priority") not in PRIORITIES:
            errors.append(f"{label}[{index}] priority must be must or should, found: {item.get('priority')!r}")
        if label == "links" and item.get("kind") not in LINK_KINDS:
            errors.append(f"{label}[{index}] kind must be one of {sorted(LINK_KINDS)}, found: {item.get('kind')!r}")
    return errors


def _duplicate_id_errors(label: str, items: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    errors = []
    for item in items:
        value = item.get("id") if isinstance(item, Mapping) else None
        if isinstance(value, str) and value in seen:
            errors.append(f"duplicate {label} id: {value}")
        if isinstance(value, str):
            seen.add(value)
    return errors


def _spec_list_errors(spec: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, (required, optional) in _SPEC_LISTS.items():
        items = spec.get(key)
        if key not in spec:
            continue
        if not isinstance(items, list):
            errors.append(f"{key} must be a list")
            continue
        for index, item in enumerate(items):
            errors += _item_errors(key, index, item, required, optional)
        errors += _priority_and_kind_errors(key, items)
    facts = spec.get("facts") if isinstance(spec.get("facts"), list) else []
    errors += [
        f"facts[{index}] capture must be non-empty text"
        for index, fact in enumerate(facts)
        if isinstance(fact, Mapping) and "capture" in fact and not _is_text(fact["capture"])
    ]
    errors += _duplicate_id_errors("fact", facts)
    errors += _duplicate_id_errors("proof", spec.get("proof") if isinstance(spec.get("proof"), list) else [])
    return errors


def _spec_destination_errors(spec: Mapping[str, Any]) -> list[str]:
    links = spec.get("links")
    if not isinstance(links, list):
        return []
    return [
        f"links[{index}] destination_id is only allowed on a commercial_pillar link"
        for index, link in enumerate(links)
        if isinstance(link, Mapping) and "destination_id" in link and link.get("kind") != "commercial_pillar"
    ]


def _spec_scalar_errors(spec: Mapping[str, Any]) -> list[str]:
    errors = []
    if spec.get("schema") != SPEC_SCHEMA:
        errors.append(f"spec schema must be {SPEC_SCHEMA}, found: {spec.get('schema')!r}")
    for key in _SPEC_TEXT_FIELDS:
        if key in spec and not _is_text(spec[key]):
            errors.append(f"spec {key} must be non-empty text")
    if "not_applicable_context_reason" in spec and not _is_text(spec["not_applicable_context_reason"]):
        errors.append("spec not_applicable_context_reason must be non-empty text")
    errors += _schema_notes_errors(spec)
    if "cta" in spec:
        errors += _item_errors("cta", 0, spec["cta"], frozenset({"text", "url"}), frozenset())
    return errors


def _schema_notes_errors(spec: Mapping[str, Any]) -> list[str]:
    if "schema_notes" not in spec:
        return []
    notes = spec["schema_notes"]
    if not isinstance(notes, list) or not all(isinstance(note, str) for note in notes):
        return ["spec schema_notes must be a list of text"]
    return [
        f"spec schema_notes entry is not an allowed note: {note!r}; allowed: {sorted(SCHEMA_NOTES)}"
        for note in notes
        if note not in SCHEMA_NOTES
    ]


def validate_spec(spec: Any) -> list[str]:
    """Return every structural error in a BOM spec; an empty list means it is well formed."""
    if not isinstance(spec, Mapping):
        return ["spec must be a JSON object"]
    errors = [f"spec has unknown key: {key}" for key in sorted(set(spec) - _SPEC_REQUIRED - _SPEC_OPTIONAL)]
    errors += [f"spec is missing {key}" for key in sorted(_SPEC_REQUIRED - set(spec))]
    return errors + _spec_scalar_errors(spec) + _spec_list_errors(spec) + _spec_destination_errors(spec)


def _bom_items(bom: Mapping[str, Any], key: str) -> list[Any]:
    value = bom.get(key)
    return value if isinstance(value, list) else []


def _paa_questions(bom: Mapping[str, Any]) -> list[Any]:
    paa = bom.get("paa")
    questions = paa.get("questions") if isinstance(paa, Mapping) else None
    return questions if isinstance(questions, list) else []


def _fact_errors(bom: Mapping[str, Any]) -> list[str]:
    errors = []
    for index, fact in enumerate(_bom_items(bom, "facts")):
        if not isinstance(fact, Mapping):
            errors.append(f"facts[{index}] must be an object")
            continue
        errors += [
            f"facts[{index}] is missing {field}" for field in ("verified_at", "url", "quote") if not _is_text(fact.get(field))
        ]
        if fact.get("support") != FACT_SUPPORT:
            errors.append(f"facts[{index}] support must be {FACT_SUPPORT}, found: {fact.get('support')!r}")
        errors += _capture_binding_errors(index, fact)
    return errors


def _is_utc_stamp(value: Any) -> bool:
    try:
        datetime.datetime.strptime(value if isinstance(value, str) else "", "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def _capture_binding_errors(index: int, fact: Mapping[str, Any]) -> list[str]:
    """A Chrome-verified fact carries exactly its capture's path, receipt hash, and UTC capture time."""
    via = fact.get("verified_via")
    where = f"facts[{index}]"
    if via is not None and via != CHROME_CAPTURE:
        return [f"{where} verified_via must be {CHROME_CAPTURE}, found: {via!r}"]
    capture = fact.get("capture")
    if via is None:
        return [f"{where} has a capture binding but verified_via is not {CHROME_CAPTURE}"] if "capture" in fact else []
    if not isinstance(capture, Mapping):
        return [f"{where} verified_via {CHROME_CAPTURE} requires a capture binding"]
    keys = {"path", "sha256", "captured_at"}
    errors = [f"{where} capture has unknown key: {key}" for key in sorted(set(capture) - keys)]
    errors += [f"{where} capture is missing {key}" for key in sorted(keys - set(capture))]
    if "path" in capture and not _is_text(capture["path"]):
        errors.append(f"{where} capture path must be non-empty text")
    if "sha256" in capture and not (isinstance(capture["sha256"], str) and _SHA256.fullmatch(capture["sha256"])):
        errors.append(f"{where} capture sha256 must be 64 lowercase hex characters")
    if "captured_at" in capture and not _is_utc_stamp(capture["captured_at"]):
        errors.append(f"{where} capture captured_at must be a UTC time like 2026-10-14T08:00:00Z")
    return errors


def _spec_binding_errors(identity: Mapping[str, Any]) -> list[str]:
    binding = identity.get("spec")
    if not isinstance(binding, Mapping):
        return ["identity spec must be a {path, sha256} binding"]
    errors = []
    if not _is_text(binding.get("path")):
        errors.append("identity spec path must be non-empty text")
    digest = binding.get("sha256")
    if not (isinstance(digest, str) and _SHA256.fullmatch(digest)):
        errors.append("identity spec sha256 must be 64 lowercase hex characters")
    return errors


def _shape_errors(bom: Mapping[str, Any]) -> list[str]:
    errors = []
    if bom.get("schema") != BOM_SCHEMA:
        errors.append(f"BOM schema must be {BOM_SCHEMA}, found: {bom.get('schema')!r}")
    errors += [f"BOM is missing {key}" for key in _BOM_REQUIRED if key not in bom]
    identity = bom.get("identity")
    if isinstance(identity, Mapping):
        errors += [f"identity is missing {key}" for key in _IDENTITY_REQUIRED if key not in identity]
        errors += _spec_binding_errors(identity)
    elif "identity" in bom:
        errors.append("identity must be an object")
    for key in ("sections", "facts", "proof", "links"):
        if key in bom and not isinstance(bom[key], list):
            errors.append(f"{key} must be a list")
    return errors + _keyword_errors(bom)


def _keyword_errors(bom: Mapping[str, Any]) -> list[str]:
    keyword = bom.get("keyword")
    if "keyword" in bom and not (isinstance(keyword, Mapping) and _is_text(keyword.get("primary"))):
        return ["keyword primary must be non-empty text"]
    return []


def validate_bom(bom: Any) -> list[str]:
    """Return structural errors in a production BOM; an empty list means it is well formed."""
    if not isinstance(bom, Mapping):
        return ["BOM must be a JSON object"]
    errors = _shape_errors(bom)
    for key in ("sections", "facts", "proof", "links"):
        errors += _priority_and_kind_errors(key, _bom_items(bom, key))
    errors += _priority_and_kind_errors("paa.questions", _paa_questions(bom))
    errors += _duplicate_id_errors("fact", _bom_items(bom, "facts"))
    errors += _duplicate_id_errors("proof", _bom_items(bom, "proof"))
    return errors + _fact_errors(bom)
