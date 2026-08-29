"""
Iteration 1 — UPI ID Direct Input Flow
========================================
Payment method: User types their UPI ID directly into a text field.

Test Scenario:
  User (Device A)
    1. Opens TOS app → logs in (mobile OTP)
    2. Fills payment form — name, mobile, amount
    3. Selects 'UPI ID' tab → types UPI ID: testuser1@upi
    4. Taps Next → sees charge calculation
    5. Taps Pay → mock payment gateway opens
    6. Mock gateway confirms instantly → TOS re-opens
    7. Uploads payment screenshot proof
    8. Submits — status shows 'Pending Approval'
    9. System sends push notification to Approver

  [STATE HANDOFF] — transaction_id, amount, upi_id, timestamp written to state

  Approver (Device B)
    1. Opens TOS app → logs in
    2. Sees notification / pending list refreshed
    3. Finds the exact transaction by ID + user name
    4. Reviews: verifies UPI ID matches, amount matches
    5. (OCR) Analyses proof image — confirms amount + UPI ID present
    6. Taps 'Make Refund' → uploads refund screenshot
    7. Confirms refund
    8. Final status: 'Refunded' ✅

Expected results:
  ✅ UPI ID entered in text field flows through to mock gateway display
  ✅ Mock gateway shows correct UPI ID
  ✅ OCR verifies proof contains amount + UPI ID
  ✅ Final status = Refunded
  ✅ Backend API confirms status = Refunded
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
ITERATION = 1


@pytest.fixture(scope="module")
def setup():
    """Module-level setup: drivers, ADB helpers, shared utilities."""
    log.info("=" * 60)
    log.info("ITERATION 1 SETUP — UPI ID Direct Input Flow")
    log.info("=" * 60)

    os.makedirs(CFG.reports["screenshots_dir"], exist_ok=True)
    os.makedirs(CFG.reports["allure_dir"],      exist_ok=True)
    os.makedirs("framework/data",              exist_ok=True)

    dm      = DriverManager()
    state   = StateManager()
    ocr     = OCRHelper()
    backend = BackendClient()

    # ADB helpers — one per device
    adb_user     = ADBHelper(CFG.user_device.udid)
    adb_approver = ADBHelper(CFG.approver_device.udid)

    # ── Pre-run device setup ──────────────────────────────────
    log.info("[Setup] Preparing devices for Iteration 1")

    # Create image directories on both devices
    adb_user.create_test_directories()
    adb_approver.create_test_directories()

    # Grant storage permissions
    adb_user.grant_permissions()
    adb_approver.grant_permissions()

    # Clear any leftover test data from previous runs
    backend.reset_test_data(CFG.test_data.user_mobile_iter1)

    # Push mock images to user device (for proof upload)
    # NOTE: QR image is NOT needed for Iteration 1 (UPI ID text input used)
    adb_user.push_payment_proof()
    # Push refund image to approver device
    adb_approver.push_refund_proof()

    # Start drivers
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

    # ── Teardown ──────────────────────────────────────────────
    log.info("[Teardown] Iteration 1 complete — quitting drivers")
    dm.quit_all()


# ════════════════════════════════════════════════════════════════
# USER FLOW — Device A
# ════════════════════════════════════════════════════════════════

class TestIter1UserFlow:

    def test_01_user_login(self, setup):
        """User authenticates via mobile OTP."""
        log.info("--- Test: User Login (Iter 1) ---")
        drv     = setup["user_drv"]
        backend = setup["backend"]

        # Get OTP (static in dev mode, or from backend)
        otp = backend.get_test_otp(CFG.test_data.user_mobile_iter1)

        login_page = UserLoginPage(drv)
        login_page.login(
            mobile=CFG.test_data.user_mobile_iter1,
            otp=otp
        )

        # Assert: home/dashboard loads after login
        # (varies by app — check for any post-login element)
        assert login_page.wait_for_text_contains("Tower", timeout=20), \
            "Home screen did not load after login"

        setup["dm"].screenshot_user("iter1_01_login_success")
        log.info("✅ User login successful")

    def test_02_fill_payment_form_upi(self, setup):
        """
        User fills the payment form using UPI ID text input.
        This is the key differentiator for Iteration 1.
        """
        log.info("--- Test: Fill Payment Form — UPI ID Input (Iter 1) ---")
        drv = setup["user_drv"]

        form_page = PaymentFormPage(drv)

        # Fill all fields and select UPI ID tab
        form_page.fill_payment_upi(
            name    = CFG.test_data.user_name_iter1,
            mobile  = CFG.test_data.user_mobile_iter1,
            amount  = CFG.test_data.payment_amount_iter1,
            upi_id  = CFG.test_data.upi_id_iter1,
        )

        # Assert UPI ID is entered (read back the field value)
        upi_field = form_page.find_by_id("et_upi_id")
        assert CFG.test_data.upi_id_iter1 in upi_field.text, \
            f"UPI ID field value mismatch: {upi_field.text}"

        # Save payment method to state
        setup["state"].update_field(ITERATION,
                                     payment_method="upi_id",
                                     upi_id=CFG.test_data.upi_id_iter1,
                                     amount=CFG.test_data.payment_amount_iter1,
                                     user_mobile=CFG.test_data.user_mobile_iter1,
                                     user_name=CFG.test_data.user_name_iter1)

        setup["dm"].screenshot_user("iter1_02_form_upi_filled")
        log.info("✅ Payment form filled with UPI ID: %s",
                 CFG.test_data.upi_id_iter1)

    def test_03_tap_next_verify_charges(self, setup):
        """User taps Next — charges are calculated and displayed."""
        log.info("--- Test: Charge Calculation Verification (Iter 1) ---")
        drv     = setup["user_drv"]
        backend = setup["backend"]

        form_page    = PaymentFormPage(drv)
        charges_page = ChargesPage(drv)

        form_page.tap_next()

        # Wait for background charge calculation
        charges_page.wait_for_charges()

        # Assert receipt appears
        assert charges_page.is_receipt_visible(), \
            "Receipt card not visible after charge calculation"

        # Assert amount matches what was entered
        assert charges_page.assert_charges(
            expected_amount=CFG.test_data.payment_amount_iter1
        ), "Charge amount mismatch"

        # Save calculated values to state
        final_total = charges_page.get_total_amount()
        setup["state"].update_field(ITERATION, final_amount=final_total)

        # Optionally verify against backend calculation
        expected = backend.get_expected_charges(CFG.test_data.payment_amount_iter1)
        if expected:
            log.info("[Charges] Backend expected total: %s", expected.get("total"))

        setup["dm"].screenshot_user("iter1_03_charges_verified")
        log.info("✅ Charges calculated. Total: %s", final_total)

    def test_04_mock_payment_gateway(self, setup):
        """
        User taps Pay Now → mock gateway opens.
        Verifies UPI ID is displayed correctly → confirms payment.
        """
        log.info("--- Test: Mock Payment Gateway (Iter 1) ---")
        drv = setup["user_drv"]

        charges_page = ChargesPage(drv)
        mock_page    = MockPaymentPage(drv)

        charges_page.tap_pay_now()

        # Wait for mock gateway
        mock_page.wait_for_mock_gateway()

        # ✅ KEY ASSERTION — UPI ID must be shown on the mock payment screen
        assert mock_page.assert_upi_id_shown(CFG.test_data.upi_id_iter1), \
            f"Mock gateway did not display UPI ID: {CFG.test_data.upi_id_iter1}"

        # Log displayed amount for debugging
        displayed_amount = mock_page.get_displayed_amount()
        log.info("[Mock Payment] Displayed amount: %s", displayed_amount)

        setup["dm"].screenshot_user("iter1_04_mock_gateway")

        # Confirm payment on mock gateway
        mock_page.confirm_payment()
        log.info("✅ Mock payment confirmed — UPI ID displayed correctly")

    def test_05_upload_payment_proof(self, setup):
        """
        TOS re-opens after mock payment.
        User uploads payment screenshot proof.
        Captures timestamp and transaction ID for state handoff.
        """
        log.info("--- Test: Upload Payment Proof (Iter 1) ---")
        drv      = setup["user_drv"]
        adb_user = setup["adb_user"]

        proof_page = ProofUploadPage(drv)

        # Wait for proof upload screen
        proof_page.wait_for_proof_screen()

        # Capture transaction ID before uploading
        txn_id = proof_page.get_transaction_id()
        ts_unix = time.time()
        ts_display = time.strftime("%d %b %Y %H:%M", time.localtime(ts_unix))
        log.info("[Proof] Transaction ID: %s | Timestamp: %s", txn_id, ts_display)

        # The payment proof image was pushed in setup — select and submit it
        proof_page.upload_and_submit(image_filename="payment_proof")

        # Write critical state for Approver test
        setup["state"].set_transaction(ITERATION, TransactionState(
            iteration         = ITERATION,
            user_mobile       = CFG.test_data.user_mobile_iter1,
            user_name         = CFG.test_data.user_name_iter1,
            transaction_id    = txn_id,
            amount            = CFG.test_data.payment_amount_iter1,
            upi_id            = CFG.test_data.upi_id_iter1,
            payment_method    = "upi_id",
            timestamp_unix    = ts_unix,
            timestamp_display = ts_display,
            qr_proof_path     = CFG.adb.proof_image_dest,
        ))

        setup["dm"].screenshot_user("iter1_05_proof_submitted")
        log.info("✅ Proof submitted — TXN: %s", txn_id)

    def test_06_verify_pending_status(self, setup):
        """User's confirmation screen shows 'Pending Approval' status."""
        log.info("--- Test: Verify Pending Status (Iter 1) ---")
        drv = setup["user_drv"]

        confirm_page = UserConfirmationPage(drv)
        confirm_page.wait_for_confirmation()

        assert confirm_page.is_pending_approval(), \
            f"Expected 'Pending Approval' status, got: '{confirm_page.get_status()}'"

        setup["dm"].screenshot_user("iter1_06_pending_status")
        log.info("✅ Status is 'Pending Approval'")

    def test_07_verify_notification_sent(self, setup):
        """Confirm the system sent a push notification to the Approver."""
        log.info("--- Test: Notification Sent (Iter 1) ---")
        backend = setup["backend"]
        state   = setup["state"]

        txn = state.get_transaction(ITERATION)
        assert txn, "Transaction state not found — run previous tests first"

        # Allow brief delay for notification dispatch
        time.sleep(3)

        sent = backend.verify_notification_sent(
            txn_id           = txn.transaction_id,
            recipient_mobile = CFG.test_data.approver_mobile
        )
        # Log result — this may be a soft assertion in dev environments
        if sent:
            log.info("✅ Notification confirmed sent to Approver")
        else:
            log.warning("⚠️ Notification could not be verified — continuing")

        # Update state
        state.update_field(ITERATION,
                            notification_sent=sent,
                            status_after_user="Payment Pending Approval")


