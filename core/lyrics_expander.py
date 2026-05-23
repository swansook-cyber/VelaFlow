from __future__ import annotations

import re
from typing import Any

from core.music_direction_engine import build_music_direction, has_rich_music_direction, normalize_section_direction_layout


REQUIRED_SECTIONS = ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Bridge", "Final Chorus", "Outro"]
MIN_LYRIC_LINES = 24
MIN_CHORUS_LINES = 4
MIN_TOTAL_WORDS = 120
SECTION_MIN_LINES = {
    "Verse 1": 4,
    "Verse 2": 4,
    "Pre-Chorus": 2,
    "Chorus": 5,
    "Bridge": 3,
    "Final Chorus": 6,
    "Outro": 2,
}


def _section_name(line: str) -> str:
    match = re.match(r"\s*\[([^\]]+)\]\s*$", str(line or ""))
    return match.group(1).strip() if match else ""


def _is_lyric_line(line: str) -> bool:
    stripped = str(line or "").strip()
    return bool(stripped and not _section_name(stripped) and not (stripped.startswith("(") and stripped.endswith(")")))


def _words(text: str) -> list[str]:
    parts = [part for part in re.split(r"\s+", str(text or "").strip()) if part]
    thai_chars = len(re.findall(r"[ก-๙]", str(text or "")))
    if thai_chars:
        parts.extend(["thai_word"] * max(0, thai_chars // 3))
    return parts


def parse_lyric_sections(lyrics: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "Intro"
    for raw in str(lyrics or "").replace("\r\n", "\n").splitlines():
        line = raw.strip()
        if not line:
            continue
        section = _section_name(line)
        if section:
            current = section
            sections.setdefault(current, [])
            continue
        if _is_lyric_line(line):
            sections.setdefault(current, []).append(line)
    return sections


def _line_count(sections: dict[str, list[str]]) -> int:
    return sum(len(lines) for lines in sections.values())


def _chorus_lines(sections: dict[str, list[str]]) -> list[str]:
    rows: list[str] = []
    for name, lines in sections.items():
        if "chorus" in name.lower():
            rows.extend(lines)
    return rows


def analyze_song_completeness(lyrics: str) -> dict[str, Any]:
    sections = parse_lyric_sections(lyrics)
    lyric_lines = _line_count(sections)
    chorus_lines = _chorus_lines(sections)
    unique_lines = {line.strip() for lines in sections.values() for line in lines if line.strip()}
    total_words = len(_words("\n".join(line for lines in sections.values() for line in lines)))
    missing = [name for name in REQUIRED_SECTIONS if not any(name.lower() == existing.lower() for existing in sections)]
    repeated_identical_lines = max(0, lyric_lines - len(unique_lines))
    source = str(lyrics or "").lower()
    has_bpm = "bpm" in source
    has_vocal_direction = "vocal" in source
    has_arrangement_tags = bool(re.search(r"\[[^\]]+\]\s*\n\s*\([^)]{20,}\)", str(lyrics or ""), flags=re.IGNORECASE))
    has_emotional_arc = any(term in source for term in ["emotional", "cinematic", "lift", "release", "vulnerable"])
    has_dynamic_progression = any(term in source for term in ["building", "rising", "final chorus", "energy", "wide"])
    has_cinematic_transition = any(term in source for term in ["fade", "breakdown", "reverb tail", "cinematic"])
    structure = validate_song_structure(lyrics)
    chorus_quality = min(100, 35 + len(chorus_lines) * 10 + min(25, len(unique_lines)))
    estimated_duration = max(30, round(lyric_lines * 4.2))
    score = 100
    if lyric_lines < MIN_LYRIC_LINES:
        score -= (MIN_LYRIC_LINES - lyric_lines) * 2
    if len(chorus_lines) < MIN_CHORUS_LINES:
        score -= (MIN_CHORUS_LINES - len(chorus_lines)) * 8
    if total_words < MIN_TOTAL_WORDS:
        score -= min(35, (MIN_TOTAL_WORDS - total_words) // 4)
    score -= len(missing) * 5
    score -= repeated_identical_lines * 3
    if not has_bpm:
        score -= 5
    if not has_vocal_direction:
        score -= 5
    if not has_arrangement_tags:
        score -= 10
    if not has_emotional_arc:
        score -= 5
    if not has_dynamic_progression:
        score -= 5
    if not has_cinematic_transition:
        score -= 5
    score -= len(structure.get("underfilled_sections", [])) * 6
    score_label = "commercial-ready" if score >= 90 else "strong" if score >= 75 else "usable" if score >= 60 else "incomplete"
    return {
        "score": max(0, min(100, score)),
        "score_label": score_label,
        "line_count": lyric_lines,
        "chorus_line_count": len(chorus_lines),
        "total_words": total_words,
        "required_sections_present": not missing,
        "missing_sections": missing,
        "section_structure": structure,
        "bpm_style_exists": has_bpm,
        "vocal_direction_exists": has_vocal_direction,
        "arrangement_tags_exist": has_arrangement_tags,
        "emotional_arc_exists": has_emotional_arc,
        "dynamic_progression_exists": has_dynamic_progression,
        "cinematic_transition_exists": has_cinematic_transition,
        "repeated_identical_lines": repeated_identical_lines,
        "chorus_quality": max(0, min(100, chorus_quality)),
        "estimated_duration_seconds": estimated_duration,
        "ok": lyric_lines >= MIN_LYRIC_LINES and len(chorus_lines) >= MIN_CHORUS_LINES and total_words >= MIN_TOTAL_WORDS and not missing and not structure.get("underfilled_sections") and repeated_identical_lines <= 10,
    }


def validate_song_structure(lyrics: str) -> dict[str, Any]:
    sections = parse_lyric_sections(lyrics)
    underfilled = []
    for section, minimum in SECTION_MIN_LINES.items():
        count = len(sections.get(section, []))
        if count < minimum:
            underfilled.append({"section": section, "line_count": count, "minimum": minimum})
    return {
        "ok": not underfilled,
        "section_line_counts": {section: len(lines) for section, lines in sections.items()},
        "underfilled_sections": underfilled,
    }


def _dedupe(lines: list[str]) -> list[str]:
    seen = set()
    out = []
    for line in lines:
        key = re.sub(r"\s+", "", line)
        if key and key not in seen:
            out.append(line)
            seen.add(key)
    return out


def _direction_tag(direction: dict[str, Any], section: str, fallback: str) -> str:
    return str((direction.get("section_tags") or {}).get(section) or fallback).strip()


def _default_lines(hook_text: str, idea: str, music_direction: dict[str, Any] | None = None) -> dict[str, list[str]]:
    direction = music_direction or build_music_direction(mood="emotional cinematic")
    hook = hook_text.strip() or "ยังคิดถึงเธอในคืนที่ฝนพรำ"
    theme = idea.strip()[:36] or "เรื่องของเราที่ค้างอยู่ในใจ"
    return {
        "Intro": [
            _direction_tag(direction, "Intro", "(acoustic guitar strumming, soft rhodes piano, warm ambient pad, emotional atmosphere)"),
            "คืนนี้เสียงฝนค่อย ๆ ถามถึงเธอ",
            "เหมือนความเงียบยังจำชื่อเราได้ดี",
        ],
        "Verse 1": [
            _direction_tag(direction, "Verse 1", "(clean electric guitar, intimate vocal tone, soft kick/snare groove)"),
            f"ฉันเดินผ่านที่เดิมที่เคยมี {theme}",
            "ไฟริมทางยังสว่างแต่ใจยังมืดอยู่",
            "ข้อความเก่าในเครื่องยังไม่กล้าลบทิ้งไป",
            "ทุกเพลงที่เปิดฟังยังพาฉันกลับไปหาเธอ",
            "พยายามยิ้มให้เหมือนไม่เป็นอะไร",
            "แต่ในใจยังมีคำถามที่ไม่เคยจาง",
        ],
        "Pre-Chorus": [
            _direction_tag(direction, "Pre-Chorus", "(building tension, rising toms, emotional lift)"),
            "ยิ่งบอกตัวเองให้ลืมยิ่งจำชัดกว่าเดิม",
            "ยิ่งหนีไกลเท่าไรหัวใจก็ยังเดินกลับมา",
            "ถ้าคืนนี้เธอได้ยินเสียงฉันในความเงียบ",
        ],
        "Chorus": [
            _direction_tag(direction, "Chorus", "(full band energy, catchy pop rock groove, layered harmony, strong emotional release)"),
            hook,
            "ทำไมใจยังเรียกหาเธอซ้ำ ๆ",
            "ทั้งที่รู้ว่าเราคงย้อนเวลาไม่ได้",
            "แต่ทุกลมหายใจยังร้องเป็นชื่อเธอ",
            "ขอให้ท่อนนี้พาใจฉันผ่านคืนนี้ไป",
        ],
        "Verse 2": [
            _direction_tag(direction, "Verse 2", "(clean electric guitar returns, stronger groove, subtle counter melody, more urgent vocal)"),
            "ฉันเห็นเงาเราซ้อนอยู่บนกระจกบานเดิม",
            "แก้วกาแฟเย็นลงเหมือนวันที่เธอจากไป",
            "เพื่อนบอกว่าเดี๋ยวเวลาก็รักษาทุกอย่าง",
            "แต่เวลายังเก็บเธอไว้ในทุกวินาที",
            "ถนนเส้นเดิมไม่เคยยาวเท่าคืนนี้",
            "เมื่อไม่มีมือเธอให้จับเหมือนวันก่อน",
        ],
        "Bridge": [
            _direction_tag(direction, "Bridge", "(cinematic breakdown, emotional piano lead, atmospheric texture)"),
            "ถ้าวันหนึ่งฉันร้องไห้โดยไม่เจ็บอีกแล้ว",
            "คงเป็นวันที่ฉันยอมให้เธอเป็นความทรงจำ",
            "แต่คืนนี้ขอร้องเพลงนี้ให้สุดหัวใจ",
            "ก่อนจะปล่อยคำว่าเราให้ลอยไปกับฝน",
        ],
        "Final Chorus": [
            _direction_tag(direction, "Final Chorus", "(big final chorus, stacked harmonies, stronger drums, wide cinematic lift)"),
            hook,
            "ทำไมใจยังเรียกหาเธอดังขึ้นทุกครั้ง",
            "ถึงรู้ว่าปลายทางไม่มีเธอยืนรอ",
            "ฉันจะร้องจนความคิดถึงค่อย ๆ เบาลง",
            "ให้เพลงสุดท้ายพาฉันรักตัวเองอีกครั้ง",
            "และถ้าพรุ่งนี้ฟ้าสว่างโดยไม่มีเธอ",
            "ฉันจะเดินต่อไปพร้อมรอยแผลที่ยังสวยงาม",
        ],
        "Outro": [
            _direction_tag(direction, "Outro", "(emotional fade out, soft guitar echoes, ambient reverb tail)"),
            "สุดท้ายเธอยังอยู่ในเพลงนี้",
            "แต่ฉันจะไม่หยุดชีวิตไว้ที่เดิม",
        ],
    }


def expand_lyrics_to_full_song(
    lyrics: str,
    *,
    hook_text: str = "",
    idea: str = "",
    artist_preset: dict[str, Any] | None = None,
    genre: str = "",
    mood: str = "",
    vocal: str = "",
    style_preset: dict[str, Any] | None = None,
) -> str:
    existing = parse_lyric_sections(lyrics)
    music_direction = build_music_direction(genre=genre, mood=mood, vocal=vocal, artist_preset=artist_preset, style_preset=style_preset)
    defaults = _default_lines(hook_text, idea, music_direction)
    final: dict[str, list[str]] = {}
    for section in REQUIRED_SECTIONS:
        source = existing.get(section) or existing.get(section.upper()) or []
        merged = _dedupe([*source, *defaults.get(section, [])])
        min_lines = 1
        if section in SECTION_MIN_LINES:
            min_lines = SECTION_MIN_LINES[section]
        final[section] = merged[: max(min_lines, len(merged))]

    text = _render_sections(final)
    report = analyze_song_completeness(text)
    if report["total_words"] < MIN_TOTAL_WORDS:
        final["Bridge"].extend([
            "ฉันเก็บทุกคำลาไว้เป็นบทเรียนของหัวใจ",
            "ให้ความเสียใจกลายเป็นแสงเล็ก ๆ ข้างใน",
        ])
        final["Final Chorus"].extend([
            "แม้ความรักจะจบลงตรงวันที่เราห่างไกล",
            "แต่เสียงเพลงจะพาฉันกลับมาหายใจได้อีกครั้ง",
        ])
    return normalize_section_direction_layout(_render_sections(final), music_direction).strip()


def _render_sections(sections: dict[str, list[str]]) -> str:
    blocks = []
    for section in ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Pre-Chorus", "Chorus", "Bridge", "Final Chorus", "Outro"]:
        lines = sections.get(section) or []
        if not lines and section in {"Pre-Chorus", "Chorus"}:
            lines = sections.get(section, [])
        if lines:
            blocks.append(f"[{section}]\n" + "\n".join(lines))
    return "\n\n".join(blocks).strip()


def apply_music_direction_tags(lyrics: str, music_direction: dict[str, Any]) -> str:
    return normalize_section_direction_layout(lyrics, music_direction).strip()


def ensure_full_song_structure(
    lyrics: str,
    *,
    hook_text: str = "",
    idea: str = "",
    artist_preset: dict[str, Any] | None = None,
    genre: str = "",
    mood: str = "",
    vocal: str = "",
    style_preset: dict[str, Any] | None = None,
) -> dict[str, Any]:
    before = analyze_song_completeness(lyrics)
    music_direction = build_music_direction(genre=genre, mood=mood, vocal=vocal, artist_preset=artist_preset, style_preset=style_preset)
    if before["ok"]:
        if has_rich_music_direction(lyrics, music_direction.get("master_music_style_prompt", "")):
            enriched = normalize_section_direction_layout(lyrics.strip(), music_direction)
        else:
            enriched = apply_music_direction_tags(lyrics.strip(), music_direction)
        after = analyze_song_completeness(enriched)
        return {"lyrics": enriched, "expanded": enriched != lyrics.strip(), "before": before, "after": after, "music_direction": music_direction}
    expanded = expand_lyrics_to_full_song(
        lyrics,
        hook_text=hook_text,
        idea=idea,
        artist_preset=artist_preset,
        genre=genre,
        mood=mood,
        vocal=vocal,
        style_preset=style_preset,
    )
    after = analyze_song_completeness(expanded)
    return {"lyrics": expanded, "expanded": True, "before": before, "after": after, "music_direction": music_direction}
