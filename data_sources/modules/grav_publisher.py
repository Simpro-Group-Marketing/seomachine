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
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class GravPublishError(RuntimeError):
    """Raised when a Grav publish operation fails."""


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
        self.blog_path = (blog_path or os.getenv("GRAV_BLOG_PATH", "blogs")).strip("/")
        self.lang = lang or os.getenv("GRAV_DEFAULT_LANG", "en")

    # ------------------------------------------------------------------ parsing

    def parse_draft_file(self, file_path: str) -> Dict:
        """
        Parse a draft/rewrite markdown file into its metadata and body.

        Real drafts use a YAML-style frontmatter block delimited by ``---`` with fields like
        ``Meta Title:``, ``Meta Description:``, ``Primary Keyword:``, ``Secondary Keywords:``,
        ``Author:``, ``Last Updated:``, and ``URL Slug:``, followed by an H1 and the body.

        Returns a dict with keys: title, meta_title, meta_description, primary_keyword,
        secondary_keywords, author, last_updated, slug, content.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Draft file not found: {file_path}")

        raw = path.read_text(encoding="utf-8")
        frontmatter, body = self._split_frontmatter(raw)

        def field(*names: str) -> str:
            for name in names:
                if name.lower() in frontmatter:
                    return frontmatter[name.lower()]
            return ""

        # H1 is the fallback title and is stripped from the body (Grav renders the
        # title from frontmatter, so a body H1 would duplicate it).
        h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        h1_title = h1_match.group(1).strip() if h1_match else ""
        body = re.sub(r"^#\s+.+\n?", "", body, count=1).strip()

        meta_title = field("Meta Title")
        title = meta_title or h1_title

        slug = self._derive_slug(
            url_slug=field("URL Slug"),
            file_stem=path.stem,
            title=h1_title or meta_title,
        )

        return {
            "title": title,
            "meta_title": meta_title or title,
            "meta_description": field("Meta Description"),
            "primary_keyword": field("Primary Keyword", "Target Keyword"),
            "secondary_keywords": field("Secondary Keywords"),
            "author": field("Author"),
            "last_updated": field("Last Updated"),
            "slug": slug,
            "content": body,
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
        secondary = [t.strip() for t in draft.get("secondary_keywords", "").split(",") if t.strip()]
        keywords = [k for k in [draft.get("primary_keyword", "").strip(), *secondary] if k]

        lines: List[str] = ["---"]
        lines.append(f"title: {self._yaml_quote(draft['title'])}")
        lines.append(f"date: {self._yaml_quote(self._format_date(draft.get('last_updated', '')))}")
        lines.append("taxonomy:")
        lines.append("    category:")
        lines.append("        - blog")
        if secondary:
            lines.append("    tag:")
            for tag in secondary:
                lines.append(f"        - {self._yaml_quote(tag)}")
        lines.append("metadata:")
        if draft.get("meta_description"):
            lines.append(f"    description: {self._yaml_quote(draft['meta_description'])}")
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
        """Path inside the Grav repo: ``<blog_path>/<slug>/article.<lang>.md``."""
        return f"{self.blog_path}/{slug}/article.{self.lang}.md"

    # --------------------------------------------------------------- gh api push

    def _gh_api(self, args: List[str], payload: Optional[Dict] = None) -> "tuple[int, str]":
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
            )
        except OSError as exc:  # pragma: no cover - environment dependent
            raise GravPublishError(f"Failed to run gh: {exc}") from exc
        out = result.stdout if result.returncode == 0 else (result.stderr or result.stdout)
        return result.returncode, out

    def _get_existing_sha(self, repo_path: str) -> Optional[str]:
        """Return the blob sha if the file already exists on the branch, else None."""
        code, out = self._gh_api(
            [f"repos/{self.repo}/contents/{repo_path}", "-f", f"ref={self.branch}"]
        )
        if code != 0:
            return None
        try:
            return json.loads(out).get("sha")
        except (json.JSONDecodeError, AttributeError):
            return None

    def push_article(self, repo_path: str, content: str, message: str) -> Dict:
        """Create or update ``repo_path`` on the configured branch via the Contents API."""
        if not self.repo:
            raise GravPublishError(
                "GRAV_REPO is not set. Set it in .env to publish, or use dry-run mode."
            )

        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": self.branch,
        }
        existing_sha = self._get_existing_sha(repo_path)
        if existing_sha:
            payload["sha"] = existing_sha

        code, out = self._gh_api(
            ["-X", "PUT", f"repos/{self.repo}/contents/{repo_path}", "--input", "-"],
            payload=payload,
        )
        if code != 0:
            raise GravPublishError(f"GitHub Contents API error:\n{out}")

        try:
            data = json.loads(out)
        except json.JSONDecodeError as exc:
            raise GravPublishError(f"Unexpected gh response:\n{out}") from exc

        return {
            "action": "updated" if existing_sha else "created",
            "commit_url": (data.get("commit") or {}).get("html_url", ""),
            "content_url": (data.get("content") or {}).get("html_url", ""),
        }

    # ------------------------------------------------------------------ publish

    def publish(self, file_path: str, dry_run: bool = False, lang: Optional[str] = None) -> Dict:
        """
        Publish a draft/rewrite file to the Grav repo.

        When ``dry_run`` is True (or GRAV_REPO is unset), the generated article is written to a
        local preview folder and no network call is made.
        """
        if lang:
            self.lang = lang

        draft = self.parse_draft_file(file_path)
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
        }

        if dry_run or not self.repo:
            preview_root = Path(__file__).resolve().parents[2] / ".grav-preview"
            preview_path = preview_root / draft["slug"] / f"article.{self.lang}.md"
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            preview_path.write_text(article, encoding="utf-8")
            result.update({
                "dry_run": True,
                "preview_path": str(preview_path),
                "commit_url": "",
            })
            return result

        push = self.push_article(
            repo_path=repo_path,
            content=article,
            message=f"Publish blog post: {draft['title']}",
        )
        result.update({"dry_run": False, **push})
        return result


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

    parser = argparse.ArgumentParser(description="Publish a draft/rewrite to Grav CMS via GitHub")
    parser.add_argument("file_path", help="Path to the draft/rewrite markdown file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and preview the article locally without pushing to GitHub",
    )
    parser.add_argument("--lang", default=None, help="Language code for article file (default: en)")
    args = parser.parse_args()

    try:
        publisher = GravPublisher()
        result = publisher.publish(args.file_path, dry_run=args.dry_run, lang=args.lang)

        print(f"\n[OK] Parsed draft: {result['title']}")
        print(f"[OK] Built {result['word_count']:,}-word Grav article ({result['lang']})")
        print(f"[OK] Slug: {result['slug']}")
        print(f"[OK] Repo path: {result['path']}  (branch: {result['branch']})")

        if result.get("dry_run"):
            print(f"\n[dry run] No push performed.")
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
