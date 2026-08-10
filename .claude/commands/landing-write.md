# Landing Page Write Command

## Context Binding Regeneration (MANDATORY)

After the final content mutation, regenerate the machine-owned binding before `/publish-readiness`:

```bash
python data_sources/modules/context_binding_generator.py "$FILE_PATH" --proof-sidecar "$PROOF_SIDECAR" --context-request "$CONTEXT_REQUEST" --context-pack "$CONTEXT_PACK" --context-receipt "$CONTEXT_RECEIPT"
```

Run this again after every scrub, optimization, or editorial change that modifies public copy. A landing-page score alone does not authorize handoff.

Use this command to create high-converting landing pages optimized for either organic SEO traffic or paid PPC traffic.

## Usage
`/landing-write [topic or research brief] --type [seo|ppc] --goal [trial|demo|lead]`

**Examples:**
- `/landing-write "product hosting for beginners" --type seo --goal trial`
- `/landing-write "research/landing-brief-private-producting.md" --type ppc --goal demo`
- `/landing-write "product monetization guide" --type seo --goal lead`

**Defaults:**
- `--type seo` (if not specified)
- `--goal trial` (if not specified)

## What This Command Does

1. Creates conversion-optimized landing pages (not blog articles)
2. Tailors content length and structure to page type (SEO vs PPC)
3. Optimizes CTAs for the specified conversion goal
4. Includes all CRO best practices (trust signals, risk reversal, etc.)
5. Scores the page against landing page best practices

## Pre-Writing Review

**Required Connector Workflow:**
- Run vault health, describe available roles/topics/entities, and search for the landing-page objective in natural language.
- Read and expand the smallest relevant results by `resource_id` for brand voice, audience, product, feature, solution, industry, Lightning, customer proof, and competitor context.
- Query approved claims for every proof-sensitive public statement, including product status, commercial treatment, metrics, customer outcomes, comparisons, quotes, pricing, and roadmap language. A context resource alone does not approve a public claim.
- Build the context pack and validate its receipt before drafting. Bind the validation sidecar to the resulting `context_pack_hash`, `receipt_hash`, supporting `resource_id` values, approved `claim_id` values, use modes, public URLs when required, and current revisions.
- If the connector is unavailable, document the exact blocker in the validation sidecar. Only then may repo-local context files be used as fallback mirrors, and unsupported public claims must be omitted.

**Required Context:**
- **CRO Best Practices**: Retrieve current conversion guidance through connector semantic search and `resource_id` reads; @context/cro-best-practices.md is an unavailable-connector fallback mirror only.
- **Brand Voice**: Retrieve current tone and messaging through connector semantic search and `resource_id` reads; @context/brand-voice.md is an unavailable-connector fallback mirror only.
- **Style Guide**: Retrieve current terminology and claim boundaries through connector semantic search and `resource_id` reads; @context/style-guide.md is an unavailable-connector fallback mirror only.
- **Product and Proof Points**: Retrieve current product and feature context by `resource_id`, then use approved `claim_id` results for capabilities, scale proof, metrics, commercial treatment, or customer outcomes. @context/features.md is an unavailable-connector fallback mirror and cannot approve public proof.
- **Lightning Context**: If the page is about Simpro Lightning, AroFlo Lightning, BigChange Lightning, Simpro Group Lightning, JustAsk, Cooper, FieldReady, JobReady, JobScribe, JobBrief, Price Lock, AI tax, TrueTime, DirectLine, Coming Specialists, or any named roadmap specialist, search, read, and expand current Lightning resources through the connector and query approved claims for public wording. @context/lightning-positioning.md is an unavailable-connector fallback mirror only.
- **Customer Proof**: Search customer-proof resources, read the selected evidence by `resource_id`, and query approved claims for the intended use mode. Public copy requires the approved public URL; exact quotes require source-visible quote approval. @context/internal-links-map.md and @context/features.md are unavailable-connector fallback mirrors only and cannot make a claim publishable.

**If Research Brief Available:**
- Review competitor analysis
- Use recommended headlines
- Reference identified pain points
- Integrate suggested trust signals

