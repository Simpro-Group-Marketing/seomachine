# Optimize Command

Use `/optimize [article file]` for findings and targeted edits after an article exists. Optimization is a findings and targeted edit loop, not a separate finalization path.

## Ownership

The command/agent applies public-copy edits. Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

Python may run guards and write governance artifacts such as scorer output, selector evidence, context binding evidence, Semrush keyword decision JSON, BOM JSON, readiness JSON, and publisher transport payloads.

## Required workflow

1. Run `/publish-readiness [article]` first unless the user explicitly requested a read-only audit.
2. Read the failed gates, `scorecard`, `aeo_geo.checks`, and `priority_fixes`.
3. Classify each issue as a public-copy gap, validation-sidecar/proof gap, or scorer/parser false negative.
4. If `semrush_keyword_decision` fails, repair or rerun the live Semrush keyword decision artifact and regenerate the editorial plan/BOM before optimizing copy.
5. Apply only the highest-impact 3 to 5 fixes. Do not invent PAA questions, proof, metrics, rankings, customer stories, quotes, or unsupported product claims to gain points.
6. Freeze the article bytes and run the required machine reviewers for the affected issue classes. If the article bytes change, rerun the full six-agent article review before release.
7. Run `/scrub [article]` as read-only diagnostics and make any required copy edits through the command/agent workflow.
8. Rerun the atomic release wrapper or `/publish-readiness` with the current sidecar, machine reviews, context artifacts, and BOM.

## SEO target handling

- SEO below 90 or any critical SEO issue is a release-floor failure and requires repair.
- SEO 90-94 is release-pass, below-target. Run one honest, source-safe optimization pass only when the recommended fixes improve reader usefulness, search clarity, proof support, or structure.
- If SEO is 90-94 and no target-safe fix exists, document `release-pass, below-target, no honest SEO fix recommended` and keep the article publishable.
- SEO 95+ meets the advisory target. Do not run SEO-only edits unless another gate fails.

## Specialist routing

- Content quality, answer completeness, or AEO/GEO findings: `content-analyzer` and `editor`.
- On-page SEO findings: `seo-optimizer`.
- Meta title or description findings: `meta-creator`.
- Internal-link findings: `internal-linker`.
- Keyword coverage, placement, or intent findings with a passed `semrush_keyword_decision` gate: `keyword-mapper`.
- Missing, stale, mismatched, or unmeasured selected keyword findings: rerun the Semrush keyword decision workflow before copy optimization.

Run only the agents needed for initial diagnosis, then rerun the full six-agent article review before release if article bytes changed: Content Analyzer (`content-analyzer`), Editor (`editor`), SEO Optimizer (`seo-optimizer`), Meta Creator (`meta-creator`), Internal Linker (`internal-linker`), and Keyword Mapper (`keyword-mapper`). When the Editor runs, it must use the reviewed Humanizer snapshot and Simpro policy against the same immutable article snapshot. Agents return advisory findings only; `/optimize` applies one consolidated edit batch and remains the sole copy owner for the repair.

## Link policy

When optimizing links, keep standard blogs at 3 to 5 internal links and never more than 7. Count the required cluster or down-funnel industry, solution, or feature link toward that total unless a valid brief-bound override narrows the supporting-link count. URL fragments and `mailto:` or `tel:` links do not count. Two distinct authoritative non-owned external sources pass; do not recommend a third source only to meet a quota, while claim-fit evidence exceptions remain uncapped.

A valid `link_policy_override` in the bound editorial plan may replace the 3 to 5 target for brief-selected internal body links but can never exceed the hard maximum of 7. It must bind the brief path, SHA-256, exact source sentence, exact count, and `pre_faq_body` scope. For single-trade Simpro posts, the matching industry page remains additive unless the bound brief explicitly prohibits it. External proof and legal citations remain separate and uncapped.

Machine-map every proof-sensitive claim to exactly one policy-engine mode: `inline_required`, `section_source_allowed`, `sidecar_only`, or `proof_not_required`. `inline_required` covers legal, regulatory, licensing, compliance, safety, fees, deadlines, pricing, status, material numeric, causal, comparative, benchmark, quote, customer, review, Fred, and fact-driven FAQ claims; use a natural link in the same paragraph or row and in the FAQ's first visible paragraph. Lower-risk body definitions, background, and process may use `section_source_allowed`; approved low-risk product or brand language and clearly framed low-risk editorial recommendations may use `sidecar_only`. Only the policy engine may assign `proof_not_required` to navigation, explicit opinion, or advice with no externally verifiable factual claim. Unknown or ambiguous high-risk claims fail closed to `inline_required`.

Machine reviewers must preserve required links and flag duplicate support, repeated destinations, and quota-only sources. They return advisory findings only; `/publish-readiness` is the sole verdict and no human approval step applies.

## Native edit receipt

Open the optimization receipt before the consolidated edit batch and close it after `/optimize` saves the Markdown. Bind the predecessor receipt hash from the current chain.

```powershell
python data_sources/modules/blog_assembly_stage_receipt.py begin-native-edit --article "[article]" --state "research/stage-receipts/[topic-slug]/optimization-state.json" --run-id "[run-id]" --stage optimization --tool-name "optimize-command" --tool-version "1" --previous-receipt-hash "[previous-receipt-hash]"
# /optimize applies and saves one native edit batch here.
python data_sources/modules/blog_assembly_stage_receipt.py finish-native-edit --article "[article]" --state "research/stage-receipts/[topic-slug]/optimization-state.json" --receipt "research/stage-receipts/[topic-slug]/optimization.json" --evidence "humanizer_policy=config/humanizer-policy.json" --evidence "humanizer_upstream=vendor/blader-humanizer/UPSTREAM.json"
```

## Scorecard requirements

Optimization is not ready until `/publish-readiness` reports:

- Content quality: 85/100 or higher.
- SEO quality: 90/100 release floor with zero critical SEO issues; 95/100 honest optimization target when source-safe improvements exist.
- AEO/GEO: 90/100 or higher.
- Every blocking proof, source, URL, public-artifact, identity, context, FAQ, PAA, branch-applicable customer-proof, E-E-A-T strength, branch-applicable Fred authority, named-feature, and vault-language gate passes.

If the article remains below threshold after 2 repair loops, leave the article in place, write a machine-readable blocker under `research/`, and return nonzero with the exact failed checks and attempted fixes.

For detailed policy, use `context/aeo-geo-blog-strategy.md`.
