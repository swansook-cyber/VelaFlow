import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import streamlit

from core.ffmpeg_utils import configure_moviepy_ffmpeg, ffmpeg_version
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


def run_healthcheck(settings: Any | None = None, runtime_api_keys: Dict[str, str] | None = None, active_provider: str | None = None, api_mode: str | None = None) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, message: str, level: str = "INFO") -> None:
        checks.append({"name": name, "ok": bool(ok), "message": message, "level": level if ok else level})

    add("Python", sys.version_info >= (3, 10), sys.version.split()[0])
    add("Streamlit", True, getattr(streamlit, "__version__", "installed"))
    velaflow_mode = getattr(settings, "velaflow_mode", "LOCAL") if settings else "LOCAL"
    add("VelaFlow mode", True, str(velaflow_mode or "LOCAL"))
    ffmpeg_path = getattr(settings, "ffmpeg_path", "ffmpeg") if settings else "ffmpeg"
    ffmpeg_info = ffmpeg_version(ffmpeg_path)
    moviepy_info = configure_moviepy_ffmpeg(ffmpeg_path)
    add("FFmpeg installed", bool(ffmpeg_info.get("ok")), ffmpeg_info.get("version") or ffmpeg_info.get("error", "not found"), "WARN")
    add("FFmpeg executable path", bool(ffmpeg_info.get("path")), str(ffmpeg_info.get("path") or "not found"), "WARN")
    add("FFmpeg version", bool(ffmpeg_info.get("version")), str(ffmpeg_info.get("version") or "not available"), "WARN")
    add("MoviePy FFmpeg access", bool(moviepy_info.get("ok")), str(moviepy_info.get("path") or moviepy_info.get("error") or "not configured"), "WARN")
    runtime_keys = runtime_api_keys or {}
    gemini_key = str(runtime_keys.get("gemini", "") or (getattr(settings, "gemini_api_key", "") if settings else ""))
    openai_key = str(runtime_keys.get("openai", "") or (getattr(settings, "openai_api_key", "") if settings else ""))
    xai_key = str(runtime_keys.get("xai", "") or (getattr(settings, "xai_api_key", "") if settings else ""))
    selected_provider = active_provider or (getattr(settings, "default_ai_provider", "gemini") if settings else "gemini")
    add("Active AI provider", True, str(selected_provider or "gemini"))
    if api_mode:
        add("API mode", True, str(api_mode))
    add("Gemini configured", bool(gemini_key), "runtime/user key present" if runtime_keys.get("gemini") else ("env key present" if gemini_key else "not configured"), "WARN")
    add("OpenAI configured", bool(openai_key), "runtime/user key present" if runtime_keys.get("openai") else ("env key present" if openai_key else "not configured"), "WARN")
    add("xAI Grok configured", bool(xai_key), "runtime/user key present" if runtime_keys.get("xai") else ("env key present" if xai_key else "not configured"), "WARN")
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
