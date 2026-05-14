import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import streamlit

from core.ffmpeg_utils import ffmpeg_available
from core.project_io import safe_name


ROOT = Path(__file__).resolve().parents[1]


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def run_healthcheck(settings: Any | None = None) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, message: str, level: str = "INFO") -> None:
        checks.append({"name": name, "ok": bool(ok), "message": message, "level": level if ok else level})

    add("Python", sys.version_info >= (3, 10), sys.version.split()[0])
    add("Streamlit", True, getattr(streamlit, "__version__", "installed"))
    ffmpeg_path = getattr(settings, "ffmpeg_path", "ffmpeg") if settings else "ffmpeg"
    add("FFmpeg", ffmpeg_available(ffmpeg_path), f"path={ffmpeg_path}", "WARN")
    gemini_key = getattr(settings, "gemini_api_key", "") if settings else ""
    add("Gemini key", bool(gemini_key), "present" if gemini_key else "missing", "WARN")
    for label, path in [
        ("outputs", ROOT / "outputs"),
        ("project_data", ROOT / "project_data"),
        ("image cache", ROOT / "outputs" / "cache" / "images"),
        ("jobs", ROOT / "outputs" / "jobs"),
        ("renders", ROOT / "outputs" / "renders"),
    ]:
        add(f"Writable {label}", _writable(path), str(path))

    ok = all(item["ok"] for item in checks if item["level"] != "WARN")
    return {"ok": ok, "message": "Healthcheck complete", "data": {"checks": checks}, "error": "" if ok else "One or more checks failed"}


def run_pre_render_healthcheck(project: Dict[str, Any], settings: Any | None = None) -> Dict[str, Any]:
    base = run_healthcheck(settings)
    checks = list(base.get("data", {}).get("checks", []))

    def add(name: str, ok: bool, message: str, level: str = "WARN") -> None:
        checks.append({"name": name, "ok": bool(ok), "message": message, "level": level})

    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    assets = project.get("assets", {}) or {}
    approved = assets.get("approved_images", {}) or {}
    missing_assets = []
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        if not approved.get(scene_id) and not (assets.get("videos", {}) or {}).get(scene_id):
            missing_assets.append(scene_id)
    add("Storyboard ready", bool(storyboard), f"{len(storyboard)} scenes", "ERROR")
    add("Approved assets", not missing_assets and bool(storyboard), f"missing scenes: {', '.join(missing_assets) if missing_assets else 'none'}", "WARN")
    add("Audio path", bool(assets.get("audio_path")), assets.get("audio_path", "missing"), "WARN")
    render_root = ROOT / "outputs" / "renders" / safe_name(project.get("title", "project"))
    add("Render output writable", _writable(render_root), str(render_root), "ERROR")
    ok = all(item["ok"] for item in checks if item.get("level") == "ERROR")
    return {"ok": ok, "message": "Pre-render healthcheck complete", "data": {"checks": checks, "missing_assets": missing_assets}, "error": "" if ok else "Critical pre-render check failed"}


def write_healthcheck_report(path: str | Path, settings: Any | None = None) -> Path:
    result = run_healthcheck(settings)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
