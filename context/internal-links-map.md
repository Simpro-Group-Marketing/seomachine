# Simpro Internal Links Map

This document catalogs verified Simpro URLs for strategic internal linking in blog and resource content.

**Source**: `https://www.simprogroup.com/sitemap.xml`, accessed through Playwright MCP on 2026-05-21. The sitemap contained 855 URLs. The Product Marketing portal confirmed this public site is the active source for product, feature, comparison, customer proof, and resource links. GSC and GA4 first-party metrics were added on 2026-05-21.

**Evidence boundary**: URLs below are sitemap-verified. Link contexts and anchor examples are editorial guidance inferred from page paths, current Simpro context files, and the Product Marketing source map. Performance notes use first-party US-only GSC/GA4 data for 2026-02-20 through 2026-05-20. This file is complete for US first-party internal-link prioritization as of 2026-05-21. Search volume and keyword difficulty belong in `target-keywords.md`.

## Internal Linking Rules

1. Link naturally when the destination helps the reader evaluate, compare, or take the next step.
2. Prefer deep links over the homepage.
3. Use three to five internal links in a standard blog post unless the article is a long pillar guide.
4. Use descriptive anchors. Do not use "click here," "read more," or vague anchors.
5. For BOFU content, include one demo, pricing, comparison, or customer story link.
6. For TOFU content, use one product/category link only when the product relevance is explicit.
7. When a customer outcome is mentioned, link to the matching case study if one exists in the sitemap.

## Performance-Informed Internal Linking Priorities

**Metric scope**: United States only; GSC `country=usa`; GA4 `country=United States`; GSC page filter contains `https://www.simprogroup.com/`. Date range: 2026-02-20 to 2026-05-20. Source artifact: `research/simpro-first-party-metrics-2026-05-21.json`.

### Priority Link Flows

1. Route FSM category authority from `/blog/best-field-service-management-software` to `/solutions/field-service-management-software`. The blog has 298,684 GSC impressions and captures the main category queries, while the solution page has stronger GA4 conversion signal.
2. Support `/solutions/field-service-management-software` from definition, buyer-guide, scheduling, dispatch, mobile app, reporting, and industry pages. The solution page has 3,469 GA4 sessions and 83 key events but weak non-brand category rankings.
3. Use industry blog clusters to reinforce industry pages. HVAC, plumbing, and electrical industry pages each have high impressions but low CTR, which makes them internal-link and snippet-improvement priorities.
4. Link commercial comparison and pricing content back to the FSM solution and relevant industry pages. Pricing has strong branded intent and 10 GA4 key events, but it should not be the only BOFU destination.
5. Keep AI education pages linked to concrete FSM and feature pages. AI field-service variants show 6,940 impressions but only 4 clicks; the link path should turn AI interest into category and workflow evaluation.

### Page Performance Signals

| Page | GSC Clicks | GSC Impressions | CTR | Avg Position | GA4 Sessions | GA4 Key Events | Link Use |
|---|---:|---:|---:|---:|---:|---:|---|
| `/` | 2,614 | 48,030 | 5.44% | 26.5 | 20,701 | 170 | Use sparingly; strong brand/conversion page but deep links are usually better. |
| `/solutions/field-service-management-software` | 19 | 21,400 | 0.09% | 23.3 | 3,469 | 83 | Primary FSM destination and conversion page. |
| `/blog/best-field-service-management-software` | 32 | 298,684 | 0.01% | 12.5 | 437 | 1 | Authority donor for FSM category links. |
| `/blog/ai-for-field-service` | 11 | 8,281 | 0.13% | 11.2 | 87 | 0 | AI education hub; link to FSM and feature pages. |
| `/pricing` | 120 | 17,684 | 0.68% | 2.7 | 430 | 10 | BOFU support link, especially from comparison and ROI content. |
| `/solutions/job-management-software` | 4 | 9,809 | 0.04% | 16.5 | 37 | 1 | Support job lifecycle and quote-to-cash content. |
| `/solutions/asset-maintenance` | 3 | 2,013 | 0.15% | 33.3 | 262 | 6 | Use for recurring maintenance, compliance, and asset content. |

