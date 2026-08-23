from __future__ import annotations

import math
import time
from array import array
from typing import Any, Sequence

import numpy as np


BPM_METHOD = "onset_energy_autocorrelation_v1"
MIN_BPM = 50.0
MAX_BPM = 200.0
FRAME_SEC = 0.040
HOP_SEC = 0.010
MIN_AUDIO_SEC = 6.0
MIN_ONSET_COUNT = 5


def _unknown(status: str = "unavailable", *, elapsed_ms: float = 0.0, reason: str = "insufficient_evidence") -> dict[str, Any]:
    return {
        "bpm": None,
        "bpm_confidence": 0.0,
        "bpm_method": BPM_METHOD,
        "bpm_status": status,
        "bpm_elapsed_ms": round(max(0.0, elapsed_ms), 3),
        "bpm_reason": reason,
    }


def _moving_average(values: np.ndarray, width: int) -> np.ndarray:
    if width <= 1 or values.size == 0:
        return values.copy()
    kernel = np.ones(width, dtype=np.float64) / float(width)
    return np.convolve(values, kernel, mode="same")


def build_onset_envelope(samples: Sequence[int] | array, sample_rate: int) -> dict[str, Any]:
    """Build a 100 Hz onset envelope from positive short-time RMS changes."""
    rate = int(sample_rate or 0)
    signal = np.asarray(samples, dtype=np.float32)
    duration = signal.size / float(rate) if rate > 0 else 0.0
    if rate <= 0 or signal.size < max(1, int(MIN_AUDIO_SEC * rate)):
        return {"ok": False, "reason": "audio_too_short", "duration_sec": duration, "envelope": np.array([], dtype=np.float64), "hop_sec": HOP_SEC}
    signal = signal / 32768.0
    frame_size = max(8, int(round(FRAME_SEC * rate)))
    hop_size = max(1, int(round(HOP_SEC * rate)))
    if signal.size < frame_size:
        return {"ok": False, "reason": "audio_too_short", "duration_sec": duration, "envelope": np.array([], dtype=np.float64), "hop_sec": HOP_SEC}

    squared = signal * signal
    cumulative = np.concatenate(([0.0], np.cumsum(squared, dtype=np.float64)))
    starts = np.arange(0, signal.size - frame_size + 1, hop_size, dtype=np.int64)
    frame_energy = (cumulative[starts + frame_size] - cumulative[starts]) / float(frame_size)
    rms = np.sqrt(np.maximum(frame_energy, 0.0))
    log_rms = np.log1p(100.0 * rms)
    positive_change = np.maximum(0.0, np.diff(log_rms, prepend=log_rms[0]))
    slow_trend = _moving_average(positive_change, max(3, int(round(0.50 / HOP_SEC))))
    onset = np.maximum(0.0, positive_change - 0.45 * slow_trend)
    onset = _moving_average(onset, 3)
    robust_peak = max(float(np.percentile(onset, 95.0)), float(np.max(onset)) * 0.25) if onset.size else 0.0
    if not math.isfinite(robust_peak) or robust_peak <= 1e-5:
        return {"ok": False, "reason": "no_onset_activity", "duration_sec": duration, "envelope": onset, "hop_sec": HOP_SEC}
    onset = np.clip(onset / robust_peak, 0.0, 2.0)
    return {
        "ok": True,
        "reason": "",
        "duration_sec": duration,
        "envelope": onset,
        "hop_sec": hop_size / float(rate),
        "frame_sec": frame_size / float(rate),
    }


def _detect_onset_peaks(envelope: np.ndarray, hop_sec: float) -> np.ndarray:
    if envelope.size < 3:
        return np.array([], dtype=np.int64)
    median = float(np.median(envelope))
    mad = float(np.median(np.abs(envelope - median)))
    threshold = max(0.12, median + 2.5 * mad, float(np.percentile(envelope, 75.0)) * 0.55)
    local = np.flatnonzero((envelope[1:-1] >= envelope[:-2]) & (envelope[1:-1] > envelope[2:]) & (envelope[1:-1] >= threshold)) + 1
    if local.size == 0:
        return local
    refractory = max(1, int(round(0.18 / hop_sec)))
    selected: list[int] = []
    for index in local:
        position = int(index)
        if not selected or position - selected[-1] >= refractory:
            selected.append(position)
        elif envelope[position] > envelope[selected[-1]]:
            selected[-1] = position
    return np.asarray(selected, dtype=np.int64)


