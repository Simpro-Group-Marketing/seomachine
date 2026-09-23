import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const ROOT = process.cwd();
const OUTPUT_DIR = path.join(ROOT, "outputs", "bigchange-g2-digital-markets-copy-2026-09-23");
const CSV_PATH = path.join(ROOT, "outputs", "bigchange-g2-digital-markets-copy-matrix-2026-09-23.csv");
const XLSX_PATH = path.join(OUTPUT_DIR, "bigchange-g2-digital-markets-copy-matrix-2026-09-23.xlsx");
const MD_PATH = path.join(ROOT, "outputs", "bigchange-g2-digital-markets-copy-audit-2026-09-23.md");
const PREVIEW_PATH = path.join(OUTPUT_DIR, "bigchange-g2-digital-markets-copy-preview.png");

const CHECKED_DATE = "2026-09-23";
const PORTAL_BASE = "https://app.g2digitalmarkets.com/products/4e18268f-3248-4693-a1e0-a6d200b2e0b2";
const HOME_URL = "https://www.bigchange.com/";
const PRICING_URL = "https://www.bigchange.com/pricing";
const KEYWORD_MAP_URL = "https://docs.google.com/spreadsheets/d/1UbipLHa7N5TEIy7evqdyKLaHV87MBwX9W2g2vJaXc88/edit?pli=1&gid=905535356#gid=905535356";
const OLD_VIDEO_URL = "https://www.youtube.com/watch?v=3-26Aa_8i9A";
const NEW_VIDEO_URL = "https://www.youtube.com/watch?v=4fcnxzGWkN0";

const PROOF = {
  rilmac: {
    customer: "Rilmac Asbestos Services Division | Construction and asbestos abatement | approximately 30% less back-office administration resource",
    qualification: "Named-customer result. Preserve 'approximately'. The source attributes the result to Rilmac's BigChange implementation and does not establish a typical outcome.",
    url: "https://www.bigchange.com/success-stories/bigchange-removes-inefficiency-for-rilmac-asbestos-services-division",
  },
  ses: {
    customer: "SES Home Services | Utilities, plumbing, heating and drainage | up to 20% greater daily job efficiency per engineer",
    qualification: "Named-customer result. Preserve 'up to' and 'per engineer daily'. The page does not provide a measurement methodology.",
    url: "https://www.bigchange.com/success-stories/ses-home-services-report-a-tangible-return-on-investment",
  },
  baydale: {
    customer: "Baydale Control Systems | Fire and security | jobs allocated 80% faster",
    qualification: "Named-customer result tied to digital stock records and engineer vehicle-stock visibility. Do not generalise the result.",
    url: "https://www.bigchange.com/success-stories/baydale-transforms-stock-management-using-bigchange",
  },
  ebgas: {
    customer: "EB Gas Services | Plumbing, heating and HVAC | 20% more routine service jobs allocated",
    qualification: "Named-customer result. No measurement period or methodology is published, so retain attribution and avoid extrapolation.",
    url: "https://www.bigchange.com/success-stories/eb-gas-boost-engineer-productivity-with-bigchange",
  },
  serious: {
    customer: "Serious Waste Management | Waste management | more than 60% less time to create and issue invoices",
    qualification: "Named-customer invoicing result. Exclude the page's conflicting growth figures.",
    url: "https://www.bigchange.com/success-stories/bigchange-job-management-system-helps-waste-company-seriously-grow-business",
  },
  eft: {
    customer: "EFT Systems | Fire and security | 30 to 40 reporting hours saved each month",
    qualification: "Result requires BigChange, Snowflake Data as a Service and partner Rathbone Results. It is not evidence for the base platform alone.",
    url: "https://www.bigchange.com/success-stories/how-bigchange-and-rathbone-results-saved-eft-systems-40-hours-per-month",
  },
  flowfree: {
    customer: "Flow Free Drainage | Drainage, waste and environmental | two office staff handling about 60 jobs daily versus five or six previously",
    qualification: "Named-customer before-and-after statement. The source uses legacy JobWatch branding and publishes no visible date, so retain the precise comparison and avoid the separate growth claim.",
    url: "https://www.bigchange.com/success-stories/bigchange-drives-40-growth-with-paperless-working-at-flow-free-drainage",
  },
  ccis: {
    customer: "CC Infrastructure Services | Specialist cleaning and infrastructure coatings | 20% less administrative resource for operational teams",
    qualification: "Named-customer result tied to replacing paper worksheets and job folders. Exclude the source's undefined '50% less waste' statement.",
    url: "https://www.bigchange.com/success-stories/cc-is-cleans-up-with-bigchange-paperless-working",
  },
};

const categoryNames = [
  "Building Maintenance", "CMMS", "Calendar", "Contractor Management", "Delivery Management",
  "Electrical Contractor", "Equipment Maintenance", "Facility Management", "Field Service Management",
  "Forms Automation", "Garage Door", "HVAC", "Handyman", "Inspection", "Janitorial", "Job Costing",
  "Locksmith", "Maintenance Management", "Pest Control", "Plumbing", "Plumbing Estimating",
  "Preventive Maintenance", "Public Works", "Scheduling", "Security System Installer", "Service Dispatch",
  "Work Order", "Workforce Management",
];

const capterraCurrent = {
  "Building Maintenance": ["BigChange's all-in-one Job Management System is the paperless way for building maintenance companies to plan, manage, schedule & track jobs in one easy to use platform. BigChange helps maintenance companies across the UK to win more work, increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's all-in-one Job Management System plans, manages, schedules & tracks your maintenance jobs in one paperless solution."],
  "CMMS": ["BigChange Job Management Platform is the paperless way for maintenance companies to plan, manage, schedule & track maintenance jobs in one simple to use and easy to integrate CMMS platform. BigChange helps maintenance companies across the UK to win more work,  increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange Job Management Platform plans, manages, schedules & tracks your building maintenance jobs in one paperless solution."],
  "Calendar": ["BigChange provides job management software for UK field teams. Integrates customer relationship management (CRM), job scheduling, live fleet tracking, mobile app, financial management and business intelligence into one simple to use and easy to integrate, cloud-based platform that any business with field workers can thrive on.\n\nNow with AI automations and digital workers (AI agents) that help you accomplish more with less.", "BigChange's all-in-one job management software plans, manages, schedules & tracks your UK field teams in a single easy-to-use solution."],
  "Contractor Management": ["BigChange Job Management Platform is the paperless way for companies to plan, manage, schedule & track jobs in one simple to use and easy to integrate platform. BigChange helps companies across the UK to win more work, increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange Job Management Platform plans, manages, schedules & tracks your contractor's jobs in one paperless solution."],
  "Delivery Management": ["BigChange Job Management Platform is the paperless way for companies to plan, manage, schedule & track deliveries in one simple to use and easy to integrate platform. Our smart scheduling uses real time data to optimise routing and allocate the perfect resource for each job helping delivery companies improve efficiency and cut costs. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange Job Management Platform plans, manages, schedules & tracks your deliveries in one cloud-based, easy-to-use solution."],
  "Electrical Contractor": ["BigChange's all-in-one Job Management System is the paperless way for electrical businesses to plan, manage, schedule & track jobs in one easy to use, cloud-based system. BigChange helps electrical companies across the UK to win more work, increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office  and field based teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's all-in-one Job Management System helps UK electricians plan, manage, schedule & track jobs in 1 paperless solution."],
  "Equipment Maintenance": ["BigChange's all-in-one Job Management System is built to help equipment maintenance companies be Unstoppable. Integrating customer relationship management (CRM), job scheduling, live tracking, mobile app, financial management & business intelligence into one simple to use and easy to implement system that equipment maintenance companies can thrive on.", "BigChange's all-in-one Job Management System helps you plan, manage, schedule & track equipment maintenance jobs in one place."],
  "Facility Management": ["BigChange's all-in-one Job Management System is the paperless way for FM companies to plan, manage, schedule & track jobs in one simple to use and easy to implement platform. BigChange helps FM companies across the UK to win more work,  increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's all-in-one Job Management System plans, manages, schedules & tracks your FM jobs in one paperless solution."],
  "Field Service Management": ["BigChange's all-in-one Field Service Management System is the paperless way to plan, manage, schedule & track jobs in one simple to use and easy to implement platform. BigChange helps field service companies across the UK to win more work,  increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's Field Service Management System helps UK service businesses plan, manage, schedule & track jobs in one paperless solution."],
  "Forms Automation": ["BigChange provides job management software for UK field teams. Integrates customer relationship management (CRM), job scheduling, live fleet tracking, mobile app, financial management and business intelligence into one simple to use and easy to integrate, cloud-based platform that any business with field workers can thrive on.\n\nNow with AI automations and digital workers (AI agents) that help you accomplish more with less.", "BigChange's all-in-one job management software plans, manages, schedules & tracks your UK field teams in a single easy-to-use solution."],
  "Garage Door": ["BigChange Job Management Platform is the paperless way for garage door businesses to plan, manage, schedule & track their engineers in one simple to use and easy to integrate platform. BigChange helps garage door companies across the UK to win more work, increase team capacity accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's Job Management Platform is the paperless way for garage door businesses to plan, manage, schedule & track their workforce"],
  "HVAC": ["BigChange's all-in-one UK Job Management System is the paperless way for HVAC businesses to plan, manage, schedule & track their jobs in one simple to use and easy to implement, cloud-based platform. BigChange helps HVAC businesses across the UK to win more work,  increase team capacity, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and HVAC teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's UK Job Management System is the paperless solution for HVAC businesses to plan, manage, schedule & track their engineers."],
  "Handyman": ["BigChange Job Management Platform is the paperless way for handyman businesses to plan, manage, schedule & track their jobs in one simple to use and easy to integrate platform. BigChange helps field service businesses across the UK to win more work, increase team capacity accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and handymen alike, our customers are achieving industry leading growth and ROI.", "BigChange's Job Management Platform is the paperless solution for handyman businesses to plan, manage, schedule & track their jobs."],
  "Inspection": ["BigChange's all-in-one Job Management System is the paperless way for teams to plan, manage, schedule & carry out inspections in one simple to use cloud-based platform. Give your field teams instant access to inspection records on a cloud based tablet & seamlessly connect your field teams, office & customers. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's Job Management System is the paperless solution for businesses to plan, manage, schedule & complete inspections."],
  "Janitorial": ["BigChange Job Management Platform is the paperless way for cleaning businesses to plan, manage, schedule & track their jobs in one simple to use and easy to integrate, cloud-based platform. BigChange helps cleaning businesses across the UK to win more work, increase team capacity accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and cleaners alike, our customers are achieving industry leading growth and ROI.", "BigChange's Job Management Platform is the paperless way for cleaning businesses to plan, manage, schedule & track their jobs."],
  "Job Costing": ["BigChange Job Management Platform has powerful, paperless job costing capabilities, allowing field teams to generate & send invoices, quotes, estimates, purchase orders and credit notes in seconds. Additionally, with easy-to-use integrations with Sage, Xero, Quickbooks & other accounting softwares, BigChange seamlessly integrates your accounting. Loved by UK office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's Job Management Platform allows field teams to send invoices, quotes, estimates, purchase orders & credit notes in seconds."],
  "Locksmith": ["BigChange's all-in-one Job Management System is the paperless way for locksmiths to plan, manage, schedule & track their jobs in one simple to use cloud-based platform. BigChange helps locksmith businesses across the UK to win more work,  increase team capacity, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and locksmith teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's all-in-one Job Management System plans, manages, schedules & tracks your locksmith jobs in one paperless solution."],
  "Maintenance Management": ["BigChange's all-in-one Job Management System is the paperless way for maintenance companies to plan, manage, schedule & track jobs in one simple to use platform. BigChange helps maintenance companies across the UK to win more work,  increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's all-in-one Job Management Platform plans, manages, schedules & tracks your maintenance jobs in one paperless solution."],
  "Pest Control": ["BigChange's all-in-one Job Management System is the paperless way for pest control businesses to plan, manage, schedule & track jobs in one simple to use cloud-based platform. BigChange helps pest control businesses across the UK to win more work,  increase team capacity accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and pest control teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's Job Management System is the paperless solution for pest control businesses to plan, manage, schedule & track their jobs."],
  "Plumbing": ["BigChange's all-in-one Job Management System is the paperless way for plumbers to plan, manage, schedule & track jobs in one simple to use cloud-based platform. BigChange helps plumbing businesses across the UK to win more work,  increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office teams and plumbers alike, our customers are achieving industry leading growth and ROI.", "BigChange's all-in-one Job Management System helps UK plumbing businesses plan, manage, schedule & track jobs in 1 paperless solution."],
  "Plumbing Estimating": ["BigChange's all-in-one Job Management System is the paperless way for plumbing businesses to estimate, manage, schedule & track jobs in one simple to use platform. BigChange helps plumbing businesses across the UK to win more work,  increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office teams and plumbers alike, our customers are achieving industry leading growth and ROI.", "BigChange's Job Management System allows plumbers to send invoices, quotes, estimates, purchase orders & credit notes in seconds."],
  "Preventive Maintenance": ["BigChange's all-in-one Job Management System is the paperless way for maintenance companies to plan, manage, schedule & track jobs in one simple to use platform. BigChange helps maintenance companies across the UK to win more work, increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange Job Management System plans, manages, schedules & tracks your maintenance jobs in one paperless solution."],
  "Public Works": ["BigChange Job Management Platform is the paperless way for companies to plan, manage, schedule & track public works in one simple to use and easy to integrate platform. BigChange helps companies across the UK  to win more work,  increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange Job Management Platform plans, manages, schedules & tracks public works in one paperless solution."],
  "Scheduling": ["BigChange's all-in-one Job Scheduling System is the paperless way to plan, manage, schedule and track jobs in one simple to use and easy to implement platform. BigChange helps field service companies across the UK to win more work, increase the capacity of their teams, accelerate invoicing & transform cashflow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's Job Scheduling System helps service businesses plan, manage, schedule & track jobs in one paperless solution."],
  "Security System Installer": ["BigChange's all-in-one Job Management System is the paperless way for security system companies to plan, manage, schedule & track jobs in one simple to use platform. BigChange helps companies across the UK to win more work,  increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's all-in-one Job Management System is the paperless way for security installers to plan, manage, schedule & track their jobs."],
  "Service Dispatch": ["BigChange's all-in-one Job Management System is the paperless way for service dispatch companies to plan, manage, schedule & track jobs in one simple to use cloud-based platform. Our smart scheduling uses real time data to optimise routes and allocate the perfect resource for each job helping service dispatchers improve efficiency and cut costs. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's Job Management System is the paperless way for service companies to plan, schedule, dispatch & track their jobs."],
  "Work Order": ["BigChange's all-in-one Work Order Management System is the paperless way for field service companies to plan, manage, schedule & track jobs in one simple to use platform. BigChange helps field service companies across the UK to win more work, increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's Work Order Management System helps UK service businesses plan, manage, schedule & track jobs in one paperless solution."],
  "Workforce Management": ["BigChange's all-in-one Mobile Workforce Management System is the paperless way to plan, manage, schedule and track jobs in one simple to use and easy to implement platform. BigChange helps field service companies across the UK to win more work, increase the capacity of their teams, accelerate invoicing & transform cash flow, all whilst reducing operational costs and admin time. Loved by office and field teams alike, our customers are achieving industry leading growth and ROI.", "BigChange's Mobile Workforce Management System helps service businesses plan, manage, schedule & track jobs in one paperless solution."],
};

