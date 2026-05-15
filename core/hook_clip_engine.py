from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paths import resolve_project_folder
from core.project_io import safe_name
from core.render_connector import build_render_package, export_render_package
from core.scene_story_engine import build_scene_sequence, build_subtitle_timing
from core.visual_presets import normalize_visual_settings


HOOK_SCORE_KEYS = [
    "emotional_score",
    "catchy_score",
    "tiktok_potential",
    "replay_potential",
    "curiosity_score",
    "cta_strength",
    "relatability_score",
]


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _candidate(text: str, source: str = "", **scores: int) -> dict[str, Any]:
    cleaned = _clean_text(text)
    if not cleaned:
        return {}
    base = {
        "hook_text": cleaned[:120],
        "source": source,
        "emotional_score": scores.get("emotional_score", 70),
        "catchy_score": scores.get("catchy_score", 70),
        "tiktok_potential": scores.get("tiktok_potential", 70),
        "replay_potential": scores.get("replay_potential", 65),
        "curiosity_score": scores.get("curiosity_score", 65),
        "cta_strength": scores.get("cta_strength", 50),
        "relatability_score": scores.get("relatability_score", 70),
    }
    base["scores"] = {
        "emotional": base["emotional_score"],
        "catchy": base["catchy_score"],
        "tiktok": base["tiktok_potential"],
        "replay": base["replay_potential"],
        "curiosity": base["curiosity_score"],
        "cta": base["cta_strength"],
        "relatability": base["relatability_score"],
    }
    base["total_score"] = sum(int(base.get(key, 0) or 0) for key in HOOK_SCORE_KEYS)
    return base


def _split_lines(text: str) -> list[str]:
    lines = []
    for line in re.split(r"[\n.!?]+", text or ""):
        cleaned = _clean_text(re.sub(r"^\[[^\]]+\]", "", line))
        cleaned = re.sub(r"^\([^)]*\)", "", cleaned).strip()
        if 4 <= len(cleaned) <= 120:
            lines.append(cleaned)
    return lines


def extract_best_hook(source_workflow: str, content: dict[str, Any] | list[Any] | str) -> dict[str, Any]:
    workflow = source_workflow or "hook_clip"
    candidates: list[dict[str, Any]] = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                candidates.append(_candidate(item.get("hook_text") or item.get("subtitle") or item.get("caption") or item.get("scene_title"), workflow))
            else:
                candidates.append(_candidate(str(item), workflow))
    elif isinstance(content, dict):
        keys_by_workflow = {
            "music": ["selected_hook_text", "hook_text", "chorus", "normalized_song_output", "complete_lyrics"],
            "music_mv": ["selected_hook_text", "hook_text", "chorus", "normalized_song_output", "complete_lyrics"],
            "seller": ["tiktok_hooks", "compressed_benefits", "caption", "cta_suggestions"],
            "podcast": ["episode_hooks", "emotional_monologue", "viral_rant_version", "tiktok_clip_hooks"],
            "viral_clips": ["viral_hooks", "subtitle_lines", "short_script", "caption"],
        }
        for key in keys_by_workflow.get(workflow, []):
            value = content.get(key)
            if isinstance(value, list):
                for item in value[:8]:
                    candidates.append(_candidate(str(item), workflow))
            elif isinstance(value, str):
                for line in _split_lines(value)[:8]:
                    candidates.append(_candidate(line, workflow))
        selected_hook = content.get("selected_hook")
        if isinstance(selected_hook, dict):
            candidates.append(_candidate(selected_hook.get("hook_text") or selected_hook.get("text"), workflow, emotional_score=90, catchy_score=88, tiktok_potential=86))
    else:
        for line in _split_lines(str(content))[:8]:
            candidates.append(_candidate(line, workflow))
    candidates = [item for item in candidates if item.get("hook_text")]
    if not candidates:
        candidates = [_candidate("หยุดดูคลิปนี้ก่อน มีบางอย่างที่คุณอาจเจอเหมือนกัน", workflow, curiosity_score=82, tiktok_potential=80)]
    return sorted(candidates, key=lambda item: item.get("total_score", 0), reverse=True)[0]


