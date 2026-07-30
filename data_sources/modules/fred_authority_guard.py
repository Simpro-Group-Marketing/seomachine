"""Publish-readiness guard for Fred Voccola authority evidence and embeds."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence
from urllib.parse import parse_qs, urlparse

try:
    from .fred_authority_selector import (
        PUBLIC_PLAYLIST_STATUS,
        USABLE_AUTHORITY_STATUS,
        FredAuthorityDataError,
        _authority_matches_inventory,
        _is_included_in_hub,
        _is_public_youtube_asset_url,
        _media_family,
        _is_public_youtube_url,
        _is_simpro_row,
        _is_usable_authority_row,
        _load_verified_rows,
        _resolve_vault_root,
    )
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from fred_authority_selector import (
        PUBLIC_PLAYLIST_STATUS,
        USABLE_AUTHORITY_STATUS,
        FredAuthorityDataError,
        _authority_matches_inventory,
        _is_included_in_hub,
        _is_public_youtube_asset_url,
        _media_family,
        _is_public_youtube_url,
        _is_simpro_row,
        _is_usable_authority_row,
        _load_verified_rows,
        _resolve_vault_root,
    )
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content


HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Fred Voccola Authority Selection:?\s*$",
    re.IGNORECASE,
)
BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")
MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S")
IFRAME_RE = re.compile(r"<iframe\b(?P<attrs>[^>]*)>", re.IGNORECASE | re.DOTALL)
ATTR_RE = re.compile(
    r"(?P<name>[A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    re.DOTALL,
)

REQUIRED_FIELDS = (
    "selector command",
    "evaluation status",
    "top candidates",
    "selected",
    "fit decision",
    "intended use",
    "target section",
    "authority row",
    "public url",
    "evidence status",
    "verification method",
    "evidence excerpt",
    "timestamp or locator",
    "playback verified",
    "exact quote",
    "embed decision",
    "videoobject",
)
INTENDED_USES = {
    "none",
    "embed",
    "inline_citation",
    "paraphrased_industry_observation",
    "exact_quote",
    "embed_and_paraphrase",
    "embed_and_quote",
}
VERIFICATION_METHODS = {
    "not_applicable",
    "source_visible_article_text",
    "transcript_and_playback",
    "paraphrase_evidence",
}
NONE_REASONS = (
    "no candidate",
    "no direct",
    "not relevant",
    "does not support",
    "outside",
    "mismatch",
    "rejected",
    "not directly",
)
NA_VALUES = {"", "none", "not applicable", "not_applicable", "n/a", "na"}


def check_content(
    content: str,
    *,
    proof_content: Optional[str] = None,
    vault_root: str | Path | None = None,
) -> List[Finding]:
    """Return findings for the mandatory Fred authority evaluation contract."""
    block = _extract_selection_block(proof_content or "")
    if block is None:
        return [
            _finding(
                "fred_authority_selection_missing",
                1,
                "The validation sidecar is missing Fred Voccola Authority Selection.",
                "Run the Fred authority selector and add the complete evaluation block.",
            )
        ]

    findings: List[Finding] = []
    fields = block["fields"]
    line = int(block["line"])
    for field in REQUIRED_FIELDS:
        if not fields.get(field, "").strip():
            findings.append(
                _finding(
                    "fred_authority_required_field_missing",
                    line,
                    f"Fred Voccola Authority Selection is missing required field: {field}.",
                    "Regenerate the complete selector block and finish the editorial decision.",
                    match=field,
                )
            )
    if findings:
        return _sorted(findings)

    evaluation = fields["evaluation status"].strip().lower()
    if evaluation != "completed":
        findings.append(
            _finding(
                "fred_authority_evaluation_blocked",
                line,
                "Fred authority evaluation is not completed.",
                "Resolve the vault or evidence blocker before publish readiness.",
                match=evaluation,
            )
        )

    intended = fields["intended use"].strip().lower()
    if intended not in INTENDED_USES:
        findings.append(
            _finding(
                "fred_authority_intended_use_invalid",
                line,
                "Fred authority intended use is invalid.",
                f"Use one of: {', '.join(sorted(INTENDED_USES))}.",
                match=intended,
            )
        )
    method = fields["verification method"].strip().lower()
    if method not in VERIFICATION_METHODS:
        findings.append(
            _finding(
                "fred_authority_verification_method_invalid",
                line,
                "Fred authority verification method is invalid.",
                f"Use one of: {', '.join(sorted(VERIFICATION_METHODS))}.",
                match=method,
            )
        )

    selected_id = _unwrap(fields["selected"])
    has_video_object = _frontmatter_has_video_object(content)
    has_video_embed = _has_video_embed(content)
    if has_video_object and not has_video_embed:
        findings.append(
            _finding(
                "fred_authority_video_object_without_embed",
                1,
                "VideoObject is present but no Fred YouTube video is embedded.",
                "Remove VideoObject when no video is embedded.",
            )
        )

    try:
        root = _resolve_vault_root(vault_root)
        inventory_rows, authority_rows = _load_verified_rows(root)
    except FredAuthorityDataError as exc:
        findings.append(
            _finding(
                "fred_authority_vault_unavailable",
                line,
                f"Fred authority vault verification failed: {exc}",
                "Restore the vault and regenerate its retrieval manifest before publishing.",
            )
        )
        return _sorted(findings)

    if selected_id.lower() == "none":
        findings.extend(_none_selection_findings(content, fields, line))
        return _sorted(findings)

    inventory = next(
        (row for row in inventory_rows if row.get("inventory_id", "").strip() == selected_id),
        None,
    )
    if inventory is None:
        findings.append(
            _finding(
                "fred_authority_id_unknown",
                line,
                f"Selected Fred authority ID is not present in the current vault: {selected_id}",
                "Choose an FVMI ID from the current selector output.",
                match=selected_id,
            )
        )
        return _sorted(findings)

    authority_by_id = {
        row.get("authority_id", "").strip(): row
        for row in authority_rows
        if row.get("authority_id", "").strip()
    }
    authority = authority_by_id.get(inventory.get("authority_id", "").strip())
    playlist_only = inventory.get("public_use_status", "").strip() == PUBLIC_PLAYLIST_STATUS
    usable = _inventory_is_usable(inventory, authority, playlist_only)
    if not usable:
        findings.append(
            _finding(
                "fred_authority_not_usable",
                line,
                "Selected Fred authority evidence is blocked, internal, placement-only, non-Simpro, or otherwise unusable.",
                "Select a usable authority row or verified public playlist asset from the current slate.",
                match=selected_id,
            )
        )

    findings.extend(_vault_match_findings(fields, inventory, authority, playlist_only, line))

    if intended == "none":
        findings.append(
            _finding(
                "fred_authority_selected_without_use",
                line,
                "A Fred authority row is selected but Intended use is none.",
                "Use Selected: [none] when no public evidence will be used.",
            )
        )
    if _is_na(fields["target section"]):
        findings.append(
            _finding(
                "fred_authority_target_section_missing",
                line,
                "Selected Fred evidence does not name its target article section.",
                "Name the heading where the source materially supports the content.",
            )
        )

    if playlist_only and intended not in {"embed", "none"}:
        findings.append(
            _finding(
                "fred_authority_playlist_authority_invalid",
                line,
                "A playlist-only asset may be used for discovery or embedding, not as independent earned-media authority.",
                "Use a usable authority row for quotations, observations, or inline authority citations.",
            )
        )

    if _uses_quote(intended):
        findings.extend(_quote_findings(content, fields, inventory, line))
    if _uses_paraphrase(intended):
        findings.extend(_paraphrase_findings(content, fields, line))
    if intended == "inline_citation":
        findings.extend(_public_link_findings(content, fields["public url"], line))

    embed_requested = _uses_embed(intended) or fields["embed decision"].strip().lower() == "yes"
    if embed_requested:
        findings.extend(_embed_findings(content, fields, inventory, line))
    else:
        if fields["embed decision"].strip().lower() != "no":
            findings.append(
                _finding(
                    "fred_authority_embed_decision_mismatch",
                    line,
                    "Embed decision must be no when Intended use does not include an embed.",
                    "Align Intended use and Embed decision.",
                )
            )
        if fields["videoobject"].strip().lower() not in {"not applicable", "not_applicable"}:
            findings.append(
                _finding(
                    "fred_authority_video_object_decision_mismatch",
                    line,
                    "VideoObject must be not applicable when no Fred video is embedded.",
                    "Remove the VideoObject handoff unless a verified video is embedded.",
                )
            )

    return _sorted(findings)


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    vault_root: str | Path | None = None,
) -> List[Finding]:
    """Check a public article file plus its validation sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    file_path = Path(path)
    return check_content(
        file_path.read_text(encoding="utf-8"),
        proof_content=load_sidecar_content(file_path, proof_sidecar),
        vault_root=vault_root,
    )


