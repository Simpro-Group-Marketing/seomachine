# Write Command

Use `/write [topic or research brief]` to draft a blog from an approved topic, brief, or research package.

## Ownership

The command/agent writes the public Markdown. Python must not draft, rewrite, or patch public blog Markdown in `drafts/`, `rewrites/`, or `published/`.

Python may write governance artifacts only: selector output, context binding evidence, Semrush keyword decision JSON, SERP/PAA artifacts, editorial-plan JSON, BOM JSON, readiness JSON, and publisher transport payloads.

## Required workflow

1. Read the user request and any supplied brief.
2. Resolve topic, title, objective, audience, region, target keyword, target URL, and whether the article is new or a rewrite.
3. Classify Context Binding from the final brand metadata and content. Use the Simpro vault connector for Simpro-owned or cross-brand-triggered work. For AroFlo, BigChange, or ClockShark work with no Simpro name or official `simprogroup.com` URL, record the nonconnector reason and omit vault, Fred, and vault-dependent customer-proof selector artifacts. When a separate approved non-vault proof-eligibility contract applies, use `nonvault_customer_proof_selector.py` and supply only `simpro-nonvault-customer-proof-selector-evidence/v1`.
4. Run the live Semrush keyword decision workflow from `context/aeo-geo-blog-strategy.md` unless a current valid `simpro-semrush-keyword-decision/v1` artifact already exists for the same article, plan, market, and assembly date.
5. Build or update the validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`.
6. Run mandatory selectors when applicable:
   - Customer proof selector before using customer proof.
   - Fred Voccola authority selector for every new or changed Simpro blog.
   - E-E-A-T strength decision for commercial-investigation blogs when no selected proof, review, Fred, author, or SME signal exists.
7. Resolve `audience_language_research` in the editorial plan. Use community language only when it materially improves reader comprehension; default regulatory and licensing topics to `not_applicable` unless the brief asks for it.
8. Validate and freeze the editorial plan, then run the six machine reviewers against that exact plan: Content Analyzer (`content-analyzer`), Editor (`editor`), SEO Optimizer (`seo-optimizer`), Meta Creator (`meta-creator`), Internal Linker (`internal-linker`), and Keyword Mapper (`keyword-mapper`). Save `simpro-blog-machine-review/v1` plan-review JSON. Resolve requested changes and repeat once if needed.
9. Run the Reader-Facing Copy Firewall before drafting. Convert brief instructions, source-fit notes, claim-selection logic, feature-omission rationale, command results, schema notes, and readiness status into article-ready guidance or sidecar/frontmatter/BOM evidence. Public body copy must read only as a blog for the ICP and must not explain how or why the article was assembled, including phrases such as "this article uses," "the brief asks," "right editorial lane," or "does not name a specific feature."
10. Write the draft Markdown section by section in plan order to `drafts/[topic-slug]-[YYYY-MM-DD].md` using the command, not a Python writer.
11. Freeze the article bytes, rerun the Reader-Facing Copy Firewall, and run the same six reviewers against that exact article. Save `simpro-blog-machine-review/v1` article-review JSON. Any `editorial_process_leakage` finding is a public-copy blocker owned by `/write`. Apply one consolidated edit batch through `/write`, then rerun all six reviewers after every article-byte change, including scrub, lint, or recovery-loop edits.
12. Run `/scrub [article]` for diagnostics only. If it reports needed changes, make those edits through `/write`, rerun `/scrub`, and rerun article machine review.
13. Run the atomic release wrapper far enough to produce an initial `/publish-readiness` scorecard or an exact non-scoring blocker. Do not skip this step, because `/optimize` needs the failed gates, `scorecard`, `aeo_geo.checks`, and `priority_fixes`.
14. Run `/optimize [article]` for every new blog after the initial scorecard or blocker report. If no source-safe edits are needed, record a no-op optimizer output with the inspected scores, priority fixes, and reason. If `/optimize` changes article bytes, rerun `/scrub`, Context Binding, and the full six-agent article review.
15. Run the atomic release wrapper again with the sidecar, machine reviews, evidence artifacts, stage receipts, optimizer output when present, post-optimization scrub receipt when applicable, and context artifacts when connector-bound. Do not hand off as ready until final `/publish-readiness` passes and reports separate Content, SEO, and AEO/GEO scores.

## Native edit receipt

Open the draft receipt before native writing, then close it after the command has saved the Markdown. These Python calls hash and attest the edit; they do not create or modify the article.

```powershell
python data_sources/modules/blog_assembly_stage_receipt.py begin-native-edit --article "drafts/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --run-id "[run-id]" --stage draft --tool-name "write-command" --tool-version "1" --input "editorial_plan=research/editorial-plan-[topic-slug]-[YYYY-MM-DD].json"
# /write creates and saves the public Markdown here.
python data_sources/modules/blog_assembly_stage_receipt.py finish-native-edit --article "drafts/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --receipt "research/stage-receipts/[topic-slug]/draft.json" --evidence "keyword_decision=research/semrush-keyword-decision-[topic-slug]-[YYYY-MM-DD].json" --evidence "serp_evidence=research/serp-evidence-[topic-slug]-[YYYY-MM-DD].json" --evidence "humanizer_policy=config/humanizer-policy.json" --evidence "humanizer_upstream=vendor/blader-humanizer/UPSTREAM.json"
```

## Scorecard requirements

`/publish-readiness` is the release owner and must report these independent gates:

- Content quality: 85/100 or higher.
- SEO quality: 90/100 release floor with zero critical SEO issues; 95/100 honest optimization target when source-safe improvements exist.
- AEO/GEO: 90/100 or higher.

Do not treat an overall score as a substitute for the SEO or AEO/GEO gates.

## Link policy

Standard blog posts use 3 to 5 internal links and never more than 7. The required cluster or down-funnel industry, solution, or feature link counts toward that total unless a valid brief-bound override narrows the supporting-link count. URL fragments and `mailto:` or `tel:` links do not count. Two distinct authoritative non-owned external sources pass; do not add a third source only to meet a quota, while claim-fit evidence exceptions remain uncapped.

A valid `link_policy_override` in `simpro-blog-editorial-plan/v1` may replace the 3 to 5 target for brief-selected internal body links but can never exceed the hard maximum of 7. It must bind the brief path, SHA-256, exact source sentence, exact count, and `pre_faq_body` scope. For single-trade Simpro posts, the matching industry page remains additive unless the bound brief explicitly prohibits it. External proof and legal citations remain separate and uncapped.

Machine-map every proof-sensitive claim to exactly one policy-engine mode: `inline_required`, `section_source_allowed`, `sidecar_only`, or `proof_not_required`. `inline_required` covers legal, regulatory, licensing, compliance, safety, fees, deadlines, pricing, status, material numeric, causal, comparative, benchmark, quote, customer, review, Fred, and fact-driven FAQ claims; use a natural link in the same paragraph or row and in the FAQ's first visible paragraph. Lower-risk body definitions, background, and process may use `section_source_allowed`; approved low-risk product or brand language and clearly framed low-risk editorial recommendations may use `sidecar_only`. Only the policy engine may assign `proof_not_required` to navigation, explicit opinion, or advice with no externally verifiable factual claim. Unknown or ambiguous high-risk claims fail closed to `inline_required`.

All six machine reviewers must protect required links and flag duplicate support, repeated destinations, and quota-only sources. They return advisory findings only; `/publish-readiness` is the sole verdict and no human approval step applies.

## Output

Return the draft path, sidecar path, evidence paths, BOM/readiness paths, scorecard, failed gates, and priority fixes. Keep proof infrastructure out of public copy.

If scoring does not run because an upstream gate blocks readiness, report `scorecard: unavailable` with the exact blocking gate. Missing scores are a workflow blocker unless a pre-scoring gate stopped `/publish-readiness`.

For detailed proof, E-E-A-T strength, and AEO/GEO policy, use `context/aeo-geo-blog-strategy.md`.
