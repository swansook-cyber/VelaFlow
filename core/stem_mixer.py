"""Optional local mixing of user-supplied, already aligned stems."""
from __future__ import annotations

import math
import json
import subprocess
import uuid
from pathlib import Path

from core.real_clip_pipeline import find_ffmpeg, _resolve_ffprobe_path
from core.remaster_engine import measure_remaster_artifact

MAX_STEM_BYTES = 64 * 1024 * 1024
MAX_EXPORT_BYTES = 96 * 1024 * 1024
MAX_DURATION_SECONDS = 300


def probe_stem(path: str | Path, ffmpeg: str) -> dict:
    """Require real FFprobe stream evidence; never accept its FFmpeg fallback."""
    ffprobe = _resolve_ffprobe_path(ffmpeg)
    if not ffprobe:
        raise ValueError("FFprobe is required to validate audio")
    run = subprocess.run(
        [ffprobe, "-v", "error", "-protocol_whitelist", "file,pipe", "-f",
         Path(path).suffix.lower().lstrip('.'), "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,sample_rate,channels,bits_per_raw_sample:format=duration",
         "-of", "json", str(Path(path).resolve())],
        capture_output=True, timeout=20, check=False,
    )
    if run.returncode:
        raise ValueError("Invalid or corrupt audio file")
    payload = json.loads(run.stdout)
    streams = payload.get("streams") or []
    if not streams:
        raise ValueError("File has no audio stream")
    stream = streams[0]
    duration = float(payload.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or not 0 < duration <= MAX_DURATION_SECONDS:
        raise ValueError(f"Each stem must be at most {MAX_DURATION_SECONDS // 60} minutes")
    if not 1 <= int(stream.get("channels", 0)) <= 8 or not 8000 <= int(stream.get("sample_rate", 0)) <= 192000:
        raise ValueError("Unsupported audio channel count or sample rate")
    return {**stream, "duration": duration}


def build_stem_mix_filter(vocal_db: float, instrumental_db: float) -> str:
    gains = [float(vocal_db), float(instrumental_db)]
    if any(not math.isfinite(g) or not -24 <= g <= 6 for g in gains):
        raise ValueError("Stem gains must be finite and between -24 and +6 dB")
    return (
        f"[0:a:0]aresample=48000,aformat=channel_layouts=stereo,volume={gains[0]:g}dB[v];"
        f"[1:a:0]aresample=48000,aformat=channel_layouts=stereo,volume={gains[1]:g}dB[i];"
        "[v][i]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.794328235:level=false:latency=true[mix]"
    )


def mix_stems(vocal: str | Path, instrumental: str | Path, output_root: str | Path,
              *, vocal_db: float = -6, instrumental_db: float = -6,
              ffmpeg_path: str = "") -> dict:
    """Render a unique PCM24 WAV and measure it before offering it to the user.

    No source separation, automatic alignment, normalization or source mutation.
    Existing mastering remains an explicit subsequent workflow.
    """
    filters = build_stem_mix_filter(vocal_db, instrumental_db)
    sources = [Path(vocal), Path(instrumental)]
    if any(not p.is_file() or p.suffix.lower() not in {".wav", ".mp3"} for p in sources):
        return {"ok": False, "error": "Two existing WAV/MP3 stems are required"}
    if any(p.stat().st_size > MAX_STEM_BYTES for p in sources):
        return {"ok": False, "error": "Each stem must be at most 64 MB"}
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "error": "FFmpeg is unavailable"}
    folder = target = None
    succeeded = False
    try:
        probes = [probe_stem(p, ffmpeg) for p in sources]
        expected_duration = max(p["duration"] for p in probes)
        candidate = Path(output_root).resolve() / uuid.uuid4().hex
        candidate.mkdir(parents=True, exist_ok=False)
        folder = candidate
        target = folder / "stem_mix.wav"
        run = subprocess.run(
            [ffmpeg, "-nostdin", "-n", "-v", "error", "-protocol_whitelist", "file,pipe",
             "-f", sources[0].suffix[1:].lower(), "-i", str(sources[0].resolve()),
             "-protocol_whitelist", "file,pipe", "-f", sources[1].suffix[1:].lower(),
             "-i", str(sources[1].resolve()), "-filter_complex", filters, "-map", "[mix]",
             "-t", str(MAX_DURATION_SECONDS), "-fs", str(MAX_EXPORT_BYTES),
             "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(target)],
            capture_output=True, timeout=180, check=False,
        )
        if run.returncode:
            return {"ok": False, "error": "Stem decoding or mixing failed"}
        probe = probe_stem(target, ffmpeg)
        if (probe.get("codec_name") != "pcm_s24le" or int(probe.get("sample_rate", 0)) != 48000
                or int(probe.get("channels", 0)) != 2 or int(probe.get("bits_per_raw_sample", 0)) != 24
                or abs(probe["duration"] - expected_duration) > 0.1
                or target.stat().st_size > MAX_EXPORT_BYTES):
            return {"ok": False, "error": "WAV format or duration validation failed"}
        measurement = measure_remaster_artifact(target, ffmpeg)
        peak = measurement.get("true_peak_dbtp")
        lufs = measurement.get("integrated_lufs")
        safe = (measurement.get("ok") and measurement.get("rail_hits") == 0
                and (measurement.get("effectively_silent") or
                     (peak is not None and math.isfinite(peak) and peak <= -1
                      and lufs is not None and math.isfinite(lufs))))
        if not safe:
            return {"ok": False, "error": "Mix did not pass measured peak validation",
                    "measurement": measurement}
        succeeded = True
        return {"ok": True, "path": str(target), "measurement": measurement, "probe": probe}
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        return {"ok": False, "error": "Mix could not be rendered or measured"}
    finally:
        if not succeeded and folder is not None:
            # Only this invocation's known output and newly created empty directory.
            # Never walk old exports, user sources, or arbitrary directory contents.
            if target is not None:
                target.unlink(missing_ok=True)
            folder.rmdir()
