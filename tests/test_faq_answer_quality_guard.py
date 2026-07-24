import json
import subprocess
import sys
from pathlib import Path

import pytest

from data_sources.modules.faq_answer_quality_guard import check_content, check_file


REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = REPO_ROOT / "data_sources" / "modules" / "faq_answer_quality_guard.py"


def test_cli_blocks_there_is_no_generic_faq_opener(tmp_path):
    article_path = tmp_path / "article.md"
    article_path.write_text(
        (
            "# Article\n\n"
            "## Frequently Asked Questions\n\n"
            "### What is the average labor burden rate?\n\n"
            "There is no single average labor burden rate for trades. "
            "Calculate the rate from payroll taxes, benefits, insurance, "
            "paid time off and productive hours.\n"
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(GUARD_PATH), str(article_path), "--fail-on", "error"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["summary"]["error"] == 1
    assert payload["findings"][0]["rule_id"] == "faq_answer_generic_opener"


def article_with_answer(question, answer):
    return (
        "# Article\n\n"
        "## Frequently Asked Questions\n\n"
        f"### {question}\n\n"
        f"{answer}\n"
    )


@pytest.mark.parametrize(
    "answer",
    [
        "No universal trade is best for every woman. Compare local options.",
        "It depends on the work you prefer and the training available nearby.",
        "Pricing depends on users, implementation, add-ons and support.",
        "Plumbing website costs vary by build route and project scope.",
        "We don't know which option works best for every business.",
        "It is unclear which career produces the strongest outcome.",
        "There is insufficient data to give readers a useful answer.",
        "It is impossible to say which option will work.",
        "No BLS source ranks one occupation as best for women.",
        "Age alone does not determine which trade fits a career changer.",
        "Every business is different when it comes to software costs.",
    ],
)
def test_generic_openers_are_blocked(answer):
    findings = check_content(
        article_with_answer("What is the best option?", answer)
    )

    assert [finding["rule_id"] for finding in findings] == [
        "faq_answer_generic_opener"
    ]


@pytest.mark.parametrize(
    "question,answer",
    [
        (
            "What trade makes $100,000 a year?",
            "Elevator installation and repair averages $109,820 a year. "
            "Actual pay changes by location and experience.",
        ),
        (
            "What is AI field service software?",
            "AI field service software applies machine learning to service "
            "workflows such as scheduling, intake and documentation.",
        ),
        (
            "How do you calculate labor burden?",
            "Add indirect employment costs, divide by direct wages and "
            "multiply the result by 100.",
        ),
        (
            "What is the best trade for a career changer?",
            "Industrial maintenance is a strong comparison for career "
            "changers because it combines paid training with documented demand.",
        ),
    ],
)
def test_concrete_answer_types_pass(question, answer):
    assert check_content(article_with_answer(question, answer)) == []


def test_direct_answer_can_be_followed_by_a_limitation():
    content = article_with_answer(
        "What trade makes $100,000 a year?",
        "Elevator installation and repair averages $109,820 a year. "
        "This figure is an occupation average, not a starting salary or guarantee.",
    )

    assert check_content(content) == []


@pytest.mark.parametrize("binary", ["Yes.", "No."])
def test_binary_answer_passes_with_immediate_explanation(binary):
    content = article_with_answer(
        "Do job sheets require software?",
        f"{binary} The template works with common office tools and can also "
        "be printed for field use.",
    )

    assert check_content(content) == []


@pytest.mark.parametrize(
    "question,answer",
    [
        ("Do job sheets require software?", "No."),
        ("What is the best format?", "Yes. Use the format that fits."),
    ],
)
def test_bare_or_mismatched_binary_answer_is_blocked(question, answer):
    findings = check_content(article_with_answer(question, answer))

    assert [finding["rule_id"] for finding in findings] == [
        "faq_answer_bare_binary"
    ]


def test_missing_answer_is_blocked():
    content = (
        "# Article\n\n"
        "## FAQ\n\n"
        "### What is the first answer?\n\n"
        "### What is the second answer?\n\n"
        "The second answer gives readers a concrete definition.\n"
    )

    findings = check_content(content)

    assert findings[0]["rule_id"] == "faq_answer_missing"
    assert findings[0]["question"] == "What is the first answer?"


def test_non_faq_content_is_ignored():
    content = (
        "# Article\n\n"
        "## Cost discussion\n\n"
        "Pricing depends on users, implementation, add-ons and support.\n"
    )

    assert check_content(content) == []


def test_check_file_accepts_publish_readiness_signature(tmp_path):
    article_path = tmp_path / "article.md"
    article_path.write_text(
        article_with_answer(
            "What is the clearest option?",
            "Elevator installation is the clearest high-pay option in this comparison.",
        ),
        encoding="utf-8",
    )

    assert check_file(
        str(article_path),
        fail_on="error",
        proof_sidecar="ignored-by-quality-guard.md",
    ) == []
