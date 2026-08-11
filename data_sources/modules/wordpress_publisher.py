"""
WordPress Publisher Module

Publishes draft articles to WordPress as draft posts via the REST API.
Supports Yoast SEO meta fields (title, description, focus keyphrase).
"""

import hashlib
import os
import re

import requests
from typing import Dict, Optional, List
from pathlib import Path

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


WORDPRESS_REQUEST_TIMEOUT = (5, 30)
MAX_TAXONOMY_PAGES = 100
SOURCE_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PAGE_TEMPLATE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PUBLICATION_KEY_META = "seo_machine_publication_key"
SOURCE_SHA256_META = "seo_machine_source_sha256"


class WordPressPartialPublishError(RuntimeError):
    """A WordPress draft exists, but a required follow-up operation failed."""

    def __init__(self, post_id: int, edit_url: str, operation: str, cause: Exception):
        self.post_id = post_id
        self.edit_url = edit_url
        self.operation = operation
        self.cause = cause
        super().__init__(
            f"WordPress draft was created as post {post_id}, but {operation} failed: "
            f"{cause}. Review the existing draft at {edit_url}; do not retry blindly."
        )


class WordPressPublisher:
    """WordPress REST API client for publishing drafts"""

    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        app_password: Optional[str] = None
    ):
        """
        Initialize WordPress publisher

        Args:
            url: WordPress site URL (defaults to env var WORDPRESS_URL)
            username: WordPress username (defaults to env var WORDPRESS_USERNAME)
            app_password: Application password (defaults to env var WORDPRESS_APP_PASSWORD)
        """
        self.url = (url or os.getenv('WORDPRESS_URL', '')).rstrip('/')
        self.username = username or os.getenv('WORDPRESS_USERNAME')
        self.app_password = app_password or os.getenv('WORDPRESS_APP_PASSWORD')

        if not self.url:
            raise ValueError("WORDPRESS_URL must be set")
        if not self.username or not self.app_password:
            raise ValueError("WORDPRESS_USERNAME and WORDPRESS_APP_PASSWORD must be set")

        self.api_base = f"{self.url}/wp-json/wp/v2"
        self.session = requests.Session()
        self.session.auth = (self.username, self.app_password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SEOMachine/1.0 (WordPress Content Publisher)'
        })

        # Cache for categories and tags
        self._categories_cache: Optional[Dict[str, int]] = None
        self._tags_cache: Optional[Dict[str, int]] = None

    def parse_draft_file(
        self,
        file_path: str,
        snapshot: Optional[PublishableMarkdown] = None,
    ) -> Dict:
        """
        Parse a markdown draft file and extract metadata and content

        Args:
            file_path: Path to the markdown file

        Returns:
            Dict with keys: title, meta_title, meta_description, target_keyword,
                           secondary_keywords, slug, category, tags, content
        """
        artifact = snapshot or read_publishable_markdown(file_path)
        title = artifact.h1 or artifact.scalar("display_title", "title", "meta_title")
        meta_title = artifact.scalar("meta_title", "title") or title
        meta_description = artifact.scalar("meta_description")
        target_keyword = artifact.scalar("target_keyword", "primary_keyword")
        secondary_keywords = ", ".join(artifact.values("secondary_keywords"))
        category = ", ".join(artifact.values("category"))
        tags = ", ".join(artifact.values("tags"))
        slug = metadata_path_tail(artifact.scalar("url_slug", "target_url"))
        if not slug:
            slug = re.sub(r'[^\w\s-]', '', title.lower())
            slug = re.sub(r'[\s_]+', '-', slug)

        return {
            'title': title,
            'meta_title': meta_title or title,
            'meta_description': meta_description,
            'target_keyword': target_keyword,
            'secondary_keywords': secondary_keywords,
            'slug': slug,
            'category': category,
            'tags': tags,
            'content': artifact.body
        }

    def markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert markdown to HTML for WordPress

        Args:
            markdown_content: Markdown formatted content

        Returns:
            HTML formatted content
        """
        try:
            import markdown
            md = markdown.Markdown(extensions=['extra', 'nl2br', 'sane_lists'])
            return md.convert(markdown_content)
        except ImportError:
            # Fallback: basic markdown conversion
            html = markdown_content

            # Convert headers
            html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
            html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
            html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

            # Convert bold and italic
            html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
            html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

            # Convert links
            html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

            # Convert unordered lists
            html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

            # Wrap paragraphs
            paragraphs = html.split('\n\n')
            wrapped = []
            for p in paragraphs:
                p = p.strip()
                if p and not p.startswith('<'):
                    wrapped.append(f'<p>{p}</p>')
                else:
                    wrapped.append(p)
            html = '\n\n'.join(wrapped)

            return html

    def get_categories(self) -> Dict[str, int]:
        """Get all categories as name->ID mapping"""
        if self._categories_cache is not None:
            return self._categories_cache

        categories = {}
        page = 1
        while page <= MAX_TAXONOMY_PAGES:
            response = self.session.get(
                f"{self.api_base}/categories",
                params={'per_page': 100, 'page': page},
                timeout=WORDPRESS_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            items = response.json()
            if not items:
                break
            for cat in items:
                categories[cat['name'].lower()] = cat['id']
            total_pages = _response_total_pages(response)
            if total_pages is not None:
                if page >= total_pages:
                    break
            elif len(items) < 100:
                break
            page += 1
        else:
            raise RuntimeError(
                f"WordPress category pagination exceeded {MAX_TAXONOMY_PAGES} pages"
            )

        self._categories_cache = categories
        return categories

    def get_tags(self) -> Dict[str, int]:
        """Get all tags as name->ID mapping"""
        if self._tags_cache is not None:
            return self._tags_cache

        tags = {}
        page = 1
        while page <= MAX_TAXONOMY_PAGES:
            response = self.session.get(
                f"{self.api_base}/tags",
                params={'per_page': 100, 'page': page},
                timeout=WORDPRESS_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            items = response.json()
            if not items:
                break
            for tag in items:
                tags[tag['name'].lower()] = tag['id']
            total_pages = _response_total_pages(response)
            if total_pages is not None:
                if page >= total_pages:
                    break
            elif len(items) < 100:
                break
            page += 1
        else:
            raise RuntimeError(
                f"WordPress tag pagination exceeded {MAX_TAXONOMY_PAGES} pages"
            )

        self._tags_cache = tags
        return tags

    def get_or_create_category(self, name: str) -> int:
        """Get category ID, creating if it doesn't exist"""
        categories = self.get_categories()
        name_lower = name.lower().strip()

        if name_lower in categories:
            return categories[name_lower]

        # Create new category
        response = self.session.post(
            f"{self.api_base}/categories",
            json={'name': name.strip()},
            timeout=WORDPRESS_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        new_cat = response.json()
        self._categories_cache[name_lower] = new_cat['id']
        return new_cat['id']

    def get_or_create_tag(self, name: str) -> int:
        """Get tag ID, creating if it doesn't exist"""
        tags = self.get_tags()
        name_lower = name.lower().strip()

        if name_lower in tags:
            return tags[name_lower]

        # Create new tag
        response = self.session.post(
            f"{self.api_base}/tags",
            json={'name': name.strip()},
            timeout=WORDPRESS_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        new_tag = response.json()
        self._tags_cache[name_lower] = new_tag['id']
        return new_tag['id']

    @staticmethod
    def _publication_key(post_type: str, slug: str, source_sha256: str) -> str:
        """Return a stable idempotency key for one source artifact and destination."""
        normalized_hash = str(source_sha256 or "").strip().lower()
        if not SOURCE_SHA256_RE.fullmatch(normalized_hash):
            raise ValueError("WordPress source SHA-256 must be 64 lowercase hex characters")
        material = f"seo-machine-publication/v1\n{post_type}\n{slug}\n{normalized_hash}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _find_existing_draft(
        self,
        *,
        title: str,
        content: str,
        slug: str,
        excerpt: str,
        category_ids: List[int],
        tag_ids: List[int],
        post_type: str,
        template: str,
        publication_key: str,
        source_sha256: str,
    ) -> Optional[Dict]:
        """Find one exact prior draft created for the same sealed source input."""
        matches: list[Dict] = []
        unmanaged_matches: list[Dict] = []
        page = 1
        while page <= MAX_TAXONOMY_PAGES:
            params = {
                "slug": slug,
                "status": "draft",
                "context": "edit",
                "per_page": 100,
            }
            if page > 1:
                params["page"] = page
            response = self.session.get(
                f"{self.api_base}/{post_type}",
                params=params,
                timeout=WORDPRESS_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise RuntimeError("WordPress idempotency lookup did not return a list")
            for candidate in payload:
                if not isinstance(candidate, dict):
                    continue
                meta = candidate.get("meta")
                if (
                    isinstance(meta, dict)
                    and meta.get(PUBLICATION_KEY_META) == publication_key
                    and meta.get(SOURCE_SHA256_META) == source_sha256
                ):
                    matches.append(candidate)
                elif _draft_content_matches(
                    candidate,
                    title=title,
                    content=content,
                    slug=slug,
                    excerpt=excerpt,
                    category_ids=category_ids,
                    tag_ids=tag_ids,
                    template=template,
                    post_type=post_type,
                ):
                    unmanaged_matches.append(candidate)

            total_pages = _response_total_pages(response)
            if total_pages is not None:
                if page >= total_pages:
                    break
            elif len(payload) < 100:
                break
            page += 1
        else:
            raise RuntimeError(
                f"WordPress idempotency lookup exceeded {MAX_TAXONOMY_PAGES} pages"
            )

        if len(matches) > 1 or (matches and unmanaged_matches):
            raise RuntimeError("WordPress idempotency lookup found duplicate matching drafts")
        if not matches:
            if unmanaged_matches:
                raise RuntimeError(
                    "WordPress found matching draft content missing idempotency metadata; "
                    "review it before retrying"
                )
            return None
        existing = matches[0]
        post_id = existing.get("id")
        if isinstance(post_id, bool) or not isinstance(post_id, int) or post_id <= 0:
            raise RuntimeError("WordPress idempotency lookup returned an invalid post ID")
        _validate_draft_readback(
            existing,
            post_id=post_id,
            title=title,
            content=content,
            slug=slug,
            excerpt=excerpt,
            category_ids=category_ids,
            tag_ids=tag_ids,
            template=template,
            post_type=post_type,
            publication_key=publication_key,
            source_sha256=source_sha256,
        )
        return existing
    def _reconcile_ambiguous_create(
        self,
        *,
        lookup_args: Dict,
        publication_key: str,
        cause: Exception,
    ) -> Dict:
        """Read back an ambiguous create exactly once without retrying the POST."""
        try:
            recovered = self._find_existing_draft(**lookup_args)
        except Exception as lookup_exc:
            raise RuntimeError(
                "WordPress draft create outcome is ambiguous and idempotency reconciliation "
                f"failed; publication key {publication_key} must be checked before retrying"
            ) from lookup_exc
        if recovered is not None:
            return recovered
        raise RuntimeError(
            "WordPress draft create outcome is ambiguous; "
            f"no draft with publication key {publication_key} was visible, so do not retry blindly"
        ) from cause
    def create_draft(
        self,
        title: str,
        content: str,
        slug: str,
        excerpt: str = '',
        category_ids: Optional[List[int]] = None,
        tag_ids: Optional[List[int]] = None,
        post_type: str = 'posts',
        template: str = '',
        source_sha256: str = '',
    ) -> Dict:
        """Create a WordPress draft idempotently and verify exact edit-context readback."""
        endpoint = _post_type_endpoint(post_type)
        normalized_template = _normalize_page_template(template)
        if normalized_template and endpoint != "pages":
            raise ValueError("WordPress templates are supported only for pages")
        normalized_source_hash = str(source_sha256 or "").strip().lower()
        if not normalized_source_hash:
            normalized_source_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if not SOURCE_SHA256_RE.fullmatch(normalized_source_hash):
            raise ValueError("WordPress source SHA-256 must be 64 lowercase hex characters")
        publication_key = self._publication_key(endpoint, slug, normalized_source_hash)
        categories = list(category_ids or [])
        tags = list(tag_ids or [])

        lookup_args = {
            "title": title,
            "content": content,
            "slug": slug,
            "excerpt": excerpt,
            "category_ids": categories,
            "tag_ids": tags,
            "post_type": endpoint,
            "template": normalized_template,
            "publication_key": publication_key,
            "source_sha256": normalized_source_hash,
        }
        existing = self._find_existing_draft(**lookup_args)
        if existing is not None:
            return existing

        post_data = {
            "title": title,
            "content": content,
            "slug": slug,
            "status": "draft",
            "excerpt": excerpt,
            "meta": {
                PUBLICATION_KEY_META: publication_key,
                SOURCE_SHA256_META: normalized_source_hash,
            },
        }
        if endpoint == "posts":
            if categories:
                post_data["categories"] = categories
            if tags:
                post_data["tags"] = tags
        if normalized_template:
            post_data["template"] = normalized_template

        try:
            response = self.session.post(
                f"{self.api_base}/{endpoint}",
                json=post_data,
                timeout=WORDPRESS_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except (requests.Timeout, requests.ConnectionError) as exc:
            return self._reconcile_ambiguous_create(
                lookup_args=lookup_args,
                publication_key=publication_key,
                cause=exc,
            )
        except requests.HTTPError as exc:
            error_response = exc.response if exc.response is not None else response
            status_code = getattr(error_response, "status_code", None)
            if isinstance(status_code, int) and (status_code >= 500 or status_code == 409):
                return self._reconcile_ambiguous_create(
                    lookup_args=lookup_args,
                    publication_key=publication_key,
                    cause=exc,
                )
            raise

        try:
            created = response.json()
        except (TypeError, ValueError) as exc:
            return self._reconcile_ambiguous_create(
                lookup_args=lookup_args,
                publication_key=publication_key,
                cause=exc,
            )
        post_id = created.get("id") if isinstance(created, dict) else None
        if isinstance(post_id, bool) or not isinstance(post_id, int) or post_id <= 0:
            return self._reconcile_ambiguous_create(
                lookup_args=lookup_args,
                publication_key=publication_key,
                cause=RuntimeError(
                    "WordPress draft response did not include a valid post ID"
                ),
            )
        edit_url = f"{self.url}/wp-admin/post.php?post={post_id}&action=edit"
        try:
            readback_response = self.session.get(
                f"{self.api_base}/{endpoint}/{post_id}",
                params={"context": "edit"},
                timeout=WORDPRESS_REQUEST_TIMEOUT,
            )
            readback_response.raise_for_status()
            readback = readback_response.json()
            _validate_draft_readback(
                readback,
                post_id=post_id,
                title=title,
                content=content,
                slug=slug,
                excerpt=excerpt,
                category_ids=categories,
                tag_ids=tags,
                template=normalized_template,
                post_type=endpoint,
                publication_key=publication_key,
                source_sha256=normalized_source_hash,
            )
        except Exception as exc:
            raise WordPressPartialPublishError(
                post_id,
                edit_url,
                "draft readback",
                exc,
            ) from exc
        return readback
    def set_yoast_meta(
        self,
        post_id: int,
        meta_title: str,
        meta_description: str,
        focus_keyphrase: str,
        post_type: str = 'posts',
        noindex: bool = False,
    ) -> Dict:
        """
        Set Yoast SEO meta fields on a post or page

        Requires the SEO Machine Yoast REST plugin to be installed:
        wp-content/mu-plugins/seo-machine-yoast-rest.php

        Args:
            post_id: WordPress post ID
            meta_title: SEO title
            meta_description: Meta description
            focus_keyphrase: Focus keyphrase (target keyword)
            post_type: WordPress post type endpoint ('posts' or 'pages')

        Returns:
            Updated post response
        """
        # Use the yoast_seo field provided by our mu-plugin
        yoast_data = {
            'yoast_seo': {
                'seo_title': meta_title,
                'meta_description': meta_description,
                'focus_keyphrase': focus_keyphrase,
                'robots_noindex': bool(noindex),
            }
        }

        response = self.session.post(
            f"{self.api_base}/{post_type}/{post_id}",
            json=yoast_data,
            timeout=WORDPRESS_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        returned = result.get('yoast_seo') if isinstance(result, dict) else None
        expected = yoast_data['yoast_seo']
        if not isinstance(returned, dict) or any(
            returned.get(key) != value for key, value in expected.items()
        ):
            raise RuntimeError("WordPress did not confirm the requested Yoast metadata")
        return result

    def publish_draft(
        self,
        file_path: str,
        post_type: str = 'post',
        proof_sidecar: Optional[str] = None,
        context_request: Optional[str] = None,
        context_pack: Optional[str] = None,
        context_receipt: Optional[str] = None,
        assembly_bom: Optional[str] = None,
        vault_root: Optional[str | Path] = None,
        noindex: bool = False,
        template: str = '',
    ) -> Dict:
        """
        Publish a draft file to WordPress as a post or page

        Args:
            file_path: Path to the markdown draft file
            post_type: Content type: 'post', 'posts', 'page', or 'pages'.
            proof_sidecar: Optional validation sidecar for proof-aware readiness gates.
            context_request: Connector context request JSON path.
            context_pack: Connector context pack JSON path.
            context_receipt: Connector validation receipt JSON path.
            assembly_bom: Blog assembly BOM JSON path.
            vault_root: Optional configured vault-root override.

        Returns:
            Dict with post_id, edit_url, view_url, and status information
        """
        api_endpoint = _post_type_endpoint(post_type)
        normalized_template = _normalize_page_template(template)
        if normalized_template and api_endpoint != 'pages':
            raise ValueError("WordPress templates are supported only for pages")
        before_readiness = read_publishable_markdown(file_path)
        preflight_draft = WordPressPublisher.parse_draft_file(
            self,
            file_path,
            snapshot=before_readiness,
        )
        try:
            _validate_wordpress_public_fields(preflight_draft)
            validate_publish_content(
                before_readiness.body,
                rendered_html=self.markdown_to_html(before_readiness.body),
            )
        except PublishContentSafetyError as exc:
            raise ValueError(str(exc)) from exc
        readiness_input_paths = {
            "proof_sidecar": proof_sidecar,
            "context_request": context_request,
            "context_pack": context_pack,
            "context_receipt": context_receipt,
            "assembly_bom": assembly_bom,
        }
        before_readiness_inputs = capture_file_snapshots(readiness_input_paths)

        _require_publish_readiness(
            file_path,
            proof_sidecar,
            "WordPress publish",
            context_request=context_request,
            context_pack=context_pack,
            context_receipt=context_receipt,
            assembly_bom=assembly_bom,
            vault_root=vault_root,
        )
        sealed_snapshot = read_publishable_markdown(file_path)
        ensure_same_snapshot(before_readiness, sealed_snapshot)
        sealed_readiness_inputs = capture_file_snapshots(readiness_input_paths)
        ensure_same_file_snapshots(before_readiness_inputs, sealed_readiness_inputs)

        def ensure_current_inputs() -> None:
            ensure_same_snapshot(
                sealed_snapshot,
                read_publishable_markdown(file_path),
            )
            ensure_same_file_snapshots(
                sealed_readiness_inputs,
                capture_file_snapshots(readiness_input_paths),
            )

        # Parse the draft file
        draft = self.parse_draft_file(file_path, snapshot=sealed_snapshot)
        try:
            _validate_wordpress_public_fields(draft)
        except PublishContentSafetyError as exc:
            raise ValueError(str(exc)) from exc

        # Convert content to HTML and reject unsafe source or rendered markup before writes.
        html_content = self.markdown_to_html(draft['content'])
        try:
            validate_publish_content(draft["content"], rendered_html=html_content)
        except PublishContentSafetyError as exc:
            raise ValueError(str(exc)) from exc
        word_count = len(draft['content'].split())

        # Process categories (only for posts)
        category_ids = []
        if api_endpoint == 'posts' and draft['category']:
            cat_names = [c.strip() for c in draft['category'].split(',')]
            for cat_name in cat_names:
                if cat_name:
                    ensure_current_inputs()
                    category_ids.append(self.get_or_create_category(cat_name))

        # Process tags (only for posts)
        tag_ids = []
        if api_endpoint == 'posts' and draft['tags']:
            tag_names = [t.strip() for t in draft['tags'].split(',')]
            for tag_name in tag_names:
                if tag_name:
                    ensure_current_inputs()
                    tag_ids.append(self.get_or_create_tag(tag_name))

        # Create the draft
        ensure_current_inputs()
        post = self.create_draft(
            title=draft['title'],
            content=html_content,
            slug=draft['slug'],
            excerpt=draft['meta_description'],
            category_ids=category_ids if category_ids else None,
            tag_ids=tag_ids if tag_ids else None,
            post_type=api_endpoint,
            template=normalized_template,
            source_sha256=sealed_snapshot.sha256,
        )

        post_id = post['id']

        # Build edit URL before follow-up writes so partial success can be reported.
        edit_url = f"{self.url}/wp-admin/post.php?post={post_id}&action=edit"
        try:
            ensure_current_inputs()
        except ValueError as exc:
            raise WordPressPartialPublishError(
                post_id,
                edit_url,
                "publish inputs changed after draft creation",
                exc,
            ) from exc

        # Set Yoast meta
        if (
            draft['meta_title']
            or draft['meta_description']
            or draft['target_keyword']
            or noindex
        ):
            try:
                ensure_current_inputs()
                self.set_yoast_meta(
                    post_id=post_id,
                    meta_title=draft['meta_title'],
                    meta_description=draft['meta_description'],
                    focus_keyphrase=draft['target_keyword'],
                    post_type=api_endpoint,
                    noindex=noindex,
                )
                ensure_current_inputs()
            except Exception as exc:
                raise WordPressPartialPublishError(
                    post_id,
                    edit_url,
                    "Yoast metadata update",
                    exc,
                ) from exc

        return {
            'post_id': post_id,
            'post_type': post_type,
            'edit_url': edit_url,
            'view_url': post.get('link', ''),
            'title': draft['title'],
            'slug': draft['slug'],
            'source_sha256': sealed_snapshot.sha256,
            'publish_input_sha256': {
                label: snapshot.sha256
                for label, snapshot in sealed_readiness_inputs.items()
            },
            'noindex': bool(noindex),
            'template': normalized_template,
            'word_count': word_count,
            'categories': [c.strip() for c in draft['category'].split(',')] if draft['category'] else [],
            'tags': [t.strip() for t in draft['tags'].split(',')] if draft['tags'] else [],
            'meta': {
                'title': draft['meta_title'],
                'description': draft['meta_description'],
                'focus_keyphrase': draft['target_keyword']
            }
        }


def _validate_wordpress_public_fields(draft: Dict) -> None:
    """Validate every public scalar or taxonomy value emitted to WordPress."""
    for field in (
        "title",
        "meta_title",
        "meta_description",
        "target_keyword",
        "secondary_keywords",
        "category",
        "tags",
        "slug",
    ):
        validate_publish_plain_text(draft.get(field, ""), field=field)
    slug = str(draft.get("slug") or "")
    if (
        not slug
        or slug in {".", ".."}
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", slug)
    ):
        raise PublishContentSafetyError(
            "unsafe plain text for slug: expected one safe URL path segment"
        )

def _draft_content_matches(
    payload: Dict,
    *,
    title: str,
    content: str,
    slug: str,
    excerpt: str,
    category_ids: List[int],
    tag_ids: List[int],
    template: str,
    post_type: str,
) -> bool:
    """Return whether a draft matches all public create fields except idempotency metadata."""
    if payload.get("status") != "draft" or payload.get("slug") != slug:
        return False
    for field, expected in {
        "title": title,
        "content": content,
        "excerpt": excerpt,
    }.items():
        value = payload.get(field)
        if not isinstance(value, dict) or value.get("raw") != expected:
            return False
    if post_type == "posts":
        return (
            payload.get("categories") == category_ids
            and payload.get("tags") == tag_ids
        )
    return payload.get("template", "") == template

def _validate_draft_readback(
    payload: object,
    *,
    post_id: int,
    title: str,
    content: str,
    slug: str,
    excerpt: str,
    category_ids: List[int],
    tag_ids: List[int],
    template: str,
    post_type: str,
    publication_key: str,
    source_sha256: str,
) -> None:
    """Require WordPress edit-context readback to match the created draft."""
    if not isinstance(payload, dict):
        raise RuntimeError("WordPress draft readback is not an object")
    expected_scalars = {
        "id": post_id,
        "status": "draft",
        "slug": slug,
    }
    for field, expected in expected_scalars.items():
        if payload.get(field) != expected:
            raise RuntimeError(
                f"WordPress draft readback mismatch for {field}: {payload.get(field)!r}"
            )
    for field, expected in {
        "title": title,
        "content": content,
        "excerpt": excerpt,
    }.items():
        value = payload.get(field)
        if not isinstance(value, dict) or value.get("raw") != expected:
            raise RuntimeError(f"WordPress draft readback mismatch for {field}")
    if post_type == "posts":
        if payload.get("categories") != category_ids:
            raise RuntimeError("WordPress draft readback mismatch for categories")
        if payload.get("tags") != tag_ids:
            raise RuntimeError("WordPress draft readback mismatch for tags")
    if post_type == "pages" and payload.get("template", "") != template:
        raise RuntimeError("WordPress draft readback mismatch for template")
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise RuntimeError("WordPress draft readback omitted publication metadata")
    if meta.get(PUBLICATION_KEY_META) != publication_key:
        raise RuntimeError("WordPress draft readback mismatch for publication key")
    if meta.get(SOURCE_SHA256_META) != source_sha256:
        raise RuntimeError("WordPress draft readback mismatch for source SHA-256")


def _normalize_page_template(template: str) -> str:
    """Return a safe relative classic-template identifier without changing case."""
    candidate = str(template or "").strip()
    if not candidate:
        return ""
    if (
        candidate.startswith("/")
        or candidate.endswith("/")
        or "\\" in candidate
        or ":" in candidate
        or "?" in candidate
        or "#" in candidate
    ):
        raise ValueError("WordPress page template must be a safe relative identifier")
    segments = candidate.split("/")
    if any(
        segment in {"", ".", ".."}
        or not PAGE_TEMPLATE_SEGMENT_RE.fullmatch(segment)
        for segment in segments
    ):
        raise ValueError("WordPress page template must be a safe relative identifier")
    return "/".join(segments)


def _post_type_endpoint(post_type: str) -> str:
    """Return one supported WordPress REST collection endpoint."""
    normalized = str(post_type).strip().lower()
    endpoint = {
        'post': 'posts',
        'posts': 'posts',
        'page': 'pages',
        'pages': 'pages',
    }.get(normalized)
    if endpoint is None:
        raise ValueError("WordPress post type must be posts or pages only")
    return endpoint


def _response_total_pages(response: requests.Response) -> Optional[int]:
    """Read and validate the WordPress pagination bound when provided."""
    raw_value = response.headers.get("X-WP-TotalPages")
    if raw_value is None:
        return None
    try:
        total_pages = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("WordPress returned an invalid X-WP-TotalPages header") from exc
    if total_pages < 0 or total_pages > MAX_TAXONOMY_PAGES:
        raise ValueError("WordPress returned an unsafe taxonomy page count")
    return total_pages


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
    raise ValueError(
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
    """CLI entry point for testing"""
    import sys
    import argparse
    from dotenv import load_dotenv

    # Load environment variables
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)

    parser = argparse.ArgumentParser(description='Publish a draft to WordPress')
    parser.add_argument('file_path', help='Path to the markdown draft file')
    parser.add_argument(
        '--type', '-t',
        default='post',
        help='Content type: post, page, or custom post type (default: post)'
    )
    parser.add_argument(
        '--proof-sidecar',
        help='Optional validation sidecar for publish-readiness proof gates',
    )
    parser.add_argument('--context-request', help='Connector context request JSON path')
    parser.add_argument('--context-pack', help='Connector context pack JSON path')
    parser.add_argument('--context-receipt', help='Connector validation receipt JSON path')
    parser.add_argument('--assembly-bom', help='Blog assembly BOM JSON path')
    parser.add_argument('--vault-root', help='Configured Simpro vault root override')
    parser.add_argument('--noindex', action='store_true', help='Request Yoast noindex metadata')
    parser.add_argument('--template', default='', help='WordPress page template slug')
    args = parser.parse_args()

    try:
        publisher = WordPressPublisher()
        result = publisher.publish_draft(
            args.file_path,
            post_type=args.type,
            proof_sidecar=args.proof_sidecar,
            context_request=args.context_request,
            context_pack=args.context_pack,
            context_receipt=args.context_receipt,
            assembly_bom=args.assembly_bom,
            vault_root=args.vault_root,
            noindex=args.noindex,
            template=args.template,
        )

        type_label = result['post_type'].title()
        print("\n[OK] Parsed draft file")
        print(f"[OK] Converted {result['word_count']:,} words to HTML")
        print(f"[OK] Created WordPress {type_label} draft (ID: {result['post_id']})")
        print("[OK] Set Yoast meta (title, description, focus keyphrase, index policy)")

        if result['categories']:
            print(f"[OK] Assigned categories: {', '.join(result['categories'])}")
        if result['tags']:
            print(f"[OK] Assigned tags: {', '.join(result['tags'])}")

        print("\nDraft published to WordPress!")
        print(f"Edit URL: {result['edit_url']}")

    except WordPressPartialPublishError as e:
        print(f"Partial WordPress publish: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"WordPress API Error: {e}")
        print(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"WordPress network error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
