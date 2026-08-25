# Research Performance Command

Analyze content performance. All-content and observed target-specific runs produce a prioritized optimization or rewrite recommendation; blocked target-specific runs produce only an evidence-and-blocker report.

## Usage

```text
/research-performance
/research-performance [blog URL or path]
```

Examples:

```text
/research-performance
/research-performance https://www.simprogroup.com/blog/hvac-ppc
/research-performance /blog/hvac-ppc
```

## Command Contract

This is a slash-command workflow. The agent executing `/research-performance` is responsible for calling the required repo scripts, MCP tools, and data-source modules internally. Do not ask the user to run Python scripts by hand.

Use the all-content mode when no URL is provided. Use target-specific mode when a URL or blog path is provided.

## All-Content Mode

When the user runs `/research-performance` with no argument:

1. Pull or consult the current GA4/GSC-backed performance queue.
2. Categorize eligible blog content into priority groups.
3. Identify the strongest next rewrite, optimization, or internal-linking opportunity.
4. Save the output to `research/performance-review-[YYYY-MM-DD].md` or the closest existing performance artifact pattern.
5. Return the top priorities and the recommended next slash command.

All-content mode does not create a target receipt.

## Target-Specific Mode

When the user runs `/research-performance [blog URL or path]`:

1. Resolve the canonical URL and normalized path, business objective, conversion definition or explicit `conversion_not_applicable_reason`, success measure, owner, review date, primary period, and the equal-length immediately preceding comparison period. Supplemental windows are optional.
2. Collect source lanes separately: GSC is search-performance truth; GA4 is behavior/conversion evidence; third-party tools are optional opportunity/SERP context and never satisfy first-party observation. Record each source `property_id`, exact `filters`, UTC `retrieved_at` time, `limitations`, and exact source-specific `blockers`.
3. Bind the target as `release_artifact` when the local release article and current final BOM are available; the canonical path must end with the sealed editorial-plan URL slug bound by that BOM. Use `live_url` only for a legacy page after canonical identity is verified with `verified_at` and `verification_method: live_canonical_observation`; its `limitations` must state that no local release artifact was available. Never invent a local artifact.
4. Inspect the live page for title, H1, structure, intent fit, and obvious regional or proof issues, then compare the evidence with any local performance shortlist or existing research artifact.
5. Write and finalize the Markdown performance report first at `research/performance-review-[slug]-[YYYY-MM-DD].md`.
6. Build the matched receipt at `research/performance-receipt-[slug]-[YYYY-MM-DD].json`. Its metadata uses the strict receipt terms `status`, `collected_at`, `article_binding`, `measurement_windows`, `sources`, `measurement_scope`, `raw_data_artifacts`, and `optimization_recommendation`; the generated receipt records `verification_scope: recorded_observation_metadata`.
7. Hash the finalized report through the receipt builder, then strictly validate the result:

   ```powershell
   python data_sources/modules/post_publish_measurement_receipt.py build --metadata "[temporary measurement metadata]" --performance-report "research/performance-review-[slug]-[YYYY-MM-DD].md" [--article "[release article]" --final-bom "[final BOM]"] --output "research/performance-receipt-[slug]-[YYYY-MM-DD].json"
   python data_sources/modules/post_publish_measurement_receipt.py check "research/performance-receipt-[slug]-[YYYY-MM-DD].json" [--article "[release article]" --final-bom "[final BOM]"] --performance-report "research/performance-review-[slug]-[YYYY-MM-DD].md" --fail-on error
   ```

   The Markdown report and JSON receipt are the only durable target-specific workflow outputs, not public outputs; implementation metadata may be in memory or temporary storage. The validator checks the report's exact H2 contract against receipt status, requires that it reproduces every blocked source identity, property, blocker code, and blocker detail verbatim, and rejects metrics from a blocked first-party lane. Only rendered Markdown can satisfy headings, blocker evidence, or observed metrics; fenced examples and HTML comments do not count. Observed metric labels require non-empty observed values, numeric except for a non-empty query value. Blocked reports use only the documented data-only status and source rows, with no free-prose action field.
8. Emit `observed` only with at least one observed first-party lane. If first-party observation cannot be established, emit `blocked` and preserve exact per-lane blockers. A blocked target report is limited to `Scope and evidence`, `Data-quality and causality limits`, and exact per-source blockers and limitations. A blocked target report contains no opportunity queue, diagnosis, recommendation of any kind, verdict, recommended action, owning-command or other workflow handoff, or success claim. An `observed` result may return an evidence-bound advisory handoff only after this check.

The target report and receipt are advisory internal evidence. They are not public-claim proof, not Customer Proof Pack or validation-sidecar proof, not an assembly BOM, not a `/publish-readiness` input or gate, and not a release requirement. `verification_scope: recorded_observation_metadata` verifies the recorded metadata and current artifact bindings only; it does not establish external analytics truth or causal correlation.

## Required Evidence

Every target receipt must record the GSC and GA4 source/property, filters, status, retrieval time, limitations, and blockers, along with the target URL, normalized page path, and date ranges. Observed reports reproduce the applicable dataset metadata and metrics. Blocked reports reproduce only exact source-specific blocker and limitation evidence under the restricted contract below; the paired receipt retains the remaining collection metadata.

Observed target reports must include only evidence from lanes whose status is `observed`:

- For an observed GSC lane, include clicks, impressions, CTR, average position, and relevant queries.
- For an observed GA4 lane, include sessions, views, active users, engagement, bounce rate, average session duration, and key events.
- For a blocked lane, include its exact source-specific blockers and omit that lane's metrics. Do not fabricate unavailable lane evidence.
- Diagnose the primary weakness and recommend a next slash command only from the observed lanes and stated limitations.

Blocked reports must instead include exact per-source blockers and limitations. A blocked target report is limited to `Scope and evidence`, `Data-quality and causality limits`, and exact per-source blockers and limitations. A blocked target report contains no opportunity queue, diagnosis, recommendation of any kind, verdict, recommended action, owning-command or other workflow handoff, or success claim.

## Output

For a target-specific run, save:

```text
research/performance-review-[slug]-[YYYY-MM-DD].md
research/performance-receipt-[slug]-[YYYY-MM-DD].json
```

For an all-content run, save:

```text
research/performance-review-[YYYY-MM-DD].md
```

The paired target-specific filenames must use the same `[slug]` and `[YYYY-MM-DD]`. Do not substitute another output convention.

## Integration

After an `observed` target-specific `/research-performance` result:

- Use `/rewrite [URL]` when the article needs a substantive rewrite.
- Use `/optimize [file]` when a rewritten or drafted artifact already exists.
- Use `/analyze-existing [URL]` when more structural or SERP-specific analysis is needed before deciding.

Do not expose internal scripts as user-required steps. If script execution is needed, run it as part of this command workflow and report the saved artifact.
