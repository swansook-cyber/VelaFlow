from __future__ import annotations

PROGRAM_NAME = "VelaFlow"
PROGRAM_SLUG = "velaflow"
BRAND_NAME = "VelaLab"
PRODUCT_TAGLINE = "AI Content Automation Pipeline"
CURRENT_VERSION = "V7.8.5b"

APP_TITLE = f"{PROGRAM_NAME} {CURRENT_VERSION}"
WINDOW_TITLE = f"{PROGRAM_NAME} - {PRODUCT_TAGLINE}"
DEFAULT_ARTIST = BRAND_NAME

LEGACY_PROGRAM_NAMES = [
    "Vela AI Studio",
    "Vela Moon AI Studio",
    "Vela Moon",
    "AI Studio",
    "vela_ai_studio",
    "vela-ai-studio",
]


def branded(text: str) -> str:
    value = text or ""
    replacements = {
        "Vela Moon AI Studio": PROGRAM_NAME,
        "Vela AI Studio": PROGRAM_NAME,
        "Vela Moon": BRAND_NAME,
        "vela_ai_studio": PROGRAM_SLUG,
        "vela-ai-studio": PROGRAM_SLUG,
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value