**Lightning Landing Pages:**
- Keep connector-discovered core Simpro messaging intact for general Simpro pages; use current connector-discovered Lightning resources only for Lightning-specific claims and copy.
- Use required brand prefixes in customer-facing copy and do not use Lightning alone as the product name.
- Include a JustAsk moment or Price Lock callout only when the validated context pack contains approved claims for the intended public use.
- Verify time-sensitive pricing, roadmap, commercial-treatment, and competitor claims through current approved claims and public evidence before publication.

**Proof-sensitive template rule:**
- Any metric, testimonial, customer name, result, rating, logo, trial term, demo duration, risk reversal, or commercial promise must map to a receipt-approved claim with its `claim_id`, permitted use mode, and public URL when required.
- If no compatible approved claim exists, omit that proof element. Conversion structure never overrides proof approval.
- Do not invent or leave publishable-looking placeholder metrics, testimonials, identities, outcomes, or commercial terms in the draft.

---

## SEO Landing Page Structure (--type seo)

**Word Count:** 1500-2500 words
**CTAs:** 3-5 distributed throughout
**Internal Links:** 2-3 strategic links

### Content Structure

```markdown
# [Benefit-Focused Headline with Keyword]

**Meta Title**: [50-60 chars, keyword + benefit, ending with | Brand]
**Meta Description**: [150-160 chars, includes CTA]
**Target Keyword**: [primary keyword]
**Page Type**: seo
**Conversion Goal**: [trial|demo|lead]

---

[HOOK: 2-3 sentences. Start with pain point, surprising stat, or question]

[Optional trust signal from a receipt-approved claim; record its `claim_id`, use mode, and public URL. Omit when none is approved.]

**[Primary CTA Button ->]**

## [H2: Problem/Pain Point Section]

[2-3 paragraphs acknowledging the reader's struggle]

[Optional customer story from a receipt-approved claim and verified identity. Otherwise use an unnamed explanatory workflow scenario that makes no empirical outcome claim.]

## [H2: Solution Overview]

[Introduce how [YOUR COMPANY] solves this problem]

**Key Benefits:**
- **[Benefit 1]** - [One sentence]
- **[Benefit 2]** - [One sentence]
- **[Benefit 3]** - [One sentence]

**[Secondary CTA ->]**

## [H2: Features That Deliver]

[3-5 features, each tied to a benefit]

### [Feature 1]
[2-3 sentences: what it is, why it matters]

### [Feature 2]
[Continue...]

## [Optional H2: Approved Customer Proof]

[Include only receipt-approved proof. Exact testimonial text requires `exact_quote` permission, verified attribution, a matching `claim_id`, and a same-paragraph public URL. Numeric outcomes require an approved metric use mode. Omit this section when no relevant approved claim exists.]
**[CTA Button ->]**

## [H2: How It Works]

1. **[Step 1]** - [Brief description]
2. **[Step 2]** - [Brief description]
3. **[Step 3]** - [Brief description]

## [H2: FAQ Section]

**[Question addressing objection]?**
[Answer - 2-3 sentences]

**[Question addressing objection]?**
[Answer - 2-3 sentences]

[4-6 FAQs total]

## [H2: Ready to [Achieve Outcome]?]

[1-2 sentences summarizing the value]

**[Strong CTA Button ->]**

[Optional risk reversal using only current receipt-approved commercial terms; otherwise omit.]
```

---

## PPC Landing Page Structure (--type ppc)

**Word Count:** 400-800 words
**CTAs:** 2-3 (same goal, prominent)
**Internal Links:** 0-1 (minimize distractions)

### Content Structure