### Industry Page Performance

| Industry Page | GSC Clicks | GSC Impressions | CTR | Avg Position | GA4 Sessions | GA4 Key Events | Internal-Link Priority |
|---|---:|---:|---:|---:|---:|---:|---|
| `/industries/hvac-software` | 2 | 43,957 | 0.005% | 25.9 | 187 | 1 | High. Link from HVAC software, estimating, invoicing, KPI, AI, and margin articles. |
| `/industries/plumbing-software` | 1 | 66,459 | 0.002% | 26.5 | 269 | 3 | High. Link from plumbing margin/KPI/template articles and Foster Plumbing proof. |
| `/industries/electrical-software` | 3 | 36,760 | 0.008% | 29.0 | 356 | 0 | High. Link from electrical estimating, bid template, KPI, and customer proof. |
| `/industries/fire-protection-software` | 2 | 7,867 | 0.025% | 23.6 | 25 | 0 | Medium. Support from security/fire compliance content. |
| `/industries/security` | 0 | 354 | 0.000% | 10.0 | 485 | 4 | Medium. GA4 signal is stronger than GSC; link from security/low-voltage content and case studies. |
| `/industries/solar-renewable-business-software` | 0 | 5,911 | 0.000% | 22.5 | 10 | 0 | Low until this vertical becomes a US priority. |
| `/industries/elevator-service-software` | 0 | 4,815 | 0.000% | 16.9 | 9 | 0 | Low/medium. Monitor because impressions exist but clicks do not. |
| `/industries/commercial-kitchen-equipment-service-software` | 0 | 819 | 0.000% | 16.2 | 1 | 0 | Low. |

## Core Conversion Pages

### Homepage
- **URL**: https://www.simprogroup.com/
- **When to Link**: Rarely. Use when introducing Simpro broadly and no deeper product page fits.
- **Anchor Text Examples**: Simpro, the Simpro platform, Simpro field service software

### Demo
- **URL**: https://www.simprogroup.com/demo
- **When to Link**: BOFU posts, product comparisons, pricing/ROI discussions, and articles where the reader is ready to evaluate Simpro.
- **Anchor Text Examples**: book a Simpro demo, see Simpro in action, schedule a field service software demo

### Pricing
- **URL**: https://www.simprogroup.com/pricing
- **When to Link**: Pricing, software cost, implementation, ROI, and competitor TCO content.
- **Anchor Text Examples**: Simpro pricing, field service software pricing, request a custom quote

### Contact
- **URL**: https://www.simprogroup.com/contact-us
- **When to Link**: Contact and regional sales handoff contexts where demo or pricing is not specific enough.
- **Anchor Text Examples**: contact Simpro, talk to the Simpro team, get in touch

### United States and Canada Contact
- **URL**: https://www.simprogroup.com/contact-us/simpro-united-states-and-canada
- **When to Link**: US/Canada-specific commercial content, regional pages, and articles aimed at North American trades businesses.
- **Anchor Text Examples**: contact Simpro in the US and Canada, talk to the North America team

### About Simpro
- **URL**: https://www.simprogroup.com/company/about-us
- **When to Link**: Brand, mission, company scale, AI-first positioning, and corporate overview content.
- **Anchor Text Examples**: about Simpro, Simpro's company story, Simpro Group

### AI Pledge
- **URL**: https://www.simprogroup.com/company/ai-pledge
- **When to Link**: AI trust, responsible AI, AI adoption, and data-governance content.
- **Anchor Text Examples**: Simpro's AI pledge, responsible AI in the trades, AI trust principles

## Product and Solution Pages

### Field Service Management Software
- **URL**: https://www.simprogroup.com/solutions/field-service-management-software
- **When to Link**: Primary destination for FSM category articles, buyer guides, and "what is field service software" content.
- **Anchor Text Examples**: field service management software, field service software for trades, FSM software

### Job Management Software
- **URL**: https://www.simprogroup.com/solutions/job-management-software
- **When to Link**: UK/ANZ job-management content, job lifecycle articles, and operations workflow topics.
- **Anchor Text Examples**: job management software, job management platform, manage jobs from quote to cash

