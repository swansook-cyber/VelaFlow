from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


HOOK_WORDS = {"hook", "chorus", "final chorus", "post-chorus", "drop", "climax"}
EMOTION_WORDS = {"sad", "lonely", "miss", "cry", "heartbreak", "emotional", "pain", "regret", "love"}
ENERGY_WORDS = {"energy", "fast", "viral", "tiktok", "beat", "drum", "strong", "power", "bigger"}
CAMERA_WORDS = {"close", "dolly", "push", "handheld", "wide", "cinematic", "slow"}


def _text(scene: Dict[str, Any]) -> str:
    keys = [
        "section",
        "lyric_part",
        "subtitle_text",
        "emotion",
        "camera",
        "camera_motion",
        "pacing_note",
        "transition",
        "scene_visual",
        "visual_description",
    ]
    return " ".join(str(scene.get(key, "") or "").lower() for key in keys)


def _scene_id(scene: Dict[str, Any], index: int) -> str:
    return str(scene.get("scene") or index + 1)


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


def classify_scene(score: int) -> Dict[str, str]:
    if score >= 75:
        return {"status": "Good", "color": "#16803c"}
    if score >= 55:
        return {"status": "Needs Review", "color": "#a86600"}
    return {"status": "Weak", "color": "#b42318"}


def _asset_bonus(assets: Dict[str, Any], scene_id: str) -> Dict[str, Any]:
    approved_image = (assets.get("approved_images", {}) or {}).get(scene_id)
    video_slot = (assets.get("videos", {}) or {}).get(scene_id)
    locked_image = (assets.get("locked_images", {}) or {}).get(scene_id)
    ready_video = False
    if video_slot:
        meta = (assets.get("video_metadata", {}) or {}).get(scene_id, {}) or {}
        ready_video = Path(str(video_slot)).is_file() and bool(meta.get("ready_for_render", True))
    return {
        "approved_image": bool(approved_image and Path(str(approved_image)).is_file()),
        "ready_video": ready_video,
        "locked_image": bool(locked_image),
    }


def score_scene(scene: Dict[str, Any], index: int = 0, assets: Dict[str, Any] | None = None) -> Dict[str, Any]:
    assets = assets or {}
    scene_id = _scene_id(scene, index)
    text = _text(scene)
    lyric = str(scene.get("subtitle_text") or scene.get("lyric_part") or "")
    duration = float(scene.get("duration_seconds") or 5)
    asset_state = _asset_bonus(assets, scene_id)

    hook_hits = sum(1 for word in HOOK_WORDS if word in text)
    emotion_hits = sum(1 for word in EMOTION_WORDS if word in text)
    energy_hits = sum(1 for word in ENERGY_WORDS if word in text)
    camera_hits = sum(1 for word in CAMERA_WORDS if word in text)

    lyric_score = 18 if 12 <= len(lyric.strip()) <= 90 else 10 if lyric.strip() else 2
    pacing_score = 14 if 3 <= duration <= 7 else 9 if 2 <= duration <= 10 else 4
    asset_score = 18 if asset_state["ready_video"] else 14 if asset_state["approved_image"] else 5
    lock_bonus = 4 if asset_state["locked_image"] else 0

    emotional_impact = _clamp(35 + emotion_hits * 12 + camera_hits * 5 + lyric_score)
    hook_potential = _clamp(30 + hook_hits * 18 + energy_hits * 10 + pacing_score + lyric_score)
    quality_score = _clamp(28 + asset_score + camera_hits * 6 + lyric_score + lock_bonus)
    teaser_score = _clamp(round((hook_potential * 0.42) + (emotional_impact * 0.32) + (quality_score * 0.26)))
    status = classify_scene(quality_score)

    notes: List[str] = []
    if hook_hits:
        notes.append("hook/chorus candidate")
    if emotion_hits >= 2:
        notes.append("strong emotion")
    if energy_hits:
        notes.append("fast social pacing")
    if asset_state["ready_video"]:
        notes.append("ready video slot")
    elif asset_state["approved_image"]:
        notes.append("approved image")
    else:
        notes.append("needs approved visual")
    actions: List[str] = []
    if not asset_state["approved_image"] and not asset_state["ready_video"]:
        actions.append("approve_or_regenerate_image")
    if quality_score < 55:
        actions.append("regenerate_image")
    if hook_potential >= 75:
        actions.append("preview_tiktok_hook")
    if emotional_impact >= 75 and hook_potential < 75:
        actions.append("preview_cinematic")

    return {
        "scene_id": scene_id,
        "scene_index": index,
        "status": status["status"],
        "status_color": status["color"],
        "quality_score": quality_score,
        "emotional_impact": emotional_impact,
        "hook_potential": hook_potential,
        "teaser_score": teaser_score,
        "duration_seconds": duration,
        "recommended_motion": "hook_energy_zoom" if hook_potential >= 75 else "emotional_push_in" if emotional_impact >= 75 else "cinematic_drift",
        "recommended_subtitle": "tiktok_bold" if hook_potential >= 75 else "cinematic" if emotional_impact >= 70 else "simple",
        "recommended_actions": actions,
        "notes": ", ".join(notes),
    }


def score_project_scenes(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    assets = project.get("assets", {}) or {}
    scores = [score_scene(scene, index, assets) for index, scene in enumerate(storyboard)]
    return sorted(scores, key=lambda item: item.get("teaser_score", 0), reverse=True)


def smart_tiktok_recommendations(project: Dict[str, Any], limit: int = 3) -> Dict[str, Any]:
    scores = score_project_scenes(project)
    picks = []
    for item in scores[: max(1, int(limit or 3))]:
        picks.append(
            {
                "scene_id": item["scene_id"],
                "teaser_score": item["teaser_score"],
                "hook_potential": item["hook_potential"],
                "emotional_impact": item["emotional_impact"],
                "motion": item["recommended_motion"],
                "subtitle": item["recommended_subtitle"],
                "aspect_ratio": "9:16",
                "render_profile": "TikTok Fast",
                "notes": item["notes"],
            }
        )
    return {
        "ok": True,
        "message": "Smart TikTok recommendations created without external API",
        "data": {"recommended_scenes": picks},
        "error": "",
    }
