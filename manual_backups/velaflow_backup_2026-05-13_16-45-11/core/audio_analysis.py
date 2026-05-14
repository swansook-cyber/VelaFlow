import json
import math
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List


def _read_wav_samples(path: Path) -> tuple[int, List[float]]:
    with wave.open(str(path), "rb") as wav:
        channels = max(1, wav.getnchannels())
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frame_count = wav.getnframes()
        raw = wav.readframes(frame_count)
    if sample_width != 2:
        return sample_rate, []
    samples: List[float] = []
    for index in range(0, len(raw), 2 * channels):
        values = []
        for channel in range(channels):
            offset = index + channel * 2
            if offset + 2 <= len(raw):
                value = int.from_bytes(raw[offset : offset + 2], byteorder="little", signed=True) / 32768.0
                values.append(value)
        if values:
            samples.append(sum(values) / len(values))
    return sample_rate, samples


def _convert_to_wav(audio_path: Path, ffmpeg_path: str, temp_dir: Path) -> Path | None:
    if not audio_path.is_file() or not shutil.which(ffmpeg_path) and not Path(ffmpeg_path).exists():
        return None
    temp_dir.mkdir(parents=True, exist_ok=True)
    wav_path = temp_dir / "analysis_audio.wav"
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(audio_path),
        "-ac",
        "1",
        "-ar",
        "22050",
        "-vn",
        str(wav_path),
    ]
    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return wav_path if process.returncode == 0 and wav_path.exists() else None


def _energy_windows(samples: List[float], sample_rate: int, window_seconds: float = 0.12) -> List[Dict[str, float]]:
    window = max(1, int(sample_rate * window_seconds))
    energies: List[Dict[str, float]] = []
    for start in range(0, len(samples), window):
        chunk = samples[start : start + window]
        if not chunk:
            continue
        rms = math.sqrt(sum(value * value for value in chunk) / len(chunk))
        energies.append({"time": start / sample_rate, "energy": rms})
    return energies


def detect_beats_from_energy(energies: List[Dict[str, float]], min_gap: float = 0.28) -> List[Dict[str, float]]:
    if not energies:
        return []
    values = [item["energy"] for item in energies]
    average = sum(values) / len(values)
    variance = sum((value - average) ** 2 for value in values) / len(values)
    threshold = average + math.sqrt(variance) * 0.65
    beats: List[Dict[str, float]] = []
    last_time = -999.0
    for index, item in enumerate(energies):
        prev_energy = energies[index - 1]["energy"] if index else 0.0
        next_energy = energies[index + 1]["energy"] if index + 1 < len(energies) else 0.0
        is_peak = item["energy"] >= prev_energy and item["energy"] >= next_energy and item["energy"] >= threshold
        if is_peak and item["time"] - last_time >= min_gap:
            beats.append({"time": round(item["time"], 3), "strength": round(min(1.0, item["energy"] / max(threshold, 0.0001)), 3)})
            last_time = item["time"]
    return beats


def analyze_audio(audio_path: str, ffmpeg_path: str = "ffmpeg", output_dir: str | Path | None = None) -> Dict[str, Any]:
    path = Path(audio_path or "")
    output = Path(output_dir) if output_dir else None
    if not path.is_file():
        result = {"ok": False, "message": "No audio file for beat detection", "data": {"beats": [], "duration_seconds": 0}, "error": "missing audio"}
        if output:
            (output / "beat_map.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    analysis_source = path
    temp_dir = output / "temp" if output else path.parent
    if path.suffix.lower() != ".wav":
        converted = _convert_to_wav(path, ffmpeg_path, temp_dir)
        if converted:
            analysis_source = converted

    try:
        sample_rate, samples = _read_wav_samples(analysis_source)
        if not samples:
            raise RuntimeError("No PCM samples available")
        duration = len(samples) / sample_rate
        energies = _energy_windows(samples, sample_rate)
        beats = detect_beats_from_energy(energies)
        result = {
            "ok": True,
            "message": "Beat map generated",
            "data": {
                "audio_path": str(path),
                "duration_seconds": round(duration, 3),
                "beat_count": len(beats),
                "beats": beats,
                "energy_windows": [{"time": round(item["time"], 3), "energy": round(item["energy"], 5)} for item in energies],
            },
            "error": "",
        }
    except Exception as error:
        result = {"ok": False, "message": "Beat detection failed", "data": {"beats": [], "duration_seconds": 0}, "error": str(error)}

    if output:
        (output / "beat_map.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def beats_in_range(beat_map: Dict[str, Any], start: float, end: float) -> List[Dict[str, float]]:
    beats = ((beat_map or {}).get("data", {}) or {}).get("beats", []) or []
    return [beat for beat in beats if start <= float(beat.get("time", 0)) < end]