### Simpro Premium
- **URL**: https://www.simprogroup.com/solutions/simpro-premium
- **When to Link**: Product overview, office workflow, core platform, and implementation content.
- **Anchor Text Examples**: Simpro Premium, Simpro's core platform, field service operations platform

### Project Management Software
- **URL**: https://www.simprogroup.com/solutions/project-management-software
- **When to Link**: Project-heavy trades, progress billing, phased jobs, estimating, and work-in-progress content.
- **Anchor Text Examples**: project management software for trades, field service project management, manage complex jobs

### Asset Maintenance
- **URL**: https://www.simprogroup.com/solutions/asset-maintenance
- **When to Link**: Asset registers, recurring maintenance, preventative maintenance, compliance, and service agreement topics.
- **Anchor Text Examples**: asset maintenance software, recurring maintenance management, preventative maintenance workflows

### Commercial
- **URL**: https://www.simprogroup.com/solutions/commercial
- **When to Link**: Commercial contractor content, multi-phase jobs, larger teams, and mixed service/project operations.
- **Anchor Text Examples**: commercial field service software, commercial contractor software, commercial service operations

### Residential
- **URL**: https://www.simprogroup.com/solutions/residential
- **When to Link**: Residential trades content, homeowner service workflows, and residential/commercial comparison articles.
- **Anchor Text Examples**: residential field service software, residential contractor software, residential service workflows

## Feature Pages

### Scheduling Software
- **URL**: https://www.simprogroup.com/features/scheduling-software
- **When to Link**: Scheduling, dispatch, technician utilization, route planning, and office-to-field coordination.
- **Anchor Text Examples**: scheduling software, field service scheduling, schedule and dispatch jobs

### Field Service Mobile App
- **URL**: https://www.simprogroup.com/features/field-service-mobile-app
- **When to Link**: Mobile workforce, offline field work, technician adoption, forms, photos, signatures, and field invoicing.
- **Anchor Text Examples**: field service mobile app, mobile app for technicians, offline-capable field app

### Estimating Software
- **URL**: https://www.simprogroup.com/features/estimating-software
- **When to Link**: Quoting, estimating, bid templates, pre-builds, takeoffs, and faster proposal content.
- **Anchor Text Examples**: estimating software, quoting and estimating tools, create accurate estimates

### Work Order Software
- **URL**: https://www.simprogroup.com/features/work-order-software
- **When to Link**: Work orders, job execution, service workflows, and field-to-office handoff topics.
- **Anchor Text Examples**: work order software, manage work orders, field service work orders

### Invoicing Software for Construction
- **URL**: https://www.simprogroup.com/features/invoicing-software-for-construction
- **When to Link**: Invoicing, progress billing, payment collection, construction workflows, and cash flow topics.
- **Anchor Text Examples**: invoicing software for construction, field service invoicing, invoice from the field

### Payments
- **URL**: https://www.simprogroup.com/features/payments
- **When to Link**: Cash flow, card/online/on-site payments, faster collections, and payment automation content.
- **Anchor Text Examples**: Simpro Payments, field service payments, get paid faster

### Fast Cash
- **URL**: https://www.simprogroup.com/features/fast-cash
- **When to Link**: Accounts receivable, payment acceleration, cash collection, and AI-assisted payment workflows.
- **Anchor Text Examples**: Fast Cash, faster invoice payments, improve cash collection

### Track Inventory
- **URL**: https://www.simprogroup.com/features/track-inventory
- **When to Link**: Inventory management, parts, supplier purchasing, truck stock, and job cost control.
- **Anchor Text Examples**: inventory tracking, field service inventory, track parts and materials

### Reporting
- **URL**: https://www.simprogroup.com/features/reporting
- **When to Link**: BI, dashboards, margin visibility, KPI reporting, and data-driven operations.
- **Anchor Text Examples**: field service reporting, reporting dashboards, business intelligence for trades

