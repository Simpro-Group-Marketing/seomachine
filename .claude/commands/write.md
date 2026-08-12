# Write Command

## Blog Assembly Seal (MANDATORY)

Create the strict frontmatter scaffold before drafting. Record and close the real draft mutation, then produce chained scrub and Context Binding receipts:

```powershell
python data_sources/modules/blog_assembly_mutation_recorder.py start --article "drafts/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --run-id "[run-id]" --stage draft --tool-name "write-command" --tool-version "1" --input "editorial_plan=research/editorial-plan-[topic-slug]-[YYYY-MM-DD].json"
# Write and save the draft here.
python data_sources/modules/blog_assembly_mutation_recorder.py finish --article "drafts/[topic-slug]-[YYYY-MM-DD].md" --state "research/stage-receipts/[topic-slug]/draft-state.json" --receipt "research/stage-receipts/[topic-slug]/draft.json" --evidence "serp_evidence=research/serp-evidence-[topic-slug]-[YYYY-MM-DD].json"
python data_sources/modules/content_scrubber.py "drafts/[topic-slug]-[YYYY-MM-DD].md" --stage scrub --run-id "[run-id]" --previous-receipt "research/stage-receipts/[topic-slug]/draft.json" --stage-receipt-output "research/stage-receipts/[topic-slug]/scrub.json"
python data_sources/modules/context_binding_generator.py "drafts/[topic-slug]-[YYYY-MM-DD].md" --proof-sidecar "research/validation-[topic-slug]-[YYYY-MM-DD].md" --context-request "research/context-request-[topic-slug].json" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --stage context_binding --run-id "[run-id]" --previous-receipt "research/stage-receipts/[topic-slug]/scrub.json" --stage-receipt-output "research/stage-receipts/[topic-slug]/context-binding.json"
```

Non-connector branch: replace that command with `python data_sources/modules/context_binding_generator.py "drafts/[topic-slug]-[YYYY-MM-DD].md" --proof-sidecar "research/validation-[topic-slug]-[YYYY-MM-DD].md" --not-applicable-reason "Final article contains no Simpro brand, URL, or connector-sensitive language." --stage context_binding --run-id "[run-id]" --previous-receipt "research/stage-receipts/[topic-slug]/scrub.json" --stage-receipt-output "research/stage-receipts/[topic-slug]/context-binding.json"`. Omit context request/pack/receipt, selector, and Fred arguments from BOM build and context arguments from readiness. The builder rejects this branch when the final article contains any Simpro signal.

Tool-emitted machine artifacts carry an `execution_attestation`, a keyed local execution-integrity attestation. Require it on every `simpro-blog-stage-receipt/v1`, verified `simpro-serp-evidence/v1`, nested `simpro-answersocrates-run-receipt/v1`, `simpro-source-classification/v1`, and `simpro-source-capture-receipt/v1`. Readiness verifies the attestation and canonical hash; a handwritten or merely rehashed replacement does not qualify. This local control does not provide a remote/provider signature and does not prove that external observations are true, so source metadata, visible evidence, freshness, PAA eligibility, and semantic claim fit still require validation. A rewrite's dedicated pre-picked PAA brief section remains path/hash-bound and takes precedence over AnswerSocrates.

After the article, research, proof, and route-specific receipts are complete, invoke `/publish-readiness`. It is the sole owner of the build -> preflight -> finalize -> final seal recipe, its final-readiness attestation, and its `verification_scope: source_artifact` boundary.

### After Optimization Mutations

All optimizer outputs and manual edits are content mutations. The closed route-specific sequence is `optimization` -> `post_optimization_scrub` -> `post_optimization_context_binding` -> `final_preflight_readiness`. Record the mutation, run the scrubber and Context Binding generator with their post-optimization stages, preserve the immutable prior BOM, then invoke `/publish-readiness` for the complete reseal.

Use this command to create comprehensive, SEO-optimized long-form blog content.

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

When `author_policy.status` is `not_provided`, first-person singular author judgment outside quotes is prohibited.

## Usage
`/write [topic or research brief]`

## What This Command Does
1. Creates complete, well-structured articles sized to the reader intent, evidence, and topic scope
2. Optimizes content for target keywords and SEO best practices
3. Maintains your brand voice and messaging throughout
4. Integrates internal and external links strategically
5. Includes all meta elements for publishing

## Process

### Obsidian Vault Source Rule

For every blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decision, use the Simpro vault connector as the active context source. The only configured content location is the vault root; do not prescribe vault hubs, filenames, or internal directories.

Required connector workflow: run vault health first, describe available roles/topics/entities, search in the task's natural language, read and expand results by `resource_id`, query approved claims only when public proof-sensitive language is needed, then build and validate a context pack.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault connector exposes them as source evidence.

The repo-local context files are downstream mirrors or operational state only. They cannot override the vault connector when the vault is available. If fallback is used because the vault is unavailable, document the explicit vault-unavailable blocker in the validation sidecar.

