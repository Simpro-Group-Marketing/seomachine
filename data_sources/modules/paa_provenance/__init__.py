"""Single-responsibility PAA provenance implementation package."""

from .dependencies import PaaDependencies
from .collection import (
    build_answersocrates_artifact,
    collect_answersocrates_raw_capture,
    find_npx_executable,
    write_answersocrates_artifact,
)
from .evaluation import check_content
from .results import check_file, evaluate_content, evaluate_file

__all__ = [
    "PaaDependencies",
    "build_answersocrates_artifact",
    "collect_answersocrates_raw_capture",
    "find_npx_executable",
    "write_answersocrates_artifact",
    "check_content",
    "check_file",
    "evaluate_content",
    "evaluate_file",
]
