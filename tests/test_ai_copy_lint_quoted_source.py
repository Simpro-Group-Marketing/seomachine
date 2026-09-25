"""Copy-style rules police our prose, not a source's verbatim words.

COPY_AVOID rules (filler words, vague generalizations, modal verbs, passive
voice) describe how Simpro writes. A quoted review snippet or interview answer
cannot be edited to satisfy them, so a match inside a quoted or blockquoted
span is downgraded to a warning instead of blocking release. It is not
suppressed: dropping it outright would let any prose clear the linter by
being wrapped in quotation marks. Substantive ERROR_RULES still apply
everywhere, including inside quotes.
"""

from data_sources.modules.ai_copy_lint.core import lint_content


QUOTE = (
    "The user interface is very intuitive, making it easy to onboard new team "
    "members without extensive training."
)


def _errors(content: str) -> list[tuple[str, str]]:
    return [
        (f["rule_id"], f["match"])
        for f in lint_content(content, profile="simpro-web")
        if f["severity"] == "error"
    ]


def _warnings(content: str) -> list[tuple[str, str]]:
    return [
        (f["rule_id"], f["match"])
        for f in lint_content(content, profile="simpro-web")
        if f["severity"] == "warning"
    ]


def test_copy_avoid_rules_still_apply_to_our_own_prose() -> None:
    assert ("filler_word", "very") in _errors("The setup is very simple.\n")
    assert any(
        rule == "vague_generalization"
        for rule, _ in _errors("Teams usually finish the sequence.\n")
    )


def test_double_quoted_source_text_is_downgraded_not_dropped() -> None:
    content = f'Joe H. put it this way: "{QUOTE}"\n'
    assert _errors(content) == []
    assert ("filler_word", "very") in _warnings(content)


def test_blockquoted_source_text_is_downgraded_not_dropped() -> None:
    content = f"Joe H. put it this way.\n\n> {QUOTE}\n"
    assert _errors(content) == []
    assert ("filler_word", "very") in _warnings(content)


def test_substantive_error_rules_still_apply_inside_quotes() -> None:
    rules = {rule for rule, _ in _errors('He said "this will boost revenue".\n')}
    assert "unsupported_hype" in rules

    rules = {rule for rule, _ in _errors('She said "we shipped it; it worked".\n')}
    assert "semicolon" in rules


def test_unquoted_text_on_a_line_with_a_quote_is_still_linted() -> None:
    rules = {
        rule
        for rule, _ in _errors(f'The rollout is very simple. Joe H. said "{QUOTE}"\n')
    }
    assert "filler_word" in rules


def test_quoted_finding_is_not_duplicated_when_also_unquoted_on_the_line() -> None:
    """The same match must not be reported twice for one line."""
    content = f'The rollout is very simple. Joe H. said "{QUOTE}"\n'
    errors = _errors(content)
    warnings = _warnings(content)
    assert errors.count(("filler_word", "very")) == 1
    assert warnings.count(("filler_word", "very")) == 1