const getappCurrent = {
  "Building Maintenance": "BigChange is the complete Job Management Platform, helping building maintenance companies to plan, manage, schedule & track maintenance jobs in one simple to use, easy to integrate, cloud-based platform.",
  "CMMS": "BigChange is the complete Job Management Platform, helping building maintenance companies to plan, manage, schedule & track maintenance jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Calendar": "BigChange is the complete Job Management Platform, helping building maintenance, construction, environmental and other field service companies to streamline operations, grow revenue and deliver winning customer experiences.",
  "Contractor Management": "BigChange is the complete Job Management Platform, helping companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Delivery Management": "BigChange Job Management Platform is the paperless way for companies to plan, manage, schedule & track deliveries in one simple to use and easy to integrate platform. Our smart scheduling uses real time data to optimise routing and allocate the perfect resource for every delivery.",
  "Electrical Contractor": "BigChange is the complete Job Management Platform, helping electrical companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Equipment Maintenance": "BigChange is the complete Job Management Platform, helping building maintenance companies to plan, manage, schedule & track maintenance jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Facility Management": "BigChange is the complete Job Management Platform, helping building maintenance companies to plan, manage, schedule & track maintenance jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Field Service Management": "BigChange is the complete Field Service Management Platform, helping field service companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Forms Automation": "BigChange is the complete Job Management Platform, helping building maintenance, construction, environmental and other field service companies to streamline operations, grow revenue and deliver winning customer experiences.",
  "Garage Door": "BigChange is the complete Job Management Platform, helping garage doors companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "HVAC": "BigChange is the complete Job Management Platform, helping HVAC companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Handyman": "BigChange is the complete Job Management Platform, helping handyman companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Inspection": "BigChange Job Platform is the paperless way for teams to plan, manage, schedule & carry out inspections in one simple to use and easy to integrate platform. Give your field teams instant access inspection records on a cloud based tablet & seamlessly connect your field teams, office & customers.",
  "Janitorial": "BigChange is the complete Job Management Platform, helping cleaning companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Job Costing": "BigChange Job Management Platform has powerful, paperless job costing capabilities, allowing field teams to generate & send invoices, quotes, estimates, purchase orders and credit notes in seconds. Includes easy-to-use integrations with Sage, Xero, Quickbooks & other accounting softwares.",
  "Locksmith": "BigChange is the complete Job Management Platform, helping locksmith companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Maintenance Management": "BigChange is the complete Job Management Platform, helping building maintenance companies to plan, manage, schedule & track maintenance jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Pest Control": "BigChange is the complete Job Management Platform, helping pest control companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Plumbing": "BigChange is the complete Job Management Platform, helping plumbing companies to plan, manage, schedule & track maintenance jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Plumbing Estimating": "BigChange Job Management Platform is the paperless way for plumbing businesses to estimate, manage, schedule & track jobs in one simple to use and easy to integrate, cloud-based platform.",
  "Preventive Maintenance": "BigChange is the complete Job Management Platform, helping building maintenance companies to plan, manage, schedule & track maintenance jobs in one simple to use, easy to integrate, cloud-based platform",
  "Public Works": "BigChange is the complete Job Management Platform, helping companies to plan, manage, schedule & track public works in one simple to use, easy to integrate, cloud-based platform.",
  "Scheduling": "BigChange Job Management Platform is the paperless way for companies to plan, manage, schedule & track jobs in one simple to use platform. Our smart scheduling uses real time data to optimise routing and allocate the perfect resource for each job helping companies improve efficiency and cut costs.",
  "Security System Installer": "BigChange is the complete Job Management Platform, helping security system companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Service Dispatch": "BigChange Job Management Platform is the paperless way for companies to plan, manage, schedule & track jobs in one simple to use platform. Our smart scheduling uses real time data to optimise routing and allocate the perfect resource for each job helping companies improve efficiency and cut costs.",
  "Work Order": "BigChange is the complete Field Service Management Platform, helping field service companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform.",
  "Workforce Management": "BigChange is the complete Job Management Platform, helping field service companies to plan, manage, schedule & track jobs in one simple to use, easy to integrate, cloud-based platform. Streamline your operations & seamlessly connect your office, & field teams in one platform.",
};

const rows = [];

function addRow({ channel, field, category, currentCopy, issue, priority, mappedKeyword, icpPain, feature, advantage, benefit, proposedCopy, fieldLimit, proof, sourceUrl, proofStatus }) {
  rows.push({
    channel,
    field,
    category,
    "current copy": currentCopy,
    issue,
    priority,
    "mapped keyword": mappedKeyword,
    "ICP pain": icpPain,
    feature,
    advantage,
    benefit,
    "proposed copy": proposedCopy,
    "field limit": fieldLimit,
    "character count": proposedCopy.length,
    "customer proof": proof?.customer ?? "None",
    "proof qualification": proof?.qualification ?? "No customer metric used.",
    "source URL": [sourceUrl, proof?.url].filter(Boolean).join(" | "),
    "checked date": CHECKED_DATE,
    "proof status": proofStatus ?? (proof ? "Verified on live BigChange case study" : "No customer proof required"),
  });
}

