# Publish Readiness Command

Run the complete publish-readiness gate stack for a blog draft, rewrite, or published article artifact.

## Usage

```text
/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

Examples:

```text
/publish-readiness rewrites/hvac-ppc-rewrite-2026-06-17.md --proof-sidecar research/validation-hvac-ppc-2026-06-17.md
/publish-readiness published/best-job-quoting-and-invoicing-software-for-field-service-businesses-2026-06-12.md --proof-sidecar research/validation-best-job-quoting-and-invoicing-software-for-field-service-businesses-2026-06-12.md
```

## Command Contract

This is the user-facing publish gate command. The agent executing `/publish-readiness` must run the repo publish-readiness runner internally and report the gate summary, content score, AEO/GEO score, and priority fixes. Do not ask the user to call the Python runner manually.

Use this command before `/optimize`, after `/optimize`, before an Asana intake handoff, and before moving an article into `published/`.

## Required Inputs

- Article artifact path
- Validation sidecar path

The validation sidecar should live at:

```text
research/validation-[topic-slug]-[YYYY-MM-DD].md
```

## Gate Stack

The command runs the complete publish-readiness stack:

1. `public_artifact_guard`
2. `ai_copy_linter`
3. `url_validator`
4. `public_research_link_guard`
5. `metric_proof_pack_guard`
6. `numeric_claim_source_guard`
7. `faq_proof_guard`
8. `paa_provenance_guard`
9. `source_support_guard`
10. `customer_proof_diversity_guard`
11. `review_story_identity_guard`
12. `content_scorer` with URL and source-support validation

403 replacement rule: If a DOL, Capterra, G2, Trustpilot, Google Play, or other public research/source URL returns 401, 403, or `manual_review`, do not remove the citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. Source Map notes must document both the rejected 403 URL and the replacement URL. The `public_research_link_guard` blocks sidecar-only handling of public research, compliance, legal, regulatory, or statistical proof and requires visible resolved non-owned public research links in the relevant article section or FAQ answer. Full policy lives in `context/aeo-geo-blog-strategy.md`.

## Output

Return:

- Overall pass/fail
- One row per gate
- Error and warning counts
- Content score
- AEO/GEO score
- Priority fixes
- Whether the artifact is ready for `/optimize`, handoff, or `published/`

If the command fails, fix the highest-severity gate first and rerun `/publish-readiness`.

AI copy lint failures include copy avoid-rule errors. The Simpro web-copy linter blocks modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences before publish readiness can pass.
