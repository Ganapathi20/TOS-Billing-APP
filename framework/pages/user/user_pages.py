"""
User Page Objects — Towers Online Services (TOS)
=================================================
Covers every screen the User role interacts with:

  1. LoginPage        — mobile number + OTP
  2. PaymentFormPage  — name, mobile, amount, UPI ID input, QR upload
  3. ChargesPage      — calculated charges and final receipt view
  4. PaymentPage      — mock payment gateway / sandbox confirmation
  5. ProofUploadPage  — upload payment screenshot as proof
  6. ConfirmationPage — final submission + status display

UPI INPUT — This implementation adds a dedicated UPI ID text field
(payment_method = "upi_id") alongside the existing QR upload option
(payment_method = "qr_code"). The form has a toggle/tab that switches
between the two modes.
"""

import time
import logging
from appium.webdriver.common.appiumby import AppiumBy
from framework.pages.base_page import BasePage

log = logging.getLogger(__name__)


# ── Page 1: Login ─────────────────────────────────────────────
class UserLoginPage(BasePage):
    """
    Screen: Mobile OTP Login (User role)

    Elements:
      - et_mobile     : mobile number input field
      - btn_send_otp  : 'Send OTP' button
      - et_otp        : OTP input field (appears after send)
      - btn_verify    : 'Verify OTP' / 'Login' button
    """

    ID_MOBILE     = "et_mobile"
    ID_SEND_OTP   = "btn_send_otp"
    ID_OTP        = "et_otp"
    ID_VERIFY     = "btn_verify_otp"

    def enter_mobile(self, mobile: str):
        log.info("[User Login] Entering mobile: %s", mobile)
        self.type_into_id(self.ID_MOBILE, mobile)

    def tap_send_otp(self):
        log.info("[User Login] Tapping Send OTP")
        self.tap_by_id(self.ID_SEND_OTP)
        # Wait for OTP field to appear
        self.find_by_id(self.ID_OTP)

    def enter_otp(self, otp: str):
        log.info("[User Login] Entering OTP: %s", otp)
        self.type_into_id(self.ID_OTP, otp)

    def tap_verify(self):
        log.info("[User Login] Tapping Verify")
        self.tap_by_id(self.ID_VERIFY)

    def login(self, mobile: str, otp: str):
        """Complete login in one call."""
        self.enter_mobile(mobile)
        self.tap_send_otp()
        self.enter_otp(otp)
        self.tap_verify()
        log.info("[User Login] Login submitted for mobile: %s", mobile)


