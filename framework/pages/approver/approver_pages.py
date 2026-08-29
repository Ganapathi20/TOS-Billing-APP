"""
Approver Page Objects — Towers Online Services (TOS)
=====================================================
Covers every screen the Approver role interacts with:

  1. ApproverLoginPage     — mobile OTP login
  2. PendingListPage       — list of all pending transactions
  3. TransactionDetailPage — single transaction details + proof viewer
  4. RefundPage            — upload refund screenshot + confirm
  5. CompletionPage        — final status confirmation screen
"""

import logging
import time
from appium.webdriver.common.appiumby import AppiumBy
from framework.pages.base_page import BasePage

log = logging.getLogger(__name__)


# ── Page 1: Approver Login ────────────────────────────────────
class ApproverLoginPage(BasePage):
    """
    Screen: Mobile OTP Login (Approver role)
    Functionally identical to User login but routes to a
    different home screen on successful authentication.
    """

    ID_MOBILE   = "et_mobile"
    ID_SEND_OTP = "btn_send_otp"
    ID_OTP      = "et_otp"
    ID_VERIFY   = "btn_verify_otp"

    def login(self, mobile: str, otp: str):
        log.info("[Approver Login] Logging in as: %s", mobile)
        self.type_into_id(self.ID_MOBILE, mobile)
        self.tap_by_id(self.ID_SEND_OTP)
        self.find_by_id(self.ID_OTP)
        self.type_into_id(self.ID_OTP, otp)
        self.tap_by_id(self.ID_VERIFY)
        log.info("[Approver Login] Submitted")


