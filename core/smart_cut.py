from __future__ import annotations

import math
from typing import Any


MIN_USEFUL_DURATION_SEC = 2.0
MIN_ACTIVE_ENERGY = 0.08
MAX_DEFAULT_SUGGESTIONS = 4


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _target_duration(duration: float, preferred: float | None) -> float:
    if preferred is not None and _number(preferred) > 0:
        return min(duration, max(MIN_USEFUL_DURATION_SEC, _number(preferred)))
    if duration >= 90.0:
        return min(36.0, max(24.0, duration * 0.20))
    if duration >= 40.0:
        return min(30.0, max(20.0, duration * 0.28))
    return max(MIN_USEFUL_DURATION_SEC, duration * 0.58)


def _profile(analysis: dict[str, Any], duration: float) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for raw in ((analysis.get("energy") or {}).get("profile") or []):
        if not isinstance(raw, dict):
            continue
        start = max(0.0, min(duration, _number(raw.get("start_sec"))))
        end = max(start, min(duration, _number(raw.get("end_sec"), start)))
        energy = max(0.0, min(1.0, _number(raw.get("normalized"))))
        if end > start:
            points.append({"start": start, "end": end, "energy": energy})
    return sorted(points, key=lambda item: (item["start"], item["end"]))


def _active_bounds(analysis: dict[str, Any], duration: float) -> tuple[float, float]:
    silence = analysis.get("silence") or {}
    leading = max(0.0, _number(silence.get("leading_sec")))
    trailing = max(0.0, _number(silence.get("trailing_sec")))
    start = min(duration, leading)
    end = max(start, duration - min(duration, trailing))
    return start, end


def _internal_silence(analysis: dict[str, Any], duration: float) -> list[tuple[float, float]]:
    regions: list[tuple[float, float]] = []
    for raw in ((analysis.get("silence") or {}).get("internal_regions") or []):
        if not isinstance(raw, dict):
            continue
        start = max(0.0, min(duration, _number(raw.get("start_sec"))))
        end = max(start, min(duration, _number(raw.get("end_sec"), start)))
        if end > start:
            regions.append((start, end))
    return sorted(regions)


def _window_metrics(points: list[dict[str, float]], start: float, end: float) -> tuple[float, float, float, float]:
    weighted: list[tuple[float, float]] = []
    for point in points:
        overlap = max(0.0, min(end, point["end"]) - max(start, point["start"]))
        if overlap > 0:
            weighted.append((point["energy"], overlap))
    duration = max(0.001, end - start)
    covered = sum(weight for _, weight in weighted)
    if not weighted or covered <= 0:
        return 0.0, 0.0, 0.0, 0.0
    mean = sum(value * weight for value, weight in weighted) / covered
    ordered = sorted(value for value, _ in weighted)
    lower = ordered[max(0, int((len(ordered) - 1) * 0.25))]
    variance = sum(weight * ((value - mean) ** 2) for value, weight in weighted) / covered
    return mean, lower, math.sqrt(variance), min(1.0, covered / duration)


def _energy_windows(points: list[dict[str, float]], active_start: float, active_end: float, target: float) -> list[dict[str, float]]:
    active_duration = active_end - active_start
    if active_duration < MIN_USEFUL_DURATION_SEC:
        return []
    length = min(target, active_duration)
    starts = {active_start, max(active_start, active_end - length)}
    starts.update(max(active_start, min(active_end - length, point["start"])) for point in points)
    windows: list[dict[str, float]] = []
    for start in sorted(starts):
        end = min(active_end, start + length)
        mean, lower, variation, coverage = _window_metrics(points, start, end)
        sustained = mean * 0.55 + lower * 0.30 + coverage * 0.15 - variation * 0.18
        windows.append({"start": start, "end": end, "mean": mean, "lower": lower, "score": max(0.0, min(1.0, sustained))})
    return sorted(windows, key=lambda item: (-item["score"], -item["mean"], item["start"]))


def _refine_with_silence(start: float, end: float, silences: list[tuple[float, float]], active_start: float, active_end: float) -> tuple[float, float]:
    minimum = max(2.0, (end - start) * 0.55)
    for silence_start, silence_end in silences:
        if start + minimum <= silence_start <= end + 4.0:
            end = min(active_end, silence_start)
            break
    for silence_start, silence_end in reversed(silences):
        if start - 4.0 <= silence_end <= end - minimum:
            start = max(active_start, silence_end)
            break
    return round(start, 3), round(end, 3)


