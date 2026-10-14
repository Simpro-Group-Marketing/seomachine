# Blog Editorial Strategy

**Purpose:** Canonical non-AEO editorial contract for reader focus, continuity, story safety, headline integrity, and CTA pressure across supported blog brands.
**Use when:** Researching, planning, writing, rewriting, analyzing, editing, or optimizing blog content.
**Owns:** Reader Contract fields, proof-safe story rules, specificity hierarchy, stakes and relevance, promise integrity, continuity, and intent-sensitive CTA profiles.
**Does not own:** AEO/GEO requirements, claims approval, customer proof, product language, competitive assertions, brand authority, or publish readiness.
**Source boundary:** Editorial operating guidance synthesized from the approved 2026-08-05 review; brand and proof sources remain authoritative for public claims and voice permissions.
**Refresh cadence:** Review when shared blog workflows or editorial quality expectations change.
**Reference detail:** Implementation plan: `docs/superpowers/plans/2026-08-05-blog-editorial-quality-upgrades.md`.

---

This is the canonical non-AEO editorial contract for Simpro, ClockShark, BigChange, AroFlo, and other blog brands supported by this repository. It governs reader focus, article coherence, story safety, editorial stakes, headline integrity, and CTA pressure. It does not replace brand-specific voice, proof, product, competitor, SEO, or AEO sources.

## Editorial Plan Ownership

The production BOM (`simpro-production-bom/v1`) is the editorial plan of record: its sections (heading, purpose, `must` or `should`), facts, approved proof, PAA questions, links, and CTA define what the article must deliver. `/research` builds it for new articles, and for rewrites it is built from the `/analyze-existing` findings. The research brief carries the Reader Contract, section throughlines, original contribution, search strategy, commercial decision, and lifecycle. Both are fixed before public prose is written. Earlier `simpro-blog-editorial-plan/v2` artifacts remain readable history only.

`/write`, `/rewrite`, and `/optimize` are the only prose writers. They consume the BOM and brief and choose the language independently. A plan-level defect (a missing or wrong section, fact, proof item, PAA question, or link) returns to `/research`, which fixes the BOM spec and rebuilds the BOM; a prose-level defect stays with the active native writing command.

No fulfillment artifact is recorded after article edits. The release's coverage check confirms that every `must` section, fact, proof item, PAA question, and link is present, and the Content Analyzer and Editor reviewers judge whether each section accomplishes its planned purpose. Planning notes never substitute for public claim proof: facts, proof, and citations reach the article only through the BOM.

The plan should specify what must become true for the reader, not sentence-by-sentence wording. Preserve creative latitude by planning contributions, purposes, evidence sources, payoffs, and transitions while leaving examples, rhythm, explanation, and final expression to the writer.

For connector-bound Simpro work, approved Hindsight internal-strategy evidence may shape the private reader angle when it is relevant to the reader task. Use it to refine the Reader Contract's distinctive angle, section emphasis, BOM section purposes, the planned contribution, search framing, commercial framing, and what the article should make clear. Bound evidence must keep `public_claim_use: prohibited` and `claim_support_allowed: false`. Do not turn Hindsight or deal-intelligence data into public proof, visible claims, metrics, rankings, comparisons, quotes, citations, or source links. If the writer finds the Hindsight-informed angle missing or wrong, route the defect to `/research` for a corrected brief and BOM instead of creating a new angle during prose writing.

## Reader Contract

Resolve this internal planning block before recommending an outline or drafting public copy. Keep it in the research brief or the `/analyze-existing` analysis. Do not place it in public article frontmatter or a proof-validation sidecar.

- Brand:
- Author mode: named_author | brand_editorial
- Primary reader:
- Sophistication:
- Entry situation or problem:
- Existing belief:
- Desired decision or action:
- Distinctive angle:
- Promised payoff:
- Intentionally out of scope:
- Funnel stage: tofu | mofu | bofu | thought_leadership

When a brief names more than one funnel stage, use the earliest stage unless the brief explicitly states a conversion objective. Use this order: `tofu`, `mofu`, `bofu`. Use `thought_leadership` only when the brief explicitly identifies that format.

## Story and Scene Safety

