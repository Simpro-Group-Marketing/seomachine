"""Fail-closed validation for Markdown and rendered publishing content."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit


class PublishContentSafetyError(ValueError):
    """Content contains markup or a URL that is unsafe to publish."""


_ALLOWED_TAG_ATTRIBUTES = {
    "a": {"href", "target", "rel"},
    "blockquote": {"cite"},
    "br": set(),
    "code": set(),
    "details": {"open"},
    "div": set(),
    "em": set(),
    "figcaption": set(),
    "figure": set(),
    "h1": set(),
    "h2": set(),
    "h3": set(),
    "h4": set(),
    "h5": set(),
    "h6": set(),
    "hr": set(),
    "i": set(),
    "iframe": {
        "allow",
        "allowfullscreen",
        "frameborder",
        "height",
        "loading",
        "referrerpolicy",
        "src",
        "title",
        "width",
    },
    "img": {"alt", "decoding", "height", "loading", "src", "title", "width"},
    "li": {"value"},
    "ol": {"reversed", "start", "type"},
    "p": set(),
    "pre": set(),
    "span": set(),
    "strong": set(),
    "sub": set(),
    "summary": set(),
    "sup": set(),
    "table": set(),
    "tbody": set(),
    "td": {"colspan", "rowspan"},
    "tfoot": set(),
    "th": {"colspan", "rowspan", "scope"},
    "thead": set(),
    "tr": set(),
    "ul": set(),
}
_GLOBAL_ATTRIBUTES = {
    "aria-describedby",
    "aria-label",
    "aria-labelledby",
    "class",
    "dir",
    "id",
    "lang",
    "role",
    "style",
    "title",
}
_BOOLEAN_ATTRIBUTES = {"allowfullscreen", "open", "reversed"}
_URL_ATTRIBUTES = {"cite", "href", "src"}
_ALLOWED_STYLE_PROPERTIES = {
    "aspect-ratio",
    "border",
    "display",
    "height",
    "margin",
    "max-width",
    "overflow",
    "padding-top",
    "position",
    "width",
}
_ALLOWED_IFRAME_HOSTS = {
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_MARKDOWN_REFERENCE_URL_RE = re.compile(
    r"(?m)^\s*\[[^\]\r\n]+\]:\s*(?:<(?P<angle>[^>\r\n]+)>|(?P<plain>\S+))"
)
_AUTOLINK_RE = re.compile(
    r"<(?P<url>(?:[A-Za-z][A-Za-z0-9+.-]*:[^<>\s]+|[^<>\s@]+@[^<>\s@]+))>"
)
_INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1", re.DOTALL)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SAFE_STYLE_VALUE_RE = re.compile(r"^[A-Za-z0-9 .,%()/#_-]+$")


def validate_publish_content(markdown_text: str, *, rendered_html: str | None = None) -> None:
    """Reject unsafe HTML elements, attributes, and URL schemes.

    Markdown is always checked because Grav publishes it directly. WordPress callers also pass
    the rendered HTML so that extension-generated markup is checked before any remote write.
    """
    visible_markdown = _without_code(markdown_text)
    for destination in _iter_markdown_destinations(visible_markdown):
        _validate_url(destination, attribute="href")
    for match in _MARKDOWN_REFERENCE_URL_RE.finditer(visible_markdown):
        _validate_url(match.group("angle") or match.group("plain"), attribute="href")
    for match in _AUTOLINK_RE.finditer(visible_markdown):
        destination = match.group("url")
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", destination):
            _validate_url(destination, attribute="href")

    html_candidate = _AUTOLINK_RE.sub("", visible_markdown)
    _AllowlistHTMLParser().feed(html_candidate)
    if rendered_html is not None:
        _AllowlistHTMLParser().feed(rendered_html)


def validate_publish_plain_text(value: object, *, field: str) -> None:
    """Reject control characters and raw or encoded markup in public scalar values."""
    candidate = str(value or "")
    decoded = candidate
    for _ in range(4):
        next_value = html.unescape(unquote(decoded))
        if next_value == decoded:
            break
        decoded = next_value
    if _CONTROL_RE.search(decoded):
        raise PublishContentSafetyError(
            f"unsafe plain text for {field}: control characters are prohibited"
        )
    if re.search(
        r"<\s*(?:/?\s*[A-Za-z][A-Za-z0-9:-]*\b|!DOCTYPE\b|!--|\?)\s*[^>]*>",
        decoded,
        re.IGNORECASE,
    ):
        raise PublishContentSafetyError(
            f"unsafe plain text for {field}: markup is prohibited"
        )

def _iter_markdown_destinations(markdown_text: str):
    """Yield inline-link destinations while honoring nested labels and parentheses."""
    index = 0
    length = len(markdown_text)
    while index < length:
        label_start = index
        if markdown_text[index] == "!" and index + 1 < length:
            label_start = index + 1
        if markdown_text[label_start] != "[":
            index += 1
            continue

        cursor = label_start + 1
        label_depth = 1
        while cursor < length and label_depth:
            char = markdown_text[cursor]
            if char == "\\" and cursor + 1 < length:
                cursor += 2
                continue
            if char == "[":
                label_depth += 1
            elif char == "]":
                label_depth -= 1
            cursor += 1
        if label_depth or cursor >= length or markdown_text[cursor] != "(":
            index = max(cursor, index + 1)
            continue

        cursor += 1
        while cursor < length and markdown_text[cursor].isspace():
            cursor += 1
        if cursor >= length:
            return
        if markdown_text[cursor] == "<":
            destination_start = cursor + 1
            destination_end = destination_start
            while destination_end < length:
                if markdown_text[destination_end] == "\\" and destination_end + 1 < length:
                    destination_end += 2
                    continue
                if markdown_text[destination_end] == ">":
                    yield _markdown_unescape(
                        markdown_text[destination_start:destination_end]
                    )
                    break
                destination_end += 1
            index = max(destination_end + 1, index + 1)
            continue

        destination_start = cursor
        parenthesis_depth = 0
        while cursor < length:
            char = markdown_text[cursor]
            if char == "\\" and cursor + 1 < length:
                cursor += 2
                continue
            if char == "(":
                parenthesis_depth += 1
            elif char == ")":
                if parenthesis_depth == 0:
                    break
                parenthesis_depth -= 1
            elif char.isspace() and parenthesis_depth == 0:
                break
            cursor += 1
        destination = markdown_text[destination_start:cursor]
        if destination:
            yield _markdown_unescape(destination)
        index = max(cursor + 1, index + 1)


def _markdown_unescape(value: str) -> str:
    return re.sub(r"\\([!\"#$%&'()*+,./:;<=>?@\[\\\]^_`{|}~-])", r"\1", value)

def _without_code(markdown_text: str) -> str:
    retained: list[str] = []
    fence: str | None = None
    for line in markdown_text.splitlines(keepends=True):
        stripped = line.lstrip()
        marker = stripped[:3]
        if fence is None and marker in {"```", "~~~"}:
            fence = marker
            retained.append("\n" if line.endswith("\n") else "")
            continue
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            retained.append("\n" if line.endswith("\n") else "")
            continue
        retained.append(line)
    return _INLINE_CODE_RE.sub("", "".join(retained))


def _validate_url(value: str, *, attribute: str) -> None:
    candidate = html.unescape(str(value)).strip()
    for _ in range(3):
        decoded = unquote(candidate)
        if decoded == candidate:
            break
        candidate = decoded
    if not candidate:
        raise PublishContentSafetyError(f"unsafe empty URL in {attribute}")
    if _CONTROL_RE.search(candidate) or any(char.isspace() for char in candidate):
        raise PublishContentSafetyError(f"unsafe whitespace or control character in {attribute} URL")
    if "\\" in candidate or candidate.startswith("//"):
        raise PublishContentSafetyError(f"unsafe URL form in {attribute}")

    parsed = urlsplit(candidate)
    scheme = parsed.scheme.lower()
    allowed = {"http", "https"}
    if attribute in {"href", "cite"}:
        allowed.update({"mailto", "tel"})
    if scheme and scheme not in allowed:
        raise PublishContentSafetyError(f"unsafe URL scheme {scheme!r} in {attribute}")
    if scheme in {"http", "https"} and not parsed.hostname:
        raise PublishContentSafetyError(f"unsafe absolute URL without a host in {attribute}")


def _validate_style(value: str) -> None:
    for declaration in value.split(";"):
        declaration = declaration.strip()
        if not declaration:
            continue
        name, separator, raw_value = declaration.partition(":")
        name = name.strip().lower()
        raw_value = raw_value.strip()
        if (
            not separator
            or name not in _ALLOWED_STYLE_PROPERTIES
            or not raw_value
            or not _SAFE_STYLE_VALUE_RE.fullmatch(raw_value)
            or any(token in raw_value.lower() for token in ("url(", "expression(", "@import", "javascript"))
        ):
            raise PublishContentSafetyError(f"unsafe inline style declaration {declaration!r}")


class _AllowlistHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._validate_tag(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._validate_tag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized not in _ALLOWED_TAG_ATTRIBUTES:
            raise PublishContentSafetyError(f"unsafe HTML tag </{normalized}>")

    def handle_decl(self, decl: str) -> None:
        raise PublishContentSafetyError(f"unsafe HTML declaration <!{decl}>")

    def unknown_decl(self, data: str) -> None:
        raise PublishContentSafetyError(f"unsafe HTML declaration <![{data}]>")

    def _validate_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        allowed_attributes = _ALLOWED_TAG_ATTRIBUTES.get(normalized)
        if allowed_attributes is None:
            raise PublishContentSafetyError(f"unsafe HTML tag <{normalized}>")

        seen: set[str] = set()
        values: dict[str, str] = {}
        for raw_name, raw_value in attrs:
            name = raw_name.lower()
            if name in seen:
                raise PublishContentSafetyError(f"unsafe duplicate HTML attribute {name!r}")
            seen.add(name)
            if name.startswith("on") or (
                name not in allowed_attributes and name not in _GLOBAL_ATTRIBUTES
            ):
                raise PublishContentSafetyError(
                    f"unsafe HTML attribute {name!r} on <{normalized}>"
                )
            if raw_value is None:
                if name not in _BOOLEAN_ATTRIBUTES:
                    raise PublishContentSafetyError(
                        f"unsafe valueless HTML attribute {name!r} on <{normalized}>"
                    )
                values[name] = ""
                continue
            values[name] = raw_value
            if name in _URL_ATTRIBUTES:
                _validate_url(raw_value, attribute=name)
            elif name == "style":
                _validate_style(raw_value)

        if normalized == "iframe":
            source = values.get("src", "")
            parsed = urlsplit(source)
            if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() not in _ALLOWED_IFRAME_HOSTS:
                raise PublishContentSafetyError(
                    "unsafe iframe source; only HTTPS youtube-nocookie.com embeds are allowed"
                )
            if not values.get("title", "").strip():
                raise PublishContentSafetyError("unsafe iframe without a descriptive title")