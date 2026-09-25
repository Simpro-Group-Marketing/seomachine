"""Optional readiness inputs are not BOM artifacts, so they may appear as extras.

`source_decision_registry` is declared optional in readiness/input_spec.py and is
read by the readiness gates, but the assembly BOM never inventories it. When
context/source-classification-decisions.json exists on disk the prior-preflight
inventory check saw it as an unexpected extra and blocked the optimized tail.
It belongs with the other optional inputs already tolerated there.
"""

import pytest

from data_sources.modules.blog_assembly.stage_receipts import (
    _validate_prior_input_inventory,
)
from data_sources.modules.readiness.input_spec import FIXED_WORKSPACE_INPUT_LABELS


def _row(name: str) -> dict[str, str]:
    return {"path": f"context/{name}.json", "sha256": "0" * 64}


BOM = {
    "artifacts": {"article": {"path": "drafts/a.md", "sha256": "1" * 64}},
    "machine_reviews": {},
}


def test_bom_backed_inputs_still_have_to_match() -> None:
    inputs = {"article": {"path": "drafts/a.md", "sha256": "2" * 64}}
    with pytest.raises(ValueError):
        _validate_prior_input_inventory(inputs, BOM)


def test_source_decision_registry_is_a_tolerated_optional_input() -> None:
    inputs = {
        "article": {"path": "drafts/a.md", "sha256": "1" * 64},
        "source_decision_registry": _row("source-classification-decisions"),
    }

    _validate_prior_input_inventory(inputs, BOM)


def test_an_unknown_extra_input_is_still_rejected() -> None:
    inputs = {
        "article": {"path": "drafts/a.md", "sha256": "1" * 64},
        "totally_unexpected_input": _row("whatever"),
    }
    with pytest.raises(ValueError):
        _validate_prior_input_inventory(inputs, BOM)


def test_source_decision_registry_is_declared_optional() -> None:
    assert "source_decision_registry" in FIXED_WORKSPACE_INPUT_LABELS


def test_both_bom_gates_tolerate_the_same_optional_inputs() -> None:
    """The two gates are independent and each had its own hardcoded set.

    Only stage_receipts was reachable from a focused unit test, so the
    bom_preflight_inputs_mismatch gate went unfixed the first time. Both now
    derive from the same public label set.
    """
    from data_sources.modules.blog_assembly.stage_receipts import (
        ALLOWED_EXTRA_INPUTS as stage_receipt_extras,
    )
    from data_sources.modules.blog_bom_validation.preflight import (
        ALLOWED_EXTRA_INPUTS as bom_preflight_extras,
    )

    assert stage_receipt_extras == bom_preflight_extras
    assert FIXED_WORKSPACE_INPUT_LABELS <= stage_receipt_extras
    assert "source_decision_registry" in bom_preflight_extras