def _normalized_autocorrelation(envelope: np.ndarray, lag: int) -> float:
    if lag <= 0 or lag >= envelope.size:
        return 0.0
    left = envelope[:-lag]
    right = envelope[lag:]
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return max(0.0, float(np.dot(left, right) / denominator)) if denominator > 1e-12 else 0.0


def _phase_alignment(peak_times: np.ndarray, period: float) -> float:
    if peak_times.size < MIN_ONSET_COUNT or period <= 0:
        return 0.0
    phases = (peak_times % period) / period * (2.0 * math.pi)
    return float(abs(np.mean(np.exp(1j * phases))))


def _interval_evidence(peak_times: np.ndarray) -> tuple[float | None, float, float]:
    if peak_times.size < MIN_ONSET_COUNT:
        return None, 0.0, 1.0
    intervals = np.diff(peak_times)
    intervals = intervals[(intervals >= 60.0 / MAX_BPM * 0.80) & (intervals <= 60.0 / MIN_BPM * 1.20)]
    if intervals.size < MIN_ONSET_COUNT - 2:
        return None, 0.0, 1.0
    median_interval = float(np.median(intervals))
    deviations = np.abs(intervals - median_interval)
    tolerance = max(0.035, median_interval * 0.18)
    inliers = intervals[deviations <= tolerance]
    if inliers.size < max(3, int(math.ceil(intervals.size * 0.45))):
        return None, 0.0, 1.0
    resolved_interval = float(np.median(inliers))
    bpm = 60.0 / resolved_interval if resolved_interval > 0 else None
    if bpm is not None:
        while bpm > MAX_BPM:
            bpm /= 2.0
        while bpm < MIN_BPM:
            bpm *= 2.0
    consistency = float(inliers.size / intervals.size)
    variation = float(np.std(inliers) / resolved_interval) if resolved_interval > 0 else 1.0
    return bpm, consistency, variation


def _segment_consistency(peak_times: np.ndarray, duration: float) -> float:
    if peak_times.size < 9 or duration <= 0:
        return 0.65
    estimates: list[float] = []
    for start, end in ((0.0, duration / 3.0), (duration / 3.0, duration * 2.0 / 3.0), (duration * 2.0 / 3.0, duration)):
        segment = peak_times[(peak_times >= start) & (peak_times < end)]
        estimate, consistency, _ = _interval_evidence(segment)
        if estimate is not None and consistency >= 0.45:
            estimates.append(estimate)
    if len(estimates) < 2:
        return 0.55
    median = float(np.median(estimates))
    spread = max(abs(value - median) / max(median, 1.0) for value in estimates)
    return max(0.0, min(1.0, 1.0 - spread / 0.18))


def score_bpm_candidates(envelope: np.ndarray, peak_times: np.ndarray, hop_sec: float) -> list[dict[str, float]]:
    interval_bpm, interval_consistency, interval_variation = _interval_evidence(peak_times)
    candidates: list[dict[str, float]] = []
    autocorrelation_cache: dict[int, float] = {}

    def autocorrelation(lag: int) -> float:
        if lag not in autocorrelation_cache:
            autocorrelation_cache[lag] = _normalized_autocorrelation(envelope, lag)
        return autocorrelation_cache[lag]

    for bpm in np.arange(MIN_BPM, MAX_BPM + 0.001, 0.5):
        lag_float = 60.0 / (float(bpm) * hop_sec)
        lower = max(1, int(math.floor(lag_float)))
        upper = max(lower, int(math.ceil(lag_float)))
        fraction = lag_float - lower
        autocorrelation_value = autocorrelation(lower)
        if upper != lower:
            autocorrelation_value = autocorrelation_value * (1.0 - fraction) + autocorrelation(upper) * fraction
        alignment = _phase_alignment(peak_times, 60.0 / float(bpm))
        interval_match = 0.0
        if interval_bpm is not None:
            distance = abs(math.log2(float(bpm) / interval_bpm))
            interval_match = math.exp(-((distance / 0.10) ** 2))
        score = autocorrelation_value * 0.52 + alignment * 0.25 + interval_match * 0.23
        candidates.append(
            {
                "bpm": float(bpm),
                "score": float(score),
                "autocorrelation": float(autocorrelation_value),
                "alignment": float(alignment),
                "interval_match": float(interval_match),
                "interval_consistency": float(interval_consistency),
                "interval_variation": float(interval_variation),
            }
        )
    return sorted(candidates, key=lambda item: (-item["score"], item["bpm"]))


