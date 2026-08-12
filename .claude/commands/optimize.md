# Optimize Command

## Blog Assembly Reseal (MANDATORY)

Start the optimization recorder before changing the article, finish it after saving, and emit the chained post-optimization receipts:

```powershell
python data_sources/modules/blog_assembly_mutation_recorder.py start --article "[file]" --state "research/stage-receipts/[topic-slug]/optimization-state.json" --run-id "[run-id]" --stage optimization --tool-name "optimize-command" --tool-version "1" --previous-receipt-hash "[sha256-of-prior-stage-receipt]"
# Apply and save the optimization here.
python data_sources/modules/blog_assembly_mutation_recorder.py finish --article "[file]" --state "research/stage-receipts/[topic-slug]/optimization-state.json" --receipt "research/stage-receipts/[topic-slug]/optimization.json" --evidence "optimizer_output=research/optimizer-[topic-slug]-[YYYY-MM-DD].json"
python data_sources/modules/content_scrubber.py "[file]" --stage post_optimization_scrub --run-id "[run-id]" --previous-receipt "research/stage-receipts/[topic-slug]/optimization.json" --stage-receipt-output "research/stage-receipts/[topic-slug]/post-optimization-scrub.json"
python data_sources/modules/context_binding_generator.py "[file]" --proof-sidecar "research/validation-[topic-slug]-[YYYY-MM-DD].md" --context-request "research/context-request-[topic-slug].json" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --stage post_optimization_context_binding --run-id "[run-id]" --previous-receipt "research/stage-receipts/[topic-slug]/post-optimization-scrub.json" --stage-receipt-output "research/stage-receipts/[topic-slug]/post-optimization-context-binding.json"
```

Non-connector branch: replace the post-optimization Context Binding command with `python data_sources/modules/context_binding_generator.py "[file]" --proof-sidecar "research/validation-[topic-slug]-[YYYY-MM-DD].md" --not-applicable-reason "Final article contains no Simpro brand, URL, or connector-sensitive language." --stage post_optimization_context_binding --run-id "[run-id]" --previous-receipt "research/stage-receipts/[topic-slug]/post-optimization-scrub.json" --stage-receipt-output "research/stage-receipts/[topic-slug]/post-optimization-context-binding.json"`. Omit context request/pack/receipt, selector, and Fred arguments from the rebuilt BOM and context arguments from readiness. The builder rejects this branch when the final article contains any Simpro signal.

Tool-emitted machine artifacts carry an `execution_attestation`, a keyed local execution-integrity attestation. Require it on every `simpro-blog-stage-receipt/v1`, verified `simpro-serp-evidence/v1`, nested `simpro-answersocrates-run-receipt/v1`, `simpro-source-classification/v1`, and `simpro-source-capture-receipt/v1`. Readiness verifies the attestation and canonical hash; a handwritten or merely rehashed replacement does not qualify. This local control does not provide a remote/provider signature and does not prove that external observations are true, so source metadata, visible evidence, freshness, PAA eligibility, and semantic claim fit still require validation. A rewrite's dedicated pre-picked PAA brief section remains path/hash-bound and takes precedence over AnswerSocrates.

Then run the exact build -> preflight -> finalize -> final reseal:

```powershell
python data_sources/modules/blog_assembly_bom.py build "[file]" --validation-sidecar "research/validation-[topic-slug]-[YYYY-MM-DD].md" --editorial-plan "research/editorial-plan-[topic-slug]-[YYYY-MM-DD].json" --serp-evidence "research/serp-evidence-[topic-slug]-[YYYY-MM-DD].json" --paa-artifact "research/paa-questions-[topic-slug]-[YYYY-MM-DD].json" --context-request "research/context-request-[topic-slug].json" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --customer-proof-selector-evidence "research/customer-proof-selector-evidence-[topic-slug].json" --fred-authority-evidence "research/fred-authority-selection-[topic-slug].md" --optimizer-output "research/optimizer-[topic-slug]-[YYYY-MM-DD].json" --prior-preflight-readiness "research/preflight-readiness-[topic-slug]-[YYYY-MM-DD].json" --stage-receipt "research/stage-receipts/[topic-slug]/draft.json" --stage-receipt "research/stage-receipts/[topic-slug]/scrub.json" --stage-receipt "research/stage-receipts/[topic-slug]/context-binding.json" --stage-receipt "research/preflight-readiness-[topic-slug]-[YYYY-MM-DD]-stage-receipt.json" --stage-receipt "research/stage-receipts/[topic-slug]/optimization.json" --stage-receipt "research/stage-receipts/[topic-slug]/post-optimization-scrub.json" --stage-receipt "research/stage-receipts/[topic-slug]/post-optimization-context-binding.json" --workflow-mode "[new|rewrite]" --assembly-date "[YYYY-MM-DD]" --output "research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization.json"
python data_sources/modules/publish_readiness.py "[file]" --proof-sidecar "research/validation-[topic-slug]-[YYYY-MM-DD].md" --context-request "research/context-request-[topic-slug].json" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --assembly-bom "research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization.json" --phase preflight --output "research/final-preflight-readiness-[topic-slug]-[YYYY-MM-DD].json"
python data_sources/modules/blog_assembly_bom.py finalize --bom "research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization.json" --preflight-readiness "research/final-preflight-readiness-[topic-slug]-[YYYY-MM-DD].json" --output "research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization-final.json"
python data_sources/modules/publish_readiness.py "[file]" --proof-sidecar "research/validation-[topic-slug]-[YYYY-MM-DD].md" --context-request "research/context-request-[topic-slug].json" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --assembly-bom "research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization-final.json" --phase final --output "research/final-readiness-attestation-[topic-slug]-[YYYY-MM-DD].json"
```

