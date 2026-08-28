# SEO Guidelines for Simpro Content

**Purpose:** General SEO structure and optimization rules for Simpro content.
**Use when:** Checking word count, keyword placement, headings, meta elements, readability, schema, or refresh strategy.
**Owns:** SEO formatting, on-page optimization, meta requirements, and refresh checklist guidance.
**Does not own:** Brand voice, AEO/GEO proof workflow, keyword source data, or internal-link priority.
**Source boundary:** Framework-style SEO guidance; pair with current keyword, SERP, GSC, and GA4 evidence before publication.
**Refresh cadence:** Review when SEO standards, schema policy, or content-quality gates change.
**Reference detail:** Current keyword data lives in [target-keywords.md](target-keywords.md).

---

This document outlines SEO best practices and requirements for all Simpro blog content to maximize organic search visibility and rankings.

## Content Scope Requirements

### Target Scope
- **Standard Blog Post**: cover the search intent and reader task without filler
- **Pillar Content / Comprehensive Guides**: cover the full decision, workflow, or cluster when evidence supports that depth
- **How-To Guides**: include every step, artifact, caveat, and proof source needed for the task
- **News / Updates**: stay concise and source-bound

### Important Scope Guidelines
- Set an intent/evidence-complete word target from the Reader Contract, search intent, and available proof
- Use competitor word counts as context, not a target
- If a topic requires more depth than one useful article can hold, break it into a series of related articles
- Aim for concise, focused content when it delivers the promised payoff

### Why Scope Matters
- Search engines and readers reward complete answers to the query, not filler
- Useful scope creates room for source-backed explanation, examples, links, and artifacts
- Depth signals expertise only when it adds evidence, decisions, or workflow clarity

### Quality Over Quantity
- Don't add fluff just to hit word counts
- Every section should provide genuine value
- Better to have a complete focused article than a padded one
- Overly long articles hurt user experience when sections stop advancing the promised payoff

## Keyword Optimization

### Keyword Research Requirements
Before writing any article:
1. Identify primary target keyword
2. Research search volume and difficulty
3. Analyze an intent-representative competitor sample until recurring structure and meaningful gaps are clear
4. Identify 3-5 secondary/related keywords
5. List semantic terms and related reader vocabulary

### Terminology Coverage Guidelines
- **Primary Keyword**: place naturally in critical reader-visible locations
- **Natural Integration**: never force exact-match phrases
- **Secondary Keywords**: use where they reflect real subtopics or searcher language
- **Semantic Variations**: use related terms that clarify the topic and reduce repetition
- **Stuffing Risk**: remove clustered or repetitive exact-match phrasing

### Critical Keyword Placement
Primary keyword MUST appear in:
- [ ] H1 headline (preferably near the beginning)
- [ ] First 100 words of article
- [ ] At least one relevant H2 where the exact phrase is natural
- [ ] Last paragraph / conclusion
- [ ] Meta title (within first 60 characters)
- [ ] Meta description
- [ ] URL slug

### Keyword Integration Best Practices
- **Natural language first**: Write for humans, optimize for search engines
- **Use variations**: Don't repeat exact phrase robotically
  - Example: "field service management software" → "field service platform" → "FSM software"
- **Question formats**: Include conversational variations
  - "How to schedule field technicians" vs "scheduling field technicians"
- **Semantic keywords**: Use related terms to support topical authority
  - For "job scheduling": include "dispatch", "field operations", "technician assignment"

### Keyword Stuffing (Avoid)
❌ "Field service software is important. Field service software helps contractors. Our field service software offers field service software features for field service software needs."

✅ "Field service management software gives trades contractors real-time visibility over every job — from initial quote through final invoice. A reliable platform ensures your technicians, materials, and billing stay on track without spreadsheets."

## Content Structure Requirements

### Heading Hierarchy

#### H1 (Title)
- **Only one H1 per article**
- Include primary keyword naturally
- 60 characters or less (for SERP display)
- Compelling and benefit-focused
- Should answer: "What will I learn/gain from this?"

#### H2 (Main Sections)
- Use one H2 per distinct reader question, decision, or task change; do not add sections to hit a quota
- Use the primary term in at least one relevant H2 where natural, then prefer semantic variations over repeated exact matches
- Descriptive and keyword-rich
- Logical progression through topic
- Can be standalone (readers should understand flow from H2s alone)

