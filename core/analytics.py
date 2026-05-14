from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANALYTICS_DIR = ROOT / "analytics"
ANALYTICS_PATH = ANALYTICS_DIR / "analytics.json"
EVENT_LOG_LIMIT = 200

WORKFLOW_QUALITY_KEYS = {
    "music": "music_workflow_usage",
    "music_mv": "music_workflow_usage",
    "song": "music_workflow_usage",
    "seller": "seller_workflow_usage",
    "podcast": "podcast_workflow_usage",
    "clips": "viral_clips_workflow_usage",
    "viral_clips": "viral_clips_workflow_usage",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _root(base_dir: str | Path | None = None) -> Path:
    return Path(base_dir) if base_dir else ROOT


def analytics_path(base_dir: str | Path | None = None) -> Path:
    return _root(base_dir) / "analytics" / "analytics.json"


def _default_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at": _now(),
        "updated_at": _now(),
        "workflow_usage": {},
        "generate_count": 0,
        "export_count": 0,
        "render_job_count": 0,
        "active_provider_usage": {},
        "preset_bundle_usage": {},
        "quality_tracking": {
            "music_workflow_usage": 0,
            "seller_workflow_usage": 0,
            "podcast_workflow_usage": 0,
            "viral_clips_workflow_usage": 0,
            "mv_storyboard_generation_count": 0,
            "render_package_generation_count": 0,
        },
        "events": [],
    }


def _safe_key(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    return text or fallback


def _increment(mapping: dict[str, Any], key: str, amount: int = 1) -> None:
    mapping[key] = int(mapping.get(key, 0) or 0) + amount


def load_beta_analytics(base_dir: str | Path | None = None) -> dict[str, Any]:
    path = analytics_path(base_dir)
    if not path.is_file():
        return _default_payload()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        payload = _default_payload()
        payload.update(loaded if isinstance(loaded, dict) else {})
        payload.setdefault("workflow_usage", {})
        payload.setdefault("active_provider_usage", {})
        payload.setdefault("preset_bundle_usage", {})
        payload.setdefault("events", [])
        quality = _default_payload()["quality_tracking"]
        quality.update(payload.get("quality_tracking") or {})
        payload["quality_tracking"] = quality
        return payload
    except Exception:
        return _default_payload()


def save_beta_analytics(data: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, Any]:
    path = analytics_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Beta analytics saved", "data": {"path": str(path)}, "error": ""}


def log_beta_event(
    event_type: str,
    *,
    workflow: str = "",
    provider: str = "",
    preset_bundle: str = "",
    metadata: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Log aggregate closed-beta usage without personal data or raw prompts."""
    try:
        payload = load_beta_analytics(base_dir)
        event_type = _safe_key(event_type, "event")
        workflow_key = _safe_key(workflow, "")
        provider_key = _safe_key(provider, "")
        bundle_key = _safe_key(preset_bundle, "")

        if workflow_key:
            _increment(payload["workflow_usage"], workflow_key)
            quality_key = WORKFLOW_QUALITY_KEYS.get(workflow_key)
            if quality_key:
                _increment(payload["quality_tracking"], quality_key)
        if provider_key:
            _increment(payload["active_provider_usage"], provider_key)
        if bundle_key:
            _increment(payload["preset_bundle_usage"], bundle_key)

        if event_type in {"generate", "generation", "workflow_generate"}:
            payload["generate_count"] = int(payload.get("generate_count", 0) or 0) + 1
        elif event_type in {"export", "workflow_export"}:
            payload["export_count"] = int(payload.get("export_count", 0) or 0) + 1
        elif event_type in {"render_job", "render_job_sent"}:
            payload["render_job_count"] = int(payload.get("render_job_count", 0) or 0) + 1
        elif event_type == "mv_storyboard_generated":
            _increment(payload["quality_tracking"], "mv_storyboard_generation_count")
            payload["generate_count"] = int(payload.get("generate_count", 0) or 0) + 1
        elif event_type == "render_package_generated":
            _increment(payload["quality_tracking"], "render_package_generation_count")
            payload["export_count"] = int(payload.get("export_count", 0) or 0) + 1

        safe_metadata = {
            str(key): value
            for key, value in (metadata or {}).items()
            if key in {"status", "workflow_mode", "page", "format", "ok", "provider_mode"}
        }
        payload["events"] = (payload.get("events") or [])[-EVENT_LOG_LIMIT + 1 :] + [
            {
                "timestamp": _now(),
                "event_type": event_type,
                "workflow": workflow_key,
                "provider": provider_key,
                "preset_bundle": bundle_key,
                "metadata": safe_metadata,
            }
        ]
        return save_beta_analytics(payload, base_dir)
    except Exception as exc:
        return {"ok": False, "message": "Beta analytics log failed", "data": {}, "error": str(exc)}


def ensure_beta_runtime_dirs(base_dir: str | Path | None = None) -> dict[str, Any]:
    try:
        root = _root(base_dir)
        dirs = [
            root / "analytics",
            root / "outputs" / "temp",
            root / "outputs" / "logs",
            root / "outputs" / "exports",
            root / "outputs" / "beta_packages",
        ]
        for path in dirs:
            path.mkdir(parents=True, exist_ok=True)
        path = analytics_path(base_dir)
        if not path.is_file():
            save_beta_analytics(_default_payload(), base_dir)
        return {"ok": True, "message": "Closed beta runtime folders ready", "data": {"dirs": [str(path) for path in dirs]}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Closed beta runtime prep failed", "data": {}, "error": str(exc)}


def cleanup_old_temp_exports(
    *,
    ttl_hours: int = 48,
    base_dir: str | Path | None = None,
    roots: list[str | Path] | None = None,
) -> dict[str, Any]:
    try:
        root = _root(base_dir)
        cutoff = time.time() - max(1, int(ttl_hours)) * 3600
        targets = [Path(path) for path in roots] if roots else [root / "outputs" / "temp"]
        removed: list[str] = []
        for target in targets:
            if not target.exists():
                continue
            try:
                target_resolved = target.resolve()
                root_resolved = root.resolve()
                if os.path.commonpath([str(target_resolved), str(root_resolved)]) != str(root_resolved):
                    continue
            except Exception:
                continue
            for path in sorted(target.rglob("*"), key=lambda item: len(item.parts), reverse=True):
                if not path.exists():
                    continue
                try:
                    if path.stat().st_mtime > cutoff:
                        continue
                    if path.is_file():
                        path.unlink()
                        removed.append(str(path))
                    elif path.is_dir() and not any(path.iterdir()):
                        shutil.rmtree(path)
                        removed.append(str(path))
                except Exception:
                    continue
        return {"ok": True, "message": "Old temp exports cleaned", "data": {"removed": removed}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Temp cleanup failed", "data": {"removed": []}, "error": str(exc)}
