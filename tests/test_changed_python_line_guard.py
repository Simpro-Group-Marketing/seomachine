from pathlib import Path

from tools.check_changed_python_lines import oversized_files, physical_line_count


def test_physical_line_count_counts_blank_lines(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_bytes(b"first\n\nthird\n")

    assert physical_line_count(source) == 3


def test_oversized_files_reports_only_files_above_limit(tmp_path: Path) -> None:
    passing = tmp_path / "passing.py"
    failing = tmp_path / "failing.py"
    passing.write_text("one\ntwo\n", encoding="utf-8")
    failing.write_text("one\ntwo\nthree\n", encoding="utf-8")

    assert oversized_files([passing, failing], limit=2) == [(failing, 3)]
