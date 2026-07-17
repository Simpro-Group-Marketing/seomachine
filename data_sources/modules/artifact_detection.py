"""
Artifact Detection Helpers

Shared, non-gate helpers for detecting usable article artifacts: filled
Markdown tables, download/calculator links, placeholder table scaffolds,
and countable body-word offsets. Used by early_artifact_guard and
answer_withholding_guard so scaffold detection cannot drift between them.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Tuple


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_LINE_RE = re.compile(r"^\s{0,3}#{1,6}\s")
BLOCKQUOTE_LINE_RE = re.compile(r"^\s*>")
IMAGE_ONLY_LINE_RE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")
TABLE_LINE_RE = re.compile(r"^\s*\|")
HORIZONTAL_RULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$")
LINK_URL_RE = re.compile(r"\]\([^)]*\)")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[(?P<anchor>[^\]]+)\]\((?P<href>[^)\s]+)[^)]*\)")

DOWNLOAD_FILE_EXT_RE = re.compile(r"\.(?:pdf|xlsx?|docx?|csv|zip|pptx?)(?:[?#]|$)", re.IGNORECASE)
ARTIFACT_ANCHOR_RE = re.compile(
    r"\b(?:download|template|checklist|calculator|worksheet|spreadsheet|cheat sheet|free tool)\b",
    re.IGNORECASE,
)
CALCULATOR_HREF_RE = re.compile(r"/(?:calculator|tools?)(?:/|$)", re.IGNORECASE)

PLACEHOLDER_CELL_RE = re.compile(
    r"^\s*(?:"
    r"enter\b.*|\[?insert\b.*|fill in\b.*|add your\b.*|\[?your\b.*|"
    r"tbd\.?|t\.b\.d\.?|n/?a|varies\b.*|"
    r"x{2,}|\?+|[-–—]|\.{3}|…|value|amount"
    r")\s*$",
    re.IGNORECASE,
)

BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")


@dataclass
class Table:
    start_line: int
    header_cells: List[str]
    data_rows: List[List[str]] = field(default_factory=list)


@dataclass
class DownloadLink:
    line: int
    anchor: str
    href: str


@dataclass
class BulletBlock:
    line: int
    fields: Dict[str, str]


def strip_frontmatter(content: str) -> Tuple[str, int]:
    """Return (body, 1-based line number where the body starts)."""
    match = FRONTMATTER_RE.match(content)
    if not match:
        return content, 1
    consumed = content[: match.end()]
    return content[match.end() :], consumed.count("\n") + 1


def extract_frontmatter(content: str) -> Dict[str, str]:
    """Return normalized frontmatter key/value pairs."""
    match = re.match(r"\A---\s*\n(.*?)\n---\s*", content, re.DOTALL)
    if not match:
        return {}

    values = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace("-", "_").replace(" ", "_")
        values[normalized_key] = value.strip().strip('"').strip("'")
    return values


def countable_words(line: str) -> int:
    """Count prose words on a line under the early-artifact counting rules.

    Headings, blockquotes, image-only lines, table rows, and horizontal
    rules count zero; link URLs are stripped so only anchor text counts.
    """
    if not line.strip():
        return 0
    if (
        HEADING_LINE_RE.match(line)
        or BLOCKQUOTE_LINE_RE.match(line)
        or IMAGE_ONLY_LINE_RE.match(line)
        or TABLE_LINE_RE.match(line)
        or HORIZONTAL_RULE_RE.match(line)
    ):
        return 0
    return len(LINK_URL_RE.sub("]", line).split())


def body_word_offsets(body_lines: List[str]) -> List[int]:
    """Cumulative countable-word offset at the START of each body line."""
    offsets: List[int] = []
    total = 0
    for line in body_lines:
        offsets.append(total)
        total += countable_words(line)
    return offsets


def parse_tables(body_lines: List[str], line_offset: int = 1) -> List[Table]:
    """Parse Markdown pipe tables. line numbers are 1-based file positions
    when line_offset is the file line number of body_lines[0]."""
    tables: List[Table] = []
    index = 0
    while index < len(body_lines) - 1:
        line = body_lines[index]
        next_line = body_lines[index + 1]
        if TABLE_LINE_RE.match(line) and TABLE_SEPARATOR_RE.match(next_line):
            table = Table(
                start_line=index + line_offset,
                header_cells=_split_row(line),
            )
            row_index = index + 2
            while row_index < len(body_lines) and TABLE_LINE_RE.match(body_lines[row_index]):
                if not TABLE_SEPARATOR_RE.match(body_lines[row_index]):
                    table.data_rows.append(_split_row(body_lines[row_index]))
                row_index += 1
            tables.append(table)
            index = row_index
            continue
        index += 1
    return tables


def _split_row(line: str) -> List[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells


def is_placeholder_cell(cell: str) -> bool:
    """True when a table cell withholds its value instead of answering."""
    if not cell.strip():
        return True
    return bool(PLACEHOLDER_CELL_RE.match(cell))


def scaffold_columns(table: Table) -> List[int]:
    """Column indices where >=2 non-empty data cells are >=50% placeholders."""
    if not table.data_rows:
        return []
    column_count = max(len(row) for row in table.data_rows)
    flagged: List[int] = []
    for column in range(column_count):
        cells = [row[column] for row in table.data_rows if column < len(row)]
        non_empty = [cell for cell in cells if cell.strip()]
        if len(non_empty) < 2:
            continue
        placeholders = sum(1 for cell in non_empty if is_placeholder_cell(cell))
        if placeholders * 2 >= len(non_empty):
            flagged.append(column)
    return flagged


def placeholder_cell_ratio(table: Table) -> float:
    """Fraction of non-empty data cells that are placeholders."""
    non_empty = [
        cell for row in table.data_rows for cell in row if cell.strip()
    ]
    if not non_empty:
        return 1.0 if table.data_rows else 0.0
    placeholders = sum(1 for cell in non_empty if is_placeholder_cell(cell))
    return placeholders / len(non_empty)


def table_is_scaffold(table: Table) -> bool:
    """True when the table withholds answers via placeholder cells."""
    if not table.data_rows:
        return False
    if scaffold_columns(table):
        return True
    return placeholder_cell_ratio(table) > 0.5


def table_is_filled(table: Table) -> bool:
    """A usable table: >=1 data row, >=2 columns, not a placeholder scaffold."""
    if not table.data_rows:
        return False
    if len(table.header_cells) < 2:
        return False
    return not table_is_scaffold(table)


def table_has_numeric_cell(table: Table) -> bool:
    """True when any data cell contains a digit (a concrete value)."""
    return any(
        any(char.isdigit() for char in cell)
        for row in table.data_rows
        for cell in row
    )


def find_download_links(body_lines: List[str], line_offset: int = 1) -> List[DownloadLink]:
    """Markdown links whose href or anchor marks a downloadable/tool artifact."""
    links: List[DownloadLink] = []
    for index, line in enumerate(body_lines):
        for match in MARKDOWN_LINK_RE.finditer(line):
            anchor = match.group("anchor")
            href = match.group("href")
            if (
                DOWNLOAD_FILE_EXT_RE.search(href)
                or ARTIFACT_ANCHOR_RE.search(anchor)
                or CALCULATOR_HREF_RE.search(href)
            ):
                links.append(DownloadLink(line=index + line_offset, anchor=anchor, href=href))
    return links


def extract_bullet_block(content: str, heading_re: Pattern[str]) -> Optional[BulletBlock]:
    """Find a sidecar block: a heading matching heading_re followed by
    `- key: value` bullets. Returns normalized lower-case keys."""
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not heading_re.match(line.strip()):
            continue

        fields: Dict[str, str] = {}
        for block_line in lines[index + 1 :]:
            stripped = block_line.strip()
            if stripped.startswith("```"):
                break
            if stripped and not stripped.startswith(("-", "*", "+")):
                break
            if not stripped:
                continue
            field_match = BULLET_FIELD_RE.match(block_line)
            if not field_match:
                continue
            fields[field_match.group("key").strip().lower()] = field_match.group("value").strip()

        return BulletBlock(line=index + 1, fields=fields)

    return None