Required validation sidecar evidence: generated vault context binding for every workflow; `Vault Brand Language Alignment` when product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` for competitor-aware posts; `Named Feature/Add-On Link Check` when named Simpro features/add-ons appear. These sections must cite connector `context_pack_hash`, `receipt_hash`, `resource_id`, `claim_id`, use mode, public URL when required, and relevant revisions. Missing required evidence blocks `/publish-readiness`, `/optimize`, and dev-ready handoff.

### Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: competitor-aware posts must document selected competitors, rejected competitors, connector-discovered competitive-context resources, approved claim IDs where public proof is used, and why the shortlist fits the article objective.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified through the claim registry. Keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked through connector-discovered product and feature resources before link decisions. Document the selected `resource_id` values, link decision, and reason in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from connector-discovered vault guidance first. Use semantic search/read/expand for messaging, positioning, feature, solution, and vertical context. When a named feature/add-on appears, include feature-specific `resource_id` evidence; when solution/industry language is used, include solution or vertical `resource_id` evidence. Document connector evidence, language applied, fallback context use, source-verification boundary, and `Status: aligned` in `Vault Brand Language Alignment`. The `vault_brand_language_guard.py` publish gate runs inside `/publish-readiness`; keep this block in the validation sidecar, not public copy. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

### Pre-Writing Review
- **Research Brief**: Review research brief from `/research` command if available
- **Brand Voice**: Use connector-discovered vault messaging guidance first; @context/brand-voice.md is a fallback mirror only when the vault is unavailable
- **Writing Examples**: Study @context/writing-examples.md for style consistency
- **Style Guide**: Use connector-discovered vault terminology first; @context/style-guide.md is a fallback mirror only when the vault is unavailable
- **SEO Guidelines**: Apply requirements from @context/seo-guidelines.md
- **AEO/GEO Strategy**: Apply @context/aeo-geo-blog-strategy.md for Generative Engine Optimization
- **Target Keywords**: Integrate keywords from @context/target-keywords.md naturally
- **Lightning Overlay**: If the topic or research brief mentions Simpro Lightning, AroFlo Lightning, BigChange Lightning, Simpro Group Lightning, JustAsk, Cooper, FieldReady, JobReady, JobScribe, JobBrief, Price Lock, AI tax, TrueTime, DirectLine, Coming Specialists, or any named roadmap specialist, search the vault connector in the task's natural language, read and expand the selected Lightning `resource_id` values, and apply that guidance as a scoped overlay. Use @context/lightning-positioning.md only as a fallback mirror when the connector is unavailable and the sidecar records the blocker.

### AEO/GEO Variable Resolution
Resolve `topic`, `audience`, `main_question`, `related_questions`, `tone`, `expertise`, and `length` from the research brief, generated vault context binding, repo context fallback, target keyword, and valid PAA binding before writing.

Every new article requires a structured AnswerSocrates artifact, including when `FAQ policy: required | not_applicable` resolves to `not_applicable` with a non-empty rationale. For rewrites only, PAA in a dedicated brief section takes precedence: bind the brief path and hash, do not rerun AnswerSocrates, and use those exact questions as visible FAQ headings. A rewrite without that section requires AnswerSocrates. A user CSV is accepted only with a bound AnswerSocrates artifact that records a genuine blocked state caused by login, CAPTCHA, quota, or unavailability. SERP, Reddit, and YouTube are supplemental research and cannot satisfy PAA provenance.

For rewrites only, the dedicated brief section must use this exact heading:

```markdown
## Pre-picked PAA Questions
- [Exact complete question?]
```

### E-E-A-T Proof Map Inputs
Before drafting, resolve an E-E-A-T Proof Map:
- **Experience**: Customer case studies, customer outcomes, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples.
- **Expertise**: Product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity.
- **Authority/Trust**: Public research, case-study URLs, review-site/source links, limitations/caveats, and no invented proof.
- **Fallback context sources**: Only when the connector is unavailable and the sidecar records the blocker, use case-study URLs from @context/internal-links-map.md, metric or proof candidates from @context/features.md, and review-site experience evidence, VoC, or competitor experience themes from @context/competitor-analysis.md or future review-context files as repo-local mirror inputs. These files cannot approve public claims.
- **Public-copy rule**: Context-backed metrics are valid only when the article body uses public-facing source links, such as the public case-study URL, review-site URL, or public research source.
- **403 replacement rule**: If a DOL, Capterra, G2, Trustpilot, Google Play, or other public research/source URL returns 401, 403, or `manual_review`, do not remove the citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. Source Map notes must document both the rejected 403 URL and the replacement URL. Full policy and the `public_research_link_guard.py` gate live in `context/aeo-geo-blog-strategy.md`.

### General Source Support Classes

Use only these exact general source-map classes: `primary_authority`, `independent_research`, `non_competing_expert`, `owned_product`, `customer_proof`, `review_platform`, and `competitor`. General causal, comparative, definitional, process, and recommendation claims require an exact claim-fit row with `Claim`, `Claim type`, `Evidence relation: directly_supports`, `Source class`, `Classification artifact`, `Classification hash`, `URL`, source-visible `Evidence`, and `Status: approved`. The hash-bound classification must use `simpro-source-classification/v1`; writer-supplied class labels do not qualify. PDF extraction or unreachable-HTML fallback additionally requires `Capture receipt` and `Capture receipt hash` from `simpro-source-capture-receipt/v1`. Repeating a duplicate or weak URL cannot satisfy authority.

### Simpro Web Copy Rules
- Use numerals for cardinal numbers, including 1-9.
- Do not block source-visible metric wording when a public proof source spells out the number; preserve the supported claim wording and rely on Metric Proof Pack, numeric claim source guard, and source support guard for proof.
- Because comma decisions are grammar/context dependent. No comma when the because clause is essential to the sentence meaning. Use a comma when the because clause is nonessential, contrastive, or needed to prevent misreading. Review negative constructions carefully because comma placement can change meaning.
- Place each link where it directly supports the sentence and reader task. Do not impose a per-paragraph quota.
- Do not write source/proof meta-commentary such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.

### Down-Funnel Internal Link Rule

Every draft must include at least 1 contextual down-funnel internal link to `/industries`, `/industries/...`, `/solutions/...`, or `/features/...` from @context/internal-links-map.md. Prefer the specific industry page when industry intent is clear, the `https://www.simprogroup.com/industries` hub for broad trades or general industry topics, the relevant solution page for category/workflow topics, and the relevant feature page for feature/workflow topics. Anchor text must match the destination keyword or an approved anchor example from @context/internal-links-map.md.

Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough. Use anchors like "field service payments," "accounts receivable follow-up with Fast Cash," or "field service management software" instead of "Simpro Payments," "Fast Cash," or "Simpro Premium."

