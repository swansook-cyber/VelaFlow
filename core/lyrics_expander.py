from __future__ import annotations

import re
from typing import Any


REQUIRED_SECTIONS = ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Bridge", "Final Chorus", "Outro"]
MIN_LYRIC_LINES = 24
MIN_CHORUS_LINES = 4
MIN_TOTAL_WORDS = 120


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
    return {
        "score": max(0, min(100, score)),
        "line_count": lyric_lines,
        "chorus_line_count": len(chorus_lines),
        "total_words": total_words,
        "required_sections_present": not missing,
        "missing_sections": missing,
        "repeated_identical_lines": repeated_identical_lines,
        "chorus_quality": max(0, min(100, chorus_quality)),
        "estimated_duration_seconds": estimated_duration,
        "ok": lyric_lines >= MIN_LYRIC_LINES and len(chorus_lines) >= MIN_CHORUS_LINES and total_words >= MIN_TOTAL_WORDS and not missing and repeated_identical_lines <= 10,
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


def _default_lines(hook_text: str, idea: str) -> dict[str, list[str]]:
    hook = hook_text.strip() or "ยังคิดถึงเธอในคืนที่ฝนพรำ"
    theme = idea.strip()[:36] or "เรื่องของเราที่ค้างอยู่ในใจ"
    return {
        "Intro": [
            "(soft piano intro)",
            "คืนนี้เสียงฝนค่อย ๆ ถามถึงเธอ",
            "เหมือนความเงียบยังจำชื่อเราได้ดี",
        ],
        "Verse 1": [
            f"ฉันเดินผ่านที่เดิมที่เคยมี {theme}",
            "ไฟริมทางยังสว่างแต่ใจยังมืดอยู่",
            "ข้อความเก่าในเครื่องยังไม่กล้าลบทิ้งไป",
            "ทุกเพลงที่เปิดฟังยังพาฉันกลับไปหาเธอ",
            "พยายามยิ้มให้เหมือนไม่เป็นอะไร",
            "แต่ในใจยังมีคำถามที่ไม่เคยจาง",
        ],
        "Pre-Chorus": [
            "ยิ่งบอกตัวเองให้ลืมยิ่งจำชัดกว่าเดิม",
            "ยิ่งหนีไกลเท่าไรหัวใจก็ยังเดินกลับมา",
            "ถ้าคืนนี้เธอได้ยินเสียงฉันในความเงียบ",
        ],
        "Chorus": [
            hook,
            "ทำไมใจยังเรียกหาเธอซ้ำ ๆ",
            "ทั้งที่รู้ว่าเราคงย้อนเวลาไม่ได้",
            "แต่ทุกลมหายใจยังร้องเป็นชื่อเธอ",
            "ขอให้ท่อนนี้พาใจฉันผ่านคืนนี้ไป",
        ],
        "Verse 2": [
            "ฉันเห็นเงาเราซ้อนอยู่บนกระจกบานเดิม",
            "แก้วกาแฟเย็นลงเหมือนวันที่เธอจากไป",
            "เพื่อนบอกว่าเดี๋ยวเวลาก็รักษาทุกอย่าง",
            "แต่เวลายังเก็บเธอไว้ในทุกวินาที",
            "ถนนเส้นเดิมไม่เคยยาวเท่าคืนนี้",
            "เมื่อไม่มีมือเธอให้จับเหมือนวันก่อน",
        ],
        "Bridge": [
            "ถ้าวันหนึ่งฉันร้องไห้โดยไม่เจ็บอีกแล้ว",
            "คงเป็นวันที่ฉันยอมให้เธอเป็นความทรงจำ",
            "แต่คืนนี้ขอร้องเพลงนี้ให้สุดหัวใจ",
            "ก่อนจะปล่อยคำว่าเราให้ลอยไปกับฝน",
        ],
        "Final Chorus": [
            hook,
            "ทำไมใจยังเรียกหาเธอดังขึ้นทุกครั้ง",
            "ถึงรู้ว่าปลายทางไม่มีเธอยืนรอ",
            "ฉันจะร้องจนความคิดถึงค่อย ๆ เบาลง",
            "ให้เพลงสุดท้ายพาฉันรักตัวเองอีกครั้ง",
            "และถ้าพรุ่งนี้ฟ้าสว่างโดยไม่มีเธอ",
            "ฉันจะเดินต่อไปพร้อมรอยแผลที่ยังสวยงาม",
        ],
        "Outro": [
            "(emotional fade out)",
            "สุดท้ายเธอยังอยู่ในเพลงนี้",
            "แต่ฉันจะไม่หยุดชีวิตไว้ที่เดิม",
        ],
    }


def expand_lyrics_to_full_song(lyrics: str, *, hook_text: str = "", idea: str = "", artist_preset: dict[str, Any] | None = None) -> str:
    existing = parse_lyric_sections(lyrics)
    defaults = _default_lines(hook_text, idea)
    final: dict[str, list[str]] = {}
    for section in REQUIRED_SECTIONS:
        source = existing.get(section) or existing.get(section.upper()) or []
        merged = _dedupe([*source, *defaults.get(section, [])])
        min_lines = 1
        if section in {"Verse 1", "Verse 2"}:
            min_lines = 4
        elif section in {"Pre-Chorus", "Bridge"}:
            min_lines = 2
        elif section in {"Chorus", "Final Chorus"}:
            min_lines = 4
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
    return _render_sections(final)


def _render_sections(sections: dict[str, list[str]]) -> str:
    blocks = []
    for section in ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Pre-Chorus", "Chorus", "Bridge", "Final Chorus", "Outro"]:
        lines = sections.get(section) or []
        if not lines and section in {"Pre-Chorus", "Chorus"}:
            lines = sections.get(section, [])
        if lines:
            blocks.append(f"[{section}]\n" + "\n".join(lines))
    return "\n\n".join(blocks).strip()


def ensure_full_song_structure(lyrics: str, *, hook_text: str = "", idea: str = "", artist_preset: dict[str, Any] | None = None) -> dict[str, Any]:
    before = analyze_song_completeness(lyrics)
    if before["ok"]:
        return {"lyrics": lyrics.strip(), "expanded": False, "before": before, "after": before}
    expanded = expand_lyrics_to_full_song(lyrics, hook_text=hook_text, idea=idea, artist_preset=artist_preset)
    after = analyze_song_completeness(expanded)
    return {"lyrics": expanded, "expanded": True, "before": before, "after": after}
