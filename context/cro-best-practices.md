# CRO Best Practices for Landing Pages

Conversion Rate Optimization guidelines for landing pages.

> **Internal CRO review update**: Treat these notes as more specific than generic rules where they conflict: two-word CTA labels have historically outperformed CTA labels of three or more words; Sales-required form fields vary by brand; CTA font choices are brand-directed; PPC pages should avoid exit points; lower-volume tests may need directional signals or leading indicators instead of fixed conversion minimums; seasonality can affect conversion results.

> **Source note**: Simpro does not maintain one fixed CRO playbook because the working model is experimentation-led. Treat the `[2023-2026] Experiments Summary & Overview` Google Sheet (`1wVrZ-R53tQRtUKuoKNp5NQYx05yO3uT-di-aOew_Ukw`) as the structured source of truth for completed experiments, and use the CRO consultant skill for page- or element-specific recommendations because it bridges historical experiment data into practical guidance. Use the `[2025] Experiments Summary & Overview` deck (`1f4E7yay4s-SsVUFcg-EZ06aB31d2MADJ3oNfQrEGnXo`) and `[2026] Experiments Summary & Overview` deck (`1KqRRORZQS0OzDy4NJoqMjAtZqERDstVwnMfeiYTW3kg`) as annual narrative summaries and links to full reports. Use the `Web Strategy: Team KPIs` Google Sheet (`1wC_8aSSoOAzQ6i8TtJq_kTIoUsjCEjWKSKbh9tS203M`) for baseline conversion-rate context through March 2026. Product Marketing's Customer Quote Matrix, Customer Stories deck, and Customer Advocacy overview are proof-source assets, not tested CRO guidance. The rules below combine framework-generic best practices with the internal CRO review notes above. **Apply them through Simpro's brand voice** (see `brand-voice.md`) — every headline should be specific, every CTA should match the funnel stage, every trust signal should be a named customer or named number from `features.md`.

---

## Simpro-Specific CRO Principles

These overlay the generic CRO rules below — when in conflict, the Simpro-specific rule wins.

### Use the experiment system as the playbook
There is no single static Simpro CRO playbook. Use the experimentation system in this order:

1. Check the `[2023-2026] Experiments Summary & Overview` workbook for completed experiments. Visible tabs include `2026_Experiments_Raw`, `2026_KPI_Summary`, `2025_Experiments_Raw`, `2025_KPI_Summary`, `2024_Experiments_Raw`, `2024_KPI_Summary`, `2023_Experiments_Raw`, `2023_KPI_Summary`, and `Data_Dictionary`.
2. Use the 2025 and 2026 summary decks for executive summaries, strategic takeaways, and links to full reports. The decks explicitly warn that a successful experiment on one page does not guarantee success on other pages or brands.
3. Query the CRO consultant skill for the specific page, template, CTA, form, proof block, or page element being evaluated.
4. Use the KPI workbook for baseline conversion-rate context by brand and month. Visible brand monthly tabs include `Simpro - Monthly`, `Clockshark - Monthly`, `BigChange - Monthly`, and `Aroflo - Monthly`.
5. Pull form completion rates from HubSpot, not the KPI sheet. Primary demo signups across brand pages generally use the same universal forms in each brand's HubSpot instance, so form analysis should identify the brand, form ID/name, page URL, traffic source, and time period.
6. Use generic CRO heuristics below only after the experiment sheet, annual summary decks, KPI baseline, HubSpot form data, and CRO consultant skill output have been checked.

### Annual deck takeaways
The annual decks are useful for directional patterns and full-report navigation. They should not be treated as one-size-fits-all rules.

- The 2025 deck identifies Mutiny as the experimentation platform and notes that ended experiments include buttons to detailed reports, preview links, and Asana tasks.
- The 2026 deck notes the February 2026 migration from Mutiny to VWO and uses Mutiny or VWO depending on experiment timing.
- Both decks include a conversion-depreciation warning: audience adaptation, seasonality, technical changes, competition, and interactions between multiple shipped experiments can change results after launch.
- The 2025 deck's Q1 summary highlights that many Simpro experiments had no significant MQL change but still created additive value through data quality, engagement, and content surfacing.
- A 2025 Simpro pricing-page add-ons widget increased pageviews per session by 58% and session length by 20%.
- A 2025 AroFlo demo-form reduction and above-the-fold fit test increased demo request form submission conversion rates by 30.82%.
- A 2026 product-tour header and footer removal test increased `/demo` page view rates by 16%, demo request form submission rates by 4%, and MQL conversion rates by 31%.

