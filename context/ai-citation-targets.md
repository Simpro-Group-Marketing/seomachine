# AI Citation Targets

When AI tools (ChatGPT, Perplexity, Gemini, Claude) recommend products or services, they pull from sources across the web. This file tracks the platforms, directories, and content surfaces where your brand needs to be present and well-represented to maximize AI citation frequency.

## Simpro AI/FSM Citation Baseline

**Source boundary**: This section uses `simpro-seo-dashboard.html` as a strategy cross-check and GSC as first-party demand signal. The dashboard states its traffic metrics are DataForSEO-estimated and that no GSC or GA4 data was used. Treat AI Overview findings as March 2026 SERP evidence that should be rechecked before campaign launch.

**Current known signals**:
- The dashboard reports Simpro was not mentioned in AI Overviews checked for `field service management software`, `best field service management software`, and `hvac software`.
- US GSC shows AI field-service semantic variants produced 4 clicks and 6,940 impressions from 2026-02-20 to 2026-05-20, with an impression-weighted average position of 13.5.
- Exact US GSC terms are still early: `AI field service software` had 0 clicks / 146 impressions / avg position 16.1, and `AI for field service` had 0 clicks / 281 impressions / avg position 12.0.

**Priority prompt families to monitor**:
- best field service management software
- field service management software for trades
- AI field service software
- AI for field service management
- AI scheduling software for field service
- AI dispatch software for HVAC, plumbing, and electrical contractors
- best HVAC software
- best plumbing software
- best electrical contractor software
- ServiceTitan alternatives for commercial contractors

## How This File Is Used

- **Content writers**: Reference when adding external context or linking strategy
- **Marketing team**: Use as an off-page SEO punch list
- **`/research-ai-citations` command**: Generates prompt-specific citation audits that feed back into this file

## Priority Citation Surfaces

### Tier 1: Software Review Directories (Highest AI Citation Frequency)

These directories are cited most frequently when AI tools recommend SaaS products:

| Platform | Listed? | Priority Action |
|----------|---------|-----------------|
| G2 | Verify | Maintain reviews, respond to feedback, keep feature list current |
| Capterra | Verify | Same as G2 |
| TrustRadius | Verify | Especially important for enterprise/B2B queries |
| Product Hunt | Verify | Historical listing matters for "best new tools" queries |
| AlternativeTo | Verify | Critical for "alternatives to [competitor]" prompts |
| Slant | Verify | Comparison-focused, frequently cited in "vs" queries |

### Tier 2: Industry-Specific Directories

Customize this section for your niche. Examples:

| Platform | Listed? | Priority Action |
|----------|---------|-----------------|
| [Niche directory 1] | Verify | [Specific action] |
| [Niche directory 2] | Verify | [Specific action] |
| [Industry publication] | Verify | [Specific action] |

### Tier 3: Listicle Articles (Outreach Targets)

AI tools heavily cite "best X" listicle articles. These are the types of articles where your brand should appear:

- "Best [your category] Tools [Year]" articles on major tech/media sites
- "Best [your category] for Beginners" roundups
- "[Your category] Comparison" articles
- "[Your category] for [specific use case]" roundups

**Outreach strategy**: Identify the author, provide value (updated pricing, new features, unique angle), and request inclusion or update.

### Tier 4: Social/Community Platforms

AI tools pull from these surfaces, especially for recent recommendations:

| Platform | Strategy |
|----------|----------|
| **Reddit** (your niche subreddits) | Comment on existing high-upvote threads with genuine value. Comments on popular threads outperform new posts. Use F5Bot to track keyword mentions. |
| **Medium** | Repurpose blog articles as Medium posts with attribution back |
| **LinkedIn Pulse** | Repurpose articles, especially for B2B use cases |
| **Quora** | Answer relevant questions with genuine expertise |
| **YouTube** | Video content gets cross-referenced by Perplexity and Gemini especially |

### Tier 5: Reputation Platforms

AI models read and synthesize review sentiment when making recommendations:

| Platform | Action |
|----------|--------|
| Google Business Profile | Maintain if applicable |
| Trustpilot | Encourage satisfied customers to review |
| App stores / plugin directories | Ratings matter for AI recommendations |

## Prompt Clusters to Monitor

Customize these for your business. These are high-commercial-intent prompt categories where your brand should appear in AI responses:

### General
- "best [your product category]"
- "best [your category] for beginners"
- "cheapest [your category]"
- "[your category] comparison"

### Feature-Specific
- "best [your category] with [key feature]"
- "[your category] that supports [capability]"

### Use-Case Specific
- "best [your category] for [industry/niche]"
- "[your category] for [specific scenario]"

### Migration/Switching
- "[competitor] alternative"
- "switch from [competitor]"
- "[competitor A] vs [competitor B]"

### Pricing
- "[your category] pricing comparison"
- "[your category] free trial"

## Updating This File

Run `/research-ai-citations [topic]` to generate a prompt-specific audit. The output will include which sources AI actually cites for that topic cluster, and whether your brand appears. Use findings to update the tables above.

Review quarterly: directories change, new listicles rank, and AI citation patterns shift.