### Reader Contract

Before drafting the outline, write a `Reader Contract` block. This is an editorial contract, not public proof infrastructure:

- **Primary reader**: the role, business type, region, or maturity level the article is written for.
- **Sophistication level**: beginner, intermediate, expert, or mixed, with one sentence explaining what the reader already understands.
- **Trigger problem**: the moment, decision, or operational pressure that brought the reader to the article.
- **Existing belief**: what the reader likely already believes, worries about, or has tried.
- **Decision or task helped**: the decision, task, or understanding the article will help them complete.
- **Distinctive angle**: why this article deserves to exist beyond matching the SERP.
- **Promised payoff**: the concrete reader payoff the headline and intro must deliver.
- **Funnel stage**: ToFu, MoFu, BoFu, or thought leadership.
- **Exclusions**: what the article intentionally will not cover, rank, quantify, or claim.

Use the contract to set an intent/evidence-complete word target, natural terminology coverage, critical keyword placement, semantic variations, and keyword-stuffing detection. Do not expand a complete article to satisfy a universal length target or add exact-match phrases to chase density.

## SERP Strategy Decision

After the Reader Contract, record the verified SERP observation source, dominant observed content type, every observed feature, recurring extracted structure, and qualified must-fill gaps. Match the dominant observed content type and target every applicable feature by default. Any deviation requires a documented Reader Contract exception. If verified SERP context is unavailable, mark the decision unresolved and do not invent observations or silently waive the handoff.

### Mandatory Editorial Plan Artifact

Create the existing `ArticlePlan`; `serialize_article_plan(plan)` emits the `simpro-blog-editorial-plan/v1` schema and deterministic JSON. Save that result at `research/editorial-plan-[topic-slug]-[YYYY-MM-DD].json`. The plan is mandatory for every new or changed blog and must include:

- **Reader Contract**: complete Reader Contract fields above.
- **SERP Strategy Decision**: verified intent and SERP decisions with evidence binding.
- **Original Contribution Map**: at least 1 original contribution mapped to its visible final section with a substantive exact `visible_evidence` excerpt that the final section contains.
- **SERP evidence binding**: use `simpro-serp-evidence/v1` with collected result observations, tool/run metadata, and its canonical evidence hash. Metadata-only verified labels and empty observations do not qualify.
- **Entity Map**: primary and supporting entity coverage mapped naturally, without density targets.
- **Query Ownership and Cannibalization Decision**: `clear | differentiated | blocked`; `blocked` prevents readiness.
- **Internal-Link Plan**: intent-appropriate reader-path links plus the required contextual down-funnel link, with no fixed count.
- **FAQ and PAA Policy**: `FAQ policy: required | not_applicable`, a non-empty rationale, and the PAA source/binding/selected-question decision.

### Content Structure

#### 1. Headline (H1)
- Include primary keyword naturally
- Create compelling, click-worthy title
- Keep under 60 characters for SERP display
- Promise clear value to reader

#### 2. Introduction (use the planned section target)

**CRITICAL: Direct Answer First (AI Search Optimization)**

For any "best/top/how" query, the first 1-2 sentences MUST directly answer the question. AI scrapers (ChatGPT, Perplexity, Gemini) pull from the top of the page. Don't bury the answer behind narrative.

**Example — "best project management tools":**
> The best project management tools in 2026 are Asana, Monday, and ClickUp — each built for different team sizes and workflows. Here's how they compare.

After the direct answer, use a hook to keep human readers engaged.

**Choose ONE hook type for each article:**

| Hook Type | Example | Best For |
|-----------|---------|----------|
| **Provocative Question** | "What does the 'free' plan still make your team handle manually?" | Challenging assumptions |
| **Proof-Safe Operational Scene** | "A dispatcher opens the schedule and sees three urgent jobs competing for the same technician." | Making the reader's work pressure concrete |
| **Surprising Statistic** | Use a sourced statistic only when approved proof supports the number and the section needs it. | Data-driven topics |
| **Bold Statement** | "Your current tool is lying to you about your numbers." | Controversial takes |
| **Counterintuitive Claim** | "The cheapest option might be the most expensive decision you make this year." | Comparison content |

**After the hook, follow the APP Formula:**
- **Agree**: Acknowledge something the reader already believes/feels
- **Promise**: Tell them exactly what they'll learn or gain
- **Preview**: Brief overview of what's coming (can include mini table of contents for long posts)

- **Keyword**: Include primary keyword in first 100 words
- **Credibility**: Establish why you/this article is authoritative

