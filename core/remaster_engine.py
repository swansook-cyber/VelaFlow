from __future__ import annotations

import json
import math
import shutil
import subprocess
import zipfile
from array import array
from datetime import datetime
from pathlib import Path
from typing import Any

from core.audio_intelligence import ANALYZER_VERSION as AUDIO_INTELLIGENCE_ANALYZER_VERSION, analyze_audio_source
from core.file_naming import build_asset_export_filename, ensure_unique_path, sanitize_filename
from core.paths import ROOT
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir, find_ffmpeg, probe_media


REMASTER_STYLES = [
    "Streaming Balanced",
    "Modern Pop",
    "Pop Rock",
    "Emotional Ballad",
    "Warm Acoustic",
    "Vocal Focus",
    "Cinematic",
    "Loud Modern",
    "Reference-Guided Master",
    "Custom",
]
REMASTER_RECOMMENDATION_MODES = ["Auto Recommended", "Manual"]

REFERENCE_GUIDED_PRESET = "Reference-Guided Master"
REFERENCE_MIN_DURATION_SEC = 30.0
REFERENCE_TARGET_LUFS_RANGE = (-16.0, -11.0)
REFERENCE_TARGET_TRUE_PEAK_RANGE = (-1.5, -1.0)
REFERENCE_UNSUPPORTED_MATCHES = [
    "lra_target",
    "spectral_balance",
    "stereo_image",
    "transients",
]

AUTO_REMASTER_PRESETS = [
    "Streaming Balanced",
    "Emotional Ballad",
    "Warm Acoustic",
    "Vocal Focus",
    "Pop Rock",
    "Modern Pop",
    "Loud Modern",
]
PRESET_SAFETY_CLASSES = {
    "Streaming Balanced": "conservative",
    "Emotional Ballad": "conservative",
    "Warm Acoustic": "conservative",
    "Vocal Focus": "moderate",
    "Pop Rock": "moderate",
    "Modern Pop": "moderate",
    "Loud Modern": "aggressive",
    "Cinematic": "artistic_special",
    "Custom": "manual_only",
    REFERENCE_GUIDED_PRESET: "manual_only",
}
RECOMMENDATION_PRIORITY = {name: index for index, name in enumerate(AUTO_REMASTER_PRESETS)}

RECOMMENDATION_REASON_LABELS = {
    "already_near_streaming_target": "Source is already near a normal streaming target.",
    "low_true_peak_headroom": "Measured true-peak headroom is low, so conservative processing is safer.",
    "already_very_loud": "Source is already loud and should not receive aggressive loudness treatment.",
    "high_dynamic_range": "Measured loudness range favors preserving musical dynamics.",
    "low_dynamic_range": "Source is already compressed, so additional aggressive compression is avoided.",
    "quiet_dynamic_source": "Quieter dynamic material supports a gentler mastering approach.",
    "dense_sustained_energy": "Sustained energy supports a denser modern character.",
    "lower_energy_material": "Lower energy supports a lighter, more open treatment.",
    "mono_source": "Mono source keeps the recommendation conservative.",
    "silent_or_unreliable_source": "Source has no reliable audible program level; balanced fallback is safest.",
    "metadata_ballad": "Project metadata indicates an emotional or ballad direction.",
    "metadata_acoustic": "Project metadata indicates an acoustic or warm direction.",
    "metadata_pop_rock": "Project metadata indicates a pop-rock direction.",
    "metadata_modern_pop": "Project metadata indicates a modern pop or electronic direction.",
    "metadata_vocal": "Project metadata indicates spoken or vocal-forward content.",
    "explicit_electronic_direction": "Explicit electronic style metadata resolves mixed modern/pop-rock evidence.",
    "explicit_style_confirmed": "Explicit project style is supported by reliable source character.",
    "conservative_fallback": "Evidence is limited or mixed; balanced processing is safest.",
}

LEGACY_STYLE_ALIASES = {
    "Vela Moon Emotional Pop Rock": "Pop Rock",
    "Spotify Pop Loud": "Modern Pop",
    "TikTok Loud Master": "Loud Modern",
    "Warm Vocal": "Vocal Focus",
    "Acoustic Smooth": "Warm Acoustic",
    "Podcast Voice Clean": "Vocal Focus",
    "Spotify Balanced": "Streaming Balanced",
    "Spotify Clean": "Streaming Balanced",
    "TikTok Loud": "Loud Modern",
    "YouTube Clean": "Streaming Balanced",
    "Cinematic Wide": "Cinematic",
    "Bass Boost": "Modern Pop",
    "Emotional Soft": "Emotional Ballad",
    "Soft Emotional": "Emotional Ballad",
}

STYLE_FILTERS: dict[str, dict[str, Any]] = {
    "Streaming Balanced": {
        "filters": "adeclick,highpass=f=28,lowpass=f=18500,equalizer=f=3200:t=q:w=1.0:g=0.8,acompressor=threshold=-18dB:ratio=1.7:attack=12:release=160,loudnorm=I=-14:TP=-1.0:LRA=10,alimiter=level_out=0.93:limit=0.93",
        "target_lufs": "-14 LUFS estimated",
        "true_peak": "-1 dBTP estimated",
        "summary": "clean streaming loudness, gentle EQ, safe limiting",
    },
    "Modern Pop": {
        "filters": "adeclick,highpass=f=30,lowpass=f=18800,equalizer=f=90:t=q:w=0.9:g=0.8,equalizer=f=2800:t=q:w=1.0:g=1.1,acompressor=threshold=-17dB:ratio=1.9:attack=10:release=145,loudnorm=I=-12.5:TP=-1.0:LRA=9,alimiter=level_out=0.93:limit=0.93",
        "target_lufs": "-12.5 LUFS estimated",
        "true_peak": "-1 dBTP estimated",
        "summary": "modern pop loudness with controlled vocal presence",
    },
    "Pop Rock": {
        "filters": "adeclick,highpass=f=30,lowpass=f=18500,equalizer=f=180:t=q:w=0.9:g=0.8,equalizer=f=2800:t=q:w=1.0:g=1.4,equalizer=f=6800:t=q:w=1.1:g=0.6,acompressor=threshold=-18dB:ratio=1.8:attack=10:release=150,loudnorm=I=-13:TP=-1.0:LRA=9,alimiter=level_out=0.93:limit=0.93",
        "target_lufs": "-13 LUFS estimated",
        "true_peak": "-1 dBTP estimated",
        "summary": "guitar-forward pop rock polish with warm vocal focus",
    },
    "Emotional Ballad": {
        "filters": "adeclick,highpass=f=24,lowpass=f=18000,equalizer=f=800:t=q:w=1.2:g=-0.8,equalizer=f=4500:t=q:w=1.0:g=0.9,acompressor=threshold=-20dB:ratio=1.4:attack=18:release=220,loudnorm=I=-15.5:TP=-1.3:LRA=13,alimiter=level_out=0.94:limit=0.94",
        "target_lufs": "-15.5 LUFS estimated",
        "true_peak": "-1.3 dBTP estimated",
        "summary": "soft dynamics for emotional ballads",
    },
    "Warm Acoustic": {
        "filters": "adeclick,highpass=f=26,lowpass=f=18000,equalizer=f=220:t=q:w=0.9:g=0.8,equalizer=f=3500:t=q:w=1.0:g=0.9,acompressor=threshold=-19dB:ratio=1.45:attack=16:release=190,loudnorm=I=-15:TP=-1.2:LRA=12,alimiter=level_out=0.94:limit=0.94",
        "target_lufs": "-15 LUFS estimated",
        "true_peak": "-1.2 dBTP estimated",
        "summary": "warm acoustic tone with light compression",
    },
    "Vocal Focus": {
        "filters": "adeclick,highpass=f=45,lowpass=f=17000,equalizer=f=1800:t=q:w=1.1:g=0.8,equalizer=f=4200:t=q:w=1.0:g=1.4,acompressor=threshold=-19dB:ratio=1.8:attack=10:release=150,loudnorm=I=-14:TP=-1.1:LRA=9,alimiter=level_out=0.93:limit=0.93",
        "target_lufs": "-14 LUFS estimated",
        "true_peak": "-1.1 dBTP estimated",
        "summary": "clearer vocal center and safe loudness",
    },
    "Cinematic": {
        "filters": "adeclick,highpass=f=25,lowpass=f=19000,equalizer=f=120:t=q:w=0.9:g=0.7,equalizer=f=4500:t=q:w=1.1:g=0.5,aecho=0.35:0.25:12:0.06,loudnorm=I=-15:TP=-1.3:LRA=12,alimiter=level_out=0.94:limit=0.94",
        "target_lufs": "-15 LUFS estimated",
        "true_peak": "-1.3 dBTP estimated",
        "summary": "wide cinematic space without aggressive loudness",
    },
    "Loud Modern": {
        "filters": "adeclick,highpass=f=35,lowpass=f=18500,equalizer=f=2500:t=q:w=1.1:g=1.5,equalizer=f=9000:t=q:w=1.1:g=0.7,acompressor=threshold=-16dB:ratio=2.2:attack=8:release=120,loudnorm=I=-11:TP=-1.0:LRA=8,alimiter=level_out=0.92:limit=0.92",
        "target_lufs": "-11 LUFS estimated",
        "true_peak": "-1 dBTP estimated",
        "summary": "louder modern master with clipping protection",
    },
}

CUSTOM_REMASTER_DEFAULTS: dict[str, float] = {
    "loudness_lufs": -14.0,
    "bass_db": 0.0,
    "mid_db": 0.8,
    "high_db": 0.0,
    "compression_ratio": 1.7,
    "stereo_width": 1.0,
    "output_ceiling_db": -1.0,
}

