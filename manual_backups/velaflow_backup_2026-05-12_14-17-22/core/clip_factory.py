import json
from pathlib import Path
from typing import Any, Dict, List

from core.ffmpeg_utils import append_log, ffmpeg_available, run_ffmpeg
from core.scene_scoring import score_project_scenes, smart_tiktok_recommendations
from core.branding import PROGRAM_NAME


CLIP_TYPES = {
    "15s teaser": {"duration": 15, "filename": "teaser_15s_9x16.mp4", "caption": "teaser", "selection": "tiktok"},
    "30s teaser": {"duration": 30, "filename": "teaser_30s_9x16.mp4", "caption": "teaser", "selection": "tiktok"},
    "60s promo": {"duration": 60, "filename": "promo_60s_9x16.mp4", "caption": "promo", "selection": "tiktok"},
    "Spotify Canvas 8s": {"duration": 8, "filename": "spotify_canvas_8s.mp4", "caption": "canvas", "selection": "visual"},
    "Hook Clip": {"duration": 30, "filename": "hook_clip_9x16.mp4", "caption": "hook", "selection": "hook"},
    "Emotional Quote Clip": {"duration": 15, "filename": "emotional_quote_clip_9x16.mp4", "caption": "quote", "selection": "emotion"},
}

CLIP_TYPE_ALIASES = {
    "Spotify Canvas 8s vertical loop": "Spotify Canvas 8s",
    "chorus hook clip": "Hook Clip",
    "emotional quote clip": "Emotional Quote Clip",
}


def _clip_type_name(clip_type: str) -> str:
    return CLIP_TYPE_ALIASES.get(clip_type, clip_type if clip_type in CLIP_TYPES else "15s teaser")


