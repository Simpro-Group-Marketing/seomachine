"""Quoted-passage check: quotes and blockquotes must appear verbatim in the production BOM."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence

from data_sources.modules.production.truth_text import Finding

_QUOTED = re.compile('"([^"]+)"|“([^”]+)”')
_QUOTE_STYLES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})
_EDGE_PUNCTUATION = " \t.,;:!?…-()[]'\""
MIN_QUOTE_WORDS = 4


def normalize_passage(text: str) -> str:
    """Casefold, unify quote style, collapse whitespace, and trim edge punctuation."""
    return " ".join(text.translate(_QUOTE_STYLES).casefold().split()).strip(_EDGE_PUNCTUATION)


def _word_count(passage: str) -> int:
    return sum(1 for word in passage.split() if any(char.isalnum() for char in word))


def _groups(lines: Sequence[str]) -> Iterator[tuple[int, bool, list[str]]]:
    """Yield (first line number, is_blockquote, lines) for each run of non-blank lines."""
    run: list[str] = []
    start, kind = 0, False
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            if run:
                yield start, kind, run
            run = []
            continue
        quoted = line.startswith(">")
        if run and quoted != kind:
            yield start, kind, run
            run = []
        if not run:
            start, kind = number, quoted
        run.append(line)
    if run:
        yield start, kind, run


def _found(passage: str, corpus: Sequence[str]) -> bool:
    needle = normalize_passage(passage)
    return bool(needle) and any(needle in source for source in corpus)


def _blockquote_findings(start: int, run: list[str], corpus: Sequence[str]) -> list[Finding]:
    texts = [line.lstrip(">").strip() for line in run]
    if _found(" ".join(texts), corpus) or all(_found(text, corpus) for text in texts if text):
        return []
    missing = next(offset for offset, text in enumerate(texts) if text and not _found(text, corpus))
    return [Finding(
        "quoted_passage", "block",
        f"blockquote is not verbatim in any BOM proof, approved quote, or fact quote: {texts[missing]!r}",
        start + missing,
    )]


def _inline_findings(start: int, run: list[str], corpus: Sequence[str]) -> list[Finding]:
    text = "\n".join(run)
    findings = []
    for match in _QUOTED.finditer(text):
        passage = match.group(1) or match.group(2)
        if _word_count(passage) >= MIN_QUOTE_WORDS and not _found(passage, corpus):
            findings.append(Finding(
                "quoted_passage", "block",
                f"quoted passage is not verbatim in any BOM proof, approved quote, or fact quote: {passage.strip()!r}",
                start + text.count("\n", 0, match.start()),
            ))
    return findings


def quoted_passage_findings(lines: Sequence[str], sources: Iterable[str]) -> list[Finding]:
    """Block quoted runs of four or more words and blockquotes that no BOM source contains."""
    corpus = [normalize_passage(source) for source in sources]
    findings: list[Finding] = []
    for start, is_blockquote, run in _groups(lines):
        check = _blockquote_findings if is_blockquote else _inline_findings
        findings += check(start, run, corpus)
    return findings
