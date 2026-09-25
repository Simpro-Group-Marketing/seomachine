import json
import subprocess
import sys


def test_source_support_cli_module_emits_json_and_success_exit_code(tmp_path):
    article = tmp_path / "article.md"
    article.write_text("# Scheduling guide\n\nReview the next section.\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "data_sources.modules.source_support.cli", str(article)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["path"] == str(article)
    assert payload["fail_on"] == "error"
    assert payload["findings"] == []
