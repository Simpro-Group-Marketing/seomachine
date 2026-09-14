"""Fail-fast lifecycle boundary for one serial readiness execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from .session import ValidationSession
from .telemetry import ReadinessTelemetry
from ..public_http import PublicHttpTransport


def run_in_session(
    *,
    input_paths: Mapping[str, str | Path | None],
    workspace_root: str | Path,
    runner: Callable[..., Mapping[str, Any]],
    runner_kwargs: Mapping[str, Any],
    blocked_result: Callable[[ValueError], Mapping[str, Any]],
    connector_factory: Callable[[], Any],
    claim_loader: Callable[[Any], Any],
    transport_factory: Callable[[], Any] | None = None,
    telemetry: ReadinessTelemetry | None,
) -> Mapping[str, Any]:
    """Capture first, fail closed, and close external resources on every exit."""
    try:
        session = ValidationSession.capture(
            input_paths,
            workspace_root=workspace_root,
            connector_factory=connector_factory,
            claim_loader=claim_loader,
            transport_factory=transport_factory or (
                lambda: PublicHttpTransport(
                    observer=telemetry.http_observer if telemetry is not None else None
                )
            ),
            telemetry=telemetry,
        )
    except ValueError as error:
        return blocked_result(error)

    with session:
        return runner(
            **dict(runner_kwargs),
            session=session,
            input_capture_error=None,
            telemetry=telemetry,
        )
