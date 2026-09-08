"""Validation helpers for production-ready standalone image placeholders."""

import re


PRODUCTION_IMAGE_PLACEHOLDER_RE = re.compile(
    r"""
    \A
    \[IMAGE[ \t]+PLACEHOLDER\b
    (?=[^\]\r\n]*\|[ \t]*source:[ \t]*https://[^\s|\]]+)
    (?=[^\]\r\n]*\|[ \t]*alt:[ \t]*"[^"\r\n]+")
    (?=[^\]\r\n]*\|[ \t]*render[ \t]+target:[ \t]*\d+[ \t]*(?:×|x)[ \t]*\d+[ \t]*px\b)
    (?=[^\]\r\n]*\bresize[ \t]+and[ \t]+compress\b)
    [^\]\r\n]*
    \]
    \Z
    """,
    re.IGNORECASE | re.VERBOSE,
)


PRODUCTION_VIDEO_PLACEHOLDER_RE = re.compile(
    r"""
    \A
    \[VIDEO[ \t]+PLACEHOLDER\b
    (?=[^\]\r\n]*\|[ \t]*source:[ \t]*[^|\]\r\n]+)
    (?=[^\]\r\n]*\|[ \t]*title:[ \t]*"[^"\r\n]+")
    (?=[^\]\r\n]*\|[ \t]*placement:[ \t]*[^|\]\r\n]+)
    (?=[^\]\r\n]*\|[ \t]*embed[ \t]+target:[ \t]*[^|\]\r\n]+)
    (?=[^\]\r\n]*\|[ \t]*VideoObject:[ \t]*add[ \t]+only[ \t]+after[ \t]+embed\b)
    [^\]\r\n]*
    \]
    \Z
    """,
    re.IGNORECASE | re.VERBOSE,
)


def is_production_image_placeholder_line(line: str) -> bool:
    """Return True only for a complete, standalone production image marker."""
    return PRODUCTION_IMAGE_PLACEHOLDER_RE.fullmatch(line.strip()) is not None


def is_production_video_placeholder_line(line: str) -> bool:
    """Return True only for a complete, standalone production video marker."""
    return PRODUCTION_VIDEO_PLACEHOLDER_RE.fullmatch(line.strip()) is not None
