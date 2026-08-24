from __future__ import annotations

import json
import logging
import re
import sys
import time
from datetime import datetime
from typing import Any, Iterable


SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
REQUIRED_SECTION_KEYS = (
    "verse_1",
    "pre_chorus",
    "chorus",
    "verse_2",
    "bridge",
    "final_chorus",
    "outro",
)
SECTION_DISPLAY = {
    "intro": "Intro",
    "verse_1": "Verse 1",
    "pre_chorus": "Pre-Chorus",
    "chorus": "Chorus",
    "post_chorus": "Post-Chorus",
    "verse_2": "Verse 2",
    "bridge": "Bridge",
    "final_chorus": "Final Chorus",
    "outro": "Outro",
}
SECTION_ORDER = tuple(SECTION_DISPLAY)
MIN_SECTION_LINES = {
    "verse_1": 4,
    "pre_chorus": 2,
    "chorus": 4,
    "verse_2": 4,
    "bridge": 2,
    "final_chorus": 5,
    "outro": 1,
}
MIN_MEANINGFUL_LINES = 30
MIN_CHARACTER_VOLUME = 380
FUZZY_SIMILARITY_THRESHOLD = 0.72
BRIDGE_SIMILARITY_THRESHOLD = 0.78
MAX_SNAPSHOTS = 3