CUSTOM_REMASTER_LIMITS: dict[str, tuple[float, float]] = {
    "loudness_lufs": (-16.0, -10.0),
    "bass_db": (-3.0, 3.0),
    "mid_db": (-3.0, 3.0),
    "high_db": (-3.0, 3.0),
    "compression_ratio": (1.2, 2.5),
    "stereo_width": (0.8, 1.2),
    "output_ceiling_db": (-1.5, -0.5),
}


def default_custom_remaster_settings() -> dict[str, float]:
    """Return a fresh, project-safe custom baseline."""
    return dict(CUSTOM_REMASTER_DEFAULTS)


def sanitize_custom_remaster_settings(settings: dict[str, Any] | None = None) -> dict[str, float]:
    source = settings if isinstance(settings, dict) else {}
    resolved: dict[str, float] = {}
    for key, default in CUSTOM_REMASTER_DEFAULTS.items():
        try:
            value = float(source.get(key, default))
        except (TypeError, ValueError):
            value = default
        lower, upper = CUSTOM_REMASTER_LIMITS[key]
        resolved[key] = round(max(lower, min(upper, value)), 2)
    return resolved


def build_custom_remaster_config(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a bounded FFmpeg chain from practical mastering controls."""
    resolved = sanitize_custom_remaster_settings(settings)
    filters = ["adeclick", "highpass=f=28", "lowpass=f=18500"]
    tone_bands = (
        ("bass_db", 100, 0.9),
        ("mid_db", 3200, 1.0),
        ("high_db", 9000, 1.1),
    )
    for key, frequency, width in tone_bands:
        gain = resolved[key]
        if abs(gain) >= 0.05:
            filters.append(f"equalizer=f={frequency}:t=q:w={width}:g={gain}")
    filters.append(
        "acompressor="
        f"threshold=-18dB:ratio={resolved['compression_ratio']}:attack=12:release=160"
    )
    if abs(resolved["stereo_width"] - 1.0) >= 0.01:
        filters.append(f"stereotools=mlev=1.0:slev={resolved['stereo_width']}")
    filters.append(
        f"loudnorm=I={resolved['loudness_lufs']}:"
        f"TP={resolved['output_ceiling_db']}:LRA=10"
    )
    limiter_level = round(0.93 * (10 ** ((resolved["output_ceiling_db"] + 1.0) / 20.0)), 4)
    filters.append(f"alimiter=level_out={limiter_level}:limit={limiter_level}")
    return {
        "filters": ",".join(filters),
        "target_lufs": f"{resolved['loudness_lufs']:g} LUFS estimated",
        "true_peak": f"{resolved['output_ceiling_db']:g} dBTP estimated",
        "summary": "project-specific custom balance with bounded EQ, compression, width, loudness, and limiting",
        "custom_settings": resolved,
    }


def _reference_metrics(analysis: dict[str, Any] | None) -> dict[str, float | None]:
    payload = analysis if isinstance(analysis, dict) else {}
    loudness = payload.get("loudness") or {}
    return {
        "lufs": _finite_metric(loudness.get("integrated_lufs")),
        "true_peak_dbtp": _finite_metric(loudness.get("true_peak_dbtp")),
        "lra_lu": _finite_metric(loudness.get("lra_lu")),
    }


def validate_reference_master_analysis(
    reference_analysis: dict[str, Any] | None,
    *,
    source_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate only reliable Reference-Guided V1 inputs."""
    analysis = reference_analysis if isinstance(reference_analysis, dict) else {}
    metadata = analysis.get("metadata") or {}
    loudness = analysis.get("loudness") or {}
    source = analysis.get("source") or {}
    metrics = _reference_metrics(analysis)
    errors: list[str] = []
    warnings: list[str] = []

    duration = _finite_metric(metadata.get("duration_sec"))
    if metadata.get("status") not in {"measured", "partial"} or not metadata.get("codec"):
        errors.append("Reference has no readable audio stream.")
    if duration is None or duration < REFERENCE_MIN_DURATION_SEC:
        errors.append("Reference Track must be at least 30 seconds long.")
    if loudness.get("status") != "measured" or any(value is None for value in metrics.values()):
        errors.append("Reference loudness analysis is unavailable.")
    if metrics["lufs"] is not None and metrics["lufs"] <= -70.0:
        errors.append("Reference Track appears to be silent.")

    channels = int(metadata.get("channels") or 0)
    sample_rate = int(metadata.get("sample_rate_hz") or 0)
    if channels == 1:
        warnings.append("Reference is mono; stereo character was not matched.")
    if sample_rate and sample_rate not in {44100, 48000}:
        warnings.append("Reference uses an unusual sample rate; VelaFlow will preserve its safe output format.")
    if metrics["lufs"] is not None and metrics["lufs"] > REFERENCE_TARGET_LUFS_RANGE[1]:
        warnings.append("Reference is louder than VelaFlow's safe target; loudness was limited.")
    elif metrics["lufs"] is not None and metrics["lufs"] < REFERENCE_TARGET_LUFS_RANGE[0]:
        warnings.append("Reference is quieter than VelaFlow's supported target; loudness was limited.")
    if metrics["true_peak_dbtp"] is not None and metrics["true_peak_dbtp"] > REFERENCE_TARGET_TRUE_PEAK_RANGE[1]:
        warnings.append("Reference True Peak is too hot; VelaFlow safety ceiling was used.")
    elif metrics["true_peak_dbtp"] is not None and metrics["true_peak_dbtp"] < REFERENCE_TARGET_TRUE_PEAK_RANGE[0]:
        warnings.append("Reference True Peak has extra headroom; VelaFlow used its supported lower ceiling.")
    if metrics["lra_lu"] is not None and metrics["lra_lu"] >= 15.0:
        warnings.append("Reference has a high loudness range; LRA is shown for comparison only.")
    else:
        warnings.append("LRA is shown for comparison only and is not directly matched.")

    if source_analysis:
        source_facts = source_analysis.get("source") or {}
        reference_digest = str(source.get("sha256") or "")
        source_digest = str(source_facts.get("sha256") or "")
        if reference_digest and source_digest and reference_digest == source_digest:
            errors.append("Source and Reference Track are identical. Choose a different reference.")

    return {
        "ok": not errors,
        "errors": list(dict.fromkeys(errors)),
        "warnings": list(dict.fromkeys(warnings)),
        "metrics": metrics,
        "duration_sec": duration,
        "source_id": str(source.get("source_id") or ""),
    }


def build_reference_master_plan(
    source_analysis: dict[str, Any] | None,
    reference_analysis: dict[str, Any] | None,
    *,
    reference_name: str = "",
) -> dict[str, Any]:
    """Build a deterministic, loudness-only Reference-Guided plan."""
    source_payload = source_analysis if isinstance(source_analysis, dict) else {}
    reference_payload = reference_analysis if isinstance(reference_analysis, dict) else {}
    source_metrics = _reference_metrics(source_payload)
    if (source_payload.get("loudness") or {}).get("status") != "measured" or any(value is None for value in source_metrics.values()):
        return {"ok": False, "error": "source_analysis_unavailable", "message": "Source loudness analysis is unavailable."}
    validation = validate_reference_master_analysis(reference_payload, source_analysis=source_payload)
    if not validation["ok"]:
        return {
            "ok": False,
            "error": "invalid_reference",
            "message": validation["errors"][0],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        }

    reference_metrics = validation["metrics"]
    target_lufs = round(max(REFERENCE_TARGET_LUFS_RANGE[0], min(REFERENCE_TARGET_LUFS_RANGE[1], float(reference_metrics["lufs"]))), 2)
    target_true_peak = round(
        min(REFERENCE_TARGET_TRUE_PEAK_RANGE[1], max(REFERENCE_TARGET_TRUE_PEAK_RANGE[0], float(reference_metrics["true_peak_dbtp"]))),
        2,
    )
    resolved_settings = sanitize_custom_remaster_settings(
        {
            "loudness_lufs": target_lufs,
            "bass_db": 0.0,
            "mid_db": 0.0,
            "high_db": 0.0,
            "compression_ratio": CUSTOM_REMASTER_LIMITS["compression_ratio"][0],
            "stereo_width": 1.0,
            "output_ceiling_db": target_true_peak,
        }
    )
    reference_source = reference_payload.get("source") or {}
    return {
        "ok": True,
        "mode": "reference",
        "source_source_id": str((source_payload.get("source") or {}).get("source_id") or ""),
        "reference_source_id": validation["source_id"],
        "reference": {
            "source_id": validation["source_id"],
            "filename": str(reference_name or Path(str(reference_source.get("path") or "")).name),
            "metrics": reference_metrics,
        },
        "source_metrics": source_metrics,
        "reference_metrics": reference_metrics,
        "targets": {"lufs": target_lufs, "true_peak_dbtp": target_true_peak},
        "resolved_custom_settings": resolved_settings,
        "unsupported_matches": list(REFERENCE_UNSUPPORTED_MATCHES),
        "warnings": validation["warnings"],
        "analysis_provenance": AUDIO_INTELLIGENCE_ANALYZER_VERSION,
    }


def analyze_reference_guided_master(
    source_audio_path: str | Path,
    reference_audio_path: str | Path,
    *,
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
    source_context: dict[str, Any] | None = None,
    reference_context: dict[str, Any] | None = None,
    reference_name: str = "",
) -> dict[str, Any]:
    """Analyze source/reference through the shared Audio Intelligence cache."""
    source = Path(source_audio_path)
    reference = Path(reference_audio_path)
    source_validation = validate_remaster_input(source, max_upload_mb=max_upload_mb)
    if not source_validation.get("ok"):
        return {"ok": False, "error": source_validation.get("error"), "message": source_validation.get("message")}
    reference_validation = validate_remaster_input(reference, max_upload_mb=max_upload_mb)
    if not reference_validation.get("ok"):
        return {"ok": False, "error": reference_validation.get("error"), "message": reference_validation.get("message")}
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "error": "missing_ffmpeg", "message": "Audio processing is unavailable on this device."}

    source_analysis = analyze_audio_source(source, source_context, depth="deep", ffmpeg_path=ffmpeg)
    reference_analysis = analyze_audio_source(reference, reference_context, depth="deep", ffmpeg_path=ffmpeg)
    plan = build_reference_master_plan(
        source_analysis,
        reference_analysis,
        reference_name=reference_name or reference.name,
    )
    if not plan.get("ok"):
        return {
            "ok": False,
            "error": plan.get("error", "invalid_reference"),
            "message": plan.get("message", "Reference Track could not be analyzed."),
            "data": {"source_analysis": source_analysis, "reference_analysis": reference_analysis},
        }
    return {
        "ok": True,
        "data": {
            "plan": plan,
            "source_analysis": source_analysis,
            "reference_analysis": reference_analysis,
            "performance": {
                "source": dict(source_analysis.get("performance") or {}),
                "reference": dict(reference_analysis.get("performance") or {}),
                "plan_subprocess_runs": 0,
            },
        },
        "error": "",
    }