const categoryMeta = {
  "Building Maintenance": { kw: "building maintenance software (P2 supporting term, confidence 60)", pain: "Reactive and planned maintenance jobs are hard to coordinate across office and field teams.", feature: "Scheduling, asset context, mobile job records and live progress", advantage: "Keeps maintenance work and service history connected", benefit: "Your team gets clearer job visibility with less paper handling" },
  "CMMS": { kw: "facilities maintenance software (P1 adjacent term, confidence 95)", pain: "Assets, service history and reminders sit in separate systems.", feature: "Asset records, maintenance scheduling, service reminders and mobile updates", advantage: "Connects maintenance activity to the relevant asset and history", benefit: "Your team can plan work with fewer information gaps" },
  "Calendar": { kw: "job scheduling software uk (P1 adjacent term, confidence 95)", pain: "Schedulers rebuild the day when urgent work or delays appear.", feature: "Shared visual calendar and job-resource scheduling", advantage: "Updates office plans and field assignments from one workflow", benefit: "Your team responds to change without spreadsheet rework" },
  "Contractor Management": { kw: "subcontractor management software (P2 supporting term, confidence 60)", pain: "Subcontractor allocation, acceptance and updates are scattered across calls and messages.", feature: "Contractor allocation, shared job details and status updates", advantage: "Keeps external resources inside the job workflow", benefit: "Your office gains visibility without chasing every update" },
  "Delivery Management": { kw: "electronic proof of delivery software (P2 supporting term, confidence 60)", pain: "Delivery outcomes and customer sign-off reach the office late.", feature: "Mobile job details, signatures, photos and completion records", advantage: "Creates a digital proof trail at the point of service", benefit: "Your office sees delivery outcomes sooner" },
  "Electrical Contractor": { kw: "electrician job management software uk (P1, confidence 95)", pain: "Electrical job details and site records do not move cleanly between office and engineers.", feature: "Scheduling, mobile job details, digital records, quotes and invoices", advantage: "Connects the electrical job from assignment to completion", benefit: "Your team reduces re-entry and keeps work moving" },
  "Equipment Maintenance": { kw: "field service asset management software; service reminder software (P2 supporting terms, confidence 60)", pain: "Teams lack one view of equipment history and upcoming service work.", feature: "Asset records, service reminders, engineer scheduling and mobile updates", advantage: "Keeps equipment context with each maintenance job", benefit: "Your team can act before service work is missed" },
  "Facility Management": { kw: "facilities maintenance software (P1, confidence 95)", pain: "Facilities teams coordinate jobs, assets and contractors across disconnected tools.", feature: "Job scheduling, asset context, mobile workflows and customer updates", advantage: "Creates one operating view from request to completion", benefit: "Your office and field teams work from the same information" },
  "Field Service Management": { kw: "field service management software (P2 supporting term, confidence 60)", pain: "CRM, scheduling, field activity, finance and reporting are disconnected.", feature: "CRM, scheduling, tracking, mobile workflows, invoicing and BI", advantage: "Connects the full job lifecycle in one platform", benefit: "Your team gains control without stitching systems together" },
  "Forms Automation": { kw: "job sheet software; job card software (P2 supporting terms, confidence 60)", pain: "Paper job sheets arrive late or incomplete.", feature: "Reusable mobile forms, job cards, signatures and photos", advantage: "Captures structured field evidence at the job", benefit: "Your office receives clearer records without rekeying paper" },
  "Garage Door": { kw: "industrial door software (P2 adjacent term, confidence 60)", pain: "Installation and service visits are difficult to coordinate across mobile teams.", feature: "Customer records, scheduling, mobile jobs and completion evidence", advantage: "Keeps door service work connected from office to site", benefit: "Your team gets a clearer view of every visit" },
  "HVAC": { kw: "hvac service software (P2 supporting term, confidence 60)", pain: "HVAC teams lose time when schedules, site details and completion records are disconnected.", feature: "Service scheduling, mobile job history and field records", advantage: "Gives technicians current information and returns updates to the office", benefit: "Your team can allocate more routine work with less coordination" },
  "Handyman": { kw: "job management software uk (P1 broad term, confidence 95)", pain: "Small mobile jobs are tracked through calls, paper and separate calendars.", feature: "Scheduling, mobile job details and completion records", advantage: "Keeps each handyman job in one workflow", benefit: "Your office sees progress without chasing updates" },
  "Inspection": { kw: "risk assessment software; job sheet software (P2 adjacent terms, confidence 60)", pain: "Inspection and risk records are incomplete or delayed when they remain on paper.", feature: "Digital forms, risk assessments, signatures and photos", advantage: "Creates a structured evidence trail on site", benefit: "Your team returns complete inspection records to the office faster" },
  "Janitorial": { kw: "cleaning business software uk (P1 adjacent term, confidence 95)", pain: "Cleaning teams need simple tasks and reliable proof without complex field tools.", feature: "Scheduling, mobile tasks, worksheets and completion evidence", advantage: "Standardises field records while keeping the workflow easy to follow", benefit: "Your office spends less time handling paper folders" },
  "Job Costing": { kw: "job quoting software; field service invoicing software (P2 supporting terms, confidence 60)", pain: "Quotes, labour, expenses and invoices are difficult to connect to the job.", feature: "Quotes, timesheets, expenses, purchase information and invoices", advantage: "Keeps financial job data together", benefit: "Your team gets clearer cost and billing visibility with less re-entry" },
  "Locksmith": { kw: "job management software uk (P1 broad term, confidence 95)", pain: "Urgent locksmith jobs are coordinated through calls and incomplete field notes.", feature: "Scheduling, mobile job details and proof of work", advantage: "Connects dispatch and completion in one record", benefit: "Your office stays updated while locksmiths remain mobile" },
  "Maintenance Management": { kw: "facilities maintenance software; building maintenance software (P1/P2 terms)", pain: "Planned and reactive work compete for attention across assets and teams.", feature: "Scheduling, asset records, reminders and service history", advantage: "Gives maintenance teams one view of work due and work completed", benefit: "Your team can prioritise with clearer operational context" },
  "Pest Control": { kw: "pest control software (P2 supporting term, confidence 60)", pain: "Visits, compliance records, quotes and follow-ups are scattered.", feature: "Customer records, scheduling, mobile forms and reporting", advantage: "Keeps pest-control work and evidence connected", benefit: "Your technicians and office share a more complete job record" },
  "Plumbing": { kw: "plumbing job management software uk (P1, confidence 95)", pain: "Plumbing jobs move slowly when scheduling, field updates and invoicing are separate.", feature: "Scheduling, mobile job information, quotes and invoices", advantage: "Connects the plumbing job from booking to billing", benefit: "Your team completes the handoff with less repeated entry" },
  "Plumbing Estimating": { kw: "plumbing job management software uk (P1); job quoting software (P2)", pain: "Accepted estimates must be re-entered before work can be scheduled and billed.", feature: "Customer records, quotes, scheduling and invoices", advantage: "Carries job information from estimate into delivery", benefit: "Your office reduces duplicate setup and keeps the commercial trail intact" },
  "Preventive Maintenance": { kw: "service reminder software; field service asset management software (P2 supporting terms, confidence 60)", pain: "Upcoming service work is missed when asset dates and reminders are disconnected.", feature: "Asset history, service reminders and planned scheduling", advantage: "Turns service dates into visible work", benefit: "Your team can plan visits before obligations are missed" },
  "Public Works": { kw: "public sector crm; highways maintenance software (P2 adjacent terms, confidence 60)", pain: "Public works teams need consistent job records across mobile crews and assets.", feature: "Job scheduling, mobile records, asset context and reporting", advantage: "Keeps field updates visible to the office", benefit: "Your team gains a clearer operational record across maintenance work" },
  "Scheduling": { kw: "job scheduling software uk (P1, confidence 95)", pain: "Dispatchers cannot see current availability when jobs change.", feature: "Drag-and-drop job and resource scheduling with live updates", advantage: "Matches work to people and sends changes to the field", benefit: "Your team adapts the day without rebuilding the plan" },
  "Security System Installer": { kw: "fire and security job management software (P1, confidence 95)", pain: "Installation, service and stock information are disconnected from engineer availability.", feature: "Scheduling, mobile jobs, stock visibility and digital certification", advantage: "Connects resource decisions to current job and stock data", benefit: "Your team can allocate suitable work faster" },
  "Service Dispatch": { kw: "job scheduling software uk; vehicle tracking software uk (P1 adjacent terms, confidence 95)", pain: "Urgent work triggers calls because dispatchers cannot see the nearest suitable engineer.", feature: "Scheduling, skills, availability and live vehicle tracking", advantage: "Brings resource choice and location into dispatch", benefit: "Your team responds with fewer manual check-ins" },
  "Work Order": { kw: "job card software; job sheet software (P2 supporting terms, confidence 60)", pain: "Paper work orders create slow handoffs and missing evidence.", feature: "Digital job cards, worksheets, signatures and photos", advantage: "Moves instructions and completion records through one workflow", benefit: "Your office receives a complete record without transporting paper" },
  "Workforce Management": { kw: "mobile workforce management software (P2 supporting term, confidence 60)", pain: "Managers lack one view of schedules, locations, time and completed work.", feature: "Mobile jobs, scheduling, live tracking, timesheets and field records", advantage: "Connects office plans with mobile activity", benefit: "Your managers see progress and exceptions in one place" },
};

const getappProposed = {
  "Building Maintenance": "Plan reactive and scheduled building maintenance in one place. Give your office a clear view of jobs, engineers, assets and service history while mobile teams capture updates and proof of work on site.",
  "CMMS": "Keep assets, maintenance jobs, service history and reminders connected. Your team can schedule work, record field updates and see the information needed to make better maintenance decisions.",
  "Calendar": "Use job scheduling software UK field teams can follow from office to site. Plan jobs and resources in one shared calendar, respond to changes quickly and keep customers updated.",
  "Contractor Management": "Use subcontractor management software to allocate work, share job details and receive updates in one workflow. Gain clearer visibility without relying on calls, paper or disconnected messages.",
  "Delivery Management": "Use electronic proof of delivery software to give mobile teams clear job details and capture signatures, photos and completion records. The office gets faster visibility of every delivery outcome.",
  "Electrical Contractor": "Use electrician job management software UK teams can rely on to schedule engineers, share job details, capture site records and move completed electrical work towards invoicing.",
  "Equipment Maintenance": "Keep equipment, service jobs and maintenance information connected. Schedule engineers, send reminders and capture mobile updates so your team has a clearer view of asset work and history.",
  "Facility Management": "Use facilities maintenance software to coordinate jobs, engineers, assets and customer updates. Give the office and field one view of work, from scheduling through completion and reporting.",
  "Field Service Management": "Bring CRM, scheduling, live tracking, mobile workflows, invoicing and reporting into one field service management software platform. Control each job while keeping field teams and customers informed.",
  "Forms Automation": "Replace paper job sheets with mobile forms and reusable workflows. Engineers can capture signatures, watermarked photos and job details on site, giving the office clearer and faster records.",
  "Garage Door": "Coordinate installation, maintenance and repair work with one view of customers, jobs and mobile teams. Schedule the right engineer and capture service records, photos and sign-off on site.",
  "HVAC": "Use HVAC service software to connect customers, schedules, engineers and job records. Give technicians mobile access to the information they need and move completed work back to the office faster.",
  "Handyman": "Use job management software UK field teams can access from office to site. Schedule handyman work, share job details, capture completion records and keep customers informed in one workflow.",
  "Inspection": "Move inspections from paper to controlled digital workflows. Send clear job details to the field, capture risk assessments, signatures and photos, and return complete records to the office.",
  "Janitorial": "Use cleaning business software UK teams can follow without complex processes. Schedule work, share tasks with mobile staff, capture completion evidence and give the office clearer job visibility.",
  "Job Costing": "Connect quotes, job activity, expenses, timesheets and invoices so you can see the information behind each job. Reduce rekeying and move completed work towards billing with fewer handoffs.",
  "Locksmith": "Plan, schedule and track locksmith jobs from one platform. Give mobile teams customer and job details, capture proof of work on site and keep the office updated without paper processes.",
  "Maintenance Management": "Coordinate maintenance schedules, assets, engineers and service reminders in one workflow. Capture mobile updates and service history so your team can act with clearer operational visibility.",
  "Pest Control": "Use pest control software to manage customers, schedules, mobile visits, compliance records and reporting. Give technicians clear job information and capture site evidence while work is completed.",
  "Plumbing": "Use plumbing job management software UK teams can rely on to schedule work, send job details, capture field updates and connect completed plumbing jobs with quotes and invoicing.",
  "Plumbing Estimating": "Connect plumbing quotes with customer, job and scheduling information. Create a clearer handoff from estimate to planned work, field completion and invoicing without re-entering the same details.",
  "Preventive Maintenance": "Plan preventive work with connected asset information, service reminders and field records. Help teams schedule visits, capture completion evidence and maintain a clearer service history.",
  "Public Works": "Coordinate public works jobs, mobile teams, assets and field records in one platform. Schedule work, capture site updates and give the office clearer visibility across maintenance operations.",
  "Scheduling": "Use job scheduling software UK field teams can follow in real time. Drag and drop jobs and resources, respond to changes quickly and share current job information with mobile engineers.",
  "Security System Installer": "Use fire and security job management software to coordinate installation and service work. Schedule engineers, share site details and capture job records, photos and sign-off in the field.",
  "Service Dispatch": "Schedule jobs and use live vehicle tracking to help send the right engineer. Give dispatchers a clearer view of field resources while mobile teams receive current job details and updates.",
  "Work Order": "Turn work orders into connected digital job cards and job sheets. Send clear instructions to the field, capture signatures and photos, and return complete records to the office without paper.",
  "Workforce Management": "Use mobile workforce management software to connect office plans with field activity. Schedule people, share job information, capture time and completion records, and see progress in one place.",
};

