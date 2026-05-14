from __future__ import annotations

import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.asset_manager import format_bytes
from core.project_io import safe_name, save_project_folder
from core.paths import iter_project_folders, resolve_project_folder, workflow_project_root
from core.quality_control import build_quality_checklist, recommend_regenerate_images
from core.scene_scoring import smart_tiktok_recommendations


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = workflow_project_root("music_pipeline")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def list_recent_projects(limit: int = 12, base_dir: str | Path | None = None) -> List[Dict[str, Any]]:
    projects: List[Dict[str, Any]] = []
    project_files = Path(base_dir).glob("*/project.json") if base_dir else (folder / "project.json" for folder in iter_project_folders())
    for project_path in project_files:
        if not project_path.is_file():
            continue
        project = _load_json(project_path, {})
        modified = project_path.stat().st_mtime
        projects.append(
            {
                "title": project.get("title") or project_path.parent.name,
                "artist": project.get("artist", ""),
                "path": str(project_path),
                "folder": str(project_path.parent),
                "modified_at": datetime.fromtimestamp(modified).isoformat(timespec="seconds"),
                "modified_ts": modified,
                "stage": build_project_status(project).get("next_step", {}).get("stage", "Unknown"),
            }
        )
    return sorted(projects, key=lambda item: item["modified_ts"], reverse=True)[: max(1, int(limit or 12))]


def load_project_file(path: str | Path) -> Dict[str, Any]:
    source = Path(path)
    project = _load_json(source, {})
    if project:
        project.setdefault("loaded_from", str(source))
    return project


def _latest_render_exists(project: Dict[str, Any]) -> bool:
    render_root = ROOT / "outputs" / "renders" / safe_name(project.get("title", "project"))
    return bool(render_root.exists() and any(path.is_dir() for path in render_root.iterdir()))


def build_project_status(project: Dict[str, Any]) -> Dict[str, Any]:
    song = project.get("song", {}) or {}
    mv = project.get("mv", {}) or {}
    assets = project.get("assets", {}) or {}
    storyboard = mv.get("storyboard", []) or []
    scene_count = len(storyboard)
    approved_images = assets.get("approved_images", {}) or {}
    image_versions = assets.get("image_versions", {}) or {}
    renders_ready = _latest_render_exists(project)

    song_ready = bool(song.get("complete_lyrics") or song.get("music_style_prompt") or song.get("selected_hook"))
    storyboard_ready = scene_count > 0
    image_count = len([path for path in approved_images.values() if path])
    generated_count = sum(len(items or []) for items in image_versions.values()) if isinstance(image_versions, dict) else 0
    images_ready = scene_count > 0 and image_count >= scene_count
    review_ready = images_ready and bool(assets.get("hero_shot") or approved_images)
    render_ready = renders_ready

    stages = [
        {"name": "Song", "ok": song_ready, "detail": "lyrics/style ready" if song_ready else "needs song or lyrics"},
        {"name": "Storyboard", "ok": storyboard_ready, "detail": f"{scene_count} scenes" if storyboard_ready else "needs MV Director storyboard"},
        {"name": "Images", "ok": images_ready, "detail": f"{image_count}/{scene_count} approved"},
        {"name": "Review", "ok": review_ready, "detail": "approved visuals ready" if review_ready else "needs image review approval"},
        {"name": "Render", "ok": render_ready, "detail": "render exists" if render_ready else "needs draft/full render"},
    ]
    missing = [stage["name"] for stage in stages if not stage["ok"]]
    next_step = determine_next_step(project, stages)
    return {
        "ok": len(missing) == 0,
        "message": "Project status complete" if not missing else f"Missing: {', '.join(missing)}",
        "data": {
            "title": project.get("title", "project"),
            "scene_count": scene_count,
            "approved_images": image_count,
            "generated_image_versions": generated_count,
            "stages": stages,
            "missing": missing,
        },
        "next_step": next_step,
        "error": "",
    }


def determine_next_step(project: Dict[str, Any], stages: List[Dict[str, Any]] | None = None) -> Dict[str, str]:
    stages = stages or build_project_status(project).get("data", {}).get("stages", [])
    stage_map = {stage["name"]: stage for stage in stages}
    if not stage_map.get("Song", {}).get("ok"):
        return {"stage": "Song", "page": "🎼 Song Studio", "label": "Create song / lyrics"}
    if not stage_map.get("Storyboard", {}).get("ok"):
        return {"stage": "Storyboard", "page": "🎬 MV Director", "label": "Generate storyboard"}
    if not stage_map.get("Images", {}).get("ok"):
        return {"stage": "Images", "page": "Image Lab", "label": "Generate missing images"}
    if not stage_map.get("Review", {}).get("ok"):
        return {"stage": "Review", "page": "Image Review", "label": "Approve images"}
    if not stage_map.get("Render", {}).get("ok"):
        return {"stage": "Render", "page": "🎞️ Render Lab", "label": "Render draft"}
    return {"stage": "Export", "page": "📦 Export Center", "label": "Export package/report"}