#### 3. Key Takeaways Block (After Introduction)

**REQUIRED: TL;DR block immediately after the introduction, before the first H2 body section.**

This gets pulled into AI-generated summaries and helps both AI and human readers quickly assess the article's value.

```markdown
> **Key Takeaways**
> - [Core finding or recommendation #1]
> - [Core finding or recommendation #2]
> - [Core finding or recommendation #3]
> - [Core finding or recommendation #4 if needed]
> - [Core finding or recommendation #5 if needed]
```

**Rules:**
- 3-5 bullet points
- Each bullet is a standalone claim with approved proof-backed specifics or concrete workflow detail; never invent numbers, names, or outcomes
- NOT a table of contents — these are the article's actual conclusions
- Written after the full article is drafted (so the takeaways are accurate)

#### 3A. AEO/GEO Structure Requirements

Apply these requirements from @context/aeo-geo-blog-strategy.md:
- **Capsule Method**: Add a 50-60 word direct-answer capsule below the H1 and at least 60% of major H2s.
- **Early usable artifact**: Place a filled data table, download link, checklist deliverable, or calculator reference within the first 300 words of body copy; Key Takeaways bullets and plain lists do not count. Full policy and the not-applicable exemption live in `context/aeo-geo-blog-strategy.md`.
- **Concrete answers**: If the target query implies a number, range, or template, supply a concrete version with disclaimers as needed. Placeholder-only table cells such as `TBD` or `Enter lender-approved value` block publish. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **PAA selection**: New articles require a structured AnswerSocrates artifact. A rewrite uses pre-picked PAA from a dedicated brief section when present; otherwise it requires AnswerSocrates. Use only complete eligible questions, without a fixed total. A user CSV requires a bound genuine blocked-state artifact; SERP, Reddit, and YouTube are supplemental only.
- **Source mapping**: Integrate claim-fit credible external sources inside natural sentences; map each source to the claim it supports. Evidence needs determine the count.
- **FAQ policy**: Use `required` when a useful FAQ is planned and `not_applicable` with a non-empty rationale otherwise. Run the following FAQ-specific rules only when visible FAQs exist.
- **FAQ answer quality**: For each visible FAQ, write a 40-60 word first paragraph that leads with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Generic deflections such as `There is no`, `It depends`, `Pricing depends`, `Costs vary`, `We do not know`, `It is unclear`, and `No source ranks` block publish readiness. Put limitations after the direct answer.
- **FAQ proof**: Every visible FAQ answer must include at least 1 authoritative non-owned public evidence link inside the visible answer. A Source Map or FAQ Proof Map can document the same evidence but cannot replace the reader-facing link.
- **FAQ Source Policy**: Every visible non-owned FAQ URL needs an exact `FAQ Proof Map` row with `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`. Use only `neutral` or `non_competing_expert` sources. Competitor-owned FAQ sources: prohibited.
- **Permitted FAQ evidence**: regulators, standards bodies, universities, trade associations, independent research/editorial, and non-competing experts. Simpro-owned links can be extra reader resources but cannot satisfy FAQ proof.
- **Vendor-specific FAQs**: remove or reframe an FAQ without compliant evidence; retain vendor evidence in comparison or vendor-specific body sections.
- **FAQ quality gate**: Run `python data_sources/modules/faq_answer_quality_guard.py [file] --fail-on error` before scoring or optimization; `/publish-readiness` runs it automatically.
- **E-E-A-T Proof Map**: Include a valid last-updated date, optional named author only when available, reviewer if available, Experience proof, Expertise proof, Authority/Trust proof, named customer proof or expert quote, and honest limitations where relevant.
- **Context boundary**: Use `context/` files as the internal source of truth for voice, positioning, keywords, product framing, internal links, approved claims, proof candidates, and approved metrics only when the Obsidian vault is unavailable; otherwise treat them as repo-local mirrors/fallbacks. Public copy may use public sources and context-backed proof, but must not mention "repo context," context file paths, Source Maps, PAA artifacts, change summaries, or internal proof-path notes.
- **Customer proof routing**: After the customer-proof selector identifies candidates, query the vault connector for approved claims in the intended public use mode, read the supporting `resource_id` values, and bind any public metric, quote, or theme to its `claim_id` and public URL. Use @context/internal-links-map.md and @context/features.md only as downstream fallback mirrors when the connector is unavailable; never publish a metric or quote solely because it appears in those files.
- **Customer proof selection governance**: Before selecting or drafting proof, resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and write the generated selector-first `Customer Proof Slate` to the validation sidecar. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the sidecar and do not invent proof. experience_story consideration is required and E-E-A-T story usage is optional. If no story fits, use `Selected: [none]` with section-specific rejection reasons. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **Fred Voccola authority evaluation**: Resolve `topic`, `title`, and `objective`, then automatically run `python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5 --output "research/fred-authority-selection-[topic-slug].md"` and copy that exact generated `Fred Voccola Authority Selection` block into the validation sidecar. Evaluation is mandatory and public use is optional. The selector defaults to `Selected: none`; select a source explicitly only after reviewing it and confirming direct topical support. If the selector, connector, context pack, or receipt validation fails, record `Evaluation status: blocked` and the blocker; do not invent Fred evidence or continue to Fred public use.
- **Recent-use proof diversity**: Treat any `recent_uses_90d` value above 0 as a proof-diversity warning, not only sources marked `overused`. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. Prefer an approved zero-recent-use source when one fits the same role, or document why no stronger underused approved proof fits. If a recently used or overused proof source is still selected, document why no stronger underused approved proof fits.
- **Selected customer proof mining**: When selected customer proof appears in public copy, add `Selected Customer Proof Mining` to the validation sidecar. Selector chooses candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **Proof-index health**: Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates, and review both recently used and overused proof rows.
- **Proof-index intake**: Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.
- **Review proof routing**: For review-derived E-E-A-T stories, automatically run `customer_proof_selector.py` with `--slate --roles experience_story --require-eeat-story`, then run the review story identity gate from the required stack below. Use `context/aeo-geo-blog-strategy.md` for Review Story Selection, Review Site Theme Selection, Capterra theme use, exact-quote, rating, and metric boundaries.
- **Customer Proof Pack**: Use the brief's Customer Proof Pack before placing direct quotes, named customer proof, approved metrics, or review-derived Experience patterns. If the pack is partial or blocked, omit unsupported claims.
- **Schema notes**: Always include BlogPosting, BreadcrumbList, ImageObject for the featured image or logo, and Organization as publisher reference only, not a separate full schema block. `FAQPage` and `Question and Answer inside FAQPage` are required only when visible FAQs exist. `Person as author` is required only when a named author exists. Require `VideoObject` if and only if a verified video embed exists. For public Markdown blog artifacts, place `schema_notes` in the top YAML frontmatter block, between the opening and closing --- delimiters. If a named author is present, include `author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and record the no-author decision in the BOM and validation sidecar.

#### 4. Main Body (use caller-supplied, intent/evidence-complete section targets)
- **Logical Flow**: Organize sections in clear, progressive order
- **H2 Sections**: Use only the main sections needed to complete the Reader Contract and verified applicable coverage
- **H3 Subsections**: Break complex sections into digestible pieces
- **Keyword Integration**: Use natural terminology coverage, critical keyword placement, semantic variations, and keyword-stuffing detection
- **Depth**: Provide thorough, actionable information at each point
- **Data**: Reference statistics and studies to support claims
- **Visuals**: Note where images, screenshots, or graphics enhance understanding
- **YouTube Embed**: Evaluate selected video evidence. Embed a relevant, public, embeddable video only when it materially supports the section; otherwise document that no eligible video was selected and omit the embed.
- **Lists**: Use bulleted or numbered lists for scannability
- **Formatting**: Bold key concepts, use short paragraphs (2-4 sentences MAX)

**OPTIONAL: Proof-Backed Customer/Review POV**

Use a proof-backed customer/review POV only when it improves the article objective. If no strong proof-backed story fits, omit the story.

Allowed:
- Actual person or business POV from an approved customer story, case study, Quote Matrix route, reference, or review-site row with sidecar proof.
- Unnamed workflow scenarios for explanation only; do not treat them as E-E-A-T.

Not allowed:
- Fictional named personas or invented company stories.
- Invented dates, metrics, quotes, outcomes, or testimonial wording.

**REQUIRED: Intent-Sensitive CTA Plan**

Give the reader a useful next action that fits the Reader Contract and funnel stage:

| Funnel stage | intent-sensitive CTA default |
|--------------|------------------------------|
| ToFu | ToFu: 0-1 soft resource/action CTA |
| MoFu | MoFu: one educational next step plus one contextual product CTA |
| BoFu | BoFu: 2-3 contextual commercial CTAs |
| Thought leadership | Thought leadership: discussion, reflection, or evidence resource |

**CTA Rules:**
- Make each CTA contextual to the surrounding section and earned by the article's proof.
- Use a commercial CTA only when the reader has enough decision context.
- Never use generic "Click here" text.

#### 5. Conclusion (use the planned section target)
- **Recap**: Close the Reader Contract promise without adding new claims
- **Action**: Provide a useful next action matched to funnel stage and reader intent
- **Next Action**: Use an intent-appropriate next action; include a commercial CTA only when the Reader Contract funnel stage calls for one
- **Encouragement**: End on empowering, forward-looking note

### SEO Optimization

#### Keyword Placement
- H1 headline
- First paragraph (within first 100 words)
- At least one relevant H2 where the exact phrase is natural; use semantic variations elsewhere without a quota
- Naturally throughout the body using reader language, related terms, and stuffing checks
- Meta title and description
- URL slug

#### Internal Linking (intent-appropriate links)
- Reference @context/internal-links-map.md for key pages
- Link to relevant pillar content from your site
- Link to related blog articles
- Link to product/service pages where natural
- Use descriptive anchor text with keywords

#### External Linking (claim-fit evidence links)
- Link to authoritative sources for statistics
- Reference industry research or studies
- Link to tools or resources mentioned
- Build credibility with quality sources

#### Readability
- Keep sentences under 25 words average
- Use transition words between sections
- Vary sentence length for rhythm
- Write at 8th-10th grade reading level
- Use active voice predominantly
- Add subheadings when the topic or reader question changes

### Target Audience Focus
- **Audience Perspective**: Write for the target audience retrieved through connector semantic search and `resource_id` reads; @context/brand-voice.md is fallback mirror context only when the connector is unavailable
- **Practical Application**: Show how information applies to their specific challenges
- **Product Integration**: Naturally mention how relevant features solve problems using connector-discovered product and feature guidance from current `resource_id` reads. Use @context/features.md only as a fallback mirror when the connector is unavailable and the sidecar records the blocker.
- **Industry Context**: Reference relevant trends and best practices
- **Technical Accuracy**: Ensure terminology and processes are correct for your industry

### Brand Voice Consistency
- Maintain Simpro tone from the vault first; reference @context/brand-voice.md only as fallback mirror context
- Follow your established voice pillars
- Use messaging framework from your context files
- Apply terminology preferences consistently
- Match tone to content type (how-to, strategy, news, etc.)
- For Lightning-specific content, apply the connector-discovered Lightning resources first: use required brand prefixes, keep JustAsk as the interface, Cooper as the brain, use exact agent names and field-service-trades first-reference wording, and publish only receipt-approved Lightning claims. Use @context/lightning-positioning.md only as a documented fallback mirror when the connector is unavailable.

## Output
Provides a complete, publish-ready article including:

### 1. Article Content
Full markdown-formatted article with:
- H1 headline
- Introduction
- Body sections with H2/H3 structure
- Conclusion with an intent-appropriate next action
- Proper formatting and styling

### 2. Meta Elements
```yaml
---
artifact_type: blog
brand: [Brand]
title: [Article title]
objective: [Reader or business objective]
audience: [Audience]
region: [Region]
last_updated: [YYYY-MM-DD matching the assembly date]
author: [Named author only when available; omit this field when no named author exists]
schema_notes:
  - BlogPosting
  - BreadcrumbList
  - ImageObject for the featured image or logo
  - "Organization as publisher reference only, not a separate full schema block"
