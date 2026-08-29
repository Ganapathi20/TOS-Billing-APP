"""
ADB Helper
==========
Handles all Android Debug Bridge operations needed by the test:

  1. Push test images to device storage
  2. Refresh the media scanner so the gallery sees pushed images
  3. Create target directories on device
  4. Capture logcat events for notification verification
  5. Clear app data between runs

Uses subprocess so no extra Python library is needed beyond stdlib.
"""

import subprocess
import logging
import time
import os
from pathlib import Path
from framework.config.loader import CFG

log = logging.getLogger(__name__)


def _run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    """Execute a shell command and return the result."""
    log.debug("ADB CMD: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"ADB command failed: {' '.join(cmd)}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def _adb(udid: str, *args) -> subprocess.CompletedProcess:
    """Run adb command targeting a specific device by UDID."""
    return _run(["adb", "-s", udid, *args])


class ADBHelper:
    """
    Device-specific ADB operations.
    One instance per device (user device vs approver device).
    """

    def __init__(self, udid: str):
        self.udid = udid

    # ── Device setup ──────────────────────────────────────────
    def create_test_directories(self):
        """Create all necessary directories on the device for test assets."""
        dirs = [
            "/sdcard/Pictures/tos_test",
            "/sdcard/Download/tos_test",
        ]
        for d in dirs:
            _adb(self.udid, "shell", "mkdir", "-p", d)
            log.info("[%s] Directory ensured: %s", self.udid, d)

    def clear_app_data(self, package: str = None):
        """Clear TOS app data for a fresh test run."""
        pkg = package or CFG.user_device.app_package
        _adb(self.udid, "shell", "pm", "clear", pkg)
        log.info("[%s] App data cleared for %s", self.udid, pkg)

    # ── Image operations ──────────────────────────────────────
    def push_image(self, local_path: str, remote_path: str) -> bool:
        """
        Push a local image file to the device.
        After pushing, triggers Media Scanner so the gallery can see it.

        Args:
            local_path:  Path on the host machine (relative to project root)
            remote_path: Absolute path on the Android device

        Returns:
            True on success
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(
                f"Mock image not found at: {local_path}. "
                "Please add mock images to the mock_assets/ directory."
            )

        # Push to device
        _adb(self.udid, "push", local_path, remote_path)
        log.info("[%s] Pushed: %s → %s", self.udid, local_path, remote_path)

        # Trigger media scanner so image appears in gallery immediately
        self._refresh_media_scanner(remote_path)
        return True

    def push_qr_image(self) -> str:
        """Push the mock QR code image. Returns the device-side path."""
        self.push_image(CFG.adb.qr_image_src, CFG.adb.qr_image_dest)
        return CFG.adb.qr_image_dest

    def push_payment_proof(self) -> str:
        """Push the mock payment proof screenshot. Returns the device-side path."""
        self.push_image(CFG.adb.proof_image_src, CFG.adb.proof_image_dest)
        return CFG.adb.proof_image_dest

    def push_refund_proof(self) -> str:
        """Push the mock refund confirmation screenshot. Returns the device-side path."""
        self.push_image(CFG.adb.refund_image_src, CFG.adb.refund_image_dest)
        return CFG.adb.refund_image_dest

    def pull_image(self, remote_path: str, local_dest: str) -> str:
        """
        Pull an image from the device back to the host for OCR verification.

        Returns:
            local_dest path where the file was saved
        """
        os.makedirs(os.path.dirname(local_dest), exist_ok=True)
        _adb(self.udid, "pull", remote_path, local_dest)
        log.info("[%s] Pulled: %s → %s", self.udid, remote_path, local_dest)
        return local_dest

    # ── Notification & event capture ──────────────────────────
    def capture_logcat(self, tag: str = "TOS", lines: int = 50) -> str:
        """
        Capture recent logcat output filtered by a tag.
        Used to verify that notifications were sent to the backend.
        """
        result = _adb(self.udid, "logcat", "-d", "-v", "brief",
                      f"-s", tag, check=False)
        output = result.stdout
        # Return only the last N lines for relevance
        return "\n".join(output.splitlines()[-lines:])

    def wait_for_logcat_event(self, keyword: str, timeout: int = 30) -> bool:
        """
        Poll logcat until a specific keyword appears or timeout is reached.
        Used to confirm notification dispatch, transaction updates, etc.
        """
        start = time.time()
        while time.time() - start < timeout:
            log_output = self.capture_logcat()
            if keyword in log_output:
                log.info("[%s] Logcat keyword found: '%s'", self.udid, keyword)
                return True
            time.sleep(2)
        log.warning("[%s] Logcat keyword NOT found within %ds: '%s'",
                    self.udid, timeout, keyword)
        return False

    # ── App state ─────────────────────────────────────────────
    def force_stop_app(self, package: str = None):
        pkg = package or CFG.user_device.app_package
        _adb(self.udid, "shell", "am", "force-stop", pkg)
        log.info("[%s] Force stopped: %s", self.udid, pkg)

    def grant_permissions(self, package: str = None):
        """Grant storage permissions required for image upload."""
        pkg = package or CFG.user_device.app_package
        permissions = [
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.READ_MEDIA_IMAGES",
        ]
        for perm in permissions:
            _adb(self.udid, "shell", "pm", "grant", pkg, perm)
        log.info("[%s] Storage permissions granted", self.udid)

    def get_device_info(self) -> dict:
        """Return basic device information for logging."""
        model  = _adb(self.udid, "shell", "getprop", "ro.product.model")
        os_ver = _adb(self.udid, "shell", "getprop", "ro.build.version.release")
        return {
            "udid":    self.udid,
            "model":   model.stdout.strip(),
            "android": os_ver.stdout.strip(),
        }

    # ── Private helpers ───────────────────────────────────────
    def _refresh_media_scanner(self, remote_path: str):
        """Broadcast the media scanner intent for the pushed file."""
        _adb(
            self.udid, "shell", "am", "broadcast",
            "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
            "-d", f"file://{remote_path}"
        )
        time.sleep(1)  # give scanner a moment to index the file
        log.debug("[%s] Media scanner refreshed for: %s", self.udid, remote_path)
