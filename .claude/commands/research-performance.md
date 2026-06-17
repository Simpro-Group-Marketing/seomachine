# Research Performance Command

Analyze content performance and produce a prioritized optimization or rewrite recommendation.

## Usage

```text
/research-performance
/research-performance [blog URL or path]
```

Examples:

```text
/research-performance
/research-performance https://www.simprogroup.com/blog/hvac-ppc
/research-performance /blog/hvac-ppc
```

## Command Contract

This is a slash-command workflow. The agent executing `/research-performance` is responsible for calling the required repo scripts, MCP tools, and data-source modules internally. Do not ask the user to run Python scripts by hand.

Use the all-content mode when no URL is provided. Use target-specific mode when a URL or blog path is provided.

## All-Content Mode

When the user runs `/research-performance` with no argument:

1. Pull or consult the current GA4/GSC-backed performance queue.
2. Categorize eligible blog content into priority groups.
3. Identify the strongest next rewrite, optimization, or internal-linking opportunity.
4. Save the output to `research/performance-review-[YYYY-MM-DD].md` or the closest existing performance artifact pattern.
5. Return the top priorities and the recommended next slash command.

## Target-Specific Mode

When the user runs `/research-performance [blog URL or path]`:

1. Normalize the input to a canonical blog URL and path.
2. Pull GA4 performance for the page across useful windows, including since publish when the publish date is available, last 90 days, and last 30 days.
3. Pull GSC page/query performance for the target URL.
4. Inspect the live page for title, H1, structure, intent fit, and obvious regional or proof issues.
5. Compare the live evidence against any local performance shortlist or existing research artifact.
6. Save a target-specific artifact:
   `research/performance-review-[topic-slug]-[YYYY-MM-DD].md`
7. Return a clear verdict:
   - rewrite
   - optimize
   - update title/meta/internal links only
   - monitor/no action

## Required Evidence

The report must include:

- Target URL and normalized page path
- GA4 property/source used
- GSC property/source used
- Date ranges
- Sessions, views, active users, engagement, bounce rate, average session duration, and key events
- Organic sessions or GSC clicks/impressions/CTR where available
- Top relevant queries with clicks, impressions, CTR, and position
- Diagnosis of the primary weakness
- Recommended next slash command

## Output

For a target-specific run, save:

```text
research/performance-review-[topic-slug]-[YYYY-MM-DD].md
```

For an all-content run, save:

```text
research/performance-review-[YYYY-MM-DD].md
```

If the repo already has a more specific output convention for the current workflow, use that convention and report the saved path.

## Integration

After `/research-performance`:

- Use `/rewrite [URL]` when the article needs a substantive rewrite.
- Use `/optimize [file]` when a rewritten or drafted artifact already exists.
- Use `/analyze-existing [URL]` when more structural or SERP-specific analysis is needed before deciding.

Do not expose internal scripts as user-required steps. If script execution is needed, run it as part of this command workflow and report the saved artifact.