def production_diagnostic_logger(name: str) -> logging.Logger:
    """Create one stderr logger that remains visible under Streamlit/systemd."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not any(getattr(handler, "_velaflow_production_diagnostics", False) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        handler._velaflow_production_diagnostics = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def safe_diagnostic_label(value: Any, *, limit: int = 96) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"(?i)bearer\s+[a-z0-9._~-]+", "Bearer [REDACTED]", text)
    text = re.sub(r"(?i)(api[_ -]?key|authorization|token)\s*[:=]\s*\S+", r"\1=[REDACTED]", text)
    text = re.sub(r"\b(?:AIza|sk-|xai-)[A-Za-z0-9_-]{8,}\b", "[REDACTED]", text)
    return text[:limit]


def safe_exception_summary(error: Any) -> str:
    """Return an operational category without copying arbitrary provider payloads."""
    if error is None:
        return "UnknownError: provider_error"
    error_type = type(error).__name__ if isinstance(error, BaseException) else "ProviderError"
    message = str(error or "").lower()
    if any(token in message for token in ("401", "403", "unauthorized", "authentication", "invalid api", "permission")):
        category = "authentication"
    elif any(token in message for token in ("429", "quota", "rate limit", "resource exhausted")):
        category = "rate_limited"
    elif any(token in message for token in ("timeout", "deadline")):
        category = "timeout"
    elif any(token in message for token in ("connection", "network", "dns", "remote end")):
        category = "network"
    elif any(token in message for token in ("404", "model not found", "not supported", "no longer available")):
        category = "model_unavailable"
    elif any(token in message for token in ("json", "parse", "malformed", "empty")):
        category = "invalid_response"
    elif "missing" in message and "key" in message:
        category = "missing_api_key"
    else:
        category = "provider_error"
    return f"{safe_diagnostic_label(error_type, limit=48)}: {category}"


class SongGenerationDiagnosticAttempt:
    """Emit compact correlated events and guarantee one final outcome event."""

    _FORBIDDEN_FIELDS = {
        "api_key",
        "authorization",
        "token",
        "prompt",
        "repair_prompt",
        "lyrics",
        "full_lyrics",
        "idea",
        "song_idea",
        "hook_text",
        "response_body",
    }

    def __init__(self, generation_id: str, logger: logging.Logger | None = None) -> None:
        self.generation_id = safe_diagnostic_label(generation_id, limit=24)
        self.logger = logger or production_diagnostic_logger("velaflow.song_studio")
        self.finalized = False

    def event(self, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
        safe_fields: list[str] = []
        for key, value in fields.items():
            normalized_key = re.sub(r"[^a-z0-9_]", "", str(key).lower())
            if not normalized_key or normalized_key in self._FORBIDDEN_FIELDS:
                continue
            if isinstance(value, BaseException) or normalized_key == "error":
                rendered = safe_exception_summary(value)
            elif isinstance(value, (bool, int, float)) or value is None:
                rendered = str(value).lower() if isinstance(value, bool) else str(value)
            elif isinstance(value, (list, tuple, set)):
                rendered = ",".join(safe_diagnostic_label(item, limit=64) for item in value)
            else:
                rendered = safe_diagnostic_label(value)
            safe_fields.append(f"{normalized_key}={rendered}")
        suffix = " " + " ".join(safe_fields) if safe_fields else ""
        self.logger.log(level, "SongStudio %s id=%s%s", safe_diagnostic_label(event, limit=48), self.generation_id, suffix)

    def fail(self, stage: str, **fields: Any) -> bool:
        if self.finalized:
            return False
        self.finalized = True
        self.event("generation_failed", level=logging.ERROR, stage=stage, **fields)
        return True

    def succeed(self, **fields: Any) -> bool:
        if self.finalized:
            return False
        self.finalized = True
        self.event("generation_success", **fields)
        return True


def _compact(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u0E00-\u0E7F]+", "", str(value or "")).lower()


def _normalize_section_name(value: str) -> str:
    name = re.sub(r"\s+", " ", str(value or "").strip().lower())
    name = name.replace("_", " ").replace("–", "-").replace("—", "-")
    if name.startswith("final chorus") or name.startswith("final hook"):
        return "final_chorus"
    if name.startswith("pre chorus") or name.startswith("pre-chorus"):
        return "pre_chorus"
    if name.startswith("post chorus") or name.startswith("post-chorus"):
        return "post_chorus"
    if re.match(r"^verse\s*2\b", name):
        return "verse_2"
    if re.match(r"^verse\s*1\b", name) or name == "verse":
        return "verse_1"
    if name.startswith("chorus") or name == "hook":
        return "chorus"
    for key in ("intro", "bridge", "outro"):
        if name.startswith(key):
            return key
    return ""


def _is_direction_line(line: str) -> bool:
    value = str(line or "").strip()
    return bool(value.startswith("(") and value.endswith(")"))


def _meaningful_lines(block: dict[str, Any]) -> list[str]:
    return [
        str(line).strip()
        for line in block.get("lines", [])
        if str(line).strip() and not _is_direction_line(str(line))
    ]


def parse_ordered_song_sections(lyrics: str) -> dict[str, Any]:
    """Parse lyrics without collapsing repeated Chorus/Pre-Chorus blocks."""
    blocks: list[dict[str, Any]] = []
    preamble: list[str] = []
    malformed_headers: list[str] = []
    current: dict[str, Any] | None = None
    counts: dict[str, int] = {}
    for raw in str(lyrics or "").replace("\r\n", "\n").split("\n"):
        match = SECTION_RE.match(raw)
        if match:
            key = _normalize_section_name(match.group(1))
            if not key:
                malformed_headers.append(match.group(1).strip())
                current = None
                continue
            counts[key] = counts.get(key, 0) + 1
            current = {
                "key": key,
                "name": SECTION_DISPLAY[key],
                "occurrence": counts[key],
                "header": f"[{match.group(1).strip()}]",
                "lines": [],
            }
            blocks.append(current)
        elif current is not None:
            current["lines"].append(raw.rstrip())
        elif raw.strip():
            preamble.append(raw.rstrip())
    return {"blocks": blocks, "preamble": preamble, "malformed_headers": malformed_headers}


def render_ordered_song_sections(parsed: dict[str, Any]) -> str:
    rendered: list[str] = []
    if parsed.get("preamble"):
        rendered.append("\n".join(str(line) for line in parsed["preamble"] if str(line).strip()))
    for block in parsed.get("blocks", []):
        lines = list(block.get("lines", []))
        while lines and not str(lines[0]).strip():
            lines.pop(0)
        while lines and not str(lines[-1]).strip():
            lines.pop()
        header = str(block.get("header") or f"[{SECTION_DISPLAY.get(block.get('key'), block.get('name', 'Section'))}]")
        rendered.append(header + ("\n" + "\n".join(lines) if lines else ""))
    return "\n\n".join(part for part in rendered if part.strip()).strip()


def sections_by_key(parsed: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for block in parsed.get("blocks", []):
        grouped.setdefault(str(block.get("key") or ""), []).append(block)
    return grouped


def build_song_blueprint(
    *,
    idea: str,
    genre: str,
    mood: str,
    vocal: str,
    selected_hook: str = "",
    title: str = "",
    music_style_override: str = "",
    explicit_advanced: dict[str, Any] | None = None,
    artist_preset: dict[str, Any] | None = None,
    manual_title: bool = False,
) -> dict[str, Any]:
    clean_idea = re.sub(r"\s+", " ", str(idea or "")).strip()
    clean_hook = str(selected_hook or "").strip()
    clean_title = str(title or "").strip()
    advanced = {key: value for key, value in dict(explicit_advanced or {}).items() if value}
    preset = artist_preset or {}
    return {
        "core_message": clean_idea,
        "point_of_view": "natural first-person Thai narrator",
        "central_situation": clean_idea,
        "emotional_arc": f"{mood}: concrete setup -> rising tension -> honest realization -> earned payoff",
        "resolved_intent": {
            "genre": str(genre or "").strip(),
            "mood": str(mood or "").strip(),
            "vocal": str(vocal or "").strip(),
            "style_override": str(music_style_override or "").strip(),
            "explicit_advanced": advanced,
            "artist_preset": str(preset.get("artist_id") or "neutral") if advanced.get("artist_preset") else "neutral",
        },
        "hook_contract": {
            "selected_hook": clean_hook,
            "title": clean_title,
            "title_is_manual": bool(manual_title),
            "must_appear_in_chorus": bool(clean_hook),
            "must_remain_recognizable_in_final_chorus": bool(clean_hook),
        },
        "section_objectives": {
            "verse_1": "Establish one concrete scene, action, and emotional starting point.",
            "pre_chorus": "Increase tension and lead naturally into the selected hook.",
            "chorus": "State the central conflict concisely and preserve the selected hook.",
            "verse_2": "Add a new event, detail, consequence, or changed situation; never paraphrase Verse 1.",
            "bridge": "Introduce a realization, perspective change, or emotional truth not stated earlier.",
            "final_chorus": "Keep the recognizable hook and add an earned resolution or changed payoff line.",
        },
        "quality_constraints": {
            "avoid_cliches": ["ฉันยังรักเธอ", "ฉันยังคิดถึงเธอ", "ยังอยู่ในใจ", "ลืมไม่ลง", "ไม่ไหวแล้ว"],
            "avoid_duplicate_non_chorus_lines": True,
            "verse_2_must_add_new_information": True,
            "bridge_must_turn_perspective": True,
            "final_chorus_must_add_payoff": True,
        },
    }


def blueprint_prompt_block(blueprint: dict[str, Any]) -> str:
    return json.dumps(blueprint, ensure_ascii=False, separators=(",", ":"))


def _similarity_units(text: str) -> set[str]:
    compact = _compact(text)
    if not compact:
        return set()
    words = re.findall(r"[A-Za-z0-9]+|[\u0E00-\u0E7F]+", str(text or "").lower())
    units = {f"w:{word}" for word in words if len(word) > 2}
    if len(compact) >= 3:
        units.update(f"c:{compact[index:index + 3]}" for index in range(len(compact) - 2))
    return units


def lyric_similarity(left: Iterable[str] | str, right: Iterable[str] | str) -> float:
    left_text = "\n".join(left) if not isinstance(left, str) else left
    right_text = "\n".join(right) if not isinstance(right, str) else right
    if _compact(left_text) and _compact(left_text) == _compact(right_text):
        return 1.0
    left_units = _similarity_units(left_text)
    right_units = _similarity_units(right_text)
    if not left_units or not right_units:
        return 0.0
    return len(left_units & right_units) / len(left_units | right_units)


def _finding(code: str, section: str = "", detail: str = "", similarity: float | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"code": code}
    if section:
        result["section"] = section
    if detail:
        result["detail"] = detail
    if similarity is not None:
        result["similarity"] = round(similarity, 3)
    return result


def validate_production_song(
    lyrics: str,
    blueprint: dict[str, Any],
    *,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    parsed = parse_ordered_song_sections(lyrics)
    grouped = sections_by_key(parsed)
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    repairable: set[str] = set()

    provenance = dict(provenance or {})
    if provenance.get("synthetic") or provenance.get("status") in {"offline_synthetic", "generation_failure"}:
        blocking.append(_finding("synthetic_production_result"))

    for key in REQUIRED_SECTION_KEYS:
        if not grouped.get(key):
            blocking.append(_finding("missing_required_section", SECTION_DISPLAY[key]))
            repairable.add(key)
            continue
        best_lines = max((_meaningful_lines(block) for block in grouped[key]), key=len, default=[])
        if len(best_lines) < MIN_SECTION_LINES[key]:
            blocking.append(_finding("underfilled_major_section", SECTION_DISPLAY[key], f"{len(best_lines)}/{MIN_SECTION_LINES[key]} lyric lines"))
            repairable.add(key)

    all_lines = [_line for block in parsed["blocks"] for _line in _meaningful_lines(block)]
    character_volume = sum(len(_compact(line)) for line in all_lines)
    if len(all_lines) < MIN_MEANINGFUL_LINES or character_volume < MIN_CHARACTER_VOLUME:
        blocking.append(_finding("song_below_minimum_structure", detail=f"{len(all_lines)} lines, {character_volume} compact characters"))
        for key in REQUIRED_SECTION_KEYS:
            if key != "chorus":
                repairable.add(key)

    hook = str((blueprint.get("hook_contract") or {}).get("selected_hook") or "").strip()
    chorus_lines = _meaningful_lines(grouped.get("chorus", [{}])[0]) if grouped.get("chorus") else []
    final_lines = _meaningful_lines(grouped.get("final_chorus", [{}])[0]) if grouped.get("final_chorus") else []
    if hook and _compact(hook) not in _compact("\n".join(chorus_lines)):
        blocking.append(_finding("selected_hook_missing_from_chorus", "Chorus"))
        repairable.add("chorus")
    if hook and final_lines and _compact(hook) not in _compact("\n".join(final_lines)):
        blocking.append(_finding("selected_hook_missing_from_final_chorus", "Final Chorus"))
        repairable.add("final_chorus")
    hook_contract = blueprint.get("hook_contract") or {}
    title = str(hook_contract.get("title") or "").strip()
    if (
        title
        and not hook_contract.get("title_is_manual")
        and _compact(title) not in _compact(hook)
        and _compact(title) not in _compact("\n".join(chorus_lines))
    ):
        blocking.append(_finding("ai_title_missing_from_chorus", "Chorus"))
        repairable.add("chorus")

    verse_1 = _meaningful_lines(grouped.get("verse_1", [{}])[0]) if grouped.get("verse_1") else []
    verse_2 = _meaningful_lines(grouped.get("verse_2", [{}])[0]) if grouped.get("verse_2") else []
    duplicate_started = time.perf_counter()
    verse_similarity = lyric_similarity(verse_1, verse_2)
    if verse_1 and verse_2 and verse_similarity >= FUZZY_SIMILARITY_THRESHOLD:
        code = "verse_2_exact_duplicate" if verse_similarity == 1.0 else "verse_2_too_similar"
        blocking.append(_finding(code, "Verse 2", similarity=verse_similarity))
        repairable.add("verse_2")

    bridge = _meaningful_lines(grouped.get("bridge", [{}])[0]) if grouped.get("bridge") else []
    bridge_similarity = max(lyric_similarity(bridge, verse_1), lyric_similarity(bridge, verse_2)) if bridge else 0.0
    if bridge and bridge_similarity >= BRIDGE_SIMILARITY_THRESHOLD:
        blocking.append(_finding("bridge_repeats_verse", "Bridge", similarity=bridge_similarity))
        repairable.add("bridge")

    final_similarity = lyric_similarity(chorus_lines, final_lines)
    chorus_set = {_compact(line) for line in chorus_lines if _compact(line)}
    final_new_lines = [line for line in final_lines if _compact(line) and _compact(line) not in chorus_set]
    if chorus_lines and final_lines and (final_similarity == 1.0 or not final_new_lines):
        blocking.append(_finding("final_chorus_missing_payoff", "Final Chorus", similarity=final_similarity))
        repairable.add("final_chorus")
    duplicate_elapsed = (time.perf_counter() - duplicate_started) * 1000

    if parsed.get("malformed_headers"):
        warnings.append(_finding("unrecognized_section_tags", detail=", ".join(parsed["malformed_headers"][:4])))
    if not grouped.get("intro"):
        warnings.append(_finding("missing_optional_intro", "Intro"))
    if any(len(line) > 72 for line in all_lines):
        warnings.append(_finding("long_lyric_lines"))
    thai_count = sum(1 for char in "".join(all_lines) if "\u0E00" <= char <= "\u0E7F")
    if all_lines and thai_count == 0:
        blocking.append(_finding("thai_lyrics_missing"))

    return {
        "passed": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "repairable_sections": [SECTION_DISPLAY[key] for key in SECTION_ORDER if key in repairable],
        "metrics": {
            "meaningful_line_count": len(all_lines),
            "character_volume": character_volume,
            "verse_similarity": round(verse_similarity, 3),
            "bridge_similarity": round(bridge_similarity, 3),
            "final_chorus_similarity": round(final_similarity, 3),
            "final_chorus_new_payoff_lines": len(final_new_lines),
            "similarity_method": "normalized exact + word/Thai character trigram Jaccard",
            "similarity_threshold": FUZZY_SIMILARITY_THRESHOLD,
            "duplicate_check_ms": round(duplicate_elapsed, 3),
            "validation_ms": round((time.perf_counter() - started) * 1000, 3),
        },
    }


def build_targeted_repair_prompt(
    *,
    idea: str,
    title: str,
    selected_hook: str,
    blueprint: dict[str, Any],
    genre: str,
    mood: str,
    vocal: str,
    current_lyrics: str,
    validation: dict[str, Any],
) -> str:
    sections = validation.get("repairable_sections", [])
    defects = [
        {"code": item.get("code"), "section": item.get("section", ""), "detail": item.get("detail", "")}
        for item in validation.get("blocking", [])
        if item.get("code") != "synthetic_production_result"
    ]
    parsed = parse_ordered_song_sections(current_lyrics)
    forbidden = []
    for block in parsed.get("blocks", []):
        if block.get("name") not in sections:
            forbidden.extend(_meaningful_lines(block))
    return (
        "You are repairing specific sections of a Thai commercial song.\n"
        "Return ONLY the repaired named sections with exact [Section] headers. No JSON, markdown, explanations, style prompt, or metadata.\n"
        "Preserve all passing sections by not returning them. Use natural Thai lyrics and English-only production tags in parentheses.\n"
        f"SECTIONS TO REPAIR: {', '.join(sections)}\n"
        f"DEFECTS: {json.dumps(defects, ensure_ascii=False)}\n"
        f"SONG IDEA: {idea}\nTITLE: {title}\nSELECTED HOOK: {selected_hook}\n"
        f"RESOLVED INTENT: Genre={genre}; Mood={mood}; Vocal={vocal}\n"
        f"BLUEPRINT: {blueprint_prompt_block(blueprint)}\n"
        f"DO NOT COPY THESE PASSING LINES INTO NEW NON-CHORUS MATERIAL: {json.dumps(forbidden[:40], ensure_ascii=False)}\n"
        f"CURRENT COMPLETE SONG:\n{current_lyrics.strip()}"
    )


def merge_repaired_sections(current_lyrics: str, repaired_text: str, section_names: Iterable[str]) -> str:
    current = parse_ordered_song_sections(current_lyrics)
    repaired = parse_ordered_song_sections(repaired_text)
    requested = {_normalize_section_name(name) for name in section_names}
    requested.discard("")
    replacements: dict[str, dict[str, Any]] = {}
    for block in repaired.get("blocks", []):
        key = str(block.get("key") or "")
        if key in requested and _meaningful_lines(block):
            replacements[key] = block
    if requested - replacements.keys():
        missing = ", ".join(SECTION_DISPLAY[key] for key in requested - replacements.keys())
        raise ValueError(f"Repair response missing required sections: {missing}")

    seen: set[str] = set()
    merged_blocks: list[dict[str, Any]] = []
    for block in current.get("blocks", []):
        key = str(block.get("key") or "")
        if key in replacements:
            replacement = dict(replacements[key])
            replacement["header"] = block.get("header") or replacement.get("header")
            replacement["occurrence"] = block.get("occurrence", 1)
            merged_blocks.append(replacement)
            seen.add(key)
        else:
            merged_blocks.append(block)

    for key in SECTION_ORDER:
        if key not in replacements or key in seen:
            continue
        replacement = dict(replacements[key])
        insert_at = len(merged_blocks)
        target_order = SECTION_ORDER.index(key)
        for index, block in enumerate(merged_blocks):
            block_key = str(block.get("key") or "")
            if block_key in SECTION_ORDER and SECTION_ORDER.index(block_key) > target_order:
                insert_at = index
                break
        merged_blocks.insert(insert_at, replacement)
    return render_ordered_song_sections({**current, "blocks": merged_blocks})


def snapshot_song_lyrics(project: dict[str, Any], *, reason: str, lyrics: str | None = None) -> bool:
    song = project.get("song") if isinstance(project.get("song"), dict) else {}
    value = str(lyrics if lyrics is not None else (song.get("normalized_song_output") or song.get("complete_lyrics") or "")).strip()
    if len(_compact(value)) < 20:
        return False
    snapshots = list(project.get("song_lyric_snapshots") or [])
    if snapshots and snapshots[-1].get("previous_lyrics") == value and snapshots[-1].get("reason") == reason:
        return False
    snapshots.append({
        "previous_lyrics": value,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "reason": str(reason or "regenerate"),
    })
    project["song_lyric_snapshots"] = snapshots[-MAX_SNAPSHOTS:]
    return True