# Add FAQPage plus Question and Answer inside FAQPage only for visible FAQs.
# Add Person as author only for a named author. Add VideoObject only for a verified embed.
Meta Title: [50-60 character optimized title ending with | Brand]
Meta Description: [150-160 character compelling description]
Primary Keyword: [main target keyword]
Secondary Keywords: [keyword1, keyword2, keyword3]
URL Slug: /blog/[optimized-slug]
Internal Links: [list of pages linked from your site]
External Links: [list of external sources]
Word Count: [actual word count]
---
```

### 3. SEO Checklist
- [ ] Primary keyword in H1
- [ ] Primary keyword in first 100 words
- [ ] Primary keyword in at least one relevant H2 where natural; semantic variations used elsewhere without a quota
- [ ] Natural terminology coverage, semantic variations, and keyword-stuffing detection checked
- [ ] Intent-appropriate internal links included, including the required down-funnel link
- [ ] Claim-fit external authority links included for the evidence used, without a fixed total
- [ ] Meta title 50-60 characters
- [ ] Meta description 150-160 characters
- [ ] Word count fits the Reader Contract, search intent, and available evidence
- [ ] Proper H2/H3 hierarchy
- [ ] Readability optimized

### 4. AI Search Optimization Checklist
- [ ] **AEO/GEO score**: Draft is expected to score 90/100 or higher
- [ ] **Direct answer**: First 1-2 sentences directly answer the target query
- [ ] **Key Takeaways**: TL;DR block with 3-5 specific bullet points after introduction
- [ ] **Meta description**: Directly answers the query (not just a teaser)
- [ ] **YouTube embed**: Video eligibility evaluated; an eligible selected video is embedded when it materially supports the article, otherwise the embed is omitted
- [ ] **FAQ prompts**: Questions written in natural language people would type into ChatGPT, not keyword fragments from AnswerSocrates
- [ ] **One idea per section**: Each H2/H3 focuses on a single clear concept
- [ ] **Author policy**: Named author mapped to Person schema when available; otherwise `author` and `Person as author` omitted
- [ ] **Capsule Method**: H1 and 60%+ major H2s include 50-60 word direct-answer capsules
- [ ] **Early usable artifact**: A filled data table, download link, checklist deliverable, or calculator reference starts within the first 300 words of body copy, or the sidecar documents a not-applicable reason
- [ ] **Concrete answers**: Number/range/template queries get a concrete answer; no placeholder table scaffolds
- [ ] **PAA**: Every question selected by the intent-driven FAQ policy is answered in the draft; a reasoned `not_applicable` decision is allowed
- [ ] **source mapping**: Every material external claim has a claim-fit source-map row and natural contextual link
- [ ] **Customer Proof Pack**: Selector automatically run, selected proof mined with `Selected Customer Proof Mining`, recent-use or overuse reason added when needed, and approved quotes/metrics mapped before use. Full proof boundaries live in `context/aeo-geo-blog-strategy.md`.
- [ ] **Schema**: Always include BlogPosting, BreadcrumbList, ImageObject for the featured image or logo, and Organization as publisher reference only, not a separate full schema block. `FAQPage` and `Question and Answer inside FAQPage` are required only when visible FAQs exist. `Person as author` is required only when a named author exists. Require `VideoObject` if and only if a verified video embed exists.

### 5. Engagement Checklist
- [ ] **Hook**: Opens with question, scenario, statistic, or bold statement (NOT generic definition)
- [ ] **APP Formula**: Introduction includes Agree, Promise, Preview elements
- [ ] **Editorial scenes**: 0-2 editorial scenes when they materially improve understanding
- [ ] **Proof-safe story boundary**: Named people or businesses require approved proof; Unnamed workflow scenarios are explanatory only; invented names, dates, metrics, quotes, and outcomes are prohibited
- [ ] **Intent-sensitive CTA**: CTA count and type match the Reader Contract funnel stage
- [ ] **Paragraph length**: No paragraphs exceed 4 sentences
- [ ] **Sentence rhythm**: Mix of short (5-10 words) and longer sentences (15-25 words)

### 6. Continuity Pass
- [ ] Every section must advance the headline promise from the Reader Contract.
- [ ] Each section answers a question created by the previous section.
- [ ] No section restarts the article, repeats the introduction, or creates repeated resets.
- [ ] Transitions explain a logical relationship, not just a transition word.
- [ ] The conclusion must complete the introduction, resolve open loops, and add a useful next action.
- [ ] remove or justify any section that does not increase the promised payoff.

## File Management
After completing the article, automatically save to:
- **File Location**: `drafts/[topic-slug]-[YYYY-MM-DD].md`
- **File Format**: Markdown with frontmatter and formatted content
- **Naming Convention**: Use lowercase, hyphenated topic slug and current date

Example: `drafts/content-marketing-strategies-2025-10-15.md`

## Validation Sidecar

Proof infrastructure belongs only in the validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`; the draft records only its sidecar path and status. Do not put an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan in the publishable blog draft. Require `VideoObject` if and only if a verified video embed exists.