def _none_selection_findings(content: str, fields: Dict[str, str], line: int) -> List[Finding]:
    findings: List[Finding] = []
    reason = fields["fit decision"].strip().lower()
    if len(reason.split()) < 8 or not any(term in reason for term in NONE_REASONS):
        findings.append(
            _finding(
                "fred_authority_none_reason_weak",
                line,
                "Selected: none does not include a substantive topical-fit rejection reason.",
                "State why the evaluated candidates do not directly support this article's subject.",
                match=fields["fit decision"],
            )
        )
    expected = {
        "intended use": {"none"},
        "authority row": {"none", "[none]"},
        "public url": {"not applicable", "not_applicable"},
        "evidence status": {"not applicable", "not_applicable"},
        "verification method": {"not_applicable"},
        "embed decision": {"no"},
        "videoobject": {"not applicable", "not_applicable"},
    }
    for field, allowed in expected.items():
        if fields[field].strip().lower() not in allowed:
            findings.append(
                _finding(
                    "fred_authority_none_field_mismatch",
                    line,
                    f"Selected: none conflicts with field {field}.",
                    "Keep all public-use fields inactive when no source is selected.",
                    match=f"{field}: {fields[field]}",
                )
            )
    if _public_fred_signal(content):
        findings.append(
            _finding(
                "fred_authority_public_use_without_selection",
                1,
                "Public Fred Voccola evidence appears while the sidecar records Selected: none.",
                "Select and verify the current FVMI row or remove the public use.",
            )
        )
    return findings