#### H3 (Subsections)
- Nested under H2s (never skip from H2 to H4)
- Break complex sections into digestible chunks
- Include keywords where natural
- More specific than H2s

### Blog Post Structure

```markdown
# [H1: Compelling Title with Primary Keyword]

## Introduction (use the planned section target)
- Hook: Attention-grabbing opening
- Problem: What challenge does this address?
- Promise: What will reader learn/achieve?
- Keyword in first 100 words

## [H2: Main Section 1 - Include Keyword Variation]
### [H3: Subsection if needed]
- Content depth
- Examples
- Data/statistics

## [H2: Main Section 2]
### [H3: Subsection if needed]
- Content depth
- Examples
- Data/statistics

## [H2: Main Section 3 - Include Keyword Variation]
### [H3: Subsection if needed]
- Content depth
- Examples
- Data/statistics

## [H2: Main Section 4]
[Continue with 4-7 total H2 sections]

## Conclusion (use the planned section target)
- Recap only the points needed to close the headline and introduction promise
- Include keyword
- Intent-appropriate next action based on the Reader Contract and funnel stage
- Next steps for reader
```

## Meta Elements

### Meta Title
**Requirements**:
- **Length**: 50-60 characters including the required brand suffix
- **Primary keyword**: Must be included
- **Brand suffix**: Must end with the owning brand in pipe format, such as `| Simpro` or `| ClockShark`
- **Compelling**: Should encourage clicks from SERP
- **Unique**: Different from other page titles for the same brand
- **Accurate**: Must match page content

**Format Options**:
- `[Primary Keyword]: [Benefit/Promise] | [Brand]`
- `How to [Goal] for [Audience] | [Brand]`
- `[Number] Ways to [Achieve Benefit] | [Brand]`
- `[Topic] Guide for [Audience] | [Brand]`

**Examples**:
- ✅ "Construction Draw Schedule Explained | ClockShark"
- ✅ "HVAC Service Software: Streamline Jobs & Profit | Simpro"
- ✅ "12 Best FSM Software for Trades Contractors | Simpro"
- ❌ "Field Service Tips and Tricks" (too vague, no keyword)
- ❌ "The Ultimate Comprehensive Guide to Everything About Starting Your Field Service Management Software Journey" (too long)

### Meta Description
**Requirements**:
- **Length**: 150-160 characters
- **Primary keyword**: Include naturally
- **Value proposition**: Clear benefit to reader
- **Search intent**: Accurate value or action language when it improves the result snippet
- **Complete**: Must not cut off mid-sentence
- **Compelling**: Should drive clicks from SERP

**Formula**:
```
[Problem/Question]? [Solution/Benefit]. [Unique angle]. [Optional intent-matched next step].
```

**Examples**:
- ✅ "Discover how Simpro's field service management software helps trades contractors schedule jobs, manage inventory and get paid faster. Get a demo." (155 chars)
- ✅ "Compare the 12 best FSM software platforms for HVAC, electrical and plumbing contractors. Features, pricing, and pros/cons. Updated 2026." (148 chars)
- ❌ "This is a blog post about field service software where we discuss many software-related topics." (vague and no reader value)

### URL Slug
**Requirements**:
- Include primary keyword
- Lowercase letters only
- Hyphens between words (not underscores)
- Short and descriptive (3-5 words ideal)
- No stop words unless necessary (a, the, and, of, etc.)

**Simpro URL structure by page type**:
- Blog posts: `/blog/[slug]` — e.g., `/blog/hvac-scheduling-software`
- Feature pages: `/features/[slug]` — e.g., `/features/job-management`
- Industry pages: `/industries/[vertical]-software` — e.g., `/industries/hvac-software`
  - Exception: security vertical uses `/industries/security` (not `/industries/security-software`)

**Examples**:
- ✅ `/blog/field-service-management-software`
- ✅ `/blog/hvac-scheduling-software`
- ✅ `/features/job-costing`
- ❌ `/blog/how-to-manage-field-service-jobs-in-2026-the-complete-guide` (too long)
- ❌ `/blog/post-12345` (no keywords)

## Internal Linking Strategy

