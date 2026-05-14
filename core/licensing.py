from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from core.feature_flags import DEFAULT_FEATURE_FLAGS, PACKAGE_FLAGS


ROOT = Path(__file__).resolve().parents[1]
LICENSE_CONFIG_PATH = ROOT / "config" / "license.json"


@dataclass(frozen=True)
class LicenseState:
    package: str
    flags: Dict[str, bool]
    expires_at: str = "2099-12-31"
    source: str = "default"


class LicenseService:
    """Local mock license service for future modular packaging.

    This intentionally does not implement auth, payment, online activation, or
    server checks. All module access should go through this service so future
    licensing can be centralized.
    """

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else LICENSE_CONFIG_PATH
        self.state = self._load_state()

    def _load_state(self) -> LicenseState:
        package = os.getenv("VELAFLOW_LICENSE_PACKAGE", "Studio")
        expires_at = os.getenv("VELAFLOW_LICENSE_EXPIRES_AT", "2027-05-09")
        overrides: Dict[str, bool] = {}
        source = "environment/default"
        if self.config_path.exists():
            try:
                payload = json.loads(self.config_path.read_text(encoding="utf-8"))
                package = str(payload.get("package", package) or package)
                expires_at = str(payload.get("expires_at", expires_at) or expires_at)
                raw_flags = payload.get("feature_flags", {}) or {}
                overrides = {str(key): bool(value) for key, value in raw_flags.items()}
                source = str(self.config_path)
            except Exception:
                source = f"{self.config_path} (invalid, using default)"
        base = PACKAGE_FLAGS.get(package, DEFAULT_FEATURE_FLAGS).copy()
        base.update(overrides)
        return LicenseState(package=package, flags=base, expires_at=expires_at, source=source)

    def is_enabled(self, feature: str) -> bool:
        return bool(self.state.flags.get(feature, False))

    def require(self, feature: str) -> bool:
        return self.is_enabled(feature)

    def module_enabled(self, module_name: str) -> bool:
        key = f"{module_name.lower()}_enabled"
        return self.is_enabled(key)

    def visible_pages(self, page_module_map: Dict[str, str]) -> list[str]:
        return [page for page, module in page_module_map.items() if self.module_enabled(module)]

    def as_dict(self) -> Dict[str, object]:
        return {"package": self.state.package, "expires_at": self.state.expires_at, "source": self.state.source, "feature_flags": self.state.flags}


def get_license_service() -> LicenseService:
    return LicenseService()
