# Optimize Command

Use this command to perform a final SEO optimization pass on completed articles before publishing.

## Usage
`/optimize [article file]`

## What This Command Does
1. Performs comprehensive SEO audit of article
2. Fine-tunes keyword placement and density
3. Optimizes meta elements for SERP performance
4. Validates internal and external links
5. Ensures all SEO best practices are met

## Process

### Validation Sidecar And Public Artifact Gate

Before returning `Ready`, confirm proof-only infrastructure lives in a validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`, not in the blog copy. The article file must not include an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan.

Preferred publish readiness command:
```bash
python data_sources/modules/publish_readiness.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

```bash
python data_sources/modules/public_artifact_guard.py [article-file] --fail-on error
```

Run proof-aware gates with `--proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` so the guards can read proof maps and proof packs without exposing them in public copy.

### URL Validation Gate

Before returning `Ready`, run URL validation:
```bash
python data_sources/modules/url_validator.py [article-file] --fail-on unresolved
```

URL validation blocks unresolved and manual-review links before publish readiness. It confirms destinations resolve; it does not prove the page supports the claim, so Source Map and E-E-A-T proof review still verify claim support.

### Metric Proof Pack Gate

Before returning `Ready`, run Metric Proof Pack guard:
```bash
python data_sources/modules/metric_proof_pack_guard.py [article-file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for the Metric Proof Pack policy and evidence boundary.

### Numeric Claim Source Gate

Before returning `Ready`, run numeric claim source guard:
```bash
python data_sources/modules/numeric_claim_source_guard.py [article-file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for numeric-claim proof requirements.

### FAQ Proof Gate

Before returning `Ready`, run FAQ proof guard:
```bash
python data_sources/modules/faq_proof_guard.py [article-file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for FAQ proof requirements.

### PAA Provenance Gate

Before returning `Ready`, run PAA provenance guard:
```bash
python data_sources/modules/paa_provenance_guard.py [article-file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

PAA provenance requires every FAQ question to match a saved PAA/FAQ source artifact when an FAQ section is present. Use `PAA/FAQ Provenance` with Source, Artifact, and Selected questions; see `context/aeo-geo-blog-strategy.md` for the full source-label and proof-boundary policy.

### Source Support Gate

Before returning `Ready`, run source support guard:
```bash
python data_sources/modules/source_support_guard.py [article-file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for source support, Approved quote, testimonial, and named customer metric boundaries.

### Customer Proof Diversity Gate

Before returning `Ready`, run customer proof diversity guard:
```bash
python data_sources/modules/customer_proof_diversity_guard.py [article-file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Run or consult `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme --limit 10` before selecting proof. The validation sidecar needs the generated selector-first `Customer Proof Slate`; use `context/aeo-geo-blog-strategy.md` for the full customer proof policy.

Run or consult `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates.

Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.

### Review Story Identity Gate

For review-derived public copy, consult the selector with `--require-eeat-story --proof-role experience_story`; use `context/aeo-geo-blog-strategy.md` for Review Story Selection, Review Site Theme Selection, Capterra theme, exact-quote, rating, and metric boundaries.

Use a proof-backed customer/review POV only when it improves the article objective. If no actual person or business POV fits, omit the story. Fictional named personas are prohibited; unnamed workflow scenarios are explanatory only and do not count as E-E-A-T.

Before returning `Ready`, run review story identity guard:
```bash
python data_sources/modules/review_story_identity_guard.py [article-file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Exact review wording still requires Approved quote handling per `context/aeo-geo-blog-strategy.md`.

### Content Audit

#### Keyword Analysis
- **Primary Keyword Density**: Check 1-2% density throughout article
- **Keyword Placement Check**:
  - [ ] In H1 headline
  - [ ] In first 100 words
  - [ ] In at least 2-3 H2 headings
  - [ ] In meta title
  - [ ] In meta description
  - [ ] In URL slug
- **Semantic Variations**: Verify related keywords are used naturally
- **Keyword Stuffing**: Ensure no over-optimization or unnatural usage
- **LSI Keywords**: Confirm latent semantic keywords are present

#### Heading Structure
- **H1**: Only one H1, includes primary keyword
- **H2s**: 4-7 H2 sections, at least 2-3 with keyword variations
- **H3s**: Proper nesting under H2s, descriptive and keyword-rich
- **Hierarchy**: Logical progression, no skipped levels (H1→H3)
- **Length**: Headings are descriptive but concise

#### Content Quality
- **Word Count**: Minimum 2000 words (2500-3000+ preferred)
- **Paragraph Length**: Average 2-4 sentences, no walls of text
- **Sentence Length**: Varied, averaging under 25 words
- **Readability Score**: 8th-10th grade level (Flesch-Kincaid)
- **Active Voice**: Predominantly active voice usage
- **Transition Words**: Smooth flow between sections
- **List Usage**: Bullets/numbers for scannability
- **Formatting**: Bold, italics used appropriately for emphasis

### Link Optimization

#### Internal Links (3-5+ required)
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

#### External Links (2-3+ required)
- **Quantity**: Count external authority links
- **Authority**: Verify links are to credible, authoritative sources
- **Relevance**: Ensure external links support content claims
- **Freshness**: Check that linked sources are current
- **Broken Links**: Test all external links
- **Link Attributes**: Verify appropriate use of nofollow where needed

**Recommendations**:
- Additional authoritative sources to link
- Outdated links to replace
- Statistics that need source citations

### Meta Element Optimization

#### Meta Title
- **Length**: 50-60 characters (check current length)
- **Keyword**: Primary keyword included naturally
- **Compelling**: Attention-grabbing and click-worthy
- **Brand**: Consider adding "| your company" if space allows
- **Uniqueness**: Distinct from other your company page titles

**Provide**:
- Current meta title analysis
- 3-5 optimized alternative options
- Recommended best choice

#### Meta Description
- **Length**: 150-160 characters (check current length)
- **Keyword**: Primary keyword included
- **Value Prop**: Clear benefit to reader
- **Call-to-Action**: Includes action phrase (learn, discover, find out)
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
- **Brand Voice**: Verify alignment with @context/brand-voice.md
- **Style Guide**: Check adherence to @context/style-guide.md
- **Messaging**: Ensure messaging reflects your company positioning
- **Product Mentions**: Natural integration of your company features
- **CTA**: Appropriate call-to-action for article intent

#### User Experience
- **Introduction**: Compelling hook that draws reader in
- **Value Delivery**: Article delivers on headline promise
- **Actionability**: Practical takeaways and next steps
- **Conclusion**: Strong summary and clear CTA
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
1. [Option 1] (58 chars)
2. [Option 2] (59 chars)
3. [Option 3] (60 chars)

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
- H2 sections: 2/5 (need 1-2 more)
- Body paragraphs: 15 instances (1.5% density) ✓
- Conclusion: ✓
- Meta title: ✓
- Meta description: ✓

### 7. Final Checklist
- [ ] Primary keyword in H1
- [ ] Primary keyword in first 100 words
- [ ] Primary keyword in 2+ H2 headings
- [ ] Keyword density 1-2%
- [ ] 3-5+ internal links included
- [ ] 2-3+ external authority links
- [ ] Meta title 50-60 characters
- [ ] Meta description 150-160 characters
- [ ] Article 2000+ words
- [ ] Proper H1/H2/H3 hierarchy
- [ ] Readability optimized (8th-10th grade)
- [ ] Images have alt text
- [ ] CTA included
- [ ] Brand voice maintained
- [ ] No broken links
- [ ] URL validation passed with `python data_sources/modules/url_validator.py [article-file] --fail-on unresolved`
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
- **Content Length Comparison**: Compare word count against top 10 SERP competitors
- **Readability Score**: Flesch Reading Ease, Flesch-Kincaid Grade Level, sentence structure analysis
- **SEO Quality Rating**: Overall score (0-100) with category breakdowns and specific recommendations

## Publishing Decision
Based on optimization score:
- **90-100**: Excellent - publish immediately
- **80-89**: Good - minor tweaks recommended but publishable
- **70-79**: Fair - address priority fixes before publishing
- **Below 70**: Needs work - significant improvements required

This ensures every article meets your company quality standards and SEO best practices before going live.
