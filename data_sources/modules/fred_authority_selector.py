"""Vault-backed selector for Fred Voccola media and PR authority evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence


DEFAULT_VAULT_ROOT = Path(
    "C:/Users/patrick.grueschow/Desktop/Obsidian/Simpro Brand Context"
)
INVENTORY_RELATIVE_PATH = Path("indexes/fred-voccola-media-inventory.csv")
AUTHORITY_RELATIVE_PATH = Path("indexes/authority-signal-matrix.csv")
MANIFEST_RELATIVE_PATH = Path("indexes/agent-retrieval-manifest.jsonl")

USABLE_AUTHORITY_STATUS = "usable_for_eeat_authority_support"
PUBLIC_PLAYLIST_STATUS = "public_curated_playlist_asset"
SIMPRO_BRAND = "simpro"
INVENTORY_REQUIRED_COLUMNS = {
    "inventory_id",
    "media_type",
    "authority_id",
    "source_layer",
    "outlet",
    "title",
    "url_or_locator",
    "date",
    "recommended_brand",
    "evidence_status",
    "public_use_status",
    "include_in_hub",
    "notes",
}
AUTHORITY_REQUIRED_COLUMNS = {
    "authority_id",
    "cluster",
    "outlet",
    "headline",
    "canonical_url",
    "date",
    "country",
    "recommended_brand",
    "total_placements",
    "also_covered_by",
    "eeat_dimension",
    "evidence_status",
    "allowed_use",
    "public_use_status",
    "source_node",
    "raw_file",
    "notes",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "blog",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
}


class FredAuthorityDataError(RuntimeError):
    """Raised when the vault evidence contract cannot be verified."""


def select_fred_authority(
    topic: str,
    *,
    title: str = "",
    objective: str = "",
    vault_root: str | Path | None = None,
    limit: int = 5,
) -> List[dict]:
    """Return ranked, vault-verified Fred Voccola authority candidates."""
    root = _resolve_vault_root(vault_root)
    inventory_rows, authority_rows = _load_verified_rows(root)
    authority_by_id = {
        row.get("authority_id", "").strip(): row
        for row in authority_rows
        if row.get("authority_id", "").strip()
    }
    query_tokens = _tokens(" ".join((topic, title, objective)))
    candidates: List[dict] = []

    for inventory in inventory_rows:
        public_status = inventory.get("public_use_status", "").strip()
        if not _is_simpro_row(inventory):
            continue
        if not _is_included_in_hub(inventory):
            continue

        playlist_only = public_status == PUBLIC_PLAYLIST_STATUS
        if public_status != USABLE_AUTHORITY_STATUS and not playlist_only:
            continue
        if playlist_only and not _is_public_youtube_asset_url(
            inventory.get("url_or_locator", "")
        ):
            continue

        authority_id = inventory.get("authority_id", "").strip()
        authority: Dict[str, str] = {}
        if not playlist_only:
            authority = authority_by_id.get(authority_id, {})
            if not authority:
                continue
            if not _is_usable_authority_row(authority):
                continue
            if not _authority_matches_inventory(inventory, authority):
                continue

        candidate = dict(inventory)
        playlist_collection = playlist_only and bool(
            re.search(r"youtube\.com/playlist\?", inventory.get("url_or_locator", ""), re.IGNORECASE)
        )
        candidate.update(
            {
                "authority_cluster": authority.get("cluster", ""),
                "authority_allowed_use": authority.get("allowed_use", ""),
                "authority_evidence_status": authority.get("evidence_status", ""),
                "authority_public_use_status": authority.get(
                    "public_use_status", ""
                ),
                "authority_canonical_url": authority.get("canonical_url", ""),
                "authority_kind": (
                    "discovery_or_embed_only"
                    if playlist_only
                    else "earned_media_authority"
                ),
                "playlist_only": playlist_only,
                "playlist_collection": playlist_collection,
            }
        )
        candidate["relevance_score"] = _relevance_score(query_tokens, candidate)
        authority_bonus = 8 if not playlist_only else 0
        collection_penalty = 4 if playlist_collection else 0
        candidate["score"] = candidate["relevance_score"] + authority_bonus - collection_penalty
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            int(item.get("score", 0)),
            int(item.get("relevance_score", 0)),
            not bool(item.get("playlist_only", False)),
            str(item.get("inventory_id", "")),
        ),
        reverse=True,
    )
    return candidates[: max(limit, 0)]


def build_fred_authority_slate(
    topic: str,
    *,
    title: str = "",
    objective: str = "",
    vault_root: str | Path | None = None,
    limit: int = 5,
    selected_id: Optional[str] = None,
) -> str:
    """Return a sidecar-ready Fred Voccola Authority Selection block."""
    results = select_fred_authority(
        topic,
        title=title,
        objective=objective,
        vault_root=vault_root,
        limit=limit,
    )
    candidate_by_id = {
        str(result.get("inventory_id", "")): result for result in results
    }
    selected = selected_id.strip() if selected_id else "none"
    if selected != "none" and selected not in candidate_by_id:
        raise FredAuthorityDataError(
            f"Selected Fred authority ID is not in the verified candidate slate: {selected}"
        )

    command = _selector_command(
        topic,
        title=title,
        objective=objective,
        limit=limit,
    )
    top_candidates = [
        str(result["inventory_id"])
        for result in results
        if result.get("inventory_id")
    ]
    selected_row = candidate_by_id.get(selected)
    if selected_row:
        authority_id = selected_row.get("authority_id") or "none"
        public_url = selected_row.get("url_or_locator") or "not applicable"
        evidence_status = selected_row.get("evidence_status") or "not applicable"
        fit_decision = (
            "Editorial source review is still required before public use; "
            f"candidate {selected} ranked for direct topical overlap with {topic}."
        )
    else:
        authority_id = "none"
        public_url = "not applicable"
        evidence_status = "not applicable"
        fit_decision = (
            "No candidate has been editorially verified as directly supporting "
            f"the article topic '{topic}'; public use is rejected until that review occurs."
        )

    return "\n".join(
        [
            "## Fred Voccola Authority Selection",
            f"- Selector command: {command}",
            "- Evaluation status: completed",
            (
                "- Top candidates: "
                f"[{', '.join(top_candidates) if top_candidates else 'none'}]"
            ),
            f"- Selected: [{selected}]",
            f"- Fit decision: {fit_decision}",
            "- Intended use: none",
            "- Target section: not applicable",
            f"- Authority row: [{authority_id}]",
            f"- Public URL: {public_url}",
            f"- Evidence status: {evidence_status}",
            "- Verification method: not_applicable",
            "- Evidence excerpt: not applicable",
            "- Timestamp or locator: not applicable",
            "- Playback verified: not_applicable",
            "- Exact quote: not applicable",
            "- Embed decision: no",
            "- VideoObject: not applicable",
        ]
    )


def _resolve_vault_root(vault_root: str | Path | None) -> Path:
    if vault_root is not None and str(vault_root).strip():
        return Path(vault_root)
    configured = os.environ.get("SIMPRO_BRAND_CONTEXT_VAULT", "").strip()
    if configured:
        return Path(configured)
    return DEFAULT_VAULT_ROOT


def _load_verified_rows(root: Path) -> tuple[List[dict], List[dict]]:
    if not root.is_dir():
        raise FredAuthorityDataError(f"Fred authority vault is unavailable: {root}")

    inventory_path = root / INVENTORY_RELATIVE_PATH
    authority_path = root / AUTHORITY_RELATIVE_PATH
    manifest_path = root / MANIFEST_RELATIVE_PATH
    for path in (inventory_path, authority_path, manifest_path):
        if not path.is_file():
            raise FredAuthorityDataError(
                f"Fred authority vault manifest or required index is unavailable: {path}"
            )

    manifest = _load_manifest(manifest_path)
    expected_hashes = {
        str(item.get("path", "")).replace("\\", "/"): str(
            item.get("sha256", "")
        ).lower()
        for item in manifest.get("control_inputs", [])
        if isinstance(item, dict)
    }
    for relative_path, path in (
        (INVENTORY_RELATIVE_PATH, inventory_path),
        (AUTHORITY_RELATIVE_PATH, authority_path),
    ):
        key = relative_path.as_posix()
        expected = expected_hashes.get(key, "")
        if not expected:
            raise FredAuthorityDataError(
                f"Fred authority manifest does not control required index: {key}"
            )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise FredAuthorityDataError(
                f"Fred authority manifest is stale for {key}: "
                f"expected {expected}, found {actual}"
            )

    return (
        _read_csv(
            inventory_path,
            required_columns=INVENTORY_REQUIRED_COLUMNS,
            id_field="inventory_id",
            label="Fred authority inventory",
        ),
        _read_csv(
            authority_path,
            required_columns=AUTHORITY_REQUIRED_COLUMNS,
            id_field="authority_id",
            label="Fred authority matrix",
        ),
    )


def _load_manifest(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("record_type") == "manifest":
                    return record
    except (OSError, json.JSONDecodeError) as exc:
        raise FredAuthorityDataError(
            f"Fred authority manifest is unreadable: {path}: {exc}"
        ) from exc
    raise FredAuthorityDataError(f"Fred authority manifest record is unavailable: {path}")


def _read_csv(
    path: Path,
    *,
    required_columns: set[str],
    id_field: str,
    label: str,
) -> List[dict]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
            missing = sorted(required_columns - fieldnames)
            if missing:
                raise FredAuthorityDataError(
                    f"{label} is missing required columns: {', '.join(missing)}"
                )
            rows = [dict(row) for row in reader]
    except (OSError, csv.Error) as exc:
        raise FredAuthorityDataError(
            f"Fred authority index is unreadable: {path}: {exc}"
        ) from exc

    seen: set[str] = set()
    for row in rows:
        identifier = row.get(id_field, "").strip()
        if not identifier:
            raise FredAuthorityDataError(f"{label} has blank {id_field}")
        if identifier in seen:
            raise FredAuthorityDataError(
                f"{label} has duplicate {id_field}: {identifier}"
            )
        seen.add(identifier)
    return rows


def _is_simpro_row(row: dict) -> bool:
    brands = {
        token
        for token in re.split(
            r"[^a-z0-9]+",
            row.get("recommended_brand", "").strip().lower(),
        )
        if token
    }
    return SIMPRO_BRAND in brands


def _is_usable_authority_row(row: dict) -> bool:
    return (
        _is_simpro_row(row)
        and row.get("public_use_status", "").strip() == USABLE_AUTHORITY_STATUS
        and bool(row.get("canonical_url", "").strip())
        and bool(row.get("allowed_use", "").strip())
    )


def _authority_matches_inventory(inventory: dict, authority: dict) -> bool:
    return all(
        (
            bool(inventory.get(field, "").strip())
            and bool(authority.get(authority_field, "").strip())
            and inventory.get(field, "").strip() == authority.get(
                authority_field, ""
            ).strip()
        )
        for field, authority_field in (
            ("authority_id", "authority_id"),
            ("title", "headline"),
            ("url_or_locator", "canonical_url"),
            ("recommended_brand", "recommended_brand"),
            ("evidence_status", "evidence_status"),
            ("public_use_status", "public_use_status"),
        )
    )


def _is_public_youtube_url(url: str) -> bool:
    return bool(
        re.fullmatch(
            r"https://(?:www\.)?(?:youtube\.com/watch\?v=[A-Za-z0-9_-]{6,}"
            r"|youtu\.be/[A-Za-z0-9_-]{6,})(?:[&#?].*)?",
            url.strip(),
            flags=re.IGNORECASE,
        )
    )


def _is_public_youtube_asset_url(url: str) -> bool:
    if _is_public_youtube_url(url):
        return True
    return bool(
        re.fullmatch(
            r"https://(?:www\.)?youtube\.com/playlist\?list=[A-Za-z0-9_-]+(?:[&#].*)?",
            url.strip(),
            flags=re.IGNORECASE,
        )
    )


def _is_included_in_hub(row: dict) -> bool:
    value = row.get("include_in_hub", "").strip().lower()
    return value in {"yes", "true", "1"} or value.startswith("yes_")


def _media_family(value: str) -> str:
    normalized = value.strip().lower()
    if "video" in normalized:
        return "video"
    if "audio" in normalized or "podcast" in normalized:
        return "audio"
    if "article" in normalized:
        return "article"
    return normalized

def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1 and token not in STOPWORDS
    }


def _relevance_score(query_tokens: set[str], candidate: dict) -> int:
    weighted_fields = (
        (candidate.get("title", ""), 4),
        (candidate.get("authority_cluster", ""), 4),
        (candidate.get("authority_allowed_use", ""), 2),
        (candidate.get("outlet", ""), 1),
        (candidate.get("notes", ""), 1),
    )
    return sum(
        len(query_tokens & _tokens(value)) * weight
        for value, weight in weighted_fields
    )


def _selector_command(
    topic: str,
    *,
    title: str,
    objective: str,
    limit: int,
) -> str:
    parts = [
        "python",
        "data_sources/modules/fred_authority_selector.py",
        topic,
    ]
    if title:
        parts.extend(("--title", title))
    if objective:
        parts.extend(("--objective", objective))
    parts.extend(("--slate", "--limit", str(limit)))
    return " ".join(shlex.quote(part) for part in parts)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rank vault-verified Fred Voccola authority evidence."
    )
    parser.add_argument("topic", help="Article topic or target query.")
    parser.add_argument("--title", default="", help="Working article title.")
    parser.add_argument("--objective", default="", help="Article objective.")
    parser.add_argument("--vault-root", help="Simpro Brand Context vault root.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum candidates.")
    parser.add_argument(
        "--slate",
        action="store_true",
        help="Print the sidecar-ready selection block.",
    )
    parser.add_argument(
        "--selected-id",
        help="Explicitly record one verified candidate in slate output.",
    )
    return parser


def _main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.slate:
            print(
                build_fred_authority_slate(
                    args.topic,
                    title=args.title,
                    objective=args.objective,
                    vault_root=args.vault_root,
                    limit=args.limit,
                    selected_id=args.selected_id,
                )
            )
        else:
            print(
                json.dumps(
                    select_fred_authority(
                        args.topic,
                        title=args.title,
                        objective=args.objective,
                        vault_root=args.vault_root,
                        limit=args.limit,
                    ),
                    indent=2,
                )
            )
    except FredAuthorityDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
