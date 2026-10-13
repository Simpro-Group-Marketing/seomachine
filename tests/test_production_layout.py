from pathlib import Path
import json, pytest
from data_sources.modules.production.layout import Layout, LayoutError, load_or_create_run_id

def _article(root: Path, rel: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# T\n", encoding="utf-8")
    return path

def test_layout_derives_slug_date_mode_and_paths(tmp_path):
    layout = Layout.for_article(_article(tmp_path, "drafts/what-is-simpro-2026-10-05.md"), tmp_path)
    assert (layout.slug, layout.date, layout.workflow_mode) == ("what-is-simpro", "2026-10-05", "new")
    assert layout.bom == tmp_path / "research/production-bom-what-is-simpro-2026-10-05.json"
    assert layout.context_pack == tmp_path / "research/context-pack-what-is-simpro.json"

def test_rewrite_folder_sets_rewrite_mode(tmp_path):
    assert Layout.for_article(_article(tmp_path, "rewrites/a-b-2026-01-02.md"), tmp_path).workflow_mode == "rewrite"

@pytest.mark.parametrize("rel", ["published/a-2026-01-02.md", "drafts/no-date.md", "drafts/a-2026-13-40.md"])
def test_invalid_article_location_or_name_raises(tmp_path, rel):
    with pytest.raises(LayoutError):
        Layout.for_article(_article(tmp_path, rel), tmp_path)

def test_run_id_is_minted_once_and_reused(tmp_path):
    layout = Layout.for_article(_article(tmp_path, "drafts/a-2026-01-02.md"), tmp_path)
    first = load_or_create_run_id(layout)
    assert load_or_create_run_id(layout) == first
    assert json.loads(layout.run_state.read_text(encoding="utf-8"))["run_id"] == first

def test_release_dir_never_reuses_existing(tmp_path):
    layout = Layout.for_article(_article(tmp_path, "drafts/a-2026-01-02.md"), tmp_path)
    first = layout.release_dir("abcdef12-0000")
    first.mkdir(parents=True)
    assert layout.release_dir("abcdef12-0000").name.endswith("-2")

def _write_raw_run_state(layout, text: str) -> None:
    layout.run_state.parent.mkdir(parents=True, exist_ok=True)
    layout.run_state.write_text(text, encoding="utf-8")

def test_corrupt_run_state_json_raises(tmp_path):
    layout = Layout.for_article(_article(tmp_path, "drafts/a-2026-01-02.md"), tmp_path)
    _write_raw_run_state(layout, "{not json")
    with pytest.raises(LayoutError, match="run state"):
        load_or_create_run_id(layout)

def test_run_state_directory_in_place_raises(tmp_path):
    layout = Layout.for_article(_article(tmp_path, "drafts/a-2026-01-02.md"), tmp_path)
    layout.run_state.mkdir(parents=True)
    with pytest.raises(LayoutError, match="run state"):
        load_or_create_run_id(layout)

@pytest.mark.parametrize("text", ["[]", '{"schema": "simpro-production-run/v1"}', '{"run_id": ""}', '{"run_id": 7}'])
def test_invalid_run_state_payload_raises(tmp_path, text):
    layout = Layout.for_article(_article(tmp_path, "drafts/a-2026-01-02.md"), tmp_path)
    _write_raw_run_state(layout, text)
    with pytest.raises(LayoutError, match="run state"):
        load_or_create_run_id(layout)

def test_explicit_run_id_overwrites_corrupt_file(tmp_path):
    layout = Layout.for_article(_article(tmp_path, "drafts/a-2026-01-02.md"), tmp_path)
    _write_raw_run_state(layout, "{not json")
    assert load_or_create_run_id(layout, run_id="explicit-1") == "explicit-1"
    assert json.loads(layout.run_state.read_text(encoding="utf-8"))["run_id"] == "explicit-1"
    assert load_or_create_run_id(layout) == "explicit-1"

def test_explicit_run_id_overwrites_valid_stored_id(tmp_path):
    layout = Layout.for_article(_article(tmp_path, "drafts/a-2026-01-02.md"), tmp_path)
    load_or_create_run_id(layout)
    assert load_or_create_run_id(layout, run_id="explicit-2") == "explicit-2"
    assert load_or_create_run_id(layout) == "explicit-2"
