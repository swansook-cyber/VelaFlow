"""Optional local mixing of user-supplied, already aligned stems."""
from __future__ import annotations

import math
import subprocess
import uuid
from pathlib import Path

from core.real_clip_pipeline import find_ffmpeg
from core.remaster_engine import measure_remaster_artifact


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
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "error": "FFmpeg is unavailable"}
    folder = Path(output_root) / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    target = folder / "stem_mix.wav"
    try:
        run = subprocess.run(
            [ffmpeg, "-nostdin", "-n", "-v", "error", "-i", str(sources[0].resolve()),
             "-i", str(sources[1].resolve()), "-filter_complex", filters, "-map", "[mix]",
             "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(target.resolve())],
            capture_output=True, timeout=180, check=False,
        )
        if run.returncode:
            return {"ok": False, "error": "Stem decoding or mixing failed"}
        measurement = measure_remaster_artifact(target, ffmpeg)
        peak = measurement.get("true_peak_dbtp")
        safe = (measurement.get("ok") and measurement.get("rail_hits") == 0
                and (measurement.get("effectively_silent") or
                     (peak is not None and math.isfinite(peak) and peak <= -1)))
        if not safe:
            return {"ok": False, "error": "Mix did not pass measured peak validation",
                    "measurement": measurement}
        return {"ok": True, "path": str(target), "measurement": measurement}
    except (OSError, subprocess.SubprocessError):
        return {"ok": False, "error": "Mix could not be rendered or measured"}