const capterraProposed = {
  "Building Maintenance": {
    long: "BigChange gives building maintenance teams one place to manage reactive call-outs, planned visits and the records behind every property and job. Office staff can schedule the right worker, share current site details and follow progress. Mobile teams can receive job information, complete digital job cards, add photos and update status from the field. This helps your business reduce paperwork, improve handovers and keep maintenance work visible through to invoicing.",
    short: "Manage reactive and planned building maintenance with connected schedules, mobile job cards, site records and invoicing.",
  },
  "CMMS": {
    long: "BigChange connects work orders, equipment records, maintenance schedules, inspections and mobile updates for teams that need practical CMMS capabilities alongside field operations. Planned and reactive work can be assigned from a central schedule, with job details and service information available to mobile workers. Completed forms, notes and costs flow back to the office, giving managers clearer maintenance history and fewer disconnected records.",
    short: "Connect work orders, equipment records, maintenance schedules, inspections and mobile updates for clearer asset control.",
  },
  "Calendar": {
    long: "BigChange turns the job calendar into a live planning view for field teams. Office staff can see availability, allocate jobs, adjust plans and keep customer and job details connected to each booking. Mobile workers receive updated schedules and job information without relying on calls, whiteboards or printed diaries. This helps your team respond to change, reduce scheduling clashes and keep workloads visible.",
    short: "Plan jobs and field teams in a live calendar, with current customer details, mobile updates and clearer workload visibility.",
  },
  "Contractor Management": {
    long: "BigChange helps businesses coordinate contractors with the same job, customer and scheduling information used for internal teams. Contractor details, work records, documents and assigned jobs can stay connected, while permissions help control access to relevant information. Office teams gain a clearer view of who is doing what and when, reducing fragmented handovers and manual follow-up.",
    short: "Coordinate contractor details, schedules, documents and work records alongside internal teams in one connected job view.",
  },
  "Delivery Management": {
    long: "BigChange helps delivery and field operations teams plan work, assign drivers or mobile workers and track progress from dispatch to completion. Current addresses, instructions and job details reach the mobile app, while location and status updates give the office visibility during the day. Digital completion records reduce paper handovers and help customer and finance teams act on completed work sooner.",
    short: "Plan and track delivery work with mobile instructions, live status updates and digital completion records.",
  },
  "Electrical Contractor": {
    long: "BigChange is job management software for electrical contractors that connects enquiries, quotes, scheduling, field job cards, forms, stock, invoicing and customer history. Office teams can plan engineers and see progress, while electricians receive job details and record work from site. This gives your business a clearer path from first contact to completed job, with less paper and fewer repeated updates.",
    short: "Connect electrical quotes, engineer schedules, field job cards, forms, stock, customer history and invoicing.",
  },
  "Equipment Maintenance": {
    long: "BigChange helps equipment maintenance teams organise assets, planned service, reactive repairs and the work history attached to each job. Schedulers can assign technicians and share equipment and site information, while mobile workers record checks, notes, photos, parts and completion details. Connected records make it easier to see outstanding work, support consistent servicing and prepare completed jobs for billing.",
    short: "Organise equipment service, repairs, technician schedules, mobile checks, parts and work history in one job record.",
  },
  "Facility Management": {
    long: "BigChange gives facilities management teams one operational view of service requests, sites, planned maintenance, reactive jobs, engineers and contractors. Work can be scheduled and tracked from the office, while mobile teams receive current details and complete digital records on site. This helps your business reduce admin, improve job visibility and keep customers informed across multiple locations.",
    short: "Manage facilities work across sites with connected requests, schedules, engineers, contractors and mobile records.",
  },
  "Field Service Management": {
    long: "BigChange is field service management software for UK businesses that need to connect office planning with work in the field. It brings customer records, quotes, scheduling, dispatch, live tracking, mobile job cards, forms, timesheets, invoicing and reporting together. Your team can allocate work with more context, capture updates at the job and move completed work towards invoicing without re-entering the same information.",
    short: "Field service management software connecting customers, scheduling, dispatch, mobile work, tracking and invoicing.",
  },
  "Forms Automation": {
    long: "BigChange replaces paper job sheets and disconnected forms with digital workflows that mobile workers can complete at the point of service. Teams can use structured worksheets to capture job details, checks, photos and completion information, then return that record to the office with the job. This reduces re-keying, missing paperwork and delays between field completion and the next office action.",
    short: "Replace paper job sheets with mobile forms that capture checks, photos and completion details in the job record.",
  },
  "Garage Door": {
    long: "BigChange helps garage door service businesses manage customer enquiries, quotes, engineer schedules, installation and repair jobs, mobile worksheets and invoices. Office teams can see workloads and progress, while technicians receive site details and record work in the field. Connected job records help your business reduce paperwork, respond to urgent repairs and keep repeat service work organised.",
    short: "Manage garage door quotes, installations, repairs, engineer schedules, mobile records and invoices in one workflow.",
  },
  "HVAC": {
    long: "BigChange helps HVAC businesses manage installations, breakdowns and routine service work from one connected job system. Office teams can schedule engineers, share site and equipment details and track progress, while mobile workers complete job cards, forms and timesheets in the field. Quotes, job records and invoices stay connected, reducing repeated administration. In a published customer story, EB Gas Services reported allocating 20% more routine jobs after adopting BigChange. This is one customer experience, not a guaranteed outcome.",
    short: "Manage HVAC installations, breakdowns and routine service with connected scheduling, mobile job cards and invoicing.",
  },
  "Handyman": {
    long: "BigChange gives handyman and property service teams a shared workflow for customer requests, quotes, scheduling, mobile job details and invoices. Office staff can plan varied work and update priorities, while field workers receive current instructions and record notes, photos and completion details. This helps your business handle more small jobs without losing information across calls, paper diaries and separate apps.",
    short: "Connect handyman requests, quotes, schedules, mobile job details and invoices without relying on paper diaries.",
  },
  "Inspection": {
    long: "BigChange helps inspection teams schedule visits, send site and asset details to mobile workers and collect structured digital records in the field. Inspectors can complete forms, add notes and photos and update job status, while office teams can see completed information without waiting for paper returns. This improves traceability and helps the next action start sooner.",
    short: "Schedule inspections and capture forms, notes, photos, asset details and job status in connected mobile records.",
  },
  "Janitorial": {
    long: "BigChange helps janitorial and commercial cleaning businesses organise recurring visits, reactive work, mobile teams and customer records. Office staff can build schedules, adjust allocations and follow job progress, while cleaners receive instructions and complete digital records in the field. This reduces paper admin and gives managers clearer control of service delivery. In a published customer story, CC Infrastructure Services reported a 20% reduction in administrative resource after adopting BigChange. This reflects one customer experience and is not a guaranteed result.",
    short: "Organise cleaning schedules, recurring visits, reactive jobs, mobile teams and customer records in one system.",
  },
  "Job Costing": {
    long: "BigChange connects job activity with quotes, labour, parts, expenses and invoicing so service businesses can see the information behind job costs in one place. Office and field updates feed the job record as work progresses, reducing the need to reconcile separate spreadsheets and paper. Managers gain earlier visibility of cost and completion information, helping them review performance and prepare accurate billing.",
    short: "Connect quotes, labour, parts, expenses and invoices for clearer job-cost visibility and more accurate billing.",
  },
  "Locksmith": {
    long: "BigChange helps locksmith businesses manage urgent call-outs, planned work, customer details, engineer schedules, mobile job cards, stock and invoices. Dispatchers can use live location and availability information when assigning work, while locksmiths receive current job details and record completion in the field. This helps your team respond with better context and reduce paper between the call and the invoice.",
    short: "Manage locksmith call-outs, schedules, mobile job cards, stock and invoices with live location and job context.",
  },
  "Maintenance Management": {
    long: "BigChange connects planned maintenance, reactive jobs, service schedules, equipment records and mobile completion details. Office teams can allocate technicians and monitor progress, while field workers access current job information and record work at the site. One connected history reduces fragmented records, supports more consistent maintenance and gives managers clearer visibility of outstanding work.",
    short: "Connect planned and reactive maintenance, service schedules, equipment records and mobile completion details.",
  },
  "Pest Control": {
    long: "BigChange helps pest control businesses coordinate surveys, treatments, recurring visits and urgent call-outs. Office teams can schedule technicians, store customer and site information and follow job status, while mobile workers receive instructions and complete digital worksheets in the field. This helps your business keep service histories organised, reduce paper and move completed work towards invoicing.",
    short: "Coordinate pest surveys, treatments, recurring visits, call-outs and mobile worksheets with connected customer records.",
  },
  "Plumbing": {
    long: "BigChange is job management software for plumbing businesses that connects enquiries, quotes, engineer schedules, emergency call-outs, mobile job cards, customer history and invoicing. Office teams can see workloads and progress, while plumbers receive current job details and record work on site. This reduces repeated entry and gives your business a clearer view from first call to completed job.",
    short: "Connect plumbing enquiries, quotes, engineer schedules, call-outs, mobile job cards, customer history and invoicing.",
  },
  "Plumbing Estimating": {
    long: "BigChange helps plumbing businesses turn enquiry and site information into connected quotes and job records. Teams can prepare estimates using customer, work and cost details, then keep the accepted information linked as the job moves into scheduling, field delivery and invoicing. This reduces repeated entry and gives estimators, engineers and finance teams a shared record.",
    short: "Create plumbing estimates from customer, work and cost details, then keep them connected to jobs and invoices.",
  },
  "Preventive Maintenance": {
    long: "BigChange helps service businesses organise preventive maintenance with recurring schedules, equipment records, mobile job cards and a connected service history. Office teams can plan upcoming visits and assign workers, while field teams receive current details and record completed checks, notes, photos and parts. This makes planned work easier to see, reduces missed information and keeps follow-up activity connected.",
    short: "Plan preventive maintenance with recurring schedules, equipment records, mobile job cards and service history.",
  },
  "Public Works": {
    long: "BigChange helps public works teams coordinate service requests, crews, vehicles, equipment and field records across planned and reactive work. Jobs can be scheduled and dispatched from the office, with current instructions delivered to mobile workers. Status updates, forms and completion information return to the job record, improving visibility and reducing paper across dispersed operations.",
    short: "Coordinate public works requests, crews, vehicles, equipment, schedules and mobile records across dispersed operations.",
  },
  "Scheduling": {
    long: "BigChange gives service businesses a live scheduling and dispatch view for jobs, mobile workers and vehicles. Office teams can see availability, allocate work, adjust priorities and use location context when plans change. Updated job details reach the field through the mobile app, helping your business reduce clashes, limit avoidable travel and keep customers better informed.",
    short: "Schedule jobs, workers and vehicles with live availability, location context, mobile updates and clearer workloads.",
  },
  "Security System Installer": {
    long: "BigChange helps security system installers manage surveys, quotes, installations, maintenance visits and emergency work in one connected job workflow. Office teams can schedule engineers, share site and equipment details and track progress, while mobile workers complete job cards and forms on site. In a published customer story, Baydale Control Systems reported 80% faster job allocation after adopting BigChange. This reflects one customer experience and is not a guaranteed result.",
    short: "Manage security surveys, quotes, installations and maintenance with engineer scheduling and mobile job records.",
  },
  "Service Dispatch": {
    long: "BigChange helps dispatchers match incoming work with available field workers using schedule, location and job information. Office teams can allocate or reassign jobs and send current customer and site details to the mobile app. Live status updates improve visibility after dispatch, helping your business respond to changing priorities and reduce time spent chasing field progress.",
    short: "Dispatch work using schedule, location and job context, with mobile instructions and live status updates.",
  },
  "Work Order": {
    long: "BigChange turns work orders into connected records that move from request and scheduling through field completion, costs and invoicing. Office teams can assign work, attach customer and site information and see current status, while mobile workers access instructions and complete digital job cards. This helps your business reduce duplicate entry, find outstanding work and act faster when a job is complete.",
    short: "Connect work orders from request and scheduling through mobile completion, cost capture and invoicing.",
  },
  "Workforce Management": {
    long: "BigChange helps field service businesses organise mobile workers, schedules, timesheets, vehicles and job activity in one operational view. Office teams can see availability and progress, update assignments and share current job information through the mobile app. This gives managers clearer workload visibility and reduces admin around coordinating a dispersed workforce.",
    short: "Organise mobile workers, schedules, timesheets, vehicles and job activity with one live operational view.",
  },
};

const capterraDefaultLong = "Job management software for UK field teams brings the office, engineers, vehicles, customers and finances into one working view. BigChange connects CRM, job scheduling, live tracking, mobile job cards, quotes, invoices and business intelligence, so your team can replace paper and disconnected systems without losing control of the job. Schedulers assign work by skills, location and availability. Engineers receive current job information, capture photos and signatures, and return completed records from site. Office teams can follow progress, keep customers updated and move finished work towards invoicing. Rilmac Asbestos Services reports that BigChange reduced its back-office administration resource by approximately 30%. That result is specific to Rilmac's operation.";
const capterraDefaultShort = "Job management software for UK field teams, connecting CRM, scheduling, tracking, mobile jobs, invoicing and reporting.";
const capterraTarget = "UK field service businesses with office and mobile teams that need to replace paper, coordinate jobs, track progress and invoice completed work.";

