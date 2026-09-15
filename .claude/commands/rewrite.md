# Rewrite Command

Use `/rewrite [existing article or analysis]` to revise an existing blog while preserving proof boundaries and source traceability.

## Ownership

The command/agent rewrites public Markdown. Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

Python may write governance artifacts only: selector output, context binding evidence, Semrush keyword decision JSON, SERP/PAA artifacts, editorial-plan JSON, BOM JSON, readiness JSON, and publisher transport payloads.

Consume `context/blog-editorial-strategy.md` for editorial execution and the canonical AEO and proof source, `context/aeo-geo-blog-strategy.md`. Author metadata controls public identity, Person schema, and whether first-person author voice is allowed; it provides zero Expertise and zero Experience credit without selected, source-visible evidence that satisfies the corresponding proof boundary. Expertise proof requires source-visible expert evidence alongside product/workflow support.

Consume the frozen `simpro-blog-editorial-plan/v2` produced by `/analyze-existing`. Do not silently alter it. The plan defines outcomes and constraints; `/rewrite` independently chooses the final prose. Return plan-level defects to `/analyze-existing` for a newly hashed plan.

After every article-byte change, regenerate `simpro-blog-plan-fulfillment/v1` with one substantive verbatim visible excerpt per planned contribution, bound to the frozen plan and current article hashes.

## Required workflow

1. Read the existing article and analysis findings.
2. Resolve topic, title, objective, audience, target keyword, target URL, and rewrite path.
3. Classify Context Binding from the final brand metadata and content. Use the Simpro vault connector for Simpro-owned or cross-brand-triggered work. For AroFlo, BigChange, or ClockShark work with no Simpro name or official `simprogroup.com` URL, record the nonconnector reason and omit vault, Fred, and vault-dependent customer-proof selector artifacts. When a separate approved non-vault proof-eligibility contract applies, use `nonvault_customer_proof_selector.py` and supply only `simpro-nonvault-customer-proof-selector-evidence/v1`.
4. Run the live Semrush keyword decision workflow from `context/aeo-geo-blog-strategy.md` unless a current valid `simpro-semrush-keyword-decision/v1` artifact already exists for the same article, plan, market, and assembly date.
5. Reuse pre-picked PAA from a dedicated rewrite brief when present. If no dedicated PAA exists and PAA is required, collect structured AnswerSocrates evidence. Do not invent questions.
6. Update the validation sidecar before changing proof-sensitive copy.
7. Run the vault customer-proof and Fred selectors only when Context Binding requires the connector. For a nonconnector article with a separate approved non-vault proof-eligibility contract, run `nonvault_customer_proof_selector.py`, preserve its hash-bound evidence, and keep review stories, exact quotes, metrics, ratings, and named-person attribution out unless a later contract explicitly approves them. For commercial-investigation rewrites, add `## E-E-A-T Strength Decision` when no selected proof, review, Fred, author, or SME signal exists.
8. Require `/analyze-existing` preservation decisions in the editorial plan as `rewrite_decisions.preserve`, `update`, `add`, and `remove`; preserve original image placeholders, useful sections, internal links, and proof unless the plan explicitly updates or removes them.
9. Resolve `audience_language_research` in the editorial plan. Use genuine Reddit, YouTube, or trade-community language only when it materially improves reader comprehension; default regulatory and licensing rewrites to `not_applicable` unless the brief asks for it.
10. If the frozen plan or validation sidecar records `Hindsight Strategy Selection` with `Status: internal_strategy_only`, use that Hindsight-informed strategy only to understand the planned reader angle, section emphasis, planned contribution purposes, objections, and commercial framing. Do not quote, cite, disclose, paraphrase, metricize, or convert Hindsight or deal-intelligence data into public claims. If the Hindsight-informed angle is missing or wrong, route the plan defect back to `/analyze-existing` for a new plan hash.
11. Validate the already frozen editorial plan, then run the six machine reviewers against that exact plan. Route plan-level changes to `/analyze-existing`; do not mutate the plan inside `/rewrite`.
12. Run the Reader-Facing Copy Firewall before rewriting. Convert brief instructions, source-fit notes, claim-selection logic, feature-omission rationale, command results, schema notes, and readiness status into article-ready guidance or sidecar/frontmatter/BOM evidence. Public body copy must read only as a blog for the ICP and must not explain how or why the article was assembled, including phrases such as "this article uses," "the brief asks," "right editorial lane," or "does not name a specific feature."
13. Write the rewrite Markdown section by section in plan order through `/rewrite`.
14. Freeze the article and fulfillment bytes, rerun the Reader-Facing Copy Firewall, and run the same six reviewers against that exact article and fulfillment evidence: `content-analyzer`, `editor`, `seo-optimizer`, `meta-creator`, `internal-linker`, and `keyword-mapper`. Content Analyzer and Editor assess whether every excerpt accomplishes its planned purpose. Save `simpro-blog-machine-review/v1` article-review JSON. Any `editorial_process_leakage` finding is a public-copy blocker owned by `/rewrite`. Apply one consolidated edit batch through `/rewrite`, regenerate fulfillment, then rerun all six reviewers after every article-byte change, including scrub, lint, or recovery-loop edits.
15. Run `/scrub [article]` as read-only diagnostics. Apply any required edits through `/rewrite`, rerun `/scrub`, and mint the scrub stage receipt only after diagnostics are clean.
16. Run the atomic release wrapper far enough to produce an initial `/publish-readiness` scorecard or an exact non-scoring blocker. Do not skip this step, because `/optimize` needs the failed gates, `scorecard`, `aeo_geo.checks`, and `priority_fixes`.
17. Run `/optimize [article]` for every rewrite after the initial scorecard or blocker report. If no source-safe edits are needed, record a no-op optimizer output with the inspected scores, priority fixes, and reason. If `/optimize` changes article bytes, rerun `/scrub`, Context Binding, and the full six-agent article review.
18. Run the atomic release wrapper again with the sidecar, machine reviews, evidence artifacts, stage receipts, optimizer output when present, post-optimization scrub receipt when applicable, and context artifacts when connector-bound. Stop unless every wrapper phase reaches final `/publish-readiness` and reports separate Content, SEO, and AEO/GEO scores.