# ── Page 2: Pending Transactions List ────────────────────────
class PendingListPage(BasePage):
    """
    Screen: Approver home — list of transactions awaiting review.

    Each list item shows:
      - User name
      - Amount
      - Timestamp
      - Status badge

    ┌───────────────────────────────────┐
    │ Pending Transactions              │
    │ ─────────────────────────────────│
    │ [Test User One]  Rs 500  10:23 AM │  ← list item
    │ [Test User Two]  Rs 1200 11:05 AM │
    └───────────────────────────────────┘
    """

    ID_PENDING_LIST   = "rv_pending_transactions"
    ID_SEARCH         = "et_search_txn"
    ID_FILTER_PENDING = "chip_pending"
    TXT_EMPTY         = "No pending transactions"

    # Accessors for list items — uses UiAutomator2 selectors
    def _item_by_txn_id(self, txn_id: str):
        return self.driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().descriptionContains("{txn_id}")'
        )

    def _item_by_user_name(self, name: str):
        return self.driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiScrollable(new UiSelector().resourceId('
            f'"{self._pkg()}:id/{self.ID_PENDING_LIST}"))'
            f'.scrollIntoView(new UiSelector().textContains("{name}"))'
        )

    def wait_for_list(self):
        log.info("[Pending List] Waiting for list screen")
        self.find_by_id(self.ID_PENDING_LIST)

    def get_item_count(self) -> int:
        items = self.find_all(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().resourceIdMatches(".*item_transaction.*")'
        )
        return len(items)

    def open_transaction_by_id(self, txn_id: str):
        """
        Locate and open a specific transaction by its ID.
        Scrolls through the list if needed.
        """
        log.info("[Pending List] Opening transaction: %s", txn_id)
        try:
            self._item_by_txn_id(txn_id).click()
        except Exception:
            # Fallback: search for it
            self.search_transaction(txn_id)
            self._item_by_txn_id(txn_id).click()

    def open_transaction_by_user(self, user_name: str, timestamp: str = None):
        """
        Locate transaction by user name. If timestamp is provided,
        it disambiguates between multiple transactions from same user.
        """
        log.info("[Pending List] Finding transaction for user: %s", user_name)
        try:
            item = self._item_by_user_name(user_name)
            if timestamp:
                # Further verify by checking timestamp in the item text
                item_text = item.text or ""
                if timestamp not in item_text:
                    log.warning("[Pending List] Timestamp mismatch — proceeding anyway")
            item.click()
        except Exception as e:
            log.error("[Pending List] Could not find transaction for %s: %s",
                      user_name, e)
            raise

    def search_transaction(self, query: str):
        """Use the search bar to filter transactions."""
        log.info("[Pending List] Searching: %s", query)
        try:
            self.type_into_id(self.ID_SEARCH, query)
            time.sleep(0.8)
        except Exception:
            log.warning("[Pending List] Search field not available")

    def refresh_list(self):
        """Pull to refresh the pending list."""
        size = self.driver.get_window_size()
        x = size["width"] // 2
        self.driver.swipe(x, int(size["height"] * 0.3),
                          x, int(size["height"] * 0.7), duration=800)
        time.sleep(1.5)
        log.info("[Pending List] Refreshed")

    def _pkg(self) -> str:
        from framework.config.loader import CFG
        return CFG.user_device.app_package


# ── Page 3: Transaction Detail ────────────────────────────────
class TransactionDetailPage(BasePage):
    """
    Screen: Full details of a single transaction.

    Shows:
      - User Name, Mobile
      - Amount, UPI ID / QR image
      - Timestamp
      - Payment Proof image (tap to expand)
      - [Approve & Refund] button
    """

    ID_USER_NAME      = "tv_detail_user_name"
    ID_USER_MOBILE    = "tv_detail_user_mobile"
    ID_AMOUNT         = "tv_detail_amount"
    ID_UPI_OR_QR      = "tv_detail_upi_or_qr"     # shows UPI ID or 'QR Code'
    ID_TIMESTAMP      = "tv_detail_timestamp"
    ID_TXN_ID         = "tv_detail_txn_id"
    ID_PROOF_THUMB    = "iv_proof_thumbnail"        # tappable proof image
    ID_PROOF_FULLVIEW = "iv_proof_full"             # full-screen proof view
    ID_STATUS_BADGE   = "tv_status_badge"
    ID_REFUND_BTN     = "btn_make_refund"
    ID_REJECT_BTN     = "btn_reject_txn"

    def wait_for_detail(self):
        log.info("[Transaction Detail] Waiting for detail screen")
        self.find_by_id(self.ID_USER_NAME)

    def get_user_name(self) -> str:
        return self.find_by_id(self.ID_USER_NAME).text

    def get_amount(self) -> str:
        return self.find_by_id(self.ID_AMOUNT).text

    def get_upi_display(self) -> str:
        """Returns the UPI ID shown (for UPI-mode) or 'QR Code' (for QR-mode)."""
        return self.find_by_id(self.ID_UPI_OR_QR).text

    def get_transaction_id(self) -> str:
        return self.find_by_id(self.ID_TXN_ID).text.strip()

    def get_status(self) -> str:
        return self.find_by_id(self.ID_STATUS_BADGE).text

    def tap_proof_thumbnail(self):
        """Expand the payment proof image to full view."""
        log.info("[Transaction Detail] Opening proof image")
        self.tap_by_id(self.ID_PROOF_THUMB)
        time.sleep(0.5)

    def get_proof_image_path_on_device(self) -> str:
        """
        Return the device-side file path of the displayed proof image.
        Used to pull the image for OCR verification.
        This reads a content-description attribute that TOS sets on the ImageView
        containing the image file URI.
        """
        try:
            proof_view = self.find_by_id(self.ID_PROOF_THUMB)
            uri = proof_view.get_attribute("content-desc") or ""
            # Strip 'file://' prefix if present
            return uri.replace("file://", "")
        except Exception:
            return ""

    def assert_transaction_details(self, user_name: str,
                                    amount: str,
                                    upi_id: str = "") -> bool:
        """
        Verify the displayed transaction details match expected values.
        Returns True if all checks pass.
        """
        checks = {
            "user_name": user_name.lower() in self.get_user_name().lower(),
            "amount":    amount in self.get_amount(),
        }
        if upi_id:
            checks["upi_id"] = upi_id in self.get_upi_display()

        all_ok = all(checks.values())
        log.info("[Transaction Detail] Assertions: %s | pass: %s", checks, all_ok)
        return all_ok

    def tap_make_refund(self):
        log.info("[Transaction Detail] Tapping Make Refund")
        self.tap_by_id(self.ID_REFUND_BTN)


# ── Page 4: Refund Processing ─────────────────────────────────
class RefundPage(BasePage):
    """
    Screen: Approver processes the refund.

    Steps:
      1. Enter refund notes (optional)
      2. Upload refund confirmation screenshot
      3. Confirm refund

    ┌───────────────────────────────────┐
    │ Process Refund                    │
    │ ─────────────────────────────────│
    │ Notes: [_______________________] │
    │ [📷 Upload Refund Proof]          │
    │ [Preview of uploaded image]       │
    │ [CONFIRM REFUND]                  │
    └───────────────────────────────────┘
    """

    ID_NOTES          = "et_refund_notes"
    ID_UPLOAD_REFUND  = "btn_upload_refund_proof"
    ID_REFUND_PREVIEW = "iv_refund_proof_preview"
    ID_CONFIRM_REFUND = "btn_confirm_refund"
    ID_TXN_AMOUNT     = "tv_refund_amount_display"

    def wait_for_refund_screen(self):
        log.info("[Refund] Waiting for refund screen")
        self.find_by_id(self.ID_UPLOAD_REFUND)

    def get_refund_amount(self) -> str:
        return self.find_by_id(self.ID_TXN_AMOUNT).text

    def enter_refund_notes(self, notes: str = "Test refund — automation"):
        log.info("[Refund] Entering notes: %s", notes)
        self.type_into_id(self.ID_NOTES, notes)

    def tap_upload_refund(self):
        log.info("[Refund] Opening gallery for refund proof")
        self.tap_by_id(self.ID_UPLOAD_REFUND)

    def select_refund_proof(self, image_filename: str = "refund_proof"):
        """Select the refund screenshot from the gallery."""
        self.tap_upload_refund()
        self.open_gallery_and_select_image(image_filename)
        self.find_by_id(self.ID_REFUND_PREVIEW)
        log.info("[Refund] Refund proof image selected")

    def tap_confirm_refund(self):
        log.info("[Refund] Confirming refund")
        self.tap_by_id(self.ID_CONFIRM_REFUND)

    def complete_refund(self, image_filename: str = "refund_proof",
                         notes: str = "Test refund — automation"):
        """Full refund flow in one call."""
        self.wait_for_refund_screen()
        self.enter_refund_notes(notes)
        self.select_refund_proof(image_filename)
        self.tap_confirm_refund()


# ── Page 5: Completion ────────────────────────────────────────
class ApproverCompletionPage(BasePage):
    """
    Screen: Final status after refund is processed.

    This is the terminal state. The Approver sees:
      - 'Refund Successful' / 'Transaction Complete' message
      - Updated status badge: 'Refunded'
      - Back button to return to the list
    """

    ID_STATUS_LABEL  = "tv_final_status"
    ID_SUCCESS_MSG   = "tv_refund_success_msg"
    ID_TXN_REF       = "tv_refund_txn_ref"
    ID_BACK_BTN      = "btn_back_to_list"
    STATUS_REFUNDED  = "Refunded"

    def wait_for_completion(self):
        log.info("[Completion] Waiting for completion screen")
        self.find_by_id(self.ID_STATUS_LABEL)

    def get_final_status(self) -> str:
        return self.find_by_id(self.ID_STATUS_LABEL).text

    def is_refunded(self) -> bool:
        status = self.get_final_status()
        refunded = self.STATUS_REFUNDED.lower() in status.lower()
        log.info("[Completion] Final status: '%s' | is_refunded: %s",
                 status, refunded)
        return refunded

    def assert_refunded(self):
        assert self.is_refunded(), (
            f"Expected status 'Refunded' but got: '{self.get_final_status()}'"
        )
        log.info("[Completion] ✅ Status confirmed: Refunded")

    def tap_back(self):
        self.tap_by_id(self.ID_BACK_BTN)
