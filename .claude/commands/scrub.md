# Scrub Command

Use `/scrub [file path]` to inspect Markdown for invisible Unicode marks, em dashes, and whitespace artifacts.

## Contract

`/scrub` is read-only diagnostics. It reports what would change and must not overwrite article Markdown. The command/agent applies any needed copy edits through the normal writing workflow, then reruns `/scrub`.

Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

## What it checks

- Zero-width spaces, byte order marks, soft hyphens, word joiners, and other format-control characters.
- Em dashes that must be changed by the command/agent because Simpro public web copy prohibits them.
- Obvious whitespace artifacts.

## Companion gates

`/scrub` is not the AI-copy gate and not the release. The release that `/publish-readiness` runs includes the AI copy linter: its `editorial_process_leakage` rule blocks, and its other findings are warnings.

If the linter reports `editorial_process_leakage`, treat it as a required public-copy recovery item. Move workflow rationale to frontmatter or the research brief, or translate it into reader-facing guidance, before rerunning `/scrub`.

Before handoff, run `/publish-readiness [article]` so the release checks truth, coverage, and the three scores.

## Output

Return diagnostic counts and whether changes are needed. Do not claim the article changed unless you actually edited it through the command/agent workflow.
