# Write Command

Use `/write [topic or research brief]` to draft a blog from an approved topic, brief, or research package.

## Ownership

The command/agent writes the public Markdown. Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

Python may write governance artifacts only: selector output, context binding evidence, SERP/PAA artifacts, editorial-plan JSON, BOM JSON, readiness JSON, and publisher transport payloads.

## Required workflow

1. Read the user request and any supplied brief.
2. Resolve topic, title, objective, audience, region, target keyword, target URL, and whether the article is new or a rewrite.
3. Use the Simpro vault connector first for brand, product, feature, audience, proof, competitor, and claim decisions. Record any vault-unavailable fallback in the validation sidecar before writing proof-sensitive public copy.
4. Build or update the validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`.
5. Run mandatory selectors when applicable:
   - Customer proof selector before using customer proof.
   - Fred Voccola authority selector for every new or changed Simpro blog.
6. Write the draft Markdown to `drafts/[topic-slug]-[YYYY-MM-DD].md` using the command, not a Python writer.
7. Freeze one draft snapshot and run `content-analyzer`, `seo-optimizer`, `meta-creator`, `internal-linker`, and `keyword-mapper` in parallel. They return advisory findings only. Select the useful findings and apply one consolidated edit batch through `/write`.
8. Run `/scrub [article]` for diagnostics only. If it reports needed changes, make those edits through `/write` and rerun `/scrub`.
9. Run `/publish-readiness [article]` with the sidecar, context artifacts, and BOM. Do not hand off as ready until it passes.

## Native edit receipt

Open the draft receipt before native writing, then close it after the command has saved the Markdown. These Python calls hash and attest the edit; they do not create or modify the article.

```powershell
python data_sources/modules/blog_assembly_stage_receipt.py begin-native-edit --article "drafts/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --run-id "[run-id]" --stage draft --tool-name "write-command" --tool-version "1" --input "editorial_plan=research/editorial-plan-[topic-slug]-[YYYY-MM-DD].json"
# /write creates and saves the public Markdown here.
python data_sources/modules/blog_assembly_stage_receipt.py finish-native-edit --article "drafts/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --receipt "research/stage-receipts/[topic-slug]/draft.json"
```

## Scorecard requirements

`/publish-readiness` is the release owner and must report these independent gates:

- Content quality: 85/100 or higher.
- SEO quality: 90/100 or higher and zero critical SEO issues.
- AEO/GEO: 90/100 or higher.

Do not treat an overall score as a substitute for the SEO or AEO/GEO gates.

## Output

Return the draft path, sidecar path, evidence paths, BOM/readiness paths, scorecard, failed gates, and priority fixes. Keep proof infrastructure out of public copy.

For detailed proof and AEO/GEO policy, use `context/aeo-geo-blog-strategy.md`.
