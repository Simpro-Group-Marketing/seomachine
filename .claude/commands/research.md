# Research Command

Use this command to conduct comprehensive SEO keyword research and competitive analysis before writing new content.

## Usage
`/research [topic]`

## What This Command Does
1. Performs keyword research for your industry-related topics
2. Analyzes top-ranking competitor content
3. Identifies content gaps and opportunities
4. Develops unique angle for your company perspective
5. Creates detailed research brief for writing

## Process

### Keyword Research
- **Primary Keyword**: Identify main target keyword for the topic
- **Search Volume & Difficulty**: Research estimated monthly searches and competition level
- **Keyword Variations**: Find semantic variations and long-tail opportunities
- **Related Questions**: Discover what people are actually asking (People Also Ask, forums, Reddit)
- **Search Intent**: Determine if intent is informational, navigational, commercial, or transactional
- **Topic Cluster**: Identify how this topic fits into your company content clusters

### Competitive Analysis
- **Top 10 SERP Review**: Analyze the top 10 ranking articles for target keyword
- **Content Length**: Note word count of top-performing articles (benchmark target)
- **Common Themes**: What topics/sections do all top articles cover?
- **Content Gaps**: What's missing from competitor coverage?
- **Unique Angles**: What perspectives or insights are underexplored?
- **Featured Snippets**: Identify if there's a featured snippet opportunity
- **Domain Authority**: Note which competitors rank (indie blogs vs. major publications)

### Context Integration
- **Must-read context before drafting the brief**:
  - @context/brand-voice.md for Simpro voice, FY26 positioning, audience maturity archetypes, and best-fit targeting boundaries
  - @context/features.md for Simpro capabilities, add-ons, AI positioning, implementation, integrations, security, proof points, and fit boundaries
  - @context/style-guide.md for terminology, product-name rules, tone, regional language, and forbidden phrasing
  - @context/internal-links-map.md for sitemap-backed internal links
  - @context/target-keywords.md for sitemap-derived topic clusters, first-party GSC/GA4 performance signals, and remaining metric boundaries
  - @context/competitor-analysis.md for competitive differentiation and objections
  - @context/cro-best-practices.md for proof-source workflow and CTA/trust-signal guidance
- **Simpro advantage**: Identify how Simpro's product features, customer proof, and best-fit use cases naturally enhance this topic.
- **Brand alignment**: Apply Simpro's authoritative, ambitious, trades-focused, practical, outcomes-driven voice.
- **Evidence boundaries**: Do not present search volume, ranking, conversion priority, or live SERP findings as verified unless checked with GSC, GA4, DataForSEO, Ahrefs/Semrush, or live SERP review in this run.

### Simpro Industry Focus
- **Trade operator angle**: Explain how this topic affects residential and commercial trade service businesses, especially low voltage, HVAC, plumbing, electrical/data, mechanical, and multi-trade operators.
- **Best-fit boundaries**: Use the Product Marketing Best-Fit Targeting Framework. Simpro is strongest for residential, light commercial, and medium commercial work involving small jobs, recurring contracts, inspections, maintenance, repairs, installations, and mid-sized projects. Be cautious with mostly residential North America, heavy commercial, industrial, general contractors, and complex-project-dominant businesses.
- **Customer maturity**: When useful, map pain points to the Empower, Elevate, and Excel archetypes from @context/brand-voice.md.
- **Product specificity**: Bring in relevant Simpro capabilities from @context/features.md, such as real-time job costing, quote-to-cash workflows, Simpro Payments, Delight, Fast Cash, Data Feed, Digital Forms, Maintenance Planner, Takeoffs, Multi-Company, Simtrac, SMS Messaging, Sage Intacct, implementation packages, and security/infrastructure proof.
- **Pain points**: Anchor recommendations in margin visibility, cash flow, admin reduction, field adoption, recurring maintenance, asset compliance, quoting speed, inventory, and scaling without chaos.

### Content Planning
- **Recommended Structure**: Outline H2 and H3 headings based on research
- **Content Depth**: Determine target word count (typically 2000-3000+ for SEO)
- **Supporting Evidence**: Identify statistics, studies, or data to include
- **Expert Sources**: Find industry experts or quotes to reference
- **Visual Opportunities**: Suggest images, screenshots, or graphics needed
- **Internal Links**: Map 3-5 key your company pages to link to (from @context/internal-links-map.md)
- **External Authority**: Identify 2-3 authoritative external sources to link

### Hook Development
- **Introduction Angle**: Compelling way to open the article
- **Value Proposition**: Clear benefit reader will get from article
- **Contrarian Elements**: Any unexpected perspectives to explore
- **Story Opportunities**: Real examples or case studies to feature

## Output
Provides a comprehensive research brief with:

### 1. SEO Foundation
- **Primary Keyword**: [keyword] (volume, difficulty)
- **Secondary Keywords**: 3-5 related keywords and variations
- **Target Word Count**: Minimum words needed to compete
- **Featured Snippet Opportunity**: Yes/No, format (paragraph, list, table)

### 2. Competitive Landscape
- **Top 3 Competitor Articles**: URLs and key takeaways from each
- **Common Sections**: Must-cover topics based on SERP analysis
- **Content Gaps**: Opportunities to provide unique value
- **Differentiation Strategy**: How your company can stand out

### 3. Recommended Outline
```
H1: [Optimized headline with primary keyword]

Introduction
- Hook
- Problem statement
- Value proposition

H2: [Main section 1]
H3: [Subsection]
H3: [Subsection]

H2: [Main section 2]
...

Conclusion
- Key takeaways
- Call to action
```

### 4. Supporting Elements
- **Statistics to Include**: 5-7 relevant data points with sources
- **Expert Quotes**: Potential sources or existing quotes
- **Examples/Case Studies**: Real Simpro customer outcomes or relevant trade-service scenarios to feature
- **Visual Suggestions**: Screenshots, charts, or graphics needed

### 5. Internal Linking Strategy
- **Pillar Page**: Main your company pillar content to link to
- **Related Articles**: 2-4 relevant blog posts to link
- **Product Pages**: your company features to naturally mention
- **Resource Pages**: Tools or guides to reference

### 6. Meta Elements Preview
- **Meta Title**: Draft optimized title (50-60 characters)
- **Meta Description**: Draft compelling description (150-160 characters)
- **URL Slug**: Recommended URL structure

## File Management
After completing the research, automatically save the brief to:
- **File Location**: `research/brief-[topic-slug]-[YYYY-MM-DD].md`
- **File Format**: Markdown with clear sections and structured data
- **Naming Convention**: Use lowercase, hyphenated topic slug and current date

Example: `research/brief-podcast-editing-software-2025-10-15.md`

## Next Steps
The research brief serves as the foundation for:
1. Running `/write [topic]` to create the optimized article
2. Reference material for maintaining SEO focus throughout writing
3. Checklist to ensure all competitive gaps are addressed

This ensures every article is built on solid SEO research and strategic competitive positioning.
