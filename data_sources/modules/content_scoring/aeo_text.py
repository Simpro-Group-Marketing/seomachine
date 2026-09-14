"""Focused aeo text scoring."""

from __future__ import annotations

from data_sources.modules.image_placeholder import is_production_image_placeholder_line
from typing import Dict
from typing import List
from typing import Tuple
import re

def _extract_frontmatter(content: str) -> Dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*", content, re.DOTALL)
    if not match:
        return {}

    metadata = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[_normalize_key(key)] = value.strip().strip('"')
    return metadata

def _normalize_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_").replace("-", "_")

def _strip_frontmatter(content: str) -> str:
    return re.sub(r"\A---\s*\n.*?\n---\s*", "", content, flags=re.DOTALL).strip()

def _plain_text(markdown: str) -> str:
    text = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`>]", "", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    return text.strip()

def _extract_markdown_links(content: str) -> List[Tuple[str, str]]:
    return [
        (match.group(1).strip(), match.group(2).strip())
        for match in re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", content)
    ]

def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))

def _sentences(text: str) -> List[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]

def _first_body_paragraph(body: str) -> str:
    lines = body.splitlines()
    paragraphs = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if is_production_image_placeholder_line(stripped):
            continue
        if (
            stripped.startswith("#")
            or stripped.startswith(">")
            or stripped.startswith("- ")
        ):
            continue
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    return paragraphs[0] if paragraphs else ""

def _extract_h2_sections(body: str) -> List[Tuple[str, str]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, re.MULTILINE))
    sections = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append((match.group(1).strip(), body[start:end].strip()))

    return sections

def _first_paragraph(section_body: str) -> str:
    lines = section_body.splitlines()
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                break
            continue
        if (
            stripped.startswith("#")
            or stripped.startswith(">")
            or stripped.startswith("- ")
        ):
            continue
        current.append(stripped)

    return " ".join(current)

def _is_capsule(paragraph: str) -> bool:
    words = _word_count(_plain_text(paragraph))
    if words < 50 or words > 60:
        return False
    sentences = _sentences(_plain_text(paragraph))
    return 2 <= len(sentences) <= 4

def _contains_ordered_target(text: str, target: str, *, max_gap_words: int = 2) -> bool:
    text_tokens = re.findall(r"[a-z0-9]+", text.casefold())
    target_tokens = re.findall(r"[a-z0-9]+", target.casefold())
    if not target_tokens:
        return False

    for start, token in enumerate(text_tokens):
        if token != target_tokens[0]:
            continue
        position = start
        inserted = 0
        for expected in target_tokens[1:]:
            position += 1
            while position < len(text_tokens) and text_tokens[position] != expected:
                inserted += 1
                if inserted > max_gap_words:
                    break
                position += 1
            if inserted > max_gap_words or position >= len(text_tokens):
                break
        else:
            return True
    return False

def _normalize_url(value: str) -> str:
    url_match = re.search(r"https?://[^\s),]+", value, re.IGNORECASE)
    if url_match:
        value = url_match.group(0)
    return value.strip().rstrip(".,)").lower()

def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

def _story_tokens(value: str) -> set[str]:
    stopwords = {
        "and",
        "describes",
        "from",
        "into",
        "owner",
        "that",
        "the",
        "their",
        "using",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) >= 3 and token not in stopwords
    }

def _paragraph_has_url_and_identity(content: str, url: str, identity: str) -> bool:
    normalized_url = _normalize_url(url)
    normalized_identity = _normalize_text(identity)
    for paragraph in re.split(r"\n\s*\n", content):
        if normalized_url not in _normalize_url(paragraph):
            continue
        if normalized_identity and normalized_identity in _normalize_text(paragraph):
            return True
    return False

def _unwrap_bracketed_value(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return cleaned.strip()


__all__ = [
    "_extract_frontmatter",
    "_normalize_key",
    "_strip_frontmatter",
    "_plain_text",
    "_extract_markdown_links",
    "_word_count",
    "_sentences",
    "_first_body_paragraph",
    "_extract_h2_sections",
    "_first_paragraph",
    "_is_capsule",
    "_contains_ordered_target",
    "_normalize_url",
    "_normalize_text",
    "_story_tokens",
    "_paragraph_has_url_and_identity",
    "_unwrap_bracketed_value",
]
