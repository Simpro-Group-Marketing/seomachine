# Optimize Command

Use `/optimize [article file]` for findings and targeted edits after an article exists. Optimization is a findings and targeted edit loop, not a separate finalization path.

## Ownership

The command/agent applies public-copy edits. Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

Python may run guards and write governance artifacts such as scorer output, selector evidence, context binding evidence, BOM JSON, readiness JSON, and publisher transport payloads.

## Required workflow

1. Run `/publish-readiness [article]` first unless the user explicitly requested a read-only audit.
2. Read the failed gates, `scorecard`, `aeo_geo.checks`, and `priority_fixes`.
3. Classify each issue as a public-copy gap, validation-sidecar/proof gap, or scorer/parser false negative.
4. Apply only the highest-impact 3 to 5 fixes. Do not invent PAA questions, proof, metrics, rankings, customer stories, quotes, or unsupported product claims to gain points.
5. Run `/scrub [article]` as read-only diagnostics and make any required copy edits through the command/agent workflow.
6. Rerun `/publish-readiness` with the current sidecar, context artifacts, and BOM.

## Specialist routing

- Content quality, answer completeness, or AEO/GEO findings: `content-analyzer` and `editor`.
- On-page SEO findings: `seo-optimizer`.
- Meta title or description findings: `meta-creator`.
- Internal-link findings: `internal-linker`.
- Keyword coverage, placement, or intent findings: `keyword-mapper`.

Run only the agents needed for the failed checks. Agents return advisory findings against one immutable snapshot; `/optimize` applies one consolidated edit batch and remains the sole copy owner for the repair.

## Native edit receipt

Open the optimization receipt before the consolidated edit batch and close it after `/optimize` saves the Markdown. Bind the predecessor receipt hash from the current chain.

```powershell
python data_sources/modules/blog_assembly_stage_receipt.py begin-native-edit --article "[article]" --state "research/stage-receipts/[topic-slug]/optimization-state.json" --run-id "[run-id]" --stage optimization --tool-name "optimize-command" --tool-version "1" --previous-receipt-hash "[previous-receipt-hash]"
# /optimize applies and saves one native edit batch here.
python data_sources/modules/blog_assembly_stage_receipt.py finish-native-edit --article "[article]" --state "research/stage-receipts/[topic-slug]/optimization-state.json" --receipt "research/stage-receipts/[topic-slug]/optimization.json"
```

## Scorecard requirements

Optimization is not ready until `/publish-readiness` reports:

- Content quality: 85/100 or higher.
- SEO quality: 90/100 or higher with zero critical SEO issues.
- AEO/GEO: 90/100 or higher.
- Every blocking proof, source, URL, public-artifact, identity, context, FAQ, PAA, customer-proof, Fred authority, named-feature, and vault-language gate passes.

If the article remains below threshold after 2 repair loops, move it to `review-required/` with the exact failed checks and attempted fixes.

For detailed policy, use `context/aeo-geo-blog-strategy.md`.
