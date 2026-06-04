---
name: grav-publish
version: 1.0.0
description: When the user wants to publish or push a finished blog article to Grav CMS via GitHub — committing blogs/<slug>/article.en.md to the dev branch. Also use when the user mentions "publish to Grav," "push to Grav dev," "Grav CMS," "article.en.md," or "publish the rewrite/draft to the blog repo." For WordPress publishing, use the /publish-draft command instead.
---

# Grav Publish

Publishes a finished article from `drafts/` or `rewrites/` to the Grav CMS GitHub repository.
The article is converted into a Grav `article.en.md` (YAML frontmatter + Markdown body) and
committed directly to the `dev` branch via the GitHub Contents API using the already-authenticated
`gh` CLI — no local clone of the Grav repo is required.

Images are **out of scope** for this version (text only). Image folders will be handled in a
later iteration.

## When to use

- The user has a finished article in `drafts/` or `rewrites/` and wants it live in Grav.
- The user says "publish this to Grav," "push the rewrite to dev," etc.

This skill only relocates already-approved body content. Do not inject, rewrite, or strip
anything beyond the frontmatter block and the leading H1 (which Grav renders from frontmatter).
Honor the content boundaries in `CLAUDE.md` — the article body must already be publish-ready.

## How it works

The logic lives in `data_sources/modules/grav_publisher.py`. It:

1. Parses the draft's YAML-style frontmatter (`Meta Title`, `Meta Description`, `Primary Keyword`,
   `Secondary Keywords`, `Author`, `Last Updated`, `URL Slug`) and Markdown body.
2. Derives the slug — precedence: `URL Slug` → filename (the blog title) → H1.
3. Builds standard Grav blog frontmatter (`title`, `date`, `taxonomy.category/tag`,
   `metadata.description/keywords`, `author`, `published: true`) plus the body with the
   frontmatter and leading H1 removed.
4. Commits `blogs/<slug>/article.en.md` to the `dev` branch (creates or updates).

## Configuration

Read from the repo-root `.env`:

| Variable | Purpose | Default |
|----------|---------|---------|
| `GRAV_REPO` | `owner/repo` of the Grav GitHub repo (required to push) | _(unset)_ |
| `GRAV_BRANCH` | Branch to commit to | `dev` |
| `GRAV_BLOG_PATH` | Blog folder path inside the repo | `blogs` |
| `GRAV_DEFAULT_LANG` | Language code for the article file | `en` |

If `GRAV_REPO` is unset, the publisher automatically runs in dry-run mode (no push).

## Workflow

1. Resolve the input file the user named in `drafts/` or `rewrites/`.
2. **Always preview first** with a dry run, and show the user the generated `article.en.md`:

   ```bash
   python data_sources/modules/grav_publisher.py <path-to-draft-or-rewrite> --dry-run
   ```

   The preview is also written to `.grav-preview/<slug>/article.en.md` at the repo root.

3. After the user confirms the frontmatter and slug look right (and `GRAV_REPO` is set), push:

   ```bash
   python data_sources/modules/grav_publisher.py <path-to-draft-or-rewrite>
   ```

4. Report the slug, the `blogs/<slug>/article.en.md` path, and the returned commit URL.

## Notes & open items

- Publishing commits **directly to `dev`** (no PR) by design.
- The Grav frontmatter mapping uses a **standard Grav blog schema**. Once a real `article.en.md`
  sample from the Grav theme is available, update `build_grav_frontmatter()` in
  `grav_publisher.py` to match — it is the single place the mapping lives.
- Folder naming defaults to a plain `<slug>/`. If the Grav blog uses numeric ordering prefixes
  (e.g. `01.<slug>/`), adjust `article_repo_path()`.
- Images: deferred. Add image upload + relative path rewriting in a future iteration.