## Native edit receipt

Open the receipt before native rewriting, then close it after `/rewrite` has saved the Markdown. Python observes hashes only.

```powershell
python data_sources/modules/blog_assembly_stage_receipt.py begin-native-edit --article "rewrites/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --run-id "[run-id]" --stage draft --tool-name "rewrite-command" --tool-version "1" --input "analysis=research/analysis-[topic-slug]-[YYYY-MM-DD].md"
# /rewrite creates and saves the public Markdown here.
python data_sources/modules/blog_assembly_stage_receipt.py finish-native-edit --article "rewrites/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --receipt "research/stage-receipts/[topic-slug]/draft.json" --evidence "keyword_decision=research/semrush-keyword-decision-[topic-slug]-[YYYY-MM-DD].json" --evidence "serp_evidence=research/serp-evidence-[topic-slug]-[YYYY-MM-DD].json" --evidence "humanizer_policy=config/humanizer-policy.json" --evidence "humanizer_upstream=vendor/blader-humanizer/UPSTREAM.json"
```

## Scorecard requirements

`/publish-readiness` must report separate gates for:

- Content quality: 85/100 or higher.
- SEO quality: 90/100 release floor with zero critical SEO issues; 95/100 honest optimization target when source-safe improvements exist.
- AEO/GEO: 90/100 or higher.

If any scorecard gate fails, repair the root copy, proof, sidecar, or scorer issue and rerun `/publish-readiness`. After 2 unsuccessful repair loops, leave the article in place, write a machine-readable blocker under `research/`, and return nonzero.

If scoring does not run because an upstream gate blocks readiness, report `scorecard: unavailable` with the exact blocking gate. Missing scores are a workflow blocker unless a pre-scoring gate stopped `/publish-readiness`.

## Link policy

Standard blog rewrites use 3 to 5 internal links and never more than 7. Existing useful links can remain, and the required cluster or down-funnel industry, solution, or feature link counts toward that total unless a valid brief-bound override narrows the supporting-link count. URL fragments and `mailto:` or `tel:` links do not count. Two distinct authoritative non-owned external sources pass; do not add a third source only to meet a quota, while claim-fit evidence exceptions remain uncapped.

A valid `link_policy_override` in `simpro-blog-editorial-plan/v2` may replace the 3 to 5 target for brief-selected internal body links but can never exceed the hard maximum of 7. It must bind the brief path, SHA-256, exact source sentence, exact count, and `pre_faq_body` scope. For single-trade Simpro posts, the matching industry page remains additive unless the bound brief explicitly prohibits it. External proof and legal citations remain separate and uncapped.

Machine-map every proof-sensitive claim to exactly one policy-engine mode: `inline_required`, `section_source_allowed`, `sidecar_only`, or `proof_not_required`. `inline_required` covers legal, regulatory, licensing, compliance, safety, fees, deadlines, pricing, status, material numeric, causal, comparative, benchmark, quote, customer, review, Fred, and fact-driven FAQ claims; use a natural link in the same paragraph or row and in the FAQ's first visible paragraph. Lower-risk body definitions, background, and process may use `section_source_allowed`; approved low-risk product or brand language and clearly framed low-risk editorial recommendations may use `sidecar_only`. Only the policy engine may assign `proof_not_required` to navigation, explicit opinion, or advice with no externally verifiable factual claim. Unknown or ambiguous high-risk claims fail closed to `inline_required`.

All six machine reviewers must preserve existing required links unless a replacement retains the exact evidence mapping, and must flag duplicate support, repeated destinations, and quota-only sources. They return advisory findings only; `/publish-readiness` is the sole verdict and no human approval step applies.

For detailed proof, E-E-A-T strength, FAQ, PAA, review story, named feature, schema, and vault language rules, use `context/aeo-geo-blog-strategy.md`.
