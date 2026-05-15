from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project_io import safe_name
from core.paths import workflow_project_root
from core.scene_story_engine import build_subtitle_timing
from core.ffmpeg_utils import resolve_ffmpeg_path


ASPECT_SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}


def find_ffmpeg() -> str:
    return resolve_ffmpeg_path("ffmpeg")


def _run_ffmpeg(args: list[str], log_path: Path) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write("\n$ " + " ".join(args) + "\n")
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        log.write(proc.stdout or "")
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": proc.stdout or ""}


def _srt_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_subtitles(subtitle_timing: list[dict[str, Any]], path: str | Path) -> dict[str, Any]:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    for idx, item in enumerate(subtitle_timing, start=1):
        text = str(item.get("subtitle") or "").strip() or " "
        blocks.append(f"{idx}\n{_srt_time(float(item.get('start', 0) or 0))} --> {_srt_time(float(item.get('end', 1) or 1))}\n{text}\n")
    output.write_text("\n".join(blocks), encoding="utf-8")
    return {"ok": True, "message": "Subtitles exported", "data": {"path": str(output)}, "error": ""}


def render_placeholder_scene(
    scene: dict[str, Any],
    output_path: str | Path,
    *,
    ffmpeg_path: str = "",
    aspect_ratio: str = "9:16",
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    output = Path(output_path)
    log = Path(log_path) if log_path else output.with_suffix(".log")
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "data": {"path": str(output)}, "error": "missing_ffmpeg"}
    width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])
    duration = max(0.5, float(scene.get("duration", 2.5) or 2.5))
    colors = ["#15151f", "#1c2230", "#211927", "#10211f", "#221b15"]
    color = colors[(int(str(scene.get("scene_id", "1")).split("_")[-1] or 1) - 1) % len(colors)]
    args = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s={width}x{height}:r=30:d={duration}",
        "-vf",
        "format=yuv420p",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-t",
        str(duration),
        str(output),
    ]
    result = _run_ffmpeg(args, log)
    return {"ok": result["ok"] and output.exists(), "message": "Scene clip rendered" if result["ok"] else "Scene clip render failed", "data": {"path": str(output), "log_path": str(log)}, "error": "" if result["ok"] else result["output"][-1000:]}


def combine_scene_clips_to_mp4(
    scene_clips: list[str | Path],
    output_path: str | Path,
    *,
    subtitle_path: str | Path | None = None,
    voiceover_path: str | Path | None = None,
    ffmpeg_path: str = "",
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    output = Path(output_path)
    log = Path(log_path) if log_path else output.with_suffix(".log")
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "data": {"path": str(output)}, "error": "missing_ffmpeg"}
    clips = [Path(path) for path in scene_clips if Path(path).is_file()]
    if not clips:
        return {"ok": False, "message": "No scene clips available", "data": {"path": str(output)}, "error": "missing_scene_clips"}
    output.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output.parent / "scene_concat.txt"
    concat_file.write_text("\n".join(f"file '{path.as_posix()}'" for path in clips), encoding="utf-8")
    temp_concat = output.parent / f"{output.stem}_concat.mp4"
    concat_args = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(temp_concat)]
    concat_result = _run_ffmpeg(concat_args, log)
    if not concat_result["ok"]:
        return {"ok": False, "message": "Scene concat failed", "data": {"path": str(output), "log_path": str(log)}, "error": concat_result["output"][-1000:]}
    input_args = [ffmpeg, "-y", "-i", str(temp_concat)]
    maps = ["-map", "0:v:0"]
    audio_args: list[str] = []
    if voiceover_path and Path(voiceover_path).is_file():
        input_args += ["-i", str(voiceover_path)]
        maps += ["-map", "1:a:0"]
        audio_args = ["-shortest", "-c:a", "aac"]
    vf = ["format=yuv420p"]
    if subtitle_path and Path(subtitle_path).is_file():
        safe_srt = str(Path(subtitle_path)).replace("\\", "/").replace(":", "\\:")
        vf.insert(0, f"subtitles='{safe_srt}'")
    final_args = input_args + maps + ["-vf", ",".join(vf), "-c:v", "libx264", "-preset", "veryfast"] + audio_args + [str(output)]
    final_result = _run_ffmpeg(final_args, log)
    if not final_result["ok"] and subtitle_path:
        fallback_args = input_args + maps + ["-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast"] + audio_args + [str(output)]
        final_result = _run_ffmpeg(fallback_args, log)
    return {"ok": final_result["ok"] and output.exists(), "message": "Final MP4 exported" if final_result["ok"] else "Final MP4 export failed", "data": {"path": str(output), "log_path": str(log)}, "error": "" if final_result["ok"] else final_result["output"][-1000:]}


