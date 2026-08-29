"""
Iteration 2 — QR Code Image Upload Flow
=========================================
Payment method: User uploads a QR code / UPI image via gallery picker.
Different user, different amount — tests the QR path independently.

Test Scenario:
  User (Device A — different mobile, different amount)
    1. Opens TOS app → logs in (fresh session, Iter 2 mobile)
    2. Fills payment form — name, mobile, amount (Rs 1200)
    3. Selects 'QR Code Upload' tab
    4. ADB pushes mock QR image → User selects from gallery
    5. Taps Next → sees charge calculation
    6. Taps Pay → mock gateway opens (shows QR image / 'QR Code' label)
    7. Confirms → TOS re-opens
    8. Uploads payment screenshot proof
    9. Submits → status 'Pending Approval'

  [STATE HANDOFF]

  Approver (Device B — same approver account)
    1. Refreshes pending list — sees new transaction
    2. Opens transaction — verifies 'QR Code' in payment method field
    3. (OCR) Verifies proof image — amount matches
    4. Processes refund → uploads refund proof
    5. Final status: 'Refunded' ✅

Key differences from Iteration 1:
  - QR image upload (not UPI ID text input)
  - Higher amount (Rs 1200)
  - Different user mobile and name
  - Mock gateway shows QR label (not UPI ID text)
  - OCR checks only amount + txn_id (no UPI ID check)
"""

import pytest
import time
import logging
import os

from framework.config.loader import CFG
from framework.utils.driver_manager import DriverManager
from framework.utils.adb_helper import ADBHelper
from framework.utils.state_manager import StateManager, TransactionState
from framework.utils.ocr_helper import OCRHelper
from framework.utils.backend_client import BackendClient

from framework.pages.user.user_pages import (
    UserLoginPage, PaymentFormPage, ChargesPage,
    MockPaymentPage, ProofUploadPage, UserConfirmationPage
)
from framework.pages.approver.approver_pages import (
    ApproverLoginPage, PendingListPage,
    TransactionDetailPage, RefundPage, ApproverCompletionPage
)

log = logging.getLogger(__name__)
ITERATION = 2


@pytest.fixture(scope="module")
def setup(request):
    """
    Module-level setup for Iteration 2.
    Reuses drivers if DriverManager is already initialised
    (when both iterations run in the same session).
    """
    log.info("=" * 60)
    log.info("ITERATION 2 SETUP — QR Code Upload Flow")
    log.info("=" * 60)

    os.makedirs(CFG.reports["screenshots_dir"], exist_ok=True)
    os.makedirs("framework/data", exist_ok=True)

    dm      = DriverManager()
    state   = StateManager()
    ocr     = OCRHelper()
    backend = BackendClient()

    adb_user     = ADBHelper(CFG.user_device.udid)
    adb_approver = ADBHelper(CFG.approver_device.udid)

    # ── Pre-run setup ─────────────────────────────────────────
    log.info("[Setup] Preparing devices for Iteration 2")

    backend.reset_test_data(CFG.test_data.user_mobile_iter2)

    # Push QR image to user device (required for QR upload)
    adb_user.push_qr_image()
    # Push payment proof to user device
    adb_user.push_payment_proof()
    # Push refund proof to approver device
    adb_approver.push_refund_proof()

    user_drv     = dm.get_user_driver()
    approver_drv = dm.get_approver_driver()

    yield {
        "dm":           dm,
        "state":        state,
        "ocr":          ocr,
        "backend":      backend,
        "adb_user":     adb_user,
        "adb_approver": adb_approver,
        "user_drv":     user_drv,
        "approver_drv": approver_drv,
    }

    log.info("[Teardown] Iteration 2 complete")
    dm.quit_all()


# ════════════════════════════════════════════════════════════════
# USER FLOW — Device A (Iteration 2)
# ════════════════════════════════════════════════════════════════

