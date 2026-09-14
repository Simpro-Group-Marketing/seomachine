"""Shared bounded file, hashing, and strict JSON primitives."""

from .hashing import (
    HASH_CHUNK_BYTES,
    canonical_json_bytes,
    canonical_json_sha256,
    stream_sha256,
)
from .json_contracts import decode_utf8, parse_json, parse_json_object
from .json_encoding import (
    JsonOutputLimitError,
    bounded_canonical_json_bytes,
    bounded_json_bytes,
)
from .writers import (
    OutputByteLimitError,
    atomic_write_bytes,
    atomic_write_canonical_json,
    atomic_write_text,
)
from .http_responses import read_response_bytes, read_response_json
from .readers import FileIdentity, file_identity, read_bounded

__all__ = [
    "FileIdentity",
    "HASH_CHUNK_BYTES",
    "JsonOutputLimitError",
    "OutputByteLimitError",
    "atomic_write_bytes",
    "atomic_write_canonical_json",
    "atomic_write_text",
    "bounded_canonical_json_bytes",
    "bounded_json_bytes",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "decode_utf8",
    "file_identity",
    "parse_json",
    "parse_json_object",
    "read_bounded",
    "read_response_bytes",
    "read_response_json",
    "stream_sha256",
]
