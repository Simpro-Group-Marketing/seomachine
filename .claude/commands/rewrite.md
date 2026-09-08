# Rewrite Command

Use `/rewrite [existing article or analysis]` to revise an existing blog while preserving proof boundaries and source traceability.

## Ownership

The command/agent rewrites public Markdown. Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

Python may write governance artifacts only: selector output, context binding evidence, SERP/PAA artifacts, editorial-plan JSON, BOM JSON, readiness JSON, and publisher transport payloads.

## Required workflow

1. Read the existing article and analysis findings.
2. Resolve topic, title, objective, audience, target keyword, target URL, and rewrite path.
3. Classify Context Binding from the final brand metadata and content. Use the Simpro vault connector for Simpro-owned or cross-brand-triggered work. For AroFlo, BigChange, or ClockShark work with no Simpro name or official `simprogroup.com` URL, record the nonconnector reason and omit vault, Fred, and vault-dependent customer-proof selector artifacts.
4. Reuse pre-picked PAA from a dedicated rewrite brief when present. If no dedicated PAA exists and PAA is required, collect structured AnswerSocrates evidence. Do not invent questions.
5. Update the validation sidecar before changing proof-sensitive copy.
6. Run customer proof and Fred authority selectors only when Context Binding requires the connector, then decide what to use publicly.
7. Write the rewrite Markdown through `/rewrite`.
8. Freeze one rewrite snapshot and run `content-analyzer`, `editor`, `seo-optimizer`, `meta-creator`, `internal-linker`, and `keyword-mapper` in parallel. The Editor must use the reviewed Humanizer snapshot and Simpro policy against this same immutable rewrite snapshot. All specialists return advisory findings only. Select the useful findings and apply one consolidated edit batch through `/rewrite`.
9. Run `/scrub [article]` as read-only diagnostics. Apply any required edits through `/rewrite` and rerun `/scrub`.
10. Run `/publish-readiness [article]` with sidecar, context artifacts, and BOM. Do not hand off as ready until every blocking gate and scorecard gate passes.

## Native edit receipt

Open the receipt before native rewriting, then close it after `/rewrite` has saved the Markdown. Python observes hashes only.

```powershell
python data_sources/modules/blog_assembly_stage_receipt.py begin-native-edit --article "rewrites/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --run-id "[run-id]" --stage draft --tool-name "rewrite-command" --tool-version "1" --input "analysis=research/analysis-[topic-slug]-[YYYY-MM-DD].md"
# /rewrite creates and saves the public Markdown here.
python data_sources/modules/blog_assembly_stage_receipt.py finish-native-edit --article "rewrites/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --receipt "research/stage-receipts/[topic-slug]/draft.json" --evidence "humanizer_policy=config/humanizer-policy.json" --evidence "humanizer_upstream=vendor/blader-humanizer/UPSTREAM.json"
```

## Scorecard requirements

`/publish-readiness` must report separate gates for:

- Content quality: 85/100 or higher.
- SEO quality: 90/100 release floor with zero critical SEO issues; 95/100 honest optimization target when source-safe improvements exist.
- AEO/GEO: 90/100 or higher.

If any scorecard gate fails, repair the root copy, proof, sidecar, or scorer issue and rerun `/publish-readiness`. After 2 unsuccessful repair loops, route to `review-required/` with failed checks and attempted fixes.

For detailed proof, FAQ, PAA, review story, named feature, schema, and vault language rules, use `context/aeo-geo-blog-strategy.md`.
