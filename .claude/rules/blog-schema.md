# Blog Schema Rule

Apply this rule to every standard blog draft, rewrite, and published Markdown handoff.

Always use these schema notes:

- BlogPosting
- BreadcrumbList
- ImageObject for the featured image or logo
- Organization as publisher reference only, not a separate full schema block

Add `FAQPage` plus `Question and Answer inside FAQPage` if and only if visible FAQs exist. When the FAQ policy is `not_applicable`, omit both.

If a named author is present, include `author` in frontmatter and map it to `Person as author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and record the no-author decision in the research brief and in the production BOM spec's `schema_notes` choice by leaving out `Person as author`.

For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. Require `artifact_type`, `brand`, `title`, `objective`, `audience`, `region`, and a valid ISO `last_updated` matching the article date. Use VideoObject only when a verified video is embedded. Keep public article bodies free of structured-data implementation plans.

A comparison of tools may add one optional `ItemList for the [N] compared tools, with exactly [N] ListItem entries` note with a matching `item_list_entries` list, validated by `data_sources/modules/schema_item_list.py`. It goes in the article frontmatter only; the BOM spec vocabulary does not carry it.

The BOM build refuses a spec `schema_notes` entry outside the allowed vocabulary. At release, the AEO/GEO scorer's schema check compares the article frontmatter `schema_notes` with the article (FAQ, author, video, and `ItemList` conditions above), and its metadata check blocks a `last_updated` that is missing, invalid, or later than the release date. Frontmatter `title` is effectively required: coverage blocks a title it cannot read and a title without the primary keyword. No release check requires `artifact_type`, `brand`, `objective`, `audience`, or `region`; they remain the CMS handoff contract. Canonical policy lives in `context/aeo-geo-blog-strategy.md`.