### CRM for Field Service
- **URL**: https://www.simprogroup.com/features/crm-for-field-service
- **When to Link**: Customer relationship management, customer history, pipeline, and sales/service coordination.
- **Anchor Text Examples**: CRM for field service, field service CRM, customer management for trades

### Digital Forms
- **URL**: https://www.simprogroup.com/features/digital-forms
- **When to Link**: Compliance forms, field checklists, paperless workflows, audits, and mobile documentation.
- **Anchor Text Examples**: Digital Forms, digital field forms, paperless compliance forms

### Data Feed
- **URL**: https://www.simprogroup.com/features/data-feed
- **When to Link**: Email attachment automation, data extraction, workflow automation, and admin reduction topics.
- **Anchor Text Examples**: Data Feed, automated data processing, reduce manual data entry

### Maintenance Planner
- **URL**: https://www.simprogroup.com/features/maintenance-planner
- **When to Link**: Preventative maintenance, recurring service, asset testing, compliance, and service intervals.
- **Anchor Text Examples**: Maintenance Planner, preventative maintenance scheduling, recurring maintenance software

### Takeoffs
- **URL**: https://www.simprogroup.com/features/takeoffs
- **When to Link**: Estimating, plan markup, material calculation, bidding, and project quoting content.
- **Anchor Text Examples**: Takeoffs, digital takeoffs, material takeoff software

### Multi-Company
- **URL**: https://www.simprogroup.com/features/multi-company
- **When to Link**: PE-backed roll-ups, multi-location operators, franchises, acquisitions, and consolidated reporting.
- **Anchor Text Examples**: Multi-Company, multi-company field service software, roll-up reporting

### Delight
- **URL**: https://www.simprogroup.com/features/delight
- **When to Link**: Customer retention, repeat revenue, AI customer marketing, recurring work, and lifecycle marketing.
- **Anchor Text Examples**: Delight, AI customer marketing agent, repeat revenue from existing customers

### Simtrac
- **URL**: https://www.simprogroup.com/features/simtrac
- **When to Link**: Fleet tracking, GPS, driver activity, field visibility, and technician location topics.
- **Anchor Text Examples**: Simtrac, GPS fleet tracking, field fleet visibility

### SMS Messaging
- **URL**: https://www.simprogroup.com/features/sms-messaging
- **When to Link**: Customer notifications, appointment reminders, field communication, and text-message workflow content.
- **Anchor Text Examples**: SMS Messaging, customer text updates, field service text messaging

### Add-Ons
- **URL**: https://www.simprogroup.com/features/add-ons
- **When to Link**: Articles summarizing optional capabilities or comparing core platform versus add-on workflows.
- **Anchor Text Examples**: Simpro Add-Ons, optional Simpro features, extend Simpro workflows

## Industry Pages

### HVAC
- **URL**: https://www.simprogroup.com/industries/hvac-software
- **When to Link**: HVAC operations, maintenance agreements, dispatch, HVAC estimating, HVAC AI, and HVAC profitability content.
- **Anchor Text Examples**: HVAC software, field service software for HVAC contractors, HVAC contractor software

### Electrical
- **URL**: https://www.simprogroup.com/industries/electrical-software
- **When to Link**: Electrical estimating, electrical KPIs, bid templates, electrical AI, and service/project workflows.
- **Anchor Text Examples**: electrical software, electrical contractor software, field service software for electricians

### Plumbing
- **URL**: https://www.simprogroup.com/industries/plumbing-software
- **When to Link**: Plumbing business growth, plumbing invoicing, plumbing estimating, and service agreement content.
- **Anchor Text Examples**: plumbing software, plumbing contractor software, field service software for plumbers

### Fire Protection
- **URL**: https://www.simprogroup.com/industries/fire-protection-software
- **When to Link**: Fire protection, compliance, inspections, recurring maintenance, and asset records.
- **Anchor Text Examples**: fire protection software, fire inspection software, fire protection field service software

### Security
- **URL**: https://www.simprogroup.com/industries/security
- **When to Link**: Low voltage, security, A/V, alarms, recurring maintenance, and project work.
- **Anchor Text Examples**: security business software, low voltage contractor software, software for security contractors