Use the exact build -> preflight -> finalize -> final sequence under **Blog Assembly Seal (MANDATORY)**. A one-pass readiness command is not valid for a blog.

Meta titles must always end with the owning brand suffix in pipe format, for example `Construction Draw Schedule Explained | ClockShark`.

Only a passed detached final-readiness attestation confirms that the final article, BOM, Context Binding, proof, URL validation, source support, content score, and AEO/GEO gates agree. Readiness reads the validation sidecar without exposing proof infrastructure in public copy.

## Automatic Scrub And Publish Readiness

**CRITICAL**: Immediately after saving the article file, close the draft mutation receipt, invoke the receipt-emitting content scrubber, regenerate Context Binding, and run the two-phase seal before handoff.

### Why This Matters
AI-generated content often contains invisible Unicode marks and characteristic punctuation patterns. Scrubbing handles cleanup. The linter handles AI-writing detection and Simpro style enforcement.

### Scrub And Publish Readiness Process
1. **Close draft receipt**: Finish the mutation recorder only after the saved article contains the completed draft.
2. **Run receipt-emitting scrub and Context Binding**: Use the exact commands under **Blog Assembly Seal (MANDATORY)**.
3. **Run the two-phase seal**: Build provisional BOM, pass preflight, finalize the BOM, then write detached final readiness.
4. **Automatic execution**: This happens without asking the user to run commands.
5. **Timing**: Complete the chain before optimizer or handoff; after an optimizer mutation, restart at the optimization receipt.
6. **Scope**: Readiness verifies source artifacts only; proof maps remain in the validation sidecar.
7. **Error handling**: Fix the highest-severity failed gate, review `because` grammar in context, regenerate affected receipts, and rerun the complete seal.
8. **AI copy avoid-rule errors**: Fix copy avoid-rule errors before handoff. The linter blocks modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences in Simpro web copy.

