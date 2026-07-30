import csv
import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.fred_authority_guard import check_content, should_fail
from tests.test_fred_authority_selector import (
    AUTHORITY_FIELDS,
    INVENTORY_FIELDS,
    write_vault_fixture,
)


ARTICLE_URL = "https://example.com/skilled-trades"
PLAYLIST_URL = "https://www.youtube.com/watch?v=abc123XYZ00"
VIDEO_URL = "https://www.youtube.com/watch?v=videoABC123"
ARTICLE_QUOTE = "Trade businesses need connected workforce technology."
VIDEO_QUOTE = "Technicians need useful context before they arrive on site."


def _refresh_manifest(vault: Path) -> None:
    manifest_path = vault / "indexes" / "agent-retrieval-manifest.jsonl"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8").splitlines()[0])
    for item in manifest["control_inputs"]:
        controlled = vault / item["path"]
        item["sha256"] = hashlib.sha256(controlled.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")


def _append_csv_row(path: Path, fields: list[str], row: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writerow(row)


def add_verified_video(vault: Path) -> None:
    _append_csv_row(
        vault / "indexes" / "fred-voccola-media-inventory.csv",
        INVENTORY_FIELDS,
        {
            "inventory_id": "FVMI-007",
            "media_type": "video",
            "authority_id": "AUTH-007",
            "source_layer": "public_interview",
            "outlet": "Field Service Today",
            "title": "Fred Voccola on technician productivity",
            "url_or_locator": VIDEO_URL,
            "date": "2026-01-07",
            "recommended_brand": "Simpro",
            "evidence_status": "source_checked_usable_authority_signal",
            "public_use_status": "usable_for_eeat_authority_support",
            "include_in_hub": "yes",
            "notes": "Public and embeddable interview",
        },
    )
    _append_csv_row(
        vault / "indexes" / "authority-signal-matrix.csv",
        AUTHORITY_FIELDS,
        {
            "authority_id": "AUTH-007",
            "cluster": "field service technician productivity",
            "outlet": "Field Service Today",
            "headline": "Fred Voccola on technician productivity",
            "canonical_url": VIDEO_URL,
            "date": "2026-01-07",
            "country": "US",
            "recommended_brand": "Simpro",
            "total_placements": "1",
            "also_covered_by": "",
            "eeat_dimension": "Expertise; Authority",
            "evidence_status": "source_checked_usable_authority_signal",
            "allowed_use": "Interview observations with transcript evidence",
            "public_use_status": "usable_for_eeat_authority_support",
            "source_node": "wiki/video.md",
            "raw_file": "raw/video.md",
            "notes": "",
        },
    )
    _refresh_manifest(vault)


def selection_block(
    *,
    selected: str = "none",
    fit: str = "No candidate directly supports this article's narrow tax compliance topic.",
    intended_use: str = "none",
    target: str = "not applicable",
    authority_id: str = "none",
    url: str = "not applicable",
    evidence_status: str = "not applicable",
    method: str = "not_applicable",
    excerpt: str = "not applicable",
    locator: str = "not applicable",
    playback: str = "not_applicable",
    exact_quote: str = "not applicable",
    embed: str = "no",
    video_object: str = "not applicable",
    evaluation: str = "completed",
) -> str:
    return f"""## Fred Voccola Authority Selection
- Selector command: python data_sources/modules/fred_authority_selector.py "topic" --title "Title" --objective "Objective" --slate --limit 5
- Evaluation status: {evaluation}
- Top candidates: [FVMI-001, FVMI-003]
- Selected: [{selected}]
- Fit decision: {fit}
- Intended use: {intended_use}
- Target section: {target}
- Authority row: [{authority_id}]
- Public URL: {url}
- Evidence status: {evidence_status}
- Verification method: {method}
- Evidence excerpt: {excerpt}
- Timestamp or locator: {locator}
- Playback verified: {playback}
- Exact quote: {exact_quote}
- Embed decision: {embed}
- VideoObject: {video_object}
"""


def article_quote_block(**overrides: str) -> str:
    values = {
        "selected": "FVMI-001",
        "fit": "The source directly supports the workforce technology section.",
        "intended_use": "exact_quote",
        "target": "Why workforce technology matters",
        "authority_id": "AUTH-001",
        "url": ARTICLE_URL,
        "evidence_status": "source_visible",
        "method": "source_visible_article_text",
        "excerpt": ARTICLE_QUOTE,
        "locator": "Article paragraph 4",
        "exact_quote": ARTICLE_QUOTE,
    }
    values.update(overrides)
    return selection_block(**values)


def video_quote_block(**overrides: str) -> str:
    values = {
        "selected": "FVMI-007",
        "fit": "The interview directly supports the technician productivity section.",
        "intended_use": "exact_quote",
        "target": "Technician productivity",
        "authority_id": "AUTH-007",
        "url": VIDEO_URL,
        "evidence_status": "source_checked_usable_authority_signal",
        "method": "transcript_and_playback",
        "excerpt": VIDEO_QUOTE,
        "locator": "00:04:12",
        "playback": "yes",
        "exact_quote": VIDEO_QUOTE,
    }
    values.update(overrides)
    return selection_block(**values)


def embedded_article(*, autoplay: bool = False, schema: bool = True) -> str:
    schema_line = "  - VideoObject\n" if schema else ""
    autoplay_suffix = "?autoplay=1" if autoplay else ""
    return f"""---
schema_notes:
  - BlogPosting
{schema_line}---
# Article

## Field service leadership

Fred Voccola discusses field service leadership in this interview.

<div class="video-embed" style="aspect-ratio: 16 / 9; width: 100%;">
  <iframe src="https://www.youtube-nocookie.com/embed/abc123XYZ00{autoplay_suffix}" title="Fred Voccola on field service leadership" loading="lazy" allowfullscreen></iframe>
</div>

[Watch Fred Voccola on field service leadership]({PLAYLIST_URL}).
"""


class FredAuthorityGuardTests(unittest.TestCase):
    def test_missing_selection_block_fails(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            findings = check_content("# Article\n\nBody.", vault_root=vault)

        self.assertTrue(any(item["rule_id"] == "fred_authority_selection_missing" for item in findings))

    def test_selected_none_with_substantive_fit_reason_passes(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            findings = check_content(
                "# Article\n\nTax compliance details.",
                proof_content=selection_block(),
                vault_root=vault,
            )

        self.assertEqual(findings, [])

    def test_selected_none_with_generic_reason_fails(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            findings = check_content(
                "# Article\n\nBody.",
                proof_content=selection_block(fit="Not used."),
                vault_root=vault,
            )

        self.assertTrue(any(item["rule_id"] == "fred_authority_none_reason_weak" for item in findings))

    def test_unknown_selected_id_and_stale_manifest_fail(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            unknown = check_content(
                "# Article\n\nBody.",
                proof_content=article_quote_block(selected="FVMI-999"),
                vault_root=vault,
            )
            inventory = vault / "indexes" / "fred-voccola-media-inventory.csv"
            inventory.write_text(inventory.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            stale = check_content(
                "# Article\n\nBody.",
                proof_content=selection_block(),
                vault_root=vault,
            )

        self.assertTrue(any(item["rule_id"] == "fred_authority_id_unknown" for item in unknown))
        self.assertTrue(any(item["rule_id"] == "fred_authority_vault_unavailable" for item in stale))

    def test_current_vault_fields_must_match_sidecar(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            content = f'# Article\n\n[Fred Voccola]({ARTICLE_URL}) said, "{ARTICLE_QUOTE}"'
            findings = check_content(
                content,
                proof_content=article_quote_block(
                    authority_id="AUTH-WRONG",
                    url="https://example.com/wrong",
                    evidence_status="wrong_status",
                ),
                vault_root=vault,
            )

        rules = {item["rule_id"] for item in findings}
        self.assertIn("fred_authority_row_mismatch", rules)
        self.assertIn("fred_authority_url_mismatch", rules)
        self.assertIn("fred_authority_status_mismatch", rules)

    def test_syndicated_placement_cannot_be_selected(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            findings = check_content(
                "# Article\n\nBody.",
                proof_content=article_quote_block(
                    selected="FVMI-005",
                    authority_id="AUTH-005",
                    url="https://example.com/syndicated",
                    evidence_status="placement_only",
                ),
                vault_root=vault,
            )

        self.assertTrue(any(item["rule_id"] == "fred_authority_not_usable" for item in findings))

    def test_unavailable_vault_fails_closed(self):
        with TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing-vault"
            findings = check_content(
                "# Article\n\nBody.",
                proof_content=selection_block(),
                vault_root=missing,
            )

        self.assertTrue(should_fail(findings))
        self.assertTrue(any(item["rule_id"] == "fred_authority_vault_unavailable" for item in findings))

    def test_exact_article_quote_with_visible_text_evidence_passes(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            content = f'# Article\n\n[Fred Voccola]({ARTICLE_URL}) said, "{ARTICLE_QUOTE}"'
            findings = check_content(
                content,
                proof_content=article_quote_block(),
                vault_root=vault,
            )

        self.assertEqual(findings, [])

    def test_exact_quote_and_source_link_in_different_paragraphs_fails(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            content = (
                f'# Article\n\nFred Voccola said, "{ARTICLE_QUOTE}"\n\n'
                f'[Read the source]({ARTICLE_URL}).'
            )
            findings = check_content(
                content,
                proof_content=article_quote_block(),
                vault_root=vault,
            )

        self.assertTrue(
            any(
                item["rule_id"] == "fred_authority_public_link_missing"
                for item in findings
            )
        )

    def test_video_quote_requires_transcript_timestamp_and_playback(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            add_verified_video(vault)
            content = f'# Article\n\n[Fred Voccola]({VIDEO_URL}) said, "{VIDEO_QUOTE}"'
            cases = {
                "method": video_quote_block(method="paraphrase_evidence"),
                "locator": video_quote_block(locator="not applicable"),
                "playback": video_quote_block(playback="not_applicable"),
                "excerpt": video_quote_block(excerpt="not applicable"),
            }
            for label, proof in cases.items():
                with self.subTest(label=label):
                    findings = check_content(content, proof_content=proof, vault_root=vault)
                    self.assertTrue(should_fail(findings))

    def test_verified_video_quote_passes(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            add_verified_video(vault)
            content = f'# Article\n\n[Fred Voccola]({VIDEO_URL}) said, "{VIDEO_QUOTE}"'
            findings = check_content(
                content,
                proof_content=video_quote_block(),
                vault_root=vault,
            )

        self.assertEqual(findings, [])

    def test_linked_supported_paraphrase_passes(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            content = f"# Article\n\n[Fred Voccola argues]({ARTICLE_URL}) that connected workforce tools can help skilled trades teams coordinate work."
            proof = article_quote_block(
                intended_use="paraphrased_industry_observation",
                method="paraphrase_evidence",
                excerpt="Connected tools help skilled trades businesses coordinate their workforce.",
                locator="Article paragraph 4",
                exact_quote="not applicable",
            )
            findings = check_content(content, proof_content=proof, vault_root=vault)

        self.assertEqual(findings, [])

    def test_unlinked_or_unsupported_paraphrase_fails(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            content = "# Article\n\nFred Voccola argues that connected workforce tools improve coordination."
            findings = check_content(
                content,
                proof_content=article_quote_block(
                    intended_use="paraphrased_industry_observation",
                    method="paraphrase_evidence",
                    excerpt="not applicable",
                    exact_quote="not applicable",
                ),
                vault_root=vault,
            )

        rules = {item["rule_id"] for item in findings}
        self.assertIn("fred_authority_public_link_missing", rules)
        self.assertIn("fred_authority_paraphrase_evidence_missing", rules)

    def test_content_first_playlist_embed_with_video_object_passes(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            proof = selection_block(
                selected="FVMI-003",
                fit="The video directly supports the field service leadership section.",
                intended_use="embed",
                target="Field service leadership",
                url=PLAYLIST_URL,
                evidence_status="playlist_verified_public",
                embed="yes",
                video_object="required",
            )
            findings = check_content(
                embedded_article(),
                proof_content=proof,
                vault_root=vault,
            )

        self.assertEqual(findings, [])

    def test_embed_rejects_autoplay_missing_schema_and_wrong_provider(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            proof = selection_block(
                selected="FVMI-003",
                fit="The video directly supports the field service leadership section.",
                intended_use="embed",
                target="Field service leadership",
                url=PLAYLIST_URL,
                evidence_status="playlist_verified_public",
                embed="yes",
                video_object="required",
            )
            autoplay = check_content(
                embedded_article(autoplay=True),
                proof_content=proof,
                vault_root=vault,
            )
            no_schema = check_content(
                embedded_article(schema=False),
                proof_content=proof,
                vault_root=vault,
            )
            wrong_provider = check_content(
                embedded_article().replace("youtube-nocookie.com", "player.vimeo.com"),
                proof_content=proof,
                vault_root=vault,
            )

        self.assertTrue(
            any(item["rule_id"] == "fred_authority_embed_autoplay" for item in autoplay)
        )
        self.assertTrue(
            any(
                item["rule_id"] == "fred_authority_video_object_missing"
                for item in no_schema
            )
        )
        self.assertTrue(
            any(
                item["rule_id"] == "fred_authority_embed_provider_invalid"
                for item in wrong_provider
            )
        )

    def test_video_object_is_prohibited_without_video_embed(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            content = (
                "---\nschema_notes:\n  - BlogPosting\n  - VideoObject\n---\n"
                "# Article\n\nBody."
            )
            findings = check_content(
                content,
                proof_content=selection_block(),
                vault_root=vault,
            )

        self.assertTrue(
            any(
                item["rule_id"] == "fred_authority_video_object_without_embed"
                for item in findings
            )
        )


    def test_video_object_with_non_fred_video_embed_is_not_treated_as_orphaned(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            content = (
                "---\nschema_notes:\n  - BlogPosting\n  - VideoObject\n---\n"
                "# Article\n\n"
                '<iframe src="https://player.vimeo.com/video/123456" '
                'title="Independent field service training video"></iframe>'
            )
            findings = check_content(
                content,
                proof_content=selection_block(),
                vault_root=vault,
            )

        self.assertFalse(
            any(
                item["rule_id"] == "fred_authority_video_object_without_embed"
                for item in findings
            )
        )

    def test_selected_none_rejects_unlinked_public_fred_quote(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            content = f'# Article\n\nFred Voccola said, "{ARTICLE_QUOTE}"'
            findings = check_content(
                content,
                proof_content=selection_block(),
                vault_root=vault,
            )

        self.assertTrue(
            any(
                item["rule_id"] == "fred_authority_public_use_without_selection"
                for item in findings
            )
        )

    def test_video_quote_requires_well_formed_timestamp(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            add_verified_video(vault)
            content = f'# Article\n\n[Fred Voccola]({VIDEO_URL}) said, "{VIDEO_QUOTE}"'
            for locator in ("article paragraph 4", "00:61", "1:02:75"):
                with self.subTest(locator=locator):
                    findings = check_content(
                        content,
                        proof_content=video_quote_block(locator=locator),
                        vault_root=vault,
                    )
                    self.assertTrue(
                        any(
                            item["rule_id"] == "fred_authority_video_timestamp_invalid"
                            for item in findings
                        )
                    )

    def test_embed_video_id_requires_exact_path_match(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            proof = selection_block(
                selected="FVMI-003",
                fit="The video directly supports the field service leadership section.",
                intended_use="embed",
                target="Field service leadership",
                url=PLAYLIST_URL,
                evidence_status="playlist_verified_public",
                embed="yes",
                video_object="required",
            )
            content = embedded_article().replace(
                "/embed/abc123XYZ00",
                "/embed/abc123XYZ00extra",
            )
            findings = check_content(content, proof_content=proof, vault_root=vault)

        self.assertTrue(
            any(
                item["rule_id"] == "fred_authority_embed_video_mismatch"
                for item in findings
            )
        )

    def test_selected_embed_requires_its_own_responsive_wrapper(self):
        with TemporaryDirectory() as temp_dir:
            vault = write_vault_fixture(Path(temp_dir))
            proof = selection_block(
                selected="FVMI-003",
                fit="The video directly supports the field service leadership section.",
                intended_use="embed",
                target="Field service leadership",
                url=PLAYLIST_URL,
                evidence_status="playlist_verified_public",
                embed="yes",
                video_object="required",
            )
            content = embedded_article().replace(
                '<div class="video-embed" style="aspect-ratio: 16 / 9; width: 100%;">',
                '<div class="video-embed">',
            )
            content += '\n<div style="aspect-ratio: 16 / 9;">Unrelated media</div>\n'
            findings = check_content(content, proof_content=proof, vault_root=vault)

        self.assertTrue(
            any(
                item["rule_id"] == "fred_authority_embed_responsive_missing"
                for item in findings
            )
        )

if __name__ == "__main__":
    unittest.main()
