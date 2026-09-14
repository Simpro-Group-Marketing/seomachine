from __future__ import annotations

import requests
import pytest

from data_sources.modules.artifact_runtime.limits import JSON_MAX_BYTES
from data_sources.modules.publisher_transport import (
    publisher_response_preview,
    read_wordpress_json,
)


def test_wordpress_response_rejects_declared_oversize_before_json_decode() -> None:
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Length"] = str(JSON_MAX_BYTES + 1)
    response._content = b"{}"

    with pytest.raises(ValueError, match="WordPress response exceeds"):
        read_wordpress_json(response)


def test_publisher_error_preview_omits_oversized_response_body() -> None:
    response = requests.Response()
    response.status_code = 500
    response.headers["Content-Length"] = str(JSON_MAX_BYTES + 1)
    response._content = b"secret error body"

    assert publisher_response_preview(response) == (
        f"[response body omitted: exceeds {JSON_MAX_BYTES} bytes]"
    )
