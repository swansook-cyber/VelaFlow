from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from core.project_io import safe_name
from core.paths import workflow_project_root
from core.scene_story_engine import build_subtitle_timing
from core.ffmpeg_utils import configure_moviepy_ffmpeg, resolve_ffmpeg_path
from core.motion_engine import image_motion_filter as build_motion_filter


ASPECT_SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}


def ensure_parent_dir(path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def _clean_ffmpeg_error(output: str, fallback: str = "ffmpeg_render_failed") -> str:
    text = str(output or "").strip()
    if not text:
        return fallback
    lowered = text.lower()
    known = [
        "no such file or directory",
        "missing_ffmpeg",
        "permission denied",
        "invalid argument",
        "error opening output",
        "unable to find a suitable output format",
        "conversion failed",
    ]
    for marker in known:
        if marker in lowered:
            return marker
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return fallback
    return lines[-1][:280]


def find_ffmpeg() -> str:
    resolved = resolve_ffmpeg_path("ffmpeg")
    if resolved:
        configure_moviepy_ffmpeg(resolved)
    return resolved


def _resolve_ffprobe_path(ffmpeg_path: str = "ffmpeg") -> str:
    ffmpeg = find_ffmpeg() if not ffmpeg_path else resolve_ffmpeg_path(ffmpeg_path)
    candidates: list[str] = []
    if ffmpeg:
        ffmpeg_path_obj = Path(ffmpeg)
        suffix = ".exe" if ffmpeg_path_obj.name.lower().endswith(".exe") else ""
        candidates.append(str(ffmpeg_path_obj.with_name(f"ffprobe{suffix}")))
    candidates.extend(["ffprobe", "/usr/bin/ffprobe", "/usr/local/bin/ffprobe", "/bin/ffprobe"])
    for candidate in candidates:
        resolved = resolve_ffmpeg_path(candidate)
        if resolved and Path(resolved).name.lower().startswith("ffprobe"):
            return resolved
        try:
            proc = subprocess.run([candidate, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if proc.returncode == 0:
                return candidate
        except Exception:
            continue
    return ""


def _run_ffmpeg(args: list[str], log_path: Path) -> dict[str, Any]:
    if args:
        resolved = resolve_ffmpeg_path(args[0])
        if resolved:
            args = [resolved, *args[1:]]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write("\n$ " + " ".join(args) + "\n")
        try:
            proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            log.write(proc.stdout or "")
            return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": proc.stdout or ""}
        except FileNotFoundError as exc:
            message = f"missing_ffmpeg: {exc}"
            log.write(message + "\n")
            return {"ok": False, "returncode": -1, "output": message}
        except Exception as exc:
            message = str(exc)
            log.write(message + "\n")
            return {"ok": False, "returncode": -1, "output": message}


def probe_media(path: str | Path, *, ffmpeg_path: str = "") -> dict[str, Any]:
    media = Path(path)
    if not media.is_file():
        return {"ok": False, "path": str(media), "duration": 0.0, "file_size": 0, "playable": False, "error": "missing_media"}
    ffprobe = _resolve_ffprobe_path(ffmpeg_path or "ffmpeg")
    if not ffprobe:
        ffmpeg = resolve_ffmpeg_path(ffmpeg_path or "ffmpeg")
        if ffmpeg:
            try:
                proc = subprocess.run([ffmpeg, "-i", str(media)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=20)
                output = proc.stdout or ""
                duration = 0.0
                for line in output.splitlines():
                    if "Duration:" not in line:
                        continue
                    stamp = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
                    h, m, s = stamp.split(":")
                    duration = int(h) * 3600 + int(m) * 60 + float(s)
                    break
                return {"ok": media.stat().st_size > 0 and duration > 0, "path": str(media), "duration": duration, "file_size": media.stat().st_size, "playable": duration > 0, "error": "" if duration > 0 else "missing_ffprobe"}
            except Exception:
                pass
        return {"ok": media.stat().st_size > 0, "path": str(media), "duration": 0.0, "file_size": media.stat().st_size, "playable": media.stat().st_size > 0, "error": "missing_ffprobe"}
    try:
        proc = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(media),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        duration = float((proc.stdout or "0").strip() or 0)
        return {
            "ok": proc.returncode == 0 and media.stat().st_size > 0 and duration > 0,
            "path": str(media),
            "duration": duration,
            "file_size": media.stat().st_size,
            "playable": proc.returncode == 0 and duration > 0,
            "error": "" if proc.returncode == 0 else (proc.stderr or "ffprobe_failed"),
        }
    except Exception as exc:
        return {"ok": False, "path": str(media), "duration": 0.0, "file_size": media.stat().st_size, "playable": False, "error": str(exc)}


def validate_mp4(path: str | Path, *, min_duration: float = 1.0, ffmpeg_path: str = "") -> dict[str, Any]:
    probe = probe_media(path, ffmpeg_path=ffmpeg_path)
    probe["valid_mp4"] = bool(probe.get("ok") and float(probe.get("duration") or 0) > min_duration and int(probe.get("file_size") or 0) > 0)
    if not probe["valid_mp4"] and not probe.get("error"):
        probe["error"] = "mp4_duration_too_short"
    return probe


def _srt_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_subtitles(subtitle_timing: list[dict[str, Any]], path: str | Path) -> dict[str, Any]:
    output = ensure_parent_dir(path)
    blocks = []
    for idx, item in enumerate(subtitle_timing, start=1):
        text = str(item.get("subtitle") or "").strip() or " "
        blocks.append(f"{idx}\n{_srt_time(float(item.get('start', 0) or 0))} --> {_srt_time(float(item.get('end', 1) or 1))}\n{text}\n")
    output.write_text("\n".join(blocks), encoding="utf-8")
    return {"ok": True, "message": "Subtitles exported", "data": {"path": str(output)}, "error": ""}


def trim_audio_clip(
    source_audio_path: str | Path,
    output_path: str | Path,
    *,
    start_time: float = 0.0,
    end_time: float = 15.0,
    ffmpeg_path: str = "",
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    source = Path(source_audio_path)
    output = ensure_parent_dir(output_path)
    log = Path(log_path) if log_path else output.with_suffix(".log")
    if not source.is_file():
        return {"ok": False, "message": "Source audio missing", "data": {"path": str(output)}, "error": "missing_audio"}
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "data": {"path": str(output)}, "error": "missing_ffmpeg"}
    start = max(0.0, float(start_time or 0))
    end = max(start + 1.0, float(end_time or start + 15.0))
    duration = max(1.0, end - start)
    args = [
        ffmpeg,
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-vn",
        "-acodec",
        "libmp3lame",
        "-b:a",
        "192k",
        str(output),
    ]
    result = _run_ffmpeg(args, log)
    clean_error = _clean_ffmpeg_error(result.get("output", ""), "audio_trim_failed")
    return {
        "ok": result["ok"] and output.exists(),
        "message": "Hook audio exported" if result["ok"] else "Hook audio trim failed",
        "data": {"path": str(output), "start_time": start, "end_time": end, "duration": duration, "log_path": str(log), "ffmpeg_error_detail": clean_error},
        "error": "" if result["ok"] else clean_error,
    }


def render_placeholder_scene(
    scene: dict[str, Any],
    output_path: str | Path,
    *,
    ffmpeg_path: str = "",
    aspect_ratio: str = "9:16",
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    output = ensure_parent_dir(output_path)
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
    clean_error = _clean_ffmpeg_error(result.get("output", ""))
    return {"ok": result["ok"] and output.exists(), "message": "Scene clip rendered" if result["ok"] else "Scene clip render failed", "data": {"path": str(output), "log_path": str(log), "ffmpeg_error_detail": clean_error}, "error": "" if result["ok"] else clean_error}


def _image_motion_filter(effect: str, width: int, height: int, duration: float) -> str:
    try:
        return build_motion_filter(effect or "cinematic_drift", width, height, duration, fps=30)
    except Exception:
        pass
    frames = max(15, int(duration * 30))
    out_fade_start = max(0.1, duration - 0.35)
    effect = (effect or "slow_zoom").lower().strip()
    fade_in = 0.18
    fade_out = 0.25
    if effect in {"slow_cinematic", "cinematic_mv", "cinematic_fade", "film_fade", "dark_fade"}:
        fade_in = 0.55
        fade_out = 0.55
    fade = f"fade=t=in:st=0:d={fade_in},fade=t=out:st={max(0.1, duration - fade_out):.2f}:d={fade_out}"
    if effect in {"slow_zoom", "slow_zoom_in", "emotional_push_in", "hook_energy_zoom", "slow_cinematic", "cinematic_mv"}:
        speed = "0.0008" if effect in {"slow_cinematic", "cinematic_mv"} else "0.0018"
        max_zoom = "1.06" if effect in {"slow_cinematic", "cinematic_mv"} else "1.10"
        return (
            f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
            f"zoompan=z='min(zoom+{speed},{max_zoom})':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps=30,"
            f"trim=duration={duration:.2f},setpts=PTS-STARTPTS,{fade},format=yuv420p"
        )
    if effect in {"pan", "pan_left", "pan_right", "minimal_pan", "product_focus"}:
        direction = "-1" if effect == "pan_right" else "1"
        travel = 12 if effect == "minimal_pan" else 24 if effect == "product_focus" else 28
        return (
            f"scale={int(width * 1.16)}:{int(height * 1.16)}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}:x='(in_w-out_w)/2+{direction}*min({travel},t*7)':y='(in_h-out_h)/2',"
            f"{fade},format=yuv420p"
        )
    if effect in {"shake", "emotional_shaky_cam", "shake_zoom"}:
        intensity = 13 if effect == "shake_zoom" else 7
        return (
            f"scale={int(width * 1.10)}:{int(height * 1.10)}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}:x='(in_w-out_w)/2+sin(t*22)*{intensity}':y='(in_h-out_h)/2+cos(t*24)*{intensity}',"
            f"{fade},format=yuv420p"
        )
    if effect in {"bounce", "cartoon_pop"}:
        return (
            f"scale={int(width * 1.18)}:{int(height * 1.18)}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}:x='(in_w-out_w)/2':y='(in_h-out_h)/2+sin(t*10)*18',"
            f"{fade},format=yuv420p"
        )
    return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},{fade},format=yuv420p"


def render_image_motion_scene(
    scene: dict[str, Any],
    output_path: str | Path,
    *,
    ffmpeg_path: str = "",
    aspect_ratio: str = "9:16",
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    output = ensure_parent_dir(output_path)
    log = Path(log_path) if log_path else output.with_suffix(".log")
    image_path = Path(str(scene.get("source_image_path") or scene.get("image_path") or ""))
    if not image_path.is_file():
        return render_placeholder_scene(scene, output, ffmpeg_path=ffmpeg, aspect_ratio=aspect_ratio, log_path=log)
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "data": {"path": str(output)}, "error": "missing_ffmpeg"}
    width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])
    duration = max(0.5, float(scene.get("duration", 2.5) or 2.5))
    motion = str(scene.get("motion_effect") or scene.get("motion") or "slow_zoom")
    vf = _image_motion_filter(motion, width, height, duration)
    args = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-t",
        str(duration),
        "-vf",
        vf,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]
    result = _run_ffmpeg(args, log)
    if result["ok"] and output.exists():
        return {"ok": True, "message": "Image motion scene rendered", "data": {"path": str(output), "log_path": str(log), "source_image_path": str(image_path), "motion_effect": motion}, "error": ""}
    fallback = render_placeholder_scene(scene, output, ffmpeg_path=ffmpeg, aspect_ratio=aspect_ratio, log_path=log)
    if fallback.get("ok"):
        fallback["message"] = "Image motion failed; placeholder scene rendered"
        fallback.setdefault("data", {})["image_motion_error"] = _clean_ffmpeg_error(result.get("output", ""))
    return fallback


def combine_scene_clips_to_mp4(
    scene_clips: list[str | Path],
    output_path: str | Path,
    *,
    subtitle_path: str | Path | None = None,
    voiceover_path: str | Path | None = None,
    background_audio_path: str | Path | None = None,
    song_volume: float = 0.7,
    voiceover_volume: float = 1.0,
    ffmpeg_path: str = "",
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    output = ensure_parent_dir(output_path)
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
    concat_args = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an", str(temp_concat)]
    concat_result = _run_ffmpeg(concat_args, log)
    if not concat_result["ok"]:
        return {"ok": False, "message": "Scene concat failed", "data": {"path": str(output), "log_path": str(log)}, "error": _clean_ffmpeg_error(concat_result.get("output", ""), "scene_concat_failed")}
    input_args = [ffmpeg, "-y", "-i", str(temp_concat)]
    maps = ["-map", "0:v:0"]
    audio_args: list[str] = []
    filter_complex: list[str] = []
    audio_inputs: list[tuple[int, float]] = []
    if background_audio_path and Path(background_audio_path).is_file():
        input_args += ["-i", str(background_audio_path)]
        audio_inputs.append((len(audio_inputs) + 1, max(0.0, min(2.0, float(song_volume or 0.7)))))
    if voiceover_path and Path(voiceover_path).is_file():
        input_args += ["-i", str(voiceover_path)]
        audio_inputs.append((len(audio_inputs) + 1, max(0.0, min(2.0, float(voiceover_volume or 1.0)))))
    if len(audio_inputs) == 1:
        input_index, volume = audio_inputs[0]
        if abs(volume - 1.0) > 0.01:
            filter_complex.append(f"[{input_index}:a]volume={volume:.2f}[aout]")
            maps += ["-map", "[aout]"]
            audio_args = ["-shortest", "-c:a", "aac"]
        else:
            maps += ["-map", f"{input_index}:a:0"]
            audio_args = ["-shortest", "-c:a", "aac"]
    elif len(audio_inputs) >= 2:
        labels = []
        for idx, (input_index, volume) in enumerate(audio_inputs):
            label = f"a{idx}"
            filter_complex.append(f"[{input_index}:a]volume={volume:.2f}[{label}]")
            labels.append(f"[{label}]")
        filter_complex.append("".join(labels) + f"amix=inputs={len(labels)}:duration=shortest:dropout_transition=0[aout]")
        maps += ["-map", "[aout]"]
        audio_args = ["-shortest", "-c:a", "aac"]
    vf = ["format=yuv420p"]
    if subtitle_path and Path(subtitle_path).is_file():
        safe_srt = str(Path(subtitle_path)).replace("\\", "/").replace(":", "\\:")
        vf.insert(0, f"subtitles='{safe_srt}'")
    complex_args = ["-filter_complex", ";".join(filter_complex)] if filter_complex else []
    final_args = input_args + complex_args + maps + ["-vf", ",".join(vf), "-c:v", "libx264", "-preset", "veryfast"] + audio_args + [str(output)]
    final_result = _run_ffmpeg(final_args, log)
    subtitle_burned = bool(final_result["ok"] and subtitle_path)
    if not final_result["ok"] and subtitle_path:
        fallback_args = input_args + complex_args + maps + ["-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast"] + audio_args + [str(output)]
        final_result = _run_ffmpeg(fallback_args, log)
        subtitle_burned = False
    clean_error = _clean_ffmpeg_error(final_result.get("output", ""), "final_mp4_export_failed")
    validation = validate_mp4(output, min_duration=1.0, ffmpeg_path=ffmpeg)
    return {
        "ok": final_result["ok"] and output.exists() and validation.get("valid_mp4", False),
        "message": "Final MP4 exported" if final_result["ok"] and validation.get("valid_mp4", False) else "Final MP4 export failed",
        "data": {
            "path": str(output),
            "log_path": str(log),
            "ffmpeg_error_detail": clean_error,
            "background_audio_path": str(background_audio_path or ""),
            "voiceover_path": str(voiceover_path or ""),
            "subtitle_burned": subtitle_burned,
            "validation": validation,
            "duration": validation.get("duration", 0),
            "file_size": validation.get("file_size", 0),
        },
        "error": "" if final_result["ok"] and validation.get("valid_mp4", False) else (validation.get("error") or clean_error),
    }


def render_real_hook_clip(
    project_name: str,
    hook_package: dict[str, Any],
    *,
    workflow_type: str = "hook",
    voiceover_path: str | Path | None = None,
    background_audio_path: str | Path | None = None,
    storage_workflow_type: str = "clips",
    ffmpeg_path: str = "",
    force: bool = False,
) -> dict[str, Any]:
    try:
        project_dir = workflow_project_root(storage_workflow_type or "clips") / safe_name(project_name or "hook_clip")
        scenes_dir = project_dir / "scenes"
        exports_dir = project_dir / "exports"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        exports_dir.mkdir(parents=True, exist_ok=True)
        log_path = exports_dir / "real_clip_render_log.txt"
        scenes = hook_package.get("scene_sequence") or (hook_package.get("scene_package") or {}).get("scenes") or []
        if not scenes:
            return {"ok": False, "message": "No hook scenes available", "data": {}, "error": "missing_scenes"}
        aspect_ratio = str((hook_package.get("render_settings") or {}).get("aspect_ratio") or "9:16")
        subtitle_timing = hook_package.get("subtitle_timing") or build_subtitle_timing(scenes)
        srt_path = exports_dir / "subtitles.srt"
        write_subtitles(subtitle_timing, srt_path)
        scene_jobs = []
        scene_paths = []
        for scene in scenes:
            scene_id = str(scene.get("scene_id") or f"scene_{len(scene_paths) + 1:02d}")
            clip_path = ensure_parent_dir(scenes_dir / f"{scene_id}.mp4")
            job = {"scene_id": scene_id, "status": "pending", "path": str(clip_path), "error": ""}
            if clip_path.is_file() and not force:
                job["status"] = "completed_existing"
                scene_jobs.append(job)
                scene_paths.append(clip_path)
                continue
            result = render_image_motion_scene(scene, clip_path, ffmpeg_path=ffmpeg_path, aspect_ratio=aspect_ratio, log_path=log_path)
            scene_validation = validate_mp4(clip_path, min_duration=0.3, ffmpeg_path=ffmpeg_path or "ffmpeg")
            job["status"] = "completed" if result.get("ok") else "failed"
            job["error"] = result.get("error", "")
            job["motion_effect"] = scene.get("motion_effect") or scene.get("motion", "")
            job["source_image_path"] = scene.get("source_image_path", "")
            job["validation"] = scene_validation
            scene_jobs.append(job)
            if result.get("ok") and scene_validation.get("valid_mp4", False):
                scene_paths.append(clip_path)
        final_name = {
            "seller": "final_seller_clip.mp4",
            "podcast": "final_podcast_clip.mp4",
            "viral_clips": "final_viral_clip.mp4",
        }.get(workflow_type, "final_hook_clip.mp4")
        final_path = ensure_parent_dir(exports_dir / final_name)
        combine = combine_scene_clips_to_mp4(
            scene_paths,
            final_path,
            subtitle_path=srt_path,
            voiceover_path=voiceover_path,
            background_audio_path=background_audio_path,
            ffmpeg_path=ffmpeg_path,
            log_path=log_path,
        )
        manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "workflow_type": workflow_type,
            "scene_jobs": scene_jobs,
            "subtitle_path": str(srt_path),
            "voiceover_path": str(voiceover_path or ""),
            "background_audio_path": str(background_audio_path or ""),
            "final_mp4": str(final_path) if combine.get("ok") else "",
            "status": "completed" if combine.get("ok") else "failed",
            "error": combine.get("error", ""),
            "duration": (combine.get("data") or {}).get("duration", 0),
            "validation": (combine.get("data") or {}).get("validation", {}),
            "subtitle_burned": (combine.get("data") or {}).get("subtitle_burned", False),
        }
        manifest_path = ensure_parent_dir(exports_dir / "real_clip_manifest.json")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": bool(combine.get("ok")), "message": combine.get("message", ""), "data": {"manifest": manifest, "manifest_path": str(manifest_path), "final_mp4": str(final_path), "subtitles": str(srt_path), "scene_jobs": scene_jobs, "log_path": str(log_path), "background_audio_path": str(background_audio_path or ""), "voiceover_path": str(voiceover_path or ""), "duration": (combine.get("data") or {}).get("duration", 0), "validation": (combine.get("data") or {}).get("validation", {}), "subtitle_burned": (combine.get("data") or {}).get("subtitle_burned", False)}, "error": combine.get("error", "")}
    except Exception as exc:
        return {"ok": False, "message": "Real hook clip render failed", "data": {}, "error": str(exc)}