def backup_project(project: Dict[str, Any], reason: str = "auto") -> Dict[str, Any]:
    title = safe_name(project.get("title", "project"))
    backup_dir = resolve_project_folder(title, project.get("workflow_type") or project.get("project_type")) / "_auto_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reason_name = safe_name(reason)[:40]
    path = backup_dir / f"project_{stamp}_{reason_name}.json"
    payload = dict(project)
    payload["backup_created_at"] = _now()
    payload["backup_reason"] = reason
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Project backup created", "data": {"path": str(path)}, "error": ""}


def duplicate_project(project: Dict[str, Any], new_title: str, base_dir: str | Path | None = None) -> Dict[str, Any]:
    if not new_title.strip():
        return {"ok": False, "message": "New title is required", "data": {}, "error": "missing_title"}
    duplicate = json.loads(json.dumps(project, ensure_ascii=False))
    duplicate["title"] = new_title.strip()
    duplicate["duplicated_from"] = project.get("title", "")
    duplicate["duplicated_at"] = _now()
    target_root = Path(base_dir) if base_dir else workflow_project_root(duplicate.get("workflow_type") or duplicate.get("project_type"))
    folder = save_project_folder(duplicate, str(target_root))
    return {"ok": True, "message": "Project duplicated", "data": {"folder": str(folder), "project": duplicate}, "error": ""}


def save_project_as(project: Dict[str, Any], new_title: str, base_dir: str | Path | None = None) -> Dict[str, Any]:
    return duplicate_project(project, new_title, base_dir)


def clean_safe_temp_files(project: Dict[str, Any]) -> Dict[str, Any]:
    title = safe_name(project.get("title", "project"))
    roots = [
        ROOT / "outputs" / "renders" / title,
        ROOT / "outputs" / "previews",
    ]
    removed: List[Dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        temp_dirs = [path for path in root.rglob("*") if path.is_dir() and path.name == "temp"]
        tmp_files = [path for path in root.rglob("*.tmp") if path.is_file()]
        for path in temp_dirs:
            if path.exists():
                size = sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
                shutil.rmtree(path)
                removed.append({"path": str(path), "bytes": size, "size": format_bytes(size)})
        for path in tmp_files:
            if path.exists():
                size = path.stat().st_size
                path.unlink()
                removed.append({"path": str(path), "bytes": size, "size": format_bytes(size)})
    return {
        "ok": True,
        "message": f"Removed {len(removed)} safe temp items",
        "data": {"removed": removed, "total_size": format_bytes(sum(item["bytes"] for item in removed))},
        "error": "",
    }


def export_project_report(project: Dict[str, Any], output_dir: str | Path | None = None) -> Dict[str, Any]:
    title = safe_name(project.get("title", "project"))
    output = Path(output_dir) if output_dir else ROOT / "outputs" / "reports" / title
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    status = build_project_status(project)
    quality = build_quality_checklist(project)
    regenerate = recommend_regenerate_images(project)
    tiktok = smart_tiktok_recommendations(project)
    report = {
        "project": project.get("title", "project"),
        "created_at": _now(),
        "status": status,
        "quality": quality,
        "regenerate_images": regenerate,
        "tiktok_recommendations": tiktok,
    }
    json_path = output / f"project_report_{stamp}.json"
    md_path = output / f"project_report_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Vela Project Report: {project.get('title', 'project')}",
        "",
        f"Created: {report['created_at']}",
        "",
        "## Project Status",
    ]
    for stage in status.get("data", {}).get("stages", []):
        mark = "OK" if stage.get("ok") else "MISSING"
        lines.append(f"- {mark} {stage.get('name')}: {stage.get('detail')}")
    next_step = status.get("next_step", {})
    lines += ["", f"Next step: {next_step.get('label', '')} ({next_step.get('page', '')})", "", "## Image Regeneration Recommendations"]
    for item in regenerate.get("data", {}).get("scenes", []) or []:
        lines.append(f"- Scene {item.get('scene_id')}: {', '.join(item.get('reasons', []))}")
    if not regenerate.get("data", {}).get("scenes"):
        lines.append("- No urgent image regeneration recommendations.")
    lines += ["", "## TikTok Candidates"]
    for item in tiktok.get("data", {}).get("recommended_scenes", []) or []:
        lines.append(f"- Scene {item.get('scene_id')}: score {item.get('teaser_score')} | {item.get('notes')}")
    if not tiktok.get("data", {}).get("recommended_scenes"):
        lines.append("- No TikTok candidates yet.")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "message": "Project report exported", "data": {"json": str(json_path), "markdown": str(md_path)}, "error": ""}
