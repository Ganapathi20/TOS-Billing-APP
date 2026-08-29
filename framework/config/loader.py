"""
Config Loader
=============
Loads config.yaml and exposes typed dataclasses so every module
gets strongly-typed configuration objects rather than raw dicts.
"""

import yaml
import os
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent   # tos_automation/
_CFG  = _ROOT / "framework" / "config" / "config.yaml"


@dataclass
class DeviceCfg:
    udid: str
    platform: str
    version: str
    app_package: str
    app_activity: str
    automation: str
    no_reset: bool
    new_command_timeout: int
    unicode_keyboard: bool
    reset_keyboard: bool


@dataclass
class AppiumCfg:
    host: str
    port_user: int
    port_approver: int

    @property
    def url_user(self):     return f"{self.host}:{self.port_user}"
    @property
    def url_approver(self): return f"{self.host}:{self.port_approver}"


@dataclass
class TestData:
    static_otp: str
    user_mobile_iter1: str
    user_mobile_iter2: str
    approver_mobile: str
    payment_amount_iter1: str
    payment_amount_iter2: str
    upi_id_iter1: str
    upi_id_iter2: str
    user_name_iter1: str
    user_name_iter2: str


@dataclass
class ADBCfg:
    qr_image_dest: str
    proof_image_dest: str
    refund_image_dest: str
    qr_image_src: str
    proof_image_src: str
    refund_image_src: str


@dataclass
class Config:
    appium:   AppiumCfg
    user_device:     DeviceCfg
    approver_device: DeviceCfg
    timeouts: dict
    test_data: TestData
    backend:  dict
    adb:      ADBCfg
    ocr:      dict
    reports:  dict


def load_config() -> Config:
    with open(_CFG, "r") as f:
        raw = yaml.safe_load(f)

    return Config(
        appium=AppiumCfg(**raw["appium"]),
        user_device=DeviceCfg(**raw["devices"]["user"]),
        approver_device=DeviceCfg(**raw["devices"]["approver"]),
        timeouts=raw["timeouts"],
        test_data=TestData(**raw["test_data"]),
        backend=raw["backend"],
        adb=ADBCfg(**raw["adb"]),
        ocr=raw["ocr"],
        reports=raw["reports"],
    )


# Singleton — loaded once per process
CFG: Config = load_config()
