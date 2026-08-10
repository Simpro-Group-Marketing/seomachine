# Blog Schema Rule

Apply this rule to standard blog drafts, rewrites, and published Markdown handoffs with FAQs.

For standard blog posts with FAQs, use these primary schema notes:

- BlogPosting
- BreadcrumbList
- FAQPage

Nested entities:

- Question and Answer inside FAQPage
- ImageObject for the featured image or logo
- Organization as publisher reference only, not a separate full schema block

If a named author is present, include `author` in frontmatter and map it to `Person as author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and record the no-author decision in the blog assembly BOM and validation sidecar.

For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. Use VideoObject only when a video is embedded. Keep public article bodies free of structured-data implementation plans. Canonical policy lives in `context/aeo-geo-blog-strategy.md`.
