"""Strict, opt-in bridge from an accepted full-song manifest to the existing FFmpeg renderer."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any, Callable

from core.full_song_mv import probe_song_audio, validate_storyboard
from core.full_song_mv_production import _digest, inspect_media
from core.render_engine import run_render
from core.render_profiles import get_render_profile


def prepare_full_song_render(project: dict[str, Any], aspect: str = "16:9") -> dict[str, Any]:
    if aspect not in {"16:9", "9:16"}:
        return {"ok": False, "error": "Choose 16:9 or 9:16.", "missing_scenes": []}
    plan = ((project.get("mv") or {}).get("full_song") or {})
    audio = plan.get("audio") or {}
    source = Path(str(audio.get("path") or ""))
    if source.suffix.lower() not in {".mp3", ".wav", ".m4a"}:
        return {"ok": False, "error": "Import a valid MP3, WAV, or M4A song.", "missing_scenes": []}
    probe = probe_song_audio(source)
    if not probe.get("ok"):
        return {"ok": False, "error": probe.get("error"), "missing_scenes": []}
    duration = float(probe["duration_seconds"])
    if abs(float(audio.get("duration_seconds") or 0) - duration) > 0.05:
        return {"ok": False, "error": "Audio changed after import.", "missing_scenes": []}
    scenes = plan.get("scenes") or []
    valid = validate_storyboard(scenes, duration)
    if not valid.get("ok"):
        return {"ok": False, "error": valid.get("error"), "missing_scenes": []}
    missing: list[dict[str, str]] = []
    timeline: list[dict[str, Any]] = []
    for scene in scenes:
        scene_id = str(scene["scene_id"])
        reasons: list[str] = []
        production = scene.get("production") or {}
        if scene.get("approval_status") != "Approved":
            reasons.append("Storyboard scene is not approved")
        assets = {str(row.get("asset_id")): row for row in production.get("assets") or []}
        selected = production.get("render_asset_ids") or [production.get("active_asset_id")]
        if not isinstance(selected, list) or not selected or any(not key for key in selected):
            reasons.append("No accepted asset selected")
            selected = []
        rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for asset_id in selected:
            row = assets.get(str(asset_id))
            if not row:
                reasons.append(f"Asset {asset_id} is missing from scene manifest")
                continue
            qc = row.get("qc_result") or {}
            if row.get("status") != "Accepted" or not qc.get("passed") or not qc.get("human_accepted"):
                reasons.append(f"Asset {asset_id} has no human-accepted QC")
            if row.get("scene_revision") != scene.get("revision") or row.get("qc_revision") != scene.get("revision"):
                reasons.append(f"Asset {asset_id} QC is stale")
            if qc.get("target_aspect_ratio", "9:16") != aspect:
                reasons.append(f"Asset {asset_id} QC targets a different aspect ratio")
            media = inspect_media(row.get("path") or "", row.get("kind") or "")
            if not media.get("ok"):
                reasons.append(f"Asset {asset_id} file is missing or unreadable")
                continue
            if abs(media["aspect_ratio"] - (16 / 9 if aspect == "16:9" else 9 / 16)) > 0.09:
                reasons.append(f"Asset {asset_id} aspect ratio changed")
            if (media["width"] < (720 if aspect == "16:9" else 480) or
                    media["height"] < (480 if aspect == "16:9" else 720)):
                reasons.append(f"Asset {asset_id} resolution is too low")
            digest = _digest(row["path"])
            if not digest or digest != qc.get("file_sha256"):
                reasons.append(f"Asset {asset_id} changed after QC")
            if row.get("provider") == "placeholder" or row.get("kind") not in {"image", "video"}:
                reasons.append(f"Asset {asset_id} is not renderable media")
            rows.append((row, media))
        if reasons:
            missing.append({"scene_id": scene_id, "reason": "; ".join(dict.fromkeys(reasons))})
            continue
        scene_duration = float(scene["duration_seconds"])
        allocations: list[float] = []
        remaining = scene_duration
        for index, (row, media) in enumerate(rows):
            last = index == len(rows) - 1
            if row["kind"] == "image":
                length = remaining if last else min(remaining, float(row.get("render_duration_seconds") or remaining / (len(rows) - index)))
            else:
                length = min(remaining, float(media["duration_seconds"]))
                if last and length < remaining:
                    if production.get("hold_last_frame") or production.get("allow_video_loop"):
                        length = remaining
                    else:
                        missing.append({"scene_id": scene_id, "reason": "Video shots are shorter than scene; add a shot/image or choose hold/loop"})
                        break
            if length <= 0:
                missing.append({"scene_id": scene_id, "reason": "Too many shots for scene duration"})
                break
            allocations.append(length)
            remaining = round(remaining - length, 6)
        if len(allocations) != len(rows) or abs(remaining) > 0.002:
            if not any(row["scene_id"] == scene_id for row in missing):
                missing.append({"scene_id": scene_id, "reason": "Shots do not cover scene duration"})
            continue
        cursor = float(scene["start_seconds"])
        for index, ((row, media), length) in enumerate(zip(rows, allocations), 1):
            mode = "trim"
            if row["kind"] == "video" and length > media["duration_seconds"] + 0.001:
                mode = "loop" if production.get("allow_video_loop") else "hold"
            timeline.append({"scene_id": f"{scene_id}_shot_{index:02d}", "parent_scene_id": scene_id,
                             "scene_revision": scene["revision"], "asset_id": row["asset_id"],
                             "asset_sha256": row["qc_result"]["file_sha256"],
                             "source_type": "video" if row["kind"] == "video" else "approved_image",
                             "source_path": row["path"], "source_duration_seconds": media["duration_seconds"],
                             "video_fill_mode": mode, "full_song_mode": True,
                             "start_time": round(cursor, 3), "duration_seconds": round(length, 3),
                             "end_time": round(cursor + length, 3), "motion_effect": "still", "transition": "none"})
            cursor += length
    if missing:
        return {"ok": False, "error": f"{len(missing)} scene(s) are not render ready.", "missing_scenes": missing}
    if not timeline or abs(timeline[-1]["end_time"] - duration) > 0.002:
        return {"ok": False, "error": "Render timeline does not cover the whole song.", "missing_scenes": []}
    return {"ok": True, "audio_path": str(source), "duration_seconds": duration,
            "aspect_ratio": aspect, "timeline": timeline, "scene_count": len(scenes), "missing_scenes": []}


def inspect_final_render(path: str | Path, duration: float, aspect: str, scale_factor: float = 1.0) -> dict[str, Any]:
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                 "format=duration,size:stream=codec_type,codec_name,width,height,duration", "-of", "json", str(path)],
                                capture_output=True, text=True, timeout=30, check=False)
        payload = json.loads(result.stdout) if result.returncode == 0 else {}
        video = next((row for row in payload.get("streams", []) if row.get("codec_type") == "video"), {})
        audio = next((row for row in payload.get("streams", []) if row.get("codec_type") == "audio"), {})
        actual_duration = float((payload.get("format") or {}).get("duration") or 0)
        audio_duration = float(audio.get("duration") or 0)
        width, height = int(video.get("width") or 0), int(video.get("height") or 0)
        expected = 16 / 9 if aspect == "16:9" else 9 / 16
        checks = {"file": Path(path).is_file(), "h264": video.get("codec_name") == "h264",
                  "aac": audio.get("codec_name") == "aac", "aspect": height > 0 and abs(width / height - expected) < 0.02,
                  "resolution": width >= round((1920 if aspect == "16:9" else 1080) * scale_factor) - 2 and
                                height >= round((1080 if aspect == "16:9" else 1920) * scale_factor) - 2,
                  "duration": math.isfinite(actual_duration) and abs(actual_duration - duration) <= 0.5,
                  "full_audio": math.isfinite(audio_duration) and abs(audio_duration - duration) <= 0.5}
        return {"ok": all(checks.values()), "checks": checks, "width": width, "height": height,
                "duration_seconds": actual_duration, "audio_duration_seconds": audio_duration,
                "size_bytes": int((payload.get("format") or {}).get("size") or 0),
                "video_codec": video.get("codec_name"), "audio_codec": audio.get("codec_name")}
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return {"ok": False, "error": "FFprobe could not inspect the rendered MP4."}


def render_full_song(project: dict[str, Any], aspect: str = "16:9", *, options: dict[str, Any] | None = None,
                     progress_callback: Callable[[int, str], None] | None = None) -> dict[str, Any]:
    ready = prepare_full_song_render(project, aspect)
    if not ready["ok"]:
        return ready
    extra = options or {}
    result = run_render(project, {**extra, "full_song_timeline": ready["timeline"],
                                  "audio_path": ready["audio_path"], "aspect_ratios": [aspect],
                                  "subtitle_mode": "none", "transition_mode": "none", "motion_style": "still",
                                  "color_grade": "none", "beat_sync": False}, progress_callback)
    if not result.get("ok") or result.get("error"):
        return {**result, "ok": False}
    output = (result.get("data", {}).get("outputs") or {}).get(aspect)
    scale = float(extra.get("scale_factor", get_render_profile(extra.get("render_profile") or "Standard")["scale_factor"]))
    qc = inspect_final_render(output or "", ready["duration_seconds"], aspect, scale)
    result["final_qc"] = qc
    if not qc.get("ok"):
        result["ok"] = False
        result["error"] = "Final MP4 failed FFprobe QC: " + ", ".join(key for key, passed in qc.get("checks", {}).items() if not passed)
    return result