def _inventory_is_usable(inventory: dict, authority: Optional[dict], playlist_only: bool) -> bool:
    if not _is_simpro_row(inventory):
        return False
    if not _is_included_in_hub(inventory):
        return False
    if playlist_only:
        return _is_public_youtube_asset_url(inventory.get("url_or_locator", ""))
    return bool(
        inventory.get("public_use_status", "").strip() == USABLE_AUTHORITY_STATUS
        and authority
        and _is_usable_authority_row(authority)
        and _authority_matches_inventory(inventory, authority)
    )


def _vault_match_findings(
    fields: Dict[str, str],
    inventory: dict,
    authority: Optional[dict],
    playlist_only: bool,
    line: int,
) -> List[Finding]:
    findings: List[Finding] = []
    expected_authority = inventory.get("authority_id", "").strip() or "none"
    if _unwrap(fields["authority row"]) != expected_authority:
        findings.append(
            _finding(
                "fred_authority_row_mismatch",
                line,
                "Sidecar Authority row does not match the current Fred inventory.",
                "Regenerate the slate from the current vault.",
                match=fields["authority row"],
            )
        )
    if _normalize_url(fields["public url"]) != _normalize_url(inventory.get("url_or_locator", "")):
        findings.append(
            _finding(
                "fred_authority_url_mismatch",
                line,
                "Sidecar Public URL does not match the current Fred inventory.",
                "Use the current vault URL exactly.",
                match=fields["public url"],
            )
        )
    if fields["evidence status"].strip() != inventory.get("evidence_status", "").strip():
        findings.append(
            _finding(
                "fred_authority_status_mismatch",
                line,
                "Sidecar Evidence status does not match the current Fred inventory.",
                "Regenerate the slate and reverify the source.",
                match=fields["evidence status"],
            )
        )
    if not inventory.get("title", "").strip() or not inventory.get("outlet", "").strip():
        findings.append(
            _finding(
                "fred_authority_metadata_incomplete",
                line,
                "The current vault row lacks a source title or outlet.",
                "Repair the vault inventory before using this source.",
            )
        )
    if not playlist_only and authority:
        if authority.get("public_use_status", "").strip() != USABLE_AUTHORITY_STATUS:
            findings.append(
                _finding(
                    "fred_authority_allowed_status_invalid",
                    line,
                    "The linked authority row is not approved for E-E-A-T authority support.",
                    "Choose a currently usable authority row.",
                )
            )
        if not authority.get("allowed_use", "").strip():
            findings.append(
                _finding(
                    "fred_authority_allowed_use_missing",
                    line,
                    "The linked authority row has no allowed-use context.",
                    "Repair the authority matrix before public use.",
                )
            )
    return findings


