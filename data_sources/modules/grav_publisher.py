"""
Grav CMS Publisher Module

Publishes a finished draft/rewrite article to a Grav CMS GitHub repository.

Each Grav blog post lives in its own folder under the blog directory, containing an
``article.<lang>.md`` file (YAML frontmatter + Markdown body) plus its images. This module
takes a draft from ``drafts/`` or ``rewrites/``, converts it into a Grav ``article.en.md``,
and commits it directly to the ``dev`` branch via the GitHub Contents API (using the
already-authenticated ``gh`` CLI -- no local clone required).

Configuration (repo-root ``.env``):
    GRAV_REPO         owner/repo of the Grav GitHub repository (required for live publish)
    GRAV_BRANCH       branch to commit to (default: dev)
    GRAV_BLOG_PATH    blog folder path inside the repo (default: blogs)
    GRAV_DEFAULT_LANG language code for the article file (default: en)

Images are out of scope for this version (text only).
"""

import os
import re
import json
import base64
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .publishable_markdown import (
        PublishableMarkdown,
        capture_file_snapshots,
        ensure_same_file_snapshots,
        ensure_same_snapshot,
        metadata_path_tail,
        read_publishable_markdown,
    )
    from .publish_content_safety import (
        PublishContentSafetyError,
        validate_publish_content,
        validate_publish_plain_text,
    )
    from .publish_readiness import run_publish_readiness
except ImportError:
    from publishable_markdown import (
        PublishableMarkdown,
        capture_file_snapshots,
        ensure_same_file_snapshots,
        ensure_same_snapshot,
        metadata_path_tail,
        read_publishable_markdown,
    )
    from publish_content_safety import (
        PublishContentSafetyError,
        validate_publish_content,
        validate_publish_plain_text,
    )
    from publish_readiness import run_publish_readiness


GH_TIMEOUT_SECONDS = 30
MAX_GRAV_READBACK_BYTES = 5 * 1024 * 1024
GH_NOT_FOUND_RE = re.compile(r"\bHTTP\s+404\b", re.IGNORECASE)
GH_HTTP_STATUS_RE = re.compile(r"\bHTTP\s+(?P<status>\d{3})\b", re.IGNORECASE)
GH_DEFINITIVE_WRITE_STATUSES = frozenset({400, 401, 403, 404, 409, 422})
GRAV_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
GRAV_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class GravPublishError(RuntimeError):
    """Raised when a Grav publish operation fails."""


class GravRequestTimeout(GravPublishError):
    """A GitHub API request timed out with an unknown remote outcome."""


class GravPartialPublishError(GravPublishError):
    """A Grav write may exist, but exact remote state could not be confirmed."""

    def __init__(self, push: Dict, cause: Exception):
        self.push = dict(push)
        self.cause = cause
        self.repo = str(push.get("repo") or "")
        self.branch = str(push.get("branch") or "")
        self.repo_path = str(push.get("repo_path") or "")
        self.expected_content_sha256 = str(push.get("expected_content_sha256") or "")
        location = str(push.get("commit_url") or "")
        if not location:
            location = f"{self.repo}@{self.branch}:{self.repo_path}"
        expected = (
            f" Expected SHA-256: {self.expected_content_sha256}."
            if self.expected_content_sha256
            else ""
        )
        super().__init__(
            "Grav article write may have completed, but post-write verification failed: "
            f"{cause}. Review {location}; do not retry blindly.{expected}"
        )