### Requirements
- Use 3 to 5 internal links in standard blog posts.
- Include at least 3 internal links; aim for 4 to 5 when the extra links improve the reader journey.
- Do not exceed 7 internal links.
- Include the required down-funnel industry, solution, or feature link when the blog workflow calls for it. That required link counts as 1 of the 3 to 5 internal links unless a brief-bound override narrows the supporting-link count.
- Choose links in this order: reader usefulness, proof/source requirements, required cluster or down-funnel destination, then the 3 to 5 internal-link target. For single-trade Simpro posts, a valid exact-count override covers only the brief-selected supporting links; the matching industry page remains additive unless the brief explicitly prohibits it.
- Do not count URL fragments or `mailto:` or `tel:` links toward the internal-link total.

### Link Types to Include

#### 1. Pillar Content
- Link to main comprehensive guides on related topics
- Builds topic cluster authority
- Usually cornerstone content that fully covers a broad cluster or decision path

#### 2. Related Blog Posts
- Link to articles on related subtopics
- Creates content web
- Helps readers explore topics comprehensively

#### 3. Product/Feature Pages
- Only when contextually relevant
- Natural mention of how Simpro solves the problem
- Never forced or overly promotional

#### 4. Resource Pages
- Templates, tools, checklists
- When mentioned as solutions in content
- Provides additional value to reader

### Internal Linking Best Practices

**Anchor Text**:
- ✅ Descriptive and keyword-rich: "our complete guide to job costing for trades"
- ✅ Natural in sentence flow: "Learn more about HVAC scheduling software"
- ❌ Generic: "click here" or "read more"
- ❌ Exact match repeatedly: Always using same anchor text for same page

**Placement**:
- Within body paragraphs (most valuable)
- Natural context that adds value to reader
- Place each link where it directly supports the sentence and reader task; do not impose a per-paragraph quota
- Distributed throughout article, not clustered

**Reference**:
- Always check @context/internal-links-map.md for priority linking targets
- Ensure links are current and functional
- Link to most relevant, up-to-date content

## External Linking Strategy

### Requirements
- Use claim-fit external sources to add credibility and support claims.
- Prefer one authority link for a contiguous claim cluster. Multiple distinct authority links may share a paragraph when separate evidence-triggered claims require them; do not split or remove required proof for a per-paragraph link count. Two distinct authoritative non-owned external sources pass the standard-blog baseline. Multiple links to one source still count as one source.
- Do not add a third source only to meet a quota. Use additional sources whenever source support, regulations, public proof, specialist same-paragraph rules, or other claim-fit evidence requires them; evidence exceptions are uncapped.
- Do not count URL fragments or `mailto:` or `tel:` links toward the external-source total.

### Risk-Tiered Citation Modes

Every proof-sensitive claim must be machine-mapped to exactly one citation mode:

- `inline_required`: legal, regulatory, licensing, compliance, safety, fees, deadlines, pricing, status, material numeric, causal, comparative, benchmark, quote, customer, review, Fred, and fact-driven FAQ claims require a natural link in the same paragraph or table row. FAQ links belong in the first visible answer paragraph.
- `section_source_allowed`: lower-risk body definitions, background, and process explanations may use one mapped source in the same H2 section.
- `sidecar_only`: approved low-risk product or brand language and clearly framed low-risk editorial recommendations may remain mapped in the validation sidecar.
- `proof_not_required`: navigation, explicit opinion, or advice with no externally verifiable factual claim requires no proof. Only the policy engine may generate this mode.

Unknown or ambiguous high-risk claims fail closed to `inline_required`. Machine reviewers preserve required links and flag duplicate support, repeated destinations, and quota-only sources. `/publish-readiness` remains the sole release verdict.

### What to Link Externally
- **Statistics and data sources**: Always cite where numbers come from
- **Research and studies**: Link to original research
- **Tools and resources**: When recommending specific tools
- **Industry authorities**: Expert opinions or industry publications

### External Link Quality Standards
- **Authority**: Link to credible, well-known sources
  - ✅ Trades industry publications (ACHR News, Electrical Contractor Magazine, Plumbing & Mechanical, Security Technology Executive, HPAC Engineering, Electrical Times, Fire Protection Contractor, Field Technologies Online)
  - ✅ Research institutions and studies
  - ✅ Established media outlets
  - ❌ Random blogs with no authority
  - ❌ Spammy or low-quality sites