def _quote_findings(content: str, fields: Dict[str, str], inventory: dict, line: int) -> List[Finding]:
    quote = fields["exact quote"].strip()
    findings = _public_link_findings(content, fields["public url"], line, required_text=quote)
    excerpt = fields["evidence excerpt"].strip()
    locator = fields["timestamp or locator"].strip()
    method = fields["verification method"].strip().lower()
    media_type = _media_family(inventory.get("media_type", ""))
    if _is_na(quote) or quote not in content:
        findings.append(
            _finding(
                "fred_authority_exact_quote_missing",
                line,
                "The selected exact quote is missing from the public article or sidecar.",
                "Record and use the exact source-visible wording, or paraphrase.",
            )
        )
    if _is_na(excerpt) or (_is_na(quote) or quote not in excerpt):
        findings.append(
            _finding(
                "fred_authority_quote_evidence_missing",
                line,
                "Evidence excerpt does not contain the exact public quote.",
                "Capture the source-visible transcript or article text containing the quote.",
            )
        )
    if _is_na(locator):
        findings.append(
            _finding(
                "fred_authority_quote_locator_missing",
                line,
                "Exact quotation evidence lacks a timestamp or article locator.",
                "Add a timestamp for audio/video or a visible article locator.",
            )
        )
    if media_type in {"video", "audio", "podcast"}:
        if not _is_valid_av_timestamp(locator):
            findings.append(
                _finding(
                    "fred_authority_video_timestamp_invalid",
                    line,
                    "Exact audio/video evidence lacks a valid MM:SS or HH:MM:SS timestamp.",
                    "Record the verified playback timestamp as MM:SS or HH:MM:SS.",
                    match=locator,
                )
            )
        if method != "transcript_and_playback":
            findings.append(
                _finding(
                    "fred_authority_transcript_required",
                    line,
                    "Exact audio/video wording lacks transcript-and-playback verification.",
                    "Use transcript_and_playback with source-visible captions/transcript, or paraphrase.",
                )
            )
        if fields["playback verified"].strip().lower() != "yes":
            findings.append(
                _finding(
                    "fred_authority_playback_required",
                    line,
                    "Exact audio/video wording has not been playback verified.",
                    "Verify playback at the recorded timestamp and set Playback verified: yes.",
                )
            )
    elif method != "source_visible_article_text":
        findings.append(
            _finding(
                "fred_authority_article_text_required",
                line,
                "Exact article wording lacks source-visible article-text verification.",
                "Use source_visible_article_text with an evidence excerpt and locator, or paraphrase.",
            )
        )
    return findings


def _paraphrase_findings(content: str, fields: Dict[str, str], line: int) -> List[Finding]:
    findings = _public_link_findings(content, fields["public url"], line)
    if fields["verification method"].strip().lower() != "paraphrase_evidence" or _is_na(
        fields["evidence excerpt"]
    ):
        findings.append(
            _finding(
                "fred_authority_paraphrase_evidence_missing",
                line,
                "Paraphrased Fred industry observation lacks supporting evidence text.",
                "Record the source passage as paraphrase_evidence or remove the observation.",
            )
        )
    paragraph = _paragraph_with_url(content, fields["public url"])
    if paragraph is not None and not re.search(r"\bFred\s+Voccola\b", paragraph, re.IGNORECASE):
        findings.append(
            _finding(
                "fred_authority_paraphrase_attribution_missing",
                line,
                "The linked paraphrase paragraph does not attribute the observation to Fred Voccola.",
                "Name Fred Voccola in the same paragraph as the source link and observation.",
            )
        )
    return findings


def _public_link_findings(content: str, url: str, line: int, *, required_text: str = "") -> List[Finding]:
    paragraph = _paragraph_with_url(content, url)
    if paragraph is not None and (not required_text or required_text in paragraph):
        return []
    return [
        _finding(
            "fred_authority_public_link_missing",
            line,
            "Fred quotation or industry observation lacks its public source link in the same paragraph.",
            "Link the selected public URL in the same paragraph as the quotation or paraphrase.",
            match=url,
        )
    ]