# ── Page 2: Payment Form ──────────────────────────────────────
class PaymentFormPage(BasePage):
    """
    Screen: Payment Details Entry

    This screen collects:
      - Payee name
      - Mobile number
      - Amount
      - Payment method toggle: UPI ID input  OR  QR Code upload

    ┌─────────────────────────────────┐
    │ Name      [___________________] │
    │ Mobile    [___________________] │
    │ Amount    [___________________] │
    │                                 │
    │ Payment Method:                 │
    │  [UPI ID] [QR Code Upload]      │  ← Tab toggle
    │                                 │
    │ [UPI ID tab active]             │
    │ UPI ID    [___________________] │  ← Direct UPI text input
    │                                 │
    │ [QR Code tab active]            │
    │ [📷 Upload QR / UPI Image]      │  ← Gallery picker trigger
    │                                 │
    │ [NEXT]                          │
    └─────────────────────────────────┘
    """

    ID_NAME         = "et_payee_name"
    ID_MOBILE       = "et_payee_mobile"
    ID_AMOUNT       = "et_amount"
    ID_TAB_UPI      = "tab_upi_id"          # Tab: UPI ID input
    ID_TAB_QR       = "tab_qr_upload"       # Tab: QR image upload
    ID_UPI_INPUT    = "et_upi_id"           # UPI ID text field
    ID_UPI_HINT     = "tv_upi_hint"         # e.g. "Enter UPI ID like name@bank"
    ID_QR_UPLOAD    = "btn_upload_qr"       # Gallery picker button
    ID_QR_PREVIEW   = "iv_qr_preview"       # Thumbnail after upload
    ID_NEXT         = "btn_next"

    # ── Basic fields ──────────────────────────────────────────
    def enter_name(self, name: str):
        log.info("[Payment Form] Name: %s", name)
        self.type_into_id(self.ID_NAME, name)

    def enter_mobile(self, mobile: str):
        log.info("[Payment Form] Mobile: %s", mobile)
        self.type_into_id(self.ID_MOBILE, mobile)

    def enter_amount(self, amount: str):
        log.info("[Payment Form] Amount: %s", amount)
        self.type_into_id(self.ID_AMOUNT, amount)

    # ── Payment method: UPI ID ────────────────────────────────
    def select_upi_id_tab(self):
        """Switch to UPI ID input mode."""
        log.info("[Payment Form] Selecting UPI ID tab")
        self.tap_by_id(self.ID_TAB_UPI)
        # Wait for UPI input field to become visible
        self.find_by_id(self.ID_UPI_INPUT)

    def enter_upi_id(self, upi_id: str):
        """
        Type the UPI ID directly into the text field.
        Example: 'testuser1@upi', 'mobile@okbank'
        """
        log.info("[Payment Form] Entering UPI ID: %s", upi_id)
        self.type_into_id(self.ID_UPI_INPUT, upi_id)

    def get_upi_hint_text(self) -> str:
        """Return the hint/placeholder visible in the UPI field."""
        try:
            return self.find_by_id(self.ID_UPI_HINT).text
        except Exception:
            return ""

    def fill_payment_upi(self, name: str, mobile: str,
                          amount: str, upi_id: str):
        """
        Full form fill using UPI ID payment method.
        Call this for Iteration 1.
        """
        self.enter_name(name)
        self.enter_mobile(mobile)
        self.enter_amount(amount)
        self.select_upi_id_tab()
        self.enter_upi_id(upi_id)
        log.info("[Payment Form] UPI ID form complete — UPI: %s", upi_id)

    # ── Payment method: QR Code Upload ───────────────────────
    def select_qr_tab(self):
        """Switch to QR image upload mode."""
        log.info("[Payment Form] Selecting QR upload tab")
        self.tap_by_id(self.ID_TAB_QR)
        # Wait for upload button to appear
        self.find_by_id(self.ID_QR_UPLOAD)

    def tap_upload_qr(self):
        """Open the Android gallery/file picker for QR image selection."""
        log.info("[Payment Form] Opening gallery for QR upload")
        self.tap_by_id(self.ID_QR_UPLOAD)

    def select_qr_from_gallery(self, image_filename: str = "qr_mock"):
        """
        Trigger gallery picker and select the pushed QR image.
        ADB must have pushed the image BEFORE this is called.
        """
        self.tap_upload_qr()
        self.open_gallery_and_select_image(image_filename)
        # Wait for preview thumbnail to appear (confirms selection)
        self.find_by_id(self.ID_QR_PREVIEW)
        log.info("[Payment Form] QR image selected from gallery")

    def fill_payment_qr(self, name: str, mobile: str,
                         amount: str, image_filename: str = "qr_mock"):
        """
        Full form fill using QR image upload method.
        Call this for Iteration 2.
        """
        self.enter_name(name)
        self.enter_mobile(mobile)
        self.enter_amount(amount)
        self.select_qr_tab()
        self.select_qr_from_gallery(image_filename)
        log.info("[Payment Form] QR form complete")

    # ── Proceed ───────────────────────────────────────────────
    def tap_next(self):
        log.info("[Payment Form] Tapping Next")
        self.tap_by_id(self.ID_NEXT)


