from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name
from core.rendering_presets import get_rendering_provider_preset
from core.visual_engine import build_scene_flow
from core.visual_presets import normalize_visual_settings


ROOT = Path(__file__).resolve().parents[1]
RENDER_JOB_PROVIDER_MODES = ["Manual / Mock", "Google Veo Ready", "Kling Ready", "Runway Ready"]
RENDER_JOB_STATUSES = ["Pending", "Rendering", "Completed", "Failed"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _project_dir(project_name: str, base_dir: str | Path | None = None) -> Path:
    root = Path(base_dir) if base_dir else ROOT / "project_data" / "projects"
    return root / safe_name(project_name or "render_project")


def _render_jobs_path(project_name: str, base_dir: str | Path | None = None) -> Path:
    return _project_dir(project_name, base_dir) / "render_jobs.json"


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_json_list(path: Path, items: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def build_render_metadata(project_name: str, workflow_type: str, provider: str, quality: str) -> Dict[str, Any]:
    return {
        "generated_by": "VelaFlow",
        "created_at": _now(),
        "project_name": project_name,
        "workflow_type": workflow_type,
        "provider": provider,
        "quality": quality,
        "status": "Ready",
        "note": "Rendering connector metadata only. No external API call or video rendering was performed.",
    }


def build_render_payload(
    *,
    workflow_type: str,
    project_type: str,
    provider: str,
    aspect_ratio: str,
    duration: str,
    quality: str,
    motion_intensity: str,
    visual_settings: Dict[str, Any] | None = None,
    visual_prompt: str = "",
    thumbnail_prompt: str = "",
    b_roll_ideas: List[str] | None = None,
    scene_structure: List[Dict[str, Any]] | None = None,
    bundle_name: str = "",
) -> Dict[str, Any]:
    visual = normalize_visual_settings(visual_settings)
    provider_preset = get_rendering_provider_preset(provider)
    return {
        "workflow_type": workflow_type,
        "project_type": project_type,
        "provider": provider_preset["provider_name"],
        "provider_preset": provider_preset,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "quality": quality,
        "motion_intensity": motion_intensity,
        "camera_preset": visual["camera_preset"],
        "lighting_preset": visual["lighting_preset"],
        "motion_preset": visual["motion_preset"],
        "visual_mood": visual["visual_mood"],
        "bundle_name": bundle_name,
        "scene_structure": scene_structure or build_scene_flow(workflow_type, visual),
        "visual_prompt": visual_prompt,
        "thumbnail_prompt": thumbnail_prompt,
        "b_roll_ideas": b_roll_ideas or [],
    }


def build_render_queue_item(project_name: str, payload: Dict[str, Any], status: str = "Ready") -> Dict[str, Any]:
    return {
        "queue_id": f"render_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
        "created_at": _now(),
        "project_name": project_name,
        "workflow_type": payload.get("workflow_type", ""),
        "provider": payload.get("provider", ""),
        "aspect_ratio": payload.get("aspect_ratio", ""),
        "duration": payload.get("duration", ""),
        "quality": payload.get("quality", ""),
        "status": status,
        "payload": payload,
    }


def build_render_package(
    project_name: str,
    workflow_type: str,
    content: Dict[str, Any] | List[Dict[str, Any]],
    render_settings: Dict[str, Any] | None = None,
    visual_settings: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    settings = {
        "provider": "Runway",
        "aspect_ratio": "9:16",
        "duration": "5s",
        "quality": "Standard",
        "motion_intensity": "Medium",
        **(render_settings or {}),
    }
    bundle_name = str(settings.get("bundle_name") or "")
    if isinstance(content, list):
        scenes = content
        visual_prompt = "\n".join(str(scene.get("video_prompt") or scene.get("visual_prompt") or "") for scene in scenes[:5])
        thumbnail_prompt = str((scenes[0] if scenes else {}).get("image_prompt") or "")
        b_roll = [str(scene.get("scene_title") or scene.get("scene_visual") or f"Scene {idx + 1}") for idx, scene in enumerate(scenes[:8])]
        scene_structure = [
            {"beat": str(scene.get("scene_title") or f"Scene {idx + 1}"), "scene": scene.get("scene", idx + 1)}
            for idx, scene in enumerate(scenes)
        ]
    else:
        data = dict(content or {})
        scenes = data.get("storyboard", [])
        visual_prompt = str(data.get("ai_video_prompt") or data.get("video_prompt") or data.get("visual_prompt") or "")
        thumbnail_prompt = str(data.get("thumbnail_prompt") or "")
        b_roll = data.get("broll_ideas") or data.get("broll_shot_ideas") or data.get("shorts_extraction_ideas") or data.get("scene_ideas") or []
        scene_structure = ((data.get("visual_engine") or {}).get("scene_flow") or build_scene_flow(workflow_type, visual_settings))
        if scenes and not visual_prompt:
            visual_prompt = "\n".join(str(scene.get("video_prompt") or scene.get("visual_prompt") or "") for scene in scenes[:5])
    payload = build_render_payload(
        workflow_type=workflow_type,
        project_type=workflow_type,
        provider=settings["provider"],
        aspect_ratio=settings["aspect_ratio"],
        duration=settings["duration"],
        quality=settings["quality"],
        motion_intensity=settings["motion_intensity"],
        visual_settings=visual_settings,
        visual_prompt=visual_prompt,
        thumbnail_prompt=thumbnail_prompt,
        b_roll_ideas=list(b_roll or []),
        scene_structure=scene_structure,
        bundle_name=bundle_name,
    )
    return {
        "metadata": build_render_metadata(project_name, workflow_type, str(payload["provider"]), settings["quality"]),
        "render_settings": settings,
        "payload": payload,
        "queue_item": build_render_queue_item(project_name, payload, "Ready"),
    }


def render_package_to_text(package: Dict[str, Any]) -> str:
    payload = package.get("payload", {}) or {}
    metadata = package.get("metadata", {}) or {}
    lines = [
        "VELAFLOW RENDER CONNECTOR PACKAGE",
        "",
        f"Project: {metadata.get('project_name', '')}",
        f"Workflow: {payload.get('workflow_type', '')}",
        f"Provider: {payload.get('provider', '')}",
        f"Preset Bundle: {payload.get('bundle_name', '') or '-'}",
        f"Aspect Ratio: {payload.get('aspect_ratio', '')}",
        f"Duration: {payload.get('duration', '')}",
        f"Quality: {payload.get('quality', '')}",
        f"Motion Intensity: {payload.get('motion_intensity', '')}",
        f"Camera Preset: {payload.get('camera_preset', '')}",
        f"Lighting Preset: {payload.get('lighting_preset', '')}",
        f"Motion Preset: {payload.get('motion_preset', '')}",
        f"Visual Mood: {payload.get('visual_mood', '')}",
        "",
        "VISUAL PROMPT",
        str(payload.get("visual_prompt") or "-"),
        "",
        "THUMBNAIL PROMPT",
        str(payload.get("thumbnail_prompt") or "-"),
        "",
        "B-ROLL IDEAS",
        "\n".join(f"- {item}" for item in payload.get("b_roll_ideas", []) or []) or "-",
        "",
        "SCENE STRUCTURE",
        "\n".join(f"- {item}" for item in payload.get("scene_structure", []) or []) or "-",
        "",
        "NOTE",
        "This is metadata and prompt packaging only. VelaFlow did not render video or call external rendering APIs.",
    ]
    return "\n".join(lines).strip() + "\n"


def export_render_package(project_name: str, package: Dict[str, Any], base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        project_dir = _project_dir(project_name, base_dir)
        export_dir = project_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        json_path = export_dir / "render_package.json"
        txt_path = export_dir / "render_package.txt"
        queue_path = project_dir / "render_queue.json"
        json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        txt_path.write_text(render_package_to_text(package), encoding="utf-8")
        queue: List[Dict[str, Any]] = []
        if queue_path.is_file():
            try:
                loaded = json.loads(queue_path.read_text(encoding="utf-8"))
                queue = loaded if isinstance(loaded, list) else []
            except Exception:
                queue = []
        queue.append(package.get("queue_item", {}))
        queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "message": "Render connector package exported",
            "data": {"json_path": str(json_path), "txt_path": str(txt_path), "queue_path": str(queue_path), "queue_count": len(queue)},
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "Render connector export failed", "data": {}, "error": str(exc)}


def load_render_queue(project_name: str, base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        queue_path = _project_dir(project_name, base_dir) / "render_queue.json"
        if not queue_path.is_file():
            return {"ok": True, "message": "Render queue empty", "data": {"items": [], "path": str(queue_path)}, "error": ""}
        data = json.loads(queue_path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else []
        return {"ok": True, "message": "Render queue loaded", "data": {"items": items, "path": str(queue_path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Render queue load failed", "data": {"items": []}, "error": str(exc)}


def mark_render_queue_item(project_name: str, queue_id: str, status: str = "Exported", base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        loaded = load_render_queue(project_name, base_dir)
        items = loaded.get("data", {}).get("items", [])
        found = False
        for item in items:
            if item.get("queue_id") == queue_id:
                item["status"] = status
                item["updated_at"] = _now()
                found = True
        if not found:
            return {"ok": False, "message": "Queue item not found", "data": {}, "error": "missing_queue_item"}
        queue_path = Path(loaded["data"]["path"])
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        queue_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "Render queue updated", "data": {"items": items, "path": str(queue_path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Render queue update failed", "data": {}, "error": str(exc)}


def build_render_job(
    project_name: str,
    render_package: Dict[str, Any],
    provider_mode: str = "Manual / Mock",
    status: str = "Pending",
) -> Dict[str, Any]:
    payload = render_package.get("payload", {}) or {}
    metadata = render_package.get("metadata", {}) or {}
    provider_mode = provider_mode if provider_mode in RENDER_JOB_PROVIDER_MODES else "Manual / Mock"
    status = status if status in RENDER_JOB_STATUSES else "Pending"
    return {
        "job_id": f"mock_{uuid.uuid4().hex[:12]}",
        "created_at": _now(),
        "updated_at": _now(),
        "project_name": project_name or metadata.get("project_name", ""),
        "provider_mode": provider_mode,
        "render_provider": payload.get("provider", ""),
        "workflow_type": payload.get("workflow_type", metadata.get("workflow_type", "")),
        "aspect_ratio": payload.get("aspect_ratio", ""),
        "duration": payload.get("duration", ""),
        "quality": payload.get("quality", ""),
        "motion_intensity": payload.get("motion_intensity", ""),
        "status": status,
        "external_api_called": False,
        "render_package_path": "",
        "result_path": "",
        "note": "Mock job only. VelaFlow did not call Google Veo, Kling, Runway, or any external render API.",
        "payload": payload,
    }


def send_render_job(
    project_name: str,
    render_package: Dict[str, Any],
    provider_mode: str = "Manual / Mock",
    base_dir: str | Path | None = None,
) -> Dict[str, Any]:
    try:
        jobs_path = _render_jobs_path(project_name, base_dir)
        jobs = _load_json_list(jobs_path)
        job = build_render_job(project_name, render_package, provider_mode, "Pending")
        export_path = _project_dir(project_name, base_dir) / "exports" / "render_package.json"
        if export_path.is_file():
            job["render_package_path"] = str(export_path)
        jobs.append(job)
        _write_json_list(jobs_path, jobs)
        return {"ok": True, "message": "Render job sent in mock mode", "data": {"job": job, "path": str(jobs_path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Send render job failed", "data": {}, "error": str(exc)}


def load_render_jobs(project_name: str, base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        jobs_path = _render_jobs_path(project_name, base_dir)
        return {"ok": True, "message": "Render jobs loaded", "data": {"items": _load_json_list(jobs_path), "path": str(jobs_path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Render jobs load failed", "data": {"items": []}, "error": str(exc)}


def check_render_job_status(project_name: str, job_id: str, base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        loaded = load_render_jobs(project_name, base_dir)
        jobs = loaded.get("data", {}).get("items", [])
        target: Dict[str, Any] | None = None
        for job in jobs:
            if job.get("job_id") == job_id:
                current = str(job.get("status") or "Pending")
                if current == "Pending":
                    job["status"] = "Rendering"
                elif current == "Rendering":
                    job["status"] = "Completed"
                    result_path = _project_dir(project_name, base_dir) / "exports" / f"{job_id}_mock_result.txt"
                    result_path.parent.mkdir(parents=True, exist_ok=True)
                    result_path.write_text(
                        "VelaFlow mock render result placeholder.\nNo external render API was called.\n",
                        encoding="utf-8",
                    )
                    job["result_path"] = str(result_path)
                job["updated_at"] = _now()
                target = job
                break
        if not target:
            return {"ok": False, "message": "Render job not found", "data": {}, "error": "missing_render_job"}
        _write_json_list(Path(loaded["data"]["path"]), jobs)
        return {"ok": True, "message": "Render job status checked", "data": {"job": target, "items": jobs, "path": loaded["data"]["path"]}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Render job status check failed", "data": {}, "error": str(exc)}
