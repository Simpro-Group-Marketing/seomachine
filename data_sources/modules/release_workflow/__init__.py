"""Pure release-workflow policy decisions."""

from .chain_decision import (
    DRAFT_READY_NOT_RELEASE_READY,
    NORMAL_CHAIN_REQUIRED,
    OPTIMIZED_TAIL_ALLOWED,
    ReleaseChainDecision,
    decide_release_chain,
)

__all__ = [
    "DRAFT_READY_NOT_RELEASE_READY",
    "NORMAL_CHAIN_REQUIRED",
    "OPTIMIZED_TAIL_ALLOWED",
    "ReleaseChainDecision",
    "decide_release_chain",
]