### Lead with named outcomes, not feature claims
The Simpro evidence library is exceptional and underused in CRO copy. Every above-the-fold hero should be in arm's reach of at least one of these:
- **60% increase in profit margin** (Shaffer Beacon Mechanical)
- **10x faster job estimates** (BGE Digital)
- **$750K+ admin cost savings over 5 years** (McCarthy Plumbing Group)
- **50% faster payments** (TEAMWired)
- **80% less time on POs** (James Frew)
- **10x revenue growth in 6 years, 6x EBITDA exit** (Foster Plumbing)

A generic "Grow your business with Simpro" hero will lose to "How Foster Plumbing grew 10x in 6 years with Simpro" — every time.

Product Marketing guidance: landing page copy should be value-based first. Feature claims are strongest when they are tied to a business outcome, customer proof point, or measurable operational improvement.

### Match the CTA to the funnel stage
- **Top-of-funnel** (blog readers, broad SEO): "View Stories" / "Watch Demo" / "Read Guide"
- **Mid-funnel** (comparison pages, alternatives, /vs/ pages): "Compare Options" / "Calculate ROI" / "Book Demo"
- **Bottom-of-funnel** (pricing, product pages, return visitors): "Book Demo" / "Talk Sales"

### Keep primary CTA labels short
Internal test history favors two-word CTA labels over labels of three or more words. Use the surrounding headline, subcopy, helper text, or risk reversal to carry specificity instead of making the button label do all the work.

Good button-label patterns:
- "Book Demo"
- "Start Trial"
- "View Pricing"
- "Watch Demo"
- "Compare Plans"

Avoid using long button labels unless legal, routing, or product requirements make the extra words necessary.

### PPC pages should be closed conversion paths
PPC landing pages should not include unnecessary exit points. Simpro has seen conversion declines when paid pages included one or two exits, including a clickable logo in the top-left corner and another link elsewhere on the page. Paid traffic pages should keep users focused on the conversion action unless a required compliance, privacy, or consent link is needed.

### Trust signals: scale + named customers
Above-the-fold trust signals that work for Simpro:
- 250,000+ users / 8,500+ customers / 20+ years (scale)
- Named customer logos in the relevant trade (relevance)
- A specific outcome quote from a similar-trade customer (proof)
- "Trusted in [US / AU / NZ / UK]" — geographic credibility

### Proof-source workflow
- Use the **Global Customer Quote Matrix** first when a page needs a quote, because it is tagged by country, state, industry, business name, theme, customer archetype, quote, and video availability.
- Match quote selection to the page's trade, region, buying stage, and archetype. A mature multi-branch operator should not get the same proof as a small residential business moving off paper.
- Use **Customer Stories** and **References** assets to verify that a quote or metric has a story path before promoting it in hero copy.
- Keep Customer Advocacy program metrics internal unless the brief is explicitly about advocacy operations. They explain the reference program, not the software value proposition.

### Headline patterns that fit Simpro voice
- **Outcome + customer**: "How [Customer] [Outcome] with Simpro"
- **Pillar + promise**: "Double Your Profits, Not Your Hours"
- **Pillar + concrete claim**: "Real-time job costing. Real-time profitability."
- **Question that opens to a strong answer**: "Outgrowing Housecall Pro? Here's what comes next."

### Anti-patterns to avoid (Simpro-specific)
- "World-class," "innovative," "cutting-edge" — every category vendor uses these
- "Streamline your operations" — every CRM/FSM uses this
- Generic stock photos of trades workers — use real customer photos, real software screenshots
- Unvalidated form complexity that works against the required sales-qualification flow
- Carousel heroes — pick the strongest hero and stand behind it

Source boundary: do not convert one winning experiment into a universal rule without checking page type, traffic source, brand, audience, seasonality, sample size, and downstream lead quality.

---

## Above-the-Fold Rules

### The 5-Second Test
Visitors should understand these within 5 seconds of landing:
1. **What** you offer
2. **Who** it's for
3. **Why** they should care
4. **What** to do next (CTA)

