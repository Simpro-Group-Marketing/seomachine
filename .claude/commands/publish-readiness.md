# Publish Readiness Command

Run the complete source-artifact gate stack for a blog draft, rewrite, published article artifact, or landing page.

## Ownership

`/publish-readiness` is the release owner. It validates, scores, assembles readiness evidence, and writes readiness/BOM governance artifacts. It must not draft, rewrite, or patch public blog Markdown.

For public copy changes, return the failed gates and priority fixes to `/write`, `/rewrite`, or `/optimize`.

## Usage

```powershell
python data_sources/modules/blog_creation_preflight.py "[article]" --proof-sidecar "[sidecar]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --keyword-decision "[keyword-decision]" --scrub-receipt "[scrub-receipt]" --customer-proof-evidence "[selector-evidence]" --fred-authority-evidence "[fred-evidence]" --editorial-plan "[editorial-plan]" --serp-evidence "[serp-evidence]" --stage-receipt "[governance-receipt]" --paa-artifact "[paa-artifact-or-brief]" --assembly-date "[YYYY-MM-DD]" --output "[pre-bom-report]"
python data_sources/modules/blog_assembly_bom.py build "[article]" --validation-sidecar "[sidecar]" --editorial-plan "[editorial-plan]" --keyword-decision "[keyword-decision]" --serp-evidence "[serp-evidence]" --paa-artifact "[paa-artifact-or-brief]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --customer-proof-selector-evidence "[selector-evidence]" --fred-authority-evidence "[fred-evidence]" --stage-receipt "[governance-receipt]" --workflow-mode "[new|rewrite]" --assembly-date "[YYYY-MM-DD]" --output "[provisional-bom]"
python data_sources/modules/publish_readiness.py "[article]" --proof-sidecar "[sidecar]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --assembly-bom "[provisional-bom]" --phase preflight --output "[preflight-readiness]"
python data_sources/modules/blog_assembly_bom.py finalize --bom "[provisional-bom]" --preflight-readiness "[preflight-readiness]" --output "[final-bom]"
python data_sources/modules/publish_readiness.py "[article]" --proof-sidecar "[sidecar]" --context-request "[request]" --context-pack "[pack]" --context-receipt "[receipt]" --assembly-bom "[final-bom]" --phase final --output "[final-readiness-attestation]"
```

Proceed to BOM build only when the pre-BOM report has `ready_for_bom: true`. A Semrush UI timeout/reset is `blocked_semrush_ui_refresh`; rerun the authenticated main Chrome Semrush UI workflow and do not substitute Semrush API, MCP, stale exports, or estimates.

Omit context request/pack/receipt only when Context Binding classifies the final article as non-connector and the sidecar records the not-applicable rationale.

## Gate stack

The runner enforces artifact identity, Context Binding, Blog Assembly BOM, public artifact checks, AI copy linting, URL validation, public research link checks, Metric Proof Pack, numeric claim source, conditional FAQ answer quality and FAQ proof, PAA provenance, editorial plan, Semrush keyword decision, source support, customer proof diversity, review story identity, E-E-A-T strength, early artifact, answer withholding, vault brand language, named feature status, Fred authority, input seal, and content scoring.

## Scorecard

The readiness output must include a `scorecard` with independent pass/fail records:

- `content_quality`: score, threshold 85 for blogs, threshold 75 for landing pages, passed.
- `seo_quality`: score, release-floor threshold 90, advisory target 95, passed, `target_met`, `target_status`, and `critical_issue_count` of 0. Blog readiness fails if the release-floor gate fails.
- `aeo_geo`: score, threshold 90 for blogs, passed. Blog readiness fails if this gate fails.

A passed blog readiness result is invalid if any scorecard gate fails, if SEO has critical issues, or if the top-level content/AEO scores disagree with the scorecard.

## Output

Report:

- Overall pass/fail.
- One row per gate with error and warning counts.
- Content score and threshold.
- SEO score, release floor, advisory target, target status, and critical issue count.
- AEO/GEO score and threshold.
- Priority fixes and the next owning command.

If readiness fails, do not mutate article copy inside this command. Return the root cause to `/optimize`, `/write`, or `/rewrite`.

For detailed proof, PAA, FAQ, schema, customer proof, E-E-A-T strength, Fred authority, named feature, and vault language policy, use `context/aeo-geo-blog-strategy.md`.
