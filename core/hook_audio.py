from __future__ import annotations

from pathlib import Path
from typing import Any

from core.real_clip_pipeline import trim_audio_clip, validate_mp4


def trim_hook_audio(
    uploaded_audio_path: str | Path,
    output_path: str | Path,
    *,
    hook_start_time: float,
    hook_end_time: float,
) -> dict[str, Any]:
    start = max(0.0, float(hook_start_time or 0.0))
    end = max(start + 1.0, float(hook_end_time or start + 1.0))
    result = trim_audio_clip(uploaded_audio_path, output_path, start_time=start, end_time=end)
    result.setdefault("data", {})["hook_start_time"] = start
    result.setdefault("data", {})["hook_end_time"] = end
    result.setdefault("data", {})["hook_duration"] = round(end - start, 3)
    return result


def validate_final_clip(path: str | Path, *, require_audio: bool = True) -> dict[str, Any]:
    return validate_mp4(path, min_duration=5.0, min_file_size=500 * 1024, require_audio=require_audio)