addRow({ channel: "Capterra", field: "Long Description", category: "Default", currentCopy: "BigChange provides job management software for UK field teams. Integrates customer relationship management (CRM), job scheduling, live fleet tracking, mobile app, financial management and business intelligence into one simple to use and easy to integrate, cloud-based platform that any business with field workers can thrive on.\n\nNow with AI automations and digital workers (AI agents) that help you accomplish more with less.", issue: "The opening matches the category but becomes a feature list, uses first-person customer language indirectly and lacks a specific buyer workflow or qualified proof.", priority: "P1", mappedKeyword: "job management software uk (P1, confidence 95); natural ICP form: job management software for UK field teams", icpPain: "Paper, disconnected systems and late field updates weaken control from enquiry to invoice.", feature: "CRM, scheduling, live tracking, mobile jobs, finance and BI", advantage: "Connects office and field information across the job lifecycle", benefit: "Your team coordinates work with less paper and repeated entry", proposedCopy: capterraDefaultLong, fieldLimit: 1000, proof: PROOF.rilmac, sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL} | ${PORTAL_BASE}/capterra#content-header` });
addRow({ channel: "Capterra", field: "Short Description", category: "Default", currentCopy: "BigChange's all-in-one job management software plans, manages, schedules & tracks your UK field teams in a single easy-to-use solution.", issue: "The field is at its 135-character limit, relies on 'all-in-one' and does not identify the connected office-to-field workflow.", priority: "P1", mappedKeyword: "job management software uk (P1, confidence 95)", icpPain: "Buyers need to identify fit and workflow quickly.", feature: "CRM, scheduling, tracking, mobile jobs, invoicing and reporting", advantage: "Names the connected workflow in one sentence", benefit: "Your buyer can understand product fit at a glance", proposedCopy: capterraDefaultShort, fieldLimit: 135, sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL}` });
addRow({ channel: "Capterra", field: "Target Market", category: "Default", currentCopy: "BigChange is the all-in-one Job Management System, helping building maintenance, construction, environmental and other UK field service companies be unstoppable every day.", issue: "The market definition is broad and ends with promotional language rather than roles, operating model and problems.", priority: "P1", mappedKeyword: "job management software uk (P1, confidence 95)", icpPain: "Field service buyers need a clear statement of who the platform suits.", feature: "UK field service workflow coverage", advantage: "Defines team structure and operational need", benefit: "Prospects can self-qualify before reading detailed copy", proposedCopy: capterraTarget, fieldLimit: 200, sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL}` });

const getappLong = `BigChange is job management software UK field teams can use to plan work, control operations and keep customers informed from one cloud platform. Bring CRM, job scheduling, live vehicle and resource tracking, mobile working, financial management and business intelligence together, so your office and field teams work from the same job information instead of paper and disconnected systems.\n\nWin and manage work with an integrated CRM, sales pipeline, quotes and customer records. Build schedules with drag and drop job and resource planning, then use live tracking to see progress and help dispatch the right engineer. Automated confirmations, ETA alerts, service reminders and a customer portal help you keep customers updated without adding more calls to the office.\n\nGive field teams the BigChange JobWatch app on Android and iOS. Engineers can access job details, complete digital job cards and worksheets, capture electronic signatures and watermarked photos, record expenses and timesheets, and carry out driver and vehicle checks while on the move. Completed information flows back to the office for faster reporting, invoicing and payment collection.\n\nConnect BigChange with tools including Sage, Xero, Microsoft Dynamics NAV, QuickBooks and SAP Business One. Use AI automations and digital workers to support repeatable admin tasks while your team stays in control.\n\nThe operational impact is documented by BigChange customers. Flow Free Drainage reports that two team members now handle around 60 jobs a day, compared with five to six people before. This before-and-after result is specific to Flow Free's operation and appears on a legacy JobWatch case study.\n\nChoose BigChange when you need one job management platform to connect customers, jobs, people, vehicles, finances and performance across your UK field operation.`;
const getappShort = "BigChange brings CRM, job scheduling, live tracking, mobile working, invoicing and reporting into one job management platform, helping UK field teams replace paper, control every job and keep customers informed.";
const getappTagline = "Job management software for UK field teams.";
const getappBenefits = `- Control every job from one platform. Connect CRM, quotes, job scheduling, live tracking, mobile workflows, invoicing and business intelligence, so office and field teams work from the same information.\n\n- Schedule and dispatch with greater visibility. Drag and drop jobs and resources, track vehicles and engineers live, and use ETA alerts to keep customers informed when plans change.\n\n- Replace paper in the field. The BigChange JobWatch app lets engineers view jobs, complete digital job cards and worksheets, capture electronic signatures and watermarked photos, log expenses and timesheets, and complete driver and vehicle checks.\n\n- Turn completed work into cash sooner. Move job information back to the office for invoicing and payment collection. Serious Waste Management reports more than 60% less time creating and issuing invoices.\n\n- Make reporting less labour intensive. Use business intelligence and performance reporting to understand operations. EFT Systems reports saving 30 to 40 reporting hours each month using BigChange with Snowflake Data as a Service and Rathbone Results.\n\n- Allocate work faster. Baydale Control Systems reports 80% faster job allocation after connecting digital stock records with visibility into vehicle stock.\n\n- Give customers self-service visibility. A branded portal lets customers request work, check job status, and view service history and documents from any web-enabled device.\n\n- Connect the systems you already use. BigChange integrates with Sage, Xero, Microsoft Dynamics NAV, QuickBooks and SAP Business One.\n\nThese customer results are specific to each named operation and do not establish typical outcomes.`;

addRow({ channel: "GetApp", field: "Long Description", category: "Default", currentCopy: "BigChange provides all-in-one job management software for UK field teams.  It helps field service businesses across the UK to win more work, take control of their operations and deliver winning customer experiences. It combines customer relationship management (CRM), job scheduling, live tracking, field resource management, financial management, and business intelligence into 1 easy-to-use platform.\n\nNow with AI automations and digital workers (AI agents) that help you accomplish more with less.\n\nBigChange liberates you from inefficient paper-based processes and the complexity of multiple different technology systems that hold your business back. Loved by office and field teams alike, our customers are achieving industry leading results and return on investment.\n\nThe BigChange team is committed to customer success and no matter your sector or whether you have a mobile workforce of 10 or a 100, we’re here to make a big difference to the way you work and to help your business grow stronger.", issue: "The copy repeats broad outcomes, uses first-person language and unsupported industry-leading and ROI claims, and underuses GetApp's longer comparison field.", priority: "P1", mappedKeyword: "job management software uk (P1, confidence 95)", icpPain: "Buyers need enough workflow detail to compare how office, field, customer and finance work connects.", feature: "CRM, scheduling, tracking, mobile, finance, integrations and AI automations", advantage: "Explains the data flow from enquiry through field completion and reporting", benefit: "Your team can evaluate fit against specific operational problems", proposedCopy: getappLong, fieldLimit: 4000, proof: PROOF.flowfree, sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL} | ${PORTAL_BASE}/getapp#content-header` });
addRow({ channel: "GetApp", field: "Short Description", category: "Default", currentCopy: "BigChange is the complete Job Management Platform, helping building maintenance, construction, environmental and other field service companies to streamline operations, grow revenue and deliver winning customer experiences.", issue: "The copy lists sectors and generic growth outcomes rather than the connected product workflow.", priority: "P1", mappedKeyword: "job management software uk (P1, confidence 95)", icpPain: "Comparison buyers need a concise statement of category, capabilities and outcome.", feature: "CRM, scheduling, tracking, mobile work, invoicing and reporting", advantage: "Condenses the end-to-end workflow", benefit: "Your buyer can establish relevance quickly", proposedCopy: getappShort, fieldLimit: 300, sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL}` });
addRow({ channel: "GetApp", field: "Tagline", category: "Default", currentCopy: "BigChange provides AI-first job management software.", issue: "The tagline names AI but omits the verified UK field-team ICP.", priority: "P1", mappedKeyword: "job management software uk (P1, confidence 95)", icpPain: "Buyers need immediate ICP and category recognition.", feature: "Job management platform for UK field teams", advantage: "Aligns the entity with homepage positioning", benefit: "Improves clarity in a scan-heavy placement", proposedCopy: getappTagline, fieldLimit: 60, sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL}` });
addRow({ channel: "GetApp", field: "Benefits", category: "Default", currentCopy: "• BigChange Job Management Platform is a cloud-based field service management system that includes an integrated back-office CRM with drag and drop job / resource scheduling, customizable template-driven workflows, invoicing, health & safety and more.\n\n• BigChange Job Management Platform adds an integrated vehicle tracking component spanning back-office live Google Mapping, geofencing, journey history logs, fleet and resource management, timesheets and performance reporting with alerts.\n\n• An on-demand booking website is made available to customers, via which they can log into a branded portal from any web-enabled device to place new job bookings, check current job status, and view service histories and documentation.\n\n• BigChange integrates with other third-party management applications including Sage, Xero, Microsoft Dynamics NAV, QuickBooks and SAP Business One.\n\n• The companion BigChange JobWatch mobile app for Android and iOS devices adds field-based feature support along with electronic signatures, watermarked photo capture, expense logging, timesheets, holiday and absence recording, plus driver checking and vehicle maintenance.", issue: "The existing bullets are feature-led, contain dated wording and do not connect capabilities to operational pains or qualified customer evidence.", priority: "P1", mappedKeyword: "job management software uk plus supporting feature terms", icpPain: "Buyers need specific reasons the platform reduces paper, improves dispatch and shortens administrative handoffs.", feature: "Connected workflow, field app, customer portal, integrations, BI and automation", advantage: "Groups capabilities around real buyer jobs", benefit: "Your buyer can compare concrete benefits and source-qualified outcomes", proposedCopy: getappBenefits, fieldLimit: 4000, proof: { customer: `${PROOF.serious.customer}; ${PROOF.eft.customer}; ${PROOF.baydale.customer}`, qualification: `${PROOF.serious.qualification} ${PROOF.eft.qualification} ${PROOF.baydale.qualification}`, url: `${PROOF.serious.url} | ${PROOF.eft.url} | ${PROOF.baydale.url}` }, sourceUrl: HOME_URL });

for (const category of categoryNames) {
  const meta = categoryMeta[category];
  addRow({ channel: "GetApp", field: "Short Description", category, currentCopy: getappCurrent[category], issue: category === "Calendar" || category === "Forms Automation" ? "The category inherits generic default copy and does not answer the category intent." : "The current copy repeats a generic platform formula and gives limited category-specific workflow detail.", priority: category === "Calendar" || category === "Forms Automation" ? "P0" : "P2", mappedKeyword: meta.kw, icpPain: meta.pain, feature: meta.feature, advantage: meta.advantage, benefit: meta.benefit, proposedCopy: getappProposed[category], fieldLimit: 300, sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL} | ${PORTAL_BASE}/getapp#content-header` });
}

const capterraProofByCategory = {
  "HVAC": PROOF.ebgas,
  "Janitorial": PROOF.ccis,
  "Security System Installer": PROOF.baydale,
};

for (const category of categoryNames) {
  const meta = categoryMeta[category];
  const proof = capterraProofByCategory[category];
  const missingCustom = category === "Calendar" || category === "Forms Automation";
  addRow({
    channel: "Capterra",
    field: "Long Description",
    category,
    currentCopy: capterraCurrent[category][0],
    issue: missingCustom
      ? "The category inherits the generic default description and does not answer category-specific buyer intent."
      : "The current copy repeats promotional, paperless and ROI language across categories without a distinct buyer workflow or qualified outcome.",
    priority: missingCustom ? "P0" : "P2",
    mappedKeyword: meta.kw,
    icpPain: meta.pain,
    feature: meta.feature,
    advantage: meta.advantage,
    benefit: meta.benefit,
    proposedCopy: capterraProposed[category].long,
    fieldLimit: 1000,
    proof,
    sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL} | ${PORTAL_BASE}/capterra#content-header`,
  });
  addRow({
    channel: "Capterra",
    field: "Short Description",
    category,
    currentCopy: capterraCurrent[category][1],
    issue: missingCustom
      ? "The category inherits the generic default short description and does not identify the category workflow."
      : "The current short copy repeats plan, manage, schedule and track language without a distinctive category benefit.",
    priority: missingCustom ? "P0" : "P2",
    mappedKeyword: meta.kw,
    icpPain: meta.pain,
    feature: meta.feature,
    advantage: meta.advantage,
    benefit: meta.benefit,
    proposedCopy: capterraProposed[category].short,
    fieldLimit: 135,
    sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL} | ${PORTAL_BASE}/capterra#content-header`,
  });
}

