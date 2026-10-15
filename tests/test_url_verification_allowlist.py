import json
from unittest.mock import patch
from data_sources.modules import url_validator
from data_sources.modules.url_validator import UrlValidationResult
from data_sources.modules.readiness import input_spec

ALLOWED = "https://www.example.org/report"


def _result(status, code, reason="HTTP"):
    return UrlValidationResult(url=ALLOWED, status=status, status_code=code, reason=reason)


def test_allowlist_never_exempts_gone_pages():
    with patch.object(url_validator, "chrome_verified_urls", return_value=frozenset({ALLOWED})):
        assert not url_validator._is_chrome_verified_manual_review(_result("unresolved", 404))
        assert not url_validator._is_chrome_verified_manual_review(_result("unresolved", 410))


def test_allowlist_still_exempts_bot_blocks_and_timeouts():
    with patch.object(url_validator, "chrome_verified_urls", return_value=frozenset({ALLOWED})):
        assert url_validator._is_chrome_verified_manual_review(_result("unresolved", None, "Read timed out"))
        assert url_validator._is_chrome_verified_manual_review(_result("manual_review", 403))


def test_allowlist_is_a_sealed_readiness_input():
    labels = dict(input_spec._FIXED_WORKSPACE_INPUTS)
    assert labels["url_verification_allowlist"] == "context/url-verification-allowlist.json"


def test_read_error_is_not_cached(tmp_path, monkeypatch):
    from data_sources.modules import url_verification_allowlist as allow
    missing = tmp_path / "allow.json"
    monkeypatch.setattr(allow, "URL_VERIFICATION_ALLOWLIST_PATH", missing)
    monkeypatch.setattr(allow, "_CHROME_VERIFIED_CACHE", None)
    assert allow.chrome_verified_urls() == frozenset()
    missing.write_text('{"entries":[{"url":"%s","verified_via":"chrome_connector"}]}' % ALLOWED, encoding="utf-8")
    assert ALLOWED in allow.chrome_verified_urls()


def test_non_dict_payload_is_treated_as_unreadable_and_not_cached(tmp_path, monkeypatch):
    from data_sources.modules import url_verification_allowlist as allow
    path = tmp_path / "allow.json"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(allow, "URL_VERIFICATION_ALLOWLIST_PATH", path)
    monkeypatch.setattr(allow, "_CHROME_VERIFIED_CACHE", None)
    assert allow.chrome_verified_urls() == frozenset()
    assert allow._CHROME_VERIFIED_CACHE is None
    path.write_text('{"entries":[{"url":"%s","verified_via":"chrome_connector"}]}' % ALLOWED, encoding="utf-8")
    assert ALLOWED in allow.chrome_verified_urls()


def test_malformed_json_is_not_cached(tmp_path, monkeypatch):
    from data_sources.modules import url_verification_allowlist as allow
    path = tmp_path / "allow.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(allow, "URL_VERIFICATION_ALLOWLIST_PATH", path)
    monkeypatch.setattr(allow, "_CHROME_VERIFIED_CACHE", None)
    assert allow.chrome_verified_urls() == frozenset()
    assert allow._CHROME_VERIFIED_CACHE is None
    path.write_text('{"entries":[{"url":"%s","verified_via":"chrome_connector"}]}' % ALLOWED, encoding="utf-8")
    assert ALLOWED in allow.chrome_verified_urls()


def _allowlist(tmp_path, monkeypatch, entries):
    from data_sources.modules import url_verification_allowlist as allow
    path = tmp_path / "allow.json"
    path.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    monkeypatch.setattr(allow, "URL_VERIFICATION_ALLOWLIST_PATH", path)
    monkeypatch.setattr(allow, "_CHROME_VERIFIED_CACHE", None)
    return allow.chrome_verified_urls()


def test_an_entry_names_the_client_that_verified_it(tmp_path, monkeypatch):
    entry = {"url": ALLOWED, "verified_via": "chrome_connector"}
    assert ALLOWED in _allowlist(tmp_path, monkeypatch, [{**entry, "client": "codex"}])
    assert ALLOWED in _allowlist(tmp_path, monkeypatch, [entry])  # recorded before the client field existed
    assert ALLOWED not in _allowlist(tmp_path, monkeypatch, [{**entry, "client": "cursor"}])


def test_every_repo_allowlist_client_is_known():
    from data_sources.modules.capture_client import CLIENTS
    from data_sources.modules.url_verification_allowlist import URL_VERIFICATION_ALLOWLIST_PATH
    entries = json.loads(URL_VERIFICATION_ALLOWLIST_PATH.read_text(encoding="utf-8"))["entries"]
    assert all(entry.get("client", "claude_code") in CLIENTS for entry in entries)
    assert any(entry.get("client") == "claude_code" for entry in entries)