- **Relevance**: Links must directly support content claims
- **Freshness**: Prefer recent sources (within 1-2 years for data)
- **Functionality**: All links must work (no broken links)

### External Link Attributes
- Most external links: No special attributes needed
- Sponsored/affiliate links: Use `rel="sponsored"` or `rel="nofollow"`
- User-generated content: Use `rel="nofollow"`

## Readability Optimization

### Target Reading Level
- **Goal**: 8th-10th grade reading level (Flesch-Kincaid)
- Makes content accessible to wider audience
- Easier to scan and understand quickly

### Sentence Structure
- **Average length**: 15-20 words per sentence
- **Maximum**: 25 words (break longer sentences into two)
- **Variety**: Mix short punchy sentences with longer explanatory ones
- **Active voice**: Preferred over passive voice (80%+ active)

### Paragraph Structure
- **Length**: 2-4 sentences per paragraph
- **One idea**: Focus each paragraph on single point
- **White space**: No walls of text
- **Mobile-friendly**: Short paragraphs scan better on phones

### Formatting for Scannability
- **Subheadings**: Add when the topic or reader question changes
- **Lists**: Use bullets/numbers for sequential or multiple items
- **Bold**: Emphasize key concepts or takeaways
- **Short paragraphs**: Easier to digest
- **White space**: Makes content less intimidating

### Transition Words
Use transition words to improve flow (target: one per paragraph):
- Addition: Additionally, Furthermore, Moreover
- Contrast: However, On the other hand, Nevertheless
- Cause/Effect: Therefore, Consequently, As a result
- Example: For instance, For example, Specifically
- Time: First, Next, Finally

## Content Quality Standards

### Expertise, Authoritativeness, Trustworthiness (E-E-A-T)

#### Expertise
- Provide accurate, detailed information on job costing, scheduling, quoting, invoicing, and trades operations
- Back claims with data and examples
- Demonstrate deep understanding of trades contractor needs
- Include actionable, practical advice

#### Authoritativeness
- Cite credible sources
- Reference industry data and trends
- Include expert quotes when relevant
- Leverage Simpro's position as leading FSM software for trades contractors
- Use approved named customer proof: prefer the most relevant selector-approved source when it materially improves the article objective; if none fits, use an unnamed explanatory scene or omit the story, and keep all public details within the proof gates

#### Trustworthiness
- Be transparent and honest
- Acknowledge limitations or challenges
- Don't overpromise results
- Cite sources for all statistics and claims
- Update outdated content regularly

### Content Originality
- **Never plagiarize**: All content must be original
- **Add unique value**: What perspective or insight do we add?
- **Fresh examples**: Use current, relevant examples
- **Updated data**: Use most recent statistics available
- **Unique angle**: Differentiate from competitor content

### Factual Accuracy
- **Verify statistics**: Check all numbers and data points
- **Current information**: Ensure practices/processes are up-to-date
- **Technical accuracy**: Field service management terminology and processes must be correct
- **Simpro features**: Ensure product references are accurate

## Image Optimization

### Image Requirements
- **Relevant**: Images should support content points
- **High-quality**: Professional appearance
- **Optimized**: Compressed for fast loading
- **Mobile-friendly**: Visible and useful on small screens

### Image SEO
**File Names**:
- Descriptive and keyword-rich
- ✅ `field-service-management-scheduling-dashboard.jpg`
- ❌ `IMG_12345.jpg`

**Alt Text**:
- Describe what image shows (accessibility + SEO)
- Include keywords naturally where relevant
- 125 characters or less
- ✅ "Field service management scheduling dashboard showing technician availability and job assignments"
- ❌ "Image"

**Placement**:
- Break up long text sections
- Illustrate concepts being discussed
- After explaining concept, not before

## Featured Snippet Optimization

Featured snippets appear at position 0 in Google search results. Optimize for them when possible.

### Question-Based Snippets
- Include question as H2 heading
- Answer concisely in 40-60 words immediately after
- Use clear, direct language

