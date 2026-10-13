import pytest
from tests.production_truth_support import article, blocks, check_truth_for

PLACEHOLDER = (
    '[IMAGE PLACEHOLDER | source: Simpro library | alt: "Crew of 25 tradespeople on a 1200x630 job site" '
    "| render target: 1200x630 | resize and compress to 80 kb]"
)


def gate(text):
    return blocks(check_truth_for(text), "number_gate")


def material(text):
    return blocks(check_truth_for(text), "claim_numbers")


@pytest.mark.parametrize("phrase", ["3x faster", "10x ROI", "6× output", "3 times faster", "9 out of 10 crews",
                                    "1 in 7 crews", "3 x faster"])
def test_multipliers_and_ratios_are_not_exempt(phrase):
    assert gate(article(f"Crews report {phrase} work.\n\n")), phrase


def test_supported_multiplier_passes_the_gate():
    assert gate(article("Crews report 24k firms and 30% gains.\n\n")) == []


def test_meta_fields_are_public_copy_and_so_is_description():
    assert gate(article(extra_front='meta_description: "Save 47% today"\n'))
    assert gate(article(extra_front='meta_title: "Save 47% today"\n'))
    found = gate(article(description="Save 47% today"))
    assert found and found[0].line == 3


def test_media_placeholder_lines_are_exempt_from_the_number_gate():
    assert gate(article(PLACEHOLDER + "\n\n")) == []


@pytest.mark.parametrize("phrase", [
    "ISO 9001", "AS/NZS 3000:2018", "NFPA 70E", "OSHA 1910", "Section 179", "Chapter 12", "Version 12",
    "Level 3", "Tier 20", "Title 24", "R-410A", "COVID-19", "iOS 17", "Android 14", "Windows 11", "v2.1",
    "401(k)", "NEC 2023", "BS 7671", "EN 12830", "Rule 14",
])
def test_standard_and_code_identifiers_are_exempt(phrase):
    assert gate(article(f"Follow {phrase} on site.\n\n")) == [], phrase


@pytest.mark.parametrize("phrase", ["the 21st job", "the 100th crew", "the 2nd and 3rd visits"])
def test_ordinals_are_exempt(phrase):
    assert gate(article(f"Book {phrase} early.\n\n")) == []


@pytest.mark.parametrize("phrase", ["9:30 am", "2:15 p.m.", "14:45", "7pm"])
def test_time_of_day_forms_are_exempt(phrase):
    assert gate(article(f"Crews start at {phrase} daily.\n\n")) == [], phrase


@pytest.mark.parametrize("phone", ["1 800 555 0199", "0412-345-678", "+61 2 9876 5432"])
def test_phone_number_shapes_are_exempt(phone):
    assert gate(article(f"Call {phone} today.\n\n")) == [], phone


@pytest.mark.parametrize("phrase", ["founded in 2002", "15 kg of cable", "a 45-day trial", "12-month terms",
                                    "since 1999", "35 amp breakers"])
def test_years_measurements_and_hyphenated_durations_stay_blocked(phrase):
    assert gate(article(f"The firm was {phrase} for crews.\n\n")), phrase


def test_material_numbers_cover_percent_currency_multiplier_and_big_integers():
    for phrase in ("20% of crews", "$40 a month", "40 crews", "2002", "5k jobs"):
        assert material(article(f"Teams see {phrase} daily.\n\n")), phrase
    for phrase in ("4 crews", "a 2026 plan", "step 3", "2.5 seats"):
        assert material(article(f"Teams see {phrase} daily.\n\n")) == [], phrase


def either(text):
    findings = check_truth_for(text)
    return [f for f in findings if f.severity == "block" and f.check in ("number_gate", "claim_numbers")]


@pytest.mark.parametrize("phrase", [
    "Level 47x faster", "Windows 50 percent", "Part 30%", "Step 45% faster", "v47%", "ISO 47x", "NFPA 70E 50k",
    "Class 61 times", "the 61st%", "10 20 30 40 50", "25 50 75 100", "$ 1200 3400 5600", "$1200 3400 5600",
    "Tier 9 million", "Version 62 billion", "1300 139 467%", "0412-345-678 times",
])
def test_exemptions_never_swallow_an_attached_percent_multiplier_or_currency(phrase):
    assert either(article(f"Crews report {phrase} work.\n\n")), phrase


@pytest.mark.parametrize("phrase", ["ISO 9001", "Step 1", "1300 139 467", "R-410A", "v2.1", "9:30 am", "the 21st job"])
def test_genuine_labels_identifiers_and_phones_still_pass(phrase):
    assert either(article(f"Crews report {phrase} work.\n\n")) == [], phrase


def listicle(count, title="12 Ways to Cut Costs", body_noun="tools"):
    sections = "".join(f"### Option {chr(65 + n)}\n\nShort text here.\n\n" for n in range(count))
    return article(f"Compare 12 {body_noun} below.\n\n{sections}", title=title)


def test_listicle_count_equal_to_the_h3_count_is_exempt_from_gate_and_paragraph_rule():
    assert either(listicle(12)) == []
    assert either(article("## 15 best apps\n\n" + "".join(f"### App {chr(65 + n)}\n\nText.\n\n" for n in range(15)))) == []


def test_listicle_count_not_equal_to_the_h3_count_blocks():
    assert either(listicle(9))


def test_listicle_exemption_needs_a_plural_noun_and_no_attached_unit():
    plain = article("Compare 12 of them below.\n\n" + "".join(f"### O{chr(65 + n)}\n\nT.\n\n" for n in range(12)))
    assert either(plain)
    percent = article("Compare 12% tools below.\n\n" + "".join(f"### O{chr(65 + n)}\n\nT.\n\n" for n in range(12)))
    assert either(percent)