# ── Page 3: Charges View ──────────────────────────────────────
class ChargesPage(BasePage):
    """
    Screen: Calculated Charges + Final Receipt Summary

    Shows:
      - Original Amount
      - Service Charges
      - GST on Charges (if applicable)
      - Final Total Amount
      - [PAY NOW] button
    """

    ID_ORIGINAL_AMOUNT = "tv_original_amount"
    ID_SERVICE_CHARGE  = "tv_service_charge"
    ID_GST_CHARGE      = "tv_gst_charge"
    ID_TOTAL_AMOUNT    = "tv_total_amount"
    ID_UPI_DISPLAY     = "tv_upi_display"   # shows UPI ID or 'QR Code' label
    ID_RECEIPT_CARD    = "card_receipt"
    ID_PAY_NOW         = "btn_pay_now"

    def wait_for_charges(self):
        """
        Wait for the charges section to fully load.
        This involves a background API call so we wait with a
        longer timeout than usual.
        """
        timeout = 45  # longer wait for charge computation
        log.info("[Charges] Waiting for charge calculation (up to %ds)...", timeout)
        self.wait_visible(AppiumBy.ID,
                          f"{self._pkg()}:id/{self.ID_TOTAL_AMOUNT}",
                          timeout=timeout)
        log.info("[Charges] Charges loaded")

    def get_original_amount(self) -> str:
        return self._text(self.ID_ORIGINAL_AMOUNT)

    def get_service_charge(self) -> str:
        return self._text(self.ID_SERVICE_CHARGE)

    def get_gst_charge(self) -> str:
        return self._text(self.ID_GST_CHARGE)

    def get_total_amount(self) -> str:
        return self._text(self.ID_TOTAL_AMOUNT)

    def get_upi_display(self) -> str:
        """Returns the UPI ID or 'QR Code' string shown in the receipt."""
        return self._text(self.ID_UPI_DISPLAY)

    def is_receipt_visible(self) -> bool:
        try:
            self.find_by_id(self.ID_RECEIPT_CARD)
            return True
        except Exception:
            return False

    def assert_charges(self, expected_amount: str,
                        expected_total: str = None) -> bool:
        """
        Verify the charges page shows sensible values.
        Original amount must match what was entered on the form.
        """
        original = self.get_original_amount()
        total    = self.get_total_amount()
        amount_ok = expected_amount in original
        log.info("[Charges] Original: %s | Total: %s | Check: %s",
                 original, total, amount_ok)
        return amount_ok

    def tap_pay_now(self):
        log.info("[Charges] Tapping Pay Now")
        self.tap_by_id(self.ID_PAY_NOW)

    def _text(self, res_id: str) -> str:
        try:
            return self.find_by_id(res_id).text
        except Exception:
            return ""

    def _pkg(self) -> str:
        from framework.config.loader import CFG
        return CFG.user_device.app_package


# ── Page 4: Mock Payment Gateway ─────────────────────────────
class MockPaymentPage(BasePage):
    """
    Screen: Simulated/Sandbox Payment Gateway

    In the test build, real UPI apps (GPay, PhonePe) are replaced
    with a mock payment screen that:
      - Shows the payee UPI ID or QR
      - Has a single 'Confirm Payment' button
      - Immediately fires a success callback when tapped

    This screen appears INSTEAD of an actual UPI deep-link.
    """

    ID_MOCK_SCREEN    = "layout_mock_payment"
    ID_UPI_DISPLAY    = "tv_mock_upi_id"
    ID_QR_DISPLAY     = "iv_mock_qr"
    ID_AMOUNT_DISPLAY = "tv_mock_amount"
    ID_CONFIRM        = "btn_mock_confirm_payment"
    ID_CANCEL         = "btn_mock_cancel"

    def wait_for_mock_gateway(self):
        """Wait for the mock payment screen to appear."""
        log.info("[Mock Payment] Waiting for mock gateway screen")
        self.find_by_id(self.ID_MOCK_SCREEN)

    def get_displayed_upi(self) -> str:
        """Read the UPI ID displayed on the mock payment screen."""
        return self.find_by_id(self.ID_UPI_DISPLAY).text

    def get_displayed_amount(self) -> str:
        return self.find_by_id(self.ID_AMOUNT_DISPLAY).text

    def confirm_payment(self):
        """
        Tap 'Confirm Payment' on the mock gateway.
        This triggers the success callback, returning control to TOS app.
        """
        log.info("[Mock Payment] Confirming payment on mock gateway")
        self.tap_by_id(self.ID_CONFIRM)
        time.sleep(1.5)  # allow deep-link return animation

    def assert_upi_id_shown(self, expected_upi: str) -> bool:
        """Verify the mock screen shows the correct UPI ID."""
        shown = self.get_displayed_upi()
        match = expected_upi in shown
        log.info("[Mock Payment] UPI display — expected: %s, shown: %s, match: %s",
                 expected_upi, shown, match)
        return match