**Example**:
```markdown
## What is Field Service Management Software?

Field service management (FSM) software is a platform that helps trades contractors schedule jobs, dispatch technicians, manage inventory, and invoice customers — all from one system. For electrical, HVAC, plumbing, and fire protection businesses, FSM software replaces spreadsheets and paper-based workflows with real-time job visibility.
```

### List-Based Snippets
- Use numbered or bulleted lists
- Keep items concise (1-2 sentences each)
- Include 5-8 items typically

### Table-Based Snippets
- Use HTML tables or markdown tables
- Comparison charts, pricing, specifications
- Clear headers and organized data

### Definition Snippets
- Define term in first sentence after heading
- 40-60 word clear, concise definition
- Expand with additional detail after

## Capsule Method (Direct-Answer Paragraphs)

The Capsule Method is the primary structural pattern for Simpro industry and feature pages, and strongly recommended for blog posts. It pairs every H1 and major H2 with a 50–60 word direct-answer paragraph that can be lifted verbatim as a featured snippet, PAA answer, or AI citation.

**Rules**:
- Write a 50–60 word direct-answer paragraph immediately under the H1 and each major H2
- Target 60%+ heading coverage (most H2s should have a capsule, not just some)
- The capsule answers the implicit question the heading poses — no preamble, no "In this section..."
- Detailed content, lists, and examples follow the capsule

**Template**:
```markdown
## [H2 Heading That Poses a Question or Problem]

[50–60 word direct answer that could stand alone as a snippet. Names the concept, states the key benefit, and references Simpro or the trades context. Complete sentences. No fluff.]

[Detailed supporting content, lists, examples below...]
```

**Example**:
```markdown
## How Does HVAC Scheduling Software Work?

HVAC scheduling software gives dispatchers a real-time view of technician availability, location, and workload. Managers assign jobs from a drag-and-drop calendar, field techs receive job details on mobile, and customers get automatic SMS updates. Simpro's scheduler handles bulk assignments and eliminates double-bookings without spreadsheets.

[Detailed section with feature breakdown, screenshots, etc.]
```

## Page Type Templates

### Feature Page Structure
Feature pages live at `/features/[slug]`. Use this section order:

1. **Hero** — H1 with primary keyword + Capsule (50–60 words)
2. **Proof bar** — 3–4 customer logos or a key stat
3. **Definition / what it is** — Capsule required
4. **Key challenges it solves** — 3–4 pain points, each with a Capsule
5. **How Simpro helps** — feature-by-feature with Capsules
6. **Workflow walkthrough** — step-by-step or numbered process
7. **Feature-to-problem table** — three columns: Feature | What it solves | Outcome
8. **Customer proof** — named quote + measurable outcome
9. **Outcomes table** — Before Simpro / After Simpro comparison
10. **Related links** — intent-appropriate links to related features or industries that advance the reader task
11. **CTA** — primary: Get Demo; secondary: Pricing
12. **FAQ** — up to 6 questions, each Capsule-style (direct answer first)

**Title format**: `[Primary Keyword] [Benefit Modifier] | Simpro` (50–60 chars)
**Meta format**: 140–160 chars, primary keyword front-loaded

### Industry Page Structure
Industry pages live at `/industries/[vertical]-software` (exception: security = `/industries/security`). Same section order as feature pages, with a compliance/regulation section added between customer proof and outcomes table:

- **Compliance/regulation** — relevant standards or requirements for the trade (electrical licensing, fire compliance, refrigerant handling, etc.)

### Blog Post Structure
See the Blog Post Structure template in the Content Structure Requirements section above.

## Industry Vertical Keyword Clusters

Use these as primary keyword targets and semantic clusters for vertical-specific content.

### HVAC (`/industries/hvac-software`)
- **Primary**: `hvac service software`, `hvac field service management`, `hvac job management software`
- **Secondary**: `hvac scheduling software`, `hvac dispatch software`, `hvac estimating software`, `hvac maintenance software`
- **Pain points**: paper-shuffling, long admin hours, double handling, schedule conflicts, recurring maintenance tracking
- **Customer proof**: Lorene Maher, RCR Infrastructure — customer portal, real-time job visibility

### Electrical (`/industries/electrical-software`)
- **Primary**: `electrical job management software`, `electrical contractor software`, `electrical field service software`
- **Secondary**: `electrician scheduling software`, `electrical estimating software`, `electrical project management software`
- **Pain points**: paper scheduling, no real-time staff visibility, manual quoting, materials tracking
- **Customer proof**: Jacqui Sheriff, O'Brien Electrical Granville — field staff see their day before leaving home