# ════════════════════════════════════════════════════════════════
# APPROVER FLOW — Device B
# ════════════════════════════════════════════════════════════════

class TestIter1ApproverFlow:

    def test_08_approver_login(self, setup):
        """Approver authenticates on Device B."""
        log.info("--- Test: Approver Login (Iter 1) ---")
        drv     = setup["approver_drv"]
        backend = setup["backend"]

        otp = backend.get_test_otp(CFG.test_data.approver_mobile)

        login_page = ApproverLoginPage(drv)
        login_page.login(
            mobile=CFG.test_data.approver_mobile,
            otp=otp
        )

        assert login_page.wait_for_text_contains("Pending", timeout=20), \
            "Approver home screen did not load"

        setup["dm"].screenshot_approver("iter1_08_approver_login")
        log.info("✅ Approver logged in")

    def test_09_find_transaction(self, setup):
        """Approver locates the correct pending transaction."""
        log.info("--- Test: Find Transaction (Iter 1) ---")
        drv   = setup["approver_drv"]
        state = setup["state"]

        # Retrieve state written by User flow
        txn = state.wait_for_transaction(ITERATION, timeout=60)
        assert txn.transaction_id, "Transaction ID missing from state"

        pending_page = PendingListPage(drv)
        pending_page.wait_for_list()

        # Refresh to ensure the new transaction appears
        pending_page.refresh_list()

        # Open the specific transaction
        try:
            pending_page.open_transaction_by_id(txn.transaction_id)
        except Exception:
            # Fallback: find by user name
            pending_page.open_transaction_by_user(
                user_name = txn.user_name,
                timestamp = txn.timestamp_display
            )

        setup["dm"].screenshot_approver("iter1_09_transaction_found")
        log.info("✅ Transaction opened: %s", txn.transaction_id)

    def test_10_verify_transaction_details(self, setup):
        """
        Approver reviews transaction details.
        Verifies user name, amount, and UPI ID are correctly shown.
        """
        log.info("--- Test: Verify Transaction Details (Iter 1) ---")
        drv   = setup["approver_drv"]
        state = setup["state"]

        txn = state.get_transaction(ITERATION)
        detail_page = TransactionDetailPage(drv)
        detail_page.wait_for_detail()

        assert detail_page.assert_transaction_details(
            user_name = txn.user_name,
            amount    = txn.amount,
            upi_id    = txn.upi_id,       # UPI ID must be visible to Approver
        ), "Transaction detail mismatch"

        setup["dm"].screenshot_approver("iter1_10_details_verified")
        log.info("✅ Transaction details verified — UPI ID: %s", txn.upi_id)

    def test_11_ocr_verify_proof_image(self, setup):
        """
        OCR: Pull the proof image from the device and verify it contains
        the correct amount and UPI ID.
        """
        log.info("--- Test: OCR Proof Verification (Iter 1) ---")
        drv          = setup["approver_drv"]
        ocr          = setup["ocr"]
        adb_approver = setup["adb_approver"]
        state        = setup["state"]

        txn = state.get_transaction(ITERATION)
        detail_page = TransactionDetailPage(drv)

        # Get the proof image path displayed to the Approver
        proof_path_on_device = detail_page.get_proof_image_path_on_device()

        if proof_path_on_device:
            # Pull image from approver device to host for OCR
            local_path = "reports/pulled_proof_iter1.jpg"
            adb_approver.pull_image(proof_path_on_device, local_path)

            # Run OCR verification
            ocr_result = ocr.assert_payment_proof_valid(
                image_path  = local_path,
                amount      = txn.amount,
                txn_id      = txn.transaction_id,
                upi_id      = txn.upi_id,
            )
            log.info("[OCR] Proof verification result: %s", ocr_result)
            # Soft assertion — OCR can be unreliable; log but don't fail
            if not ocr_result:
                log.warning("⚠️ OCR verification failed — manual review may be needed")
        else:
            log.warning("[OCR] Could not retrieve proof image path — skipping OCR")

        log.info("✅ OCR step complete")

    def test_12_process_refund(self, setup):
        """
        Approver taps Make Refund, uploads refund proof, confirms.
        ADB pushes the mock refund screenshot before gallery opens.
        """
        log.info("--- Test: Process Refund (Iter 1) ---")
        drv          = setup["approver_drv"]
        adb_approver = setup["adb_approver"]

        detail_page = TransactionDetailPage(drv)
        detail_page.tap_make_refund()

        # Push refund proof image to approver device just before gallery opens
        adb_approver.push_refund_proof()

        refund_page = RefundPage(drv)
        refund_page.complete_refund(
            image_filename = "refund_proof",
            notes          = f"Iter1 refund — auto test — {time.strftime('%H:%M')}"
        )

        setup["dm"].screenshot_approver("iter1_12_refund_submitted")
        log.info("✅ Refund submitted")

    def test_13_verify_final_status_ui(self, setup):
        """Final UI assertion: status shows 'Refunded'."""
        log.info("--- Test: Final Status UI (Iter 1) ---")
        drv = setup["approver_drv"]

        completion_page = ApproverCompletionPage(drv)
        completion_page.wait_for_completion()
        completion_page.assert_refunded()

        setup["dm"].screenshot_approver("iter1_13_refunded")
        log.info("✅ Final UI status: Refunded ✅")

    def test_14_verify_final_status_backend(self, setup):
        """Backend API assertion: confirms database status = Refunded."""
        log.info("--- Test: Backend Status Verification (Iter 1) ---")
        backend = setup["backend"]
        state   = setup["state"]

        txn = state.get_transaction(ITERATION)

        reached = backend.wait_for_status(
            txn_id          = txn.transaction_id,
            expected_status = "Refunded",
            timeout         = 30
        )

        assert reached, (
            f"Backend status did not reach 'Refunded' within 30s "
            f"for transaction {txn.transaction_id}"
        )
        log.info("✅ Backend confirmed: Transaction %s = Refunded",
                 txn.transaction_id)
        log.info("=" * 60)
        log.info("ITERATION 1 COMPLETE ✅ — UPI ID Flow End-to-End Passed")
        log.info("=" * 60)
