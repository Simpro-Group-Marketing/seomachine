import pytest

from data_sources.modules.production.numbers import extract_numbers, numbers_supported


@pytest.mark.parametrize(("text", "expected"), [
    ("seventy percent of crews", {"70"}),
    ("twenty-four thousand businesses", {"24000"}),
    ("twenty four thousand businesses", {"24000"}),
    ("two hundred jobs", {"200"}),
    ("two hundred and fifty jobs", {"250"}),
    ("a hundred jobs", {"100"}),
    ("a thousand jobs", {"1000"}),
    ("three million dollars", {"3000000"}),
    ("three million two hundred thousand visits", {"3200000"}),
    ("Ninety-nine crews", {"99"}),
    ("eleven crews", {"11"}),
    ("nine hours", {"9"}),
])
def test_spelled_cardinals_are_numbers(text, expected):
    assert extract_numbers(text) == frozenset(expected)


@pytest.mark.parametrize(("text", "expected"), [
    ("half of all jobs", {"50"}),
    ("a third of all jobs", {"33.33"}),
    ("one third of all jobs", {"33.33"}),
    ("a quarter of all jobs", {"25"}),
    ("two thirds of all jobs", {"66.67"}),
    ("two-thirds of all jobs", {"66.67"}),
    ("three quarters of all jobs", {"75"}),
])
def test_fraction_of_is_a_number(text, expected):
    assert extract_numbers(text) == frozenset(expected)


@pytest.mark.parametrize("text", [
    "one of the best tools", "a one-off job", "a third party installer", "the first step",
    "the second visit", "someone often phones", "the third quarter of the year", "half an hour",
    "the second half of the year", "thousands of crews", "hundreds of jobs", "no one waits",
])
def test_words_that_are_not_cardinals_produce_nothing(text):
    assert extract_numbers(text) == frozenset()


@pytest.mark.parametrize(("text", "expected"), [
    ("nine out of ten crews", {"9", "10"}),
    ("one in five crews", {"1", "5"}),
    ("one percent of jobs", {"1"}),
    ("one hundred jobs", {"100"}),
])
def test_one_counts_in_ratios_percents_and_compounds(text, expected):
    assert extract_numbers(text) == frozenset(expected)


def test_spelled_and_digit_forms_compare_equal():
    assert numbers_supported("Seventy percent of contractors", "70% of contractors") == (True, frozenset())
    assert numbers_supported("twenty-four thousand trades", "24,000 trades") == (True, frozenset())
    assert numbers_supported("Seventy percent of contractors", "60% of contractors") == (False, frozenset({"70"}))