Final readiness writes a detached final-readiness attestation with `verification_scope: source_artifact`; it is not hashed back into the BOM and does not imply CMS-rendered verification.

### After Optimization Mutations

All optimizer outputs and manual edits are content mutations. The closed sequence is `optimization` -> `post_optimization_scrub` -> `post_optimization_context_binding` -> `final_preflight_readiness`. The initial preflight remains bound to the immutable provisional BOM at `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json`, whose out-of-place finalized form is `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-final.json`. Use the receipt and reseal commands above for the distinct post-optimization provisional and final BOMs. Do not overwrite the BOM referenced by the prior preflight. Any further mutation invalidates the BOM and detached attestation and requires another versioned provisional/final pair.

Use this command to perform a final SEO optimization pass on completed articles before publishing.

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

When `author_policy.status` is `not_provided`, first-person singular author judgment outside quotes is prohibited.

## Usage
`/optimize [article file]`

## What This Command Does
1. Performs comprehensive SEO audit of article
2. Reviews critical keyword placement, natural terminology coverage, and stuffing risk
3. Optimizes meta elements for SERP performance
4. Validates internal and external links
5. Ensures all SEO best practices are met

## Process

Use the Simpro vault connector as the primary source for every blog, SEO, AEO, competitor, proof, product, audience, and workflow decision. Run vault health, describe available roles/topics/entities, use semantic search in the task's natural language, read and expand results by `resource_id`, query approved claims for public proof-sensitive language, then build and validate the context pack and receipt. Repo-local context is fallback only when the vault is unavailable: record the explicit vault-unavailable blocker in the validation sidecar, and do not treat fallback files as public-claim approval authority.

### Validation Sidecar And Publish Readiness

Before returning `Ready`, confirm proof-only infrastructure lives in a validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`, not in the blog copy. The article file must not include an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, `Vault Brand Language Alignment`, or structured data plan.

For every Simpro optimization, resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5 --output "research/fred-authority-selection-[topic-slug].md"`, and copy that exact generated `Fred Voccola Authority Selection` block into the validation sidecar. Evaluation is mandatory and public use is optional. The selector defaults to `Selected: none`; select a source explicitly only after reviewing it and confirming direct topical support. If the selector, connector, context pack, or receipt validation fails, record `Evaluation status: blocked` and the blocker; do not invent Fred evidence, change public Fred content, or return `Ready`.

Vault product-language check: If the article uses Simpro product, feature, add-on, solution, industry, or related Simpro product URL language, confirm the validation sidecar contains `Vault Brand Language Alignment` with connector evidence, `context_pack_hash`, `receipt_hash`, relevant `resource_id` values, feature-specific `resource_id` evidence when named features/add-ons appear, solution or vertical `resource_id` evidence when solution/industry language appears, any required `claim_id` values, language applied, fallback context use, source-verification boundary, and `Status: aligned`. The `vault_brand_language_guard.py` readiness gate runs inside both phases. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

Before returning `Ready`, run the exact reseal at the top of this command. It runs URL validation, public artifact checks, AI copy linting, public research link checks, Metric Proof Pack, numeric claim, conditional FAQ answer quality and FAQ proof, PAA provenance, source support, customer proof diversity, review story identity, vault brand language, Named Feature Status, content score, and AEO/GEO gates.

FAQ answers must use a 40-60 word first paragraph, lead with a supported number/range, named recommendation, definition, concrete action, or explained yes/no response, and move limitations after the direct answer. Every FAQ answer must contain at least 1 authoritative non-owned public evidence link in visible copy; a Source Map or FAQ Proof Map cannot replace that link.

