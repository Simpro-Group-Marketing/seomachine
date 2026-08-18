from __future__ import annotations

import importlib.util
import subprocess
import sys
from contextlib import redirect_stdout
from io import BytesIO, TextIOWrapper
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pytest

from scripts import seo_bofu_rankings
from scripts import seo_competitor_analysis


ROOT = Path(__file__).resolve().parents[1]
GSC_ROOT = ROOT / "mcp-gsc"


def _cp1252_stream():
    return TextIOWrapper(BytesIO(), encoding="cp1252")


def test_bofu_cli_output_is_safe_when_stdout_is_cp1252():
    class DFS:
        def get_serp_data(self, keyword, limit=50):
            return {"organic_results": []}

    class GSC:
        def get_keyword_positions(self, **kwargs):
            return []

    with (
        patch.object(seo_bofu_rankings, "DataForSEO", DFS),
        patch.object(seo_bofu_rankings, "GoogleSearchConsole", GSC),
        patch.object(
            seo_bofu_rankings,
            "load_config",
            return_value={"bofu_keywords": ["field service"], "key_queries": []},
        ),
        redirect_stdout(_cp1252_stream()),
    ):
        seo_bofu_rankings.main()


def test_competitor_cli_output_is_safe_when_stdout_is_cp1252():
    class DFS:
        def get_serp_data(self, keyword, limit=100):
            return {"organic_results": []}

        def get_domain_keywords(self, *args, **kwargs):
            return []

    with (
        patch.object(seo_competitor_analysis, "DataForSEO", DFS),
        patch.object(
            seo_competitor_analysis,
            "load_config",
            return_value={
                "bofu_keywords": ["field service"],
                "direct_competitors": ["competitor.com"],
            },
        ),
        redirect_stdout(_cp1252_stream()),
    ):
        seo_competitor_analysis.main()


def _load_gsc_server():
    spec = importlib.util.spec_from_file_location(
        "gsc_server_under_test",
        GSC_ROOT / "gsc_server.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load gsc_server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gsc_auth_fallback_does_not_write_diagnostics_to_mcp_stdout(capsys):
    module = _load_gsc_server()
    module.SKIP_OAUTH = False
    module.POSSIBLE_CREDENTIAL_PATHS = []
    module.get_gsc_service_oauth = lambda: (_ for _ in ()).throw(
        RuntimeError("oauth unavailable")
    )

    with pytest.raises(FileNotFoundError):
        module.get_gsc_service()

    assert capsys.readouterr().out == ""


def test_mcp_gsc_builds_an_installable_wheel_with_server_module(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(tmp_path),
            str(GSC_ROOT),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    wheels = list(tmp_path.glob("mcp_gsc-*.whl"))
    assert len(wheels) == 1
    with ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
        assert "gsc_server.py" in names
        assert any(name.endswith("entry_points.txt") for name in names)
