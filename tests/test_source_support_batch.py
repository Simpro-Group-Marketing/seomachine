from __future__ import annotations

import requests

from data_sources.modules.source_support_guard import check_content, fetch_source_text_many


def test_source_support_batches_and_deduplicates_independent_html_sources() -> None:
    url = "https://regulator.example.gov/tradesman"
    article = f"""# License guide

| License | Current fees |
|---|---|
| Tradesman | A $36 exam fee and a $35 initial fee. See [requirements]({url}). |
"""
    sidecar = f"""## Source Map
- Claim: $36 exam fee | URL: {url} | Evidence: Exam Fee: $36 | Status: approved
- Claim: $35 initial fee | URL: {url} | Evidence: Initial Fee: $35 | Status: approved
"""
    calls: list[tuple[str, ...]] = []

    def fetch_many(urls):
        calls.append(tuple(urls))
        return {url: "Fees. Exam Fee: $36. Initial Fee: $35."}

    findings = check_content(
        article,
        proof_content=sidecar,
        fetch_many=fetch_many,
    )

    assert findings == []
    assert calls == [(url,)]


def test_source_support_batch_failure_remains_a_source_fetch_finding() -> None:
    url = "https://regulator.example.gov/tradesman"
    article = f"# License guide\n\nThe current exam fee is $36 [under the rules]({url}).\n"
    sidecar = (
        "## Source Map\n"
        f"- Claim: exam fee is $36 | URL: {url} | Evidence: Exam Fee: $36 | "
        "Status: approved\n"
    )

    findings = check_content(
        article,
        proof_content=sidecar,
        fetch_many=lambda urls: {url: RuntimeError("network unavailable")},
    )

    assert any(finding["rule_id"] == "source_fetch_failed" for finding in findings)


def test_fetch_source_text_many_deduplicates_and_normalizes_once() -> None:
    urls = ["https://example.com/one", "https://example.com/one"]
    calls: list[tuple[str, ...]] = []
    normalized: list[str] = []
    responses: list[requests.Response] = []

    class Transport:
        def request_many(self, method, requested, **kwargs):
            del method, kwargs
            calls.append(tuple(requested))
            response = requests.Response()
            response.status_code = 200
            response.url = requested[0]
            response._content = b"<html><body>Visible evidence</body></html>"
            response.headers["Content-Type"] = "text/html"
            responses.append(response)
            return [response]

    result = fetch_source_text_many(
        urls,
        transport=Transport(),
        normalize=lambda key, loader: normalized.append(key) or loader(),
    )

    assert calls == [(urls[0],)]
    assert result[urls[0]] == "Visible evidence"
    assert len(normalized) == 1
    assert responses[0].content == b""