def _embed_findings(content: str, fields: Dict[str, str], inventory: dict, line: int) -> List[Finding]:
    findings: List[Finding] = []
    if fields["embed decision"].strip().lower() != "yes":
        findings.append(
            _finding(
                "fred_authority_embed_decision_mismatch",
                line,
                "Intended use includes an embed but Embed decision is not yes.",
                "Set Embed decision: yes after validating the handoff.",
            )
        )
    if fields["videoobject"].strip().lower() != "required":
        findings.append(
            _finding(
                "fred_authority_video_object_decision_mismatch",
                line,
                "Embedded Fred video does not mark VideoObject: required.",
                "Set VideoObject: required and add it to frontmatter schema notes.",
            )
        )
    public_url = inventory.get("url_or_locator", "").strip()
    if _media_family(inventory.get("media_type", "")) != "video" or not _is_public_youtube_url(public_url):
        findings.append(
            _finding(
                "fred_authority_embed_source_invalid",
                line,
                "Only a selected public YouTube video may be embedded.",
                "Choose a public, embeddable YouTube FVMI row that supports the target section.",
            )
        )
        return findings

    video_id = _youtube_video_id(public_url)
    iframe_matches = list(IFRAME_RE.finditer(content))
    if not iframe_matches:
        findings.append(_finding("fred_authority_embed_missing", line, "Embed decision is yes but no iframe is present.", "Add the responsive privacy-enhanced YouTube handoff."))
        return findings

    matching = None
    for match in iframe_matches:
        attrs = _iframe_attributes(match.group("attrs"))
        if video_id and _embed_video_id(attrs.get("src", "")) == video_id:
            matching = (match, attrs)
            break
    if matching is None:
        findings.append(_finding("fred_authority_embed_video_mismatch", line, "Embedded video ID does not match the selected Fred inventory URL.", "Embed the exact selected YouTube video."))
        return findings

    match, attrs = matching
    src = attrs.get("src", "")
    if not re.match(r"^https://www\.youtube-nocookie\.com/embed/", src, re.IGNORECASE):
        findings.append(_finding("fred_authority_embed_provider_invalid", line, "Fred video embed is not using the privacy-enhanced YouTube provider.", "Use https://www.youtube-nocookie.com/embed/VIDEO_ID.", match=src))
    if "autoplay" in src.lower() or "autoplay" in match.group("attrs").lower():
        findings.append(_finding("fred_authority_embed_autoplay", line, "Fred video embed enables autoplay.", "Remove autoplay from the iframe URL and attributes."))
    if attrs.get("loading", "").lower() != "lazy":
        findings.append(_finding("fred_authority_embed_lazy_missing", line, "Fred video iframe is not lazy loaded.", "Add loading=\"lazy\"."))
    title = attrs.get("title", "").strip()
    if len(title.split()) < 4 or "fred" not in title.lower():
        findings.append(_finding("fred_authority_embed_title_invalid", line, "Fred video iframe lacks a descriptive title.", "Add a descriptive iframe title naming Fred and the video subject."))
    if "allowfullscreen" not in match.group("attrs").lower():
        findings.append(_finding("fred_authority_embed_fullscreen_missing", line, "Fred video iframe does not allow fullscreen.", "Add allowfullscreen to the iframe."))
    if not _has_responsive_wrapper(content, match):
        findings.append(_finding("fred_authority_embed_responsive_missing", line, "Fred video handoff does not declare responsive 16:9 dimensions.", "Wrap the iframe in a responsive 16:9 container."))
    if not _visible_fallback_link(content, public_url):
        findings.append(_finding("fred_authority_embed_fallback_missing", line, "Fred video embed lacks a visible fallback link.", "Add a visible link to the selected public YouTube URL."))
    if not _frontmatter_has_video_object(content):
        findings.append(_finding("fred_authority_video_object_missing", 1, "Embedded Fred video lacks VideoObject in frontmatter schema notes.", "Add VideoObject to schema_notes."))
    target = fields["target section"].strip()
    before_iframe = content[: match.start()]
    target_match = re.search(rf"^\s*#{{1,6}}\s+{re.escape(target)}\s*$", before_iframe, re.IGNORECASE | re.MULTILINE)
    target_body = before_iframe[target_match.end() :] if target_match else ""
    if target_match is None or len(re.sub(r"[#<>{}\[\]()*_]", " ", target_body).strip()) < 20:
        findings.append(_finding("fred_authority_embed_content_first_missing", line, "Fred embed is not preceded by material content in its target section.", "Introduce the source's topical relevance before the video embed."))
    return findings


def _extract_selection_block(content: str) -> Optional[Dict[str, object]]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not HEADING_RE.match(line.strip()):
            continue
        fields: Dict[str, str] = {}
        for block_line in lines[index + 1 :]:
            stripped = block_line.strip()
            if MARKDOWN_HEADING_RE.match(stripped):
                break
            match = BULLET_FIELD_RE.match(block_line)
            if match:
                fields[_normalize_key(match.group("key"))] = match.group("value").strip()
            elif stripped and fields:
                break
        return {"line": index + 1, "fields": fields}
    return None