def build_reference_result_comparison(plan: dict[str, Any] | None, result_analysis: dict[str, Any] | None) -> dict[str, Any]:
    reference_plan = plan if isinstance(plan, dict) else {}
    result_metrics = _reference_metrics(result_analysis)
    target_lufs = _finite_metric((reference_plan.get("targets") or {}).get("lufs"))
    result_lufs = result_metrics.get("lufs")
    loudness_delta = round(result_lufs - target_lufs, 2) if result_lufs is not None and target_lufs is not None else None
    return {
        "source": dict(reference_plan.get("source_metrics") or {}),
        "reference": dict(reference_plan.get("reference_metrics") or {}),
        "result": result_metrics,
        "targets": dict(reference_plan.get("targets") or {}),
        "loudness_delta_lu": loudness_delta,
        "loudness_guided": bool(loudness_delta is not None and abs(loudness_delta) <= 1.0),
        "note": "LRA is comparison context only; no exact dynamics match was attempted.",
    }


def _run(args: list[str], timeout: int = 180) -> dict[str, Any]:
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": proc.stdout or "", "command": args}
    except FileNotFoundError as exc:
        return {"ok": False, "returncode": -1, "output": f"missing_ffmpeg: {exc}", "command": args}
    except Exception as exc:
        return {"ok": False, "returncode": -1, "output": str(exc), "command": args}


def _max_volume_db(ffmpeg: str, path: Path) -> float | None:
    result = _run([ffmpeg, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], timeout=120)
    for line in result.get("output", "").splitlines():
        if "max_volume:" in line:
            try:
                return float(line.split("max_volume:", 1)[1].strip().split()[0])
            except Exception:
                return None
    return None


def _normalize_style(style: str) -> str:
    selected = LEGACY_STYLE_ALIASES.get(style, style)
    if selected in {"Custom", REFERENCE_GUIDED_PRESET}:
        return selected
    return selected if selected in STYLE_FILTERS else "Streaming Balanced"


def _confidence_label(score: int) -> str:
    if score >= 76:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"


