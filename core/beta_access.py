from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project_io import safe_name


ROOT = Path(__file__).resolve().parents[1]
BETA_ACCESS_PATH = ROOT / "config" / "beta_access.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def default_beta_access() -> dict[str, Any]:
    joined_at = _now()
    return {
        "beta_status": "active",
        "build_name": "Founding Creator Build",
        "creator_name": "Founding Creator",
        "creator_id": f"founding_{datetime.now().strftime('%Y%m%d')}",
        "joined_at": joined_at,
        "total_renders": 0,
        "last_active": joined_at,
    }


def load_beta_access(path: str | Path | None = None) -> dict[str, Any]:
    access_path = Path(path) if path else BETA_ACCESS_PATH
    payload = default_beta_access()
    loaded = _read_json(access_path, {})
    if isinstance(loaded, dict):
        payload.update({key: value for key, value in loaded.items() if key != "api_key"})
    if not str(payload.get("creator_id", "")).strip():
        payload["creator_id"] = f"founding_{safe_name(payload.get('creator_name') or 'creator').lower()}"
    return payload


def save_beta_access(data: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    try:
        access_path = Path(path) if path else BETA_ACCESS_PATH
        payload = load_beta_access(access_path)
        safe_update = {key: value for key, value in (data or {}).items() if key != "api_key"}
        payload.update(safe_update)
        payload["last_active"] = _now()
        _write_json(access_path, payload)
        return {"ok": True, "message": "Beta access saved", "data": {"path": str(access_path), "profile": payload}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Beta access save failed", "data": {}, "error": str(exc)}


def register_beta_activity(render_count: int = 0, path: str | Path | None = None) -> dict[str, Any]:
    profile = load_beta_access(path)
    profile["total_renders"] = int(profile.get("total_renders", 0) or 0) + max(0, int(render_count or 0))
    return save_beta_access(profile, path)
