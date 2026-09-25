import json
from pathlib import Path


def write_nonvault_proof_inputs(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    index_path = root / "customer-proof-index.json"
    ledger_path = root / "customer-proof-usage-ledger.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 1,
                "proof": [
                    {
                        "proof_id": "clockshark-customer-story-mabrys-electrical-service",
                        "customer": "Mabry's Electrical Service",
                        "source_type": "customer_story",
                        "industry": ["electrical", "field service"],
                        "region": ["US"],
                        "workflow_fit": [
                            "employee time theft",
                            "buddy punching",
                            "manual timekeeping",
                            "payroll",
                        ],
                        "themes": [
                            "buddy punching prevention",
                            "lost job sheets",
                            "digital time records",
                        ],
                        "public_url": "https://www.clockshark.com/testimonials/mabry-s-electrical-service-inc",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "evidence": (
                            "The public customer story describes manual rounding, lost job "
                            "sheets, buddy punching, employee meetings, and the reported "
                            "change after digital timekeeping."
                        ),
                        "last_verified": "2026-08-28",
                        "approved_quotes": [],
                        "approved_metrics": [],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "business",
                            "identity_display": "Mabry's Electrical Service",
                            "business_name": "Mabry's Electrical Service",
                            "platform": "ClockShark customer story",
                            "public_url": "https://www.clockshark.com/testimonials/mabry-s-electrical-service-inc",
                            "workflow_story": (
                                "Mabry's Electrical Service describes manual timekeeping, "
                                "lost job sheets, buddy punching, and digital time records."
                            ),
                            "verification_status": "public ClockShark customer story page",
                        },
                    },
                    {
                        "proof_id": "clockshark-customer-story-bear-down-builders",
                        "customer": "Bear Down Builders",
                        "source_type": "customer_story",
                        "industry": ["general contracting"],
                        "region": ["US"],
                        "workflow_fit": ["paper timesheets", "GPS", "payroll"],
                        "themes": ["inaccurate timesheets", "jobsite verification"],
                        "public_url": "https://www.clockshark.com/testimonials/bear-down-builders-llc",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "evidence": "The public story describes inaccurate paper timesheets.",
                        "last_verified": "2026-08-28",
                        "approved_quotes": [],
                        "approved_metrics": [],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "business",
                            "identity_display": "Bear Down Builders",
                            "business_name": "Bear Down Builders",
                            "platform": "ClockShark customer story",
                            "public_url": "https://www.clockshark.com/testimonials/bear-down-builders-llc",
                            "workflow_story": "Bear Down Builders describes inaccurate paper timesheets.",
                            "verification_status": "public ClockShark customer story page",
                        },
                    },
                    {
                        "proof_id": "simpro-customer-story-cross-brand",
                        "customer": "Cross Brand Customer",
                        "source_type": "customer_story",
                        "industry": ["electrical"],
                        "region": ["US"],
                        "workflow_fit": ["buddy punching"],
                        "themes": ["employee time theft"],
                        "public_url": "https://www.simprogroup.com/case-studies/cross-brand",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "evidence": "Cross-brand proof must not enter a ClockShark slate.",
                        "last_verified": "2026-08-28",
                    },
                    {
                        "proof_id": "clockshark-review-without-brand-contract",
                        "customer": "ClockShark reviewer",
                        "source_type": "review_site",
                        "industry": ["construction"],
                        "region": ["US"],
                        "workflow_fit": ["buddy punching"],
                        "themes": ["employee time theft"],
                        "public_url": "https://www.g2.com/products/clockshark/reviews/example",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "evidence": "Review rows are out of scope for the v1 non-vault contract.",
                        "last_verified": "2026-08-28",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    ledger_path.write_text(
        json.dumps({"version": 1, "uses": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    return index_path, ledger_path


BIGCHANGE_CAPTERRA_URL = (
    "https://www.capterra.co.uk/software/149479/jobwatch-powered-by-bigchange"
)


def write_bigchange_review_proof_inputs(root: Path) -> tuple[Path, Path]:
    """BigChange nonconnector fixtures for the Capterra review-proof extension."""
    root.mkdir(parents=True, exist_ok=True)
    index_path = root / "customer-proof-index.json"
    ledger_path = root / "customer-proof-usage-ledger.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 1,
                "proof": [
                    {
                        "proof_id": "bigchange-review-capterra-owner-job-scheduling",
                        "customer": "Dana R",
                        "source_type": "review_site",
                        "industry": ["field service"],
                        "region": ["UK"],
                        "workflow_fit": ["job scheduling", "field teams"],
                        "themes": ["job scheduling", "engineer visibility"],
                        "public_url": BIGCHANGE_CAPTERRA_URL,
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "evidence": (
                            "The public Capterra review describes faster job scheduling "
                            "and real-time visibility for field engineers."
                        ),
                        "last_verified": "2026-09-24",
                        "approved_quotes": [
                            {
                                "quote": "Job scheduling got so much faster with JobWatch.",
                                "status": "approved",
                            }
                        ],
                        "approved_metrics": [],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Dana R",
                            "business_name": "",
                            "person_name": "Dana R",
                            "role_title": "Operations Manager",
                            "platform": "Capterra",
                            "source_row_ref": "Capterra row 12",
                            "public_url": BIGCHANGE_CAPTERRA_URL,
                            "workflow_story": (
                                "Dana R describes faster job scheduling and clearer "
                                "engineer visibility after switching to JobWatch."
                            ),
                            "objective_fit": ["job scheduling", "field visibility"],
                            "copy_use": "paraphrased E-E-A-T story with same-paragraph source link",
                            "verification_status": "brand-captured public review source",
                        },
                    },
                    {
                        "proof_id": "bigchange-review-capterra-wrong-brand",
                        "customer": "Wrong brand reviewer",
                        "source_type": "review_site",
                        "industry": ["field service"],
                        "region": ["UK"],
                        "workflow_fit": ["job scheduling"],
                        "themes": ["job scheduling"],
                        "public_url": "https://www.capterra.com/p/166811/aroflo",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "evidence": "Wrong-brand Capterra page must not enter a BigChange slate.",
                        "last_verified": "2026-09-24",
                        "approved_quotes": [],
                        "approved_metrics": [],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Wrong brand reviewer",
                            "person_name": "Wrong brand reviewer",
                            "platform": "Capterra",
                            "public_url": "https://www.capterra.com/p/166811/aroflo",
                            "workflow_story": "Describes AroFlo, not BigChange.",
                        },
                    },
                    {
                        "proof_id": "bigchange-review-g2-wrong-platform",
                        "customer": "G2 reviewer",
                        "source_type": "review_site",
                        "industry": ["field service"],
                        "region": ["UK"],
                        "workflow_fit": ["job scheduling"],
                        "themes": ["job scheduling"],
                        "public_url": "https://www.g2.com/products/bigchange/reviews/example",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "evidence": "G2 review rows are out of scope for the Capterra review-proof extension.",
                        "last_verified": "2026-09-24",
                        "approved_quotes": [],
                        "approved_metrics": [],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "G2 reviewer",
                            "person_name": "G2 reviewer",
                            "platform": "G2",
                            "public_url": "https://www.g2.com/products/bigchange/reviews/example",
                            "workflow_story": "Describes job scheduling on G2, not Capterra.",
                        },
                    },
                    {
                        "proof_id": "bigchange-review-capterra-story-not-allowed",
                        "customer": "Not allowed reviewer",
                        "source_type": "review_site",
                        "industry": ["field service"],
                        "region": ["UK"],
                        "workflow_fit": ["job scheduling"],
                        "themes": ["job scheduling"],
                        "public_url": BIGCHANGE_CAPTERRA_URL,
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "evidence": "Row is not cleared for public E-E-A-T story use.",
                        "last_verified": "2026-09-24",
                        "approved_quotes": [],
                        "approved_metrics": [],
                        "review_story": {
                            "story_allowed": False,
                            "identity_type": "person",
                            "identity_display": "Not allowed reviewer",
                            "person_name": "Not allowed reviewer",
                            "platform": "Capterra",
                            "public_url": BIGCHANGE_CAPTERRA_URL,
                            "workflow_story": "Describes job scheduling but is not cleared for public use.",
                        },
                    },
                    {
                        "proof_id": "bigchange-review-capterra-unapproved",
                        "customer": "Unapproved reviewer",
                        "source_type": "review_site",
                        "industry": ["field service"],
                        "region": ["UK"],
                        "workflow_fit": ["job scheduling"],
                        "themes": ["job scheduling"],
                        "public_url": BIGCHANGE_CAPTERRA_URL,
                        "approval_status": "pending",
                        "public_copy_allowed": True,
                        "evidence": "Row is not yet approved for public use.",
                        "last_verified": "2026-09-24",
                        "approved_quotes": [],
                        "approved_metrics": [],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Unapproved reviewer",
                            "person_name": "Unapproved reviewer",
                            "platform": "Capterra",
                            "public_url": BIGCHANGE_CAPTERRA_URL,
                            "workflow_story": "Describes job scheduling but is not approved.",
                        },
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    ledger_path.write_text(
        json.dumps({"version": 1, "uses": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    return index_path, ledger_path
