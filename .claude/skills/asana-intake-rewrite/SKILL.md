---
name: asana-intake-rewrite
version: 1.0.0
description: Use when the user wants to submit a blog rewrite request to the simPRO marketing intake form, or says things like "submit this blog for rewrite", "create an Asana intake request", "fill out the intake form", "create a rewrite task in Asana", "intake form for this blog", or "send this to the marketing team for rewriting". Also trigger when the user has a .md blog file and wants to request a rewrite, or provides a blog file path and mentions Asana, intake, or rewrite request.
---

# Asana Intake Rewrite

Submits a blog rewrite request to the simPRO Unified Marketing Intake form by reading the
blog's `.md` file, extracting its metadata, filling the web form via Playwright browser
automation, and saving a submission receipt to `research/`.

**Form URL:** `https://form.asana.com/?k=PkocDXFD9eCZ6Zt_Q5D9Sw&d=1129643090232729`

The form is a JavaScript SPA — Playwright is the only viable approach. WebFetch will not work.

## Input

The user provides a blog file path (from `drafts/`, `rewrites/`, or any path) in their prompt.
Optionally they may include extra notes, a priority level, or a target deadline.

## Workflow

### Step 1 — Read the blog file

Read the `.md` file the user named. Extract these fields from the YAML-style frontmatter block
at the top of the file:

| Field | Frontmatter key | Fallback |
|---|---|---|
| Article title | `Meta Title:` | First H1 heading |
| URL slug / live URL | `URL Slug:` | Filename without extension |
| Primary keyword | `Primary Keyword:` | — |
| Secondary keywords | `Secondary Keywords:` | — |
| Meta description | `Meta Description:` | First paragraph |
| Author | `Author:` | `Simpro` |
| Last updated | `Last Updated:` | Today's date |

Build a short rewrite brief (3–5 sentences) summarising what the article covers, the primary
keyword it targets, and any extra notes the user added in their prompt. This becomes the form
description field.

### Step 2 — Navigate to the intake form

```
browser_navigate → https://form.asana.com/?k=PkocDXFD9eCZ6Zt_Q5D9Sw&d=1129643090232729
```

Wait for the form to load, then:

```
browser_snapshot
```

Study the snapshot carefully to identify every visible field label, input type (text, textarea,
dropdown, date, file upload, radio, checkbox), and whether it is required. **Do not hard-code
selectors.** Use only snapshot-derived targets throughout.

### Step 3 — Map blog metadata to form fields

The Unified Marketing Intake Form has the following fields. Use this mapping:

**Section: Project Overview**

| Form field | Required | Value |
|---|---|---|
| Email address | ✅ | Use Patrick's email: `patrick.grueschow@simprogroup.com` |
| Project Name | ✅ | `Blog Rewrite: [Meta Title]` |
| Project Description | ✅ | 1–2 sentence brief: what article, what keyword, what URL, what the rewrite achieves |
| KPIs/Measurable Impact | — | Organic rankings for primary keyword; traffic to the URL; AI citation presence |
| Additional Approvers | ✅ | `N/A` (unless user specifies otherwise) |
| Ideal Completion Date | ✅ | Use the calendar picker button (not free text) — click the calendar icon, then click the target date. Ask the user if not provided, or default to today for ready-to-publish rewrites. |
| Rank the priority | — | Click dropdown to see options; default to `Medium` |
| Context for Urgency | — | `N/A` (unless user specifies a deadline driver) |
| In-Market/Live Date | ✅ | Ask the user if not provided, or default to 3 weeks from today |
| Brand/Entity (checkboxes) | ✅ | Check `Simpro` |
| Region (checkboxes) | ✅ | Ask the user which regions apply — default `ANZ` for simprogroup.com.au content |
| Primary Audience (checkboxes) | — | Check `Prospects` |

**Section: Request Details**

| Form field | Required | Value |
|---|---|---|
| Bill of Materials (checkboxes) | ✅ | Check `Web - SEO Article - Update` for a blog rewrite |
| Work order/brief link | — | Leave blank (local file; use file attachment instead) |
| Additional Project Documentation | — | Leave blank unless user has an Asana board link |
| File attachment | — | Use `browser_file_upload` with the absolute path to the `.md` file |

**For the priority dropdown**, click the button to expand it, take a `browser_snapshot` to read
available options, then select the best match. Never hard-code option text.

For multi-line text fields (`Project Description`, `KPIs`, `Context for Urgency`) use
`browser_type`. For single-line fields use `browser_type` as well — these Asana form fields
are all textbox elements.

**For checkboxes**, use `browser_click` with the checkbox ref from the snapshot.

If a required field has no clear mapping from blog metadata, stop and ask the user before
proceeding.

### Step 4 — Dry-run preview

**Before submitting**, print a confirmation table like this:

```
─────────────────────────────────────────────
  ASANA INTAKE — REWRITE REQUEST PREVIEW
─────────────────────────────────────────────
  Task name    : Blog Rewrite: Payments for Trades Businesses...
  Type         : Blog Rewrite (or whichever option was selected)
  URL          : https://www.simprogroup.com/blog/modern-customer-...
  Primary KW   : payments for trades businesses
  Description  : [first 2 sentences of brief]
  Priority     : Medium
  Attachment   : rewrites/modern-customer-payment-expectations-...md
─────────────────────────────────────────────
  Ready to submit? (yes / no)
─────────────────────────────────────────────
```

Wait for the user to confirm with "yes" (or equivalent) before submitting. If they say "no" or
ask to change anything, update the field values and re-display the preview.

### Step 5 — Submit

Click the submit button using the snapshot-derived target. Take a `browser_snapshot` after
clicking to verify the form was accepted (look for a confirmation message or a redirect).

If the form shows a validation error, read the error message from the snapshot and fix the
offending field, then resubmit.

### Step 6 — Save receipt

After successful submission, save a brief receipt to:

```
research/asana-intake-[slug]-[YYYY-MM-DD].md
```

Receipt format:

```markdown
---
type: asana-intake-receipt
submitted: [YYYY-MM-DD]
form: https://form.asana.com/?k=PkocDXFD9eCZ6Zt_Q5D9Sw&d=1129643090232729
---

# Asana Intake Submitted — [Meta Title]

- **Task name:** Blog Rewrite: [Meta Title]
- **Slug:** [URL Slug]
- **Primary keyword:** [Primary Keyword]
- **Submitted:** [YYYY-MM-DD HH:MM]
- **Asana task URL:** [if shown on confirmation page, otherwise "— not displayed"]
- **Source file:** [path to .md file]
```

Report the receipt path and Asana task URL (if available) to the user.

## Error handling

- **Form not loading:** Wait up to 10 seconds, retry `browser_navigate` once.
- **Required field missing:** Stop and ask the user for the value before continuing.
- **File upload not available:** Paste the meta description + brief into the description field instead, and note the limitation in the receipt.
- **Submission error:** Read the snapshot error message, fix the field, resubmit. If the error persists, report it to the user with the full snapshot text.
- **No confirmation message visible:** Snapshot the post-submit page and report what was seen so the user can verify manually.

## Notes

- This skill uses **Playwright MCP browser automation** — the `playwright@claude-plugins-official` plugin must be enabled globally (it is, by default in this workspace).
- The Asana plugin (`asana@claude-plugins-official`) is intentionally disabled. This skill uses the public web form instead.
- Do not rewrite or edit the blog content. The `.md` file is submitted as-is.
- For WordPress publishing use `/publish-draft`. For Grav CMS publishing use `/grav-publish`.
