from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


VIDEO_VISUAL_MODE = "cinematic_live_action_video_v1"
FORBIDDEN_VIDEO_PROMPT_TERMS = (
    "split screen",
    "storyboard",
    "contact sheet",
    "multi-panel",
    "subtitles",
    "subtitle",
    "text overlay",
    "logo",
    "watermark",
    "caption",
)


def _clean_prompt(value: str) -> str:
    text = " ".join(str(value or "").split())
    lowered = text.lower()
    replacements = {
        "thumbnail": "cinematic film frame",
        "meme": "grounded emotional realism",
        "viral text": "cinematic visual rhythm",
        "caption": "bottom-safe composition",
        "subtitle": "bottom-safe composition",
        "score": "emotional intensity",
        "67/100": "emotional intensity",
    }
    for source, target in replacements.items():
        if source in lowered:
            text = text.replace(source, target).replace(source.title(), target)
            lowered = text.lower()
    return text


def build_hook_video_shot_prompts(
    *,
    full_hook_lyrics: str,
    mood: str = "",
    scene_director_plan: dict[str, Any] | None = None,
    emotional_arc: dict[str, Any] | list[Any] | None = None,
    target_duration: float = 15.0,
    shot_count: int = 6,
) -> list[dict[str, Any]]:
    scenes = (scene_director_plan or {}).get("scenes") or []
    shot_count = max(6, min(10, int(shot_count or 6)))
    duration = max(2.0, min(4.0, float(target_duration or 15.0) / shot_count))
    camera_styles = [
        "wide emotional establishing shot with subtle handheld drift",
        "medium profile shot with slow push-in",
        "over-shoulder reflection shot with parallax depth",
        "close-up eyes shot with emotional breathing motion",
        "side profile shot with cinematic drift",
        "release shot with soft pull-out and fade",
        "low-angle room detail shot with slow pan",
        "close emotional face shot with rack-focus feeling",
        "negative-space silhouette shot with gentle orbit",
        "ending close-up with soft light falloff",
    ]
    hook = _clean_prompt(full_hook_lyrics)
    arc_text = _clean_prompt(json.dumps(emotional_arc or {}, ensure_ascii=False, default=str))
    prompts: list[dict[str, Any]] = []
    for index in range(shot_count):
        scene = scenes[index % len(scenes)] if scenes else {}
        camera = camera_styles[index]
        emotional_intent = _clean_prompt(str(scene.get("emotional_intent") or scene.get("subtitle") or mood or "emotional longing"))
        continuity = scene.get("continuity_notes") or {}
        continuity_text = _clean_prompt(
            "same character, same face, same hairstyle, same clothing, same room, same lighting palette, "
            f"{continuity.get('character', '')} {continuity.get('location', '')}"
        )
        prompt = (
            "single continuous cinematic video shot, ultra realistic live-action, vertical 9:16, "
            "natural human motion, cinematic camera movement, realistic skin texture, natural lighting, "
            f"{camera}, {emotional_intent}, {continuity_text}, mood: {mood}, emotional arc: {arc_text[:220]}, "
            f"full hook feeling: {hook[:360]}, no text, no subtitles, no logos, no watermark, no split screen, no storyboard"
        )
        prompts.append(
            {
                "shot_id": f"shot_{index + 1:02d}",
                "duration_seconds": round(duration, 2),
                "aspect_ratio": "9:16",
                "motion_style": camera,
                "prompt": prompt,
                "full_hook_section_used": bool(hook),
            }
        )
    return prompts


def validate_video_prompt(prompt: str) -> dict[str, Any]:
    lowered = str(prompt or "").lower()
    found = [term for term in FORBIDDEN_VIDEO_PROMPT_TERMS if term in lowered and f"no {term}" not in lowered]
    required = [
        "single continuous cinematic video shot",
        "ultra realistic live-action",
        "vertical 9:16",
        "natural human motion",
        "cinematic camera movement",
        "no text",
        "no subtitles",
    ]
    missing = [term for term in required if term not in lowered]
    return {"ok": not found and not missing, "forbidden_terms_found": found, "missing_required_terms": missing}


def generate_video_shot(
    prompt: str,
    duration_seconds: float,
    output_path: str | Path,
    *,
    provider: str = "gemini_veo",
    aspect_ratio: str = "9:16",
    motion_style: str = "cinematic drift",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or {}
    output = Path(output_path)
    validation = validate_video_prompt(prompt)
    if not validation.get("ok"):
        return {
            "ok": False,
            "message": "Video prompt failed safety validation",
            "data": {"path": str(output), "provider": provider, "prompt_validation": validation},
            "error": "video_prompt_validation_failed",
        }
    api_key = str(settings.get("gemini_api_key") or settings.get("veo_api_key") or "").strip()
    if provider in {"gemini_veo", "google_veo", "veo"} and not api_key:
        return {
            "ok": False,
            "message": "AI video provider unavailable",
            "data": {
                "path": str(output),
                "provider": provider,
                "provider_available": False,
                "fallback_reason": "missing_api_key",
                "duration_seconds": duration_seconds,
                "aspect_ratio": aspect_ratio,
                "motion_style": motion_style,
                "prompt_validation": validation,
            },
            "error": "missing_api_key",
        }
    return {
        "ok": False,
        "message": "AI video provider placeholder is not connected yet",
        "data": {
            "path": str(output),
            "provider": provider,
            "provider_available": bool(api_key),
            "fallback_reason": "provider_placeholder_not_connected",
            "duration_seconds": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "motion_style": motion_style,
            "prompt_validation": validation,
        },
        "error": "provider_placeholder_not_connected",
    }


def generate_video(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if len(args) >= 4:
        provider = str(args[0] or "gemini_veo")
        prompt = str(args[1] or "")
        output_path = args[3]
        settings = args[4] if len(args) >= 5 and isinstance(args[4], dict) else kwargs.get("settings") or {}
        if provider == "offline":
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.with_suffix(".json").write_text(
                json.dumps(
                    {
                        "generated_by": "VelaFlow",
                        "provider": "offline",
                        "prompt": prompt,
                        "source_image": str(args[2] or ""),
                        "metadata": settings,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            output.with_suffix(".video_slot.txt").write_text(
                "Offline video provider placeholder. Use image-motion fallback for final MP4.\n",
                encoding="utf-8",
            )
            return {"ok": True, "message": "Offline video slot exported", "data": {"path": str(output)}, "error": ""}
    else:
        prompt = str(args[0] if args else kwargs.get("prompt", ""))
        output_path = args[1] if len(args) >= 2 else kwargs.get("output_path", "")
        provider = str(kwargs.get("provider") or "gemini_veo")
        settings = kwargs.get("settings") or {}
    return generate_video_shot(
        prompt,
        float(kwargs.get("duration_seconds") or kwargs.get("duration") or 5.0),
        output_path,
        provider=provider,
        aspect_ratio=str(kwargs.get("aspect_ratio") or "9:16"),
        motion_style=str(kwargs.get("motion_style") or "cinematic drift"),
        settings=settings,
    )


def save_video_generation_manifest(path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {"generated_by": "VelaFlow", "created_at": datetime.now().isoformat(timespec="seconds"), **payload}
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Video generation manifest exported", "data": {"path": str(output), "manifest": data}, "error": ""}