def render_real_hook_clip(
    project_name: str,
    hook_package: dict[str, Any],
    *,
    workflow_type: str = "hook",
    voiceover_path: str | Path | None = None,
    ffmpeg_path: str = "",
) -> dict[str, Any]:
    try:
        project_dir = workflow_project_root("clips") / safe_name(project_name or "hook_clip")
        scenes_dir = project_dir / "scenes"
        exports_dir = project_dir / "exports"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        exports_dir.mkdir(parents=True, exist_ok=True)
        log_path = exports_dir / "real_clip_render_log.txt"
        scenes = hook_package.get("scene_sequence") or (hook_package.get("scene_package") or {}).get("scenes") or []
        if not scenes:
            return {"ok": False, "message": "No hook scenes available", "data": {}, "error": "missing_scenes"}
        subtitle_timing = hook_package.get("subtitle_timing") or build_subtitle_timing(scenes)
        srt_path = exports_dir / "subtitles.srt"
        write_subtitles(subtitle_timing, srt_path)
        scene_jobs = []
        scene_paths = []
        for scene in scenes:
            scene_id = str(scene.get("scene_id") or f"scene_{len(scene_paths) + 1:02d}")
            clip_path = scenes_dir / f"{scene_id}.mp4"
            job = {"scene_id": scene_id, "status": "pending", "path": str(clip_path), "error": ""}
            if clip_path.is_file():
                job["status"] = "completed_existing"
                scene_jobs.append(job)
                scene_paths.append(clip_path)
                continue
            result = render_placeholder_scene(scene, clip_path, ffmpeg_path=ffmpeg_path, aspect_ratio="9:16", log_path=log_path)
            job["status"] = "completed" if result.get("ok") else "failed"
            job["error"] = result.get("error", "")
            scene_jobs.append(job)
            if result.get("ok"):
                scene_paths.append(clip_path)
        final_name = {
            "seller": "final_seller_clip.mp4",
            "podcast": "final_podcast_clip.mp4",
            "viral_clips": "final_viral_clip.mp4",
        }.get(workflow_type, "final_hook_clip.mp4")
        final_path = exports_dir / final_name
        combine = combine_scene_clips_to_mp4(scene_paths, final_path, subtitle_path=srt_path, voiceover_path=voiceover_path, ffmpeg_path=ffmpeg_path, log_path=log_path)
        manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "workflow_type": workflow_type,
            "scene_jobs": scene_jobs,
            "subtitle_path": str(srt_path),
            "voiceover_path": str(voiceover_path or ""),
            "final_mp4": str(final_path) if combine.get("ok") else "",
            "status": "completed" if combine.get("ok") else "failed",
            "error": combine.get("error", ""),
        }
        manifest_path = exports_dir / "real_clip_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": bool(combine.get("ok")), "message": combine.get("message", ""), "data": {"manifest": manifest, "manifest_path": str(manifest_path), "final_mp4": str(final_path), "subtitles": str(srt_path), "scene_jobs": scene_jobs, "log_path": str(log_path)}, "error": combine.get("error", "")}
    except Exception as exc:
        return {"ok": False, "message": "Real hook clip render failed", "data": {}, "error": str(exc)}