const softwareAdviceCurrent = "BigChange provides all-in-one job management software for UK field teams. It combines customer relationship management (CRM), job scheduling, live tracking, field resource management, financial management, and business intelligence into one platform. Now with AI automations and digital workers (AI agents) that help you accomplish more with less.\n\nBigChange helps field service businesses across the UK win more work, increase the capacity of their teams, accelerate invoicing & transform cash flow. All whilst reducing operational costs and admin time. Additionally, with easy-to-use integrations with Sage, Xero, Quickbooks & other accounting softwares, BigChange seamlessly integrate your accounting.\n\nLoved by office and field teams alike, our customers are achieving industry leading growth and return on investment. The BigChange team is committed to customer success and no matter your sector or whether you have a mobile workforce of 10 or a 100, we’re here to make a big difference to the way you work and to help your business grow stronger.";
const softwareAdviceProposed = `BigChange is job management software for UK field service teams that connects office staff, engineers, vehicles, customers and finances in one system. If your day is slowed by paper job sheets, disconnected software, repeated phone calls or updates that reach the office too late, BigChange gives your team a shared view of every job from enquiry to invoice.\n\nSchedulers can assign work by engineer skills, location and availability, see live job status, respond to urgent call-outs and adjust the day without rebuilding a spreadsheet. Field engineers receive jobs, site history, notes and documents on the mobile app. They can complete digital job sheets, capture photos and signatures, record time and update progress while they are on site. The office gets the information it needs sooner, with fewer calls back to the field.\n\nBigChange combines CRM, job scheduling, live vehicle tracking, quotes, invoices, customer communications and business intelligence. Automated booking confirmations and ETA updates help keep customers informed. Online portals let customers request work, track progress and access job records. Reporting dashboards bring job, team, customer and financial information together so managers can spot problems and act with current data.\n\nFor teams that want more automation, BigChange Lightning adds AI tools for plain-language business questions, pre-job briefs, field documentation, customer summaries and technician onboarding. These tools work with data already held in BigChange to reduce repetitive preparation and reporting.\n\nThe platform supports UK businesses across plumbing and heating, HVAC, electrical contracting, fire and security, facilities and building maintenance, industrial doors, equipment hire, drainage, waste and environmental services. It can be configured around different worksheets, job types and service requirements.\n\nThe customer results are specific to each operation. SES Home Services reports that skills, location and availability-based scheduling increased daily job efficiency by up to 20% per engineer. BigChange also provides 24/7 access to its UK-based RoadCrew support team, a customer success manager and training through BigChange University and its Help Centre.\n\nBigChange is suited to teams that need to replace disconnected tools with one job management workflow that keeps the office, field team and customer working from the same information.`;

addRow({ channel: "Software Advice", field: "Long Description", category: "Default", currentCopy: softwareAdviceCurrent, issue: "The current copy repeats promotional outcomes, uses first-person language and does not guide a buyer through fit, workflow, support or qualified proof.", priority: "P1", mappedKeyword: "job management software uk (P1, confidence 95)", icpPain: "Buyers need help recognising their workflow, evaluating fit and understanding adoption support.", feature: "Connected job lifecycle, Lightning automation, mobile workflows and UK support", advantage: "Explains how the platform changes work for schedulers, engineers, managers and customers", benefit: "Your buyer can assess fit with less ambiguity", proposedCopy: softwareAdviceProposed, fieldLimit: 4000, proof: PROOF.ses, sourceUrl: `${HOME_URL} | ${KEYWORD_MAP_URL} | ${PORTAL_BASE}/softwareadvice#content-header` });

const captionRows = [
  ["Capterra", "Screenshot Caption 1", "UK job management cockpit", "Plan the day from one scheduling view. Match engineers to jobs by skill, location and availability, then update assignments as urgent work and delays change the schedule."],
  ["Capterra", "Screenshot Caption 2", "UK job management reporting", "Turn live job, customer and financial data into a clearer operating view. Track performance, spot exceptions and answer questions without rebuilding reports in spreadsheets."],
  ["Capterra", "Screenshot Caption 3", "UK Fleet tracking", "See engineers, vehicles and active jobs on one live map. Find the nearest suitable resource, review journey history and keep the office informed without manual check-ins."],
  ["Software Advice", "Screenshot Caption 1", "UK job management cockpit", "Replace the scheduling spreadsheet with one live view of jobs and engineers. Dispatch by skill, location and availability, then send changes directly to the field team."],
  ["Software Advice", "Screenshot Caption 2", "UK job management reports", "Give managers a current view of jobs, customers and finances. Dashboards make it easier to spot delays, review performance and decide where attention is needed."],
  ["Software Advice", "Screenshot Caption 3", "UK job management fleet tracking", "When an urgent job arrives, see which suitable engineer is nearby and available. Live vehicle and job visibility helps dispatchers respond without repeated phone calls."],
  ["GetApp", "Screenshot Caption 1", "UK job management cockpit", "Coordinate jobs from a visual scheduling cockpit that connects assignments, engineer availability and live status with updates sent to the mobile workforce."],
  ["GetApp", "Screenshot Caption 2", "UK job management reports", "Bring operational and financial reporting into one dashboard. Review job progress, team performance and business data without moving information between separate tools."],
  ["GetApp", "Screenshot Caption 3", "UK fleet management", "Map live vehicles and active jobs together. Use nearest-resource search, journey histories and geofence alerts to support dispatch, fleet oversight and customer updates."],
];

for (const [channel, field, currentCopy, proposedCopy] of captionRows) {
  addRow({ channel, field, category: "Media", currentCopy, issue: "The current caption names the screen but does not explain the workflow or buyer benefit.", priority: "P1", mappedKeyword: field.endsWith("1") ? "job scheduling software uk (P1)" : field.endsWith("2") ? "business reporting software (P2 supporting term)" : "vehicle tracking software uk (P1)", icpPain: field.endsWith("1") ? "Schedulers need to see how the day is planned and changed." : field.endsWith("2") ? "Managers need current operating information without rebuilding spreadsheets." : "Dispatchers need live resource context without repeated calls.", feature: field.endsWith("1") ? "Visual scheduling cockpit" : field.endsWith("2") ? "Operational and financial dashboard" : "Live fleet tracking map", advantage: field.endsWith("1") ? "Shows assignments, availability and live status together" : field.endsWith("2") ? "Brings decision information into one view" : "Combines vehicles, engineers and active jobs", benefit: field.endsWith("1") ? "Your buyer can see how scheduling pressure is handled" : field.endsWith("2") ? "Your buyer can see how managers spot exceptions" : "Your buyer can see how dispatch and fleet oversight improve", proposedCopy, fieldLimit: 255, sourceUrl: `${PORTAL_BASE}/${channel === "Software Advice" ? "softwareadvice" : channel.toLowerCase()}/screenshots#content-header | ${HOME_URL}` });
}

for (const channel of ["Capterra", "Software Advice", "GetApp"]) {
  addRow({ channel, field: "Video Recommendation", category: "Media", currentCopy: OLD_VIDEO_URL, issue: "The shared overview was published 15 December 2022 and does not reflect BigChange Lightning or the current 2026 positioning.", priority: "P1", mappedKeyword: "job management software uk plus current product entity alignment", icpPain: "Buyers need a current product demonstration rather than a dated brand overview.", feature: "BigChange Lightning product demonstration", advantage: "Shows the current AI layer and connected field-service workflows", benefit: "Your buyer gets a clearer, current view of the product before conversion", proposedCopy: NEW_VIDEO_URL, fieldLimit: "URL field", sourceUrl: `${OLD_VIDEO_URL} | ${NEW_VIDEO_URL} | https://www.bigchange.com/lightning`, proofStatus: "Verified public and embeddable on 2026-09-23. Confirm channel fit and package availability at publication." });
}

const pricingRows = [
  ["Vehicle Tracking", "This plan is designed for vehicle tracking with the driver mobile app.", "For teams that need live fleet visibility. View engineers, technicians and vehicles on a map, find the nearest suitable resource for urgent work, review journey histories and use geofence alerts for key locations. Driver behaviour and electronic vehicle checks help the office monitor fleet activity."],
  ["Job Management", "All–in–one mobile workforce management includes free vehicle tracking with every mobile user.", "For office and mobile teams that want one workflow from enquiry to invoice. Job Management connects CRM, team planning, scheduling, live tracking, quotes, invoices, worksheets, workflows, job cards, customer booking and performance dashboards. Engineers receive job information on the mobile app while office teams see live progress and completed records."],
  ["Job Management Plus", "JobWatchPlus is charged per mobile user per month and includes fully managed rugged Samsung tablets.", "Job Management Plus adds a managed rugged tablet package for field users to the core Job Management workflow. Keep office and field information connected while mobile teams receive jobs, capture records and return completed work through a managed device."],
  ["Job Management Unlimited", "All-in-one job management including rugged tablet or smartphone, unlimited calls + data and hard-wired vehicle tracking for mobile users.", "Job Management Unlimited adds a rugged tablet or smartphone, mobile connectivity and hard-wired vehicle tracking for field users to the core Job Management workflow. Keep jobs, field records, people and vehicles connected from one operating view."],
];

for (const [category, currentCopy, proposedCopy] of pricingRows) {
  addRow({ channel: "Cross-channel", field: "Pricing Plan Description", category, currentCopy, issue: "The plan description is dated and the current public pricing page does not display this package or amount. Portal plan prices also conflict with the pricing-details field.", priority: "P0", mappedKeyword: category === "Vehicle Tracking" ? "vehicle tracking software uk (P1)" : "job management software uk (P1)", icpPain: "Buyers need current inclusions and a consistent billing basis.", feature: category === "Vehicle Tracking" ? "Fleet visibility and driver tools" : "Job management workflow and mobile package", advantage: "Explains the intended plan fit without repeating an unverified price", benefit: "Your buyer gets clearer plan context while commercial terms remain verification-gated", proposedCopy, fieldLimit: 1000, sourceUrl: `${PRICING_URL} | ${PORTAL_BASE}/pricing#content-header`, proofStatus: "Blocked for publication until BigChange confirms package, price, billing unit and included terms." });
}

const pricingDetailsCurrent = "Vehicle Tracking = £14.95 per vehicle, per month\nJobWatch = £69.95 per vehicle, per month\nJobWatch Plus = £99.95 per vehicle, per month";
const pricingDetailsProposed = "BigChange provides pricing by quotation. The current UK pricing page states that plans include support, CRM, job scheduling, a mobile app, live tracking, quotes and invoices, business intelligence and the collaboration network. Optional extras listed publicly include AI dashcams, fleet services, fuel cards, Data as a Service and mobile hardware or data packages. Final pricing may depend on office and mobile users, vehicle-tracking hardware, installation, optional services and contract terms.";
addRow({ channel: "Cross-channel", field: "Pricing Details", category: "Default", currentCopy: pricingDetailsCurrent, issue: "The field lists JobWatch at £69.95 while the active Job Management plan displays £79.95. The page was last updated 16 May 2024, and the current public pricing page is quote-based.", priority: "P0", mappedKeyword: "job management software uk (P1)", icpPain: "Conflicting public prices undermine buyer trust and lead quality.", feature: "Quote-based pricing with plan inclusions and optional extras", advantage: "Avoids publishing unresolved amounts while explaining pricing variables", benefit: "Your buyer sees a consistent commercial framework", proposedCopy: pricingDetailsProposed, fieldLimit: 5000, sourceUrl: `${PRICING_URL} | ${PORTAL_BASE}/pricing#content-header`, proofStatus: "Blocked for publication until the £79.95 versus £69.95 conflict and 2024 freshness are resolved." });

const headers = [
  "channel", "field", "category", "current copy", "issue", "priority", "mapped keyword", "ICP pain",
  "feature", "advantage", "benefit", "proposed copy", "field limit", "character count", "customer proof",
  "proof qualification", "source URL", "checked date", "proof status",
];

const channelOrder = new Map([["Capterra", 1], ["Software Advice", 2], ["GetApp", 3], ["Cross-channel", 4]]);
const fieldOrder = new Map([
  ["Long Description", 1], ["Short Description", 2], ["Target Market", 3], ["Tagline", 4], ["Benefits", 5],
  ["Screenshot Caption 1", 6], ["Screenshot Caption 2", 7], ["Screenshot Caption 3", 8], ["Video Recommendation", 9],
  ["Pricing Plan Description", 10], ["Pricing Details", 11],
]);
const categoryOrder = new Map([["Default", 0], ...categoryNames.map((name, index) => [name, index + 1]), ["Media", 100]]);

rows.sort((a, b) =>
  (channelOrder.get(a.channel) ?? 99) - (channelOrder.get(b.channel) ?? 99)
  || (categoryOrder.get(a.category) ?? 99) - (categoryOrder.get(b.category) ?? 99)
  || (fieldOrder.get(a.field) ?? 99) - (fieldOrder.get(b.field) ?? 99)
);

function fail(message) {
  throw new Error(`QA failure: ${message}`);
}