FAQ Source Policy: For every visible non-owned FAQ URL, add an exact `FAQ Proof Map` row with `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`; source class must be `neutral` or `non_competing_expert`. Competitor-owned FAQ sources: prohibited. Use neutral authorities or non-competing experts; Simpro-owned links are supplemental only. Reframe or remove vendor-specific FAQs without compliant evidence and retain vendor evidence in comparison or vendor-specific body sections.


Run `python data_sources/modules/faq_answer_quality_guard.py [file] --fail-on error` when debugging FAQ quality failures; `/publish-readiness` runs it automatically.

403 replacement rule: If a DOL, Capterra, G2, Trustpilot, Google Play, or other public research/source URL returns 401, 403, or `manual_review`, do not remove the citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. Source Map notes must document both the rejected 403 URL and the replacement URL. `/publish-readiness` runs `public_research_link_guard.py` to block sidecar-only handling of public research, compliance, legal, regulatory, or statistical proof.

Fix copy avoid-rule errors before returning `Ready`. The AI copy linter blocks modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences in Simpro web copy.

Use `context/aeo-geo-blog-strategy.md` for the full proof policy and individual module debugging when `/publish-readiness` reports a specific failed gate.

If selected customer proof appears in public copy, confirm the validation sidecar has `Selected Customer Proof Mining`. Selector chooses candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use.

If customer proof appears in public copy, experience_story consideration is required and E-E-A-T story usage is optional. Confirm the `Customer Proof Slate` includes an `experience_story` row with a selected proof-backed story or `Selected: [none]` plus section-specific rejection reasons. Full policy lives in `context/aeo-geo-blog-strategy.md`.

## AEO/GEO Recovery Loop

An AEO/GEO score below 90/100 is a repair trigger, not a reporting endpoint. Unless the user explicitly requested a read-only audit, the LLM must continue in the same workflow:

1. Review every failed check in `aeo_geo.checks` and the scorer's `priority_fixes`.
2. Classify each failure as a public-copy gap, validation-sidecar/proof gap, or scorer or parser false negative.
3. If the article visibly satisfies the written requirement but scoring misses it, add a regression test and fix the scorer or parser false negative. Do not distort accurate, brief-approved copy to satisfy brittle matching.
4. Apply the top 3-5 fixes that address root causes. Do not invent PAA questions, claims, proof, metrics, quotes, or customer experience to gain points.
5. Finish the optimization receipt, run the post-optimization scrub and Context Binding receipt stages, rebuild with `--prior-preflight-readiness`, then run preflight -> finalize -> final.
6. Repeat once if needed. If AEO/GEO remains below 90/100 after 2 iterations, route the artifact to `review-required/` with the score, failed checks, attempted fixes, and any external evidence or authority blocker.

`/optimize` is allowed inside this recovery loop when all proof, source, URL, and public-artifact gates pass but content quality or AEO/GEO does not. Final handoff still requires content quality of at least 85/100, AEO/GEO of at least 90/100, and every blocking gate to pass.

### Content Audit

#### Keyword Analysis
- **Primary Keyword Coverage**: Check natural terminology coverage, critical keyword placement, semantic variations, and keyword-stuffing detection
- **Keyword Placement Check**:
  - [ ] In H1 headline
  - [ ] In first 100 words
  - [ ] In at least one relevant H2 where the exact phrase is natural
  - [ ] In meta title
  - [ ] In meta description
  - [ ] In URL slug
- **Semantic Variations**: Verify related keywords are used naturally
- **Keyword Stuffing**: Ensure no over-optimization or unnatural usage
- **Semantic Terms**: Confirm related terminology is present where it improves clarity and coverage

#### Heading Structure
- **H1**: Only one H1, includes primary keyword
- **H2s**: One section per distinct reader question or task change; use the primary term or a semantic variation where natural, without a quota
- **H3s**: Proper nesting under H2s, descriptive and keyword-rich
- **Hierarchy**: Logical progression, no skipped levels (H1→H3)
- **Length**: Headings are descriptive but concise

#### Content Quality
- **Word Count**: Fits search intent, evidence depth, and article objective without filler
- **Paragraph Length**: Average 2-4 sentences, no walls of text
- **Sentence Length**: Varied, averaging under 25 words
- **Readability Score**: 8th-10th grade level (Flesch-Kincaid)
- **Active Voice**: Predominantly active voice usage
- **Transition Words**: Smooth flow between sections
- **List Usage**: Bullets/numbers for scannability
- **Formatting**: Bold, italics used appropriately for emphasis

