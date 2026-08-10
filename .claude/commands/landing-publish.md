# Landing Page Publish Command

## Context Binding Regeneration (MANDATORY)

After the final content mutation, regenerate the machine-owned binding before `/publish-readiness` and before any WordPress API call:

```bash
python data_sources/modules/context_binding_generator.py "$FILE_PATH" --proof-sidecar "$PROOF_SIDECAR" --context-request "$CONTEXT_REQUEST" --context-pack "$CONTEXT_PACK" --context-receipt "$CONTEXT_RECEIPT"
```

If the landing page changes after this command, stop and regenerate the binding again.

Use this command to publish landing pages to WordPress as pages (not blog posts).

## Usage
`/landing-publish [file path] [options]`

**Options:**
- `--noindex`: Set noindex meta (for PPC pages)
- `--template [slug]`: Use specific WordPress page template

**Examples:**
- `/landing-publish landing-pages/product-hosting-beginners-2025-12-11.md`
- `/landing-publish landing-pages/free-trial-ppc-2025-12-11.md --noindex`
- `/landing-publish landing-pages/pricing-comparison-2025-12-11.md --template landing-page`

## What This Command Does

1. Validates the landing page file
2. Runs the full publish-readiness stack with current connector context artifacts
3. Parses markdown and metadata
4. Creates WordPress page via REST API
5. Sets Yoast SEO fields
6. Returns edit URL for review

## Prerequisites

Before publishing, ensure:
1. Full publish readiness passes with the current context request, pack, and receipt
2. No critical issues remain
3. All required metadata is present
4. Content has been scrubbed for AI watermarks

## File Format Requirements

Landing page files must include this metadata:

```markdown
# [H1 Headline]

**Meta Title**: [50-60 characters ending with | Brand]
**Meta Description**: [150-160 characters]
**Target Keyword**: [primary keyword]
**Page Type**: seo | ppc
**Conversion Goal**: trial | demo | lead
**URL Slug**: /[page-slug]/

---

[Content...]
```

## Publishing Process

### Step 1: Validation

Check file exists and contains required fields:
- Meta Title (required)
- Meta Description (required)
- Target Keyword (required for SEO pages)
- Page Type
- Conversion Goal
- URL Slug

### Step 2: Publish Readiness

Run the same fail-closed gate stack used by blog publishing:
```bash
/publish-readiness "$FILE_PATH" --proof-sidecar "$PROOF_SIDECAR" --context-request "$CONTEXT_REQUEST" --context-pack "$CONTEXT_PACK" --context-receipt "$CONTEXT_RECEIPT"
```

Context Binding must pass before downstream proof, URL, quality, or handoff gates. A landing-page score alone never authorizes a WordPress API call.

### Step 3: Content Preparation

1. Parse metadata from file header
2. Extract main content (markdown)
3. Convert markdown to HTML
4. Prepare Yoast SEO fields

### Step 4: WordPress API Call

Uses existing `wordpress_publisher.py` module:

```python
from data_sources.modules.wordpress_publisher import WordPressPublisher

publisher = WordPressPublisher()

result = publisher.publish_draft(
    file_path,
    post_type="page",
    noindex=noindex,
    template=template_slug,
    proof_sidecar=proof_sidecar,
    context_request=context_request,
    context_pack=context_pack,
    context_receipt=context_receipt,
)
```

### Step 5: Additional Settings

`WordPressPublisher.publish_draft` sends `template` in the page-creation payload and
`robots_noindex` in the registered `yoast_seo` REST field. It verifies the returned
Yoast values. A metadata failure after page creation returns a partial-publish error
containing the existing page ID and edit URL so the workflow does not create a duplicate.

## Output

### Successful Publish
```
=== Landing Page Published ===

Status: Draft created
Page ID: [ID]
Edit URL: https://yoursite.com/wp-admin/post.php?post=[ID]&action=edit

Next Steps:
1. Review the page in WordPress
2. Check formatting and images
3. Set featured image if needed
4. Publish when ready

Landing Page Score: [X]/100
```

### Failed Publish
```
=== Publishing Failed ===

Reason: [Error message]

If score too low:
- Current Score: [X]/100
- Required Score: 75/100
- Critical Issues:
  1. [Issue 1]
  2. [Issue 2]

Run `/landing-audit landing-pages/[file].md` for full analysis.
```

## Differences from /publish-draft

| Aspect | /publish-draft (Blog) | /landing-publish (Pages) |
|--------|----------------------|--------------------------|
| WordPress Type | Post | Page |
| Categories/Tags | Yes | No |
| Score Required | Full publish-readiness stack PASS | Full publish-readiness stack PASS |
| noindex Option | No | Yes (for PPC) |
| Template Option | No | Yes |
| Output Directory | drafts/ | landing-pages/ |

## Pre-Publish Checklist

Before running this command, verify:

### Content
- [ ] Headline is benefit-focused
- [ ] Value proposition is clear
- [ ] CTAs use action verbs
- [ ] Trust signals present
- [ ] Risk reversal near CTAs
- [ ] FAQ section (for SEO pages)

### Meta
- [ ] Meta title 50-60 characters ending with `| Brand`
- [ ] Meta title includes keyword
- [ ] Meta description 150-160 characters
- [ ] Meta description includes CTA
- [ ] URL slug is clean and short

### Technical
- [ ] Content scrubbed for AI watermarks
- [ ] Full publish-readiness stack passed with current context request, pack, and receipt
- [ ] No critical issues
- [ ] Proper markdown formatting

## Post-Publish Tasks

After publishing to WordPress:

1. **Review in WordPress**
   - Check formatting displays correctly
   - Verify all links work
   - Ensure CTAs are prominent

2. **Add Visuals**
   - Set featured image
   - Add any hero images
   - Add trust badges/logos

3. **Final SEO Check**
   - Verify Yoast green lights
   - Check mobile preview
   - Validate schema if applicable

4. **Publish Live**
   - Change status from Draft to Published
   - Clear any caches
   - Verify live page loads correctly

## Rollback

If issues are found after publishing:

1. In WordPress, revert to draft status
2. Fix issues in the markdown file
3. Re-run `/landing-audit` to verify score
4. Re-publish with `/landing-publish`

## Integration with Other Commands

**Typical Workflow:**
```bash
# 1. Research (optional)
/landing-research "product hosting" --type seo

# 2. Create landing page
/landing-write "product hosting" --type seo --goal trial

# 3. Audit the draft
/landing-audit landing-pages/product-hosting-2025-12-11.md

# 4. Fix any issues (if needed)
# Edit the file manually

# 5. Re-audit until score ≥75
/landing-audit landing-pages/product-hosting-2025-12-11.md

# 6. Publish
/landing-publish landing-pages/product-hosting-2025-12-11.md
```
