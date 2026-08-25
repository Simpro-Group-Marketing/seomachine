# Repurpose Command

Prepare a manual, evidence-bound distribution handoff from a sealed article. This command does not post to any external platform and does not predict distribution, backlink, platform-algorithm, or AI-citation outcomes.

## Usage

`/repurpose [article] --final-readiness [attestation] [--canonical-url URL]`

Example:

`/repurpose published/field-service-guide.md --final-readiness research/final-readiness-field-service-guide-2026-08-21.json --canonical-url https://example.com/field-service-guide`

`[article]` is the exact Markdown artifact to repurpose. `[attestation]` is its existing final-readiness validation artifact. `--canonical-url` is optional; do not infer or invent it.

## Source-sealing requirement

Before any derivative generation, read the complete article and load the existing final-readiness validation through `data_sources.modules.publish_readiness.validate_passed_readiness_result`. Require phase `final` and `passed: true`. Require the attestation's `input_hashes.article.sha256` to match the supplied article's current exact-byte hash, and require its recorded `file` path to match the supplied article path. Calculate the current article SHA-256 hash from the supplied article bytes; do not normalize, reformat, or substitute the article before matching.

If the validation is missing, does not attest a passing final-readiness result, has no article hash, or its hash differs from the current article, set the state to `blocked`. Do not generate derivatives, draft public-platform copy, or suggest posting actions. Report the failed check and the corrective action: rerun final readiness against the current article before returning to `/repurpose`.

## Handoff states

- `blocked`: source-sealing validation failed. Output only the blocker and corrective action.
- `sealed_preview`: final-readiness validation and exact article hash match succeeded. Inspect the sealed article, identify eligible distribution opportunities, and select channels rather than force them. A clearly labeled pre-publication derivative preview is permitted for selected channels, but it is not a publish-ready handoff or posting instruction. Canonical link: absent/unverified. Every derivative must be clearly labeled non-postable and remain manual-review-only.
- `handoff_prepared`: the selected channels each have a complete manual review packet, a live check verifies the canonical identity, and every selected channel has verified owner, account identity, and disclosure. Derivative candidates may be prepared only from the sealed article and only for the selected channels. They remain manual-review artifacts, not posted content.

A supplied URL alone is not verification. Record the canonical identity live check and every owner, account identity, and disclosure check with check/time/evidence in the channel packet. If any required check cannot be verified, fall back to `sealed_preview`.

## Proof boundary

Derivatives may carry only claims already present and supported in the sealed article. Preserve the original claim meaning and cite the sealed article passage that permits each claim. Public proof links may be carried only when they are already present in the sealed article and support the same claim. If an adapted angle needs a new fact, proof link, customer statement, metric, quote, comparison, product capability, review assertion, or other proof-sensitive claim, omit it and record the gap for human review.

No new proof-sensitive claims may be added. Do not add invented personal experience, affiliation, authorship, customer perspective, outcomes, product use, or platform participation. A useful explanation of the article is permitted only when it does not change or expand its supported claims.

## Select distribution channels

Evaluate possible channels against the sealed article and available, specific opportunities. Select channels rather than force them. A channel is eligible only when its audience and a concrete opportunity fit the article without creating unsupported claims or artificial participation.

For every selected channel, create a packet with all of these fields:

```markdown
### [Channel]

- Audience/opportunity: [specific audience and live, relevant opportunity]
- Adapted angle: [article-supported angle for that audience]
- Permitted source passages: [article heading/section and exact supporting passage]
- Public proof links: [only article-carried, claim-supporting URLs; or none]
- Canonical link: [provided canonical URL after live identity verification; or omitted]
- Owner: [named responsible person or team]
- Account identity: [the account that may post and its relationship to the article]
- Disclosure: [required affiliation/relationship disclosure, or not applicable with reason]
- Human review required: yes
- manual posting: required
```

Do not select a channel when a real opportunity, owner, account identity, truthful disclosure, or human review cannot be specified. Do not force a channel merely because it appears in a context file or was used for another article.

## Reddit and Quora

Reddit and Quora are eligible only with a specific live thread or question that is relevant to the sealed article. The packet must name and link the live thread or question, include a disclosed affiliation, and state why the answer helps that audience. An optional directly useful link to the canonical article is never required; include it only when it materially helps the reader. Manual posting is required.

Never fabricate a personal story, individual experience, independent recommendation, or community participation. If an appropriate live thread or question does not exist, do not prepare Reddit or Quora content.

## Prohibited behavior

- Automated posting is prohibited.
- Fixed derivative counts are prohibited.
- Fixed word quotas are prohibited.
- Backlink promises are prohibited.
- platform-algorithm claims are prohibited.
- AI-citation predictions are prohibited.
- Do not claim a platform will reward, penalize, rank, cite, distribute, or link to the derivative.
- Do not promise links, traffic, citations, reach, engagement, or other outcomes.

## Output

For `sealed_preview` and `handoff_prepared`, save the selected and rejected channel decisions plus any clearly labeled derivative candidates to:

`repurposed/[slug]-repurposed-[YYYY-MM-DD].md`

The repurposed handoff is advisory distribution work, not an assembly BOM artifact, not a `/publish-readiness` input or gate, and not a release requirement.

The output must begin with the article path, final-readiness attestation path, attested article hash, current article hash, state, canonical URL status, and a statement that no external posting occurred. Include selected-channel packets, rejected channels with reasons, and a final manual-review checklist. In `sealed_preview`, every derivative remains clearly labeled non-postable. Do not create an output file for `blocked`.

## Related workflow

`/research-ai-citations` can identify research questions and observed source patterns, but it does not authorize a channel, add proof, or predict citation outcomes. Use only a sealed-article handoff through this command for derivative preparation.
