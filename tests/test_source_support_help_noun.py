"""The causal claim pattern matches the verb "help", not documentation nouns.

"Help article", "help centre" and "help guide" are product destination names.
Treating them as causal claims forced a Source Map row onto every sentence that
named a vendor help centre, which no external source can support.
"""

from data_sources.modules.source_support.common import GENERAL_CLAIM_PATTERNS
from data_sources.modules.source_support.proof_parsing import _extract_claim_candidates


CAUSAL = dict(GENERAL_CLAIM_PATTERNS)["causal"]


def test_causal_pattern_still_matches_the_verb() -> None:
    assert CAUSAL.search("Training helps new starters reach competence sooner.")
    assert CAUSAL.search("The report helps a coordinator see stalled jobs.")
    assert CAUSAL.search("A shorter handover helps the office close jobs.")


def test_the_inflected_verb_is_causal_even_before_a_documentation_noun() -> None:
    """Only the bare noun "help" is exempt; "helps" is always the verb.

    An earlier exemption keyed on `helps?`, which silently excused genuine
    causal claims whose object happened to be a documentation noun.
    """
    for sentence in (
        "This helps guide the technician through the job.",
        "Scheduling helps sites run to plan.",
        "Caching helps pages load faster.",
        "The template helps documentation teams standardise handovers.",
    ):
        assert CAUSAL.search(sentence), sentence


def test_causal_pattern_still_matches_other_causal_verbs() -> None:
    for sentence in (
        "The release reduces office admin.",
        "That change improves first-time fix rates.",
        "The setting prevents portal over-exposure.",
        "This enables recurring work to generate itself.",
    ):
        assert CAUSAL.search(sentence), sentence


def test_documentation_nouns_are_not_causal_claims() -> None:
    for sentence in (
        "Help articles stay open at the AroFlo help centre.",
        "Release notes and how-to articles live in the Simpro help guide.",
        "| Disputed timesheets | AroFlo | Clock In and Clock Out | Help article |",
        "The Help Guide Video Library covers the same ground.",
        "Search the help center for the task name.",
        "The help desk answers that question.",
        "Product help documentation lists every field.",
        "Open the help page for that setting.",
        "The help docs cover the rest.",
        "See https://x.test/articles/#!help-guide/how-to-manage-contracts",
    ):
        assert CAUSAL.search(sentence) is None, sentence


def test_naming_a_help_centre_does_not_require_a_source_map_row() -> None:
    content = (
        "# Learning update\n\n"
        "Help articles stay open at the AroFlo help centre.\n"
    )

    candidates = _extract_claim_candidates(content, frozenset())

    assert [c for c in candidates if c.claim_type == "causal"] == []
