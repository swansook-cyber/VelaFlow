from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name


VISUAL_BANK = [
    "young Thai singer sitting beside a window in a small apartment at night with rain outside",
    "empty city street after rain with neon reflections on wet asphalt",
    "lonely rooftop overlooking Bangkok city lights",
    "bedroom lit by a television glow with scattered memories on the floor",
    "quiet convenience store exterior at midnight with soft rain",
    "mirror reflection close-up with tired emotional eyes",
    "slow walk across a pedestrian bridge under warm street lights",
    "inside an old car parked by the roadside with blurred city bokeh",
    "silhouette standing in a doorway with warm light behind",
    "wide shot of an empty room as morning light slowly enters",
]

CAMERA_BANK = [
    "slow push-in shot",
    "handheld emotional close-up",
    "wide cinematic establishing shot",
    "soft over-shoulder shot",
    "slow dolly left",
    "static frame with subtle breathing room",
    "vertical close-up with gentle camera drift",
    "slow pull-back reveal",
    "low-angle reflective shot",
    "top-down emotional shot",
]

LIGHTING_BANK = [
    "cinematic blue night lighting",
    "warm practical lamp light",
    "neon reflections on wet street",
    "soft window light",
    "moody rain lighting",
    "golden hour backlight",
    "low-key cinematic contrast",
    "warm lonely street light",
    "soft film look glow",
    "dim room light with gentle shadows",
]

