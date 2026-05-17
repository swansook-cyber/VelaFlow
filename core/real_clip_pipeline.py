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
from core.subtitle_engine import generate_styled_subtitles, normalize_subtitle_timing


ASPECT_SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
STATIC_SAFE_SIZES = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (1080, 1080)}
STATIC_SAFE_SCENE_DURATION = 5.0


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
            return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": proc.stdout or "", "command": args}
        except FileNotFoundError as exc:
            message = f"missing_ffmpeg: {exc}"
            log.write(message + "\n")
            return {"ok": False, "returncode": -1, "output": message, "command": args}
        except Exception as exc:
            message = str(exc)
            log.write(message + "\n")
            return {"ok": False, "returncode": -1, "output": message, "command": args}


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
        duration_proc = subprocess.run(
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
        duration = float((duration_proc.stdout or "0").strip() or 0)
        stream_proc = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "json",
                str(media),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        stream_types: list[str] = []
        if stream_proc.returncode == 0:
            try:
                stream_payload = json.loads(stream_proc.stdout or "{}")
                stream_types = [str(item.get("codec_type", "")) for item in stream_payload.get("streams", []) if item.get("codec_type")]
            except Exception:
                stream_types = []
        return {
            "ok": duration_proc.returncode == 0 and media.stat().st_size > 0 and duration > 0,
            "path": str(media),
            "duration": duration,
            "file_size": media.stat().st_size,
            "playable": duration_proc.returncode == 0 and duration > 0,
            "stream_types": stream_types,
            "has_video": "video" in stream_types,
            "has_audio": "audio" in stream_types,
            "error": "" if duration_proc.returncode == 0 else (duration_proc.stderr or "ffprobe_failed"),
        }
    except Exception as exc:
        return {"ok": False, "path": str(media), "duration": 0.0, "file_size": media.stat().st_size, "playable": False, "error": str(exc)}


def validate_mp4(path: str | Path, *, min_duration: float = 1.0, min_file_size: int = 1, require_audio: bool = False, ffmpeg_path: str = "") -> dict[str, Any]:
    probe = probe_media(path, ffmpeg_path=ffmpeg_path)
    probe["min_file_size"] = min_file_size
    probe["require_audio"] = require_audio
    probe["valid_mp4"] = bool(
        probe.get("ok")
        and float(probe.get("duration") or 0) > min_duration
        and int(probe.get("file_size") or 0) >= min_file_size
        and probe.get("has_video", True)
        and (not require_audio or probe.get("has_audio", False))
    )
    if not probe["valid_mp4"] and not probe.get("error"):
        probe["error"] = "mp4_missing_required_stream_or_too_short"
    return probe


def _write_render_stage(exports_dir: Path, stage: dict[str, Any]) -> Path:
    path = ensure_parent_dir(exports_dir / "render_stage.json")
    path.write_text(json.dumps(stage, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _media_duration(path: str | Path | None, *, ffmpeg_path: str = "") -> float:
    if not path or not Path(path).is_file():
        return 0.0
    return max(0.0, float(probe_media(path, ffmpeg_path=ffmpeg_path).get("duration") or 0.0))


def _ffmpeg_subtitle_path(path: str | Path) -> str:
    value = str(Path(path).resolve()).replace("\\", "/")
    if len(value) > 1 and value[1] == ":":
        value = value[0] + r"\:" + value[2:]
    return value.replace("'", r"\'")


def _srt_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_subtitles(subtitle_timing: list[dict[str, Any]], path: str | Path, *, total_duration: float = 0.0) -> dict[str, Any]:
    output = ensure_parent_dir(path)
    if total_duration:
        subtitle_timing = normalize_subtitle_timing(subtitle_timing, total_duration)
    blocks = []
    for idx, item in enumerate(subtitle_timing, start=1):
        text = str(item.get("subtitle") or item.get("text") or "").strip() or " "
        blocks.append(f"{idx}\n{_srt_time(float(item.get('start', 0) or 0))} --> {_srt_time(float(item.get('end', 1) or 1))}\n{text}\n")
    output.write_text("\n".join(blocks), encoding="utf-8-sig")
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
    args = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={width}x{height}:rate=30:duration={duration}",
        "-vf",
        "format=yuv420p",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-r",
        "30",
        "-b:v",
        "2500k",
        "-movflags",
        "+faststart",
        "-t",
        str(duration),
        str(output),
    ]
    result = _run_ffmpeg(args, log)
    clean_error = _clean_ffmpeg_error(result.get("output", ""))
    validation = validate_mp4(output, min_duration=0.3, min_file_size=1, ffmpeg_path=ffmpeg)
    return {
        "ok": result["ok"] and output.exists() and validation.get("playable", False),
        "message": "Scene clip rendered" if result["ok"] else "Scene clip render failed",
        "data": {
            "path": str(output),
            "log_path": str(log),
            "ffmpeg_error_detail": clean_error,
            "render_mode_used": "placeholder_testsrc",
            "ffmpeg_command": result.get("command", args),
            "ffmpeg_return_code": result.get("returncode", -1),
            "scene_validation_ok": bool(validation.get("playable")),
            "validation": validation,
        },
        "error": "" if result["ok"] else clean_error,
    }


def _replace_if_valid(temp_path: Path, output_path: Path, validation: dict[str, Any]) -> None:
    if validation.get("valid_mp4"):
        output_path.unlink(missing_ok=True)
        temp_path.replace(output_path)
    else:
        temp_path.unlink(missing_ok=True)


def _safe_static_image_scene(
    image_path: Path,
    output_path: Path,
    *,
    ffmpeg: str,
    width: int,
    height: int,
    duration: float,
    log_path: Path,
) -> dict[str, Any]:
    temp_output = output_path.with_name(f"{output_path.stem}_static_tmp.mp4")
    temp_output.unlink(missing_ok=True)
    args = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-t",
        f"{duration:.3f}",
        "-r",
        "30",
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-g",
        "15",
        "-keyint_min",
        "15",
        "-sc_threshold",
        "0",
        "-b:v",
        "4000k",
        "-minrate",
        "4000k",
        "-maxrate",
        "4000k",
        "-bufsize",
        "8000k",
        "-x264-params",
        "nal-hrd=cbr:force-cfr=1",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-shortest",
        str(temp_output),
    ]
    result = _run_ffmpeg(args, log_path)
    validation = validate_mp4(temp_output, min_duration=1.0, min_file_size=100 * 1024, ffmpeg_path=ffmpeg)
    _replace_if_valid(temp_output, output_path, validation)
    return {
        "ok": result.get("ok") and output_path.is_file() and validation.get("valid_mp4", False),
        "message": "Static image scene rendered" if validation.get("valid_mp4") else "Static image scene render failed",
        "data": {
            "path": str(output_path),
            "log_path": str(log_path),
            "render_mode_used": "static_safe",
            "ffmpeg_command": result.get("command", args),
            "ffmpeg_return_code": result.get("returncode", -1),
            "scene_validation_ok": bool(validation.get("valid_mp4")),
            "validation": validation,
        },
        "error": "" if validation.get("valid_mp4") else (validation.get("error") or _clean_ffmpeg_error(result.get("output", ""), "static_scene_render_failed")),
    }


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
    output.unlink(missing_ok=True)
    log = Path(log_path) if log_path else output.with_suffix(".log")
    image_path = Path(str(scene.get("source_image_path") or scene.get("image_path") or ""))
    if not image_path.is_file():
        return render_placeholder_scene(scene, output, ffmpeg_path=ffmpeg, aspect_ratio=aspect_ratio, log_path=log)
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "data": {"path": str(output)}, "error": "missing_ffmpeg"}
    requested_mode = str(scene.get("render_mode") or scene.get("render_mode_used") or "static_safe").strip().lower()
    if requested_mode not in {"motion", "cinematic_motion"}:
        width, height = STATIC_SAFE_SIZES.get(aspect_ratio, STATIC_SAFE_SIZES["9:16"])
        return _safe_static_image_scene(
            image_path,
            output,
            ffmpeg=ffmpeg,
            width=width,
            height=height,
            duration=STATIC_SAFE_SCENE_DURATION,
            log_path=log,
        )
    width, height = ASPECT_SIZES.get(aspect_ratio, ASPECT_SIZES["9:16"])
    duration = max(1.2, float(scene.get("duration", 2.5) or 2.5))
    motion = str(scene.get("motion_effect") or scene.get("motion") or "slow_zoom")
    vf = _image_motion_filter(motion, width, height, duration)
    temp_output = output.with_name(f"{output.stem}_motion_tmp.mp4")
    temp_output.unlink(missing_ok=True)
    args = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-framerate",
        "30",
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
        "-r",
        "30",
        "-b:v",
        "2500k",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-shortest",
        str(temp_output),
    ]
    result = _run_ffmpeg(args, log)
    validation = validate_mp4(temp_output, min_duration=1.0, min_file_size=100 * 1024, ffmpeg_path=ffmpeg)
    if result["ok"] and validation.get("valid_mp4", False):
        _replace_if_valid(temp_output, output, validation)
        return {
            "ok": True,
            "message": "Image motion scene rendered",
            "data": {
                "path": str(output),
                "log_path": str(log),
                "source_image_path": str(image_path),
                "motion_effect": motion,
                "render_mode_used": "motion",
                "ffmpeg_command": result.get("command", args),
                "ffmpeg_return_code": result.get("returncode", -1),
                "scene_validation_ok": True,
                "validation": validation,
            },
            "error": "",
        }
    temp_output.unlink(missing_ok=True)
    fallback_width, fallback_height = STATIC_SAFE_SIZES.get(aspect_ratio, STATIC_SAFE_SIZES["9:16"])
    fallback = _safe_static_image_scene(image_path, output, ffmpeg=ffmpeg, width=fallback_width, height=fallback_height, duration=STATIC_SAFE_SCENE_DURATION, log_path=log)
    fallback.setdefault("data", {})["image_motion_error"] = _clean_ffmpeg_error(result.get("output", ""))
    fallback.setdefault("data", {})["motion_ffmpeg_command"] = result.get("command", args)
    fallback.setdefault("data", {})["motion_ffmpeg_return_code"] = result.get("returncode", -1)
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
    concat_duration = _media_duration(temp_concat, ffmpeg_path=ffmpeg)
    hook_audio_duration = _media_duration(background_audio_path, ffmpeg_path=ffmpeg)
    voiceover_duration = _media_duration(voiceover_path, ffmpeg_path=ffmpeg)
    target_duration = hook_audio_duration or min(concat_duration, voiceover_duration) if voiceover_duration else concat_duration
    target_duration = max(1.0, float(target_duration or concat_duration or 1.0))
    input_args = [ffmpeg, "-y"]
    if target_duration > concat_duration + 0.1:
        input_args += ["-stream_loop", "-1"]
    input_args += ["-i", str(temp_concat)]
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
    audio_source = "provided" if audio_inputs else "silent"
    if not audio_inputs:
        input_args += ["-f", "lavfi", "-t", f"{target_duration:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        audio_inputs.append((1, 1.0))
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
        safe_subtitle = _ffmpeg_subtitle_path(subtitle_path)
        vf.insert(0, f"subtitles='{safe_subtitle}':charenc=UTF-8:force_style='Fontname=Arial,Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H7F000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=105'")
    complex_args = ["-filter_complex", ";".join(filter_complex)] if filter_complex else []
    final_args = input_args + complex_args + maps + ["-t", f"{target_duration:.3f}", "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart"] + audio_args + [str(output)]
    final_result = _run_ffmpeg(final_args, log)
    subtitle_burned = bool(final_result["ok"] and subtitle_path)
    if not final_result["ok"] and subtitle_path:
        fallback_args = input_args + complex_args + maps + ["-t", f"{target_duration:.3f}", "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart"] + audio_args + [str(output)]
        final_result = _run_ffmpeg(fallback_args, log)
        subtitle_burned = False
    clean_error = _clean_ffmpeg_error(final_result.get("output", ""), "final_mp4_export_failed")
    validation = validate_mp4(output, min_duration=1.0, require_audio=True, ffmpeg_path=ffmpeg)
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
            "subtitle_status": "burned" if subtitle_burned else ("exported_only" if subtitle_path else "none"),
            "audio_attached": bool(audio_inputs),
            "audio_source": audio_source,
            "audio_sync_status": "matched_hook_audio" if hook_audio_duration else ("silent_audio" if audio_source == "silent" else "matched_video"),
            "target_duration": target_duration,
            "hook_audio_duration": hook_audio_duration,
            "source_video_duration": concat_duration,
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
        hook_audio_duration = _media_duration(background_audio_path, ffmpeg_path=ffmpeg_path or "ffmpeg")
        scene_total_duration = sum(max(0.5, float(scene.get("duration", STATIC_SAFE_SCENE_DURATION) or STATIC_SAFE_SCENE_DURATION)) for scene in scenes)
        final_target_duration = hook_audio_duration or scene_total_duration or STATIC_SAFE_SCENE_DURATION * len(scenes)
        subtitle_timing = normalize_subtitle_timing(subtitle_timing, final_target_duration)
        srt_path = exports_dir / "subtitles.srt"
        write_subtitles(subtitle_timing, srt_path, total_duration=final_target_duration)
        subtitle_style = str(hook_package.get("subtitle_animation") or hook_package.get("subtitle_style") or "")
        preset_id = str((hook_package.get("creator_outcome_preset") or {}).get("preset_id") or "")
        styled_subtitle = generate_styled_subtitles(subtitle_timing, exports_dir, preset_id=preset_id, subtitle_style=subtitle_style)
        ass_path = Path(str((styled_subtitle.get("data") or {}).get("ass") or ""))
        burn_subtitle_path = ass_path if ass_path.is_file() else srt_path
        render_stage = {
            "render_mode_used": "cinematic_motion",
            "scene_render_ok": False,
            "combine_ok": False,
            "audio_attach_ok": False,
            "subtitle_ok": bool(srt_path.is_file()),
            "final_mp4_ok": False,
            "final_mp4_path": "",
            "safe_error_message": "",
            "subtitle_burned": False,
            "subtitle_status": "exported",
            "subtitle_path": str(srt_path),
            "styled_subtitle_path": str(ass_path) if ass_path.is_file() else "",
            "audio_sync_status": "",
            "target_duration": final_target_duration,
            "hook_audio_duration": hook_audio_duration,
            "scene_count": len(scenes),
            "completed_scene_count": 0,
            "ffmpeg_return_code": -1,
            "scene_jobs": [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        scene_jobs = []
        scene_paths = []
        for scene in scenes:
            scene_id = str(scene.get("scene_id") or f"scene_{len(scene_paths) + 1:02d}")
            clip_path = ensure_parent_dir(scenes_dir / f"{scene_id}.mp4")
            job = {"scene_id": scene_id, "status": "pending", "path": str(clip_path), "error": ""}
            if clip_path.is_file() and not force:
                scene_validation = validate_mp4(clip_path, min_duration=1.0, min_file_size=100 * 1024, ffmpeg_path=ffmpeg_path or "ffmpeg")
                if scene_validation.get("valid_mp4", False):
                    job["status"] = "completed_existing"
                    job["validation"] = scene_validation
                    job["scene_validation_ok"] = True
                    job["render_mode_used"] = "existing_valid_scene"
                    job["ffmpeg_command"] = ["existing_valid_scene", str(clip_path)]
                    job["ffmpeg_return_code"] = 0
                    scene_jobs.append(job)
                    scene_paths.append(clip_path)
                    continue
                clip_path.unlink(missing_ok=True)
            result = render_image_motion_scene(scene, clip_path, ffmpeg_path=ffmpeg_path, aspect_ratio=aspect_ratio, log_path=log_path)
            scene_validation = validate_mp4(clip_path, min_duration=1.0, min_file_size=100 * 1024, ffmpeg_path=ffmpeg_path or "ffmpeg")
            job["status"] = "completed" if result.get("ok") else "failed"
            job["error"] = result.get("error", "")
            job["motion_effect"] = scene.get("motion_effect") or scene.get("motion", "")
            job["source_image_path"] = scene.get("source_image_path", "")
            job["render_mode_used"] = (result.get("data") or {}).get("render_mode_used", "")
            job["ffmpeg_command"] = (result.get("data") or {}).get("ffmpeg_command", [])
            job["ffmpeg_return_code"] = (result.get("data") or {}).get("ffmpeg_return_code", -1)
            job["scene_validation_ok"] = bool(scene_validation.get("valid_mp4"))
            job["validation"] = scene_validation
            scene_jobs.append(job)
            if result.get("ok") and scene_validation.get("valid_mp4", False):
                scene_paths.append(clip_path)
        render_stage["completed_scene_count"] = len(scene_paths)
        render_stage["scene_render_ok"] = bool(scene_paths) and len(scene_paths) == len(scenes)
        render_stage["scene_jobs"] = scene_jobs
        render_stage["render_mode_used"] = "cinematic_motion" if any(str(job.get("render_mode_used")) == "motion" for job in scene_jobs) else "static_safe"
        render_stage["ffmpeg_return_code"] = next((int(job.get("ffmpeg_return_code", -1)) for job in reversed(scene_jobs) if "ffmpeg_return_code" in job), -1)
        final_name = {
            "seller": "final_seller_clip.mp4",
            "podcast": "final_podcast_clip.mp4",
            "viral_clips": "final_viral_clip.mp4",
        }.get(workflow_type, "final_hook_clip.mp4")
        final_path = ensure_parent_dir(exports_dir / final_name)
        if not render_stage["scene_render_ok"]:
            render_stage.update(
                {
                    "combine_ok": False,
                    "audio_attach_ok": False,
                    "subtitle_ok": bool(srt_path.is_file()),
                    "subtitle_status": "exported_only",
                    "final_mp4_ok": False,
                    "final_mp4_path": "",
                    "safe_error_message": "Render failed: scene video could not be created",
                    "validation": {},
                }
            )
            render_stage_path = _write_render_stage(exports_dir, render_stage)
            manifest = {
                "generated_by": "VelaFlow",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "project_name": project_name,
                "workflow_type": workflow_type,
                "scene_jobs": scene_jobs,
                "subtitle_path": str(srt_path),
                "voiceover_path": str(voiceover_path or ""),
                "background_audio_path": str(background_audio_path or ""),
                "final_mp4": "",
                "status": "failed",
                "error": "scene_video_render_failed",
                "duration": 0,
                "validation": {},
                "subtitle_burned": False,
                "render_stage_path": str(render_stage_path),
                "render_stage": render_stage,
            }
            manifest_path = ensure_parent_dir(exports_dir / "real_clip_manifest.json")
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            return {
                "ok": False,
                "message": "Scene video render failed",
                "data": {
                    "manifest": manifest,
                    "manifest_path": str(manifest_path),
                    "render_stage_path": str(render_stage_path),
                    "render_stage": render_stage,
                    "final_mp4": "",
                    "subtitles": str(srt_path),
                    "scene_jobs": scene_jobs,
                    "log_path": str(log_path),
                    "background_audio_path": str(background_audio_path or ""),
                    "voiceover_path": str(voiceover_path or ""),
                    "duration": 0,
                    "validation": {},
                    "subtitle_burned": False,
                    "audio_attached": False,
                },
                "error": "scene_video_render_failed",
            }
        combine = combine_scene_clips_to_mp4(
            scene_paths,
            final_path,
            subtitle_path=burn_subtitle_path,
            voiceover_path=voiceover_path,
            background_audio_path=background_audio_path,
            ffmpeg_path=ffmpeg_path,
            log_path=log_path,
        )
        combine_data = combine.get("data") or {}
        final_validation = combine_data.get("validation") or validate_mp4(final_path, ffmpeg_path=ffmpeg_path or "ffmpeg")
        render_stage.update(
            {
                "combine_ok": bool(combine.get("ok")),
                "audio_attach_ok": bool(combine_data.get("audio_attached")) if (background_audio_path or voiceover_path) else True,
                "subtitle_ok": bool(srt_path.is_file()),
                "subtitle_burned": bool(combine_data.get("subtitle_burned")),
                "subtitle_status": combine_data.get("subtitle_status", "exported_only"),
                "audio_sync_status": combine_data.get("audio_sync_status", ""),
                "target_duration": combine_data.get("target_duration", final_target_duration),
                "hook_audio_duration": combine_data.get("hook_audio_duration", hook_audio_duration),
                "final_mp4_ok": bool(final_validation.get("valid_mp4", False)),
                "final_mp4_path": str(final_path) if final_path.is_file() else "",
                "safe_error_message": "" if combine.get("ok") else (combine.get("error") or "Final MP4 render failed"),
                "ffmpeg_return_code": 0 if combine.get("ok") else render_stage.get("ffmpeg_return_code", -1),
                "validation": final_validation,
            }
        )
        render_stage_path = _write_render_stage(exports_dir, render_stage)
        manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "workflow_type": workflow_type,
            "scene_jobs": scene_jobs,
            "subtitle_path": str(srt_path),
            "styled_subtitle_path": str(ass_path) if ass_path.is_file() else "",
            "voiceover_path": str(voiceover_path or ""),
            "background_audio_path": str(background_audio_path or ""),
            "final_mp4": str(final_path) if combine.get("ok") else "",
            "status": "completed" if combine.get("ok") else "failed",
            "error": combine.get("error", ""),
            "duration": (combine.get("data") or {}).get("duration", 0),
            "validation": (combine.get("data") or {}).get("validation", {}),
            "subtitle_burned": (combine.get("data") or {}).get("subtitle_burned", False),
            "subtitle_status": (combine.get("data") or {}).get("subtitle_status", "exported_only"),
            "audio_sync_status": (combine.get("data") or {}).get("audio_sync_status", ""),
            "render_stage_path": str(render_stage_path),
            "render_stage": render_stage,
        }
        manifest_path = ensure_parent_dir(exports_dir / "real_clip_manifest.json")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": bool(combine.get("ok")), "message": combine.get("message", ""), "data": {"manifest": manifest, "manifest_path": str(manifest_path), "render_stage_path": str(render_stage_path), "render_stage": render_stage, "final_mp4": str(final_path), "subtitles": str(srt_path), "styled_subtitles": str(ass_path) if ass_path.is_file() else "", "scene_jobs": scene_jobs, "log_path": str(log_path), "background_audio_path": str(background_audio_path or ""), "voiceover_path": str(voiceover_path or ""), "duration": (combine.get("data") or {}).get("duration", 0), "validation": (combine.get("data") or {}).get("validation", {}), "subtitle_burned": (combine.get("data") or {}).get("subtitle_burned", False), "subtitle_status": (combine.get("data") or {}).get("subtitle_status", "exported_only"), "audio_sync_status": (combine.get("data") or {}).get("audio_sync_status", ""), "audio_attached": (combine.get("data") or {}).get("audio_attached", False)}, "error": combine.get("error", "")}
    except Exception as exc:
        return {"ok": False, "message": "Real hook clip render failed", "data": {}, "error": str(exc)}
