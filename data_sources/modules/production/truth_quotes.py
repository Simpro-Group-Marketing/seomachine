"""Quoted-passage check: quotes and blockquotes must appear verbatim in one production BOM source."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence

from data_sources.modules.production.truth_text import Finding

_DOUBLE = re.compile(r'"([^"]+)"')
_SINGLE = re.compile(r"(?<!\w)[‘‚'](.+?)[’‘'](?!\w)")
_TO_DOUBLE = str.maketrans({"“": '"', "”": '"', "«": '"', "»": '"', "„": '"'})
_NORMAL_STYLES = str.maketrans({
    "“": '"', "”": '"', "«": '"', "»": '"', "„": '"',
    "‘": "'", "’": "'", "‚": "'",
})
_INTRA_WORD_APOSTROPHE = re.compile(r"(?<=\w)['‘’](?=\w)")
_PROTECTED = "\u0001"
_ATTRIBUTION = re.compile(r"\s*(?:[—–]|(?<=\s)-(?=\s)).*$", re.DOTALL)
_CALLOUT = re.compile('^\\*\\*[^*"“”]{1,60}\\*\\*')
_ELLIPSIS = re.compile(r"…|\.\.\.")
_CUE = re.compile(r"\b(?:said|says|told|according\s+to)\b|[—–]", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?](?:[\"'”’])?\s|\n")
_EDGE_PUNCTUATION = " \t.,;:!?…-()[]'\""
MIN_QUOTE_WORDS = 4
MIN_ATTRIBUTED_WORDS = 2


def normalize_passage(text: str) -> str:
    """Casefold, unify quote style, collapse whitespace, and trim edge punctuation."""
    return " ".join(text.translate(_NORMAL_STYLES).casefold().split()).strip(_EDGE_PUNCTUATION)


def strip_attribution(text: str) -> str:
    """Drop a trailing attribution that starts at a dash, such as an em dash and a name."""
    return _ATTRIBUTION.sub("", text)


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
    """True when every elided fragment of the passage sits in one and the same source."""
    fragments = [normalize_passage(part) for part in _ELLIPSIS.split(strip_attribution(passage))]
    fragments = [part for part in fragments if part]
    return not fragments or any(all(part in source for part in fragments) for source in corpus)


def _blockquote_findings(start: int, run: list[str], corpus: Sequence[str]) -> list[Finding]:
    texts = [strip_attribution(line.lstrip(">").strip()) for line in run]
    kept = [(offset, text) for offset, text in enumerate(texts) if text.strip()]
    if not kept or _found(" ".join(text for _, text in kept), corpus):
        return []
    return [Finding(
        "quoted_passage", "block",
        "blockquote is not verbatim in a single BOM proof text, approved quote, or fact quote: "
        f"{' '.join(text for _, text in kept)!r}",
        start + kept[0][0],
    )]


def _quoted_spans(text: str) -> list[tuple[int, str]]:
    """Return (offset, passage) for every double-, single-, or guillemet-quoted span."""
    protected = _INTRA_WORD_APOSTROPHE.sub(_PROTECTED, text).translate(_TO_DOUBLE)
    spans = [(match.start(), match.group(1)) for match in _DOUBLE.finditer(protected)]
    spans += [(match.start(), match.group(1)) for match in _SINGLE.finditer(protected)]
    return [(start, passage.replace(_PROTECTED, "'")) for start, passage in sorted(spans)]


def _has_cue(text: str, start: int, end: int, customers: Sequence[str]) -> bool:
    """True when the quote's own sentence carries an attribution cue or names a customer."""
    before = [match.end() for match in _SENTENCE_END.finditer(text, 0, start)]
    after = _SENTENCE_END.search(text, end)
    sentence = text[(before[-1] if before else 0) : (after.start() if after else len(text))]
    lowered = sentence.casefold()
    return _CUE.search(sentence) is not None or any(name.casefold() in lowered for name in customers)


def _inline_findings(
    start: int, run: list[str], corpus: Sequence[str], customers: Sequence[str]
) -> list[Finding]:
    """Block unverifiable quotes that carry an attribution cue; an unattributed phrase only warns."""
    text = "\n".join(run)
    findings = []
    for offset, passage in _quoted_spans(text):
        end = offset + len(passage) + 2
        cued = _has_cue(text, offset, end, customers)
        if _word_count(passage) >= (MIN_ATTRIBUTED_WORDS if cued else MIN_QUOTE_WORDS) and not _found(passage, corpus):
            findings.append(Finding(
                "quoted_passage", "block" if cued else "warn",
                "quoted passage is not verbatim in a single BOM proof text, approved quote, or fact quote: "
                f"{passage.strip()!r}",
                start + text.count("\n", 0, offset),
            ))
    return findings


def _is_callout(run: Sequence[str]) -> bool:
    """A blockquote opened by a bold label such as "**Key takeaways**" is a callout, not a quotation."""
    return _CALLOUT.match(run[0].lstrip(">").strip()) is not None


def quoted_passage_findings(
    lines: Sequence[str], sources: Iterable[str], customers: Sequence[str] = ()
) -> list[Finding]:
    """Block unverifiable quotes and blockquotes; each must sit whole in one BOM source."""
    corpus = [normalize_passage(source) for source in sources]
    findings: list[Finding] = []
    for start, is_blockquote, run in _groups(lines):
        if is_blockquote:
            findings += [] if _is_callout(run) else _blockquote_findings(start, run, corpus)
        else:
            findings += _inline_findings(start, run, corpus, customers)
    return findings