def build_hook_scene(
    source_workflow: str,
    hook: dict[str, Any],
    visual_settings: dict[str, Any] | None = None,
    clip_mode: str = "Fast Hook",
    duration_seconds: int = 8,
    source_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    visual = normalize_visual_settings(visual_settings)
    hook_text = hook.get("hook_text", "")
    scenes = build_scene_sequence(
        workflow_type=source_workflow,
        hook_text=hook_text,
        visual_settings=visual,
        clip_mode=clip_mode,
        duration_seconds=duration_seconds,
        source_context=source_context,
    )
    return {
        "hook_text": hook_text,
        "clip_mode": clip_mode,
        "duration_seconds": max(5, min(10, int(duration_seconds or 8))),
        "visual_settings": visual,
        "scenes": scenes,
        "subtitle_timing": build_subtitle_timing(scenes),
    }


def build_hook_video_prompt(scene_package: dict[str, Any]) -> str:
    scenes = scene_package.get("scenes", []) or []
    lines = [
        "Create a short vertical 9:16 viral hook clip, 5-10 seconds total.",
        f"Hook: {scene_package.get('hook_text', '')}",
        f"Clip mode: {scene_package.get('clip_mode', 'Fast Hook')}",
        "Scene sequence:",
    ]
    for scene in scenes:
        lines.append(
            f"- {scene.get('scene_id')}: {scene.get('visual_prompt')} | camera: {scene.get('camera_direction')} | "
            f"motion: {scene.get('motion')} | subtitle: {scene.get('subtitle')}"
        )
    return "\n".join(lines)


def build_hook_caption(hook: dict[str, Any], source_workflow: str) -> dict[str, Any]:
    text = hook.get("hook_text", "")
    tags = ["#VelaFlow", "#TikTok", "#Shorts", "#Reels"]
    if source_workflow == "seller":
        tags += ["#รีวิวสินค้า", "#TikTokShop", "#ของดีบอกต่อ"]
    elif source_workflow == "podcast":
        tags += ["#Podcastไทย", "#เล่าเรื่อง", "#มนุษย์ออฟฟิศ"]
    elif source_workflow == "viral_clips":
        tags += ["#คลิปไวรัล", "#คอนเทนต์สั้น"]
    else:
        tags += ["#เพลงไทย", "#เพลงใหม่"]
    return {"caption": f"{text}\n\n{' '.join(tags[:12])}", "hashtags": tags[:12], "subtitle_line": text[:80]}


def build_hook_render_package(
    project_name: str,
    source_workflow: str,
    content: dict[str, Any] | list[Any] | str,
    *,
    visual_settings: dict[str, Any] | None = None,
    render_settings: dict[str, Any] | None = None,
    clip_mode: str = "Fast Hook",
    duration_seconds: int = 8,
    export: bool = True,
) -> dict[str, Any]:
    hook = extract_best_hook(source_workflow, content)
    scene_package = build_hook_scene(source_workflow, hook, visual_settings, clip_mode, duration_seconds, content if isinstance(content, dict) else {})
    prompt = build_hook_video_prompt(scene_package)
    caption = build_hook_caption(hook, source_workflow)
    thumbnail_prompt = (
        f"Vertical short-form thumbnail for hook '{hook.get('hook_text', '')}', expressive subject, bold emotional moment, "
        "clean composition, no random text, high quality"
    )
    package = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_workflow": source_workflow,
        "hook": hook,
        "hook_text": hook.get("hook_text", ""),
        "subtitle_line": caption["subtitle_line"],
        "scene_package": scene_package,
        "scene_sequence": scene_package["scenes"],
        "subtitle_timing": scene_package["subtitle_timing"],
        "thumbnail_prompt": thumbnail_prompt,
        "caption": caption["caption"],
        "hashtags": caption["hashtags"],
        "render_prompt": prompt,
        "render_settings": {
            "provider": "PixVerse",
            "aspect_ratio": "9:16",
            "duration": f"{scene_package['duration_seconds']}s",
            "quality": "Draft",
            "motion_intensity": "High",
            "bundle_name": "TikTok Viral",
            **(render_settings or {}),
        },
    }
    render_content = {
        "ai_video_prompt": prompt,
        "thumbnail_prompt": thumbnail_prompt,
        "broll_ideas": [scene.get("beat", "") for scene in scene_package["scenes"]],
        "visual_engine": {"scene_flow": scene_package["scenes"]},
    }
    render_package = build_render_package(project_name, "hook_clip", render_content, package["render_settings"], visual_settings)
    package["render_connector_package"] = render_package
    export_data: dict[str, Any] = {}
    if export:
        export_data = export_hook_clip_package(project_name, package)
        render_root = resolve_project_folder(project_name, "clips").parent
        render_export = export_render_package(project_name, render_package, render_root)
        package["render_connector_export"] = render_export.get("data", {})
    return {"ok": True, "message": "Hook clip package generated", "data": {"package": package, "export": export_data}, "error": ""}


def hook_clip_package_to_text(package: dict[str, Any]) -> str:
    lines = [
        "VELAFLOW HOOK AUTO CLIP PACKAGE",
        "",
        f"Source Workflow: {package.get('source_workflow', '')}",
        f"Hook Text: {package.get('hook_text', '')}",
        f"Subtitle: {package.get('subtitle_line', '')}",
        f"Clip Mode: {(package.get('scene_package') or {}).get('clip_mode', '')}",
        f"Duration: {(package.get('scene_package') or {}).get('duration_seconds', '')}s",
        "",
        "SCENES",
    ]
    for scene in package.get("scene_sequence", []) or []:
        lines.extend(
            [
                f"[{scene.get('scene_id')}] {scene.get('beat')}",
                f"Subtitle: {scene.get('subtitle')}",
                f"Visual: {scene.get('visual_prompt')}",
                f"Camera: {scene.get('camera_direction')}",
                f"Motion: {scene.get('motion')}",
                f"Lighting: {scene.get('lighting')}",
                f"Transition: {scene.get('transition')}",
                "",
            ]
        )
    lines.extend(
        [
            "RENDER PROMPT",
            package.get("render_prompt", ""),
            "",
            "THUMBNAIL PROMPT",
            package.get("thumbnail_prompt", ""),
            "",
            "CAPTION",
            package.get("caption", ""),
            "",
            "HASHTAGS",
            " ".join(package.get("hashtags", []) or []),
            "",
            "NOTE",
            "Render package and queue metadata only. No external video API was called.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def export_hook_clip_package(project_name: str, package: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, Any]:
    try:
        folder = (Path(base_dir) / safe_name(project_name or "hook_clip")) if base_dir else resolve_project_folder(project_name or "hook_clip", "clips")
        export_dir = folder / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        json_path = export_dir / "hook_clip_package.json"
        txt_path = export_dir / "hook_clip_package.txt"
        json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        txt_path.write_text(hook_clip_package_to_text(package), encoding="utf-8")
        return {"ok": True, "message": "Hook clip package exported", "data": {"json_path": str(json_path), "txt_path": str(txt_path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Hook clip export failed", "data": {}, "error": str(exc)}