### Solar and Renewable
- **URL**: https://www.simprogroup.com/industries/solar-renewable-business-software
- **When to Link**: Solar, renewable energy, install/service workflows, and recurring maintenance.
- **Anchor Text Examples**: solar business software, renewable business software, software for solar contractors

### Elevator Service
- **URL**: https://www.simprogroup.com/industries/elevator-service-software
- **When to Link**: Elevator service, inspections, maintenance schedules, and asset management content.
- **Anchor Text Examples**: elevator service software, elevator maintenance software

### Commercial Kitchen Equipment Service
- **URL**: https://www.simprogroup.com/industries/commercial-kitchen-equipment-service-software
- **When to Link**: Commercial kitchen equipment, service contracts, maintenance, and technician scheduling.
- **Anchor Text Examples**: commercial kitchen equipment service software, kitchen equipment service management

## Comparison Pages

Use these pages when mentioning a named competitor, writing alternatives content, or supporting BOFU buyer decisions.

| Competitor | URL | Anchor Text Examples |
|---|---|---|
| Ascora | https://www.simprogroup.com/comparisons/simpro-vs-ascora | Simpro vs Ascora, Ascora alternative |
| BuildOps | https://www.simprogroup.com/comparisons/simpro-vs-buildops | Simpro vs BuildOps, BuildOps alternative |
| Commusoft | https://www.simprogroup.com/comparisons/simpro-vs-commusoft | Simpro vs Commusoft, Commusoft alternative |
| Fergus | https://www.simprogroup.com/comparisons/simpro-vs-fergus | Simpro vs Fergus, Fergus alternative |
| FieldEdge | https://www.simprogroup.com/comparisons/simpro-vs-fieldedge | Simpro vs FieldEdge, FieldEdge alternative |
| FieldPulse | https://www.simprogroup.com/comparisons/simpro-vs-fieldpulse | Simpro vs FieldPulse, FieldPulse alternative |
| Housecall Pro | https://www.simprogroup.com/comparisons/simpro-vs-housecall-pro | Simpro vs Housecall Pro, Housecall Pro alternative |
| Jobber | https://www.simprogroup.com/comparisons/simpro-vs-jobber | Simpro vs Jobber, Jobber alternative |
| Joblogic | https://www.simprogroup.com/comparisons/simpro-vs-joblogic | Simpro vs Joblogic, Joblogic alternative |
| Microsoft Dynamics 365 Field Service | https://www.simprogroup.com/comparisons/simpro-vs-microsoft-dynamics | Simpro vs Microsoft Dynamics, Dynamics field service alternative |
| NextMinute | https://www.simprogroup.com/comparisons/simpro-vs-nextminute | Simpro vs NextMinute, NextMinute alternative |
| Procore | https://www.simprogroup.com/comparisons/simpro-vs-procore | Simpro vs Procore, Procore alternative |
| Salesforce Field Service | https://www.simprogroup.com/comparisons/simpro-vs-salesforce-field-service | Simpro vs Salesforce Field Service, Salesforce field service alternative |
| Service Fusion | https://www.simprogroup.com/comparisons/simpro-vs-service-fusion | Simpro vs Service Fusion, Service Fusion alternative |
| ServiceM8 | https://www.simprogroup.com/comparisons/simpro-vs-servicem8 | Simpro vs ServiceM8, ServiceM8 alternative |
| ServiceTitan | https://www.simprogroup.com/comparisons/simpro-vs-servicetitan | Simpro vs ServiceTitan, ServiceTitan alternative |
| Tradify | https://www.simprogroup.com/comparisons/simpro-vs-tradify | Simpro vs Tradify, Tradify alternative |
| Uptick | https://www.simprogroup.com/comparisons/simpro-vs-uptick | Simpro vs Uptick, Uptick alternative |

## Customer Proof Links

Use customer stories when a post mentions the customer, the same trade, or a measurable outcome from `features.md`.
Use this table for verified case-study URLs and topic fit. Use `context/features.md` > `Named Customer Proof Points` for exact metrics, and do not infer new claims from a case-study URL alone.