def _storyboard(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(((project.get("mv", {}) or {}).get("storyboard", []) or []))


def _scene_id(scene: Dict[str, Any], index: int) -> str:
    return str(scene.get("scene") or index + 1)


def _scene_starts(project: Dict[str, Any]) -> Dict[str, float]:
    starts: Dict[str, float] = {}
    current = 0.0
    for index, scene in enumerate(_storyboard(project)):
        scene_id = _scene_id(scene, index)
        try:
            explicit = scene.get("start_time")
            starts[scene_id] = float(explicit) if explicit not in {None, ""} else current
        except Exception:
            starts[scene_id] = current
        try:
            duration = max(1.0, float(scene.get("duration_seconds") or 5))
        except Exception:
            duration = 5.0
        current += duration
    return starts


def _scene_by_id(project: Dict[str, Any], scene_id: str) -> Dict[str, Any]:
    for index, scene in enumerate(_storyboard(project)):
        if _scene_id(scene, index) == str(scene_id):
            return scene
    return {}


def choose_clip_scene(project: Dict[str, Any], clip_type: str) -> Dict[str, Any]:
    clip_type = _clip_type_name(clip_type)
    spec = CLIP_TYPES[clip_type]
    scores = score_project_scenes(project)
    starts = _scene_starts(project)
    tiktok = smart_tiktok_recommendations(project).get("data", {}).get("recommended_scenes", []) or []
    selected = None
    selection = spec.get("selection", "tiktok")

    if selection == "emotion":
        selected = max(scores, key=lambda item: item.get("emotional_impact", 0), default=None)
    elif selection == "hook":
        selected = max(scores, key=lambda item: item.get("hook_potential", 0), default=None)
    elif selection == "visual":
        selected = max(scores, key=lambda item: item.get("quality_score", 0), default=None)
    elif tiktok:
        scene_id = str(tiktok[0].get("scene_id", ""))
        selected = next((item for item in scores if str(item.get("scene_id")) == scene_id), None) or (scores[0] if scores else None)
    else:
        selected = scores[0] if scores else None

    if not selected:
        return {"scene_id": "1", "scene_index": 0, "start_seconds": 0.0, "score": {}, "scene": {}}

    scene_id = str(selected.get("scene_id", "1"))
    scene = _scene_by_id(project, scene_id)
    return {
        "scene_id": scene_id,
        "scene_index": int(selected.get("scene_index", 0) or 0),
        "start_seconds": starts.get(scene_id, 0.0),
        "score": selected,
        "scene": scene,
    }


def choose_clip_start(project: Dict[str, Any], clip_type: str, fallback_duration: float = 0.0) -> float:
    chosen = choose_clip_scene(project, clip_type)
    if chosen.get("scene"):
        return max(0.0, float(chosen.get("start_seconds", 0.0) or 0.0))
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    song = project.get("song", {}) or {}
    recommendations = song.get("tiktok_clip_cut_recommendation", []) or []
    if recommendations:
        first = recommendations[0]
        for key in ["start_seconds", "start", "start_time"]:
            try:
                return float(first.get(key, 0))
            except Exception:
                pass
    target_words = ["chorus", "hook", "final chorus"] if "chorus" in clip_type.lower() or "teaser" in clip_type.lower() else ["sad", "emotional", "cry", "lonely"]
    for scene in storyboard:
        text = " ".join(str(scene.get(key, "") or "").lower() for key in ["lyric_part", "emotion", "pacing_note", "section"])
        if any(word in text for word in target_words):
            try:
                return max(0.0, float(scene.get("start_time", 0) or 0))
            except Exception:
                return 0.0
    return 0.0 if fallback_duration < 20 else max(0.0, fallback_duration * 0.35)


def build_clip_caption(project: Dict[str, Any], clip_type: str, selected_scene: Dict[str, Any]) -> Dict[str, Any]:
    clip_type = _clip_type_name(clip_type)
    scene = selected_scene.get("scene", {}) or {}
    score = selected_scene.get("score", {}) or {}
    song = project.get("song", {}) or {}
    title = project.get("title") or song.get("title") or PROGRAM_NAME
    lyric = str(scene.get("subtitle_text") or scene.get("lyric_part") or song.get("selected_hook") or "").strip()
    if len(lyric) > 120:
        lyric = lyric[:117].rstrip() + "..."
    hook = lyric or str(song.get("selected_hook", "") or "").strip()
    hashtags = ["#เพลงไทย", "#VelaFlow", "#MV", "#VelaLab"]
    if "TikTok" in clip_type or "teaser" in clip_type.lower() or "Hook" in clip_type:
        hashtags += ["#TikTokเพลง", "#เพลงใหม่"]
    if "Emotional" in clip_type:
        hashtags += ["#เพลงเศร้า", "#แคปชั่นเพลง"]
    caption = f"{hook}\n\n{title}\n{' '.join(hashtags)}".strip()
    return {
        "clip_type": clip_type,
        "scene_id": selected_scene.get("scene_id", ""),
        "title": title,
        "caption": caption,
        "hashtags": hashtags,
        "lyric_quote": hook,
        "recommended_motion": score.get("recommended_motion", ""),
        "recommended_subtitle": score.get("recommended_subtitle", ""),
        "teaser_score": score.get("teaser_score", 0),
    }


def _write_caption_files(clips_dir: Path, output_path: Path, caption: Dict[str, Any]) -> Dict[str, str]:
    caption_txt = clips_dir / f"{output_path.stem}_caption.txt"
    caption_json = clips_dir / f"{output_path.stem}_caption.json"
    caption_txt.write_text(caption.get("caption", ""), encoding="utf-8")
    caption_json.write_text(json.dumps(caption, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"txt": str(caption_txt), "json": str(caption_json)}


def generate_clip(
    project: Dict[str, Any],
    source_video: str,
    render_dir: str | Path,
    clip_type: str,
    ffmpeg_path: str = "ffmpeg",
    preview: bool = False,
    scene_id: str = "",
) -> Dict[str, Any]:
    render_dir = Path(render_dir)
    clips_dir = render_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = clips_dir / "clip_metadata.json"
    clip_type = _clip_type_name(clip_type)
    spec = CLIP_TYPES[clip_type]
    selected_scene = choose_clip_scene(project, clip_type)
    if scene_id:
        scene = _scene_by_id(project, scene_id)
        starts = _scene_starts(project)
        if scene:
            selected_scene = {
                "scene_id": str(scene_id),
                "scene_index": next((index for index, item in enumerate(_storyboard(project)) if _scene_id(item, index) == str(scene_id)), 0),
                "start_seconds": starts.get(str(scene_id), 0.0),
                "score": next((item for item in score_project_scenes(project) if str(item.get("scene_id")) == str(scene_id)), {}),
                "scene": scene,
            }
    filename = spec["filename"]
    output_path = clips_dir / (f"preview_{filename}" if preview else filename)
    start = max(0.0, float(selected_scene.get("start_seconds", 0.0) or 0.0))
    duration = min(5, int(spec["duration"])) if preview else int(spec["duration"])
    caption = build_clip_caption(project, clip_type, selected_scene)
    caption_paths = _write_caption_files(clips_dir, output_path, caption)
    metadata = {
        "clip_type": clip_type,
        "mode": "preview" if preview else "final",
        "source_video": source_video,
        "start_seconds": start,
        "duration_seconds": duration,
        "target_duration_seconds": spec["duration"],
        "aspect_ratio": "9:16",
        "selected_scene": selected_scene,
        "caption": caption,
        "caption_paths": caption_paths,
        "output_path": str(output_path),
    }

    if not source_video or not Path(source_video).is_file() or not ffmpeg_available(ffmpeg_path):
        metadata["status"] = "metadata_only"
        _append_clip_metadata(metadata_path, metadata)
        return {"ok": False, "message": "Clip metadata created; source video or ffmpeg unavailable", "data": metadata, "error": "missing source or ffmpeg"}

    log_path = render_dir / "render_log.txt"
    append_log(log_path, f"[INFO] Generating clip {clip_type}")
    command: List[str] = [
        ffmpeg_path,
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        source_video,
        "-t",
        str(duration),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    result = run_ffmpeg(command, log_path)
    metadata["status"] = "ready" if result["ok"] else "failed"
    metadata["command"] = result["command"]
    metadata["error"] = result["error"]
    _append_clip_metadata(metadata_path, metadata)
    return {"ok": result["ok"], "message": "Clip generated" if result["ok"] else "Clip failed", "data": metadata, "error": result["error"]}


def _append_clip_metadata(metadata_path: Path, metadata: Dict[str, Any]) -> None:
    existing: Dict[str, Any] = {"clips": []}
    if metadata_path.exists():
        try:
            loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
                existing.setdefault("clips", [])
        except Exception:
            existing = {"clips": []}
    existing["clips"].append(metadata)
    existing["latest"] = metadata
    metadata_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_clip_set(
    project: Dict[str, Any],
    source_video: str,
    render_dir: str | Path,
    ffmpeg_path: str = "ffmpeg",
    preview: bool = False,
) -> Dict[str, Any]:
    results = []
    for clip_type in CLIP_TYPES:
        results.append(generate_clip(project, source_video, render_dir, clip_type, ffmpeg_path, preview=preview))
    ok = any(item.get("ok") for item in results)
    return {
        "ok": ok,
        "message": "Clip set generated" if ok else "Clip set metadata created",
        "data": {"clips": [item.get("data", {}) for item in results]},
        "error": "; ".join(item.get("error", "") for item in results if item.get("error")),
    }