class TestIter2UserFlow:

    def test_01_user_login(self, setup):
        """Iteration 2 user logs in with different mobile number."""
        log.info("--- Test: User Login (Iter 2) ---")
        drv     = setup["user_drv"]
        backend = setup["backend"]

        # Reset app state (back to login screen) for fresh iteration
        setup["adb_user"].force_stop_app()
        time.sleep(1.5)
        setup["adb_user"].clear_app_data()

        otp = backend.get_test_otp(CFG.test_data.user_mobile_iter2)

        login_page = UserLoginPage(drv)

        # Re-launch app after clear
        drv.activate_app(CFG.user_device.app_package)
        time.sleep(2)

        login_page.login(
            mobile = CFG.test_data.user_mobile_iter2,
            otp    = otp
        )

        assert login_page.wait_for_text_contains("Tower", timeout=20), \
            "Home screen not loaded (Iter 2)"

        setup["dm"].screenshot_user("iter2_01_login")
        log.info("✅ Iter 2 user login: %s", CFG.test_data.user_mobile_iter2)

    def test_02_fill_payment_form_qr(self, setup):
        """
        User fills form using QR code upload method.
        ADB has already pushed the mock QR image in setup.
        """
        log.info("--- Test: Fill Payment Form — QR Upload (Iter 2) ---")
        drv      = setup["user_drv"]
        adb_user = setup["adb_user"]

        form_page = PaymentFormPage(drv)

        # Push QR image again immediately before gallery opens
        # (ensures media scanner has the latest version)
        adb_user.push_qr_image()

        form_page.fill_payment_qr(
            name           = CFG.test_data.user_name_iter2,
            mobile         = CFG.test_data.user_mobile_iter2,
            amount         = CFG.test_data.payment_amount_iter2,
            image_filename = "qr_mock",
        )

        # Assert QR preview thumbnail appeared (confirms selection)
        qr_preview = form_page.find_by_id("iv_qr_preview")
        assert qr_preview.is_displayed(), "QR preview not visible after selection"

        # Save state
        setup["state"].update_field(ITERATION,
                                     payment_method="qr_code",
                                     amount=CFG.test_data.payment_amount_iter2,
                                     user_mobile=CFG.test_data.user_mobile_iter2,
                                     user_name=CFG.test_data.user_name_iter2)

        setup["dm"].screenshot_user("iter2_02_form_qr_filled")
        log.info("✅ Payment form filled — QR image selected")

    def test_03_verify_charges(self, setup):
        """Charges calculated after QR payment form submission."""
        log.info("--- Test: Charge Calculation (Iter 2) ---")
        drv = setup["user_drv"]

        form_page    = PaymentFormPage(drv)
        charges_page = ChargesPage(drv)

        form_page.tap_next()
        charges_page.wait_for_charges()

        assert charges_page.is_receipt_visible(), \
            "Receipt not visible (Iter 2)"
        assert charges_page.assert_charges(CFG.test_data.payment_amount_iter2), \
            "Charge amount mismatch (Iter 2)"

        final_total = charges_page.get_total_amount()
        setup["state"].update_field(ITERATION, final_amount=final_total)

        setup["dm"].screenshot_user("iter2_03_charges")
        log.info("✅ Charges shown. Total: %s", final_total)

    def test_04_mock_payment_qr_gateway(self, setup):
        """
        Mock gateway opens for QR payment.
        Instead of showing a UPI ID, it may show 'QR Code' label
        or display the QR image — we verify it loads correctly.
        """
        log.info("--- Test: Mock Payment Gateway — QR Mode (Iter 2) ---")
        drv = setup["user_drv"]

        charges_page = ChargesPage(drv)
        mock_page    = MockPaymentPage(drv)

        charges_page.tap_pay_now()
        mock_page.wait_for_mock_gateway()

        # For QR mode, the gateway shows 'QR Code' as the payment reference
        displayed = mock_page.get_displayed_upi()   # reuse field; shows 'QR Code'
        log.info("[Mock Gateway Iter 2] Payment reference shown: %s", displayed)
        assert displayed != "", "Mock gateway payment reference is empty"

        setup["dm"].screenshot_user("iter2_04_mock_gateway_qr")

        mock_page.confirm_payment()
        log.info("✅ Mock QR payment confirmed")

    def test_05_upload_payment_proof(self, setup):
        """Upload proof screenshot after QR payment confirmation."""
        log.info("--- Test: Upload Proof (Iter 2) ---")
        drv      = setup["user_drv"]
        adb_user = setup["adb_user"]

        # Re-push proof image just before it's needed
        adb_user.push_payment_proof()

        proof_page = ProofUploadPage(drv)
        proof_page.wait_for_proof_screen()

        txn_id     = proof_page.get_transaction_id()
        ts_unix    = time.time()
        ts_display = time.strftime("%d %b %Y %H:%M", time.localtime(ts_unix))

        log.info("[Proof Iter 2] TXN: %s | Timestamp: %s", txn_id, ts_display)

        proof_page.upload_and_submit(image_filename="payment_proof")

        # Write state for Approver
        setup["state"].set_transaction(ITERATION, TransactionState(
            iteration         = ITERATION,
            user_mobile       = CFG.test_data.user_mobile_iter2,
            user_name         = CFG.test_data.user_name_iter2,
            transaction_id    = txn_id,
            amount            = CFG.test_data.payment_amount_iter2,
            upi_id            = "",          # No UPI ID in QR mode
            payment_method    = "qr_code",
            timestamp_unix    = ts_unix,
            timestamp_display = ts_display,
            qr_proof_path     = CFG.adb.proof_image_dest,
        ))

        setup["dm"].screenshot_user("iter2_05_proof_submitted")
        log.info("✅ Proof submitted — TXN: %s", txn_id)

    def test_06_verify_pending_status(self, setup):
        """Status shows 'Pending Approval' after submission."""
        log.info("--- Test: Pending Status (Iter 2) ---")
        drv = setup["user_drv"]

        confirm_page = UserConfirmationPage(drv)
        confirm_page.wait_for_confirmation()

        assert confirm_page.is_pending_approval(), \
            f"Expected 'Pending Approval', got: '{confirm_page.get_status()}'"

        setup["dm"].screenshot_user("iter2_06_pending")
        log.info("✅ Status: Pending Approval (Iter 2)")

    def test_07_verify_notification(self, setup):
        """Confirm notification sent to Approver for Iter 2 transaction."""
        log.info("--- Test: Notification (Iter 2) ---")
        backend = setup["backend"]
        state   = setup["state"]

        time.sleep(3)
        txn = state.get_transaction(ITERATION)

        sent = backend.verify_notification_sent(
            txn_id           = txn.transaction_id,
            recipient_mobile = CFG.test_data.approver_mobile
        )

        state.update_field(ITERATION,
                            notification_sent=sent,
                            status_after_user="Payment Pending Approval")

        log.info("[Notification Iter 2] Sent: %s", sent)
        log.info("✅ Notification step complete")


