from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from core.licensing import LicenseService


ROOT = Path(__file__).resolve().parents[1]
EXPORT_CONFIG_PATH = ROOT / "config" / "export.json"


DEFAULT_EXPORT_POLICY = {
    "watermark_enabled": True,
    "watermark_text": "VelaFlow",
    "export_without_watermark": False,
}


def load_export_policy(license_service: LicenseService | None = None, path: str | Path | None = None) -> Dict[str, Any]:
    source = Path(path) if path else EXPORT_CONFIG_PATH
    policy = DEFAULT_EXPORT_POLICY.copy()
    if source.exists():
        try:
            policy.update(json.loads(source.read_text(encoding="utf-8")))
        except Exception:
            pass
    service = license_service or LicenseService()
    policy["export_without_watermark"] = bool(service.is_enabled("export_without_watermark") and policy.get("export_without_watermark", False))
    policy["watermark_enabled"] = bool(policy.get("watermark_enabled", True) and not policy["export_without_watermark"])
    return policy