| Customer | URL | Link When Writing About |
|---|---|---|
| Shaffer Beacon Mechanical | https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical | Job costing, margin improvement, mechanical/HVAC operations |
| Foster Plumbing | https://www.simprogroup.com/case-studies/foster-plumbing | Business growth, exit readiness, plumbing, real-time job costing |
| TEAMWired | https://www.simprogroup.com/case-studies/teamwired | Payments, faster collections, security/low voltage |
| Tequa | https://www.simprogroup.com/case-studies/tequa | Debt reduction, payments, cash collection |
| O'Brien Electrical Granville | https://www.simprogroup.com/case-studies/obrien-electrical-granville | Electrical operations, field visibility, scheduling |
| Enhanced Electrical | https://www.simprogroup.com/case-studies/enhanced-electrical | Scaling field technicians without proportional admin |
| Proguard Protection Services | https://www.simprogroup.com/case-studies/proguard-protection-services | Field technician productivity, security workflows |
| Proguard Protection Services Delight | https://www.simprogroup.com/case-studies/proguard-protection-services-delight | Delight, customer retention, repeat revenue |
| McCarthy Plumbing Group | https://www.simprogroup.com/case-studies/mccarthy-plumbing-group | Plumbing admin savings, operational efficiency |
| BGE Digital | https://www.simprogroup.com/case-studies/bge-digital | Estimating speed, digital jobs, quote workflows |
| James Frew | https://www.simprogroup.com/case-studies/james-frew | Purchase orders, admin reduction, integration workflows |
| alarmQuest | https://www.simprogroup.com/case-studies/alarmquest | Faster invoicing, security, field workflows |
| Infinite Audio Video Solutions | https://www.simprogroup.com/case-studies/infinite-audio-video-solutions | A/V, low voltage, admin reduction, daily jobs per technician |
| Norberg Electric | https://www.simprogroup.com/case-studies/norberg-electric | Electrical estimating, project blueprints |
| Orion | https://www.simprogroup.com/case-studies/orion | Revenue growth, security workflows |

## Resources and Guides

### Voice of the Trades
- **URL**: https://www.simprogroup.com/resources/ebooks/voice-of-the-trades
- **When to Link**: Industry outlook, trades sentiment, workforce, and thought leadership.
- **Anchor Text Examples**: Voice of the Trades, trades industry report, field service industry insights

### Trades Outlook Report 2025
- **URL**: https://www.simprogroup.com/resources/ebooks/trades-outlook-report-2025
- **When to Link**: Market outlook, industry trends, AI, workforce, and planning content.
- **Anchor Text Examples**: Trades Outlook Report, trades trends report, field service outlook

### Scale Field Service Business Guide
- **URL**: https://www.simprogroup.com/resources/ebooks/scale-field-service-business-guide
- **When to Link**: Scaling, business growth, process maturity, and operational discipline.
- **Anchor Text Examples**: guide to scaling a field service business, field service growth guide

### Job Costing Ebook
- **URL**: https://www.simprogroup.com/resources/ebooks/job-costing
- **When to Link**: Job costing, margin, profitability, and financial control content.
- **Anchor Text Examples**: job costing guide, field service job costing, improve job profitability

### Business Reporting for Trade Contractors
- **URL**: https://www.simprogroup.com/resources/ebooks/business-reporting-trade-contractors
- **When to Link**: Reporting, KPIs, dashboards, data-driven operations, and management visibility.
- **Anchor Text Examples**: business reporting for trade contractors, field service reporting guide

### Field Service Management in the Cloud
- **URL**: https://www.simprogroup.com/resources/ebooks/field-service-management-in-the-cloud
- **When to Link**: Cloud software, modernization, implementation, and moving off spreadsheets.
- **Anchor Text Examples**: cloud field service management, field service software in the cloud

### Field Service Management for Security Integrators
- **URL**: https://www.simprogroup.com/resources/ebooks/field-service-management-for-security-integrators
- **When to Link**: Security, low voltage, A/V, fire/security, and integrator-specific content.
- **Anchor Text Examples**: field service management for security integrators, security integrator software guide

