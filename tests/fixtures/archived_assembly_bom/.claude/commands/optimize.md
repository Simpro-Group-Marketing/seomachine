# Optimize Command

Consume `context/blog-editorial-strategy.md` for editorial decisions and `context/aeo-geo-blog-strategy.md` for AEO and proof governance. `/optimize` may edit public prose through the native command, but it must stay inside the production BOM. Route a BOM defect, such as a missing fact, source, section, or proof item, back to `/research` (or the rewrite BOM build step) to fix the spec and rebuild.

Use `/optimize [article file]` after a release record exists. Optimization is a findings and targeted edit loop, not a separate finalization path: it revises from the latest release record and then runs the release again.

## Ownership

The command/agent applies public-copy edits. Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

Python may run the release and write governance artifacts such as selector evidence, the production BOM, the release record, and publisher transport payloads.

## Required workflow

1. Read the latest release record for the article in `research/releases/[slug]-[date]-[run8]-[n]/release-record.json`. If none exists, run `/publish-readiness [article]` first, unless the user explicitly requested a read-only audit. If the release stopped before scoring, report `scores: unavailable` with the exact stop reason and do not claim optimization scores.
2. Read the blocking findings (`severity: block`), the score gates in `scores.gates`, the AEO/GEO `failed_checks` and `failed_rules`, and `scores.priority_fixes`.
3. Classify each issue:
   - public-copy gap: fix the prose;
   - BOM gap (a needed fact, proof item, PAA question, section, or link is missing or refused): route it to `/research`;
   - scorer or parser false negative: when the article visibly satisfies the rule, add a regression test and fix the scorer instead of distorting accurate copy.
4. Run the Reader-Facing Copy Firewall as part of optimization diagnosis. If public body copy contains brief rationale, source-fit notes, feature-omission reasoning, command status, or `editorial_process_leakage`, classify it as a public-copy gap and repair it; never end optimization while this blocker remains.
5. Preserve the Hindsight-informed reader angle, section emphasis, section purposes, objections, and commercial framing recorded in the research brief. Do not quote, cite, disclose, paraphrase, metricize, or convert Hindsight or deal-intelligence data into public claims. If optimization needs a new Hindsight-derived angle, route the plan defect back to `/research`.
6. Apply every blocking fix, then only the highest-impact 3 to 5 priority fixes. Fix the AI copy linter warnings (`check: lint`) here too: they do not block the release, but they are copy defects that `/optimize` owns. Do not invent PAA questions, proof, metrics, rankings, customer stories, quotes, or unsupported product claims to gain points; every new fact must already be in the BOM.
7. When the edits are larger than a few sentences, dispatch the advisory reviewers the issues call for as parallel subagents against the edited snapshot and the BOM path: `editor`, `seo-optimizer` (with the `meta-creator`, `internal-linker`, and `keyword-mapper` checklists), `content-analyzer`, and the fact-check reviewer. Apply their findings in one consolidated edit batch.
8. Run `/scrub [article]` as read-only diagnostics and make any required copy edits.
9. Run `/publish-readiness [article]` again, which runs `python -m data_sources.modules.production.release [article]`.

When the release passed and no source-safe priority fix exists, make no edits and report the passing record with the reason. A passing record stays valid only while the article and BOM bytes are unchanged.

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
- Keyword coverage, placement, or intent findings: `keyword-mapper`.
- A primary keyword missing from the title, H1, or first 100 words is a coverage block: fix the copy. A wrong primary keyword is a BOM defect: rerun the Semrush lane in `/research`.

Agents return advisory findings only; `/optimize` applies one consolidated edit batch and remains the sole copy owner for the repair. When the Editor runs, it uses the reviewed Humanizer snapshot and Simpro policy.

## Link policy

Keep standard blogs at 3 to 5 internal links and never more than 7 below 3,000 visible words; the commercial pillar link counts toward that total. URL fragments and `mailto:` or `tel:` links do not count. Two distinct authoritative non-owned external sources pass; do not recommend a third source only to meet a quota, while claim-fit evidence exceptions remain uncapped. Every cited source must be a BOM fact or proof URL; a claim that cites a source outside the BOM blocks the release. Keep the commercial pillar link with its exact planned anchor.

## Score requirements

Optimization is not done until the latest release record passed for the current article bytes:

- Content quality: 85/100 or higher.
- SEO quality: 90/100 release floor with zero critical SEO issues; 95/100 honest optimization target when source-safe improvements exist.
- AEO/GEO: 90/100 or higher.
- Zero blocking truth or coverage findings.

If the article remains blocked after 2 repair loops, leave the article in place and return the exact blocking findings and attempted fixes from the latest release record.

For detailed policy, use `context/aeo-geo-blog-strategy.md`.
