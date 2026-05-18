from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from providers.veo_provider import DEFAULT_VEO_MODEL, build_veo_payload, download_render_result, poll_render_status, submit_render_job


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
    api_key = str(
        settings.get("gemini_api_key")
        or settings.get("google_api_key")
        or settings.get("veo_api_key")
        or os.getenv("GEMINI_API_KEY", "")
        or os.getenv("GOOGLE_API_KEY", "")
        or os.getenv("VEO_API_KEY", "")
    ).strip()
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
    if provider not in {"gemini_veo", "google_veo", "veo"}:
        return {
            "ok": False,
            "message": "AI video provider unsupported",
            "data": {"path": str(output), "provider": provider, "fallback_reason": "unsupported_provider", "prompt_validation": validation},
            "error": "unsupported_provider",
        }
    model = str(settings.get("model") or settings.get("veo_model") or os.getenv("VEO_MODEL", "") or DEFAULT_VEO_MODEL)
    timeout_seconds = int(settings.get("timeout_seconds") or settings.get("timeout") or os.getenv("VEO_TIMEOUT_SECONDS", "900"))
    poll_interval = max(2, int(settings.get("poll_interval_seconds") or os.getenv("VEO_POLL_INTERVAL_SECONDS", "10")))
    payload = build_veo_payload(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        duration_seconds=max(3, min(8, int(round(float(duration_seconds or 5))))),
        model=model,
    )
    submit = submit_render_job(payload, api_key=api_key, timeout_seconds=timeout_seconds)
    if not submit.get("ok"):
        return {
            "ok": False,
            "message": f"AI Video provider failed: {submit.get('error') or submit.get('message')}",
            "data": {
                "path": str(output),
                "provider": provider,
                "provider_used": "google_veo",
                "provider_available": True,
                "fallback_reason": submit.get("error") or "submit_failed",
                "provider_status": "submit_failed",
                "submit": submit.get("data", {}),
                "payload": {**payload, "prompt": prompt},
                "prompt_validation": validation,
            },
            "error": submit.get("error") or "submit_failed",
        }
    job_id = ((submit.get("data") or {}).get("job_id") or "")
    started = time.time()
    status_history: list[dict[str, Any]] = [{"status": "submitted", "job_id": job_id, "at": datetime.now().isoformat(timespec="seconds")}]
    last_status: dict[str, Any] = submit
    while time.time() - started <= timeout_seconds:
        polled = poll_render_status(job_id, api_key=api_key, timeout_seconds=poll_interval)
        last_status = polled
        status = str(((polled.get("data") or {}).get("status") or "")).lower()
        status_history.append({"status": status or polled.get("error", ""), "job_id": job_id, "at": datetime.now().isoformat(timespec="seconds")})
        if polled.get("ok") and status == "completed":
            download = download_render_result(job_id, output, api_key=api_key)
            if not download.get("ok"):
                return {
                    "ok": False,
                    "message": f"AI Video provider failed: {download.get('error') or download.get('message')}",
                    "data": {
                        "path": str(output),
                        "provider": provider,
                        "provider_used": "google_veo",
                        "provider_available": True,
                        "fallback_reason": download.get("error") or "download_failed",
                        "provider_status": "download_failed",
                        "job_id": job_id,
                        "status_history": status_history,
                        "download": download.get("data", {}),
                        "payload": {**payload, "prompt": prompt},
                        "prompt_validation": validation,
                    },
                    "error": download.get("error") or "download_failed",
                }
            try:
                from core.real_clip_pipeline import validate_mp4

                media_validation = validate_mp4(output, min_duration=1.0, min_file_size=100 * 1024)
            except Exception as exc:
                media_validation = {"valid_mp4": output.is_file() and output.stat().st_size > 100 * 1024, "error": type(exc).__name__}
            if not media_validation.get("valid_mp4") or not media_validation.get("has_video", True):
                return {
                    "ok": False,
                    "message": "AI Video provider returned invalid MP4",
                    "data": {
                        "path": str(output),
                        "provider": provider,
                        "provider_used": "google_veo",
                        "fallback_reason": "invalid_provider_video",
                        "provider_status": "validation_failed",
                        "job_id": job_id,
                        "status_history": status_history,
                        "validation": media_validation,
                        "payload": {**payload, "prompt": prompt},
                        "prompt_validation": validation,
                    },
                    "error": "invalid_provider_video",
                }
            return {
                "ok": True,
                "message": "AI video shot generated",
                "data": {
                    "path": str(output),
                    "provider": provider,
                    "provider_used": "google_veo",
                    "provider_available": True,
                    "real_ai_video_used": True,
                    "fallback_reason": "",
                    "provider_status": "complete",
                    "job_id": job_id,
                    "status_history": status_history,
                    "duration_seconds": duration_seconds,
                    "aspect_ratio": aspect_ratio,
                    "motion_style": motion_style,
                    "validation": media_validation,
                    "payload": {**payload, "prompt": prompt},
                    "prompt_validation": validation,
                },
                "error": "",
            }
        if not polled.get("ok") or status in {"failed", "error"}:
            break
        time.sleep(poll_interval)
    reason = last_status.get("error") or "provider_timeout"
    return {
        "ok": False,
        "message": f"AI Video provider failed: {reason}",
        "data": {
            "path": str(output),
            "provider": provider,
            "provider_used": "google_veo",
            "provider_available": True,
            "fallback_reason": reason,
            "provider_status": "failed_or_timeout",
            "job_id": job_id,
            "status_history": status_history,
            "last_status": last_status.get("data", {}),
            "payload": {**payload, "prompt": prompt},
            "prompt_validation": validation,
        },
        "error": reason,
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
