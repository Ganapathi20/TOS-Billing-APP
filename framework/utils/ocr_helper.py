"""
OCR Helper
==========
Uses Tesseract OCR (via pytesseract) to verify image content.

Two main use cases in TOS:
  1. Verify the Payment Proof screenshot contains the expected amount
  2. Verify the Refund screenshot shows the correct transaction reference

Includes OpenCV-based pre-processing to improve OCR accuracy on
mobile screenshots which may have watermarks, colour backgrounds,
or low contrast text.
"""

import logging
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image
from pathlib import Path
from framework.config.loader import CFG

log = logging.getLogger(__name__)
pytesseract.pytesseract.tesseract_cmd = CFG.ocr["tesseract_path"]


class OCRHelper:

    # ── Pre-processing ────────────────────────────────────────
    @staticmethod
    def preprocess(image_path: str) -> np.ndarray:
        """
        Apply OpenCV pre-processing to improve OCR accuracy.
        Pipeline:
            1. Load image
            2. Convert to grayscale
            3. Apply adaptive thresholding (handles uneven lighting)
            4. Denoise
            5. Return processed image array
        """
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"OCR: Image not found at {image_path}")

        gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh  = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        denoised = cv2.fastNlMeansDenoising(thresh, h=10)
        return denoised

    # ── Core extraction ───────────────────────────────────────
    def extract_text(self, image_path: str) -> str:
        """
        Run Tesseract on a pre-processed image and return raw text.
        """
        processed = self.preprocess(image_path)
        pil_img   = Image.fromarray(processed)
        config    = f"--oem 3 --psm 6 -l {CFG.ocr['lang']}"
        text      = pytesseract.image_to_string(pil_img, config=config)
        log.debug("OCR raw text:\n%s", text)
        return text

    def extract_with_confidence(self, image_path: str) -> list[dict]:
        """
        Return per-word OCR data including confidence scores.
        Used to filter out low-confidence detections.
        """
        processed = self.preprocess(image_path)
        pil_img   = Image.fromarray(processed)
        data = pytesseract.image_to_data(
            pil_img, output_type=pytesseract.Output.DICT,
            config=f"--oem 3 --psm 6 -l {CFG.ocr['lang']}"
        )
        threshold = CFG.ocr["confidence_threshold"]
        words = []
        for i, conf in enumerate(data["conf"]):
            try:
                if int(conf) >= threshold:
                    words.append({
                        "text":  data["text"][i],
                        "conf":  int(conf),
                        "left":  data["left"][i],
                        "top":   data["top"][i],
                    })
            except (ValueError, TypeError):
                continue
        return words

    # ── Verification methods ──────────────────────────────────
    def verify_amount(self, image_path: str, expected_amount: str) -> bool:
        """
        Check that a payment/refund screenshot contains the expected amount.
        Handles formats like '500', '500.00', 'Rs 500', '₹500'.
        """
        text = self.extract_text(image_path)
        # Normalise: remove currency symbols and spaces
        normalised = re.sub(r"[₹Rs,\s]", "", text)
        # Look for the expected number
        clean_amount = expected_amount.replace(",", "").strip()
        found = clean_amount in normalised
        log.info("OCR amount check — expected: %s, found: %s, pass: %s",
                 clean_amount, found, found)
        return found

    def verify_transaction_id(self, image_path: str, txn_id: str) -> bool:
        """Confirm the transaction ID appears in the proof screenshot."""
        text = self.extract_text(image_path)
        found = txn_id.upper() in text.upper()
        log.info("OCR txn_id check — expected: %s, pass: %s", txn_id, found)
        return found

    def verify_upi_id(self, image_path: str, upi_id: str) -> bool:
        """Confirm the UPI ID appears in the payment proof."""
        text = self.extract_text(image_path)
        found = upi_id.lower() in text.lower()
        log.info("OCR UPI ID check — expected: %s, pass: %s", upi_id, found)
        return found

    def verify_keywords(self, image_path: str, keywords: list[str]) -> dict[str, bool]:
        """
        Check multiple keywords at once.
        Returns a dict of {keyword: found_bool}.
        """
        text = self.extract_text(image_path).lower()
        results = {}
        for kw in keywords:
            results[kw] = kw.lower() in text
            log.info("OCR keyword '%s': %s", kw, results[kw])
        return results

    def assert_payment_proof_valid(self, image_path: str,
                                    amount: str, txn_id: str,
                                    upi_id: str = "") -> bool:
        """
        Single assertion method for payment proof validation.
        Checks:
          - Amount matches
          - Transaction ID present
          - UPI ID present (if provided)
          - 'Success' or 'Paid' keyword visible

        Returns True if all checks pass.
        """
        checks = {
            "amount":     self.verify_amount(image_path, amount),
            "txn_id":     self.verify_transaction_id(image_path, txn_id),
            "paid_kw":    bool(self.verify_keywords(
                              image_path, ["success", "paid", "successful"]
                          ).get("success") or
                          self.verify_keywords(
                              image_path, ["paid"]
                          ).get("paid")),
        }
        if upi_id:
            checks["upi_id"] = self.verify_upi_id(image_path, upi_id)

        all_pass = all(checks.values())
        log.info("Payment proof validation — results: %s | overall: %s",
                 checks, all_pass)
        return all_pass