### Required Elements
| Element | Purpose | Guidelines |
|---------|---------|------------|
| Headline | Grab attention | Benefit-focused, <70 chars |
| Subheadline | Clarify value | Expand on headline, 1-2 sentences |
| CTA Button | Drive action | High contrast, action verb |
| Trust Signal | Build credibility | Customer count, rating, or logo |

### Above-the-Fold Don'ts
- No sliders or carousels
- No multiple competing CTAs
- No walls of text
- No autoplay videos with sound
- No navigation that distracts from CTA

---

## Headline Best Practices

### Headline Formulas That Convert

**Problem-Solution:**
- "Stop [Pain Point]. Start [Desired Outcome]."
- "No More [Problem]. Just [Solution]."

**Benefit-First:**
- "[Achieve Outcome] Without [Sacrifice]"
- "The [Fastest/Easiest/Only] Way to [Outcome]"

**Social Proof:**
- "Join [Number] [Audience] Who [Achieved Outcome]"
- "Why [Number] [Audience] Switched to [Product]"

**Question:**
- "Ready to [Achieve Outcome]?"
- "What if You Could [Desired Outcome]?"

### Headline Testing Checklist
- [ ] Contains the primary benefit
- [ ] Under 70 characters (mobile-friendly)
- [ ] Uses "you" or implies the reader
- [ ] Specific (not vague or generic)
- [ ] Creates curiosity or urgency

### Weak Headlines to Avoid
- "Welcome to [Company]"
- "The Best [Product] Solution"
- "Everything You Need"
- "We Help You [Generic Verb]"
- Starting with "Our" or "We"

---

## CTA Best Practices

### CTA Text Guidelines

**By Conversion Goal:**

| Goal | Strong CTAs | Avoid |
|------|-------------|-------|
| Trial | "Start Trial" | "Sign Up" |
| Trial | "Try Free" | "Submit" |
| Trial | "Create Account" | "Register" |
| Demo | "Book Demo" | "Contact Us" |
| Demo | "Schedule Call" | "Get in Touch" |
| Demo | "Watch Demo" | "Learn More" |
| Lead | "Download Guide" | "Submit" |
| Lead | "Get Access" | "Subscribe" |
| Lead | "View Checklist" | "Send" |

### CTA Button Formula
**[Action Verb] + [Benefit/Object]**

Examples:
- "Start" + "Trial"
- "Get" + "Access"
- "Book" + "Demo"

Add urgency or detail near the button, not inside the primary button label, unless a longer label is required.

### CTA Placement Strategy
1. **Hero CTA** (0-20% of page): Primary, most prominent
2. **Post-Problem CTA** (30-40%): After establishing pain
3. **Post-Proof CTA** (60-70%): After testimonials
4. **Closing CTA** (90-100%): Final push with risk reversal

### CTA Visual Best Practices
- **Color**: High contrast with background
- **Size**: Large enough to tap (44x44px minimum)
- **Whitespace**: Breathing room around button
- **Consistency**: Same style throughout page
- **Mobile**: Full-width on small screens
- **Font**: Use only brand-approved CTA fonts. Font choice is brand-driven, and Rachel Shannon has directed that CTA fonts stay within the approved brand set.

---

## Trust Signal Hierarchy

### Strongest (Use First)
1. **Specific Results**: "Grew audience by 300%"
2. **Named Testimonials**: "Sarah M., The Creative Hour"
3. **Customer Count with Context**: "50,000+ customers"

### Strong
4. **Star Ratings**: "4.9/5 on G2"
5. **Media Logos**: "As seen in..."
6. **Customer Logos**: Enterprise/recognizable brands

### Supporting
7. **Awards/Certifications**: "Best in Category 2024"
8. **Partnerships**: "Official Partner"
9. **Security Badges**: For payment/data collection pages

### Trust Signal Placement
| Location | Best Trust Signal |
|----------|-------------------|
| Hero (above fold) | Customer count or rating |
| After problem section | Mini-story with outcome |
| Middle of page | Full testimonials (2-3) |
| Near CTA | Risk reversal statement |
| Footer | Security/privacy badges |

---

## Risk Reversal Tactics

### For Free Trial
- "No credit card required"
- "Cancel anytime"
- "Full access for [X] days"
- "No commitment"
- "Set up in under 5 minutes"

### For Demo Requests
- "No pressure, no hard sell"
- "Just [X] minutes of your time"
- "Get your questions answered"
- "See if we're a fit"

