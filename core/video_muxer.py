from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from core.real_clip_pipeline import combine_scene_clips_to_mp4, ensure_parent_dir, validate_mp4, write_subtitles
from core.subtitle_engine import generate_styled_subtitles


def ffprobe_summary(path: str | Path) -> dict[str, Any]:
    return validate_mp4(path, min_duration=0.1, min_file_size=1)


def write_ffprobe_text(path: str | Path, output_path: str | Path) -> str:
    output = ensure_parent_dir(output_path)
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        text = proc.stdout or json.dumps(ffprobe_summary(path), ensure_ascii=False, indent=2)
    except Exception:
        text = json.dumps(ffprobe_summary(path), ensure_ascii=False, indent=2)
    output.write_text(text, encoding="utf-8")
    return str(output)


def mux_video_shots_with_audio(
    shot_paths: list[str | Path],
    hook_audio_path: str | Path,
    output_path: str | Path,
    *,
    subtitle_timing: list[dict[str, Any]],
    subtitles_dir: str | Path,
) -> dict[str, Any]:
    subtitles_dir = Path(subtitles_dir)
    srt_path = subtitles_dir / "subtitles.srt"
    write_subtitles(subtitle_timing, srt_path)
    styled = generate_styled_subtitles(subtitle_timing, subtitles_dir, subtitle_style="Thai Emotional MV")
    ass_path = Path(str((styled.get("data") or {}).get("ass") or ""))
    result = combine_scene_clips_to_mp4(
        shot_paths,
        output_path,
        subtitle_path=ass_path if ass_path.is_file() else srt_path,
        background_audio_path=hook_audio_path,
    )
    result.setdefault("data", {})["subtitles"] = str(srt_path)
    result.setdefault("data", {})["styled_subtitles"] = str(ass_path) if ass_path.is_file() else ""
    return result