def _finite_metric(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _metadata_text(metadata: dict[str, Any] | str | None) -> str:
    if isinstance(metadata, dict):
        values = [value for value in metadata.values() if isinstance(value, (str, int, float, list, tuple, dict))]
        return " ".join(str(value) for value in values).lower()
    return str(metadata or "").lower()


def _energy_summary(audio_intelligence: dict[str, Any]) -> dict[str, float | None]:
    energy = audio_intelligence.get("energy") or {}
    profile = energy.get("profile") if energy.get("status") == "ok" else []
    values = sorted(
        value
        for value in (_finite_metric((point or {}).get("normalized")) for point in (profile or []))
        if value is not None
    )
    if not values:
        return {"median": None, "high_ratio": None, "low_ratio": None, "variance": None}
    middle = len(values) // 2
    median = values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2.0
    mean = sum(values) / len(values)
    return {
        "median": round(median, 4),
        "high_ratio": round(sum(value >= 0.67 for value in values) / len(values), 4),
        "low_ratio": round(sum(value <= 0.33 for value in values) / len(values), 4),
        "variance": round(sum((value - mean) ** 2 for value in values) / len(values), 4),
    }


def recommend_remaster_preset(
    audio_intelligence: dict[str, Any] | None,
    proxy_metrics: dict[str, Any] | None = None,
    metadata: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Return a deterministic reliable-first preset recommendation.

    Reliable measurements define safety and context. Explicit metadata may
    distinguish character after those gates are applied. ``proxy_metrics`` is
    retained only for caller compatibility and never influences Auto.
    """
    analysis = audio_intelligence if isinstance(audio_intelligence, dict) else {}
    _ = proxy_metrics
    loudness = analysis.get("loudness") or {}
    source_metadata = analysis.get("metadata") or {}
    silence = analysis.get("silence") or {}
    source = analysis.get("source") or {}
    integrated_lufs = _finite_metric(loudness.get("integrated_lufs"))
    true_peak = _finite_metric(loudness.get("true_peak_dbtp"))
    lra = _finite_metric(loudness.get("lra_lu"))
    channels = _finite_metric(source_metadata.get("channels"))
    duration = _finite_metric(source_metadata.get("duration_sec"))
    leading_silence = _finite_metric(silence.get("leading_sec"))
    trailing_silence = _finite_metric(silence.get("trailing_sec"))
    energy = _energy_summary(analysis)
    text = _metadata_text(metadata)

    scores = {name: 20.0 for name in AUTO_REMASTER_PRESETS}
    scores["Streaming Balanced"] = 35.0
    scores["Loud Modern"] = 8.0
    reasons: dict[str, list[str]] = {name: [] for name in AUTO_REMASTER_PRESETS}
    metrics_used: list[str] = []
    excluded: dict[str, str] = {}
    safety = {
        "aggressive_allowed": True,
        "true_peak_headroom_low": False,
        "already_very_loud": False,
        "high_lra": False,
        "low_lra": False,
        "already_near_streaming_target": False,
        "silent_or_unreliable_source": False,
    }

    reliable_count = 0
    if integrated_lufs is not None:
        reliable_count += 1
        metrics_used.append("integrated_lufs")
    if true_peak is not None:
        reliable_count += 1
        metrics_used.append("true_peak_dbtp")
    if lra is not None:
        reliable_count += 1
        metrics_used.append("lra_lu")

    if (
        integrated_lufs is not None
        and true_peak is not None
        and lra is not None
        and -15.0 <= integrated_lufs <= -13.0
        and true_peak <= -0.8
        and 4.0 <= lra <= 11.0
    ):
        safety["already_near_streaming_target"] = True
        scores["Streaming Balanced"] += 50
        reasons["Streaming Balanced"].append("already_near_streaming_target")

    if true_peak is not None and true_peak > -0.5:
        safety["true_peak_headroom_low"] = True
        safety["aggressive_allowed"] = False
        excluded["Loud Modern"] = "low_true_peak_headroom"
        scores["Streaming Balanced"] += 42
        reasons["Streaming Balanced"].append("low_true_peak_headroom")
        for name in ("Modern Pop", "Pop Rock", "Vocal Focus"):
            scores[name] -= 8

    if integrated_lufs is not None and integrated_lufs > -10.5:
        safety["already_very_loud"] = True
        safety["aggressive_allowed"] = False
        excluded["Loud Modern"] = "already_very_loud"
        scores["Streaming Balanced"] += 38
        reasons["Streaming Balanced"].append("already_very_loud")
        scores["Modern Pop"] -= 8

    if lra is not None and lra >= 11.0:
        safety["high_lra"] = True
        safety["aggressive_allowed"] = False
        excluded["Loud Modern"] = "high_dynamic_range"
        scores["Emotional Ballad"] += 30
        scores["Warm Acoustic"] += 26
        scores["Modern Pop"] -= 12
        reasons["Emotional Ballad"].append("high_dynamic_range")
        reasons["Warm Acoustic"].append("high_dynamic_range")
    elif lra is not None and lra <= 3.5:
        safety["low_lra"] = True
        safety["aggressive_allowed"] = False
        excluded["Loud Modern"] = "low_dynamic_range"
        scores["Streaming Balanced"] += 24
        reasons["Streaming Balanced"].append("low_dynamic_range")

    if integrated_lufs is not None and integrated_lufs <= -18.0:
        scores["Warm Acoustic"] += 14
        scores["Emotional Ballad"] += 14
        reasons["Warm Acoustic"].append("quiet_dynamic_source")
        reasons["Emotional Ballad"].append("quiet_dynamic_source")

    if channels is not None:
        metrics_used.append("channels")
        if channels <= 1:
            scores["Streaming Balanced"] += 7
            scores["Vocal Focus"] += 5
            reasons["Streaming Balanced"].append("mono_source")

    if energy["median"] is not None:
        metrics_used.extend(["energy_median", "energy_high_ratio", "energy_low_ratio", "energy_variance"])
        if float(energy["high_ratio"] or 0.0) >= 0.55:
            scores["Modern Pop"] += 12
            scores["Pop Rock"] += 10
            reasons["Modern Pop"].append("dense_sustained_energy")
        if float(energy["low_ratio"] or 0.0) >= 0.55:
            scores["Warm Acoustic"] += 10
            scores["Emotional Ballad"] += 9
            reasons["Warm Acoustic"].append("lower_energy_material")

    if duration and duration > 0 and leading_silence is not None and trailing_silence is not None:
        metrics_used.extend(["leading_silence", "trailing_silence"])
        if (leading_silence + trailing_silence) / duration >= 0.15:
            scores["Vocal Focus"] += 4

    metadata_rules = [
        ("metadata_ballad", "Emotional Ballad", ("ballad", "emotional", "slow song", "บัลลาด", "เพลงช้า"), 34),
        ("metadata_acoustic", "Warm Acoustic", ("acoustic", "warm", "piano", "อะคูสติก", "อบอุ่น"), 30),
        ("metadata_pop_rock", "Pop Rock", ("pop rock", "rock", "guitar", "drum kit", "ป๊อปร็อก", "กีตาร์"), 31),
        ("metadata_modern_pop", "Modern Pop", ("modern pop", "electronic", "edm", "trap", "dance", "808", "อิเล็กทรอนิก"), 31),
        ("metadata_vocal", "Vocal Focus", ("podcast", "narration", "spoken", "speech", "voice", "พอดแคสต์", "บรรยาย"), 34),
    ]
    for reason, preset, keywords, weight in metadata_rules:
        matches = sorted({keyword for keyword in keywords if keyword in text})
        if matches:
            scores[preset] += weight + min(10, (len(matches) - 1) * 3)
            reasons[preset].append(reason)
            metrics_used.append(reason)

            reliable_character_match = (
                preset in {"Pop Rock", "Modern Pop"} and float(energy["high_ratio"] or 0.0) >= 0.55
            ) or (
                preset in {"Warm Acoustic", "Emotional Ballad"}
                and (float(energy["low_ratio"] or 0.0) >= 0.55 or bool(lra is not None and lra >= 11.0))
            ) or (
                preset == "Vocal Focus" and bool(channels is not None and channels <= 1)
            )
            if safety["already_near_streaming_target"] and reliable_character_match:
                scores[preset] += 26
                reasons[preset].append("explicit_style_confirmed")

    if (
        "metadata_modern_pop" in reasons["Modern Pop"]
        and "metadata_pop_rock" in reasons["Pop Rock"]
        and any(keyword in text for keyword in ("electronic", "edm", "trap", "dance", "808"))
    ):
        scores["Modern Pop"] += 4
        reasons["Modern Pop"].append("explicit_electronic_direction")

    source_effectively_silent = (
        integrated_lufs is None
        and true_peak is None
        and energy["median"] == 0.0
        and float(energy["high_ratio"] or 0.0) == 0.0
    )
    if source_effectively_silent:
        safety["silent_or_unreliable_source"] = True
        safety["aggressive_allowed"] = False
        excluded["Loud Modern"] = "silent_or_unreliable_source"
        for name in scores:
            scores[name] = 0.0
            reasons[name] = []
        scores["Streaming Balanced"] = 100.0
        reasons["Streaming Balanced"] = ["silent_or_unreliable_source"]

    available_scores = {name: score for name, score in scores.items() if name not in excluded}
    ranked = sorted(available_scores, key=lambda name: (-available_scores[name], RECOMMENDATION_PRIORITY[name]))
    winner = ranked[0] if ranked else "Streaming Balanced"
    if available_scores.get(winner, 0.0) <= 35.0 and not reasons[winner]:
        winner = "Streaming Balanced"
        reasons[winner].append("conservative_fallback")
    runner_up_score = max((available_scores[name] for name in available_scores if name != winner), default=0.0)
    winner_score = available_scores.get(winner, scores["Streaming Balanced"])
    separation = max(0.0, winner_score - runner_up_score)
    evidence_count = len(set(reasons[winner]))
    if source_effectively_silent:
        confidence = 0.30
    elif reliable_count == 0 and evidence_count <= 1:
        confidence = 0.35 if evidence_count else 0.25
    else:
        confidence = min(0.92, 0.40 + reliable_count * 0.10 + min(0.25, separation / 100.0) + min(0.08, evidence_count * 0.02))
    reason_codes = list(dict.fromkeys(reasons[winner])) or ["conservative_fallback"]
    if set(reason_codes).issubset({"mono_source", "conservative_fallback"}):
        confidence = min(confidence, 0.64 if reliable_count else 0.35)
    return {
        "preset": winner,
        "confidence": round(confidence, 2),
        "reasons": reason_codes,
        "reason_labels": [RECOMMENDATION_REASON_LABELS.get(reason, reason.replace("_", " ")) for reason in reason_codes],
        "metrics_used": list(dict.fromkeys(metrics_used)),
        "source_id": str(source.get("source_id") or ""),
        "safety": safety | {"excluded_presets": excluded},
        "candidate_scores": {name: round(scores[name], 2) for name in AUTO_REMASTER_PRESETS},
        "energy_summary": energy,
        "reliable_metric_count": reliable_count,
    }


def _reliable_recommendation_metrics(analysis: dict[str, Any] | None) -> dict[str, Any]:
    source_analysis = analysis if isinstance(analysis, dict) else {}
    metadata = source_analysis.get("metadata") or {}
    loudness = source_analysis.get("loudness") or {}
    silence = source_analysis.get("silence") or {}
    musical = source_analysis.get("musical") or {}
    return {
        "duration": metadata.get("duration_sec"),
        "integrated_loudness": loudness.get("integrated_lufs"),
        "true_peak_dbtp": loudness.get("true_peak_dbtp"),
        "lra_lu": loudness.get("lra_lu"),
        "channels": metadata.get("channels"),
        "energy_summary": _energy_summary(source_analysis),
        "leading_silence_sec": silence.get("leading_sec"),
        "trailing_silence_sec": silence.get("trailing_sec"),
        "internal_silence_regions": list(silence.get("internal_regions") or []),
        "measured_bpm": musical.get("bpm") if musical.get("bpm_status") == "ok" else None,
        "provenance": AUDIO_INTELLIGENCE_ANALYZER_VERSION,
    }


def build_remaster_recommendation(decision: dict[str, Any], analysis: dict[str, Any], metrics: dict[str, Any] | None = None, *, source: str = "audio_analysis") -> dict[str, Any]:
    _ = metrics
    confidence_value = max(0.0, min(1.0, float(decision.get("confidence") or 0.0)))
    score = int(round(confidence_value * 100))
    preset = str(decision.get("preset") or "Streaming Balanced")
    return {
        "source": source,
        "recommended_preset": preset,
        "selected_preset": preset,
        "confidence": _confidence_label(score),
        "confidence_score": score,
        "reasons": list(decision.get("reason_labels") or []),
        "metrics": _reliable_recommendation_metrics(analysis),
        "audio_intelligence": analysis,
        "recommendation_confidence": confidence_value,
        "recommendation_reasons": list(decision.get("reasons") or []),
        "recommendation_metrics_used": list(decision.get("metrics_used") or []),
        "recommendation_source_id": str(decision.get("source_id") or ""),
        "recommendation_safety": dict(decision.get("safety") or {}),
        "candidate_scores": dict(decision.get("candidate_scores") or {}),
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
    }


def remaster_recommendation_matches_source(recommendation: dict[str, Any] | None, audio_intelligence: dict[str, Any] | None) -> bool:
    stored = recommendation if isinstance(recommendation, dict) else {}
    if stored.get("source") != "audio_analysis":
        return True
    active = audio_intelligence if isinstance(audio_intelligence, dict) else {}
    active_source_id = str((active.get("source") or {}).get("source_id") or "")
    stored_source_id = str(
        stored.get("recommendation_source_id")
        or (((stored.get("audio_intelligence") or {}).get("source") or {}).get("source_id"))
        or ""
    )
    return bool(active_source_id and stored_source_id == active_source_id)


def recommend_remaster_preset_from_metadata(metadata: dict[str, Any] | str | None) -> dict[str, Any]:
    if isinstance(metadata, dict):
        text = " ".join(str(value) for value in metadata.values() if isinstance(value, (str, int, float, list, tuple, dict))).lower()
    else:
        text = str(metadata or "").lower()
    groups = {
        "Loud Modern": ["cheer", "stadium", "crowd", "chant", "high energy", "ตะโกน", "เชียร์", "สนาม", "พลัง", "มันส์"],
        "Modern Pop": ["edm", "trap", "dance", "808", "sub bass", "heavy bass", "electronic", "club", "เบสหนัก", "แดนซ์"],
        "Pop Rock": ["rock", "live band", "guitar", "strong snare", "drum kit", "pop rock", "ร็อก", "กีตาร์", "วงดนตรี"],
        "Vocal Focus": ["podcast", "narration", "spoken", "voice", "speech", "talk", "พอดแคสต์", "เล่าเรื่อง", "พูด", "บรรยาย"],
        "Warm Acoustic": ["ballad", "soft vocal", "acoustic", "emotional", "piano", "warm", "อะคูสติก", "อบอุ่น", "บัลลาด", "เศร้า"],
    }
    scores: dict[str, int] = {}
    reasons: dict[str, list[str]] = {}
    for preset, keywords in groups.items():
        matched = [keyword for keyword in keywords if keyword in text]
        scores[preset] = len(matched)
        reasons[preset] = matched
    best_preset = max(scores, key=lambda key: scores[key]) if scores else "Streaming Balanced"
    if scores.get(best_preset, 0) <= 0:
        best_preset = "Streaming Balanced"
    confidence_score = min(92, 42 + scores.get(best_preset, 0) * 17)
    reason_lines = [f"Project metadata contains: {', '.join(reasons.get(best_preset, [])[:5])}"] if reasons.get(best_preset) else ["Project metadata is mixed or limited; balanced preset is safest."]
    return {
        "source": "project_metadata",
        "recommended_preset": best_preset,
        "selected_preset": best_preset,
        "confidence": _confidence_label(confidence_score),
        "confidence_score": confidence_score,
        "reasons": reason_lines,
        "metrics": {"metadata_keyword_matches": scores, "matched_keywords": reasons.get(best_preset, [])},
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
    }


def _decode_analysis_pcm(path: Path, ffmpeg: str, *, sample_rate: int = 8000, max_duration: float = 360.0) -> dict[str, Any]:
    args = [ffmpeg, "-v", "error", "-i", str(path), "-map", "0:a:0", "-t", f"{max_duration:.3f}", "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-"]
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    except Exception as exc:
        return {"ok": False, "error": "decode_failed", "message": str(exc), "command": args}
    if proc.returncode != 0 or not proc.stdout:
        return {"ok": False, "error": "decode_failed", "message": (proc.stderr or b"Audio analysis failed").decode("utf-8", errors="replace")[:600], "command": args}
    samples = array("h")
    samples.frombytes(proc.stdout)
    return {"ok": bool(samples), "samples": samples, "sample_rate": sample_rate, "command": args}


def _probe_from_audio_intelligence(analysis: dict[str, Any]) -> dict[str, Any]:
    """Adapt authoritative Audio Intelligence facts to legacy output validation."""
    metadata = analysis.get("metadata") or {}
    codec = str(metadata.get("codec") or "")
    duration = metadata.get("duration_sec")
    sample_rate = metadata.get("sample_rate_hz")
    channels = metadata.get("channels")
    metadata_ok = metadata.get("status") in {"measured", "partial"} and bool(codec and duration and sample_rate and channels)
    return {
        "ok": bool(metadata_ok),
        "has_audio": bool(metadata_ok),
        "duration": duration,
        "audio_codec": codec,
        "audio_bit_rate": metadata.get("bitrate_bps"),
        "sample_rate": sample_rate,
        "channels": channels,
        "analysis_method": AUDIO_INTELLIGENCE_ANALYZER_VERSION,
    }


def _analysis_warning(analysis: dict[str, Any], label: str) -> str:
    details = [str(item) for item in [*(analysis.get("errors") or []), *(analysis.get("warnings") or [])] if item]
    return f"{label} Audio Intelligence analysis incomplete: {'; '.join(details) or 'measurement unavailable'}"


def analyze_remaster_quality_metrics(
    source_audio_path: str | Path,
    *,
    ffmpeg_path: str = "",
    max_duration: float = 360.0,
    source_context: dict[str, Any] | None = None,
    audio_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure transparent before/after proxies without changing the mastering chain."""
    source = Path(source_audio_path)
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not source.is_file() or not ffmpeg:
        return {"ok": False, "error": "missing_source_or_ffmpeg", "metrics": {}}
    analysis = audio_intelligence or analyze_audio_source(source, source_context, depth="deep", ffmpeg_path=ffmpeg)
    metadata = analysis.get("metadata") or {}
    loudness = analysis.get("loudness") or {}
    args = [ffmpeg, "-v", "error", "-i", str(source), "-map", "0:a:0", "-t", f"{max_duration:.3f}", "-ac", "2", "-ar", "8000", "-f", "s16le", "-"]
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=150)
    except Exception as exc:
        return {"ok": False, "error": f"decode_failed: {exc}", "metrics": {}}
    if proc.returncode != 0 or not proc.stdout:
        return {"ok": False, "error": "decode_failed", "metrics": {}}
    samples = array("h")
    samples.frombytes(proc.stdout)
    frame_count = len(samples) // 2
    if frame_count <= 0:
        return {"ok": False, "error": "empty_audio", "metrics": {}}
    sum_sq = sum_mid_sq = sum_side_sq = 0.0
    peak = 0.0
    for idx in range(0, frame_count * 2, 2):
        left = samples[idx] / 32768.0
        right = samples[idx + 1] / 32768.0
        sum_sq += (left * left + right * right) * 0.5
        mid = (left + right) * 0.5
        side = (left - right) * 0.5
        sum_mid_sq += mid * mid
        sum_side_sq += side * side
        peak = max(peak, abs(left), abs(right))
    rms = math.sqrt(sum_sq / frame_count)
    crest = peak / max(rms, 0.000001)
    stereo_width = math.sqrt(sum_side_sq / frame_count) / max(math.sqrt(sum_mid_sq / frame_count), 0.000001)
    metrics = {
        "integrated_lufs": loudness.get("integrated_lufs"),
        "true_peak_dbtp": loudness.get("true_peak_dbtp"),
        "lra_lu": loudness.get("lra_lu"),
        "peak_dbfs_proxy": round(20.0 * math.log10(max(peak, 0.000001)), 2),
        "rms_dbfs": round(20.0 * math.log10(max(rms, 0.000001)), 2),
        "crest_factor_db": round(20.0 * math.log10(max(crest, 0.000001)), 2),
        "stereo_width_proxy": round(min(4.0, stereo_width), 3),
        "duration": round(float(metadata.get("duration_sec") or frame_count / 8000.0), 3),
        "codec": metadata.get("codec"),
        "bitrate_bps": metadata.get("bitrate_bps"),
        "sample_rate": metadata.get("sample_rate_hz"),
        "channels": metadata.get("channels"),
    }
    return {
        "ok": True,
        "metrics": metrics,
        "method": f"{AUDIO_INTELLIGENCE_ANALYZER_VERSION} plus stereo PCM RMS/crest/width proxies",
        "audio_intelligence": analysis,
        "warnings": list(analysis.get("warnings") or []),
        "error": "; ".join(str(item) for item in analysis.get("errors") or []),
    }


def select_remaster_preview_range(source_audio_path: str | Path, *, ffmpeg_path: str = "", preview_duration: float = 15.0) -> dict[str, Any]:
    source = Path(source_audio_path)
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not source.is_file() or not ffmpeg:
        return {"ok": False, "start": 0.0, "duration": preview_duration, "error": "missing_source_or_ffmpeg"}
    probe = probe_media(source, ffmpeg_path=ffmpeg)
    duration = float(probe.get("duration") or 0.0)
    decoded = _decode_analysis_pcm(source, ffmpeg, sample_rate=4000, max_duration=min(480.0, duration or 480.0))
    if not decoded.get("ok") or duration <= 0:
        return {"ok": False, "start": 0.0, "duration": min(preview_duration, duration or preview_duration), "error": "analysis_unavailable"}
    samples = decoded["samples"]
    rate = int(decoded["sample_rate"])
    clip_duration = min(float(preview_duration), duration)
    window = max(1, int(clip_duration * rate))
    step = max(1, int(2.0 * rate))
    start_floor = 0 if duration <= clip_duration + 4 else int(2.0 * rate)
    end_limit = min(len(samples) - window, int(max(0.0, duration - clip_duration - 2.0) * rate))
    best_start, best_score = 0, -1.0
    for start in range(start_floor, max(start_floor, end_limit) + 1, step):
        chunk = samples[start : start + window]
        if not chunk:
            continue
        rms = math.sqrt(sum((value / 32768.0) ** 2 for value in chunk) / len(chunk))
        silence = sum(1 for value in chunk if abs(value) < 420) / len(chunk)
        score = rms * (1.0 - min(0.9, silence))
        if score > best_score:
            best_start, best_score = start, score
    return {"ok": True, "start": round(best_start / rate, 3), "duration": round(clip_duration, 3), "method": "highest stable non-silent RMS window", "error": ""}


def _comparison_direction(before: float | None, after: float | None, *, tolerance: float = 0.25) -> str:
    if before is None or after is None:
        return "Unknown"
    delta = after - before
    if abs(delta) <= tolerance:
        return "Similar"
    return "Higher" if delta > 0 else "Lower"


def build_remaster_quality_comparison(
    original_path: str | Path,
    mastered_path: str | Path,
    *,
    ffmpeg_path: str = "",
    original_context: dict[str, Any] | None = None,
    mastered_context: dict[str, Any] | None = None,
    original_analysis: dict[str, Any] | None = None,
    mastered_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    before = analyze_remaster_quality_metrics(
        original_path,
        ffmpeg_path=ffmpeg_path,
        source_context=original_context,
        audio_intelligence=original_analysis,
    )
    after = analyze_remaster_quality_metrics(
        mastered_path,
        ffmpeg_path=ffmpeg_path,
        source_context=mastered_context,
        audio_intelligence=mastered_analysis,
    )
    before_metrics = before.get("metrics", {})
    after_metrics = after.get("metrics", {})
    return {
        "ok": bool(before.get("ok") and after.get("ok")),
        "original": before_metrics,
        "mastered": after_metrics,
        "summary": {
            "loudness": _comparison_direction(before_metrics.get("integrated_lufs"), after_metrics.get("integrated_lufs")),
            "true_peak": _comparison_direction(before_metrics.get("true_peak_dbtp"), after_metrics.get("true_peak_dbtp")),
            "lra": _comparison_direction(before_metrics.get("lra_lu"), after_metrics.get("lra_lu")),
            "peak": _comparison_direction(before_metrics.get("peak_dbfs_proxy"), after_metrics.get("peak_dbfs_proxy")),
            "rms": _comparison_direction(before_metrics.get("rms_dbfs"), after_metrics.get("rms_dbfs")),
            "dynamics": _comparison_direction(before_metrics.get("crest_factor_db"), after_metrics.get("crest_factor_db")),
            "stereo_width": _comparison_direction(before_metrics.get("stereo_width_proxy"), after_metrics.get("stereo_width_proxy"), tolerance=0.04),
        },
        "method": f"{AUDIO_INTELLIGENCE_ANALYZER_VERSION}; RMS, crest, and width remain PCM proxies.",
        "analysis": {"before": before.get("audio_intelligence") or {}, "after": after.get("audio_intelligence") or {}},
        "errors": [item for item in [before.get("error"), after.get("error")] if item],
    }


def build_remaster_ab_previews(original_path: str | Path, mastered_path: str | Path, output_dir: str | Path, *, ffmpeg_path: str = "", preview_duration: float = 15.0) -> dict[str, Any]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    selected = select_remaster_preview_range(original_path, ffmpeg_path=ffmpeg, preview_duration=preview_duration)
    if not ffmpeg or not selected.get("ok"):
        return {"ok": False, "error": selected.get("error") or "missing_ffmpeg"}
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    original_preview = output / "quality_preview_original.mp3"
    mastered_preview = output / "quality_preview_mastered.mp3"
    results = []
    for source, target in ((Path(original_path), original_preview), (Path(mastered_path), mastered_preview)):
        results.append(_run([ffmpeg, "-y", "-ss", str(selected["start"]), "-t", str(selected["duration"]), "-i", str(source), "-vn", "-c:a", "libmp3lame", "-b:a", "320k", "-ar", "48000", "-ac", "2", str(target)], timeout=120))
    ok = all(item.get("ok") for item in results) and original_preview.is_file() and mastered_preview.is_file()
    return {
        "ok": ok,
        "start": selected["start"],
        "duration": selected["duration"],
        "original_preview": str(original_preview) if original_preview.is_file() else "",
        "mastered_preview": str(mastered_preview) if mastered_preview.is_file() else "",
        "format": "audio/mpeg",
        "selection_method": selected.get("method", ""),
        "error": "" if ok else "preview_generation_failed",
    }


def analyze_audio_for_remaster_recommendation(
    source_audio_path: str | Path,
    *,
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
    source_context: dict[str, Any] | None = None,
    audio_intelligence: dict[str, Any] | None = None,
    metadata: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    source = Path(source_audio_path)
    validation = validate_remaster_input(source, max_upload_mb=max_upload_mb)
    if not validation.get("ok"):
        return {"ok": False, "message": validation.get("message", "Invalid audio"), "error": validation.get("error", "invalid_audio")}
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "message": "FFmpeg not found", "error": "missing_ffmpeg"}
    analysis = audio_intelligence or analyze_audio_source(source, source_context, depth="deep", ffmpeg_path=ffmpeg)
    probe = _probe_from_audio_intelligence(analysis)
    if not probe.get("ok") or not probe.get("has_audio", True):
        probe = probe_media(source, ffmpeg_path=ffmpeg)
    if not probe.get("ok") or not probe.get("has_audio", True):
        return {"ok": False, "message": "Invalid or corrupt audio file", "error": "invalid_audio", "data": {"probe": probe}}
    decision = recommend_remaster_preset(analysis, metadata=metadata)
    recommendation = build_remaster_recommendation(decision, analysis)
    return {"ok": True, "data": recommendation, "error": ""}


def _source_ext(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def validate_remaster_input(path: str | Path, *, max_upload_mb: int = 200) -> dict[str, Any]:
    source = Path(path)
    ext = _source_ext(source)
    if not source.is_file():
        return {"ok": False, "error": "missing_audio", "message": "Source audio missing"}
    if ext not in {"mp3", "wav"}:
        return {"ok": False, "error": "unsupported_format", "message": "Only MP3 and WAV are supported in Remaster Studio V1"}
    size_mb = source.stat().st_size / (1024 * 1024)
    if size_mb > max_upload_mb:
        return {"ok": False, "error": "file_too_large", "message": f"Audio exceeds the {max_upload_mb} MB upload limit"}
    return {"ok": True, "error": "", "message": "", "format": ext, "size_mb": round(size_mb, 3)}


def build_remaster_project_id(original_name: str) -> str:
    stem = sanitize_filename(Path(original_name).stem or "remaster")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return safe_name(f"{stem}_{stamp}")


def _report_text(report: dict[str, Any]) -> str:
    def measured(value: Any, unit: str) -> str:
        return f"{value} {unit}" if isinstance(value, (int, float)) else "unavailable"

    lines = [
        "VELAFLOW REMASTER REPORT",
        "",
        f"Overall status: {report.get('overall_status', report.get('status', 'failed'))}",
        f"WAV status: {report.get('wav_status', 'unknown')}",
        f"MP3 status: {report.get('mp3_status', 'unknown')}",
        f"Duration status: {report.get('duration_status', 'unknown')}",
        f"Clipping validation: {(report.get('clipping_validation') or {}).get('status', 'unknown')}",
        f"Original filename: {report.get('original_filename', '')}",
        f"Input format: {report.get('input_format', '')}",
        f"Input sample rate: {report.get('input_sample_rate', 'unknown')}",
        f"Input duration: {report.get('input_duration', 0)}",
        f"Selected preset: {report.get('selected_preset', '')}",
        f"Preset mode: {report.get('preset_mode', '')}",
        f"Preset name: {report.get('preset_name', '')}",
        "",
        "Processing steps applied:",
        *[f"- {step}" for step in report.get("processing_steps_applied", [])],
        "",
        f"Output WAV settings: {report.get('output_wav_settings', {})}",
        f"Output MP3 settings: {report.get('output_mp3_settings', {})}",
        f"Analysis method: {report.get('analysis_method', 'unknown')}",
        f"Loudness method: {report.get('loudness_method', 'unknown')}",
        f"Measured loudness result: {measured(report.get('loudness_result'), 'LUFS')}",
        f"Measured true peak result: {measured(report.get('peak_result'), 'dBTP')}",
        f"Measured loudness range: {measured(report.get('lra_result'), 'LU')}",
        f"Target loudness: {report.get('target_loudness', '')}",
        f"Target true peak: {report.get('target_true_peak', '')}",
        "Warnings: " + (", ".join(report.get("warnings", [])) if report.get("warnings") else "None"),
        f"Processing date/time: {report.get('processing_date_time', '')}",
    ]
    recommendation = report.get("remaster_recommendation") or {}
    custom_settings = report.get("custom_settings") or {}
    if custom_settings:
        lines += ["", "Resolved Custom Settings:"]
        lines.extend(f"- {key}: {value}" for key, value in custom_settings.items())
    reference = report.get("reference") or {}
    reference_comparison = report.get("reference_comparison") or {}
    if reference:
        lines += [
            "",
            "Reference-Guided Master:",
            f"Reference: {reference.get('filename', '')}",
            f"Reference source ID: {reference.get('source_id', '')}",
            f"Reference metrics: {reference.get('metrics', {})}",
            f"Targets: {report.get('targets', {})}",
            f"Resolved settings: {report.get('resolved_settings', {})}",
            f"Result metrics: {report.get('result_metrics', {})}",
            f"Unsupported matches: {report.get('unsupported_matches', [])}",
            f"Analysis provenance: {report.get('analysis_provenance', '')}",
            f"Source / Reference / Result: {reference_comparison}",
        ]
    if recommendation:
        lines += [
            "",
            "Preset Recommendation:",
            f"Input source: {recommendation.get('input_source', '')}",
            f"Recommendation source: {recommendation.get('source', '')}",
            f"Recommended preset: {recommendation.get('recommended_preset', '')}",
            f"Confidence: {recommendation.get('confidence', '')}",
            f"User-selected preset: {recommendation.get('selected_preset', report.get('selected_preset', ''))}",
            f"Recommendation overridden: {'Yes' if recommendation.get('overridden') else 'No'}",
            "Why this preset:",
            *[f"- {reason}" for reason in recommendation.get("reasons", [])],
        ]
    comparison = report.get("quality_comparison") or {}
    if comparison:
        lines += [
            "",
            "Before / After Quality Summary:",
            f"Before measured values: {comparison.get('original', {})}",
            f"After measured values: {comparison.get('mastered', {})}",
            f"Loudness: {(comparison.get('summary') or {}).get('loudness', 'Unknown')}",
            f"True peak: {(comparison.get('summary') or {}).get('true_peak', 'Unknown')}",
            f"Loudness range: {(comparison.get('summary') or {}).get('lra', 'Unknown')}",
            f"RMS: {(comparison.get('summary') or {}).get('rms', 'Unknown')}",
            f"Dynamics / crest proxy: {(comparison.get('summary') or {}).get('dynamics', 'Unknown')}",
            f"Stereo width proxy: {(comparison.get('summary') or {}).get('stereo_width', 'Unknown')}",
        ]
    return "\n".join(lines)


def build_clipping_validation(max_volume_db: Any) -> dict[str, Any]:
    """Classify measured clipping without treating unavailable data as a pass."""
    try:
        measured_peak = float(max_volume_db)
    except (TypeError, ValueError):
        return {
            "status": "unknown",
            "measured_peak_db": None,
            "no_clipping_above_0db": None,
            "reason": "Peak measurement unavailable.",
        }
    passed = measured_peak <= 0.0
    return {
        "status": "pass" if passed else "fail",
        "measured_peak_db": measured_peak,
        "no_clipping_above_0db": passed,
        "reason": "Peak is at or below 0 dB." if passed else "Peak exceeds 0 dB.",
    }


def validate_remaster_outputs(
    source_probe: dict[str, Any],
    wav_path: str | Path,
    wav_probe: dict[str, Any],
    mp3_path: str | Path,
    mp3_probe: dict[str, Any],
    *,
    wav_command_ok: bool = True,
    mp3_command_ok: bool = True,
    duration_tolerance: float = 0.25,
) -> dict[str, Any]:
    """Classify required remaster deliverables as success, partial, or failed."""
    source_duration = float(source_probe.get("duration") or 0.0)

    def inspect(path_value: str | Path, probe: dict[str, Any], expected: str, command_ok: bool) -> dict[str, Any]:
        path = Path(path_value)
        codec = str(probe.get("audio_codec") or "").lower()
        duration = float(probe.get("duration") or 0.0)
        codec_ok = codec.startswith("pcm") if expected == "wav" else codec == "mp3"
        delta = abs(source_duration - duration) if source_duration > 0 and duration > 0 else None
        duration_ok = delta is not None and delta <= duration_tolerance
        checks = {
            "command_ok": bool(command_ok),
            "file_exists": path.is_file(),
            "file_nonempty": path.is_file() and path.stat().st_size > 0,
            "probe_ok": bool(probe.get("ok") and probe.get("has_audio", True)),
            "codec_ok": codec_ok,
            "duration_ok": duration_ok,
        }
        return {
            "status": "pass" if all(checks.values()) else "fail",
            "checks": checks,
            "codec": codec,
            "duration": duration,
            "duration_delta_seconds": round(delta, 3) if delta is not None else None,
        }

    wav_result = inspect(wav_path, wav_probe, "wav", wav_command_ok)
    mp3_result = inspect(mp3_path, mp3_probe, "mp3", mp3_command_ok)
    if wav_result["status"] != "pass":
        overall_status = "failed"
    elif mp3_result["status"] != "pass":
        overall_status = "partial"
    else:
        overall_status = "success"
    duration_status = "pass" if wav_result["checks"]["duration_ok"] and mp3_result["checks"]["duration_ok"] else "fail"
    return {
        "ok": overall_status == "success",
        "overall_status": overall_status,
        "wav_status": wav_result["status"],
        "mp3_status": mp3_result["status"],
        "duration_status": duration_status,
        "wav_validation": wav_result,
        "mp3_validation": mp3_result,
    }


def remaster_song_audio(
    source_audio_path: str | Path,
    *,
    project_name: str = "remaster_project",
    remaster_style: str = "Streaming Balanced",
    ffmpeg_path: str = "",
    max_upload_mb: int = 200,
    recommendation_data: dict[str, Any] | None = None,
    preset_mode: str = "",
    custom_settings: dict[str, Any] | None = None,
    source_context: dict[str, Any] | None = None,
    reference_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = Path(source_audio_path)
    ffmpeg = ffmpeg_path or find_ffmpeg()
    input_validation = validate_remaster_input(source, max_upload_mb=max_upload_mb)
    if not input_validation.get("ok"):
        return {"ok": False, "status": "failed", "message": input_validation.get("message", "Invalid audio"), "data": {"overall_status": "failed", "validation": input_validation}, "error": input_validation.get("error", "invalid_audio")}
    if not ffmpeg:
        return {
            "ok": False,
            "status": "failed",
            "message": "FFmpeg not found. Install on Debian with: sudo apt-get update && sudo apt-get install -y ffmpeg",
            "data": {"overall_status": "failed", "setup_hint": "sudo apt-get update && sudo apt-get install -y ffmpeg"},
            "error": "missing_ffmpeg",
        }

    requested_style = _normalize_style(remaster_style)
    requested_reference_plan = dict(reference_plan or {}) if requested_style == REFERENCE_GUIDED_PRESET else {}
    if requested_style == REFERENCE_GUIDED_PRESET and (
        requested_reference_plan.get("mode") != "reference"
        or not requested_reference_plan.get("source_source_id")
        or not requested_reference_plan.get("reference_source_id")
        or not isinstance(requested_reference_plan.get("resolved_custom_settings"), dict)
    ):
        return {
            "ok": False,
            "status": "failed",
            "message": "Reference Track is not ready. Analyze a valid reference before processing.",
            "data": {"overall_status": "failed"},
            "error": "invalid_reference_plan",
        }

    project_id = build_remaster_project_id(project_name or source.stem)
    base_dir = ROOT / "exports" / "remaster" / project_id
    original_dir = base_dir / "original"
    output_dir = base_dir / "output"
    reports_dir = base_dir / "reports"
    original_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    source_copy = original_dir / f"source_audio.{_source_ext(source)}"
    shutil.copy2(source, source_copy)
    wav_path = output_dir / build_asset_export_filename(project_name, source.name, "Master", "wav")
    mp3_path = output_dir / build_asset_export_filename(project_name, source.name, "Master", "mp3")
    report_path = reports_dir / build_asset_export_filename(project_name, source.name, "Remaster_Report", "json")
    report_txt_path = reports_dir / build_asset_export_filename(project_name, source.name, "Remaster_Report", "txt")
    legacy_report_path = reports_dir / "mastering_report.json"
    zip_path = ensure_unique_path(base_dir / build_asset_export_filename(project_name, source.name, "Remaster_Package", "zip"))
    converted_path = output_dir / "source_converted_48k_24bit.wav"
    style = requested_style
    reference_mode = style == REFERENCE_GUIDED_PRESET
    resolved_reference_plan = requested_reference_plan
    if reference_mode:
        requested_targets = resolved_reference_plan.get("targets") or {}
        requested_settings = resolved_reference_plan["resolved_custom_settings"]
        requested_lufs = _finite_metric(requested_targets.get("lufs", requested_settings.get("loudness_lufs")))
        requested_true_peak = _finite_metric(requested_targets.get("true_peak_dbtp", requested_settings.get("output_ceiling_db")))
        target_lufs = max(
            REFERENCE_TARGET_LUFS_RANGE[0],
            min(REFERENCE_TARGET_LUFS_RANGE[1], requested_lufs if requested_lufs is not None else -14.0),
        )
        target_true_peak = min(
            REFERENCE_TARGET_TRUE_PEAK_RANGE[1],
            max(REFERENCE_TARGET_TRUE_PEAK_RANGE[0], requested_true_peak if requested_true_peak is not None else -1.0),
        )
        resolved_custom_settings = sanitize_custom_remaster_settings(
            {
                "loudness_lufs": target_lufs,
                "bass_db": 0.0,
                "mid_db": 0.0,
                "high_db": 0.0,
                "compression_ratio": CUSTOM_REMASTER_LIMITS["compression_ratio"][0],
                "stereo_width": 1.0,
                "output_ceiling_db": target_true_peak,
            }
        )
        resolved_reference_plan["targets"] = {
            "lufs": resolved_custom_settings["loudness_lufs"],
            "true_peak_dbtp": resolved_custom_settings["output_ceiling_db"],
        }
        resolved_reference_plan["resolved_custom_settings"] = resolved_custom_settings
        style_config = build_custom_remaster_config(resolved_custom_settings)
    else:
        resolved_custom_settings = sanitize_custom_remaster_settings(custom_settings) if style == "Custom" else {}
        style_config = build_custom_remaster_config(resolved_custom_settings) if style == "Custom" else STYLE_FILTERS[style]
    recommendation = dict(recommendation_data or {})
    resolved_preset_mode = str(preset_mode or recommendation.get("preset_mode") or ("manual" if style in {"Custom", REFERENCE_GUIDED_PRESET} or recommendation.get("source") == "manual" else "auto")).strip().lower()
    if resolved_preset_mode not in {"auto", "manual"}:
        resolved_preset_mode = "manual" if style in {"Custom", REFERENCE_GUIDED_PRESET} else "auto"
    resolved_preset_name = "reference-guided" if reference_mode else "custom" if style == "Custom" else style
    if recommendation:
        recommendation["selected_preset"] = style
        recommendation["overridden"] = bool(recommendation.get("recommended_preset") and recommendation.get("recommended_preset") != style)
        recommendation["preset_mode"] = resolved_preset_mode
        recommendation["preset_name"] = resolved_preset_name
        if resolved_custom_settings:
            recommendation["custom_settings"] = resolved_custom_settings
        if reference_mode:
            recommendation["source"] = "reference"
            recommendation["reference_source_id"] = resolved_reference_plan.get("reference_source_id", "")
    resolved_source_context = dict(source_context or {})
    resolved_source_context.setdefault("kind", "file")
    resolved_source_context.setdefault("project_id", project_name)
    resolved_source_context.setdefault("path_role", "remaster_source")
    source_analysis = analyze_audio_source(source, resolved_source_context, depth="deep", ffmpeg_path=ffmpeg)
    if reference_mode and str((source_analysis.get("source") or {}).get("source_id") or "") != str(resolved_reference_plan.get("source_source_id") or ""):
        return {
            "ok": False,
            "status": "failed",
            "message": "Source changed after Reference Track analysis. Analyze the reference again.",
            "data": {"overall_status": "failed", "audio_intelligence": {"before": source_analysis}},
            "error": "reference_source_changed",
        }
    source_probe = _probe_from_audio_intelligence(source_analysis)
    source_probe_fallback_used = False
    if not source_probe.get("ok"):
        # Operational validation may fall back, but report measurements stay null.
        source_probe = probe_media(source, ffmpeg_path=ffmpeg)
        source_probe_fallback_used = True
    if not source_probe.get("ok") or not source_probe.get("has_audio", True):
        return {
            "ok": False,
            "status": "failed",
            "message": "Invalid or corrupt audio file",
            "data": {"overall_status": "failed", "source_probe": source_probe, "audio_intelligence": {"before": source_analysis}},
            "error": "invalid_audio",
        }
    convert = _run([ffmpeg, "-y", "-i", str(source), "-vn", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(converted_path)])
    if not convert.get("ok"):
        return {"ok": False, "status": "failed", "message": "Audio conversion failed", "data": {"overall_status": "failed", "command": convert.get("command", [])}, "error": "audio_convert_failed"}

    filters = style_config["filters"]
    wav = _run([ffmpeg, "-y", "-i", str(converted_path), "-vn", "-af", filters, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(wav_path)])
    master_context = {
        "kind": "remaster_master",
        "project_id": str(resolved_source_context.get("project_id") or project_name),
        "path_role": "final_master_wav",
    }
    master_analysis = analyze_audio_source(wav_path, master_context, depth="deep", ffmpeg_path=ffmpeg)
    wav_probe = _probe_from_audio_intelligence(master_analysis)
    wav_probe_fallback_used = False
    if wav_path.is_file() and not wav_probe.get("ok"):
        wav_probe = probe_media(wav_path, ffmpeg_path=ffmpeg)
        wav_probe_fallback_used = True
    max_volume = _max_volume_db(ffmpeg, wav_path) if wav_path.is_file() else None
    clipping_validation = build_clipping_validation(max_volume)
    no_clipping = clipping_validation["no_clipping_above_0db"]
    if not wav.get("ok") or not wav_probe.get("ok") or clipping_validation["status"] == "fail":
        report = {
            "ok": False,
            "overall_status": "failed",
            "wav_status": "failed",
            "mp3_status": "not_attempted",
            "duration_status": "failed",
            "style": style,
            "preset_mode": resolved_preset_mode,
            "preset_name": resolved_preset_name,
            "custom_settings": resolved_custom_settings,
            "reference": dict(resolved_reference_plan.get("reference") or {}),
            "targets": dict(resolved_reference_plan.get("targets") or {}),
            "resolved_settings": resolved_custom_settings if reference_mode else {},
            "unsupported_matches": list(resolved_reference_plan.get("unsupported_matches") or []),
            "analysis_provenance": resolved_reference_plan.get("analysis_provenance", ""),
            "export_name": project_name,
            "source_path": str(source_copy),
            "mastered_wav": str(wav_path),
            "source_probe": source_probe,
            "wav_probe": wav_probe,
            "audio_intelligence": {"before": source_analysis, "after": master_analysis},
            "max_volume_db": max_volume,
            "no_clipping_above_0db": no_clipping,
            "clipping_validation": clipping_validation,
            "remaster_recommendation": recommendation,
            "error": "master_wav_failed" if wav.get("ok") else wav.get("output", "master_wav_failed")[:1200],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        ensure_parent_dir(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        ensure_parent_dir(legacy_report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        ensure_parent_dir(report_txt_path).write_text(_report_text(report), encoding="utf-8")
        return {"ok": False, "status": "failed", "message": "Mastered WAV failed validation", "data": {"overall_status": "failed", "report_path": str(report_path), "report": report}, "error": "master_wav_failed"}

    mp3 = _run([ffmpeg, "-y", "-i", str(wav_path), "-vn", "-c:a", "libmp3lame", "-b:a", "320k", "-minrate", "320k", "-maxrate", "320k", "-ar", "48000", "-ac", "2", "-write_xing", "0", str(mp3_path)])
    mp3_probe = probe_media(mp3_path, ffmpeg_path=ffmpeg) if mp3_path.is_file() else {"ok": False}
    output_validation = validate_remaster_outputs(
        source_probe,
        wav_path,
        wav_probe,
        mp3_path,
        mp3_probe,
        wav_command_ok=bool(wav.get("ok")),
        mp3_command_ok=bool(mp3.get("ok")),
    )
    overall_status = output_validation["overall_status"]
    duration_delta = output_validation["wav_validation"].get("duration_delta_seconds")
    warnings: list[str] = list(resolved_reference_plan.get("warnings") or [])
    if source_analysis.get("errors") or (source_analysis.get("loudness") or {}).get("status") != "measured":
        warnings.append(_analysis_warning(source_analysis, "Source"))
    if master_analysis.get("errors") or (master_analysis.get("loudness") or {}).get("status") != "measured":
        warnings.append(_analysis_warning(master_analysis, "Master"))
    if source_probe_fallback_used:
        warnings.append("Source metadata used operational FFprobe fallback; authoritative Audio Intelligence values remain unchanged.")
    if wav_probe_fallback_used:
        warnings.append("Master metadata used operational FFprobe fallback; authoritative Audio Intelligence values remain unchanged.")
    if max_volume is None:
        warnings.append("Legacy clipping validation is unavailable; Audio Intelligence true peak is reported separately.")
    if not mp3.get("ok"):
        warnings.append("MP3 export failed.")
    elif output_validation["mp3_status"] != "pass":
        warnings.append("MP3 export failed codec, file, or duration validation.")
    quality_comparison = build_remaster_quality_comparison(
        source,
        wav_path,
        ffmpeg_path=ffmpeg,
        original_context=resolved_source_context,
        mastered_context=master_context,
        original_analysis=source_analysis,
        mastered_analysis=master_analysis,
    )
    reference_comparison = build_reference_result_comparison(resolved_reference_plan, master_analysis) if reference_mode else {}
    ab_previews = (
        build_remaster_ab_previews(source_copy, mp3_path, output_dir / "quality_previews", ffmpeg_path=ffmpeg)
        if output_validation["mp3_status"] == "pass"
        else {"ok": False, "error": "mastered_distribution_mp3_unavailable"}
    )
    processing_steps = [
        "Input validation",
        "Source copy preserved in original/",
        "48 kHz stereo PCM 24-bit conversion",
        "DC click/pop cleanup where detectable",
        "High-pass filtering",
        "Light compression",
        "Reference-guided loudness normalization",
        "VelaFlow-safe output limiting",
        "WAV + MP3 export",
    ] if reference_mode else [
        "Input validation",
        "Source copy preserved in original/",
        "48 kHz stereo PCM 24-bit conversion",
        "DC click/pop cleanup where detectable",
        "High-pass filtering",
        "Corrective EQ",
        "Gentle compression",
        "Preset stereo/space enhancement where configured",
        "Loudness normalization",
        "True-peak style limiting",
        "WAV + MP3 export",
    ]
    report = {
        "ok": overall_status == "success",
        "overall_status": overall_status,
        "wav_status": output_validation["wav_status"],
        "mp3_status": output_validation["mp3_status"],
        "duration_status": output_validation["duration_status"],
        "project_id": project_id,
        "source_context": resolved_source_context,
        "original_filename": source.name,
        "export_name": project_name,
        "input_format": input_validation.get("format"),
        "input_codec": (source_analysis.get("metadata") or {}).get("codec"),
        "input_bitrate_bps": (source_analysis.get("metadata") or {}).get("bitrate_bps"),
        "input_sample_rate": (source_analysis.get("metadata") or {}).get("sample_rate_hz"),
        "input_duration": (source_analysis.get("metadata") or {}).get("duration_sec"),
        "input_channels": (source_analysis.get("metadata") or {}).get("channels"),
        "input_loudness": (source_analysis.get("loudness") or {}).get("integrated_lufs"),
        "input_true_peak_dbtp": (source_analysis.get("loudness") or {}).get("true_peak_dbtp"),
        "input_lra_lu": (source_analysis.get("loudness") or {}).get("lra_lu"),
        "input_peak_level": (source_analysis.get("loudness") or {}).get("true_peak_dbtp"),
        "selected_preset": style,
        "preset_mode": resolved_preset_mode,
        "preset_name": resolved_preset_name,
        "custom_settings": resolved_custom_settings,
        "reference": dict(resolved_reference_plan.get("reference") or {}),
        "targets": dict(resolved_reference_plan.get("targets") or {}),
        "resolved_settings": resolved_custom_settings if reference_mode else {},
        "result_metrics": dict(reference_comparison.get("result") or {}),
        "unsupported_matches": list(resolved_reference_plan.get("unsupported_matches") or []),
        "reference_comparison": reference_comparison,
        "analysis_provenance": resolved_reference_plan.get("analysis_provenance", AUDIO_INTELLIGENCE_ANALYZER_VERSION if reference_mode else ""),
        "remaster_recommendation": recommendation,
        "processing_steps_applied": processing_steps,
        "output_wav_settings": {"format": "WAV", "codec": "pcm_s24le", "bit_depth": "24-bit", "sample_rate_hz": 48000, "channels": "stereo", "lossless": True},
        "output_mp3_settings": {"format": "MP3", "codec": "libmp3lame", "bitrate": "320 kbps", "mode": "CBR", "channels": "stereo"},
        "loudness_result": (master_analysis.get("loudness") or {}).get("integrated_lufs"),
        "peak_result": (master_analysis.get("loudness") or {}).get("true_peak_dbtp"),
        "lra_result": (master_analysis.get("loudness") or {}).get("lra_lu"),
        "target_loudness": style_config.get("target_lufs", ""),
        "target_true_peak": style_config.get("true_peak", ""),
        "warnings": warnings,
        "processing_date_time": datetime.now().isoformat(timespec="seconds"),
        "style": style,
        "source_path": str(source_copy),
        "converted_wav": str(converted_path),
        "mastered_wav": str(wav_path),
        "mp3_preview": str(mp3_path) if mp3_path.is_file() else "",
        "mastered_mp3": str(mp3_path) if mp3_path.is_file() else "",
        "source_probe": source_probe,
        "wav_probe": wav_probe,
        "mp3_probe": mp3_probe,
        "audio_intelligence": {"before": source_analysis, "after": master_analysis},
        "analysis_method": AUDIO_INTELLIGENCE_ANALYZER_VERSION,
        "loudness_method": "ffmpeg_loudnorm",
        "duration_matches_original": output_validation["duration_status"] == "pass",
        "duration_delta_seconds": duration_delta,
        "max_volume_db": max_volume,
        "no_clipping_above_0db": no_clipping,
        "clipping_validation": clipping_validation,
        "output_validation": output_validation,
        "filters": filters,
        "preset_summary": style_config.get("summary", ""),
        "quality_comparison": quality_comparison,
        "ab_previews": ab_previews,
        "external_api_used": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    ensure_parent_dir(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    ensure_parent_dir(legacy_report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    ensure_parent_dir(report_txt_path).write_text(_report_text(report), encoding="utf-8")
    if overall_status in {"success", "partial"}:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in [source_copy, wav_path, mp3_path, report_path, report_txt_path]:
                if path.is_file():
                    archive.write(path, str(path.relative_to(base_dir)))
    if overall_status == "success":
        message = "Remaster ready"
        error = ""
    elif overall_status == "partial":
        message = "Remaster partially completed: WAV is valid but MP3 is unavailable or invalid."
        error = "master_mp3_failed"
    else:
        message = "Remaster failed output validation."
        error = "master_output_validation_failed"
    return {
        "ok": overall_status == "success",
        "status": overall_status,
        "message": message,
        "data": {
            "overall_status": overall_status,
            "project_id": project_id,
            "original_audio": str(source_copy),
            "export_name": project_name,
            "mastered_wav": str(wav_path) if output_validation["wav_status"] == "pass" else "",
            "mp3_preview": str(mp3_path) if output_validation["mp3_status"] == "pass" else "",
            "mastered_mp3": str(mp3_path) if output_validation["mp3_status"] == "pass" else "",
            "report_path": str(report_path),
            "report_txt_path": str(report_txt_path),
            "zip_path": str(zip_path) if zip_path.is_file() and overall_status in {"success", "partial"} else "",
            "report": report,
            "quality_comparison": quality_comparison,
            "reference_comparison": reference_comparison,
            "ab_previews": ab_previews,
        },
        "error": error,
    }
