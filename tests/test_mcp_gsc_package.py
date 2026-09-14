from __future__ import annotations

import asyncio
import inspect
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "mcp-gsc"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


TOOL_SIGNATURES = {
    "list_properties": "() -> 'str'",
    "add_site": "(site_url: 'str') -> 'str'",
    "delete_site": "(site_url: 'str') -> 'str'",
    "get_search_analytics": "(site_url: 'str', days: 'int' = 28, dimensions: 'str' = 'query', row_limit: 'int' = 20) -> 'str'",
    "get_site_details": "(site_url: 'str') -> 'str'",
    "get_sitemaps": "(site_url: 'str') -> 'str'",
    "inspect_url_enhanced": "(site_url: 'str', page_url: 'str') -> 'str'",
    "batch_url_inspection": "(site_url: 'str', urls: 'str') -> 'str'",
    "check_indexing_issues": "(site_url: 'str', urls: 'str') -> 'str'",
    "get_performance_overview": "(site_url: 'str', days: 'int' = 28) -> 'str'",
    "get_advanced_search_analytics": "(site_url: 'str', start_date: 'str' = None, end_date: 'str' = None, dimensions: 'str' = 'query', search_type: 'str' = 'WEB', row_limit: 'int' = 1000, start_row: 'int' = 0, sort_by: 'str' = 'clicks', sort_direction: 'str' = 'descending', filter_dimension: 'str' = None, filter_operator: 'str' = 'contains', filter_expression: 'str' = None, filters: 'str' = None, data_state: 'str' = None) -> 'str'",
    "compare_search_periods": "(site_url: 'str', period1_start: 'str', period1_end: 'str', period2_start: 'str', period2_end: 'str', dimensions: 'str' = 'query', limit: 'int' = 10) -> 'str'",
    "get_search_by_page_query": "(site_url: 'str', page_url: 'str', days: 'int' = 28, row_limit: 'int' = 20) -> 'str'",
    "list_sitemaps_enhanced": "(site_url: 'str', sitemap_index: 'str' = None) -> 'str'",
    "get_sitemap_details": "(site_url: 'str', sitemap_url: 'str') -> 'str'",
    "submit_sitemap": "(site_url: 'str', sitemap_url: 'str') -> 'str'",
    "delete_sitemap": "(site_url: 'str', sitemap_url: 'str') -> 'str'",
    "manage_sitemaps": "(site_url: 'str', action: 'str', sitemap_url: 'str' = None, sitemap_index: 'str' = None) -> 'str'",
    "get_creator_info": "() -> 'str'",
    "reauthenticate": "() -> 'str'",
}


class _Call:
    def __init__(self, result):
        self.result = result

    def execute(self):
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class _Sites:
    def __init__(self, responses):
        self.responses = responses

    def list(self):
        return _Call(self.responses["list"])

    def get(self, **kwargs):
        return _Call(self.responses["get"])

    def add(self, **kwargs):
        return _Call(self.responses["add"])

    def delete(self, **kwargs):
        return _Call(self.responses["delete"])


class _Service:
    def __init__(self, *, sites=None, analytics=None, inspection=None, sitemaps=None):
        self._sites = _Sites(sites or {})
        self._analytics = _QueuedResource(analytics or [])
        self._inspection = _InspectionResource(inspection or [])
        self._sitemaps = _SitemapsResource(sitemaps or {})

    def sites(self):
        return self._sites

    def searchanalytics(self):
        return self._analytics

    def urlInspection(self):
        return self._inspection

    def sitemaps(self):
        return self._sitemaps


class _QueuedResource:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        return _Call(self.responses.pop(0))


class _InspectionResource:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def index(self):
        return self

    def inspect(self, **kwargs):
        self.calls.append(kwargs)
        return _Call(self.responses.pop(0))


class _SitemapsResource:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(("list", kwargs))
        return _Call(self.responses["list"])

    def get(self, **kwargs):
        self.calls.append(("get", kwargs))
        return _Call(self.responses["get"])

    def submit(self, **kwargs):
        self.calls.append(("submit", kwargs))
        return _Call(self.responses.get("submit", {}))

    def delete(self, **kwargs):
        self.calls.append(("delete", kwargs))
        return _Call(self.responses.get("delete", {}))


def test_server_registers_exact_legacy_tool_names_and_signatures():
    from mcp_gsc import server

    registered = [tool.name for tool in asyncio.run(server.mcp.list_tools())]
    assert registered == list(TOOL_SIGNATURES)
    for name, signature in TOOL_SIGNATURES.items():
        assert str(inspect.signature(getattr(server, name))) == signature