### Managing Change in Field Service
- **URL**: https://www.simprogroup.com/resources/ebooks/managing-change-field-service
- **When to Link**: Implementation, adoption, change management, and software-switching content.
- **Anchor Text Examples**: managing change in field service, field service software adoption guide

## Blog and Article Links

These are sitemap-confirmed blog pages relevant to Simpro content production. Use the performance section above when choosing priority authority donors; not every listed blog page is confirmed as top-performing.

### Field Service Category
- **What Is Field Service Management**: https://www.simprogroup.com/blog/what-is-field-service-management
- **Best Field Service Management Software**: https://www.simprogroup.com/blog/best-field-service-management-software
- **Field Service and Trades Software Buyer's Guide**: https://www.simprogroup.com/blog/field-service-and-trades-software-buyers-guide
- **Field Service Automation**: https://www.simprogroup.com/blog/field-service-automation
- **Field Service Operations**: https://www.simprogroup.com/blog/field-service-operations
- **Field Service KPIs Every Trade Business Should Track**: https://www.simprogroup.com/blog/field-service-kpis-every-trade-business-should-track

### AI in the Trades
- **AI Operating Platforms for Trades Businesses**: https://www.simprogroup.com/blog/ai-operating-platforms-for-trades-businesses
- **AI-First vs AI-Powered in the Trades**: https://www.simprogroup.com/blog/ai-first-vs-ai-powered-in-the-trades
- **AI for Field Service**: https://www.simprogroup.com/blog/ai-for-field-service
- **Data Fuel for AI in the Trades**: https://www.simprogroup.com/blog/data-fuel-for-ai-in-the-trades

### Profitability, Margin, and Cash Flow
- **Hidden Margin Leak in Field Service**: https://www.simprogroup.com/blog/hidden-margin-leak-field-service
- **Job Costing Formula**: https://www.simprogroup.com/blog/job-costing-formula
- **Trade Services KPIs That Protect Margin**: https://www.simprogroup.com/blog/trade-services-kpis-that-protect-margin
- **Payments as a Strategic Growth Lever for Trades**: https://www.simprogroup.com/blog/payments-as-a-strategic-growth-lever-for-trades
- **Faster Field Service Payments With Simpro**: https://www.simprogroup.com/blog/faster-field-service-payments-with-simpro

### HVAC
- **HVAC Profit Margins**: https://www.simprogroup.com/blog/hvac-profit-margins
- **HVAC KPIs That Protect Margin**: https://www.simprogroup.com/blog/hvac-kpis-that-protect-margin
- **HVAC Estimating**: https://www.simprogroup.com/blog/hvac-estimating
- **HVAC Invoicing**: https://www.simprogroup.com/blog/hvac-invoicing
- **HVAC Apps**: https://www.simprogroup.com/blog/hvac-apps

### Plumbing
- **Plumbing Business Profit Margin Guide**: https://www.simprogroup.com/blog/plumbing-business-profit-margin-guide
- **Plumbing KPIs That Protect Margin**: https://www.simprogroup.com/blog/plumbing-kpis-that-protect-margin
- **Plumbing Invoicing**: https://www.simprogroup.com/blog/plumbing-invoicing
- **Plumbing Estimate Template**: https://www.simprogroup.com/blog/plumbing-estimate-template
- **Plumbing Maintenance Agreement Template**: https://www.simprogroup.com/blog/plumbing-maintenance-agreement-template

### Electrical
- **Electrical Business Profit Margin**: https://www.simprogroup.com/blog/electrical-business-profit-margin
- **Electrical KPIs That Protect Margin**: https://www.simprogroup.com/blog/electrical-kpis-that-protect-margin
- **Electrical Estimate Template**: https://www.simprogroup.com/blog/electrical-estimate-template
- **Electrical Bid Template**: https://www.simprogroup.com/blog/electrical-bid-template
- **Electrical Advertising**: https://www.simprogroup.com/blog/electrical-advertising

## Quick Reference by Topic

