from __future__ import annotations

from datetime import date

from core.branding import BRAND_NAME, PROGRAM_NAME


APP_VERSION = "7.8.1b"
BUILD_VERSION = "2026.05.09"
BUILD_DATE = date(2026, 5, 9).isoformat()
GENERATED_BY = PROGRAM_NAME
BUILD_IDENTITY = {
    "generated_by": GENERATED_BY,
    "brand": BRAND_NAME,
    "app_version": APP_VERSION,
    "build_version": BUILD_VERSION,
    "build_date": BUILD_DATE,
}


def build_label() -> str:
    return f"{PROGRAM_NAME} V{APP_VERSION}"


def identity_payload() -> dict[str, str]:
    return dict(BUILD_IDENTITY)
