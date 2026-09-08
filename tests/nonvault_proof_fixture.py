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