### Plumbing (`/industries/plumbing-software`)
- **Primary**: `plumbing service software`, `plumbing job management`, `plumbing business software`
- **Secondary**: `plumbing scheduling software`, `plumbing estimating software`, `plumbing inventory management`
- **Pain points**: missed/unbilled work, manual estimates, slow invoicing, inventory leakage
- **Customer proof**: Nikki Schembri, Tequa — "Written off debt is now less than 0.01%"

### Security (`/industries/security`)
- **Primary**: `security management software`, `security company software`, `security job management`
- **Secondary**: `security contractor software`, `security scheduling software`, `security compliance software`
- **Pain points**: compliance documentation burden, job costing accuracy, competing with larger firms on documentation quality
- **Customer proof**: Darren Thorne, DT Fire Systems — compete with bigger companies through better documentation

### Fire Protection (`/industries/fire-protection-software`)
- **Primary**: `fire protection software`, `fire protection service management`, `fire protection compliance software`
- **Secondary**: `fire protection field service software`, `fire protection scheduling`, `fire protection asset management`
- **Pain points**: compliance tracking (AS 1851 and equivalents), recurring maintenance scheduling, asset testing time
- **Customer proof**: Todd Rankin, AlarmQuest — "more positive feedback from Simpro than any other software we've used"

### Additional Verticals (no dedicated industry pages — blog content opportunities)
Solar, Elevator Service, Pest Control, Pool Service, Commercial Kitchen Equipment. Target `[vertical] field service software` as primary keyword pattern.

## Schema Markup Requirements

Implement structured data per page type. These are required, not optional.

### Blog Posts
- `BlogPosting`
- `BreadcrumbList`
- `ImageObject for the featured image or logo`
- `Organization as publisher reference only, not a separate full schema block`
- `FAQPage` plus `Question and Answer inside FAQPage` if and only if visible FAQs exist
- `VideoObject` if and only if a verified video is embedded
- `Person as author` only when a named author exists; otherwise omit both the `author` frontmatter field and Person schema

`FAQPage` and `Question and Answer inside FAQPage` are required only when visible FAQs exist. `Person as author` is required only when a named author exists. Require `VideoObject` if and only if a verified video embed exists.

If a named author is present, include `author` in frontmatter and map it to `Person as author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization as publisher reference only`, and record the decision in the BOM and validation sidecar. When `author_policy.status` is `not_provided`, first-person singular author judgment outside quotes is prohibited.

### Feature Pages
- `SoftwareApplication` or `Product`
- `BreadcrumbList`
- `Organization`
- `FAQPage` — required (feature pages must have FAQ)

### Industry Pages
- `SoftwareApplication`
- `BreadcrumbList`
- `FAQPage` — required
- `Review` / `AggregateRating` — if customer testimonials with measurable outcomes are present

### hreflang
Simpro operates in AU/NZ, UK, and US/Canada/IE markets. All pages require hreflang tags:

```html
<link rel="alternate" hreflang="en-AU" href="https://simprogroup.com/[path]/" />
<link rel="alternate" hreflang="en-NZ" href="https://simprogroup.com/[path]/" />
<link rel="alternate" hreflang="en-GB" href="https://simprogroup.com/[path]/" />
<link rel="alternate" hreflang="en-US" href="https://simprogroup.com/[path]/" />
<link rel="alternate" hreflang="en-IE" href="https://simprogroup.com/[path]/" />
<link rel="alternate" hreflang="x-default" href="https://simprogroup.com/[path]/" />
```

## Mobile Optimization

### Mobile-First Considerations
- **Short paragraphs**: 2-3 sentences max
- **Scannable**: Heavy use of subheadings and lists
- **Large fonts**: Readable without zooming
- **Tap-friendly links**: Adequate spacing
- **Fast loading**: Optimized images

## AI Search Optimization (AEO/GEO)

Use URL-derived blog best practices as idea sources only. Keep guidance that fits the Reader Contract, search intent, source evidence, and `context/aeo-geo-blog-strategy.md`; do not turn third-party advice into universal Simpro rules unless the canonical strategy already requires it.

