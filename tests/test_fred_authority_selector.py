import csv
import hashlib
import json
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from data_sources.modules.fred_authority_selector import (
    FredAuthorityDataError,
    _main,
    _resolve_vault_root,
    build_fred_authority_slate,
    select_fred_authority,
)


INVENTORY_FIELDS = [
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
]

AUTHORITY_FIELDS = [
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
]


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_vault_fixture(root: Path) -> Path:
    inventory_path = root / "indexes" / "fred-voccola-media-inventory.csv"
    authority_path = root / "indexes" / "authority-signal-matrix.csv"
    manifest_path = root / "indexes" / "agent-retrieval-manifest.jsonl"

    _write_csv(
        inventory_path,
        INVENTORY_FIELDS,
        [
            {
                "inventory_id": "FVMI-001",
                "media_type": "article",
                "authority_id": "AUTH-001",
                "source_layer": "public_pr",
                "outlet": "Field Service News",
                "title": "Why skilled trades need better workforce technology",
                "url_or_locator": "https://example.com/skilled-trades",
                "date": "2026-01-01",
                "recommended_brand": "Simpro",
                "evidence_status": "source_visible",
                "public_use_status": "usable_for_eeat_authority_support",
                "include_in_hub": "yes",
                "notes": "",
            },
            {
                "inventory_id": "FVMI-002",
                "media_type": "article",
                "authority_id": "AUTH-002",
                "source_layer": "public_pr",
                "outlet": "Finance Daily",
                "title": "Private equity market conditions",
                "url_or_locator": "https://example.com/finance",
                "date": "2026-01-02",
                "recommended_brand": "Simpro",
                "evidence_status": "source_visible",
                "public_use_status": "usable_for_eeat_authority_support",
                "include_in_hub": "yes",
                "notes": "",
            },
            {
                "inventory_id": "FVMI-003",
                "media_type": "video",
                "authority_id": "",
                "source_layer": "youtube_playlist",
                "outlet": "YouTube",
                "title": "Fred Voccola on field service leadership",
                "url_or_locator": "https://www.youtube.com/watch?v=abc123XYZ00",
                "date": "2026-01-03",
                "recommended_brand": "Simpro",
                "evidence_status": "playlist_verified_public",
                "public_use_status": "public_curated_playlist_asset",
                "include_in_hub": "yes",
                "notes": "Public and embeddable",
            },
            {
                "inventory_id": "FVMI-004",
                "media_type": "article",
                "authority_id": "AUTH-004",
                "source_layer": "internal",
                "outlet": "Internal",
                "title": "Internal workforce memo",
                "url_or_locator": "raw/internal.md",
                "date": "2026-01-04",
                "recommended_brand": "Simpro",
                "evidence_status": "internal_only",
                "public_use_status": "blocked",
                "include_in_hub": "no",
                "notes": "",
            },
            {
                "inventory_id": "FVMI-005",
                "media_type": "article",
                "authority_id": "AUTH-005",
                "source_layer": "syndicated",
                "outlet": "Syndication Wire",
                "title": "Syndicated skilled trades placement",
                "url_or_locator": "https://example.com/syndicated",
                "date": "2026-01-05",
                "recommended_brand": "Simpro",
                "evidence_status": "placement_only",
                "public_use_status": "syndicated_placement_only",
                "include_in_hub": "yes",
                "notes": "",
            },
            {
                "inventory_id": "FVMI-006",
                "media_type": "article",
                "authority_id": "AUTH-006",
                "source_layer": "public_pr",
                "outlet": "Trade News",
                "title": "Skilled trades operations",
                "url_or_locator": "https://example.com/other-brand",
                "date": "2026-01-06",
                "recommended_brand": "BigChange",
                "evidence_status": "source_visible",
                "public_use_status": "usable_for_eeat_authority_support",
                "include_in_hub": "yes",
                "notes": "",
            },
        ],
    )
    _write_csv(
        authority_path,
        AUTHORITY_FIELDS,
        [
            {
                "authority_id": "AUTH-001",
                "cluster": "skilled trades workforce technology",
                "outlet": "Field Service News",
                "headline": "Why skilled trades need better workforce technology",
                "canonical_url": "https://example.com/skilled-trades",
                "date": "2026-01-01",
                "country": "US",
                "recommended_brand": "Simpro",
                "total_placements": "1",
                "also_covered_by": "",
                "eeat_dimension": "Expertise; Authority",
                "evidence_status": "source_visible",
                "allowed_use": "Industry observation with contextual citation",
                "public_use_status": "usable_for_eeat_authority_support",
                "source_node": "wiki/source.md",
                "raw_file": "raw/source.md",
                "notes": "",
            },
            {
                "authority_id": "AUTH-002",
                "cluster": "finance and investment",
                "outlet": "Finance Daily",
                "headline": "Private equity market conditions",
                "canonical_url": "https://example.com/finance",
                "date": "2026-01-02",
                "country": "US",
                "recommended_brand": "Simpro",
                "total_placements": "1",
                "also_covered_by": "",
                "eeat_dimension": "Authority",
                "evidence_status": "source_visible",
                "allowed_use": "Industry observation with contextual citation",
                "public_use_status": "usable_for_eeat_authority_support",
                "source_node": "wiki/finance.md",
                "raw_file": "raw/finance.md",
                "notes": "",
            },
            {
                "authority_id": "AUTH-004",
                "cluster": "workforce",
                "outlet": "Internal",
                "headline": "Internal workforce memo",
                "canonical_url": "",
                "date": "2026-01-04",
                "country": "US",
                "recommended_brand": "Simpro",
                "total_placements": "0",
                "also_covered_by": "",
                "eeat_dimension": "Expertise",
                "evidence_status": "internal_only",
                "allowed_use": "internal only",
                "public_use_status": "blocked",
                "source_node": "wiki/internal.md",
                "raw_file": "raw/internal.md",
                "notes": "",
            },
            {
                "authority_id": "AUTH-005",
                "cluster": "skilled trades",
                "outlet": "Syndication Wire",
                "headline": "Syndicated skilled trades placement",
                "canonical_url": "https://example.com/syndicated",
                "date": "2026-01-05",
                "country": "US",
                "recommended_brand": "Simpro",
                "total_placements": "20",
                "also_covered_by": "",
                "eeat_dimension": "Authority",
                "evidence_status": "placement_only",
                "allowed_use": "syndicated placement only",
                "public_use_status": "syndicated_placement_only",
                "source_node": "wiki/syndicated.md",
                "raw_file": "raw/syndicated.md",
                "notes": "",
            },
            {
                "authority_id": "AUTH-006",
                "cluster": "skilled trades",
                "outlet": "Trade News",
                "headline": "Skilled trades operations",
                "canonical_url": "https://example.com/other-brand",
                "date": "2026-01-06",
                "country": "UK",
                "recommended_brand": "BigChange",
                "total_placements": "1",
                "also_covered_by": "",
                "eeat_dimension": "Authority",
                "evidence_status": "source_visible",
                "allowed_use": "Industry observation with contextual citation",
                "public_use_status": "usable_for_eeat_authority_support",
                "source_node": "wiki/other.md",
                "raw_file": "raw/other.md",
                "notes": "",
            },
        ],
    )
    manifest_path.write_text(
        json.dumps(
            {
                "record_type": "manifest",
                "schema": "simpro-agent-retrieval-manifest/v1",
                "control_inputs": [
                    {
                        "path": "indexes/fred-voccola-media-inventory.csv",
                        "sha256": _sha256(inventory_path),
                    },
                    {
                        "path": "indexes/authority-signal-matrix.csv",
                        "sha256": _sha256(authority_path),
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return root



def refresh_manifest(vault: Path) -> None:
    manifest_path = vault / "indexes" / "agent-retrieval-manifest.jsonl"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8").splitlines()[0])
    for item in manifest["control_inputs"]:
        item["sha256"] = _sha256(vault / item["path"])
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
class FredAuthoritySelectorTests(unittest.TestCase):
    def test_topic_fit_ranks_relevant_authority_first(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            results = select_fred_authority(
                "skilled trades workforce",
                title="How workforce technology supports field service teams",
                objective="Explain labor challenges in the trades",
                vault_root=vault,
                limit=5,
            )

        self.assertEqual(results[0]["inventory_id"], "FVMI-001")
        self.assertEqual(results[0]["authority_id"], "AUTH-001")
        self.assertGreater(results[0]["score"], results[1]["score"])

    def test_slate_defaults_to_explicit_no_selection(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            slate = build_fred_authority_slate(
                "skilled trades workforce",
                title="Workforce technology",
                objective="Explain labor challenges",
                vault_root=vault,
                limit=3,
            )

        self.assertIn("## Fred Voccola Authority Selection", slate)
        self.assertIn("- Evaluation status: completed", slate)
        self.assertIn("- Selected: [none]", slate)
        self.assertIn("- Intended use: none", slate)

    def test_status_brand_and_syndication_filters_fail_closed(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            results = select_fred_authority("skilled trades", vault_root=vault, limit=10)

        ids = {result["inventory_id"] for result in results}
        self.assertEqual(ids, {"FVMI-001", "FVMI-002", "FVMI-003"})

    def test_public_playlist_asset_is_discovery_only_without_authority_join(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            result = next(
                item
                for item in select_fred_authority(
                    "field service leadership",
                    vault_root=vault,
                    limit=5,
                )
                if item["inventory_id"] == "FVMI-003"
            )

        self.assertTrue(result["playlist_only"])
        self.assertEqual(result["authority_id"], "")
        self.assertEqual(result["authority_kind"], "discovery_or_embed_only")

    def test_stale_manifest_hash_raises(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            inventory = vault / "indexes" / "fred-voccola-media-inventory.csv"
            inventory.write_text(inventory.read_text(encoding="utf-8") + "\n", encoding="utf-8")

            with self.assertRaisesRegex(FredAuthorityDataError, "stale"):
                select_fred_authority("field service", vault_root=vault)

    def test_missing_manifest_raises(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            (vault / "indexes" / "agent-retrieval-manifest.jsonl").unlink()

            with self.assertRaisesRegex(FredAuthorityDataError, "manifest"):
                select_fred_authority("field service", vault_root=vault)

    def test_vault_path_precedence_is_explicit_then_env_then_default(self):
        explicit = Path("C:/explicit-vault")
        with patch.dict(
            os.environ,
            {"SIMPRO_BRAND_CONTEXT_VAULT": "C:/environment-vault"},
            clear=False,
        ):
            self.assertEqual(_resolve_vault_root(explicit), explicit)
            self.assertEqual(
                _resolve_vault_root(None),
                Path("C:/environment-vault"),
            )

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                _resolve_vault_root(None),
                Path(
                    "C:/Users/patrick.grueschow/Desktop/Obsidian/"
                    "Simpro Brand Context"
                ),
            )

    def test_cli_slate_keeps_selection_none_without_selected_id(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            output = StringIO()
            with redirect_stdout(output):
                exit_code = _main(
                    [
                        "skilled trades",
                        "--title",
                        "Workforce technology",
                        "--objective",
                        "Explain labor challenges",
                        "--vault-root",
                        str(vault),
                        "--slate",
                        "--limit",
                        "2",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("- Selected: [none]", output.getvalue())


    def test_live_vault_include_flags_and_playlist_collection_are_eligible(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            inventory_path = vault / "indexes" / "fred-voccola-media-inventory.csv"
            with inventory_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                if row["inventory_id"] == "FVMI-001":
                    row["include_in_hub"] = "yes_fred_media"
                    row["media_type"] = "article_authority"
                if row["inventory_id"] == "FVMI-003":
                    row["include_in_hub"] = "yes_playlist"
                    row["media_type"] = "curated_playlist"
                    row["url_or_locator"] = "https://www.youtube.com/playlist?list=PL123"
            _write_csv(inventory_path, INVENTORY_FIELDS, rows)
            manifest_path = vault / "indexes" / "agent-retrieval-manifest.jsonl"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8").splitlines()[0])
            for item in manifest["control_inputs"]:
                item["sha256"] = _sha256(vault / item["path"])
            manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

            results = select_fred_authority("workforce technology", vault_root=vault, limit=10)

        ids = {result["inventory_id"] for result in results}
        self.assertIn("FVMI-001", ids)
        self.assertIn("FVMI-003", ids)
        playlist = next(result for result in results if result["inventory_id"] == "FVMI-003")
        self.assertTrue(playlist["playlist_only"])

    def test_blank_authority_join_metadata_excludes_candidate(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            authority_path = vault / "indexes" / "authority-signal-matrix.csv"
            with authority_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                if row["authority_id"] == "AUTH-001":
                    row["headline"] = ""
            _write_csv(authority_path, AUTHORITY_FIELDS, rows)
            refresh_manifest(vault)

            results = select_fred_authority(
                "skilled trades workforce technology",
                vault_root=vault,
                limit=10,
            )

        self.assertNotIn(
            "FVMI-001",
            {result["inventory_id"] for result in results},
        )


    def test_duplicate_inventory_or_authority_ids_fail_closed(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            inventory_path = vault / "indexes" / "fred-voccola-media-inventory.csv"
            with inventory_path.open("r", encoding="utf-8", newline="") as handle:
                inventory_rows = list(csv.DictReader(handle))
            _write_csv(
                inventory_path,
                INVENTORY_FIELDS,
                [*inventory_rows, dict(inventory_rows[0])],
            )
            refresh_manifest(vault)
            with self.assertRaisesRegex(FredAuthorityDataError, "duplicate inventory_id"):
                select_fred_authority("workforce", vault_root=vault)

        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            authority_path = vault / "indexes" / "authority-signal-matrix.csv"
            with authority_path.open("r", encoding="utf-8", newline="") as handle:
                authority_rows = list(csv.DictReader(handle))
            _write_csv(
                authority_path,
                AUTHORITY_FIELDS,
                [*authority_rows, dict(authority_rows[0])],
            )
            refresh_manifest(vault)
            with self.assertRaisesRegex(FredAuthorityDataError, "duplicate authority_id"):
                select_fred_authority("workforce", vault_root=vault)

    def test_missing_required_csv_column_fails_closed(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            authority_path = vault / "indexes" / "authority-signal-matrix.csv"
            with authority_path.open("r", encoding="utf-8", newline="") as handle:
                authority_rows = list(csv.DictReader(handle))
            fields = [field for field in AUTHORITY_FIELDS if field != "allowed_use"]
            projected = [{field: row[field] for field in fields} for row in authority_rows]
            _write_csv(authority_path, fields, projected)
            refresh_manifest(vault)

            with self.assertRaisesRegex(FredAuthorityDataError, "missing required columns"):
                select_fred_authority("workforce", vault_root=vault)

if __name__ == "__main__":
    unittest.main()
