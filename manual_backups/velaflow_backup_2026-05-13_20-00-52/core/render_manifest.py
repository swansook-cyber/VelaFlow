import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name
from core.version import identity_payload
from core.export_policy import load_export_policy


ROOT = Path(__file__).resolve().parents[1]


def new_render_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:8]}"


def render_folder(project_name: str, render_id: str, base_dir: str | Path | None = None) -> Path:
    base = Path(base_dir) if base_dir else ROOT / "outputs" / "renders"
    folder = base / safe_name(project_name) / render_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "temp").mkdir(exist_ok=True)
    (folder / "cache").mkdir(exist_ok=True)
    return folder


def create_manifest(
    project: Dict[str, Any],
    render_id: str,
    selected_aspect_ratios: List[str],
    audio_path: str = "",
    subtitle_mode: str = "simple",
    transition_mode: str = "none",
    motion_style: str = "auto",
) -> Dict[str, Any]:
    assets = project.get("assets", {}) or {}
    return {
        **identity_payload(),
        "project_name": project.get("title", "project"),
        "render_id": render_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "selected_aspect_ratios": selected_aspect_ratios,
        "audio_source_path": audio_path or assets.get("audio_path", ""),
        "storyboard_version": project.get("version", "V6"),
        "approved_image_versions": assets.get("approved_images", {}),
        "video_slots_used": assets.get("videos", {}),
        "subtitle_mode": subtitle_mode,
        "transition_mode": transition_mode,
        "motion_style": motion_style,
        "render_status": "CREATED",
        "ffmpeg_command_history": [],
        "outputs": {},
        "errors": [],
        "export_policy": load_export_policy(),
    }


def save_manifest(manifest: Dict[str, Any], render_dir: str | Path) -> Path:
    path = Path(render_dir) / "render_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def update_manifest(render_dir: str | Path, **updates: Any) -> Dict[str, Any]:
    path = Path(render_dir) / "render_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for key, value in updates.items():
        if key == "ffmpeg_command_history":
            manifest.setdefault(key, []).extend(value if isinstance(value, list) else [value])
        elif key == "errors":
            manifest.setdefault(key, []).extend(value if isinstance(value, list) else [value])
        else:
            manifest[key] = value
    save_manifest(manifest, render_dir)
    return manifest


def write_assets_used(render_dir: str | Path, timeline: List[Dict[str, Any]], project: Dict[str, Any]) -> Path:
    assets = {
        **identity_payload(),
        "project": project.get("title", ""),
        "audio_path": (project.get("assets", {}) or {}).get("audio_path", ""),
        "timeline_sources": [
            {
                "scene_id": item.get("scene_id"),
                "source_type": item.get("source_type"),
                "source_path": item.get("source_path"),
                "duration_seconds": item.get("duration_seconds"),
            }
            for item in timeline
        ],
    }
    path = Path(render_dir) / "assets_used.json"
    path.write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