```markdown
# [Headline Matching Ad Copy]

**Meta Title**: [Match ad headline]
**Meta Description**: [Match ad description]
**Target Keyword**: [ad keyword]
**Page Type**: ppc
**Conversion Goal**: [trial|demo|lead]

---

[One-sentence value proposition matching the ad]

[Optional trust signal from a receipt-approved claim; record its `claim_id`, use mode, and public URL. Omit when none is approved.]

**[Primary CTA Button - Large and Prominent ->]**

## [H2: Why [Audience] Choose [YOUR COMPANY]]

- **[Benefit 1]** - [One sentence max]
- **[Benefit 2]** - [One sentence max]
- **[Benefit 3]** - [One sentence max]

## [Optional H2: Approved Proof]

[Include only receipt-approved proof with a matching `claim_id`, permitted use mode, verified attribution when applicable, and a same-paragraph public URL. Omit when no relevant approved claim exists.]
**[Primary CTA Button ->]**

## [H2: What You Get]

- [Included item/benefit]
- [Included item/benefit]
- [Included item/benefit]

[Optional risk-reversal section using only current receipt-approved commercial terms. Omit when none is approved.]
**[Final CTA Button ->]**
```

---

## Goal-Specific Guidelines

### Trial Goal (--goal trial)

**Primary CTAs:**
- "Start Your Trial"
- "Explore the Product"
- [A current receipt-approved trial CTA when commercial terms are stated]

**Supporting Copy:**
- State trial length, cost, setup time, credit-card requirements, cancellation terms, or commitment language only when each term is supported by a current receipt-approved claim.
- Omit unapproved commercial details.

**Optional Trust Signals:**
- Receipt-approved customer or user scale
- Receipt-approved ease-of-setup evidence
- Receipt-approved commitment terms

### Demo Goal (--goal demo)

**Primary CTAs:**
- "Book Your Demo ->"
- "Schedule a Call ->"
- "See It in Action ->"

**Supporting Copy:**
- Explain what the demo covers.
- State duration, sales treatment, or personalization promises only when supported by current approved guidance or a receipt-approved claim; otherwise omit them.

**Optional Trust Signals:**
- Receipt-approved customer logos
- Connector-supported solution language
- Verified expert guidance

### Lead Goal (--goal lead)

**Primary CTAs:**
- "Download the Guide"
- "Access the Resource"
- "Get the Resource"
**Supporting Copy:**
- Explain what the reader receives.
- Include a content preview or teaser.
- State delivery timing, privacy, or contact-frequency promises only when verified in current approved guidance; otherwise omit them.

**Optional Trust Signals:**
- Receipt-approved community or subscriber size
- Verified author credentials
- Content preview

---

## Required Elements Checklist

### Above the Fold (Critical)
- [ ] Benefit-focused headline (H1)
- [ ] Clear value proposition (1-2 sentences)
- [ ] Primary CTA button (prominent, contrasting)
- [ ] Optional trust signal only when it maps to a receipt-approved claim; omission is valid

### Trust Signals
- [ ] Every included proof element maps to a receipt-approved `claim_id` and permitted use mode
- [ ] Exact quotes and identities have verified attribution and a same-paragraph public URL
- [ ] Numeric outcomes use approved metric claims
- [ ] Unapproved testimonials, results, ratings, logos, and risk reversals are omitted

### CTAs
- [ ] Action verb in CTA text (Start, Get, Try, Book)
- [ ] Value-oriented CTA language that does not assert unapproved commercial terms
- [ ] Goal-aligned CTA copy
- [ ] First CTA within 20% of page
- [ ] CTA at end of page

### SEO (SEO pages only)
- [ ] Keyword in headline
- [ ] Keyword in meta title
- [ ] Keyword in first 100 words
- [ ] 2-3 internal links

---

## Headline Requirements

### Formula Options

**Benefit-Focused:**
- "[Achieve Outcome] Without [Pain Point]"
- "The [Adjective] Way to [Achieve Outcome]"
- "Finally, [Solution] for [Audience]"

**Number-Based (only with a matching receipt-approved metric claim):**
- "[Approved Number] [Audience] Use [Product]"
- "[Approved Time] to [Supported Outcome]"
**Question-Based:**
- "Ready to [Achieve Outcome]?"
- "What if You Could [Desired Outcome]?"

### Headline Don'ts
- NO "Welcome to..."
- NO "The Best..." without proof
- NO generic "Everything You Need"
- NO starting with "Our" or "We"
- NO longer than 70 characters

---

## File Output