def test_legacy_facade_is_explicit_and_exports_same_server():
    import gsc_server
    from mcp_gsc import server

    source = (PACKAGE_ROOT / "gsc_server.py").read_text(encoding="utf-8")
    assert "import *" not in source
    assert gsc_server.mcp is server.mcp
    for name in TOOL_SIGNATURES:
        assert getattr(gsc_server, name) is getattr(server, name)


def test_package_entrypoint_targets_package_server():
    config = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert config["project"]["scripts"]["mcp-gsc"] == "mcp_gsc.server:main"
    assert config["tool"]["setuptools"]["packages"]["find"]["include"] == [
        "mcp_gsc*"
    ]
    assert config["tool"]["setuptools"]["py-modules"] == ["gsc_server"]


def test_properties_use_fake_service_and_preserve_formatting(monkeypatch):
    from mcp_gsc import auth, properties

    service = _Service(
        sites={
            "list": {
                "siteEntry": [
                    {
                        "siteUrl": "sc-domain:example.com",
                        "permissionLevel": "siteOwner",
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(auth, "get_gsc_service", lambda: service)

    assert asyncio.run(properties.list_properties()) == (
        "- sc-domain:example.com (siteOwner)"
    )


def test_auth_prefers_oauth_then_credential_paths(monkeypatch, tmp_path: Path):
    from mcp_gsc import auth

    oauth_service = object()
    monkeypatch.setattr(auth, "SKIP_OAUTH", False)
    monkeypatch.setattr(auth, "get_gsc_service_oauth", lambda: oauth_service)
    assert auth.get_gsc_service() is oauth_service

    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")
    attempted: list[str] = []
    credentials = object()
    built_service = object()

    def load(path, *, scopes):
        attempted.append(path)
        if path == str(first):
            raise ValueError("bad first credential")
        return credentials

    monkeypatch.setattr(auth, "SKIP_OAUTH", True)
    monkeypatch.setattr(auth, "POSSIBLE_CREDENTIAL_PATHS", [None, str(first), str(second)])
    monkeypatch.setattr(
        auth.service_account.Credentials,
        "from_service_account_file",
        load,
    )
    monkeypatch.setattr(
        auth,
        "build",
        lambda *args, **kwargs: built_service,
    )

    assert auth.get_gsc_service() is built_service
    assert attempted == [str(first), str(second)]


def test_corrupt_oauth_token_is_replaced_at_same_path(monkeypatch, tmp_path: Path):
    from mcp_gsc import auth

    token = tmp_path / "token.json"
    token.write_text("corrupt", encoding="utf-8")

    class _Credentials:
        valid = True

        def to_json(self):
            return '{"fresh":true}'

    class _Flow:
        def run_local_server(self, *, port):
            assert port == 0
            return _Credentials()

    secrets = tmp_path / "client_secrets.json"
    secrets.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(auth, "TOKEN_FILE", str(token))
    monkeypatch.setattr(auth, "OAUTH_CLIENT_SECRETS_FILE", str(secrets))
    monkeypatch.setattr(
        auth.Credentials,
        "from_authorized_user_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("corrupt")),
    )
    monkeypatch.setattr(
        auth.InstalledAppFlow,
        "from_client_secrets_file",
        lambda *args, **kwargs: _Flow(),
    )
    built = object()
    monkeypatch.setattr(auth, "build", lambda *args, **kwargs: built)

    assert auth.get_gsc_service_oauth() is built
    assert token.read_text(encoding="utf-8") == '{"fresh":true}'


def test_advanced_analytics_preserves_request_and_output(monkeypatch):
    from mcp_gsc import analytics_advanced, auth

    service = _Service(
        analytics=[
            {
                "rows": [
                    {
                        "keys": ["heat pump"],
                        "clicks": 7,
                        "impressions": 100,
                        "ctr": 0.07,
                        "position": 3.25,
                    }
                ]
            }
        ]
    )
    monkeypatch.setattr(auth, "get_gsc_service", lambda: service)
    monkeypatch.setattr(analytics_advanced, "DATA_STATE", "all")

    output = asyncio.run(
        analytics_advanced.get_advanced_search_analytics(
            "sc-domain:example.com",
            start_date="2026-08-01",
            end_date="2026-08-31",
            filters='[{"dimension":"country","operator":"equals","expression":"usa"}]',
        )
    )

    assert service._analytics.calls == [
        {
            "siteUrl": "sc-domain:example.com",
            "body": {
                "startDate": "2026-08-01",
                "endDate": "2026-08-31",
                "dimensions": ["query"],
                "rowLimit": 1000,
                "startRow": 0,
                "searchType": "WEB",
                "dataState": "all",
                "orderBy": [
                    {"metric": "CLICK_COUNT", "direction": "descending"}
                ],
                "dimensionFilterGroups": [
                    {
                        "filters": [
                            {
                                "dimension": "country",
                                "operator": "equals",
                                "expression": "usa",
                            }
                        ]
                    }
                ],
            },
        }
    ]
    assert output == (
        "Search analytics for sc-domain:example.com:\n"
        "Date range: 2026-08-01 to 2026-08-31\n"
        "Search type: WEB\n"
        "Filters: country equals 'usa'\n"
        "Showing rows 1 to 1 (sorted by clicks descending)\n"
        "\n--------------------------------------------------------------------------------\n\n"
        "Query | Clicks | Impressions | CTR | Position\n"
        "--------------------------------------------------------------------------------\n"
        "heat pump | 7 | 100 | 7.00% | 3.2"
    )


def test_url_inspection_preserves_request_and_output(monkeypatch):
    from mcp_gsc import auth, inspection

    service = _Service(
        inspection=[
            {
                "inspectionResult": {
                    "inspectionResultLink": "https://search.google.test/result",
                    "indexStatusResult": {
                        "verdict": "PASS",
                        "coverageState": "Submitted and indexed",
                        "lastCrawlTime": "2026-09-10T14:30:00Z",
                        "pageFetchState": "SUCCESSFUL",
                    },
                    "richResultsResult": {
                        "verdict": "PASS",
                        "detectedItems": [{"richResultType": "FAQ"}],
                    },
                }
            }
        ]
    )
    monkeypatch.setattr(auth, "get_gsc_service", lambda: service)

    output = asyncio.run(
        inspection.inspect_url_enhanced(
            "sc-domain:example.com", "https://example.com/page"
        )
    )

    assert service._inspection.calls == [
        {
            "body": {
                "inspectionUrl": "https://example.com/page",
                "siteUrl": "sc-domain:example.com",
            }
        }
    ]
    assert output == (
        "URL Inspection for https://example.com/page:\n"
        "--------------------------------------------------------------------------------\n"
        "Search Console Link: https://search.google.test/result\n"
        "--------------------------------------------------------------------------------\n"
        "Indexing Status: PASS\n"
        "Coverage: Submitted and indexed\n"
        "Last Crawled: 2026-09-10 14:30\n"
        "Page Fetch: SUCCESSFUL\n"
        "\nRich Results: PASS\n"
        "Detected Rich Result Types:\n"
        "- FAQ"
    )


def test_sitemap_listing_preserves_request_and_output(monkeypatch):
    from mcp_gsc import auth, sitemaps

    service = _Service(
        sitemaps={
            "list": {
                "sitemap": [
                    {
                        "path": "https://example.com/sitemap.xml",
                        "lastDownloaded": "2026-09-10T14:30:00Z",
                        "errors": "0",
                        "contents": [{"type": "web", "submitted": "42"}],
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(auth, "get_gsc_service", lambda: service)

    output = asyncio.run(sitemaps.get_sitemaps("sc-domain:example.com"))

    assert service._sitemaps.calls == [
        ("list", {"siteUrl": "sc-domain:example.com"})
    ]
    assert output == (
        "Sitemaps for sc-domain:example.com:\n"
        "--------------------------------------------------------------------------------\n"
        "Path | Last Downloaded | Status | Indexed URLs | Errors\n"
        "--------------------------------------------------------------------------------\n"
        "https://example.com/sitemap.xml | 2026-09-10 14:30 | Valid | 42 | 0"
    )


def test_analytics_404_preserves_property_guidance(monkeypatch):
    from mcp_gsc import analytics, auth, formatting

    service = _Service(analytics=[RuntimeError("404 property missing")])
    monkeypatch.setattr(auth, "get_gsc_service", lambda: service)

    output = asyncio.run(
        analytics.get_search_analytics("sc-domain:example.com")
    )

    assert output == formatting.site_not_found_error("sc-domain:example.com")


def test_advanced_invalid_filter_preserves_error_without_api_call(monkeypatch):
    from mcp_gsc import analytics_advanced, auth

    service = _Service(analytics=[])
    monkeypatch.setattr(auth, "get_gsc_service", lambda: service)

    output = asyncio.run(
        analytics_advanced.get_advanced_search_analytics(
            "sc-domain:example.com", filters="not-json"
        )
    )

    assert output == (
        "Invalid filters JSON. Please provide a valid JSON array of filter objects."
    )
    assert service._analytics.calls == []
