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

def test_leading_dot_decimal_keeps_fraction():
    assert extract_numbers(".5%") == frozenset({"0.5"})
    assert extract_numbers("$.50") == frozenset({"0.5"})
    assert numbers_supported("$.5", "5") == (False, frozenset({"0.5"}))

def test_space_separated_bn_suffix():
    assert extract_numbers("$2 bn") == frozenset({"2000000000"})
    assert numbers_supported("$2 bn revenue", "2 jobs") == (False, frozenset({"2000000000"}))

def test_mm_is_millimetres_not_million():
    assert extract_numbers("20 mm pipe") == frozenset({"20"})
    assert extract_numbers("20mm conduit") == frozenset({"20"})

def test_space_separated_m_and_k_are_not_suffixes():
    assert extract_numbers("5 m away") == frozenset({"5"})

def test_identifiers_do_not_yield_numbers():
    assert extract_numbers("B2B and H2 and v2 and Web3") == frozenset()
    assert numbers_supported("B2B teams save 30%", "save 30% of time") == (True, frozenset())

def test_iso_dates_are_skipped():
    assert extract_numbers("Updated 2026-10-13") == frozenset()

def test_suffixed_claim_does_not_match_unsuffixed_quote():
    assert numbers_supported("24k jobs", "24 jobs") == (False, frozenset({"24000"}))
