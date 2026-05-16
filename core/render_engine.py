import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List

from core.ffmpeg_utils import ASPECT_RATIOS, append_log, ffmpeg_available, normalize_scene_filter, run_ffmpeg, safe_concat_line
from core.audio_analysis import analyze_audio
from core.color_pipeline import color_grade_filter
from core.motion_engine import image_motion_filter
from core.render_manifest import create_manifest, new_render_id, render_folder, save_manifest, update_manifest, write_assets_used
from core.render_profiles import get_render_profile
from core.render_recovery import mark_scene_failed, mark_scene_rendered, save_render_state
from core.subtitle_engine import generate_subtitles
from core.timeline_builder import build_timeline
from core.transition_engine import scene_transition_filter


ProgressCallback = Callable[[int, str], None]
ROOT = Path(__file__).resolve().parents[1]


def _progress(callback: ProgressCallback | None, value: int, message: str) -> None:
    if callback:
        callback(max(0, min(100, int(value))), message)


def _ass_filter_path(path: str | Path) -> str:
    value = str(Path(path).resolve()).replace("\\", "/")
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    return value


def _scene_cache_key(item: Dict[str, Any], aspect: str, width: int, height: int, fps: int, profile: Dict[str, Any]) -> str:
    source_path = Path(item.get("source_path", ""))
    stat_payload: Dict[str, Any] = {"exists": source_path.exists()}
    if source_path.exists():
        stat = source_path.stat()
        stat_payload.update({"path": str(source_path.resolve()), "size": stat.st_size, "mtime": int(stat.st_mtime)})
    payload = {
        "source": stat_payload,
        "source_type": item.get("source_type", ""),
        "scene_id": item.get("scene_id", ""),
        "duration_seconds": item.get("duration_seconds", 0),
        "motion_effect": item.get("motion_effect", ""),
        "aspect": aspect,
        "width": width,
        "height": height,
        "fps": fps,
        "profile": {
            "name": profile.get("name", ""),
            "crf": profile.get("crf", 23),
            "preset": profile.get("preset", "medium"),
            "scale_factor": profile.get("scale_factor", 1.0),
            "color_grade": profile.get("color_grade", "none"),
            "transition_mode": item.get("transition", ""),
            "audio_reactive_strength": item.get("audio_reactive_strength", 0),
        },
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _render_scene_clip(
    ffmpeg_path: str,
    item: Dict[str, Any],
    aspect: str,
    scene_output: Path,
    log_path: Path,
    fps: int = 30,
    profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    profile = profile or get_render_profile("Standard")
    spec = ASPECT_RATIOS[aspect]
    scale_factor = float(profile.get("scale_factor", 1.0) or 1.0)
    width = max(2, int(int(spec["width"]) * scale_factor) // 2 * 2)
    height = max(2, int(int(spec["height"]) * scale_factor) // 2 * 2)
    source_path = Path(item.get("source_path", ""))
    duration = max(1.0, float(item.get("duration_seconds", 1) or 1))
    source_type = item.get("source_type", "placeholder")
    color_filter = color_grade_filter(profile.get("color_grade", "none"))
    transition_filter = scene_transition_filter(item.get("transition", profile.get("transition_mode", "none")), duration)
    cache_key = _scene_cache_key(item, aspect, width, height, fps, profile)
    shared_cache_dir = ROOT / "outputs" / "renders" / "_scene_cache" / aspect.replace(":", "x")
    shared_cache_dir.mkdir(parents=True, exist_ok=True)
    shared_cache_path = shared_cache_dir / f"{cache_key}.mp4"
    scene_meta = scene_output.with_suffix(".json")

    if scene_output.exists() and scene_meta.exists():
        try:
            metadata = json.loads(scene_meta.read_text(encoding="utf-8"))
            if metadata.get("cache_key") == cache_key:
                append_log(log_path, f"[CACHE] Scene {item.get('scene_id')} {aspect} unchanged; using render-local cache")
                return {"ok": True, "message": "Scene clip cache hit", "data": {"path": str(scene_output), "command": [], "cache": "local"}, "error": ""}
        except Exception:
            pass

    if shared_cache_path.exists():
        scene_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(shared_cache_path, scene_output)
        scene_meta.write_text(json.dumps({"cache_key": cache_key, "source": str(source_path), "shared_cache": str(shared_cache_path)}, ensure_ascii=False, indent=2), encoding="utf-8")
        append_log(log_path, f"[CACHE] Scene {item.get('scene_id')} {aspect} reused from shared cache")
        return {"ok": True, "message": "Scene clip reused from shared cache", "data": {"path": str(scene_output), "command": [], "cache": "shared"}, "error": ""}

    scene_output.parent.mkdir(parents=True, exist_ok=True)
    if source_type == "video" and source_path.is_file():
        vf_parts = [normalize_scene_filter(width, height, fps)]
        if color_filter:
            vf_parts.append(color_filter)
        if transition_filter:
            vf_parts.append(transition_filter)
        vf = ",".join(vf_parts)
        command = [
            ffmpeg_path,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(source_path),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            str(profile.get("preset", "medium")),
            "-crf",
            str(profile.get("crf", 23)),
            "-pix_fmt",
            "yuv420p",
            "-frames:v",
            str(max(1, int(duration * fps))),
            str(scene_output),
        ]
    else:
        vf_parts = [image_motion_filter(item.get("motion_effect", "cinematic_drift"), width, height, duration, fps)]
        if color_filter:
            vf_parts.append(color_filter)
        if transition_filter:
            vf_parts.append(transition_filter)
        vf = ",".join(vf_parts)
        command = [
            ffmpeg_path,
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(fps),
            "-t",
            f"{duration:.3f}",
            "-i",
            str(source_path),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            str(profile.get("preset", "medium")),
            "-crf",
            str(profile.get("crf", 23)),
            "-pix_fmt",
            "yuv420p",
            "-frames:v",
            str(max(1, int(duration * fps))),
            str(scene_output),
        ]

    result = run_ffmpeg(command, log_path)
    if result["ok"] and scene_output.exists():
        shutil.copy2(scene_output, shared_cache_path)
        scene_meta.write_text(json.dumps({"cache_key": cache_key, "source": str(source_path), "shared_cache": str(shared_cache_path)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": result["ok"],
        "message": "Scene clip rendered" if result["ok"] else "Scene clip failed",
        "data": {"path": str(scene_output), "command": result["command"], "returncode": result["returncode"], "cache_key": cache_key},
        "error": result["error"],
    }


def _concat_scene_clips(
    ffmpeg_path: str,
    clip_paths: List[Path],
    aspect: str,
    render_dir: Path,
    log_path: Path,
    audio_path: str = "",
    ass_path: str = "",
    profile: Dict[str, Any] | None = None,
    total_duration: float = 0.0,
) -> Dict[str, Any]:
    profile = profile or get_render_profile("Standard")
    spec = ASPECT_RATIOS[aspect]
    output_path = render_dir / spec["filename"]
    concat_path = render_dir / "temp" / f"concat_{aspect.replace(':', 'x')}.txt"
    concat_path.write_text("\n".join(safe_concat_line(path) for path in clip_paths), encoding="utf-8")
    temp_concat = render_dir / "temp" / f"joined_{aspect.replace(':', 'x')}.mp4"

    concat_command = [ffmpeg_path, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(temp_concat)]
    concat_result = run_ffmpeg(concat_command, log_path)
    if not concat_result["ok"]:
        return {"ok": False, "message": "Concat failed", "data": {"command": concat_result["command"]}, "error": concat_result["error"]}

    has_audio = bool(audio_path and Path(audio_path).is_file())
    command: List[str] = [ffmpeg_path, "-y"]
    if has_audio:
        command += ["-stream_loop", "-1"]
    command += ["-i", str(temp_concat)]
    if has_audio:
        command += ["-i", audio_path]
    vf_parts = []
    if ass_path and Path(ass_path).is_file():
        vf_parts.append(f"ass='{_ass_filter_path(ass_path)}'")
    if vf_parts:
        command += ["-vf", ",".join(vf_parts)]
    if has_audio:
        command += ["-map", "0:v:0", "-map", "1:a:0", "-shortest", "-c:a", "aac"]
        fade_seconds = float(profile.get("audio_fade_seconds", 0) or 0)
        if fade_seconds > 0:
            out_start = max(0.0, float(total_duration or 0) - fade_seconds)
            command += ["-af", f"afade=t=in:st=0:d={fade_seconds:.3f},afade=t=out:st={out_start:.3f}:d={fade_seconds:.3f}"]
    else:
        command += ["-an"]
    command += ["-c:v", "libx264", "-preset", str(profile.get("preset", "medium")), "-crf", str(profile.get("crf", 23)), "-pix_fmt", "yuv420p", str(output_path)]

    final_result = run_ffmpeg(command, log_path)
    return {
        "ok": final_result["ok"],
        "message": "Final render complete" if final_result["ok"] else "Final render failed",
        "data": {"path": str(output_path), "command": final_result["command"]},
        "error": final_result["error"],
    }


def run_render(
    project: Dict[str, Any],
    options: Dict[str, Any] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> Dict[str, Any]:
    options = options or {}
    selected_aspects = [aspect for aspect in options.get("aspect_ratios", ["16:9"]) if aspect in ASPECT_RATIOS] or ["16:9"]
    profile = get_render_profile(options.get("render_profile") or options.get("profile") or "Standard")
    render_id = options.get("render_id") or new_render_id()
    render_dir = render_folder(project.get("title", "project"), render_id, options.get("base_dir"))
    log_path = render_dir / "render_log.txt"
    ffmpeg_path = options.get("ffmpeg_path", "ffmpeg")
    audio_path = options.get("audio_path") or (project.get("assets", {}) or {}).get("audio_path", "")
    subtitle_mode = options.get("subtitle_mode") or profile.get("subtitle_mode", "simple")
    transition_mode = options.get("transition_mode") or profile.get("transition_mode", "none")
    motion_style = options.get("motion_style") or profile.get("motion_style", "auto")
    color_grade = options.get("color_grade") or profile.get("color_grade", "none")
    beat_sync = bool(options.get("beat_sync", profile.get("beat_sync", False)))
    fps = int(options.get("fps", profile.get("fps", 30)) or 30)
    profile["color_grade"] = color_grade
    profile["transition_mode"] = transition_mode

    append_log(log_path, f"[INFO] Render {render_id} started")
    save_render_state(render_dir, {"render_id": render_id, "status": "RUNNING", "completed_scenes": [], "failed_scenes": [], "resume_enabled": bool(options.get("resume", True))})
    manifest = create_manifest(project, render_id, selected_aspects, audio_path, subtitle_mode, transition_mode, motion_style)
    manifest["render_profile"] = profile
    manifest["color_grade"] = color_grade
    manifest["beat_sync"] = beat_sync
    save_manifest(manifest, render_dir)
    _progress(progress_callback, 3, "Building timeline")
    try:
        beat_map = analyze_audio(audio_path, ffmpeg_path, render_dir) if audio_path else {"ok": False, "data": {"beats": []}, "error": "no audio"}
        timeline_data = build_timeline(project, render_dir, motion_style, beat_map=beat_map, beat_sync=beat_sync)
        timeline = timeline_data.get("items", [])
        write_assets_used(render_dir, timeline, project)
        subtitle_result = generate_subtitles(timeline, render_dir, subtitle_mode)
        ass_path = subtitle_result.get("data", {}).get("ass", "") if subtitle_result.get("ok") else ""
    except Exception as error:
        message = f"Render preparation failed: {error}"
        append_log(log_path, f"[ERROR] {message}")
        update_manifest(render_dir, render_status="FAILED", errors=[message])
        save_render_state(render_dir, {"render_id": render_id, "status": "FAILED", "error": message})
        return {"ok": False, "message": "Render failed during preparation", "data": {"render_id": render_id, "render_dir": str(render_dir)}, "error": message}

    if not ffmpeg_available(ffmpeg_path):
        message = "ffmpeg is not available; manifest, timeline, subtitles, and assets log were created."
        append_log(log_path, f"[WARN] {message}")
        update_manifest(render_dir, render_status="FAILED", errors=[message])
        return {"ok": False, "message": message, "data": {"render_id": render_id, "render_dir": str(render_dir)}, "error": message}

    outputs: Dict[str, str] = {}
    errors: List[str] = []
    command_history: List[List[str]] = []
    total_steps = max(1, len(selected_aspects) * max(1, len(timeline)))
    step = 0
    for aspect in selected_aspects:
        clip_paths: List[Path] = []
        for item in timeline:
            step += 1
            scene_id = str(item.get("scene_id", step)).zfill(2)
            scene_output = render_dir / "cache" / aspect.replace(":", "x") / f"scene_{scene_id}.mp4"
            _progress(progress_callback, 5 + int(step / total_steps * 70), f"Rendering scene {scene_id} {aspect}")
            try:
                result = _render_scene_clip(ffmpeg_path, item, aspect, scene_output, log_path, fps, profile)
            except Exception as error:
                result = {"ok": False, "message": "Scene clip exception", "data": {}, "error": str(error)}
            if result.get("data", {}).get("command"):
                command_history.append(result["data"]["command"])
            if result["ok"]:
                clip_paths.append(scene_output)
                mark_scene_rendered(render_dir, aspect, scene_id, str(scene_output))
            else:
                errors.append(f"Scene {scene_id} {aspect}: {result['error']}")
                mark_scene_failed(render_dir, aspect, scene_id, str(result.get("error", "")))
        if not clip_paths:
            errors.append(f"No scene clips rendered for {aspect}")
            continue
        _progress(progress_callback, 82, f"Concatenating {aspect}")
        try:
            final_result = _concat_scene_clips(ffmpeg_path, clip_paths, aspect, render_dir, log_path, audio_path, ass_path, profile, timeline_data.get("total_duration_seconds", 0))
        except Exception as error:
            final_result = {"ok": False, "message": "Final concat exception", "data": {}, "error": str(error)}
        if final_result.get("data", {}).get("command"):
            command_history.append(final_result["data"]["command"])
        if final_result["ok"]:
            outputs[aspect] = final_result["data"]["path"]
        else:
            errors.append(f"Final {aspect}: {final_result['error']}")

    status = "DONE" if outputs and not errors else "PARTIAL" if outputs else "FAILED"
    update_manifest(render_dir, render_status=status, outputs=outputs, errors=errors, ffmpeg_command_history=command_history)
    save_render_state(render_dir, {"render_id": render_id, "status": status, "completed_outputs": outputs, "errors": errors})
    _progress(progress_callback, 100, "Render finished")
    ok = bool(outputs)
    return {
        "ok": ok,
        "message": "Render completed" if ok else "Render failed",
        "data": {
            "render_id": render_id,
            "render_dir": str(render_dir),
            "outputs": outputs,
            "timeline_path": str(render_dir / "timeline.json"),
            "manifest_path": str(render_dir / "render_manifest.json"),
            "log_path": str(log_path),
            "subtitle": subtitle_result.get("data", {}),
        },
        "error": "; ".join(errors),
    }
