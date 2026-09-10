from __future__ import annotations

from tools.check_python_structure import complexity_errors, production_line_errors


def test_production_line_baseline_rejects_growth_and_stale_debt() -> None:
    baseline = {"legacy.py": 700}

    assert production_line_errors({"legacy.py": 700}, baseline, maximum=500) == []
    assert production_line_errors({"legacy.py": 701}, baseline, maximum=500) == [
        "legacy.py grew from 700 to 701 physical lines"
    ]
    assert production_line_errors({"legacy.py": 699}, baseline, maximum=500) == [
        "legacy.py improved to 699 lines; lower its stale 700-line baseline"
    ]
    assert production_line_errors({"new.py": 501}, baseline, maximum=500) == [
        "legacy.py is absent; remove its stale line baseline",
        "new.py has 501 lines; new production files are limited to 500",
    ]


def test_complexity_baseline_rejects_new_growth_and_stale_debt() -> None:
    baseline = {"legacy.py": {"old": 14}}

    assert complexity_errors({"legacy.py": {"old": 14}}, baseline) == []
    assert complexity_errors({"legacy.py": {"old": 15}}, baseline) == [
        "legacy.py:old complexity grew from 14 to 15"
    ]
    assert complexity_errors({"legacy.py": {"old": 13}}, baseline) == [
        "legacy.py:old improved to complexity 13; lower its stale 14 baseline"
    ]
    assert complexity_errors({"new.py": {"new": 11}}, baseline) == [
        "legacy.py:old no longer violates C901; remove its stale baseline",
        "new.py:new is a new C901 violation at complexity 11",
    ]
