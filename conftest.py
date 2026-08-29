"""
conftest.py — Global PyTest Configuration
==========================================
Runs before any test. Sets up:
  - Logging format
  - Reports directory
  - State manager reset
  - Mock asset validation
"""

import os
import logging
import pytest
from framework.config.loader import CFG
from framework.utils.state_manager import StateManager

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("conftest")


# ── Session-wide setup ────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def session_setup():
    log.info("=" * 60)
    log.info("TOS AUTOMATION FRAMEWORK — SESSION START")
    log.info("=" * 60)

    # Create output directories
    for d in [CFG.reports["output_dir"],
              CFG.reports["screenshots_dir"],
              CFG.reports["allure_dir"],
              "framework/data"]:
        os.makedirs(d, exist_ok=True)

    # Validate mock assets exist
    missing = []
    for path in [CFG.adb.qr_image_src,
                 CFG.adb.proof_image_src,
                 CFG.adb.refund_image_src]:
        if not os.path.exists(path):
            missing.append(path)

    if missing:
        log.warning("⚠️  Mock assets missing: %s", missing)
        log.warning("Create placeholder images in mock_assets/ before running.")
        # Auto-create placeholders for CI/CD environments
        _create_mock_images()

    # Clear state from previous run
    StateManager().clear()
    log.info("State manager cleared — fresh run")

    yield

    log.info("=" * 60)
    log.info("TOS AUTOMATION FRAMEWORK — SESSION END")
    log.info("=" * 60)


def _create_mock_images():
    """
    Create minimal valid JPEG placeholders for mock assets.
    These are not real screenshots but allow the framework
    to run without real device images during CI.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        os.makedirs("mock_assets", exist_ok=True)

        configs = [
            (CFG.adb.qr_image_src,      "MOCK QR CODE",       "white",  "black"),
            (CFG.adb.proof_image_src,    "Payment Successful\nAmount: Rs 500\nUPI: testuser1@upi", "green",  "white"),
            (CFG.adb.refund_image_src,   "Refund Processed\nRef: TXN001",    "blue",   "white"),
        ]

        for path, text, bg, fg in configs:
            if not os.path.exists(path):
                img  = Image.new("RGB", (400, 600), color=bg)
                draw = ImageDraw.Draw(img)
                draw.multiline_text((20, 100), text, fill=fg, spacing=10)
                img.save(path, "JPEG")
                log.info("Created mock image: %s", path)

    except ImportError:
        log.warning("Pillow not installed — mock images not created")


# ── Per-test hooks ────────────────────────────────────────────
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        log.error("FAILED: %s", item.nodeid)
