"""Customer-proof selection, evidence, and diversity components."""

from .contracts import CustomerProofDataError
from .nonconnector_contracts import NonVaultProofDataError
from .nonconnector_selection import select_nonvault_customer_proofs
from .selection import build_customer_proof_slate, select_customer_proofs

__all__ = [
    "CustomerProofDataError",
    "NonVaultProofDataError",
    "build_customer_proof_slate",
    "select_customer_proofs",
    "select_nonvault_customer_proofs",
]
