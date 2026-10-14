# Publish Draft to WordPress

Publishes a released blog article from this project to WordPress as a Draft, with all SEO metadata auto-populated.

## Precondition: a passing release record

A blog post publishes only when its latest release record passed for the exact article bytes on disk. `/publish-readiness` writes that record. Before any WordPress API call, the command runs:

```bash
python -m data_sources.modules.production.record verify "$FILE_PATH"
```

Exit `0` means publishable. Exit `1` prints the refusal reason: no record, a failing release, or an article, BOM, spec, or evidence file changed since the passing release. Fix it through `/write`, `/rewrite`, or `/optimize`, then rerun `/publish-readiness`. Exit `2` is a layout error: the article must sit directly in `drafts/` or `rewrites/` as `<slug>-YYYY-MM-DD.md`. The publisher enforces the same check internally and rechecks the article hash before every WordPress write.

The retired readiness flags (`--proof-sidecar`, `--context-request`, `--context-pack`, `--context-receipt`, `--assembly-bom`, `--vault-root`) are refused for blog posts with exit `2`. Landing pages use `/landing-publish`, which keeps its own readiness gate and flags.

## Usage
`/publish-draft [filename] [--type post|page]`

### Examples

**Create a blog post (default):**
```
/publish-draft drafts/content-marketing-guide-[YYYY-MM-DD].md
```

**Create a page:**
```
/publish-draft drafts/pricing-comparison.md --type page
```

### Post Types
- `post` - Standard blog post (default) - supports categories and tags; requires a passing release record
- `page` - WordPress page - no categories/tags; runs the landing-page readiness gate (see `/landing-publish`)

Any other type, including custom post types, is rejected before any WordPress request.

## What This Command Does

1. **Checks the release record** - Runs `python -m data_sources.modules.production.record verify "$FILE_PATH"` before any WordPress API call
2. **Parses the draft file** - Extracts all metadata from frontmatter
3. **Converts Markdown to HTML** - Formats content for WordPress
4. **Creates WordPress draft** - Posts via REST API with status "draft"
5. **Sets Yoast SEO fields**:
   - SEO Title (from Meta Title)
   - Meta Description
   - Focus Keyphrase (from Target Keyword)
6. **Assigns taxonomy** - Categories and Tags if specified
7. **Records proof use** - After the draft and its Yoast fields are written, adds one `config/customer-proof-usage-ledger.json` entry for each production BOM proof item the article links
8. **Returns edit URL** - Direct link to edit the post in WordPress

## Metadata Mapping

| Draft Field | WordPress/Yoast Field |
|-------------|----------------------|
| H1 Title | Post Title |
| Meta Title | Yoast SEO Title |
| Meta Description | Yoast Meta Description + Excerpt |
| Target Keyword | Yoast Focus Keyphrase |
| URL Slug | Post Slug |
| Category | Post Categories |
| Tags | Post Tags |
| Content | Post Content (HTML) |

## Required Environment Variables

These must be set in `.env`:
```
WORDPRESS_URL=https://yoursite.com
WORDPRESS_USERNAME=your-username
WORDPRESS_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

### Getting an Application Password
1. Log into WordPress Admin
2. Go to Users > Your Profile
3. Scroll to "Application Passwords"
4. Enter a name (e.g., "SEO Machine")
5. Click "Add New Application Password"
6. Copy the generated password to your `.env` file

## Process

When you run this command:

### Step 1: Validate File
- Confirm the draft file exists
- Parse metadata and content
- Display extracted fields for confirmation

### Step 2: Check the Release Record
Run the record check before any WordPress request:
```bash
python -m data_sources.modules.production.record verify "$FILE_PATH"
```

If it refuses, report the printed reason and do not create a WordPress draft.

### Step 3: Publish to WordPress
Run the WordPress publisher:
```bash
cd /path/to/seomachine
python -m data_sources.modules.wordpress_publisher "$FILE_PATH"
```

A ledger failure after the draft exists is reported as a partial publish with the draft's edit URL; review that draft instead of retrying.

### Step 4: Confirm Success
Display the WordPress edit URL so the user can review and publish.

## Optional: Add Categories/Tags

To assign categories or tags, add these fields to your draft frontmatter:

```markdown
**Category**: [Your Category]
**Tags**: [your topic], beginner, getting started
```

Multiple categories/tags are comma-separated.

## Troubleshooting

### "WORDPRESS_URL must be set"
Add credentials to `.env` file. See Required Environment Variables above.

### "401 Unauthorized"
- Verify username is correct
- Regenerate Application Password
- Ensure user has permission to create posts

### "Could not find category"
The category will be created automatically if it doesn't exist.

## Notes

- Posts are always created as **drafts** (never published automatically)
- The H1 heading from the article becomes the WordPress post title
- Images/media are not uploaded - only text content is transferred
- Rerunning on the same unchanged file returns the matching existing draft (found by its publication key) instead of creating a duplicate; the ledger records each proof use once per article and day
- A passing release record for the exact article bytes must exist before WordPress network calls begin