TRANSITION_BANK = [
    "fade into city lights",
    "blur dissolve to the next memory",
    "match cut on window reflection",
    "slow dip to black",
    "soft light leak transition",
    "rain ripple dissolve",
    "gentle whip pan for hook energy",
    "crossfade into a close-up",
    "flash cut on emotional lyric",
    "smooth cinematic dissolve",
]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _song_value(song: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = song.get(key)
        if isinstance(value, dict):
            continue
        if _clean_text(value):
            return _clean_text(value)
    return ""


def _nested_song_value(song: Dict[str, Any], parent: str, key: str) -> str:
    value = song.get(parent)
    if isinstance(value, dict):
        return _clean_text(value.get(key))
    return ""


def _lyric_lines(lyrics: str) -> List[str]:
    lines: List[str] = []
    for raw in (lyrics or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.fullmatch(r"\[[^\]]+\]", line):
            continue
        if re.fullmatch(r"\([^)]+\)", line):
            continue
        lines.append(line)
    return lines[:24] or [
        "instrumental emotional opening",
        "main emotional lyric moment",
        "hook line performance moment",
        "bridge reflection moment",
        "final chorus emotional release",
    ]


def _pick(items: List[str], index: int, offset: int = 0) -> str:
    return items[(index + offset) % len(items)]


def _scene_title(visual: str, mood: str, index: int) -> str:
    title_map = [
        "Night Apartment Loneliness",
        "Rain Street Reflection",
        "Rooftop Emotional Distance",
        "Bedroom Memory Glow",
        "Midnight Convenience Store",
        "Mirror Regret Close-Up",
        "Bridge Walk Release",
        "Car Window Confession",
        "Doorway Hope",
        "Morning After Resolution",
    ]
    if index < len(title_map):
        return title_map[index]
    words = [word.capitalize() for word in re.findall(r"[A-Za-z]+", visual)[:3]]
    return " ".join(words) or f"{mood.title()} Scene {index + 1}"


def _metadata_from_song(song: Dict[str, Any], project: Dict[str, Any] | None = None) -> Dict[str, str]:
    project = project or {}
    music_preset_data = song.get("music_preset_data") if isinstance(song.get("music_preset_data"), dict) else {}
    vocal_data = song.get("vocal_direction_data") if isinstance(song.get("vocal_direction_data"), dict) else {}
    return {
        "song_title": _song_value(song, "song_title", "title") or _clean_text(project.get("title")) or "Untitled Song",
        "genre": _song_value(song, "genre") or _nested_song_value(song, "artist_preset_data", "genre") or _clean_text(music_preset_data.get("genre")) or "Modern Pop / Pop Rock",
        "mood": _song_value(song, "mood") or _clean_text(music_preset_data.get("mood")) or _clean_text((project.get("creative_direction") or {}).get("mood")) or "emotional, cinematic",
        "vocal_direction": _song_value(song, "vocal_direction") or _clean_text(vocal_data.get("name")) or _clean_text(vocal_data.get("vocal_style")) or "Male Emotional",
        "music_preset": _song_value(song, "music_preset") or _clean_text(music_preset_data.get("name")) or "VelaFlow Default",
    }


def generate_mv_storyboard(
    song: Dict[str, Any],
    project: Dict[str, Any] | None = None,
    scene_count: int = 8,
) -> Dict[str, Any]:
    try:
        count = max(5, min(10, int(scene_count or 8)))
        metadata = _metadata_from_song(song or {}, project)
        lyrics = (
            _song_value(song or {}, "normalized_song_output", "complete_lyrics", "lyrics", "original_song_output")
            or _clean_text((project or {}).get("manual_lyrics"))
        )
        lines = _lyric_lines(lyrics)
        mood = metadata["mood"]
        genre = metadata["genre"]
        vocal = metadata["vocal_direction"]
        preset = metadata["music_preset"]
        scenes: List[Dict[str, Any]] = []
        hook_indices = {max(1, count // 3), max(2, (count * 2) // 3)}

        for index in range(count):
            lyric = lines[index % len(lines)]
            visual = _pick(VISUAL_BANK, index)
            camera = _pick(CAMERA_BANK, index, len(preset))
            lighting = _pick(LIGHTING_BANK, index, len(genre))
            transition = _pick(TRANSITION_BANK, index, len(vocal))
            scene_mood = mood if index not in hook_indices else f"{mood}, emotional hook emphasis"
            title = _scene_title(visual, mood, index)
            vertical_note = "vertical 9:16 safe composition"
            visual_prompt = (
                f"{visual}, inspired by the lyric moment '{lyric[:80]}', {lighting}, "
                f"{camera}, cinematic emotional realistic style, {vertical_note}, "
                f"optimized for AI video generation"
            )
            video_prompt = f"{visual_prompt}, subtle natural motion, realistic human emotion, concise shot design"
            scenes.append(
                {
                    "scene": index + 1,
                    "scene_number": index + 1,
                    "scene_title": title,
                    "visual_prompt": visual_prompt,
                    "camera_direction": camera,
                    "lighting": lighting,
                    "mood": scene_mood,
                    "transition_idea": transition,
                    "lyric_part": lyric,
                    "emotion": scene_mood,
                    "camera": camera,
                    "transition": transition,
                    "scene_visual": visual,
                    "image_prompt": visual_prompt,
                    "video_prompt": video_prompt,
                    "vertical_shorts_prompt": f"9:16 vertical short, {video_prompt}",
                    "duration_seconds": 5 if index in hook_indices else 7,
                    "pacing_note": "strong hook cut" if index in hook_indices else "cinematic emotional pacing",
                }
            )

        return {
            "ok": True,
            "message": f"Generated {len(scenes)} MV storyboard scenes",
            "data": {"storyboard": scenes, "metadata": metadata},
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "MV storyboard generation failed", "data": {}, "error": str(exc)}


def storyboard_to_text(storyboard: List[Dict[str, Any]], metadata: Dict[str, Any] | None = None) -> str:
    metadata = metadata or {}
    lines = [
        "MV STORYBOARD",
        "",
        f"Song Title: {metadata.get('song_title', 'Untitled Song')}",
        f"Genre: {metadata.get('genre', '')}",
        f"Mood: {metadata.get('mood', '')}",
        f"Vocal Direction: {metadata.get('vocal_direction', '')}",
        f"Music Preset: {metadata.get('music_preset', '')}",
        f"Generated At: {datetime.now().isoformat(timespec='seconds')}",
        "",
    ]
    for index, scene in enumerate(storyboard or [], start=1):
        lines.extend(
            [
                f"Scene {scene.get('scene_number') or scene.get('scene') or index}:",
                str(scene.get("scene_title") or f"Scene {index}"),
                "Prompt:",
                str(scene.get("visual_prompt") or scene.get("image_prompt") or ""),
                "Camera:",
                str(scene.get("camera_direction") or scene.get("camera") or ""),
                "Lighting:",
                str(scene.get("lighting") or ""),
                "Mood:",
                str(scene.get("mood") or scene.get("emotion") or ""),
                "Transition:",
                str(scene.get("transition_idea") or scene.get("transition") or ""),
                "Vertical Shorts:",
                str(scene.get("vertical_shorts_prompt") or ""),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def export_mv_storyboard(
    project_name: str,
    storyboard: List[Dict[str, Any]],
    metadata: Dict[str, Any] | None = None,
    base_dir: str | Path = "project_data/projects",
) -> Dict[str, Any]:
    try:
        project_dir = Path(base_dir) / safe_name(project_name or "project")
        export_dir = project_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        txt_path = export_dir / "mv_storyboard.txt"
        json_path = export_dir / "mv_storyboard.json"
        txt_path.write_text(storyboard_to_text(storyboard, metadata), encoding="utf-8")
        json_path.write_text(
            json.dumps({"metadata": metadata or {}, "storyboard": storyboard or []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "ok": True,
            "message": "MV storyboard exported",
            "data": {"txt_path": str(txt_path), "json_path": str(json_path)},
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "MV storyboard export failed", "data": {}, "error": str(exc)}
