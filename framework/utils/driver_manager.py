"""
Driver Manager
==============
Creates and tears down Appium WebDriver instances for
User and Approver devices independently.

Each driver maps to its own Appium server (separate ports)
so both devices can be controlled in parallel if needed.
"""

import logging
from typing import Optional
from appium import webdriver
from appium.options import UiAutomator2Options
from selenium.webdriver.support.ui import WebDriverWait
from framework.config.loader import CFG, DeviceCfg

log = logging.getLogger(__name__)


def _build_options(device_cfg: DeviceCfg) -> UiAutomator2Options:
    opts = UiAutomator2Options()
    opts.udid               = device_cfg.udid
    opts.platform_name      = device_cfg.platform
    opts.platform_version   = device_cfg.version
    opts.app_package        = device_cfg.app_package
    opts.app_activity       = device_cfg.app_activity
    opts.automation_name    = device_cfg.automation
    opts.no_reset           = device_cfg.no_reset
    opts.new_command_timeout = device_cfg.new_command_timeout
    opts.unicode_keyboard   = device_cfg.unicode_keyboard
    opts.reset_keyboard     = device_cfg.reset_keyboard
    return opts


class DriverManager:
    """
    Single point of driver lifecycle management.
    Usage:
        dm = DriverManager()
        user_driver     = dm.get_user_driver()
        approver_driver = dm.get_approver_driver()
        dm.quit_all()
    """

    def __init__(self):
        self._user_driver:     Optional[webdriver.Remote] = None
        self._approver_driver: Optional[webdriver.Remote] = None

    # ── User driver ───────────────────────────────────────────
    def get_user_driver(self) -> webdriver.Remote:
        if self._user_driver is None:
            log.info("Starting User Appium driver on %s", CFG.appium.url_user)
            self._user_driver = webdriver.Remote(
                command_executor=CFG.appium.url_user,
                options=_build_options(CFG.user_device),
            )
            self._user_driver.implicitly_wait(CFG.timeouts["implicit_wait"])
            log.info("User driver ready — session: %s", self._user_driver.session_id)
        return self._user_driver

    # ── Approver driver ───────────────────────────────────────
    def get_approver_driver(self) -> webdriver.Remote:
        if self._approver_driver is None:
            log.info("Starting Approver Appium driver on %s", CFG.appium.url_approver)
            self._approver_driver = webdriver.Remote(
                command_executor=CFG.appium.url_approver,
                options=_build_options(CFG.approver_device),
            )
            self._approver_driver.implicitly_wait(CFG.timeouts["implicit_wait"])
            log.info("Approver driver ready — session: %s", self._approver_driver.session_id)
        return self._approver_driver

    # ── Waits ─────────────────────────────────────────────────
    def user_wait(self) -> WebDriverWait:
        return WebDriverWait(self.get_user_driver(),
                             CFG.timeouts["explicit_wait"])

    def approver_wait(self) -> WebDriverWait:
        return WebDriverWait(self.get_approver_driver(),
                             CFG.timeouts["explicit_wait"])

    # ── Screenshots ───────────────────────────────────────────
    def screenshot_user(self, name: str):
        path = f"{CFG.reports['screenshots_dir']}{name}_user.png"
        self._user_driver.get_screenshot_as_file(path)
        log.info("Screenshot saved: %s", path)

    def screenshot_approver(self, name: str):
        path = f"{CFG.reports['screenshots_dir']}{name}_approver.png"
        self._approver_driver.get_screenshot_as_file(path)
        log.info("Screenshot saved: %s", path)

    # ── Cleanup ───────────────────────────────────────────────
    def quit_all(self):
        for name, drv in [("user", self._user_driver),
                           ("approver", self._approver_driver)]:
            if drv:
                try:
                    drv.quit()
                    log.info("%s driver quit successfully", name)
                except Exception as e:
                    log.warning("Error quitting %s driver: %s", name, e)
        self._user_driver     = None
        self._approver_driver = None