### What Gets Cleaned
- Invisible Unicode watermarks (zero-width spaces, BOMs, format-control characters)
- Em-dashes replaced with contextually appropriate punctuation (commas or periods)
- Whitespace normalization and formatting cleanup
- All changes preserve content meaning and markdown structure

### Verification
The scrubber will display statistics:
- Unicode watermarks removed
- Format-control characters removed
- Em-dashes replaced

The AI copy linter will display:
- Error count
- Warning count
- Line-level findings with suggested fixes

URL validation will display:
- Resolved URL count
- Unresolved URL count
- Manual-review URL count

The Metric Proof Pack guard will display:
- Metric Proof Pack blocker count
- Line-level findings for missing `Search log`, missing `Approved metric` rows, or Evidence not found in the proof source

The numeric claim source guard will display:
- Unsupported metric, statistic, or numeric business claim count
- Line-level findings for claims missing a public URL or local proof artifact

The FAQ proof guard will display:
- FAQ proof blocker count
- Line-level findings for generic FAQ openers and FAQ answers missing an authoritative non-owned public evidence link in visible copy

The PAA provenance guard will display:
- PAA provenance blocker count
- Line-level findings for FAQ questions missing exact saved source-artifact provenance

The source support guard will display:
- Source support blocker count
- Line-level findings for claims whose Evidence is not visible in the cited source
- Named customer metric blockers when metrics are not in Customer Proof Pack Approved metrics
- Exact quote/testimonial blockers when quotes are not in Customer Proof Pack Approved quotes

### Example Workflow
1. Write article and save to `drafts/article-name-2025-10-31.md`.
2. Run `/scrub`, AI copy lint, URL validation, and the required proof gate stack above. Review every `because` construction during this loop, fix grammar in the sentence itself, and rerun the gates.
3. If errors remain, revise once and rerun the same stack.
4. Then proceed with scoring and optimization agents below.

This keeps cleanup separate from AI copy detection before any further processing.

URL validation confirms destinations resolve; it does not prove the page supports the claim. Use `context/aeo-geo-blog-strategy.md` for proof, source support, metric, FAQ, PAA, quote, testimonial, and customer metric boundaries.

## Automatic Agent Execution
After saving, scrubbing, linting, and passing the quality loop, execute optimization agents:

