import requests
from data_sources.modules.production.facts import verify_quotes

URL = "https://example.org/report"
QUOTE = "more than 24,000 trade businesses"
PAGE = "<html><body><p>Simpro supports more than 24,000 trade businesses.</p></body></html>"

def _response(url, status, body=""):
    response = requests.Response()
    response.status_code, response.url = status, url
    response._content, response._content_consumed = body.encode("utf-8"), True
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

class FakeTransport:
    def __init__(self, replies):
        self.replies, self.calls = replies, []
    def request_many(self, method, urls, **kwargs):
        self.calls.append(list(urls))
        out = []
        for url in urls:
            reply = self.replies[url]
            if isinstance(reply, Exception):
                raise reply
            out.append(reply)
        return out

def test_quote_on_page_is_verified():
    result = verify_quotes([(URL, QUOTE)], transport=FakeTransport({URL: _response(URL, 200, PAGE)}))
    assert result[(URL, QUOTE)].status == "verified"

def test_quote_absent_is_reported():
    result = verify_quotes([(URL, "fewer than 10 businesses")], transport=FakeTransport({URL: _response(URL, 200, PAGE)}))
    assert result[(URL, "fewer than 10 businesses")].status == "quote_missing"

def test_404_and_410_are_gone():
    for status in (404, 410):
        result = verify_quotes([(URL, QUOTE)], transport=FakeTransport({URL: _response(URL, status)}))
        assert result[(URL, QUOTE)].status == "gone"

def test_403_is_unreachable():
    result = verify_quotes([(URL, QUOTE)], transport=FakeTransport({URL: _response(URL, 403)}))
    assert result[(URL, QUOTE)].status == "unreachable"

def test_batch_failure_marks_every_url_unreachable():
    result = verify_quotes([(URL, QUOTE)], transport=FakeTransport({URL: requests.Timeout("slow")}))
    assert result[(URL, QUOTE)].status == "unreachable"

def test_one_batch_for_all_pairs():
    transport = FakeTransport({URL: _response(URL, 200, PAGE)})
    verify_quotes([(URL, QUOTE), (URL, "trade businesses")], transport=transport)
    assert transport.calls == [[URL]]

def test_server_error_is_unreachable():
    result = verify_quotes([(URL, QUOTE)], transport=FakeTransport({URL: _response(URL, 500)}))
    assert result[(URL, QUOTE)].status == "unreachable"

def test_mixed_urls_share_one_request_and_keep_their_own_status():
    gone_url = "https://example.org/removed"
    transport = FakeTransport({
        gone_url: _response(gone_url, 404),
        URL: _response(URL, 200, PAGE),
    })
    result = verify_quotes([(gone_url, QUOTE), (URL, QUOTE)], transport=transport)
    assert transport.calls == [[gone_url, URL]]
    assert result[(gone_url, QUOTE)].status == "gone"
    assert result[(URL, QUOTE)].status == "verified"
