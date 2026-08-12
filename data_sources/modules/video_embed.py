"""Strict source-artifact validation for supported video embeds."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlparse


YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    }
)
VIMEO_HOSTS = frozenset({"player.vimeo.com"})
NATIVE_VIDEO_SUFFIXES = frozenset({".mp4", ".ogg", ".webm"})
YOUTUBE_PATH_RE = re.compile(r"^/embed/([A-Za-z0-9_-]{11})/?$")
VIMEO_PATH_RE = re.compile(r"^/video/([0-9]+)/?$")
INLINE_CODE_RE = re.compile(r"`+[^`\n]*`+")


@dataclass(frozen=True)
class VideoEmbedInspection:
    """Validated video sources plus any attempted-embed errors."""

    sources: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def has_supported_embed(self) -> bool:
        return bool(self.sources) and not self.errors


@dataclass
class _OpenVideo:
    sources_seen: int = 0
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class _VideoEmbedParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[str] = []
        self.errors: list[str] = []
        self._videos: list[_OpenVideo] = []
        self._video_iframes: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        attributes = {key.casefold(): value for key, value in attrs}
        source_values = [value for key, value in attrs if key.casefold() == "src"]
        if normalized_tag == "iframe":
            self._handle_iframe(attributes, source_values)
            return
        if normalized_tag == "video":
            video = _OpenVideo()
            if len(source_values) > 1:
                video.sources_seen = len(source_values)
                video.errors.append("native video element cannot declare duplicate src attributes")
            elif "src" in attributes:
                self._record_native_source(video, attributes.get("src"))
            self._videos.append(video)
            return
        if normalized_tag == "source" and self._videos:
            if len(source_values) > 1:
                video = self._videos[-1]
                video.sources_seen += len(source_values)
                video.errors.append("native source element cannot declare duplicate src attributes")
            else:
                self._record_native_source(self._videos[-1], attributes.get("src"))

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag == "iframe" and self._video_iframes:
            self.sources.append(self._video_iframes.pop())
        elif normalized_tag == "video" and self._videos:
            self._finish_video(self._videos.pop())

    def finish(self) -> None:
        while self._video_iframes:
            self._video_iframes.pop()
            self.errors.append("video iframe element is not closed")
        while self._videos:
            video = self._videos.pop()
            video.errors.append("native video element is not closed")
            self._finish_video(video)

    def _handle_iframe(
        self,
        attributes: dict[str, str | None],
        source_values: list[str | None],
    ) -> None:
        if len(source_values) > 1:
            if any(self._is_video_iframe_source(value) for value in source_values):
                self.errors.append("video iframe cannot declare duplicate src attributes")
            return
        raw_source = attributes.get("src")
        if not isinstance(raw_source, str) or not raw_source.strip():
            return
        source = raw_source.strip()
        parsed = urlparse(source)
        host = (parsed.hostname or "").casefold()
        if not self._is_video_host(host):
            return
        if host not in YOUTUBE_HOSTS | VIMEO_HOSTS:
            self.errors.append("video iframe provider host is unsupported")
            return
        if parsed.scheme.casefold() != "https":
            self.errors.append("video iframe source must use HTTPS")
            return
        if host in YOUTUBE_HOSTS:
            if not YOUTUBE_PATH_RE.fullmatch(parsed.path):
                self.errors.append("YouTube embed requires an exact 11-character video ID")
                return
        elif not VIMEO_PATH_RE.fullmatch(parsed.path):
            self.errors.append("Vimeo embed requires a numeric video ID")
            return
        self._video_iframes.append(source)

    @staticmethod
    def _is_video_iframe_source(value: str | None) -> bool:
        if not isinstance(value, str) or not value.strip():
            return False
        host = (urlparse(value.strip()).hostname or "").casefold()
        return _VideoEmbedParser._is_video_host(host)

    @staticmethod
    def _is_video_host(host: str) -> bool:
        return (
            host in YOUTUBE_HOSTS | VIMEO_HOSTS
            or host.endswith(".youtube.com")
            or host.endswith(".youtube-nocookie.com")
            or host.endswith(".vimeo.com")
        )

    @staticmethod
    def _record_native_source(video: _OpenVideo, raw_source: str | None) -> None:
        video.sources_seen += 1
        if not isinstance(raw_source, str) or not raw_source.strip():
            video.errors.append("native video source must be non-empty")
            return
        source = raw_source.strip()
        parsed = urlparse(source)
        suffix = next(
            (candidate for candidate in NATIVE_VIDEO_SUFFIXES if parsed.path.casefold().endswith(candidate)),
            "",
        )
        if parsed.scheme.casefold() != "https" or not parsed.hostname or not suffix:
            video.errors.append(
                "native video source must be an HTTPS MP4, WebM, or Ogg URL"
            )
            return
        video.sources.append(source)

    def _finish_video(self, video: _OpenVideo) -> None:
        if video.sources_seen == 0:
            video.errors.append("native video element requires an HTTPS src or source")
        self.sources.extend(video.sources)
        self.errors.extend(video.errors)


def inspect_video_embeds(content: str) -> VideoEmbedInspection:
    """Inspect visible raw HTML and reject malformed attempted video embeds."""
    parser = _VideoEmbedParser()
    parser.feed(_strip_code_examples(content))
    parser.close()
    parser.finish()
    return VideoEmbedInspection(
        sources=tuple(parser.sources),
        errors=tuple(parser.errors),
    )


def _strip_code_examples(content: str) -> str:
    """Remove fenced and inline code before interpreting raw HTML as public copy."""
    visible_lines: list[str] = []
    fence_marker = ""
    for line in content.splitlines():
        stripped = line.lstrip()
        if fence_marker:
            if stripped.startswith(fence_marker):
                fence_marker = ""
            continue
        if stripped.startswith("```"):
            fence_marker = "```"
            continue
        if stripped.startswith("~~~"):
            fence_marker = "~~~"
            continue
        visible_lines.append(INLINE_CODE_RE.sub("", line))
    return "\n".join(visible_lines)
