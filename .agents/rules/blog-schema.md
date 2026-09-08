# Blog Schema Rule

Apply this rule to standard blog drafts, rewrites, and published Markdown handoffs. Schema remains a later CMS stage; this rule checks the handoff only.

For every standard blog, use these primary schema notes:

- BlogPosting
- BreadcrumbList
- FAQPage only when visible FAQs exist

Nested entities:

- Person as author only when a verified author exists; Missing author passes
- Question and Answer inside FAQPage only when visible FAQs exist
- ImageObject for the featured image or logo
- Organization as publisher reference only, not a separate full schema block

For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. Use VideoObject if and only if a video is embedded. Schema notes must never be reported as rendered JSON-LD implementation. Keep public article bodies free of structured-data implementation plans. Canonical policy lives in `context/aeo-geo-blog-strategy.md`.