### For Lead Capture
- "No spam, ever"
- "Unsubscribe anytime"
- "Instant download"
- "Free, no strings attached"

### Risk Reversal Placement
Always place risk reversal **directly below or beside the CTA button**.

---

## Objection Handling

### Common Objections & Responses

**"It's too expensive"**
- Lead with free trial
- Show ROI/value
- Compare to competitor costs
- Highlight what's included

**"It looks complicated"**
- "Set up in 5 minutes"
- Show simple 3-step process
- Include "no technical skills needed"

**"I'm not ready"**
- Use urgency sparingly
- Offer lead magnet alternative
- Provide "learn more" secondary CTA

**"I don't know if it's right for me"**
- Testimonials from similar users
- Specific use case sections
- "Perfect for [audience]" positioning

**"Can I trust you?"**
- Customer count
- Years in business
- Known customer logos
- Money-back guarantee

---

## Form Optimization

### Form measurement source
Form completion rates should be pulled from HubSpot. Most primary demo signups across Simpro Group brand pages use the same universal forms in each brand's HubSpot instance, so form-performance analysis should compare the same form across page type, source, campaign, and brand before attributing a change to page copy or layout.

### Field Reduction
Every additional field can reduce completion, but field reduction does not override Sales-required lead qualification fields. Optimize the order, grouping, labels, and step structure before removing fields that Sales needs.

### Why added fields are being tested
Historically, added form fields have reduced engagement, so field expansion should be treated cautiously and tested rather than assumed to be harmless. Most brands now use a `/quickquestions` post-demo form to collect extra qualification details without blocking the main lead flow. The current push for more fields comes from a pipeline-quality constraint: after org and leadership restructuring removed BDR filtering from the lead path, Sales became more sensitive to both lead volume and lead quality. When Sales requests added fields, the test should measure the tradeoff between lower form engagement and better lead qualification, not form completion alone.

**Sales-Required Fields by Brand:**
| Brand | Required Fields | Current Notes |
|-------|-----------------|---------------|
| ClockShark | First name, last name, work email, password, company name, industry type, work phone number, number of users, country, state/province | Start with first name, last name, work email, and password. Then collect company name, industry type, work phone number, number of users, country, and state/province. Bryce Nill is testing signup-flow structures that break the flow into steps. |
| Simpro | First name, last name, work email, phone number, company name | Paid pages will likely roll out company size based on the current experiment. An organic experiment should follow to determine whether organic pages use the same field. |
| BigChange | First name, phone number, company mail, business email address | Keep the required field names aligned with Sales guidance before launch. |
| AroFlo | Work email, first name, phone number, state/region, company name | Maintain region-specific field naming where required. |

Some regions also require marketing email opt-in options. Confirm regional opt-in requirements before publishing or testing a form.

### Form Best Practices
- Single column layout
- Clear labels above fields
- Helpful placeholder text
- Real-time validation
- Mobile-friendly input types
- Progress indicator for multi-step
- Break longer forms into clear steps when the required field set is too large for one comfortable screen
- Preserve Sales-required qualification fields unless Sales approves a test that removes or delays them

### Form Placement
- Above the fold for PPC
- After value establishment for SEO
- Never at the very bottom
- On PPC pages, keep the page focused on the form or CTA and avoid nonessential exits

---

## Page Speed Impact

### Conversion Impact
- 1 second delay = 7% conversion drop
- 3 second load = 40% abandonment
- Mobile users expect <3 seconds

### Quick Wins
- Compress images (WebP format)
- Minimize JavaScript
- Use lazy loading for below-fold
- Optimize fonts, while keeping CTA fonts within the approved brand set
- Enable browser caching

---

## Mobile Optimization

### Mobile-First Rules
- 60%+ traffic is mobile
- Design for mobile, then adapt for desktop
- Touch-friendly tap targets (44x44px)
- Readable without zooming (16px+ font)

### Mobile CTA Guidelines
- Full-width buttons
- Sticky CTA on scroll (optional)
- Phone number click-to-call
- Simplified forms

### Mobile Content Rules
- Shorter headlines (<60 chars)
- Front-load key information
- Accordion FAQs to save space
- Minimal navigation

---

## A/B Testing Priorities

### High Impact (Test First)
1. Headline
2. CTA text
3. CTA color/size
4. Hero image/video
5. Social proof placement

### Medium Impact
6. Subheadline
7. Form length
8. Testimonial selection
9. Pricing presentation
10. Risk reversal text