# ── Page 5: Proof Upload ──────────────────────────────────────
class ProofUploadPage(BasePage):
    """
    Screen: Upload Payment Proof Screenshot

    After mock payment succeeds, TOS re-opens and asks for
    a screenshot of the payment confirmation as proof.

    Shows:
      - Paid amount summary
      - [Upload Screenshot] button
      - Uploaded image preview
      - [Submit Proof] button
    """

    ID_PAID_AMOUNT   = "tv_paid_amount_summary"
    ID_UPLOAD_BTN    = "btn_upload_payment_proof"
    ID_PROOF_PREVIEW = "iv_proof_preview"
    ID_SUBMIT        = "btn_submit_proof"
    ID_TXN_ID_LABEL  = "tv_transaction_id"

    def wait_for_proof_screen(self):
        log.info("[Proof Upload] Waiting for proof screen")
        self.find_by_id(self.ID_UPLOAD_BTN)

    def get_paid_amount(self) -> str:
        return self.find_by_id(self.ID_PAID_AMOUNT).text

    def get_transaction_id(self) -> str:
        """Read the transaction ID displayed on screen — crucial for Approver."""
        try:
            return self.find_by_id(self.ID_TXN_ID_LABEL).text.strip()
        except Exception:
            return ""

    def tap_upload_proof(self):
        log.info("[Proof Upload] Opening gallery for proof upload")
        self.tap_by_id(self.ID_UPLOAD_BTN)

    def select_proof_from_gallery(self, image_filename: str = "payment_proof"):
        """Select the payment proof screenshot from the gallery."""
        self.tap_upload_proof()
        self.open_gallery_and_select_image(image_filename)
        # Wait for preview thumbnail
        self.find_by_id(self.ID_PROOF_PREVIEW)
        log.info("[Proof Upload] Proof image selected from gallery")

    def tap_submit_proof(self):
        log.info("[Proof Upload] Submitting proof")
        self.tap_by_id(self.ID_SUBMIT)

    def upload_and_submit(self, image_filename: str = "payment_proof"):
        """Full proof upload flow in one call."""
        self.select_proof_from_gallery(image_filename)
        self.tap_submit_proof()


# ── Page 6: User Confirmation ─────────────────────────────────
class UserConfirmationPage(BasePage):
    """
    Screen: Submission Confirmation

    Shows:
      - Success message ("Proof Submitted!")
      - Current status ("Pending Approval")
      - Transaction reference
    """

    ID_SUCCESS_MSG  = "tv_submission_success"
    ID_STATUS_LABEL = "tv_current_status"
    ID_TXN_REF      = "tv_txn_reference"
    ID_DONE_BTN     = "btn_done"

    def wait_for_confirmation(self):
        log.info("[Confirmation] Waiting for confirmation screen")
        self.find_by_id(self.ID_SUCCESS_MSG)

    def get_status(self) -> str:
        return self.find_by_id(self.ID_STATUS_LABEL).text

    def get_txn_reference(self) -> str:
        return self.find_by_id(self.ID_TXN_REF).text

    def is_pending_approval(self) -> bool:
        status = self.get_status()
        return "pending" in status.lower() or "approval" in status.lower()
