"""Link resolution for the production BOM, including the verified commercial pillar."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import current_utc_date
from data_sources.modules.commercial_pillar_index import (
    CommercialPillarIndexError,
    CommercialPillarRecord,
    get_verified_destination,
    load_index,
    validate_index,
)
from data_sources.modules.production.bom import BuildEnvironmentError
from data_sources.modules.production.bom_artifacts import squash

PILLAR_INDEX = Path("context") / "commercial-pillar-index.json"
_INDEX_WIDE_RULES = frozenset({"commercial_pillar_schema_unsupported"})


def _validated_record(link: Mapping[str, Any], spec: Mapping[str, Any], root: Path) -> CommercialPillarRecord:
    try:
        index = load_index(root / PILLAR_INDEX)
    except CommercialPillarIndexError as error:
        raise BuildEnvironmentError(f"commercial pillar index is unusable: {error}") from error
    record = get_verified_destination(
        index, destination_id=link["destination_id"], brand=spec["brand"], market=spec["market"]
    )
    row = index.records.index(record) + 1
    findings = [
        finding
        for finding in validate_index(index, today=current_utc_date())
        if finding["line"] == row or finding["rule_id"] in _INDEX_WIDE_RULES
    ]
    if findings:
        details = "; ".join(f"{finding['rule_id']}: {finding['message']}" for finding in findings)
        raise ValueError(f"commercial pillar destination {record.destination_id} failed validation: {details}")
    return record


def _check_pillar(link: Mapping[str, Any], spec: Mapping[str, Any], root: Path) -> None:
    if not link.get("destination_id"):
        raise ValueError("commercial_pillar link requires destination_id")
    if link["priority"] != "must":
        raise ValueError("commercial_pillar link priority must be must")
    record = _validated_record(link, spec, root)
    if link["url"] != record.canonical_url:
        raise ValueError(
            f"commercial_pillar url must equal the canonical url {record.canonical_url}, found: {link['url']}"
        )
    keyword = re.escape(squash(record.main_keyword))
    if re.search(rf"(?<!\w){keyword}(?!\w)", squash(link["anchor"])) is None:
        raise ValueError(f"commercial_pillar anchor must contain the main keyword: {record.main_keyword}")


def resolve_links(spec: Mapping[str, Any], root: Path, nonconnector: bool) -> list[dict[str, Any]]:
    """Copy links, requiring and verifying the commercial pillar for connector specs."""
    links = copy.deepcopy(spec["links"])
    pillars = [link for link in links if link["kind"] == "commercial_pillar"]
    if len(pillars) > 1 or (not nonconnector and len(pillars) != 1):
        raise ValueError(f"expected exactly one commercial_pillar link, found {len(pillars)}")
    for pillar in pillars:
        _check_pillar(pillar, spec, root)
    return links
