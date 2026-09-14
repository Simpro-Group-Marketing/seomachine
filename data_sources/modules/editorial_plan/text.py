"""Visible-article normalization helpers for editorial-plan bindings."""

from __future__ import annotations

import re



def _visible_article_text(body: str) -> str:
    visible = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', body)
    visible = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', visible)
    visible = re.sub(r'^\s*\[[^\]]+\]:\s*\S+.*$', ' ', visible, flags=re.MULTILINE)
    visible = re.sub(r'<(?:https?://|mailto:)[^>]+>', ' ', visible, flags=re.IGNORECASE)
    visible = re.sub(r'https?://\S+', ' ', visible, flags=re.IGNORECASE)
    visible = re.sub(r'<[^>]+>', ' ', visible)
    return re.sub(r'\s+', ' ', visible).casefold()


def _visible_sections_by_heading(body: str) -> dict[str, str]:
    lines = body.splitlines()
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r'^(#{1,6})\s+(.+?)\s*$', line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).rstrip('#').strip()))
    sections: dict[str, str] = {}
    for heading_index, (line_index, level, heading) in enumerate(headings):
        end = len(lines)
        for next_line, next_level, _ in headings[heading_index + 1:]:
            if next_level <= level:
                end = next_line
                break
        key = heading.casefold()
        visible = _visible_article_text('\n'.join(lines[line_index + 1:end]))
        sections[key] = f"{sections.get(key, '')} {visible}".strip()
    return sections


def _normalize_visible_text(value: str) -> str:
    return _visible_article_text(value)


def _contains_entity(visible_body: str, entity: str) -> bool:
    normalized = re.sub(r'\s+', ' ', entity.strip()).casefold()
    if not normalized:
        return False
    pattern = re.escape(normalized).replace(r'\ ', r'\s+')
    return bool(re.search(rf'(?<!\w){pattern}(?!\w)', visible_body))