**Source boundary:** Semrush is third-party opportunity/SERP context; GSC remains first-party performance truth. source-artifact readiness does not validate rendered CMS output; rendered canonical, indexability, schema deployment, Core Web Vitals, mobile rendering, image accessibility, and CMS link checks belong to launch QA until a separate rendered-page gate exists.

### Direct-Answer-First Principle

For answerable queries, lead with a direct answer, definition, recommendation, or clear thesis before adding background. Put limitations, assumptions, and proof boundaries after the answer.

**Rules:**
- **Answer the query directly in the first 1-2 sentences** of the article, before the narrative hook or story
- For "best/top/how" queries, state the answer (or a clear thesis) immediately
- Align the meta description with the reader task when the question can be answered accurately in 150-160 characters
- Do NOT bury the answer behind 200+ words of context, history, or definitions
- The narrative hook and APP formula still apply, but they come AFTER the direct answer sentence

**Pattern:**
> State the supported recommendation, definition, or decision first. Follow with context, proof, and comparison detail only after the reader knows the answer.

### TL;DR / Key Takeaways Block

Use a key-takeaways block when it improves reader scanning and helps the article state its conclusions early. Omit it when the format is a short opinion post, news-style update, or another format where a separate block would duplicate the intro.

**Format:**
```markdown
> **Key Takeaways**
> - [Core finding or recommendation #1]
> - [Core finding or recommendation #2]
> - [Core finding or recommendation #3]
> - [Core finding or recommendation #4 if needed]
> - [Core finding or recommendation #5 if needed]
```

**Rules:**
- 3-5 bullet points maximum
- Each bullet is a complete, standalone claim (not a teaser)
- Use approved proof-backed numbers, names, or outcomes when relevant; otherwise use concrete workflow detail rather than a vague summary
- This is NOT a table of contents — it's the article's actual conclusions up front

### Authority Signaling for AI

Apply authorship and freshness signals conditionally, and do not invent a person, review process, badge, or proof status:

- **Author policy**: Use a named author only when one is actually provided; otherwise omit the author field and Person schema
- **Reviewer/editor credit**: Use only when an actual reviewer or editor is provided and approved for public display
- **Last updated date**: Visible on the page, not just in metadata
- **Expert verification badge**: Use only when a real expert-review workflow exists and is approved for the article
- **Year in titles**: Include current year for time-sensitive topics ("Best FSM Software 2026")

These signals should be in the article's frontmatter for the WordPress publisher to render.

### One Idea Per Section

Each H2/H3 section should focus on one clear idea so humans and machines can understand the section without blending unrelated claims.

- One concept per heading
- Use bullet lists and structured formatting within sections
- Avoid long flowing paragraphs that blend multiple topics

### Embedded Media for Cross-Validation

Evaluate video only when the SERP, reader task, available assets, or section evidence makes video useful. Embedding a video is optional and must be source-fit.

Embed a public, embeddable video only when it materially supports a specific section and the sidecar/BOM records the decision. Require `VideoObject` only when a video is embedded.

### FAQ Sections as Prompt Targets

Use an FAQ section only when the editorial plan records `FAQ policy: required`. When the policy is `not_applicable`, record a non-empty rationale and omit FAQ-specific schema and gates.

- Write FAQ questions in natural prompt language (how real people ask, not SEO-speak)
- Answer each question directly in the first sentence, then expand
- Include only the useful complete questions bound to the structured AnswerSocrates artifact or, for a rewrite, its dedicated pre-picked brief section; do not target a fixed count
- Reddit, YouTube comments, and search suggestions may inform intent but cannot satisfy PAA provenance

### Content Repurposing for AI Citation Surface

Repurposing can expand distribution when the source material is proof-safe and channel-fit. Treat it as a separate distribution workflow, not as a guaranteed citation or ranking tactic.

### AI Citation Audit

For competitive topics, audit which sources AI actually cites. See `context/ai-citation-targets.md` for priority citation surfaces and the `/research-ai-citations` command for prompt-based auditing.

## Content Refresh Strategy

### When to Update Content
- Article is 12+ months old
- Statistics or data are outdated
- Processes or best practices have changed
- Competitor content has surpassed ours
- Rankings have declined
- New relevant information available

