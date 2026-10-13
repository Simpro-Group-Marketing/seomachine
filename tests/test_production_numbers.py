from data_sources.modules.production.numbers import extract_numbers, numbers_supported

def test_equivalent_forms_normalize_to_one_value():
    assert extract_numbers("24,000 and 24000 and 24k and 24 thousand") == frozenset({"24000"})

def test_percent_and_decimal_and_currency():
    assert extract_numbers("12.5% of $1.2m") == frozenset({"12.5", "1200000"})

def test_years_are_kept_as_numbers():
    assert extract_numbers("in 2026") == frozenset({"2026"})

def test_claim_number_missing_from_quote_is_reported():
    assert numbers_supported("Saves 30% of admin time", "cut admin time by 25%") == (False, frozenset({"30"}))

def test_claim_without_numbers_is_supported():
    assert numbers_supported("Scheduling matters", "anything") == (True, frozenset())

def test_word_suffix_with_space_alone_normalizes():
    assert extract_numbers("24 thousand") == frozenset({"24000"})

def test_hyphenated_range_yields_two_numbers():
    assert extract_numbers("3-5 days") == frozenset({"3", "5"})
