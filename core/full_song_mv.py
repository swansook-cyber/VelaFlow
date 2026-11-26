"""Local full-song MV planning. No provider calls or rendering occur here."""
from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.mv_storyboard_generator import generate_mv_storyboard


SECTION_NAMES = {"intro", "verse", "pre-chorus", "chorus", "bridge", "instrumental", "outro", "post-chorus"}
APPROVAL_STATES = {"Planned", "Approved", "Needs Revision"}


def probe_song_audio(path: str | Path, ffprobe_path: str = "ffprobe") -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        return {"ok": False, "error": "Audio file is missing. Import it again before planning."}
    try:
        result = subprocess.run(
            [ffprobe_path, "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(source)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if result.returncode:
            return {"ok": False, "error": "Audio could not be read. Use a valid MP3, WAV, or M4A file."}
        payload = json.loads(result.stdout)
        duration = float((payload.get("format") or {}).get("duration") or 0)
        has_audio = any(item.get("codec_type") == "audio" for item in payload.get("streams", []))
        if not has_audio or not math.isfinite(duration) or duration <= 0:
            return {"ok": False, "error": "The file has no playable audio or measurable duration."}
        return {"ok": True, "duration_seconds": round(duration, 3), "path": str(source.resolve()), "size_bytes": source.stat().st_size}
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return {"ok": False, "error": "Audio metadata is unavailable. Check the file and FFprobe installation."}


def _sections(lyrics: str, structure_plan: dict[str, Any] | None = None) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current = "Verse"
    found_heading = False
    for raw in str(lyrics or "").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            label = line[1:-1].strip()
            if any(name in label.lower() for name in SECTION_NAMES):
                found_heading = True
                current = label
                sections.append((current, []))
            continue
        if line and not line.startswith("("):
            if not sections:
                sections.append((current, []))
            sections[-1][1].append(line)
    if found_heading:
        return sections
    planned = (structure_plan or {}).get("sections") or []
    if planned:
        return [(str(item.get("section") or "Instrumental"), [""] * max(1, int(item.get("weight") or 1)))
                for item in planned if isinstance(item, dict)]
    return [(name, []) for name in ("Intro", "Verse 1", "Chorus", "Verse 2", "Chorus", "Bridge", "Final Chorus", "Outro")]


def _section_for_index(index: int, count: int, sections: list[tuple[str, list[str]]]) -> tuple[str, str]:
    weights = [max(1, len(lines)) for _, lines in sections]
    position = (index + 0.5) * sum(weights) / count
    cumulative = 0
    for (name, lines), weight in zip(sections, weights):
        cumulative += weight
        if position < cumulative:
            return name, lines[index % len(lines)] if lines else ""
    name, lines = sections[-1]
    return name, lines[-1] if lines else ""


def validate_storyboard(scenes: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    if not scenes or not math.isfinite(duration) or duration <= 0:
        return {"ok": False, "error": "Storyboard or audio duration is missing."}
    ids: set[str] = set()
    cursor = 0.0
    for order, scene in enumerate(scenes, start=1):
        scene_id = str(scene.get("scene_id") or "")
        start = float(scene.get("start_seconds", -1))
        end = float(scene.get("end_seconds", -1))
        if not scene_id or scene_id in ids or scene.get("scene_order") != order:
            return {"ok": False, "error": f"Scene {order} has an invalid ID or order."}
        if abs(start - cursor) > 0.002 or end <= start or abs((end - start) - float(scene.get("duration_seconds", 0))) > 0.002:
            return {"ok": False, "error": f"Scene {order} has a gap, overlap, or invalid duration."}
        if scene.get("asset_path") and not Path(str(scene["asset_path"])).is_file():
            return {"ok": False, "error": f"Scene {order} refers to a missing asset."}
        ids.add(scene_id)
        cursor = end
    if abs(cursor - duration) > 0.002:
        return {"ok": False, "error": "Storyboard does not cover the full audio duration."}
    return {"ok": True, "scene_count": len(scenes), "duration_seconds": duration}


def _reflow(scenes: list[dict[str, Any]], duration: float) -> None:
    cursor = 0.0
    for order, scene in enumerate(scenes, start=1):
        end = duration if order == len(scenes) else round(cursor + float(scene["duration_seconds"]), 3)
        scene.update(scene_order=order, scene=order, start_seconds=round(cursor, 3), end_seconds=round(end, 3), duration_seconds=round(end - cursor, 3))
        cursor = end


def _record_timeline_changes(
    before: list[dict[str, Any]], after: list[dict[str, Any]], *, already_revised: set[str] | None = None,
    explicitly_approved: set[str] | None = None,
) -> None:
    previous = {scene["scene_id"]: scene for scene in before}
    already_revised = already_revised or set()
    explicitly_approved = explicitly_approved or set()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    timing_fields = ("scene_order", "start_seconds", "end_seconds", "duration_seconds")
    for scene in after:
        old = previous[scene["scene_id"]]
        if not any(scene[field] != old[field] for field in timing_fields):
            continue
        if scene["scene_id"] not in already_revised:
            scene["revision"] = int(scene.get("revision") or 0) + 1
            scene["updated_at"] = now
        if scene.get("approval_status") == "Approved" and scene["scene_id"] not in explicitly_approved:
            scene["approval_status"] = "Needs Revision"


def create_full_song_storyboard(song: dict[str, Any], project: dict[str, Any], duration: float, scene_count: int) -> dict[str, Any]:
    if not math.isfinite(duration) or duration <= 0 or not 2 <= scene_count <= 120 or duration / scene_count < 1:
        return {"ok": False, "error": "Choose 2–120 scenes with at least one second per scene."}
    seed = generate_mv_storyboard(song, project, scene_count=10, visual_settings=(project.get("mv") or {}).get("visual_settings"))
    if not seed.get("ok"):
        return {"ok": False, "error": seed.get("error") or "Storyboard template is unavailable."}
    templates = seed["data"]["storyboard"]
    lyrics = str(song.get("normalized_song_output") or song.get("complete_lyrics") or "")
    sections = _sections(lyrics, song.get("song_structure_plan") or {})
    character = project.get("character") or {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    scenes = []
    for index in range(scene_count):
        base = templates[index % len(templates)]
        section, lyric = _section_for_index(index, scene_count, sections)
        scenes.append({
            **base, "scene_id": f"scene_{index + 1:03d}", "scene_order": index + 1,
            "song_section": section, "lyric_part": lyric,
            "scene_description": base.get("scene_title", ""),
            "character": str(character.get("name") or ""), "costume": str(character.get("outfit") or ""),
            "location": "", "visual_style": str((project.get("mv") or {}).get("visual_style") or "cinematic emotional Thai pop rock MV"),
            "reference_asset": "", "approval_status": "Planned", "asset_path": "", "asset_status": "Planned",
            "qc_status": "Pending", "retry_count": 0, "revision": 1, "updated_at": now,
            "shot_strategy": "New shot", "duration_seconds": duration / scene_count,
        })
    _reflow(scenes, duration)
    return {"ok": True, "scenes": scenes, "audio_duration_seconds": duration, "section_source": "lyrics headings or estimated structure", "validation": validate_storyboard(scenes, duration)}


def edit_scene(scenes: list[dict[str, Any]], scene_id: str, changes: dict[str, Any], duration: float) -> dict[str, Any]:
    updated = [dict(scene) for scene in scenes]
    index = next((i for i, scene in enumerate(updated) if scene.get("scene_id") == scene_id), -1)
    if index < 0:
        return {"ok": False, "error": "Scene was not found."}
    allowed = {"song_section", "scene_description", "visual_prompt", "character", "costume", "location", "visual_style", "reference_asset", "shot_strategy", "approval_status"}
    if "approval_status" in changes and changes["approval_status"] not in APPROVAL_STATES:
        return {"ok": False, "error": "Invalid approval status."}
    try:
        new_duration = float(changes.get("duration_seconds", updated[index]["duration_seconds"]))
    except (TypeError, ValueError):
        return {"ok": False, "error": "Duration must be a finite number of seconds."}
    old_duration = float(updated[index]["duration_seconds"])
    if not math.isfinite(new_duration):
        return {"ok": False, "error": "Duration must be a finite number of seconds."}
    delta = round(new_duration - old_duration, 3)
    neighbor = index + 1 if index + 1 < len(updated) else index - 1
    if new_duration < 1 or (delta and (neighbor < 0 or float(updated[neighbor]["duration_seconds"]) - delta < 1)):
        return {"ok": False, "error": "Duration needs at least one second in this scene and its neighbor."}
    for field in allowed & changes.keys():
        updated[index][field] = str(changes[field])
    if updated[index].get("approval_status") == "Approved" and "approval_status" not in changes:
        changed_content = any(str(changes[field]) != str(scenes[index].get(field, "")) for field in allowed & changes.keys()) or bool(delta)
        if changed_content:
            updated[index]["approval_status"] = "Needs Revision"
    if delta:
        updated[index]["duration_seconds"] = new_duration
        updated[neighbor]["duration_seconds"] = round(float(updated[neighbor]["duration_seconds"]) - delta, 3)
    updated[index]["revision"] = int(updated[index].get("revision") or 0) + 1
    updated[index]["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _reflow(updated, duration)
    _record_timeline_changes(
        scenes, updated, already_revised={scene_id},
        explicitly_approved={scene_id} if changes.get("approval_status") == "Approved" else set(),
    )
    validation = validate_storyboard(updated, duration)
    return {"ok": True, "scenes": updated} if validation["ok"] else validation


def move_scene(scenes: list[dict[str, Any]], scene_id: str, direction: int, duration: float) -> dict[str, Any]:
    updated = [dict(scene) for scene in scenes]
    index = next((i for i, scene in enumerate(updated) if scene.get("scene_id") == scene_id), -1)
    target = index + direction
    if index < 0 or not 0 <= target < len(updated):
        return {"ok": False, "error": "Scene cannot move further in that direction."}
    updated[index], updated[target] = updated[target], updated[index]
    _reflow(updated, duration)
    _record_timeline_changes(scenes, updated)
    return {"ok": True, "scenes": updated} if validate_storyboard(updated, duration)["ok"] else {"ok": False, "error": "Scene order could not be validated."}


def attach_approved_asset(scenes: list[dict[str, Any]], scene_id: str, asset_path: str, duration: float) -> dict[str, Any]:
    source = Path(asset_path)
    if not source.is_file():
        return {"ok": False, "error": "Approved asset is missing on disk."}
    updated = [dict(scene) for scene in scenes]
    scene = next((item for item in updated if item.get("scene_id") == scene_id), None)
    if scene is None:
        return {"ok": False, "error": "Scene was not found."}
    if scene.get("asset_path") and scene["asset_path"] != str(source):
        return {"ok": False, "error": "This scene already has an asset. Its approved file was preserved."}
    scene.update(asset_path=str(source), asset_status="Asset Ready", qc_status="Pending", revision=int(scene.get("revision") or 0) + 1,
                 updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return {"ok": True, "scenes": updated} if validate_storyboard(updated, duration)["ok"] else {"ok": False, "error": "Asset could not be attached."}