def estimate_bpm(samples: Sequence[int] | array, sample_rate: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        onset = build_onset_envelope(samples, sample_rate)
        if not onset.get("ok"):
            return _unknown(elapsed_ms=(time.perf_counter() - started) * 1000.0, reason=str(onset.get("reason") or "onset_unavailable"))
        envelope = np.asarray(onset["envelope"], dtype=np.float64)
        hop_sec = float(onset["hop_sec"])
        peaks = _detect_onset_peaks(envelope, hop_sec)
        if peaks.size < MIN_ONSET_COUNT:
            return _unknown(elapsed_ms=(time.perf_counter() - started) * 1000.0, reason="too_few_repeated_onsets")
        peak_times = peaks.astype(np.float64) * hop_sec
        interval_bpm, interval_consistency, interval_variation = _interval_evidence(peak_times)
        if interval_bpm is None:
            return _unknown(elapsed_ms=(time.perf_counter() - started) * 1000.0, reason="irregular_onset_intervals")
        candidates = score_bpm_candidates(envelope, peak_times, hop_sec)
        if not candidates:
            return _unknown(elapsed_ms=(time.perf_counter() - started) * 1000.0, reason="no_tempo_candidate")
        best = candidates[0]
        if best["bpm"] < MIN_BPM or best["bpm"] > MAX_BPM or best["autocorrelation"] < 0.12:
            return _unknown(elapsed_ms=(time.perf_counter() - started) * 1000.0, reason="weak_periodicity")

        non_octave = [item for item in candidates[1:] if abs(math.log2(item["bpm"] / best["bpm"])) > 0.12]
        runner_up = non_octave[0]["score"] if non_octave else 0.0
        separation = max(0.0, min(1.0, (best["score"] - runner_up) / 0.20))
        octave_rivals = [item for item in candidates if 0.92 <= abs(math.log2(item["bpm"] / best["bpm"])) <= 1.08]
        octave_rival_score = max((item["score"] for item in octave_rivals), default=0.0)
        octave_gap = max(0.0, best["score"] - octave_rival_score)
        octave_ambiguity = max(0.0, min(1.0, 1.0 - octave_gap / 0.15)) if octave_rivals else 0.0
        ambiguity_factor = 1.0 - 0.45 * octave_ambiguity
        cycles = peak_times.size
        cycle_factor = max(0.0, min(1.0, (cycles - 3) / 10.0))
        interval_factor = max(0.0, min(1.0, interval_consistency * (1.0 - min(1.0, interval_variation / 0.20))))
        segment_factor = _segment_consistency(peak_times, float(onset["duration_sec"]))
        confidence = (
            best["autocorrelation"] * 0.30
            + best["alignment"] * 0.17
            + interval_factor * 0.23
            + segment_factor * 0.15
            + cycle_factor * 0.10
            + separation * 0.05
        ) * ambiguity_factor
        confidence = max(0.0, min(1.0, confidence))
        if confidence < 0.18:
            return _unknown(elapsed_ms=(time.perf_counter() - started) * 1000.0, reason="low_periodicity_confidence")
        return {
            "bpm": round(float(best["bpm"]), 2),
            "bpm_confidence": round(confidence, 4),
            "bpm_method": BPM_METHOD,
            "bpm_status": "ok" if confidence >= 0.55 else "low_confidence",
            "bpm_elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "bpm_reason": "measured_periodic_onsets" if confidence >= 0.55 else "tempo_detected_with_limited_evidence",
            "onset_count": int(peaks.size),
            "segment_consistency": round(segment_factor, 4),
            "half_double_ambiguity": round(octave_ambiguity, 4),
        }
    except Exception as exc:
        result = _unknown("error", elapsed_ms=(time.perf_counter() - started) * 1000.0, reason=f"bpm_analysis_error:{type(exc).__name__}")
        return result