### Low Impact (Test Later)
11. Button shape
12. Minor font treatment within the approved brand set
13. Footer content
14. Image style
15. Color scheme

### Testing Rules
- One variable at a time
- No fixed minimum conversions per variant: some websites and pages will not reach a hard threshold within a reasonable time
- Use statistically clean test rules where volume allows
- On lower-volume pages, document directional signals, leading indicators, sample size, and the reason the decision is still useful
- Run long enough to cover meaningful traffic patterns and account for seasonality
- Record seasonality, traffic-source mix, offer changes, and major page changes before reading the result

---

## Conversion Goal Benchmarks

Use the `Web Strategy: Team KPIs` workbook as the internal baseline source. It has brand monthly tabs and was identified as current through March 2026. Use these internal baselines before generic industry averages, and segment by brand, traffic source, page type, campaign, and form where possible.

For form-level conversion or completion rates, use HubSpot because the primary demo forms are managed there. The KPI workbook can contextualize site and team performance, but it should not replace HubSpot form analytics for field-level or form-level decisions.

### Industry Averages
Use these only as fallback context when an internal KPI baseline is unavailable or when explaining general CRO ranges to a non-Simpro stakeholder.

| Goal | Average | Good | Excellent |
|------|---------|------|-----------|
| Free Trial | 3-5% | 7-10% | 15%+ |
| Demo Request | 2-4% | 5-8% | 10%+ |
| Lead Capture | 5-10% | 15-25% | 30%+ |

### Factors That Affect Conversion
- Traffic source quality
- Brand awareness
- Price point
- Competition
- Offer strength
- Page experience
- Seasonality

---

## Psychology Principles

### Scarcity
- Limited time offers
- Limited spots available
- Stock/availability indicators
- Use sparingly and honestly

### Social Proof
- "Join 50,000+ customers"
- Testimonials with faces
- Live user counts
- Recent signup notifications

### Authority
- Expert endorsements
- Media mentions
- Certifications
- Years of experience

### Reciprocity
- Free trial first
- Free resources/guides
- Helpful content before ask

### Urgency
- Time-limited offers
- "Start today" messaging
- Countdown timers (use carefully)
- Season/event-based hooks

---

## Landing Page Audit Checklist

### Above the Fold
- [ ] Clear, benefit-focused headline
- [ ] Value proposition in 5 seconds
- [ ] Prominent CTA button
- [ ] Trust signal visible
- [ ] No distracting elements

### Content
- [ ] Value-based copy before feature detail
- [ ] Scannable format (lists, bold, headers)
- [ ] Appropriate length for page type
- [ ] Addresses objections
- [ ] Clear next step

### CTAs
- [ ] Two-word CTA label where possible
- [ ] Action verb + benefit
- [ ] High contrast visibility
- [ ] Distributed throughout page
- [ ] Goal-aligned messaging
- [ ] Risk reversal nearby
- [ ] CTA font uses the approved brand set

### Forms
- [ ] Brand-specific Sales-required fields are present
- [ ] Required fields are grouped in the right order
- [ ] Regional marketing email opt-in requirements are included where needed
- [ ] Multi-step flow is used where it improves completion without hiding required qualification fields

### PPC
- [ ] No nonessential exit points
- [ ] Clickable logo navigation removed unless required
- [ ] Page action is focused on one conversion goal

### Trust
- [ ] Customer testimonials with names
- [ ] Specific results/numbers
- [ ] Social proof (count, logos)
- [ ] Risk reversal present
- [ ] Security indicators (if needed)

### Technical
- [ ] Mobile responsive
- [ ] Fast load time (<3s)
- [ ] Form works correctly
- [ ] Links not broken
- [ ] Analytics tracking installed

---

## Quick Reference: Conversion Killers

**Avoid These:**
1. Generic headlines ("Welcome to our site")
2. Weak CTAs ("Submit", "Click here")
3. No visible trust signals
4. Walls of unformatted text
5. Multiple competing goals
6. Slow page load
7. Forms that ignore Sales-required qualification fields or regional opt-in rules
8. No risk reversal
9. Mobile-unfriendly design
10. Navigation that distracts from goal
11. Three-word-plus CTA labels when a two-word label would work
12. PPC page exit points that pull users away from the form or CTA
13. Reading low-volume tests without directional-signal and seasonality context
