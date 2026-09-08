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

`/scrub` is not the AI-copy gate and not publish readiness. After fixing diagnostics, run:

```powershell
python data_sources/modules/ai_copy_linter.py [file-path] --profile simpro-web --fail-on error
```

If the linter reports `editorial_process_leakage`, treat it as a required public-copy recovery item. Move workflow rationale to frontmatter, the validation sidecar, the editorial plan, the optimizer output, the release BOM, or a command receipt, or translate it into reader-facing guidance before rerunning `/scrub`.

Before handoff, run `/publish-readiness [article]` so the full gate stack and independent scorecard are checked.

## Output

Return diagnostic counts and whether changes are needed. Do not claim the article changed unless you actually edited it through the command/agent workflow.
