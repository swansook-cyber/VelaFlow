import json
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont

from core.motion_engine import select_motion
from core.audio_analysis import beats_in_range


VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _scene_key(scene: Dict[str, Any], index: int) -> str:
    return str(scene.get("scene") or index + 1)


def _placeholder_image(render_dir: Path, scene_id: str, label: str = "") -> Path:
    folder = render_dir / "placeholders"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"scene_{str(scene_id).zfill(2)}_placeholder.png"
    if path.exists():
        return path
    image = Image.new("RGB", (1920, 1080), (18, 20, 27))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arial.ttf", 72)
        body_font = ImageFont.truetype("arial.ttf", 38)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
    draw.rectangle((0, 0, 1919, 1079), outline=(85, 170, 255), width=8)
    draw.text((80, 80), f"Scene {scene_id}", fill=(235, 240, 248), font=title_font)
    draw.text((80, 190), label or "Missing approved image/video - offline placeholder", fill=(190, 205, 220), font=body_font)
    image.save(path)
    return path


def _select_source(project: Dict[str, Any], scene_id: str, render_dir: Path) -> Dict[str, str]:
    assets = project.get("assets", {}) or {}
    video_path = assets.get("videos", {}).get(scene_id) or assets.get("videos", {}).get(str(int(scene_id)) if scene_id.isdigit() else scene_id) or ""
    video_meta = assets.get("video_metadata", {}).get(scene_id, {}) or {}
    if video_path and Path(video_path).is_file() and Path(video_path).suffix.lower() in VIDEO_SUFFIXES and video_meta.get("ready_for_render", True):
        return {"source_type": "video", "source_path": str(Path(video_path))}

    image_path = assets.get("approved_images", {}).get(scene_id) or assets.get("images", {}).get(scene_id) or ""
    if image_path and Path(image_path).is_file() and Path(image_path).suffix.lower() in IMAGE_SUFFIXES:
        return {"source_type": "approved_image", "source_path": str(Path(image_path))}

    placeholder = _placeholder_image(render_dir, scene_id)
    return {"source_type": "placeholder", "source_path": str(placeholder)}


def _section_type(scene: Dict[str, Any]) -> str:
    text = " ".join(str(scene.get(key, "") or "").lower() for key in ["lyric_part", "pacing_note", "emotion", "section", "time_range"])
    if "final chorus" in text:
        return "final_chorus"
    if "chorus" in text or "hook" in text:
        return "hook"
    if "bridge" in text:
        return "bridge"
    if "verse" in text:
        return "verse"
    return "scene"


def _timeline_intelligence(scene: Dict[str, Any], duration: float, motion: str, transition: str, beat_count: int = 0) -> Dict[str, Any]:
    section = _section_type(scene)
    emotion_text = str(scene.get("emotion", "") or "").lower()
    camera_text = str(scene.get("camera") or scene.get("camera_motion") or "").lower()
    pacing_note = str(scene.get("pacing_note", "") or "")
    adjusted_duration = duration
    adjusted_motion = motion
    adjusted_transition = transition or "fade"
    edit_note = "balanced scene pacing"

    if section in {"hook", "final_chorus"}:
        adjusted_duration = max(2.0, min(duration, 6.0))
        adjusted_motion = "hook_energy_zoom" if motion == "cinematic_drift" else motion
        adjusted_transition = "flash cut" if not transition or transition == "fade" else transition
        edit_note = "hook/chorus gets faster cuts and stronger motion"
    elif section == "verse":
        adjusted_duration = max(duration, 5.0)
        adjusted_motion = "slow_zoom_in" if motion in {"hook_energy_zoom", "cinematic_drift"} else motion
        adjusted_transition = "fade" if not transition else transition
        edit_note = "verse stays slower and softer"
    elif section == "bridge":
        adjusted_duration = max(duration, 6.0)
        adjusted_motion = "emotional_push_in" if motion == "cinematic_drift" else motion
        adjusted_transition = "blur dissolve" if not transition or transition == "fade" else transition
        edit_note = "bridge keeps darker emotional pacing"

    if any(word in emotion_text for word in ["sad", "lonely", "cry", "miss", "emotional"]) or any(word in camera_text for word in ["close", "push", "dolly"]):
        if section not in {"hook", "final_chorus"}:
            adjusted_motion = "emotional_push_in"
            edit_note += "; emotion pushes in"
    if beat_count >= 3 and section in {"hook", "final_chorus", "scene"}:
        adjusted_motion = "hook_energy_zoom"
        edit_note += "; beat density increases motion"

    return {
        "duration_seconds": round(adjusted_duration, 3),
        "motion_effect": adjusted_motion,
        "transition": adjusted_transition,
        "section_type": section,
        "edit_intelligence": edit_note,
    }


def build_timeline(project: Dict[str, Any], render_dir: str | Path, motion_style: str = "auto", beat_map: Dict[str, Any] | None = None, beat_sync: bool = False) -> Dict[str, Any]:
    render_path = Path(render_dir)
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    if not storyboard:
        storyboard = [
            {
                "scene": 1,
                "duration_seconds": 5,
                "lyric_part": "",
                "emotion": "neutral",
                "camera": "still",
                "pacing_note": "fallback",
                "transition": "fade",
                "subtitle_text": "",
            }
        ]

    timeline: List[Dict[str, Any]] = []
    start_time = 0.0
    for index, scene in enumerate(storyboard):
        scene_id = _scene_key(scene, index)
        duration = max(1.0, _as_float(scene.get("duration_seconds"), 6.0))
        source = _select_source(project, scene_id, render_path)
        scene_beats = beats_in_range(beat_map or {}, start_time, start_time + duration)
        motion = select_motion(scene, motion_style)
        intelligence = _timeline_intelligence(scene, duration, motion, scene.get("transition", ""), len(scene_beats))
        duration = intelligence["duration_seconds"]
        if beat_sync and scene_beats:
            last_beat = scene_beats[-1]["time"]
            duration = max(1.0, round(last_beat - start_time, 3))
            intelligence["edit_intelligence"] += "; duration snapped to beat"
        item = {
            "scene_id": scene_id,
            "start_time": round(start_time, 3),
            "duration_seconds": round(duration, 3),
            "source_type": source["source_type"],
            "source_path": source["source_path"],
            "lyric_part": scene.get("lyric_part", ""),
            "emotion": scene.get("emotion", ""),
            "camera": scene.get("camera") or scene.get("camera_motion", ""),
            "pacing_note": scene.get("pacing_note", ""),
            "transition": intelligence["transition"],
            "motion_effect": intelligence["motion_effect"],
            "section_type": intelligence["section_type"],
            "edit_intelligence": intelligence["edit_intelligence"],
            "beat_count": len(scene_beats),
            "beat_times": [beat["time"] for beat in scene_beats[:12]],
            "audio_reactive_strength": round(max([beat.get("strength", 0) for beat in scene_beats] or [0]), 3),
            "subtitle_text": scene.get("subtitle_text") or scene.get("lyric_part", ""),
        }
        timeline.append(item)
        start_time += duration

    data = {
        "project": project.get("title", ""),
        "total_duration_seconds": round(start_time, 3),
        "scene_count": len(timeline),
        "items": timeline,
    }
    output = render_path / "timeline.json"
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
