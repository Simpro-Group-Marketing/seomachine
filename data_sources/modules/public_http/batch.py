"""Bounded stable-order batch execution for public HTTP requests."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator, Mapping

import requests

from .policies import MAX_PER_HOST, MAX_WORKERS, HttpRequestPolicy
from .snapshot import ResponseSnapshot


MIB = 1024 * 1024
Observer = Callable[[str, int], None]
Request = Callable[..., requests.Response]


@dataclass(frozen=True, slots=True)
class HttpBatchPolicy:
    """Concurrency and aggregate-memory limits for one transport batch."""

    max_workers: int = MAX_WORKERS
    max_per_host: int = MAX_PER_HOST
    max_aggregate_response_bytes: int = 32 * MIB

    def __post_init__(self) -> None:
        _positive_integer(self.max_workers, field_name="max_workers")
        _positive_integer(self.max_per_host, field_name="max_per_host")
        _positive_integer(
            self.max_aggregate_response_bytes,
            field_name="max_aggregate_response_bytes",
        )
        if self.max_per_host > self.max_workers:
            raise ValueError("max_per_host cannot exceed max_workers")
@dataclass(slots=True)
class _Pending:
    key: str
    reserved_bytes: int


@dataclass(slots=True)
class _BatchState:
    iterator: Iterator[str]
    order: list[str] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)
    responses: dict[str, ResponseSnapshot] = field(default_factory=dict)
    pending: dict[Future[requests.Response], _Pending] = field(default_factory=dict)
    deferred: tuple[str, str] | None = None
    response_bytes: int = 0
    exhausted: bool = False

    @property
    def reserved_bytes(self) -> int:
        return sum(item.reserved_bytes for item in self.pending.values())


def execute_many(
    method: str,
    urls: Iterable[str],
    *,
    request: Request,
    key_for: Callable[[str], str],
    request_policy: HttpRequestPolicy,
    batch_policy: HttpBatchPolicy,
    headers: Mapping[str, str] | None,
    observer: Observer | None,
) -> list[requests.Response]:
    """Execute unique requests through a bounded sliding window."""
    if not isinstance(request_policy, HttpRequestPolicy):
        raise ValueError("HTTP batch requires a declared typed request policy")
    if not isinstance(batch_policy, HttpBatchPolicy):
        raise ValueError("HTTP batch requires a declared typed batch policy")
    state = _BatchState(iter(urls))
    try:
        with ThreadPoolExecutor(max_workers=batch_policy.max_workers) as executor:
            try:
                while not state.exhausted or state.pending or state.deferred is not None:
                    _fill_window(
                        state,
                        executor=executor,
                        method=method,
                        request=request,
                        key_for=key_for,
                        request_policy=request_policy,
                        batch_policy=batch_policy,
                        headers=headers,
                        observer=observer,
                    )
                    if not state.pending:
                        if state.deferred is not None:
                            raise ValueError(
                                "public HTTP batch exceeds aggregate response byte limit"
                            )
                        continue
                    _collect_completed(
                        state,
                        request_policy=request_policy,
                        observer=observer,
                    )
            except BaseException:
                _cancel_pending(state, observer=observer)
                raise
        return [state.responses[key].response() for key in state.order]
    finally:
        if state.response_bytes:
            _observe(observer, "retained_bytes_delta", -state.response_bytes)


def resolve_batch_policy(
    policy: HttpBatchPolicy | None,
    *,
    max_workers: int,
    max_per_host: int,
) -> HttpBatchPolicy:
    """Bridge legacy constructor limits to the typed batch policy."""
    if policy is None:
        return HttpBatchPolicy(max_workers=max_workers, max_per_host=max_per_host)
    if not isinstance(policy, HttpBatchPolicy):
        raise ValueError("batch_policy must be an HttpBatchPolicy")
    if max_workers != MAX_WORKERS or max_per_host != MAX_PER_HOST:
        raise ValueError("batch_policy cannot be combined with legacy concurrency arguments")
    return policy


def _fill_window(
    state: _BatchState,
    *,
    executor: ThreadPoolExecutor,
    method: str,
    request: Request,
    key_for: Callable[[str], str],
    request_policy: HttpRequestPolicy,
    batch_policy: HttpBatchPolicy,
    headers: Mapping[str, str] | None,
    observer: Observer | None,
) -> None:
    while len(state.pending) < batch_policy.max_workers and not state.exhausted:
        raw_url, key = _next_unique(state, key_for=key_for, observer=observer)
        if raw_url is None or key is None:
            continue
        if not _can_reserve(state, request_policy=request_policy, batch_policy=batch_policy):
            state.deferred = (raw_url, key)
            return
        future = executor.submit(
            request,
            method,
            raw_url,
            policy=request_policy,
            headers=headers,
        )
        state.pending[future] = _Pending(key, request_policy.max_response_bytes)
        _observe(observer, "reserved_bytes_delta", request_policy.max_response_bytes)


def _next_unique(
    state: _BatchState,
    *,
    key_for: Callable[[str], str],
    observer: Observer | None,
) -> tuple[str | None, str | None]:
    if state.deferred is not None:
        value = state.deferred
        state.deferred = None
        return value
    try:
        raw_url = next(state.iterator)
    except StopIteration:
        state.exhausted = True
        return None, None
    key = key_for(raw_url)
    state.order.append(key)
    if key in state.seen:
        _observe(observer, "deduplicated_requests", 1)
        return None, None
    state.seen.add(key)
    return raw_url, key


def _can_reserve(
    state: _BatchState,
    *,
    request_policy: HttpRequestPolicy,
    batch_policy: HttpBatchPolicy,
) -> bool:
    projected = (
        state.response_bytes
        + state.reserved_bytes
        + request_policy.max_response_bytes
    )
    return projected <= batch_policy.max_aggregate_response_bytes


def _collect_completed(
    state: _BatchState,
    *,
    request_policy: HttpRequestPolicy,
    observer: Observer | None,
) -> None:
    completed, _ = wait(tuple(state.pending), return_when=FIRST_COMPLETED)
    for future in completed:
        pending = state.pending.pop(future)
        _observe(observer, "reserved_bytes_delta", -pending.reserved_bytes)
        snapshot = ResponseSnapshot.capture(future.result(), policy=request_policy)
        state.response_bytes += len(snapshot.body)
        state.responses[pending.key] = snapshot
        _observe(observer, "retained_bytes_delta", len(snapshot.body))


def _cancel_pending(state: _BatchState, *, observer: Observer | None) -> None:
    for future, pending in tuple(state.pending.items()):
        future.cancel()
        _observe(observer, "reserved_bytes_delta", -pending.reserved_bytes)
    state.pending.clear()


def _positive_integer(value: object, *, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer")


def _observe(observer: Observer | None, name: str, amount: int) -> None:
    if observer is None:
        return
    try:
        observer(name, amount)
    except Exception:
        return


DEFAULT_HTTP_BATCH_POLICY = HttpBatchPolicy()