Stories and scenes are optional. Use one only when it materially improves the reader's understanding of the article's subject or decision.

Allowed story sources are:

- approved customer proof selected through the applicable brand proof workflow;
- source-supported author experience whose first-hand boundary is visible;
- unnamed explanatory workflows that clarify a process without acting as customer or E-E-A-T proof.

Unnamed explanatory workflows cannot contain invented people, business names, dates, numbers, quotes, metrics, or outcomes. Do not turn an illustrative workflow into a testimonial or imply that it happened to a real customer.

## Specificity Hierarchy

Use this Specificity hierarchy before reaching for names or numbers:

Prefer specificity in this order:

1. A concrete workflow, decision, constraint, or tradeoff.
2. A source-supported operational detail or example.
3. A source-visible name, date, number, quote, metric, or outcome that passes the applicable proof controls.

Never create precision to make copy sound credible. When proof is unavailable, make the workflow clearer or remove the claim.

## Stakes and Relevance

Show why the subject matters through operational consequences: identify the affected role, the work that becomes harder, and the downstream decision or handoff at risk. Do not manufacture fear, urgency, scarcity, loss, or emotional intensity. Emotion may appear when it is faithful to approved customer proof or source-supported author experience.

## Headline Promise Integrity

Every blog headline must pass four checks:

- **Reader specificity**: The intended reader or situation is identifiable.
- **Payoff clarity**: The value of reading is apparent.
- **Distinctiveness**: The angle is substantive rather than a cosmetic power word.
- **Promise Integrity**: The article fully delivers the promise with available evidence and does not depend on an unsupported number, timeframe, superlative, urgency cue, or transformation claim.

## Section Throughline

Every planned body section must record:

- Reader question:
- Section answer or payoff:
- Bridge from previous section:
- Bridge to next section:

After section-by-section assembly and before scrub, run a continuity pass:

- Every section advances the headline promise.
- Sections do not restart the article or repeat prior setup.
- Transitions express the actual logical relationship between sections.
- Introduction tensions, questions, and open loops are resolved.
- The conclusion completes the introduction and supplies a suitable next action.
- A removable section is removed unless it provides a documented payoff.

## CTA Profiles

| Funnel stage | Editorial requirement |
|---|---|
| `tofu` | Include at least one reader-value next step. Do not impose a commercial or early-placement quota. |
| `mofu` | Include one educational next step and one contextual product-relevant CTA, distributed across the article. |
| `bofu` | Include two or three contextual commercial CTAs, with at least one within the first 500 words and one near the conclusion. |
| `thought_leadership` | Include at least one relevant next step. It may invite reflection, discussion, evidence review, or related reading. |

The next step must match the article objective. Do not treat every reader action as a demo or trial request.

## Reviewed Humanizer Governance

The Editor reviews `/write`, `/rewrite`, and `/optimize` snapshots against the pinned Humanizer snapshot recorded in `vendor/blader-humanizer/UPSTREAM.json`, the local decisions in `config/humanizer-policy.json`, and current vault voice context. Humanizer is style advice only. It never edits public copy directly, does not approve claims, and has no runtime network access. Only policy entries explicitly marked for deterministic enforcement may enter the existing AI-copy linter. `/publish-readiness` remains the sole release owner.

Validate the vendored snapshot offline with `python tools/humanizer_upstream.py verify`. Use `check-upstream`, `stage`, and `adopt` for reviewed upgrades. The weekly workflow may open a draft vendor-only PR, but it never auto-merges or changes the local policy. A maintainer must classify upstream pattern changes, update the local policy, and update `reviewed_upstream_commit` before CI can pass. Never modify `config/humanizer-policy.json` automatically from upstream content.

## Brand and Proof Boundaries

Named-author voice remains available only when the applicable brand source permits it. For Simpro, follow the active Obsidian vault voice routes. For other brands, follow their declared brand context and proof authority. Brand-specific rules always control terminology, public claims, customer proof, product language, competitor treatment, and author permissions.

This editorial contract does not approve claims, proof, product language, or competitive assertions. It does not change AEO direct answers, Key Takeaways, early artifacts, PAA/FAQ provenance, FAQ evidence, schema, source routing, proof selectors, Fred authority evaluation, or AEO scoring thresholds.
