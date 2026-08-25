from pathlib import Path

from data_sources.modules import industry_cluster_link_policy


def _article(body: str) -> str:
    return (
        "---\n"
        "artifact_type: blog\n"
        "brand: Simpro\n"
        "title: CRM for Electricians\n"
        "objective: Help electrical contractors compare CRM software.\n"
        "audience: Electrical contractor owners and operations managers\n"
        "region: US\n"
        "---\n"
        "# CRM for Electricians\n\n"
        f"{body}\n"
    )


def _rules(findings):
    return {finding["rule_id"] for finding in findings}


def test_article_requires_electrical_industry_link_for_single_trade_simpro_blog():
    findings = industry_cluster_link_policy.check_content(
        _article(
            "CRM for electricians should connect customer records, quotes, jobs, "
            "invoices and service history."
        )
    )

    assert "industry_cluster_link_missing" in _rules(findings)


def test_article_accepts_electrical_industry_link_in_intro():
    findings = industry_cluster_link_policy.check_content(
        _article(
            "CRM for electricians should connect customer records, quotes, jobs, "
            "invoices and service history. It should also fit the wider "
            "[electrical contractor software]"
            "(https://www.simprogroup.com/industries/electrical-software) stack."
        )
    )

    assert findings == []


def test_article_rejects_late_industry_cluster_link():
    filler = " ".join(f"word{i}" for i in range(301))
    findings = industry_cluster_link_policy.check_content(
        _article(
            "CRM for electricians should connect customer records, quotes, jobs, "
            f"invoices and service history. {filler} "
            "[electrical contractor software]"
            "(https://www.simprogroup.com/industries/electrical-software)"
        )
    )

    assert "industry_cluster_link_late" in _rules(findings)


def test_check_file_reads_article_body_not_frontmatter(tmp_path: Path):
    article = tmp_path / "crm.md"
    article.write_text(
        "---\n"
        "artifact_type: blog\n"
        "brand: Simpro\n"
        "title: CRM for Electricians\n"
        "objective: Help electrical contractors compare CRM software.\n"
        "audience: Electrical contractor owners and operations managers\n"
        "region: US\n"
        "hero_link: https://www.simprogroup.com/industries/electrical-software\n"
        "---\n"
        "# CRM for Electricians\n\n"
        "CRM for electricians should connect customer records, quotes, jobs, "
        "invoices and service history.\n",
        encoding="utf-8",
    )

    findings = industry_cluster_link_policy.check_file(article)

    assert "industry_cluster_link_missing" in _rules(findings)
