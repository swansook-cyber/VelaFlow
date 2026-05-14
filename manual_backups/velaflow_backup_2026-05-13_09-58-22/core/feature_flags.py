from __future__ import annotations

from typing import Dict


DEFAULT_FEATURE_FLAGS: Dict[str, bool] = {
    "core_enabled": True,
    "director_enabled": True,
    "motion_enabled": True,
    "render_enabled": True,
    "clips_enabled": True,
    "canvas_enabled": True,
    "marketing_enabled": True,
    "assets_enabled": True,
    "providers_enabled": True,
    "licensing_enabled": True,
    "batch_render_enabled": True,
    "export_without_watermark": True,
    "commercial_use": True,
}


PACKAGE_FLAGS: Dict[str, Dict[str, bool]] = {
    "Free": {
        **DEFAULT_FEATURE_FLAGS,
        "director_enabled": False,
        "motion_enabled": False,
        "render_enabled": False,
        "clips_enabled": False,
        "canvas_enabled": False,
        "marketing_enabled": False,
        "batch_render_enabled": False,
        "export_without_watermark": False,
        "commercial_use": False,
    },
    "Creator": {
        **DEFAULT_FEATURE_FLAGS,
        "render_enabled": False,
        "clips_enabled": False,
        "marketing_enabled": False,
        "batch_render_enabled": False,
        "export_without_watermark": False,
        "commercial_use": True,
    },
    "Studio": DEFAULT_FEATURE_FLAGS.copy(),
    "Enterprise": DEFAULT_FEATURE_FLAGS.copy(),
}