### Link Optimization

#### Internal Links (intent-appropriate; contextual down-funnel link required)
- **Quantity**: Count current internal links to your company content
- **Quality**: Verify links are contextually relevant
- **Anchor Text**: Check for keyword-rich, descriptive anchor text
- **Placement**: Natural integration within body content
- **Variety**: Links to different page types (pillar, blog, product, resources)
- **Reference**: Cross-check @context/internal-links-map.md for opportunities
- **Broken Links**: Verify all internal links work

**Recommendations**:
- Where to add additional internal links
- Better anchor text for existing links
- High-priority pages that should be linked

#### External Links (claim-fit evidence required; no fixed total)
- **Quantity**: Count resolved non-owned public research links; owned Simpro and ClockShark product links do not count as external research links
- **Authority**: Verify links are to credible, authoritative sources
- **Relevance**: Ensure external links support content claims
- **Freshness**: Check that linked sources are current
- **Broken Links**: Test all external links
- **Link Attributes**: Verify appropriate use of nofollow where needed
- **Not Applicable**: Use fewer than 2 resolved non-owned public research links only when the validation sidecar marks `External research requirement: not applicable` with a reason

**Recommendations**:
- Additional authoritative sources to link
- Outdated links to replace
- Statistics that need source citations

### Meta Element Optimization

#### Meta Title
- **Length**: 50-60 characters (check current length)
- **Keyword**: Primary keyword included naturally
- **Compelling**: Attention-grabbing and click-worthy
- **Brand**: Required final suffix in pipe format, such as `| Simpro` or `| ClockShark`
- **Uniqueness**: Distinct from other your company page titles

**Provide**:
- Current meta title analysis
- 3-5 optimized alternative options
- Recommended best choice

#### Meta Description
- **Length**: 150-160 characters (check current length)
- **Keyword**: Primary keyword included
- **Value Prop**: Clear benefit to reader
- **Search Intent**: Uses accurate value or action language when it improves the result snippet
- **Compelling**: Encourages click from SERP
- **Completeness**: Doesn't cut off mid-sentence

**Provide**:
- Current meta description analysis
- 3-5 optimized alternative options
- Recommended best choice

#### URL Slug
- **Length**: Concise but descriptive
- **Keyword**: Primary keyword included
- **Structure**: Lowercase, hyphens between words
- **Brevity**: Shorter is better (3-5 words ideal)
- **Clean**: No stop words (a, the, and) unless necessary

**Provide**:
- Current URL evaluation
- Alternative if improvement needed

### Technical SEO

#### Image Optimization
- **Alt Text**: Note where images need alt text with keywords
- **File Names**: Check that image file names are descriptive
- **Placement**: Images break up text appropriately
- **Relevance**: Images support content points

#### Featured Snippet Opportunity
- **Question Format**: Check if content answers specific question
- **List Format**: Identify list-based content for snippet optimization
- **Table Format**: Note if data could be formatted as table
- **Definition**: Check if concept could be featured snippet
- **Optimization**: Suggest how to structure for snippet capture

#### Schema Markup Suggestions
- **Article Schema**: Recommend article schema elements
- **FAQ Schema**: If Q&A format used
- **How-To Schema**: If step-by-step instructions included

### Brand & Voice

#### your company Alignment
- **Brand Voice**: Verify alignment through connector semantic search and current `resource_id` reads; use @context/brand-voice.md only as a fallback mirror when the connector is unavailable
- **Style Guide**: Check connector semantic search and current `resource_id` reads first; use @context/style-guide.md only as a fallback mirror when the vault is unavailable and the validation sidecar records the vault-unavailable blocker
- **Messaging**: Ensure messaging reflects your company positioning
- **Product Mentions**: Natural integration of your company features
- **Next Action**: Matches the Reader Contract and funnel stage; no CTA is added when none is called for

#### User Experience
- **Introduction**: Compelling hook that draws reader in
- **Value Delivery**: Article delivers on headline promise
- **Actionability**: Practical takeaways and next steps
- **Conclusion**: Completes the headline promise with an intent-appropriate next action
- **Scannability**: Easy to skim and find key information

## Output
Provides comprehensive optimization report:

### 1. SEO Score (0-100)
- **Keyword Optimization**: /25
- **Technical SEO**: /25
- **Content Quality**: /25
- **User Experience**: /25
- **Overall Score**: /100

### 2. Priority Fixes
List of critical issues to address before publishing:
- [ ] Fix 1 (High Priority)
- [ ] Fix 2 (High Priority)
- [ ] Fix 3 (Medium Priority)

