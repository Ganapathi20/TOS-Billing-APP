"""
State Manager
=============
Manages the shared transaction state between the User flow
and the Approver flow. When the User test completes its flow,
it writes the transaction details here. The Approver test reads
from here to locate the exact transaction it needs to approve.

This is the 'State Handoff' described in the architecture:
   User Test → writes → StateManager → reads → Approver Test

For single-machine runs, this is an in-memory singleton.
For distributed runs, the write/read methods can be swapped
to use a Redis cache, a shared JSON file, or a REST endpoint.
"""

import json
import os
import time
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional
from pathlib import Path

log = logging.getLogger(__name__)

_STATE_FILE = Path("framework/data/shared_state.json")


@dataclass
class TransactionState:
    """
    All data produced by the User flow that the Approver flow needs.
    """
    iteration:          int         = 0
    user_mobile:        str         = ""
    user_name:          str         = ""
    transaction_id:     str         = ""
    amount:             str         = ""
    upi_id:             str         = ""      # NEW — UPI ID entered by user
    payment_method:     str         = ""      # "upi_id" | "qr_code"
    timestamp_unix:     float       = 0.0
    timestamp_display:  str         = ""
    status_after_user:  str         = ""      # e.g. "Payment Pending Approval"
    qr_proof_path:      str         = ""      # Device path of proof image
    notification_sent:  bool        = False
    charges_calculated: str         = ""      # Calculated charge shown to user
    final_amount:       str         = ""      # Total including charges


@dataclass
class AppState:
    """Top-level application state — holds multiple transactions."""
    transactions: dict = field(default_factory=dict)   # keyed by iteration
    current_iteration: int = 1


class StateManager:
    """
    Thread-safe(ish) in-memory + file-backed state store.
    Single instance shared across all test modules.
    """

    _instance: Optional["StateManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._app = AppState()
            cls._instance._load_from_file()
        return cls._instance

    # ── Write (called by User flow) ───────────────────────────
    def set_transaction(self, iteration: int, txn: TransactionState):
        """Store transaction state after User flow completes."""
        txn.iteration = iteration
        self._app.transactions[str(iteration)] = txn
        self._persist()
        log.info("[State] Saved transaction for iteration %d: txn_id=%s",
                 iteration, txn.transaction_id)

    def update_field(self, iteration: int, **kwargs):
        """Update specific fields of an existing transaction state."""
        txn = self.get_transaction(iteration)
        if txn:
            for k, v in kwargs.items():
                setattr(txn, k, v)
            self._persist()
            log.info("[State] Updated iteration %d: %s", iteration, kwargs)

    # ── Read (called by Approver flow) ────────────────────────
    def get_transaction(self, iteration: int) -> Optional[TransactionState]:
        """Retrieve transaction state for a given iteration."""
        txn_dict = self._app.transactions.get(str(iteration))
        if txn_dict is None:
            log.warning("[State] No transaction found for iteration %d", iteration)
            return None
        if isinstance(txn_dict, TransactionState):
            return txn_dict
        # Re-hydrate from dict (loaded from file)
        return TransactionState(**txn_dict)

    def wait_for_transaction(self, iteration: int,
                              timeout: int = 60) -> Optional[TransactionState]:
        """
        Poll until the transaction for this iteration is available.
        Useful when Approver test starts before User test finishes writing.
        """
        start = time.time()
        while time.time() - start < timeout:
            txn = self.get_transaction(iteration)
            if txn and txn.transaction_id:
                return txn
            time.sleep(2)
            log.debug("[State] Waiting for iteration %d state...", iteration)
        raise TimeoutError(
            f"Transaction state for iteration {iteration} not available "
            f"within {timeout}s. Ensure User flow ran before Approver flow."
        )

    def get_transaction_id(self, iteration: int) -> str:
        txn = self.get_transaction(iteration)
        return txn.transaction_id if txn else ""

    def clear(self):
        """Reset all state (called in teardown)."""
        self._app = AppState()
        if _STATE_FILE.exists():
            _STATE_FILE.unlink()
        log.info("[State] All state cleared")

    # ── Persistence ───────────────────────────────────────────
    def _persist(self):
        """Write state to disk so it survives process restarts."""
        os.makedirs(_STATE_FILE.parent, exist_ok=True)
        serialisable = {}
        for k, v in self._app.transactions.items():
            serialisable[k] = asdict(v) if isinstance(v, TransactionState) else v
        with open(_STATE_FILE, "w") as f:
            json.dump({"transactions": serialisable,
                       "iteration":    self._app.current_iteration}, f, indent=2)

    def _load_from_file(self):
        """Restore state from disk if file exists (cross-session persistence)."""
        if _STATE_FILE.exists():
            try:
                with open(_STATE_FILE) as f:
                    data = json.load(f)
                self._app.transactions     = data.get("transactions", {})
                self._app.current_iteration = data.get("iteration", 1)
                log.info("[State] Restored %d transactions from disk",
                         len(self._app.transactions))
            except Exception as e:
                log.warning("[State] Could not load state file: %s", e)