def _overlap_ratio(left: dict[str, Any], right: dict[str, Any]) -> float:
    overlap = max(0.0, min(_number(left["end_sec"]), _number(right["end_sec"])) - max(_number(left["start_sec"]), _number(right["start_sec"])))
    shortest = min(_number(left["end_sec"]) - _number(left["start_sec"]), _number(right["end_sec"]) - _number(right["start_sec"]))
    return overlap / shortest if shortest > 0 else 0.0


def _suggestion(kind: str, label: str, start: float, end: float, score: float, reason: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "start_sec": round(start, 3),
        "end_sec": round(end, 3),
        "score": round(max(0.0, min(1.0, score)), 3),
        "reason": reason,
    }


def suggest_cut_regions(
    analysis: dict[str, Any],
    preferred_duration_sec: float | None = None,
    max_suggestions: int = MAX_DEFAULT_SUGGESTIONS,
) -> list[dict[str, Any]]:
    """Suggest conservative cut regions from cached energy and silence data only."""
    if not isinstance(analysis, dict) or max_suggestions <= 0:
        return []
    duration = _number((analysis.get("metadata") or {}).get("duration_sec"))
    if duration < MIN_USEFUL_DURATION_SEC or (analysis.get("energy") or {}).get("status") != "ok":
        return []
    points = _profile(analysis, duration)
    if not points or max((point["energy"] for point in points), default=0.0) < MIN_ACTIVE_ENERGY:
        return []

    active_start, active_end = _active_bounds(analysis, duration)
    if active_end - active_start < MIN_USEFUL_DURATION_SEC:
        return []
    target = min(_target_duration(duration, preferred_duration_sec), active_end - active_start)
    silences = _internal_silence(analysis, duration)
    windows = _energy_windows(points, active_start, active_end, target)
    energies = [point["energy"] for point in points if point["energy"] >= MIN_ACTIVE_ENERGY]
    spread = max(energies, default=0.0) - min(energies, default=0.0)
    candidates: list[dict[str, Any]] = []

    sustained = [window for window in windows if spread >= 0.06 and window["mean"] >= 0.30 and window["lower"] >= 0.15]
    if sustained:
        best = sustained[0]
        start, end = _refine_with_silence(best["start"], best["end"], silences, active_start, active_end)
        if end - start >= MIN_USEFUL_DURATION_SEC:
            candidates.append(_suggestion("strong_section", "Strong Section", start, end, best["score"], "sustained_high_energy"))

        if spread >= 0.06:
            for alternative in sustained[1:]:
                suggestion = _suggestion("high_energy", "High Energy", alternative["start"], alternative["end"], alternative["score"], "distinct_sustained_energy")
                if all(_overlap_ratio(suggestion, existing) <= 0.50 for existing in candidates):
                    start, end = _refine_with_silence(alternative["start"], alternative["end"], silences, active_start, active_end)
                    suggestion.update({"start_sec": start, "end_sec": end})
                    if end - start >= MIN_USEFUL_DURATION_SEC:
                        candidates.append(suggestion)
                    break

    intro_end = min(active_end, active_start + target)
    for silence_start, _ in silences:
        if active_start + MIN_USEFUL_DURATION_SEC <= silence_start <= intro_end + 5.0:
            intro_end = silence_start
            break
    intro_mean, _, _, _ = _window_metrics(points, active_start, intro_end)
    if intro_end - active_start >= MIN_USEFUL_DURATION_SEC and intro_mean >= MIN_ACTIVE_ENERGY:
        candidates.append(_suggestion("clean_intro", "Clean Intro", active_start, intro_end, intro_mean, "leading_silence_excluded"))

    outro_start = max(active_start, active_end - target)
    for _, silence_end in reversed(silences):
        if outro_start - 5.0 <= silence_end <= active_end - MIN_USEFUL_DURATION_SEC:
            outro_start = silence_end
            break
    outro_mean, _, _, _ = _window_metrics(points, outro_start, active_end)
    has_signal_boundaries = active_start > 0.05 or active_end < duration - 0.05 or bool(silences)
    if (spread >= 0.06 or has_signal_boundaries) and active_end - outro_start >= MIN_USEFUL_DURATION_SEC and outro_mean >= MIN_ACTIVE_ENERGY:
        candidates.append(_suggestion("clean_outro", "Clean Outro", outro_start, active_end, outro_mean, "trailing_silence_excluded"))

    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate["start_sec"] < 0 or candidate["end_sec"] > duration or candidate["start_sec"] >= candidate["end_sec"]:
            continue
        if any(_overlap_ratio(candidate, existing) > 0.52 for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) >= min(MAX_DEFAULT_SUGGESTIONS, int(max_suggestions)):
            break
    return selected
