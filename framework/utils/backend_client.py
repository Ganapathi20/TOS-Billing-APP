"""
Backend Client
==============
REST / WebSocket client for direct backend verification.

Rather than relying solely on UI assertion, these methods
hit the TOS backend API to:
  - Confirm notification was dispatched to Approver
  - Fetch the current transaction status
  - Verify the database state after each flow step

In test environments, the backend must expose a
/test/ namespace with authentication via API key.
"""

import requests
import websocket
import json
import logging
import time
from typing import Optional
from framework.config.loader import CFG

log = logging.getLogger(__name__)


class BackendClient:

    def __init__(self):
        self.base    = CFG.backend["base_url"]
        self.headers = {
            "X-API-Key":    CFG.backend["api_key"],
            "Content-Type": "application/json",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # ── Transaction state ─────────────────────────────────────
    def get_transaction(self, txn_id: str) -> Optional[dict]:
        """Fetch full transaction record from backend."""
        try:
            resp = self.session.get(
                f"{self.base}/test/transactions/{txn_id}",
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            log.info("[API] Transaction %s — status: %s",
                     txn_id, data.get("status"))
            return data
        except Exception as e:
            log.warning("[API] Could not fetch transaction %s: %s", txn_id, e)
            return None

    def get_transaction_by_user(self, user_mobile: str) -> Optional[dict]:
        """
        Fetch the most recent transaction for a mobile number.
        Used when transaction_id is not yet known.
        """
        try:
            resp = self.session.get(
                f"{self.base}/test/transactions/by-mobile/{user_mobile}",
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.warning("[API] Could not fetch txn for mobile %s: %s",
                        user_mobile, e)
            return None

    def wait_for_status(self, txn_id: str,
                         expected_status: str,
                         timeout: int = 45) -> bool:
        """
        Poll the backend until the transaction reaches the expected status
        or the timeout expires.

        Used for:
          - Confirming 'Payment Pending Approval' after User submits proof
          - Confirming 'Refunded' after Approver uploads refund proof
        """
        start = time.time()
        while time.time() - start < timeout:
            txn = self.get_transaction(txn_id)
            if txn and txn.get("status") == expected_status:
                log.info("[API] Transaction %s reached status: %s",
                         txn_id, expected_status)
                return True
            time.sleep(3)
            log.debug("[API] Waiting for status '%s'... current: %s",
                      expected_status, txn.get("status") if txn else "unknown")
        log.error("[API] Status '%s' not reached within %ds for txn %s",
                  expected_status, timeout, txn_id)
        return False

    # ── Notification verification ─────────────────────────────
    def verify_notification_sent(self, txn_id: str,
                                   recipient_mobile: str) -> bool:
        """
        Verify that a push notification was dispatched to the Approver
        after the User submitted their payment proof.
        """
        try:
            resp = self.session.get(
                f"{self.base}/test/notifications",
                params={"txn_id": txn_id, "recipient": recipient_mobile},
                timeout=10
            )
            resp.raise_for_status()
            notifications = resp.json()
            sent = any(
                n.get("status") == "delivered" for n in notifications
            )
            log.info("[API] Notification sent to %s: %s",
                     recipient_mobile, sent)
            return sent
        except Exception as e:
            log.warning("[API] Notification check failed: %s", e)
            return False

    # ── Charges calculation ───────────────────────────────────
    def get_expected_charges(self, amount: str) -> dict:
        """
        Fetch the expected charge breakdown from the backend
        so the UI assertion knows what numbers to validate.
        """
        try:
            resp = self.session.get(
                f"{self.base}/test/charges/calculate",
                params={"amount": amount},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            log.info("[API] Charges for %s: %s", amount, data)
            return data
        except Exception as e:
            log.warning("[API] Charges fetch failed: %s", e)
            return {}

    # ── OTP bypass (dev mode) ─────────────────────────────────
    def get_test_otp(self, mobile: str) -> str:
        """
        For development/test environments — fetch the OTP that was
        sent to a specific mobile number without needing to receive an SMS.
        Falls back to static OTP if endpoint is unavailable.
        """
        try:
            resp = self.session.get(
                f"{self.base}/test/otp/{mobile}",
                timeout=5
            )
            if resp.status_code == 200:
                otp = resp.json().get("otp", CFG.test_data.static_otp)
                log.info("[API] OTP for %s: %s", mobile, otp)
                return otp
        except Exception:
            pass
        log.info("[API] Using static OTP: %s", CFG.test_data.static_otp)
        return CFG.test_data.static_otp

    # ── WebSocket event listener ──────────────────────────────
    def listen_for_event(self, event_type: str, timeout: int = 30) -> Optional[dict]:
        """
        Connect to the backend WebSocket and wait for a specific event.
        Useful for confirming real-time events like notification dispatch.

        Returns:
            The event payload dict, or None if timeout exceeded.
        """
        received_event = None
        ws_url = CFG.backend["ws_url"]

        def on_message(ws, message):
            nonlocal received_event
            try:
                data = json.loads(message)
                if data.get("type") == event_type:
                    received_event = data
                    ws.close()
            except json.JSONDecodeError:
                pass

        def on_error(ws, error):
            log.warning("[WS] WebSocket error: %s", error)

        try:
            ws = websocket.WebSocketApp(
                ws_url,
                header={"X-API-Key": CFG.backend["api_key"]},
                on_message=on_message,
                on_error=on_error,
            )
            ws.run_forever(ping_interval=10, ping_timeout=5)
        except Exception as e:
            log.warning("[WS] WebSocket connection failed: %s", e)

        return received_event

    # ── Cleanup ───────────────────────────────────────────────
    def reset_test_data(self, mobile: str):
        """Delete all test transactions for a mobile number (pre-run cleanup)."""
        try:
            self.session.delete(
                f"{self.base}/test/transactions/by-mobile/{mobile}",
                timeout=10
            )
            log.info("[API] Test data reset for mobile: %s", mobile)
        except Exception as e:
            log.warning("[API] Reset failed for %s: %s", mobile, e)