### What to Update
- Publication date or "Last Updated" date
- Statistics with current data
- Screenshots with current versions
- Examples with recent case studies
- SEO elements (keyword focus may have shifted)
- Internal links to newer content

## SEO Checklist for Every Article

Before publishing, verify:

### Content
- [ ] Word count fits the Reader Contract, search intent, and available evidence
- [ ] Primary keyword identified
- [ ] Natural terminology coverage, semantic variations, and keyword-stuffing detection checked
- [ ] 3-5 secondary keywords included
- [ ] Semantic terms naturally integrated where they improve clarity
- [ ] Provides unique value vs. competitors
- [ ] Factually accurate and current

### Structure
- [ ] One H1 with primary keyword
- [ ] Each H2 advances a distinct reader question, decision, or task change
- [ ] Primary terminology and semantic variations appear naturally in relevant H2s without a quota
- [ ] Proper H1>H2>H3 hierarchy
- [ ] Keyword in first 100 words
- [ ] Keyword in conclusion

### Page Structure
- [ ] Capsule Method: 50–60 word direct-answer paragraph under H1 and major H2s
- [ ] 60%+ heading coverage with capsules
- [ ] Schema markup implemented (correct type for page)
- [ ] hreflang tags present for AU/NZ/UK/US/IE
- [ ] URL matches correct pattern for page type (blog / features / industries)

### Meta Elements
- [ ] Meta title 50-60 characters with keyword
- [ ] Meta description 150-160 characters with accurate value or action language suited to search intent
- [ ] URL slug includes primary keyword
- [ ] All meta elements are unique

### Links
- [ ] 3-5 intent-appropriate internal links included for standard blog posts, unless a valid brief-bound override narrows the supporting-link count
- [ ] Internal links use descriptive anchor text
- [ ] Required cluster or down-funnel link is included when the workflow calls for it; for single-trade Simpro posts, include the matching industry page even when a valid exact-count override exists, unless the brief explicitly prohibits it
- [ ] Every proof-sensitive claim has a machine-assigned citation mode and claim-fit evidence placement; use at least 2 distinct authoritative non-owned sources, prohibit a quota-only third source, and add uncapped evidence when proof requires it
- [ ] All links functional (no broken links)
- [ ] Links add value to reader

### Readability
- [ ] 8th-10th grade reading level
- [ ] Average sentence length 15-20 words
- [ ] Paragraphs 2-4 sentences
- [ ] Subheadings follow topic and reader-question changes
- [ ] Lists used for scannability
- [ ] Active voice predominantly

### Images
- [ ] Relevant images included
- [ ] Descriptive file names
- [ ] Alt text with keywords
- [ ] Images optimized for web

### AI Search Optimization
- [ ] Direct answer in first 1-2 sentences (not buried)
- [ ] TL;DR / Key Takeaways block after introduction
- [ ] Meta description directly answers the target query
- [ ] FAQ questions written in natural prompt language
- [ ] Video eligibility evaluated; embed only an eligible selected video that materially supports the article
- [ ] Author policy matches the BOM: named author and Person schema when provided; otherwise both are omitted
- [ ] Last updated date included
- [ ] Year included in title for time-sensitive topics

### Quality
- [ ] No spelling or grammar errors
- [ ] Factually accurate
- [ ] Sources cited
- [ ] Brand voice maintained
- [ ] Provides actionable value
- [ ] Intent-appropriate next action; no CTA added when the Reader Contract does not call for one

## SEO Tools & Resources

### Recommended Tools
- **Keyword Research**: Ahrefs, SEMrush, Google Keyword Planner
- **Content Analysis**: Clearscope, Surfer SEO, MarketMuse
- **Readability**: Hemingway Editor, Grammarly
- **Technical SEO**: Screaming Frog, Google Search Console
- **Rank Tracking**: Ahrefs, SEMrush, Google Search Console

### Reference Resources
- Google's Search Quality Evaluator Guidelines
- Moz Beginner's Guide to SEO
- Backlinko Blog (Brian Dean)
- Search Engine Journal
- Ahrefs Blog

---

**Remember**: SEO serves the user, not the algorithm. Never sacrifice content quality, accuracy, or helpfulness for keyword optimization. The best SEO is great content that genuinely helps your audience succeed.