### 1. Content Analyzer Agent (NEW!)
- **Agent**: `content-analyzer`
- **Input**: Full article, meta elements, keywords, SERP data (if available)
- **Output**: Comprehensive analysis covering search intent, keyword distribution, content scope comparison, readability score, and SEO quality rating
- **File**: `drafts/content-analysis-[topic-slug]-[YYYY-MM-DD].md`

This new agent uses 5 specialized analysis modules:
- Search intent analysis
- Keyword distribution, terminology coverage, and clustering
- Content length vs competitors
- Readability scoring (Flesch scores)
- SEO quality rating (0-100)

### 2. SEO Optimizer Agent
- **Agent**: `seo-optimizer`
- **Input**: Full article content
- **Output**: SEO optimization report and suggestions
- **File**: `drafts/seo-report-[topic-slug]-[YYYY-MM-DD].md`

### 3. Meta Creator Agent
- **Agent**: `meta-creator`
- **Input**: Article content and primary keyword
- **Output**: Multiple meta title/description options
- **File**: `drafts/meta-options-[topic-slug]-[YYYY-MM-DD].md`

### 4. Internal Linker Agent
- **Agent**: `internal-linker`
- **Input**: Article content
- **Output**: Specific internal linking recommendations
- **File**: `drafts/link-suggestions-[topic-slug]-[YYYY-MM-DD].md`

### 5. Keyword Mapper Agent
- **Agent**: `keyword-mapper`
- **Input**: Article and target keywords
- **Output**: Keyword placement analysis and improvements
- **File**: `drafts/keyword-analysis-[topic-slug]-[YYYY-MM-DD].md`

## Automatic Quality Loop

After saving the initial draft, automatically close the mutation receipt and run the receipt-emitting scrubber, Context Binding, and two-phase readiness gate:

### Step 1: Scrub The Draft
Run the scrubber before publish readiness:
```bash
/scrub drafts/[article-file].md
```

### Step 2: Confirm Publish Readiness
Run the exact build -> preflight -> finalize -> final sequence at the top of this command. Do not use a one-pass shortcut.

The draft must have zero non-scoring blocking findings before `/optimize`. When content quality is below 85/100 or AEO/GEO is below 90/100, `/optimize` may run inside the AEO/GEO Recovery Loop to repair the score. Final handoff still requires both score thresholds and every blocking gate to pass.

### Step 3: Evaluate Score
The publish-readiness command includes 5 content-quality dimensions plus the required AEO/GEO gate:

| Dimension | Weight | Target |
|-----------|--------|--------|
| Humanity/Voice | 30% | No AI phrases, use contractions |
| Specificity | 25% | Concrete operational and workflow detail; proof-sensitive names, numbers, quotes, metrics, dates, and outcomes remain score-neutral until validated |
| Structure Balance | 20% | 40-70% prose (not all lists) |
| SEO Compliance | 15% | Keywords, meta, structure |
| Readability | 10% | Flesch 60-70, grade 8-10 |

### Step 4: Auto-Revise if Needed
If content quality is below 85/100 or AEO/GEO is below 90/100:
1. Review the `priority_fixes` from `/publish-readiness`
2. Review every failed check in `aeo_geo.checks`
3. Classify each failure as a copy gap, proof/sidecar gap, or scorer or parser false negative; fix false negatives in the scorer with regression coverage instead of distorting accurate copy
4. Apply the top 3-5 fixes automatically
5. Rerun `/scrub`
6. Review `because` grammar in context, then rerun `/publish-readiness`
7. Repeat once more if still below threshold, for a maximum of 2 iterations

### Step 5: Route Based on Final Score
- **General content quality score >= 85/100 and AEO/GEO score >= 90/100**: Save to `drafts/` and proceed to optimization agents
- **Any AI copy lint errors after 1 revision, or general content quality score < 85/100 or AEO/GEO score < 90/100 after 2 iterations**: Save to `review-required/` with a `_REVIEW_NOTES.md` file containing lint findings, scoring details, AEO/GEO failed checks, and remaining issues

### Review-Required Folder
Articles that fail quality threshold after 2 revision attempts go to `review-required/`:
```
review-required/
├── article-name-[YYYY-MM-DD].md
└── article-name-[YYYY-MM-DD]_REVIEW_NOTES.md
```

The `_REVIEW_NOTES.md` file contains:
- Final composite score
- Dimension breakdown
- Remaining priority fixes
- Reason for human review

## Quality Standards
Every article must meet these requirements:

### Content Requirements
- Intent/evidence-complete word target based on the Reader Contract, search intent, and proof available
- Proper H1/H2/H3 hierarchy
- Primary keyword naturally integrated
- Intent-appropriate internal links to your site content
- Claim-fit external authority links for the evidence used, without a fixed total
- Compelling meta title and description
- Clear introduction and conclusion
- Actionable, valuable information
- Brand voice maintained
- Target audience focused

### Engagement Requirements
- **Compelling hook** in first 1-2 sentences (no generic openings)
- Optional proof-backed customer/review POV when it improves the objective
- **Intent-sensitive CTA** count and type based on funnel stage
- **Usable artifact within first 300 words**
- **No paragraphs longer than 4 sentences**
- **Varied sentence rhythm** (mix short punchy + longer flowing)

### Quality Score
- **Composite quality score must be 85/100 or higher**
- **AEO/GEO score must be 90/100 or higher**
- Publish-ready quality

This ensures every article is comprehensive, optimized, engaging, and ready to rank while providing genuine value to your target audience.