### 3. Optimization Recommendations
**Quick Wins** (can be done in 5-10 minutes):
- Specific keyword placement adjustments
- Meta element tweaks
- Internal link additions

**Strategic Improvements** (more time investment):
- Content expansion opportunities
- Structural reorganization
- Additional research needed

### 4. Optimized Meta Options
**Meta Title Options** (pick one):
1. [Option 1 | Brand] (58 chars)
2. [Option 2 | Brand] (59 chars)
3. [Option 3 | Brand] (60 chars)

**Meta Description Options** (pick one):
1. [Option 1] (157 chars)
2. [Option 2] (158 chars)
3. [Option 3] (160 chars)

### 5. Link Enhancement
**Internal Links to Add**:
- Link to [Page Name] in [Section Name] with anchor text "[suggested text]"
- Link to [Page Name] in [Section Name] with anchor text "[suggested text]"

**External Links to Add**:
- Add source for statistic in [Section Name]: [suggested source]
- Add authority link in [Section Name]: [suggested source]

### 6. Keyword Distribution Map
Visual representation of where primary keyword appears:
- H1: ✓
- First 100 words: ✓
- H2 sections: report relevant exact-match and semantic placements without a heading quota
- Body paragraphs: report natural semantic coverage and flag only demonstrable stuffing; do not target a density percentage
- Conclusion: ✓
- Meta title: ✓
- Meta description: ✓

### 7. Final Checklist
- [ ] Primary keyword in H1
- [ ] Primary keyword in first 100 words
- [ ] Primary keyword in at least one relevant H2 where natural; semantic variations used elsewhere without a quota
- [ ] Natural terminology coverage, semantic variations, and keyword-stuffing detection checked
- [ ] Intent-appropriate internal links included, including the required contextual down-funnel link
- [ ] Every material external claim has a claim-fit authority link; no fixed link total is used
- [ ] Meta title 50-60 characters ending with `| Brand`
- [ ] Meta description 150-160 characters
- [ ] Word count fits search intent, evidence depth, and article objective
- [ ] Proper H1/H2/H3 hierarchy
- [ ] Readability optimized (8th-10th grade)
- [ ] Images have alt text
- [ ] Next action matches the Reader Contract and funnel stage; no CTA is added when none is called for
- [ ] Brand voice maintained
- [ ] No broken links
- [ ] URL validation passed through `/publish-readiness`
- [ ] Metric Proof Pack guard passed using the gate command above
- [ ] Numeric claim source guard passed using the gate command above
- [ ] FAQ proof guard passed using the gate command above
- [ ] PAA provenance guard passed using the gate command above
- [ ] Source support guard passed using the gate command above
- [ ] Ready to publish

### 8. Publishing Readiness
**Status**: Ready / Needs Minor Fixes / Needs Revision

**Estimated Time to Publishing**: [X minutes/hours]

**Next Steps**:
1. [Specific action needed]
2. [Specific action needed]
3. Move to `/published` folder when complete

## File Management
After optimization analysis, save report to:
- **File Location**: `drafts/optimization-report-[topic-slug]-[YYYY-MM-DD].md`
- **File Format**: Markdown with scores, checklists, and recommendations
- **Naming Convention**: Use article slug + "optimization-report" + date

Example: `drafts/optimization-report-podcast-analytics-2025-10-15.md`

## Integration with Agents
The `/optimize` command triggers final review from all agents:
- **content-analyzer** (NEW!): Comprehensive analysis with search intent, keyword density & clustering, content length comparison, readability score, and SEO quality rating (0-100)
- **seo-optimizer**: Technical SEO final check
- **meta-creator**: Best meta title/description options
- **internal-linker**: Last opportunity internal linking suggestions
- **keyword-mapper**: Final keyword distribution analysis

### New: Content Analyzer Module
The optimize command now includes advanced SEO analysis:
- **Search Intent**: Verify content matches user search intent (informational/commercial/transactional)
- **Keyword Density & Clustering**: Detailed density analysis, keyword stuffing detection, topic clustering
- **Content Length Comparison**: Compare word count against an intent-representative SERP sample; use competitor length as context, not a target
- **Readability Score**: Flesch Reading Ease, Flesch-Kincaid Grade Level, sentence structure analysis
- **SEO Quality Rating**: Overall score (0-100) with category breakdowns and specific recommendations

## Publishing Decision
An optimization score alone never authorizes publication. Final handoff requires content quality of at least 85/100, AEO/GEO of at least 90/100, a final BOM, a passed detached final-readiness attestation, and no blocking gate failures. Any lower score or failed gate returns the article to the repair loop or `review-required/`.

This ensures every article meets your company quality standards and SEO best practices before going live.