class GravPublisher:
    """Builds Grav ``article.<lang>.md`` files and commits them via the GitHub Contents API."""

    def __init__(
        self,
        repo: Optional[str] = None,
        branch: Optional[str] = None,
        blog_path: Optional[str] = None,
        lang: Optional[str] = None,
    ):
        self.repo = repo or os.getenv("GRAV_REPO", "")
        self.branch = branch or os.getenv("GRAV_BRANCH", "dev")
        self.blog_path = _validate_blog_path(
            blog_path or os.getenv("GRAV_BLOG_PATH", "blogs")
        )
        self.lang = _validate_language_tag(lang or os.getenv("GRAV_DEFAULT_LANG", "en"))
        self.preview_root = Path(__file__).resolve().parents[2] / ".grav-preview"

    # ------------------------------------------------------------------ parsing

    def parse_draft_file(
        self,
        file_path: str,
        snapshot: Optional[PublishableMarkdown] = None,
    ) -> Dict:
        """
        Parse a draft/rewrite markdown file into its metadata and body.

        Real drafts use a YAML-style frontmatter block delimited by ``---`` with fields like
        ``Meta Title:``, ``Meta Description:``, ``Primary Keyword:``, ``Secondary Keywords:``,
        ``Author:``, ``Last Updated:``, and ``URL Slug:``, followed by an H1 and the body.

        Returns a dict with keys: title, meta_title, meta_description, primary_keyword,
        secondary_keywords, author, last_updated, slug, content.
        """
        artifact = snapshot or read_publishable_markdown(file_path)
        path = artifact.path
        meta_title = artifact.scalar("meta_title", "title")
        title = meta_title or artifact.h1

        slug = self._derive_slug(
            url_slug=metadata_path_tail(artifact.scalar("url_slug", "target_url")),
            file_stem=path.stem,
            title=artifact.h1 or meta_title,
        )

        return {
            "title": title,
            "display_title": artifact.h1,
            "meta_title": meta_title or title,
            "meta_description": artifact.scalar("meta_description"),
            "primary_keyword": artifact.scalar("primary_keyword", "target_keyword"),
            "secondary_keywords": ", ".join(artifact.values("secondary_keywords")),
            "author": artifact.scalar("author"),
            "last_updated": artifact.scalar("last_updated"),
            "slug": slug,
            "content": artifact.body,
        }

    @staticmethod
    def _split_frontmatter(raw: str) -> "tuple[Dict[str, str], str]":
        """Split a ``---``-delimited YAML-style frontmatter block from the body.

        Returns (frontmatter_dict_lowercased_keys, body). If no frontmatter block is present,
        returns ({}, raw).
        """
        fm: Dict[str, str] = {}
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.DOTALL)
        if not match:
            return fm, raw

        block, body = match.group(1), match.group(2)
        for line in block.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, sep, value = line.partition(":")
            if not sep:
                continue
            fm[key.strip().lower()] = value.strip()
        return fm, body

    @staticmethod
    def slugify(text: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s_]+", "-", slug)
        return slug.strip("-")

    def _derive_slug(self, url_slug: str, file_stem: str, title: str) -> str:
        """Slug precedence: URL Slug field -> filename (blog title) -> H1/meta title.

        Each candidate is slugified; an empty result falls through to the next source.
        """
        # e.g. "/blog/modern-customer-payments" -> "modern-customer-payments"
        url_tail = url_slug.rstrip("/").split("/")[-1] if url_slug else ""
        for candidate in (url_tail, file_stem, title):
            slug = self.slugify(candidate)
            if slug:
                return slug
        return ""

    # ------------------------------------------------------- frontmatter / build

    @staticmethod
    def _yaml_quote(value: str) -> str:
        """Single-quote a scalar for YAML, doubling any embedded single quotes."""
        return "'" + value.replace("'", "''") + "'"

    def _format_date(self, last_updated: str) -> str:
        """Return a Grav-style ``YYYY-MM-DD HH:MM`` date string."""
        candidate = last_updated.strip()
        if candidate:
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(candidate, fmt)
                    return dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    continue
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    def build_grav_frontmatter(self, draft: Dict) -> str:
        """
        Build standard Grav blog frontmatter from a parsed draft.

        NOTE: This is the single place that maps draft fields to the Grav schema. Adjust this
        method to match the real Grav theme once a sample ``article.en.md`` is available.
        """
        secondary = [
            t.strip()
            for t in draft.get("secondary_keywords", "").split(",")
            if t.strip()
        ]
        keywords = [
            k for k in [draft.get("primary_keyword", "").strip(), *secondary] if k
        ]

        lines: List[str] = ["---"]
        lines.append(f"title: {self._yaml_quote(draft['title'])}")
        lines.append(
            f"date: {self._yaml_quote(self._format_date(draft.get('last_updated', '')))}"
        )
        lines.append("taxonomy:")
        lines.append("    category:")
        lines.append("        - blog")
        if secondary:
            lines.append("    tag:")
            for tag in secondary:
                lines.append(f"        - {self._yaml_quote(tag)}")
        lines.append("metadata:")
        if draft.get("meta_description"):
            lines.append(
                f"    description: {self._yaml_quote(draft['meta_description'])}"
            )
        if keywords:
            lines.append(f"    keywords: {self._yaml_quote(', '.join(keywords))}")
        if draft.get("author"):
            lines.append(f"author: {self._yaml_quote(draft['author'])}")
        lines.append("published: true")
        lines.append("---")
        return "\n".join(lines)

    def build_article(self, draft: Dict) -> str:
        """Assemble the full ``article.<lang>.md`` content (frontmatter + body)."""
        return f"{self.build_grav_frontmatter(draft)}\n\n{draft['content']}\n"

    def article_repo_path(self, slug: str) -> str:
        """Return a contained, repository-relative article path."""
        if not GRAV_PATH_SEGMENT_RE.fullmatch(slug) or slug in {".", ".."}:
            raise GravPublishError("unsafe Grav article slug")
        lang = _validate_language_tag(self.lang)
        candidate = f"{self.blog_path}/{slug}/article.{lang}.md"
        if not candidate.startswith(f"{self.blog_path}/"):
            raise GravPublishError("Grav article path escaped the configured blog path")
        return candidate

    # --------------------------------------------------------------- gh api push

    def _gh_api(
        self, args: List[str], payload: Optional[Dict] = None
    ) -> "tuple[int, str]":
        """Invoke ``gh api`` with the given args. Returns (returncode, stdout/stderr)."""
        if shutil.which("gh") is None:
            raise GravPublishError("GitHub CLI ('gh') not found on PATH.")
        cmd = ["gh", "api", *args]
        try:
            result = subprocess.run(
                cmd,
                input=json.dumps(payload) if payload is not None else None,
                capture_output=True,
                text=True,
                timeout=GH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise GravRequestTimeout(
                f"GitHub CLI request timed out after {GH_TIMEOUT_SECONDS} seconds."
            ) from exc
        except OSError as exc:  # pragma: no cover - environment dependent
            raise GravPublishError(f"Failed to run gh: {exc}") from exc
        out = (
            result.stdout
            if result.returncode == 0
            else (result.stderr or result.stdout)
        )
        return result.returncode, out

    def _get_existing_sha(self, repo_path: str) -> Optional[str]:
        """Return the blob sha if the file already exists on the branch, else None."""
        code, out = self._gh_api(
            [
                "-X",
                "GET",
                f"repos/{self.repo}/contents/{repo_path}",
                "-f",
                f"ref={self.branch}",
            ]
        )
        if code != 0:
            if GH_NOT_FOUND_RE.search(out):
                return None
            raise GravPublishError(f"Could not inspect existing Grav article:\n{out}")
        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            raise GravPublishError(
                f"Unexpected existing-content response:\n{out}"
            ) from exc
        if not isinstance(data, dict):
            raise GravPublishError(f"Unexpected existing-content response:\n{out}")
        sha = data.get("sha")
        if not isinstance(sha, str) or not sha.strip():
            raise GravPublishError(
                "Existing Grav article response did not include a blob SHA."
            )
        return sha

    def _read_remote_article(self, repo_path: str) -> tuple[str, bytes]:
        """Read back one committed article from the configured branch."""
        code, out = self._gh_api(
            [
                "-X",
                "GET",
                f"repos/{self.repo}/contents/{repo_path}",
                "-f",
                f"ref={self.branch}",
            ]
        )
        if code != 0:
            raise GravPublishError(
                f"Could not read back committed Grav article:\n{out}"
            )
        try:
            payload = json.loads(out)
        except json.JSONDecodeError as exc:
            raise GravPublishError(
                f"Unexpected Grav readback response:\n{out}"
            ) from exc
        if not isinstance(payload, dict):
            raise GravPublishError("Grav remote readback is not an object")
        blob_sha = payload.get("sha")
        encoding = payload.get("encoding")
        encoded = payload.get("content")
        if (
            not isinstance(blob_sha, str)
            or not blob_sha
            or encoding != "base64"
            or not isinstance(encoded, str)
        ):
            raise GravPublishError(
                "Grav remote readback omitted content or blob metadata"
            )
        compact = "".join(encoded.split())
        if len(compact) > ((MAX_GRAV_READBACK_BYTES + 2) // 3) * 4:
            raise GravPublishError(
                "Grav remote readback exceeded the content size limit"
            )
        try:
            content = base64.b64decode(compact, validate=True)
        except (ValueError, TypeError) as exc:
            raise GravPublishError(
                "Grav remote readback content is not valid base64"
            ) from exc
        if len(content) > MAX_GRAV_READBACK_BYTES:
            raise GravPublishError(
                "Grav remote readback exceeded the content size limit"
            )
        return blob_sha, content

    def _reconcile_ambiguous_put(
        self,
        *,
        operation: Dict,
        repo_path: str,
        expected_content: bytes,
        expected_content_sha256: str,
        failure_label: str,
        cause: Exception,
    ) -> Dict:
        try:
            remote_blob_sha, remote_content = self._read_remote_article(repo_path)
        except Exception as readback_exc:
            raise GravPartialPublishError(
                operation,
                GravPublishError(
                    f"GitHub PUT {failure_label} and exact target readback failed: "
                    f"{readback_exc}"
                ),
            ) from cause
        remote_content_sha256 = hashlib.sha256(remote_content).hexdigest()
        if (
            remote_content != expected_content
            or remote_content_sha256 != expected_content_sha256
        ):
            raise GravPartialPublishError(
                operation,
                GravPublishError(
                    f"GitHub PUT {failure_label} and target readback differs from "
                    "expected content"
                ),
            ) from cause
        return {
            **operation,
            "action": "recovered",
            "recovered_after_timeout": failure_label == "timed out",
            "recovered_after_ambiguous_failure": True,
            "commit_url": "",
            "content_url": "",
            "remote_blob_sha": remote_blob_sha,
            "remote_content_sha256": remote_content_sha256,
        }

    def push_article(self, repo_path: str, content: str, message: str) -> Dict:
        """Create or update ``repo_path`` and reconcile ambiguous PUT outcomes."""
        if not self.repo:
            raise GravPublishError(
                "GRAV_REPO is not set. Set it in .env to publish, or use dry-run mode."
            )

        expected_content = content.encode("utf-8")
        expected_content_sha256 = hashlib.sha256(expected_content).hexdigest()
        operation = {
            "repo": self.repo,
            "branch": self.branch,
            "repo_path": repo_path,
            "expected_content_sha256": expected_content_sha256,
        }
        payload = {
            "message": message,
            "content": base64.b64encode(expected_content).decode("ascii"),
            "branch": self.branch,
        }
        existing_sha = self._get_existing_sha(repo_path)
        if existing_sha:
            payload["sha"] = existing_sha

        try:
            code, out = self._gh_api(
                [
                    "-X",
                    "PUT",
                    f"repos/{self.repo}/contents/{repo_path}",
                    "--input",
                    "-",
                ],
                payload=payload,
            )
        except GravRequestTimeout as exc:
            return self._reconcile_ambiguous_put(
                operation=operation,
                repo_path=repo_path,
                expected_content=expected_content,
                expected_content_sha256=expected_content_sha256,
                failure_label="timed out",
                cause=exc,
            )

        if code != 0:
            failure = GravPublishError(f"GitHub Contents API error:\n{out}")
            status_match = GH_HTTP_STATUS_RE.search(out)
            status = int(status_match.group("status")) if status_match else None
            if status in GH_DEFINITIVE_WRITE_STATUSES:
                raise failure
            return self._reconcile_ambiguous_put(
                operation=operation,
                repo_path=repo_path,
                expected_content=expected_content,
                expected_content_sha256=expected_content_sha256,
                failure_label="failed ambiguously",
                cause=failure,
            )

        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            failure = GravPublishError(f"Unexpected gh response:\n{out}")
            return self._reconcile_ambiguous_put(
                operation=operation,
                repo_path=repo_path,
                expected_content=expected_content,
                expected_content_sha256=expected_content_sha256,
                failure_label="returned an invalid response",
                cause=failure,
            )
        if not isinstance(data, dict):
            failure = GravPublishError(f"Unexpected gh response:\n{out}")
            return self._reconcile_ambiguous_put(
                operation=operation,
                repo_path=repo_path,
                expected_content=expected_content,
                expected_content_sha256=expected_content_sha256,
                failure_label="returned an invalid response",
                cause=failure,
            )
        commit = data.get("commit")
        content_record = data.get("content")
        push = {
            **operation,
            "action": "updated" if existing_sha else "created",
            "commit_url": commit.get("html_url", "")
            if isinstance(commit, dict)
            else "",
            "content_url": (
                content_record.get("html_url", "")
                if isinstance(content_record, dict)
                else ""
            ),
        }
        expected_blob_sha = (
            content_record.get("sha") if isinstance(content_record, dict) else None
        )
        if (
            not push["commit_url"]
            or not push["content_url"]
            or not isinstance(expected_blob_sha, str)
            or not expected_blob_sha
        ):
            failure = GravPublishError(
                "GitHub commit response omitted audit URLs or the content blob SHA"
            )
            return self._reconcile_ambiguous_put(
                operation=operation,
                repo_path=repo_path,
                expected_content=expected_content,
                expected_content_sha256=expected_content_sha256,
                failure_label="returned an incomplete response",
                cause=failure,
            )
        try:
            remote_blob_sha, remote_content = self._read_remote_article(repo_path)
            if remote_blob_sha != expected_blob_sha:
                raise GravPublishError(
                    "Grav remote readback blob SHA does not match the commit"
                )
            if remote_content != expected_content:
                raise GravPublishError(
                    "Grav remote readback content differs from the article"
                )
        except Exception as exc:
            if isinstance(exc, GravPartialPublishError):
                raise
            raise GravPartialPublishError(push, exc) from exc
        push["remote_blob_sha"] = remote_blob_sha
        push["remote_content_sha256"] = hashlib.sha256(remote_content).hexdigest()
        return push

    # ------------------------------------------------------------------ publish

    def publish(
        self,
        file_path: str,
        dry_run: bool = False,
        lang: Optional[str] = None,
        proof_sidecar: Optional[str] = None,
        context_request: Optional[str] = None,
        context_pack: Optional[str] = None,
        context_receipt: Optional[str] = None,
        assembly_bom: Optional[str] = None,
        vault_root: Optional[str | Path] = None,
    ) -> Dict:
        """
        Publish a draft/rewrite file to the Grav repo.

        When ``dry_run`` is True, the generated article is written to a local preview folder and
        no network call is made. A live request without GRAV_REPO fails closed.
        """
        if lang:
            self.lang = _validate_language_tag(lang)
        if not dry_run and not self.repo:
            raise GravPublishError(
                "GRAV_REPO is not set. Configure it for live publish or explicitly use dry-run mode."
            )

        effective_dry_run = bool(dry_run)
        before_readiness = read_publishable_markdown(file_path)
        preflight_draft = GravPublisher.parse_draft_file(
            self,
            file_path,
            snapshot=before_readiness,
        )
        try:
            _validate_grav_public_fields(preflight_draft)
            validate_publish_content(before_readiness.body)
        except PublishContentSafetyError as exc:
            raise GravPublishError(str(exc)) from exc
        readiness_input_paths = {
            "proof_sidecar": proof_sidecar,
            "context_request": context_request,
            "context_pack": context_pack,
            "context_receipt": context_receipt,
            "assembly_bom": assembly_bom,
        }
        before_readiness_inputs = (
            capture_file_snapshots(readiness_input_paths)
            if not effective_dry_run
            else {}
        )
        if not effective_dry_run:
            _require_publish_readiness(
                file_path,
                proof_sidecar,
                "Grav publish",
                context_request=context_request,
                context_pack=context_pack,
                context_receipt=context_receipt,
                assembly_bom=assembly_bom,
                vault_root=vault_root,
            )
            sealed_snapshot = read_publishable_markdown(file_path)
            try:
                ensure_same_snapshot(before_readiness, sealed_snapshot)
                sealed_readiness_inputs = capture_file_snapshots(readiness_input_paths)
                ensure_same_file_snapshots(
                    before_readiness_inputs,
                    sealed_readiness_inputs,
                )
            except ValueError as exc:
                raise GravPublishError(str(exc)) from exc
        else:
            sealed_snapshot = before_readiness
            sealed_readiness_inputs = {}

        def ensure_current_inputs() -> None:
            try:
                ensure_same_snapshot(
                    sealed_snapshot,
                    read_publishable_markdown(file_path),
                )
                ensure_same_file_snapshots(
                    sealed_readiness_inputs,
                    capture_file_snapshots(readiness_input_paths),
                )
            except ValueError as exc:
                raise GravPublishError(str(exc)) from exc

        draft = self.parse_draft_file(file_path, snapshot=sealed_snapshot)
        try:
            _validate_grav_public_fields(draft)
            validate_publish_content(draft["content"])
        except PublishContentSafetyError as exc:
            raise GravPublishError(str(exc)) from exc
        article = self.build_article(draft)
        repo_path = self.article_repo_path(draft["slug"])
        word_count = len(draft["content"].split())

        result = {
            "slug": draft["slug"],
            "path": repo_path,
            "branch": self.branch,
            "title": draft["title"],
            "word_count": word_count,
            "lang": self.lang,
            "article": article,
            "source_sha256": sealed_snapshot.sha256,
            "article_sha256": hashlib.sha256(article.encode("utf-8")).hexdigest(),
            "publish_input_sha256": {
                label: snapshot.sha256
                for label, snapshot in sealed_readiness_inputs.items()
            },
        }

        if effective_dry_run:
            preview_path = self.preview_root / draft["slug"] / f"article.{self.lang}.md"
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            preview_path.write_text(article, encoding="utf-8")
            result.update(
                {
                    "dry_run": True,
                    "preview_path": str(preview_path),
                    "commit_url": "",
                }
            )
            return result

        ensure_current_inputs()
        push = self.push_article(
            repo_path=repo_path,
            content=article,
            message=f"Publish blog post: {draft['title']}",
        )
        try:
            ensure_current_inputs()
        except GravPublishError as exc:
            raise GravPartialPublishError(push, exc) from exc
        result.update({"dry_run": False, **push})
        return result


def _validate_grav_public_fields(draft: Dict) -> None:
    """Validate every public scalar or taxonomy value emitted to Grav."""
    for field in (
        "title",
        "display_title",
        "meta_title",
        "meta_description",
        "primary_keyword",
        "secondary_keywords",
        "author",
        "last_updated",
        "slug",
    ):
        validate_publish_plain_text(draft.get(field, ""), field=field)
    slug = str(draft.get("slug") or "")
    if not slug or slug in {".", ".."} or not GRAV_PATH_SEGMENT_RE.fullmatch(slug):
        raise PublishContentSafetyError(
            "unsafe plain text for slug: expected one safe path segment"
        )


def _validate_language_tag(value: str) -> str:
    """Validate a safe language tag for an ``article.<lang>.md`` filename."""
    candidate = str(value or "").strip()
    if not GRAV_LANGUAGE_RE.fullmatch(candidate):
        raise GravPublishError("unsafe Grav language tag")
    return candidate


def _validate_blog_path(value: str) -> str:
    """Validate a non-empty repository-relative Grav blog directory."""
    candidate = str(value or "").strip().replace("\\", "/")
    if (
        not candidate
        or candidate.startswith("/")
        or candidate.endswith("/")
        or ":" in candidate
    ):
        raise GravPublishError("unsafe Grav blog path")
    segments = candidate.split("/")
    if any(
        segment in {"", ".", ".."} or not GRAV_PATH_SEGMENT_RE.fullmatch(segment)
        for segment in segments
    ):
        raise GravPublishError("unsafe Grav blog path")
    return "/".join(segments)


def _require_publish_readiness(
    file_path: str,
    proof_sidecar: Optional[str],
    context: str,
    *,
    context_request: Optional[str] = None,
    context_pack: Optional[str] = None,
    context_receipt: Optional[str] = None,
    assembly_bom: Optional[str] = None,
    vault_root: Optional[str | Path] = None,
) -> Dict:
    result = run_publish_readiness(
        file_path,
        proof_sidecar=proof_sidecar,
        context_request=context_request,
        context_pack=context_pack,
        context_receipt=context_receipt,
        assembly_bom=assembly_bom,
        vault_root=vault_root,
    )
    if result.get("passed"):
        return result
    raise GravPublishError(
        f"Publish readiness failed before {context}:\n"
        f"{_format_readiness_blockers(result)}"
    )


def _format_readiness_blockers(result: Dict) -> str:
    lines = []
    for gate in result.get("gates", []):
        if gate.get("passed"):
            continue
        name = gate.get("name", "unknown_gate")
        label = gate.get("label", name)
        lines.append(f"- {name} ({label})")
        for blocker in gate.get("blockers", [])[:3]:
            lines.append(f"  - {blocker}")
    if not lines:
        for fix in result.get("priority_fixes", [])[:3]:
            lines.append(f"- {fix.get('issue', 'readiness blocker')}")
    return "\n".join(lines) if lines else "- readiness failed"


def main():
    """CLI entry point."""
    import sys
    import argparse
    from dotenv import load_dotenv

    # Windows consoles default to cp1252; article bodies and output may contain non-ASCII.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    parser = argparse.ArgumentParser(
        description="Publish a draft/rewrite to Grav CMS via GitHub"
    )
    parser.add_argument("file_path", help="Path to the draft/rewrite markdown file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and preview the article locally without pushing to GitHub",
    )
    parser.add_argument(
        "--lang", default=None, help="Language code for article file (default: en)"
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar for publish-readiness proof gates",
    )
    parser.add_argument("--context-request", help="Connector context request JSON path")
    parser.add_argument("--context-pack", help="Connector context pack JSON path")
    parser.add_argument(
        "--context-receipt", help="Connector validation receipt JSON path"
    )
    parser.add_argument("--assembly-bom", help="Blog assembly BOM JSON path")
    parser.add_argument("--vault-root", help="Configured Simpro vault root override")
    args = parser.parse_args()

    try:
        publisher = GravPublisher()
        result = publisher.publish(
            args.file_path,
            dry_run=args.dry_run,
            lang=args.lang,
            proof_sidecar=args.proof_sidecar,
            context_request=args.context_request,
            context_pack=args.context_pack,
            context_receipt=args.context_receipt,
            assembly_bom=args.assembly_bom,
            vault_root=args.vault_root,
        )

        print(f"\n[OK] Parsed draft: {result['title']}")
        print(
            f"[OK] Built {result['word_count']:,}-word Grav article ({result['lang']})"
        )
        print(f"[OK] Slug: {result['slug']}")
        print(f"[OK] Repo path: {result['path']}  (branch: {result['branch']})")

        if result.get("dry_run"):
            print("\n[dry run] No push performed.")
            print(f"Preview written to: {result['preview_path']}")
            print("\n----- article.{lang}.md -----".format(lang=result["lang"]))
            print(result["article"])
        else:
            print(f"\n[OK] {result['action'].title()} on branch '{result['branch']}'")
            if result.get("commit_url"):
                print(f"Commit: {result['commit_url']}")
            if result.get("content_url"):
                print(f"File:   {result['content_url']}")

    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    except GravPublishError as exc:
        print(f"Grav publish error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
