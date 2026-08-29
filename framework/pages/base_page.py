"""
Base Page
=========
All Page Object classes inherit from BasePage.
Provides:
  - Safe element-finding with explicit waits
  - Tap, type, scroll helpers
  - Gallery picker (image selection from Android gallery)
  - Toast message capture
  - Screen transition wait
"""

import logging
import time
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, NoSuchElementException,
                                         StaleElementReferenceException)
from framework.config.loader import CFG

log = logging.getLogger(__name__)


class BasePage:

    def __init__(self, driver):
        self.driver  = driver
        self.wait    = WebDriverWait(driver, CFG.timeouts["explicit_wait"])
        self.timeout = CFG.timeouts["explicit_wait"]

    # ── Element finders ───────────────────────────────────────
    def find(self, by, value, timeout=None):
        t = timeout or self.timeout
        try:
            return WebDriverWait(self.driver, t).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            self._screenshot_on_failure(f"find_timeout_{value[:20]}")
            raise TimeoutException(
                f"Element not found [{by}='{value}'] within {t}s"
            )

    def find_all(self, by, value):
        return self.driver.find_elements(by, value)

    def find_by_id(self, resource_id):
        full_id = f"{CFG.user_device.app_package}:id/{resource_id}"
        return self.find(AppiumBy.ID, full_id)

    def find_by_text(self, text):
        return self.find(AppiumBy.ANDROID_UIAUTOMATOR,
                         f'new UiSelector().text("{text}")')

    def find_by_content_desc(self, desc):
        return self.find(AppiumBy.ACCESSIBILITY_ID, desc)

    def find_by_xpath(self, xpath):
        return self.find(AppiumBy.XPATH, xpath)

    def wait_visible(self, by, value, timeout=None):
        t = timeout or self.timeout
        return WebDriverWait(self.driver, t).until(
            EC.visibility_of_element_located((by, value))
        )

    def wait_clickable(self, by, value, timeout=None):
        t = timeout or self.timeout
        return WebDriverWait(self.driver, t).until(
            EC.element_to_be_clickable((by, value))
        )

    # ── Interactions ──────────────────────────────────────────
    def tap(self, element):
        try:
            element.click()
        except StaleElementReferenceException:
            log.warning("StaleElement on tap — retrying once")
            time.sleep(0.5)
            element.click()

    def type_text(self, element, text: str, clear_first: bool = True):
        if clear_first:
            element.clear()
        element.send_keys(text)
        log.debug("Typed: '%s'", text)

    def tap_by_id(self, resource_id: str):
        self.tap(self.find_by_id(resource_id))

    def tap_by_text(self, text: str):
        self.tap(self.find_by_text(text))

    def type_into_id(self, resource_id: str, text: str):
        el = self.find_by_id(resource_id)
        self.type_text(el, text)

    def type_into_xpath(self, xpath: str, text: str):
        el = self.find_by_xpath(xpath)
        self.type_text(el, text)

    # ── Wait helpers ──────────────────────────────────────────
    def wait_for_text(self, text: str, timeout: int = 30) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR,
                     f'new UiSelector().text("{text}")')
                )
            )
            return True
        except TimeoutException:
            return False

    def wait_for_text_contains(self, partial_text: str,
                                timeout: int = 30) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (AppiumBy.ANDROID_UIAUTOMATOR,
                     f'new UiSelector().textContains("{partial_text}")')
                )
            )
            return True
        except TimeoutException:
            return False

    def wait_for_screen(self, activity_fragment: str, timeout: int = 15):
        """Wait until the current activity contains the expected string."""
        start = time.time()
        while time.time() - start < timeout:
            current = self.driver.current_activity or ""
            if activity_fragment in current:
                return True
            time.sleep(1)
        return False

    # ── Scroll ────────────────────────────────────────────────
    def scroll_down(self, swipes: int = 1):
        size = self.driver.get_window_size()
        x = size["width"] // 2
        start_y = int(size["height"] * 0.7)
        end_y   = int(size["height"] * 0.3)
        for _ in range(swipes):
            self.driver.swipe(x, start_y, x, end_y, duration=600)

    def scroll_to_text(self, text: str):
        self.driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiScrollable(new UiSelector().scrollable(true))'
            f'.scrollIntoView(new UiSelector().text("{text}"))'
        )

    # ── Toast capture ─────────────────────────────────────────
    def get_toast_message(self, timeout: int = 5) -> str:
        """Capture Android toast message text."""
        try:
            toast = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (AppiumBy.XPATH, "//android.widget.Toast")
                )
            )
            return toast.text
        except TimeoutException:
            return ""

    # ── Android Gallery picker ────────────────────────────────
    def open_gallery_and_select_image(self, image_filename: str):
        """
        Navigate the Android gallery picker to select a specific image.

        Flow:
          1. The app opens the standard Android file/gallery picker
          2. We tap 'Gallery' or 'Photos' in the chooser
          3. We navigate to the Pictures/tos_test album
          4. We tap the image with matching filename/description

        NOTE: Accessibility IDs vary slightly between Android versions.
        This implementation uses UIAutomator2 selectors that work on
        Android 11–14 with the standard Google Photos / Files picker.
        """
        time.sleep(1.5)  # wait for picker animation

        # ── Handle 'Open from' chooser if it appears ─────────
        try:
            # Try 'Gallery' option first
            gallery_btn = self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().textContains("Gallery")'
            )
            gallery_btn.click()
        except NoSuchElementException:
            pass  # picker might open gallery directly

        time.sleep(1)

        # ── Navigate to tos_test album ─────────────────────────
        try:
            # Scroll and find the tos_test folder or DCIM
            self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiScrollable(new UiSelector().scrollable(true))'
                f'.scrollIntoView(new UiSelector().textContains("tos_test"))'
            ).click()
            time.sleep(0.8)
        except Exception:
            log.warning("Could not find tos_test album; selecting first image")

        # ── Select the first/latest image ─────────────────────
        # Try by filename content description
        try:
            img = self.driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().descriptionContains("{image_filename}")'
            )
            img.click()
        except NoSuchElementException:
            # Fallback: tap the first image in the grid
            images = self.driver.find_elements(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().className("android.widget.ImageView")'
            )
            if images:
                images[0].click()
            else:
                raise NoSuchElementException(
                    "No images found in gallery picker. "
                    "Ensure ADB push + media scanner ran before this step."
                )

        time.sleep(0.5)
        log.info("Gallery image selected: %s", image_filename)

    # ── Debug helpers ─────────────────────────────────────────
    def _screenshot_on_failure(self, name: str):
        try:
            path = f"{CFG.reports['screenshots_dir']}failure_{name}.png"
            self.driver.get_screenshot_as_file(path)
        except Exception:
            pass

    def get_element_text(self, by, value) -> str:
        try:
            return self.find(by, value).text
        except Exception:
            return ""
