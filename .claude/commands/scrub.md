# Scrub Command

Use this command to remove invisible Unicode marks, em dashes, and whitespace artifacts from markdown content files.

## Usage
`/scrub [file path]`

## What This Command Does
1. Removes invisible Unicode marks commonly embedded in generated content
2. Replaces em dashes with contextually appropriate commas or periods
3. Cleans up whitespace and formatting artifacts
4. Provides statistics on changes made

## What This Command Does Not Do
`/scrub` is a cleanup step, not the AI copy detection gate. Run the AI copy linter after scrub:

```bash
python data_sources/modules/ai_copy_linter.py [file-path] --profile simpro-web --fail-on error
```

The linter catches AI-writing giveaways, Simpro style violations, passive voice, filler, modal verbs, rhetorical setup questions, hashtags, semicolons, and unsupported hype terms.

## Process

### 1. Watermark Detection And Removal

The scrubber identifies and removes several types of invisible Unicode characters:

- **Zero-width spaces** (U+200B): Often inserted between words
- **Byte Order Marks** (U+FEFF): BOM characters that should not appear in content
- **Zero-width non-joiners** (U+200C): Invisible formatting characters
- **Word joiners** (U+2060): Non-breaking invisible characters
- **Soft hyphens** (U+00AD): Optional hyphenation points
- **Narrow no-break spaces** (U+202F): Special spacing characters
- **All format-control characters**: Unicode category Cf characters

### 2. Em Dash Replacement

The scrubber replaces em dashes with visible punctuation:

- **Attribution**: Replaces with a comma when used for quotes or attribution
- **Strong breaks**: Replaces with a period when separating distinct sentences
- **Simple separation**: Replaces with a comma for list items or short asides
- **Conjunctive adverbs**: Replaces with a period before words like "however", "therefore", or "moreover"

The scrubber does not introduce semicolons.

### 3. Whitespace Normalization

After removing marks and replacing em dashes, the scrubber cleans up formatting:

- **Multiple spaces**: Reduces multiple consecutive spaces to single spaces
- **Punctuation spacing**: Removes spaces before punctuation marks
- **Post-punctuation spacing**: Ensures single spaces after sentence-ending punctuation where appropriate
- **Excessive line breaks**: Reduces 3+ consecutive line breaks to 2

## Output

The command displays:

```text
Content Scrubbing Complete:
  - Unicode watermarks removed: [count]
  - Format-control chars removed: [count]
  - Em-dashes replaced: [count]
  - AI phrases replaced: [count]
```

The original file is overwritten with cleaned content unless an output path is supplied by the module API.

## Integration With Writing Workflow

After `/write`, `/rewrite`, `/article`, or `/landing-write` saves a content file:

1. Run `/scrub [file-path]`
2. Run `python data_sources/modules/ai_copy_linter.py [file-path] --profile simpro-web --fail-on error`
3. If linter errors remain, revise once, rerun scrub, rerun lint
4. If errors remain after revision, route to `review-required/` with lint findings
5. Include linter warnings in review notes unless strict mode is requested

## Technical Details

Scrubbing is implemented in:

- **Module**: `data_sources/modules/content_scrubber.py`
- **Main Function**: `scrub_file(file_path, output_path, verbose)`
- **Class**: `ContentScrubber`

AI copy detection is implemented in:

- **Module**: `data_sources/modules/ai_copy_linter.py`
- **Main Functions**: `lint_content(content, profile="simpro-web")` and `lint_file(path, profile="simpro-web", fail_on="error")`

## Idempotency

The scrubber is idempotent. Running it multiple times on already cleaned content should produce no additional changes.

## Example Usage

```bash
/scrub drafts/content-marketing-strategies-2025-10-31.md
python data_sources/modules/ai_copy_linter.py drafts/content-marketing-strategies-2025-10-31.md --profile simpro-web --fail-on error
```

## Quality Standards

Every scrubbed file should have:

- Zero invisible Unicode marks
- No em dashes
- No scrubber-introduced semicolons
- Clean whitespace formatting

Every linted file should have:

- Zero linter errors before scoring or optimization
- Warning findings captured in review notes