def _frontmatter_has_video_object(content: str) -> bool:
    if not content.startswith("---"):
        return False
    end = content.find("\n---", 3)
    return end >= 0 and bool(re.search(r"\bVideoObject\b", content[3:end]))


def _has_video_embed(content: str) -> bool:
    if re.search(r"<video\b", content, re.IGNORECASE):
        return True
    providers = ("youtube", "youtu.be", "vimeo", "wistia", "vidyard")
    return any(
        any(provider in match.group("attrs").lower() for provider in providers)
        for match in IFRAME_RE.finditer(content)
    )


def _iframe_attributes(attrs: str) -> Dict[str, str]:
    return {match.group("name").lower(): match.group("value") for match in ATTR_RE.finditer(attrs)}


def _youtube_video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower().endswith("youtu.be"):
        return parsed.path.strip("/").split("/")[0]
    return parse_qs(parsed.query).get("v", [""])[0]


def _embed_video_id(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or parts[0].lower() != "embed":
        return ""
    return parts[1]


def _has_responsive_wrapper(content: str, iframe_match: re.Match[str]) -> bool:
    before = content[: iframe_match.start()]
    opening_start = before.rfind("<div")
    closing_start = before.rfind("</div>")
    if opening_start < 0 or opening_start < closing_start:
        return False
    opening_end = before.find(">", opening_start)
    if opening_end < 0:
        return False
    opening_tag = before[opening_start : opening_end + 1]
    return bool(
        re.search(
            r"aspect-ratio\s*:\s*16\s*/\s*9|padding-bottom\s*:\s*56\.25%",
            opening_tag,
            re.IGNORECASE,
        )
    )


def _is_valid_av_timestamp(value: str) -> bool:
    parts = value.strip().split(":")
    if len(parts) not in {2, 3} or not all(part.isdigit() for part in parts):
        return False
    if len(parts) == 2:
        minutes, seconds = (int(part) for part in parts)
        return minutes <= 59 and seconds <= 59
    _, minutes, seconds = (int(part) for part in parts)
    return minutes <= 59 and seconds <= 59


def _visible_fallback_link(content: str, url: str) -> bool:
    return bool(
        re.search(rf"\[[^\]]+\]\({re.escape(url)}(?:\s+['\"][^'\"]+['\"])?\)", content, re.IGNORECASE)
        or re.search(rf"<a\b[^>]*href=['\"]{re.escape(url)}['\"][^>]*>[^<]+</a>", content, re.IGNORECASE)
    )


def _paragraph_with_url(content: str, url: str) -> Optional[str]:
    normalized = _normalize_url(url)
    for paragraph in re.split(r"\n\s*\n", content):
        if normalized and normalized in _normalize_url(paragraph):
            return paragraph
    return None


def _public_fred_signal(content: str) -> bool:
    return bool(re.search(r"\bFred\s+Voccola\b", content, re.IGNORECASE))


def _uses_quote(intended: str) -> bool:
    return intended in {"exact_quote", "embed_and_quote"}


def _uses_paraphrase(intended: str) -> bool:
    return intended in {"paraphrased_industry_observation", "embed_and_paraphrase"}


def _uses_embed(intended: str) -> bool:
    return intended in {"embed", "embed_and_paraphrase", "embed_and_quote"}


def _is_na(value: str) -> bool:
    return value.strip().lower() in NA_VALUES


def _unwrap(value: str) -> str:
    return value.strip().strip("[]").strip()


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/).,|").lower()


def _finding(rule_id: str, line: int, message: str, suggestion: str, *, match: str = "") -> Finding:
    return make_finding(rule_id, "error", line, message=message, suggestion=suggestion, match=match)


def _sorted(findings: List[Finding]) -> List[Finding]:
    return sorted(findings, key=lambda item: (int(item["line"]), str(item["rule_id"])))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Fred Voccola authority evidence.")
    parser.add_argument("file_path")
    parser.add_argument("--proof-sidecar")
    parser.add_argument("--vault-root")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    args = parser.parse_args(argv)
    findings = check_file(args.file_path, proof_sidecar=args.proof_sidecar, vault_root=args.vault_root)
    if args.json:
        print(json.dumps({"findings": findings, "summary": summarize_findings(findings)}, indent=2))
    else:
        for finding in findings:
            print(f"{finding['severity'].upper()} {finding['rule_id']}: {finding.get('message', '')}")
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(_main())