Save completed landing page to:
- **Directory**: `landing-pages/`
- **Filename**: `[topic-slug]-[YYYY-MM-DD].md`
- **Example**: `landing-pages/product-hosting-beginners-2025-12-11.md`

---

## Automatic Scrub And AI Copy Lint

After saving, immediately run the content scrubber:
```
/scrub landing-pages/[filename].md
```

This removes invisible Unicode marks, em dashes, and whitespace artifacts.

Then run the AI copy linter:
```bash
python data_sources/modules/ai_copy_linter.py landing-pages/[filename].md --profile simpro-web --fail-on error
```

If errors remain, revise once, rerun `/scrub`, rerun the linter, then save to `review-required/landing-pages/` with lint findings if errors remain. Copy avoid-rule errors block handoff, including modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences.

---

## Automatic Scoring

After scrubbing and linting, score the landing page using:

```bash
python data_sources/modules/landing_page_scorer.py landing-pages/[filename].md --type [seo|ppc] --goal [trial|demo|lead]
```

Or run via the landing-page-optimizer agent.

### Score Requirements
- **Minimum Score**: 75/100 to be publish-ready
- **No Critical Issues**: Must resolve any critical issues before publishing

### If Score < 75:
1. Review critical issues and warnings
2. Apply top 3 fixes
3. Rerun `/scrub` and the AI copy linter
4. Re-score
5. If AI copy lint errors remain after 1 revision or score is still below threshold, save to `review-required/landing-pages/` with notes

---

## Automatic Agent Execution

After saving and scrubbing, run these agents:

### 1. Landing Page Optimizer Agent
- **Agent**: `landing-page-optimizer`
- **Input**: Full landing page content
- **Output**: CRO optimization report
- **Analyzes**: Above-fold, CTAs, trust signals, structure

### 2. Headline Generator Agent
- **Agent**: `headline-generator`
- **Input**: Page content and keyword
- **Output**: 10+ headline variations for A/B testing

### 3. CRO Analyst Agent
- **Agent**: `cro-analyst`
- **Input**: Page content and goal
- **Output**: Psychology and persuasion analysis

---

## Quality Standards

### SEO Landing Pages Must Have:
- 1500-2500 words
- 3-5 CTAs distributed throughout
- 4-6 FAQ questions (featured snippet opportunity)
- 2-3 internal links
- Proper H2/H3 structure
- Receipt-approved proof only when relevant approved claims exist; otherwise omit proof sections

### PPC Landing Pages Must Have:
- 400-800 words maximum
- 2-3 prominent CTAs (same goal)
- Headline matching ad copy
- Minimal navigation/distractions
- Fast-loading (minimal images)
- Receipt-approved proof and commercial terms only when relevant approved claims exist; otherwise omit them

### Both Page Types Need:
- Score >= 75 on landing page scorer
- No critical issues
- All required above-fold elements
- Goal-aligned CTA copy
- Trust signals present only when receipt-approved; omission is valid when no relevant approved claim exists
- Clear value proposition

---

## Differences from /write Command

| Aspect | /write (Blog) | /landing-write |
|--------|---------------|----------------|
| **Goal** | Educate & inform | Convert visitors |
| **Length** | 2000-3000+ words | 400-2500 words |
| **CTAs** | 2-3 contextual | 3-5 prominent (SEO) |
| **Structure** | Educational flow | Conversion flow |
| **SEO Focus** | High (rankings) | Varies (SEO vs PPC) |
| **Internal Links** | 3-5 | 0-3 |
| **Output** | drafts/ | landing-pages/ |
| **Scoring** | content_scorer | landing_page_scorer |

---

## Example Workflow

```bash
# 1. Research the opportunity (optional but recommended)
/landing-research "product hosting for wordpress" --type seo

# 2. Create the landing page
/landing-write "research/landing-brief-product-hosting-wordpress.md" --type seo --goal trial

# 3. Review score and recommendations
# (automatic scoring runs after save)

# 4. Make revisions if needed
# (edit the file in landing-pages/)

# 5. Publish when ready
/landing-publish landing-pages/product-hosting-wordpress-2025-12-11.md
```