function escapeCsv(value) {
  const string = String(value ?? "");
  return `"${string.replaceAll('"', '""')}"`;
}

function isNumericLimit(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function validateRows() {
  if (rows.length !== 109) fail(`expected 109 rows, found ${rows.length}`);
  for (const [index, row] of rows.entries()) {
    for (const header of headers) {
      if (row[header] === undefined || row[header] === null || row[header] === "") {
        fail(`row ${index + 1} has blank required column '${header}'`);
      }
    }
    if (row["character count"] !== row["proposed copy"].length) fail(`row ${index + 1} character count mismatch`);
    if (isNumericLimit(row["field limit"]) && row["character count"] > row["field limit"]) {
      fail(`row ${index + 1} exceeds ${row["field limit"]} characters with ${row["character count"]}`);
    }
    if (/[;—–]/u.test(row["proposed copy"])) fail(`row ${index + 1} contains prohibited punctuation`);
    if (/\b(best|leading|industry[- ]leading|unbeatable|unstoppable)\b/iu.test(row["proposed copy"])) fail(`row ${index + 1} contains hype language`);
    if (row.channel === "Capterra" && /\b(we|our|us)\b/iu.test(row["proposed copy"])) fail(`row ${index + 1} uses first-person Capterra copy`);
    if (["Short Description", "Tagline"].includes(row.field) || row.field.startsWith("Screenshot Caption")) {
      if (/\b(?:Rilmac|SES|Baydale|EB Gas|Serious Waste|EFT Systems|Flow Free|CC Infrastructure)\b/u.test(row["proposed copy"])) {
        fail(`row ${index + 1} puts customer proof in a short field`);
      }
    }
    const customerMetric = /(?:%|30 to 40 reporting hours|around 60 jobs|approximately 30%)/u.test(row["proposed copy"]);
    if (customerMetric && row["customer proof"] === "None") fail(`row ${index + 1} has a customer metric without proof metadata`);
    if (customerMetric && (!row["source URL"].includes("bigchange.com/success-stories/") || row["checked date"] !== CHECKED_DATE)) {
      fail(`row ${index + 1} has incomplete metric provenance`);
    }
  }

  const proseRows = rows.filter(row => !row.field.startsWith("Screenshot Caption") && row.field !== "Video Recommendation");
  const seenCopy = new Map();
  for (const row of proseRows) {
    const key = row["proposed copy"].trim().toLowerCase();
    if (seenCopy.has(key)) fail(`duplicate proposed prose in rows ${seenCopy.get(key)} and ${row.channel}/${row.category}/${row.field}`);
    seenCopy.set(key, `${row.channel}/${row.category}/${row.field}`);
  }

  const proofUsage = new Map();
  for (const row of rows) {
    for (const proof of Object.values(PROOF)) {
      if (row["source URL"].includes(proof.url)) proofUsage.set(proof.url, (proofUsage.get(proof.url) ?? 0) + 1);
    }
  }
  for (const [url, count] of proofUsage) {
    if (count > 2) fail(`proof source used ${count} times: ${url}`);
  }
}

function buildCsv() {
  return [headers.map(escapeCsv).join(","), ...rows.map(row => headers.map(header => escapeCsv(row[header])).join(","))].join("\r\n") + "\r\n";
}

function countCsvRecords(csvText) {
  let inQuotes = false;
  let records = 0;
  for (let index = 0; index < csvText.length; index += 1) {
    const character = csvText[index];
    if (character === '"') {
      if (inQuotes && csvText[index + 1] === '"') index += 1;
      else inQuotes = !inQuotes;
    } else if (character === "\n" && !inQuotes) {
      records += 1;
    }
  }
  return records;
}

function priorityCount(priority) {
  return rows.filter(row => row.priority === priority).length;
}

function channelCount(channel) {
  return rows.filter(row => row.channel === channel).length;
}

function buildMarkdown() {
  return `# BigChange G2 Digital Markets SEO/AEO copy audit

Reviewed and implemented ${CHECKED_DATE}. Scope: UK-English Capterra, Software Advice and GetApp listing copy in G2 Digital Markets. The authenticated Chrome session was used to save and reload-verify 104 eligible fields. Five pricing fields were deliberately left unchanged because the portal and public pricing evidence conflict.

## Outcome

The package contains 109 ready-to-review rows:

| Channel or field group | Rows | Coverage |
|---|---:|---|
| Capterra | ${channelCount("Capterra")} | Default long, short and target market; long and short copy for all 28 categories; three captions; one video URL |
| Software Advice | ${channelCount("Software Advice")} | Long description; three captions; one video URL |
| GetApp | ${channelCount("GetApp")} | Default long, short, tagline and benefits; one description for all 28 categories; three captions; one video URL |
| Cross-channel pricing | ${channelCount("Cross-channel")} | Four plan descriptions and pricing details |

The XLSX and CSV matrices contain current copy, issue, priority, mapped keyword, ICP pain, feature, advantage, benefit, proposed copy, exact character count and proof provenance for every row.

## Priority 0 findings

1. Calendar and Forms Automation now use custom copy on both Capterra and GetApp. The live listing-completion score increased from 96% to 100% after the description updates were saved.
2. Pricing needs owner confirmation before publication. The active Job Management plan shows £79.95, while Pricing Details still says JobWatch costs £69.95 per vehicle per month. The portal pricing record was last updated 16 May 2024. BigChange's current public pricing page is quote-based and does not validate the portal amounts.
3. BigChange has 28 selected categories, zero reviews in the last 90 days and a 0.0 average rating for that period. Copy cannot offset missing recent review evidence.

## Copy strategy

- Lead applicable default copy with a natural form of **job management software for UK field teams**. This supports external SEO, buyer comprehension and answer extraction. It is not presented as a disclosed G2 or Capterra ranking factor.
- Use the keyword map's P1 terms directly where they fit the field. P2 terms remain supporting language because the map labels ownership research as incomplete.
- Build substantive fields around feature, operational advantage and buyer benefit. The copy addresses scheduling pressure, paper job sheets, disconnected office and field work, weak job visibility, delayed records, invoicing friction and limited operating control.
- Keep short descriptions, taglines and captions free of customer metrics. Customer outcomes appear only in long evaluation fields with named attribution, qualifiers and direct source URLs.
- Follow [Capterra's profile guidelines](https://www.capterra.com/legal/listing-guidelines/): third-person brand references, unique and accurate copy, and no calls to action, embedded links, comparative claims or unsupported superlatives in pasted descriptions.

## Marketplace SEO and AEO findings

- [G2's research methodology](https://documentation.g2.com/docs/research-scoring-methodologies) documents review responses, volume, recency, completeness, readability, source and market-presence signals. It does not disclose description keyword frequency as a G2 Score factor.
- [G2's product-information guidance](https://documentation.g2.com/docs/product-information) supports optimising profile details for branded search and long-tail relevance while keeping the official product name unchanged.
- [Capterra's research methodology](https://www.capterra.com/resources/proprietary-data-research/) uses recent ratings and popularity signals for Shortlist research. [Capterra's transparency guidance](https://www.capterra.com/resources/how-we-ensure-transparency/) explains that sponsored placements can affect marketplace position.
- The practical order of operations is category accuracy, complete structured fields, fresh representative reviews, current media and consistent entity language. Keyword placement strengthens relevance and comprehension within that larger system.

## Customer proof controls

| Customer | Approved metric used | Important qualification |
|---|---|---|
| Rilmac Asbestos Services | Approximately 30% less back-office administration resource | Named-customer result; used once; no typical-outcome claim |
| SES Home Services | Up to 20% greater daily job efficiency per engineer | Retains "up to," daily and per-engineer context |
| Baydale Control Systems | 80% faster job allocation | Tied to stock visibility; used twice |
| EB Gas Services | 20% more routine service jobs allocated | No published measurement period; attribution retained |
| Serious Waste Management | More than 60% less time to create and issue invoices | Conflicting growth figures excluded |
| EFT Systems | 30 to 40 reporting hours saved each month | Explicitly credits BigChange, Snowflake Data as a Service and Rathbone Results |
| Flow Free Drainage | Two office staff handling about 60 jobs daily versus five or six before | Legacy JobWatch story; separate growth claim excluded |
| CC Infrastructure Services | 20% less administrative resource | Undefined waste claim excluded |

All eight source pages returned successfully and displayed the supporting metric on ${CHECKED_DATE}. None exposed a visible publication date, so the matrix records the verification date instead of inventing one.

## Media recommendations

- The shared 2022 overview was replaced on all three channels with [BigChange Lightning Demo - Take a Look!](https://www.youtube.com/watch?v=4fcnxzGWkN0). The video was published 18 May 2026, runs 4 minutes 27 seconds and exposes an embeddable YouTube URL.
- Generic screenshot labels were replaced with channel-specific captions that explain the scheduling, reporting and fleet-tracking workflow shown on screen.

## Pricing recommendation

Do not publish new pricing descriptions until BigChange confirms plan names, amounts, billing units, included hardware, installation, mobile data, support, contract and VAT terms. The matrix supplies verification-gated draft language and a quote-based pricing-details alternative that does not repeat the unresolved amounts.

## Ethical review programme

Maintain a continuous, representative review programme. Invite a broad customer mix and ask reviewers to describe their role, job-to-be-done, implementation experience and outcome in their own words. Do not cherry-pick only satisfied customers or script keyword-rich review language. Track recent review volume, latest review date, category attribution and response completeness separately from profile-copy performance.

## Validation record

- Matrix QA: 109 rows; ${priorityCount("P0")} P0, ${priorityCount("P1")} P1 and ${priorityCount("P2")} P2 recommendations.
- Limit QA: every numeric portal limit passes; each stored character count matches the proposed copy.
- Proof QA: every metric-bearing row contains a named customer, sector, precise metric, qualifier, direct BigChange case-study URL, checked date and proof status.
- Short-field QA: no named customer metric appears in a short description, tagline or screenshot caption.
- Style QA: proposed copy contains no em dashes, en dashes, semicolons, unsupported superlatives or Capterra first-person brand language.
- Uniqueness QA: all prose fields are distinct. The same verified YouTube URL is intentionally recommended across three channel-specific video fields.
- Workbook QA: CSV and XLSX use the same 109-row source array. The workbook contains filterable, wrapped and frozen matrix headers plus summary and proof-ledger tabs.

## Live implementation record

1. Saved and reload-verified all 59 Capterra description fields, including custom Calendar and Forms Automation copy.
2. Saved and reload-verified the Software Advice long description.
3. Saved and reload-verified all 32 GetApp description fields, including custom Calendar and Forms Automation copy.
4. Saved and reload-verified nine screenshot captions and the 2026 Lightning video on all three channels.
5. Confirmed the live listing-completion score is 100%.
6. Left all five pricing-copy fields unchanged pending commercial verification of the conflicting plan amounts and terms.
7. Re-audit category fit, structured fields and review recency quarterly.

## Primary sources

- [BigChange homepage](${HOME_URL})
- [BigChange pricing page](${PRICING_URL})
- [BigChange keyword map](${KEYWORD_MAP_URL})
- [Current BigChange YouTube demo](${NEW_VIDEO_URL})
- Direct BigChange customer-story URLs are recorded beside every metric-bearing row in the matrix.
`;
}

async function buildWorkbook() {
  const workbook = Workbook.create();
  const summary = workbook.worksheets.add("Audit Summary");
  const matrix = workbook.worksheets.add("Copy Matrix");
  const proof = workbook.worksheets.add("Proof Ledger");
  const fontName = "Arial";
  const navy = "#143A52";
  const blue = "#1B6A8F";
  const orange = "#F47C20";
  const lightBlue = "#EAF4F8";
  const lightOrange = "#FFF0E6";
  const lightGrey = "#F3F5F6";
  const red = "#FDE8E7";
  const amber = "#FFF4CC";

  summary.showGridLines = false;
  summary.getRange("A1:H1").merge();
  summary.getRange("A1").values = [["BigChange G2 Digital Markets SEO/AEO copy package"]];
  summary.getRange("A1:H1").format.font = { name: fontName, size: 18, bold: true, color: navy };
  summary.getRange("A2:H2").merge();
  summary.getRange("A2").values = [["UK-English Capterra, Software Advice and GetApp implementation | Saved and verified 2026-09-23 | 104 eligible fields updated"]];
  summary.getRange("A2:H2").format.font = { name: fontName, size: 10, italic: true, color: "#55636B" };
  summary.getRange("A3:H3").format.borders = { bottom: { style: "thin", color: orange } };
  summary.getRange("A5:C5").values = [["Decision", "Evidence", "Recommendation"]];
  summary.getRange("A6:C10").values = [
    ["Completion", "100%; Calendar and Forms Automation are customised on Capterra and GetApp", "Re-audit completeness and category fit quarterly"],
    ["Pricing", "£79.95 active plan versus £69.95 Pricing Details; last updated 2024-05-16", "Block publication until the commercial owner confirms current terms"],
    ["Reviews", "0 reviews and 0.0 average rating in the last 90 days", "Run a continuous, representative and unscripted review programme"],
    ["Video", "2026 Lightning demo is saved on Capterra, Software Advice and GetApp", "Revalidate the promoted capabilities when the package changes"],
    ["Keywords", "P1 terms are high-confidence; P2 ownership remains unresolved", "Use P1 naturally and treat P2 as supporting vocabulary"],
  ];
  summary.getRange("E5:F5").values = [["Package count", "Rows"]];
  summary.getRange("E6:F11").values = [
    ["All rows", rows.length], ["Capterra", channelCount("Capterra")], ["Software Advice", channelCount("Software Advice")],
    ["GetApp", channelCount("GetApp")], ["Cross-channel pricing", channelCount("Cross-channel")], ["P0 recommendations", priorityCount("P0")],
  ];
  summary.getRange("A13:H13").merge();
  summary.getRange("A13").values = [["Use the Copy Matrix for paste-ready drafts and row-level proof. Pricing rows remain verification-gated."]];
  summary.getRange("A13:H13").format = { fill: lightOrange, font: { name: fontName, bold: true, color: navy }, wrapText: true };
  summary.getRange("A5:C5").format = { fill: navy, font: { name: fontName, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center" };
  summary.getRange("E5:F5").format = { fill: blue, font: { name: fontName, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
  summary.getRange("A6:C10").format = { font: { name: fontName, size: 10, color: "#1F2933" }, wrapText: true, verticalAlignment: "top" };
  summary.getRange("E6:F11").format = { font: { name: fontName, size: 10, color: "#1F2933" }, verticalAlignment: "center" };
  summary.getRange("F6:F11").format.horizontalAlignment = "right";
  summary.getRange("A5:C10").format.borders = {
    top: { style: "thin", color: "#CBD5DB" },
    bottom: { style: "thin", color: "#CBD5DB" },
    left: { style: "thin", color: "#CBD5DB" },
    right: { style: "thin", color: "#CBD5DB" },
    insideVertical: { style: "thin", color: "#E1E7EA" },
  };
  summary.getRange("E5:F11").format.borders = { preset: "outside", style: "thin", color: "#CBD5DB" };
  summary.getRange("A1:H13").format.font.name = fontName;
  summary.getRange("A:A").format.columnWidth = 24;
  summary.getRange("B:B").format.columnWidth = 44;
  summary.getRange("C:C").format.columnWidth = 46;
  summary.getRange("D:D").format.columnWidth = 4;
  summary.getRange("E:E").format.columnWidth = 26;
  summary.getRange("F:F").format.columnWidth = 12;
  summary.getRange("G:H").format.columnWidth = 4;
  summary.getRange("1:1").format.rowHeight = 28;
  summary.getRange("6:10").format.rowHeight = 58;
  summary.getRange("13:13").format.rowHeight = 36;
  summary.tabColor = orange;

  matrix.showGridLines = false;
  matrix.getRange("A1:S1").merge();
  matrix.getRange("A1").values = [["BigChange listing rewrite matrix"]];
  matrix.getRange("A1:S1").format.font = { name: fontName, size: 16, bold: true, color: navy };
  matrix.getRange("A2:S2").merge();
  matrix.getRange("A2").values = [["109 fields | UK English | character counts include spaces and punctuation | proof checked 2026-09-23"]];
  matrix.getRange("A2:S2").format.font = { name: fontName, size: 10, italic: true, color: "#55636B" };
  matrix.getRange("A3:S3").format.borders = { bottom: { style: "thin", color: orange } };
  matrix.getRange("A4:S4").values = [headers];
  const data = rows.map(row => headers.map(header => row[header]));
  matrix.getRangeByIndexes(4, 0, data.length, headers.length).values = data;
  matrix.getRange(`A4:S${rows.length + 4}`).format.font = { name: fontName, size: 9, color: "#1F2933" };
  matrix.getRange("A4:S4").format = { fill: navy, font: { name: fontName, size: 9, bold: true, color: "#FFFFFF" }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "inside", style: "thin", color: "#FFFFFF" } };
  matrix.getRange(`A5:S${rows.length + 4}`).format.wrapText = true;
  matrix.getRange(`A5:S${rows.length + 4}`).format.verticalAlignment = "top";
  matrix.getRange(`M5:N${rows.length + 4}`).format.horizontalAlignment = "right";
  matrix.getRange(`A5:S${rows.length + 4}`).format.borders = { bottom: { style: "thin", color: "#E1E7EA" } };
  matrix.getRange(`F5:F${rows.length + 4}`).conditionalFormats.add("containsText", { text: "P0", format: { fill: red, font: { bold: true, color: "#9B1C1C" } } });
  matrix.getRange(`F5:F${rows.length + 4}`).conditionalFormats.add("containsText", { text: "P1", format: { fill: amber, font: { bold: true, color: "#7A5200" } } });
  matrix.getRange(`F5:F${rows.length + 4}`).conditionalFormats.add("containsText", { text: "P2", format: { fill: lightBlue, font: { bold: true, color: blue } } });
  matrix.getRange(`S5:S${rows.length + 4}`).conditionalFormats.add("containsText", { text: "Blocked", format: { fill: red, font: { bold: true, color: "#9B1C1C" } } });
  matrix.tables.add(`A4:S${rows.length + 4}`, true, "BigChangeCopyMatrix");
  matrix.freezePanes.freezeRows(4);
  matrix.freezePanes.freezeColumns(3);
  const widths = [15, 23, 24, 58, 48, 10, 42, 44, 42, 42, 42, 78, 12, 14, 50, 58, 70, 13, 54];
  widths.forEach((width, index) => matrix.getRangeByIndexes(0, index, rows.length + 4, 1).format.columnWidth = width);
  matrix.getRange("1:1").format.rowHeight = 26;
  matrix.getRange("4:4").format.rowHeight = 40;
  matrix.getRange(`5:${rows.length + 4}`).format.rowHeight = 88;
  matrix.tabColor = blue;

  proof.showGridLines = false;
  proof.getRange("A1:F1").merge();
  proof.getRange("A1").values = [["BigChange customer proof ledger"]];
  proof.getRange("A1:F1").format.font = { name: fontName, size: 16, bold: true, color: navy };
  proof.getRange("A2:F2").merge();
  proof.getRange("A2").values = [["Only the qualified treatment below is approved for this copy package. Live pages checked 2026-09-23."]];
  proof.getRange("A2:F2").format.font = { name: fontName, size: 10, italic: true, color: "#55636B" };
  const proofHeaders = ["Customer", "Sector", "Approved metric", "Qualification", "Direct source URL", "Status"];
  proof.getRange("A4:F4").values = [proofHeaders];
  const proofData = [
    ["Rilmac Asbestos Services Division", "Construction and asbestos abatement", "Approximately 30% less back-office administration resource", PROOF.rilmac.qualification, PROOF.rilmac.url, "Verified"],
    ["SES Home Services", "Utilities, plumbing, heating and drainage", "Up to 20% greater daily job efficiency per engineer", PROOF.ses.qualification, PROOF.ses.url, "Verified"],
    ["Baydale Control Systems", "Fire and security", "Jobs allocated 80% faster", PROOF.baydale.qualification, PROOF.baydale.url, "Verified"],
    ["EB Gas Services", "Plumbing, heating and HVAC", "20% more routine service jobs allocated", PROOF.ebgas.qualification, PROOF.ebgas.url, "Verified"],
    ["Serious Waste Management", "Waste management", "More than 60% less time to create and issue invoices", PROOF.serious.qualification, PROOF.serious.url, "Verified"],
    ["EFT Systems", "Fire and security", "30 to 40 reporting hours saved each month", PROOF.eft.qualification, PROOF.eft.url, "Verified"],
    ["Flow Free Drainage", "Drainage, waste and environmental", "Two staff handling about 60 jobs daily versus five or six before", PROOF.flowfree.qualification, PROOF.flowfree.url, "Verified; legacy branding"],
    ["CC Infrastructure Services", "Specialist cleaning and infrastructure coatings", "20% less administrative resource", PROOF.ccis.qualification, PROOF.ccis.url, "Verified"],
  ];
  proof.getRange("A5:F12").values = proofData;
  proof.getRange("A4:F4").format = { fill: navy, font: { name: fontName, size: 10, bold: true, color: "#FFFFFF" }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center" };
  proof.getRange("A5:F12").format = { font: { name: fontName, size: 9, color: "#1F2933" }, wrapText: true, verticalAlignment: "top", borders: { bottom: { style: "thin", color: "#E1E7EA" } } };
  proof.tables.add("A4:F12", true, "BigChangeProofLedger");
  proof.freezePanes.freezeRows(4);
  proof.freezePanes.freezeColumns(1);
  [26, 28, 42, 64, 72, 22].forEach((width, index) => proof.getRangeByIndexes(0, index, 12, 1).format.columnWidth = width);
  proof.getRange("4:4").format.rowHeight = 34;
  proof.getRange("5:12").format.rowHeight = 80;
  proof.tabColor = "#3C8D6C";

  const matrixInspect = await workbook.inspect({ kind: "table", range: `Copy Matrix!A1:S14`, include: "values,formulas", tableMaxRows: 14, tableMaxCols: 19, maxChars: 12000 });
  const summaryInspect = await workbook.inspect({ kind: "table", range: "Audit Summary!A1:F13", include: "values,formulas", tableMaxRows: 13, tableMaxCols: 6, maxChars: 6000 });
  const proofInspect = await workbook.inspect({ kind: "table", range: "Proof Ledger!A1:F12", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 6, maxChars: 8000 });
  const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
  if (errors.ndjson && errors.ndjson.includes('"value"')) fail("formula error string found in workbook");

  const tempDir = path.join(ROOT, "temp", "bigchange-g2-copy-qa");
  await fs.mkdir(tempDir, { recursive: true });
  for (const [sheetName, range, filename] of [
    ["Audit Summary", "A1:H13", "summary.png"],
    ["Copy Matrix", "A1:S14", "matrix.png"],
    ["Proof Ledger", "A1:F12", "proof.png"],
  ]) {
    const preview = await workbook.render({ sheetName, range, scale: 1.2, format: "png" });
    await fs.writeFile(path.join(tempDir, filename), new Uint8Array(await preview.arrayBuffer()));
  }

  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(XLSX_PATH);
  const finalPreview = await workbook.render({ sheetName: "Audit Summary", range: "A1:H13", scale: 1.2, format: "png" });
  await fs.writeFile(PREVIEW_PATH, new Uint8Array(await finalPreview.arrayBuffer()));
  return { matrixInspect: matrixInspect.ndjson, summaryInspect: summaryInspect.ndjson, proofInspect: proofInspect.ndjson, errorInspect: errors.ndjson };
}

validateRows();
await fs.mkdir(OUTPUT_DIR, { recursive: true });
await fs.writeFile(CSV_PATH, buildCsv(), "utf8");
await fs.writeFile(MD_PATH, buildMarkdown(), "utf8");
const workbookChecks = await buildWorkbook();

const csvText = await fs.readFile(CSV_PATH, "utf8");
const csvRecordCount = countCsvRecords(csvText);
if (csvRecordCount !== rows.length + 1) fail(`CSV expected ${rows.length + 1} records, found ${csvRecordCount}`);

console.log(JSON.stringify({ rows: rows.length, p0: priorityCount("P0"), p1: priorityCount("P1"), p2: priorityCount("P2"), csvPath: CSV_PATH, xlsxPath: XLSX_PATH, mdPath: MD_PATH, previewPath: PREVIEW_PATH, workbookChecks }, null, 2));