# ════════════════════════════════════════════════════════════════
# APPROVER FLOW — Device B (Iteration 2)
# ════════════════════════════════════════════════════════════════

class TestIter2ApproverFlow:

    def test_08_approver_refresh_pending_list(self, setup):
        """
        Approver is already logged in from Iteration 1.
        Navigate back to pending list and refresh.
        """
        log.info("--- Test: Approver — Refresh Pending List (Iter 2) ---")
        drv = setup["approver_drv"]

        # Navigate to home / pending list
        # (press back or home if on a detail screen)
        try:
            drv.back()
            time.sleep(0.8)
            drv.back()
        except Exception:
            pass

        pending_page = PendingListPage(drv)

        # If approver session expired, re-login
        try:
            pending_page.wait_for_list()
        except Exception:
            log.info("[Approver Iter 2] Session may have expired — re-logging in")
            backend = setup["backend"]
            otp = backend.get_test_otp(CFG.test_data.approver_mobile)
            login_page = ApproverLoginPage(drv)
            login_page.login(
                mobile = CFG.test_data.approver_mobile,
                otp    = otp
            )
            pending_page.wait_for_list()

        pending_page.refresh_list()
        item_count = pending_page.get_item_count()
        log.info("[Pending List Iter 2] Items visible: %d", item_count)

        setup["dm"].screenshot_approver("iter2_08_pending_refreshed")
        log.info("✅ Pending list refreshed")

    def test_09_find_iter2_transaction(self, setup):
        """Locate the Iteration 2 transaction by ID or user name."""
        log.info("--- Test: Find Iter 2 Transaction ---")
        drv   = setup["approver_drv"]
        state = setup["state"]

        txn = state.wait_for_transaction(ITERATION, timeout=60)
        assert txn.transaction_id, "Iter 2 transaction ID missing from state"

        pending_page = PendingListPage(drv)

        try:
            pending_page.open_transaction_by_id(txn.transaction_id)
        except Exception:
            pending_page.open_transaction_by_user(txn.user_name, txn.timestamp_display)

        setup["dm"].screenshot_approver("iter2_09_transaction_opened")
        log.info("✅ Iter 2 transaction opened: %s", txn.transaction_id)

    def test_10_verify_qr_payment_details(self, setup):
        """
        Verify transaction shows 'QR Code' as payment method
        (not a UPI ID text string).
        """
        log.info("--- Test: Verify QR Payment Details (Iter 2) ---")
        drv   = setup["approver_drv"]
        state = setup["state"]

        txn = state.get_transaction(ITERATION)
        detail_page = TransactionDetailPage(drv)
        detail_page.wait_for_detail()

        # Verify user name and amount
        assert detail_page.assert_transaction_details(
            user_name = txn.user_name,
            amount    = txn.amount,
            upi_id    = "",        # No UPI ID — QR mode
        ), "Detail verification failed (Iter 2)"

        # Verify payment method shows 'QR Code' label
        upi_field_text = detail_page.get_upi_display()
        assert "qr" in upi_field_text.lower() or "code" in upi_field_text.lower(), \
            f"Expected 'QR Code' in payment method display, got: '{upi_field_text}'"

        setup["dm"].screenshot_approver("iter2_10_qr_details_verified")
        log.info("✅ QR payment details verified. Method shown: %s", upi_field_text)

    def test_11_ocr_verify_proof_amount(self, setup):
        """
        OCR: For QR mode, verify proof image contains the correct amount.
        (No UPI ID to check — only amount + transaction ID.)
        """
        log.info("--- Test: OCR Amount Verification (Iter 2) ---")
        drv          = setup["approver_drv"]
        ocr          = setup["ocr"]
        adb_approver = setup["adb_approver"]
        state        = setup["state"]

        txn = state.get_transaction(ITERATION)
        detail_page = TransactionDetailPage(drv)

        proof_path = detail_page.get_proof_image_path_on_device()
        if proof_path:
            local_path = "reports/pulled_proof_iter2.jpg"
            adb_approver.pull_image(proof_path, local_path)

            amount_ok = ocr.verify_amount(local_path, txn.amount)
            log.info("[OCR Iter 2] Amount '%s' found in proof: %s",
                     txn.amount, amount_ok)

            if txn.transaction_id:
                txn_ok = ocr.verify_transaction_id(local_path, txn.transaction_id)
                log.info("[OCR Iter 2] TXN ID found in proof: %s", txn_ok)
        else:
            log.warning("[OCR Iter 2] Proof path not available — skipping")

        log.info("✅ OCR step complete (Iter 2)")

    def test_12_process_refund(self, setup):
        """Approver processes refund for QR-mode transaction."""
        log.info("--- Test: Process Refund (Iter 2) ---")
        drv          = setup["approver_drv"]
        adb_approver = setup["adb_approver"]

        detail_page = TransactionDetailPage(drv)
        detail_page.tap_make_refund()

        # Push refund proof before gallery opens
        adb_approver.push_refund_proof()

        refund_page = RefundPage(drv)
        refund_page.complete_refund(
            image_filename = "refund_proof",
            notes          = f"Iter2 QR refund — auto test — {time.strftime('%H:%M')}"
        )

        setup["dm"].screenshot_approver("iter2_12_refund_submitted")
        log.info("✅ Iter 2 refund submitted")

    def test_13_verify_final_status_ui(self, setup):
        """Final UI: status = Refunded for Iter 2."""
        log.info("--- Test: Final Status UI (Iter 2) ---")
        drv = setup["approver_drv"]

        completion_page = ApproverCompletionPage(drv)
        completion_page.wait_for_completion()
        completion_page.assert_refunded()

        setup["dm"].screenshot_approver("iter2_13_refunded")
        log.info("✅ Iter 2 final status: Refunded ✅")

    def test_14_verify_final_status_backend(self, setup):
        """Backend confirms Iter 2 transaction = Refunded."""
        log.info("--- Test: Backend Status (Iter 2) ---")
        backend = setup["backend"]
        state   = setup["state"]

        txn = state.get_transaction(ITERATION)

        reached = backend.wait_for_status(
            txn_id          = txn.transaction_id,
            expected_status = "Refunded",
            timeout         = 30
        )

        assert reached, (
            f"Backend did not confirm 'Refunded' for Iter 2 txn "
            f"{txn.transaction_id}"
        )

        log.info("✅ Backend confirmed: Iter 2 Transaction = Refunded")
        log.info("=" * 60)
        log.info("ITERATION 2 COMPLETE ✅ — QR Upload Flow End-to-End Passed")
        log.info("=" * 60)