**When writing about field service software**, link to:
- https://www.simprogroup.com/solutions/field-service-management-software - primary field service management software page
- https://www.simprogroup.com/blog/what-is-field-service-management - definition and education support
- https://www.simprogroup.com/blog/best-field-service-management-software - commercial comparison support
- https://www.simprogroup.com/demo - conversion next step

**When writing about AI in the trades**, link to:
- https://www.simprogroup.com/company/ai-pledge - trust and responsible AI
- https://www.simprogroup.com/blog/ai-operating-platforms-for-trades-businesses - AI operating platform education
- https://www.simprogroup.com/blog/ai-first-vs-ai-powered-in-the-trades - category distinction
- https://www.simprogroup.com/features/delight - AI customer marketing agent

**When writing about profitability or margin**, link to:
- https://www.simprogroup.com/resources/ebooks/job-costing - job costing guide
- https://www.simprogroup.com/blog/hidden-margin-leak-field-service - margin leak article
- https://www.simprogroup.com/blog/job-costing-formula - job costing formula article
- https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical - customer proof for profit margin improvement

**When writing about cash flow and payments**, link to:
- https://www.simprogroup.com/features/payments - Simpro Payments
- https://www.simprogroup.com/features/fast-cash - cash acceleration
- https://www.simprogroup.com/blog/payments-as-a-strategic-growth-lever-for-trades - strategic payment content
- https://www.simprogroup.com/case-studies/teamwired - customer proof for faster payments

**When writing about HVAC**, link to:
- https://www.simprogroup.com/industries/hvac-software - HVAC industry page
- https://www.simprogroup.com/blog/hvac-profit-margins - HVAC margin article
- https://www.simprogroup.com/blog/hvac-kpis-that-protect-margin - HVAC KPI article
- https://www.simprogroup.com/blog/ai-operating-platforms-for-hvac-businesses - HVAC AI article

**When writing about plumbing**, link to:
- https://www.simprogroup.com/industries/plumbing-software - plumbing industry page
- https://www.simprogroup.com/blog/plumbing-business-profit-margin-guide - plumbing margin guide
- https://www.simprogroup.com/blog/plumbing-kpis-that-protect-margin - plumbing KPI article
- https://www.simprogroup.com/case-studies/foster-plumbing - plumbing growth and exit proof

**When writing about electrical contractors**, link to:
- https://www.simprogroup.com/industries/electrical-software - electrical industry page
- https://www.simprogroup.com/blog/electrical-business-profit-margin - electrical margin article
- https://www.simprogroup.com/blog/electrical-kpis-that-protect-margin - electrical KPI article
- https://www.simprogroup.com/case-studies/obrien-electrical-granville - electrical customer proof

**When writing about security, low voltage, or fire protection**, link to:
- https://www.simprogroup.com/industries/security - security industry page
- https://www.simprogroup.com/industries/fire-protection-software - fire protection industry page
- https://www.simprogroup.com/resources/ebooks/field-service-management-for-security-integrators - security integrator guide
- https://www.simprogroup.com/case-studies/infinite-audio-video-solutions - A/V customer proof

**When writing about software switching or competitor comparisons**, link to:
- The relevant `/comparisons/simpro-vs-[competitor]` page from the comparison table above
- https://www.simprogroup.com/resources/ebooks/managing-change-field-service - change management guide
- https://www.simprogroup.com/pricing - pricing and quote-based evaluation
- https://www.simprogroup.com/demo - demo conversion step

## Maintenance Notes

- Re-check the sitemap quarterly or after major site migrations.
- Refresh GSC/GA4 performance data quarterly before changing link priority.
- Rebuild this map only when a new sitemap pull changes the URL inventory or a new GSC/GA4 pull materially changes page priority.
- Canonical destination rule: `simpro.ai` is for Lightning, Cooper, JustAsk, named Lightning agents, and AI-for-the-trades topics. Classic Simpro product, feature, industry, comparison, pricing, blog, resource, customer-story, and internal-link destinations remain on `simprogroup.com` unless a specific URL migration is verified.
- If any `simpro.ai` content path becomes relevant for internal linking, build a separate verified `simpro.ai` map from that domain's sitemap and analytics data instead of replacing this `simprogroup.com` map.
