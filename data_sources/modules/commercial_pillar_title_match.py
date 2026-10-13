"""Title evidence and title-keyword matching for commercial pillar records."""

from __future__ import annotations

import re


def line_binds_title(line: str, page_title: str) -> bool:
    evidence_text = re.sub(r"^\s*#{1,6}\s+", "", line)
    evidence_text = re.sub(r"[*_`]", "", evidence_text)
    normalize = lambda value: re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    return normalize(evidence_text) == normalize(page_title)


def title_keyword_fit(page_title: str, keyword: str) -> bool:
    title_tokens = {fold_plural(token) for token in re.findall(r"[a-z0-9]+", page_title.casefold())}
    keyword_tokens = {fold_plural(token) for token in re.findall(r"[a-z0-9]+", keyword.casefold())}
    generic = {
        "bigchange",
        "simpro",
        "software",
        "solution",
        "industry",
        "feature",
        "for",
        "management",
    }
    significant_title_tokens = title_tokens - generic
    significant_keyword_tokens = keyword_tokens - generic
    return bool(significant_title_tokens) and (
        significant_title_tokens.issubset(keyword_tokens)
        or bool(significant_keyword_tokens)
        and significant_keyword_tokens.issubset(title_tokens)
    )


def fold_plural(token: str) -> str:
    """Normalize only regular English singular/plural variants for title matching."""
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 3 and token.endswith("s") and not token.endswith(("is", "ss", "us")):
        return token[:-1]
    return token


_normalize_keyword_token = fold_plural
