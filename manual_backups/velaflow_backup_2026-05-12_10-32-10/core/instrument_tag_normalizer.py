from __future__ import annotations

import re
from typing import Any, Dict, List


THAI_PATTERN = re.compile(r"[\u0E00-\u0E7F]")
SECTION_PATTERN = re.compile(r"^\s*\[([^\]]+)\]")
PAREN_PATTERN = re.compile(r"\(([^()]*)\)")

TAG_TRANSLATION_MAP = {
    "กีต้าร์โปร่ง": "acoustic guitar",
    "กีตาร์โปร่ง": "acoustic guitar",
    "กีต้าร์คลีน": "clean electric guitar",
    "กีตาร์คลีน": "clean electric guitar",
    "เปียโนเศร้า": "emotional piano",
    "เปียโน": "piano",
    "แพดนุ่ม": "soft ambient pad",
    "แพด": "ambient pad",
    "เบสอุ่น": "warm bass",
    "กลองเบา": "soft drums",
    "กลองหนัก": "punchy drums",
    "จังหวะกลาง": "mid-tempo beat",
    "เมโลดี้เศร้า": "melancholic melody",
    "บรรยากาศเหงา": "lonely atmosphere",
    "ร้องนุ่ม": "smooth vocal delivery",
    "เสียงผู้ชาย": "male vocal",
    "ดนตรีค่อยๆ เฟด": "music slowly fades out",
    "ดนตรีค่อยๆ fade": "music slowly fades out",
    "เฟดเอาท์": "fade out",
    "คลอเบาๆ": "gentle accompaniment",
    "ค่อยๆ": "gradually",
    "ดนตรี": "music",
}

SECTION_FALLBACKS = {
    "Intro": "acoustic guitar strumming, soft ambient pad, intimate atmosphere",
    "Verse 1": "clean electric guitar picking, warm bass, smooth male vocal",
    "Verse 2": "rhythmic acoustic strumming, warm bass, relaxed drum groove",
    "Pre-Chorus": "drum pattern builds up slightly, light synth pad",
    "Chorus": "full band arrangement, catchy pop rock groove, emotional vocal delivery",
    "Post-Chorus": "melodic electric guitar hook, easy listening vibe",
    "Bridge": "music strips down, emotional piano, warm bass, intimate vocal focus",
    "Guitar Solo": "melodic pop-rock guitar solo, driving rhythm section",
    "Final Chorus": "maximum energy, full band, brighter vocal delivery, expanded emotion",
    "Outro": "music slowly fades out, lingering acoustic guitar chord",
}


def contains_thai(text: str) -> bool:
    return bool(THAI_PATTERN.search(text or ""))


def normalize_instrument_tag(tag_text: str, section_name: str | None = None, artist_preset: Dict[str, Any] | None = None) -> str:
    value = (tag_text or "").strip()
    if not contains_thai(value):
        return value
    lowered = value.lower()
    replacements: List[str] = []
    for thai, english in TAG_TRANSLATION_MAP.items():
        if thai in value or thai.lower() in lowered:
            replacements.append(english)
    if replacements:
        cleaned = _dedupe(replacements)
        return ", ".join(cleaned)
    preset_tags = (artist_preset or {}).get("section_instrument_tags", {}) or {}
    return preset_tags.get(section_name or "", "") or SECTION_FALLBACKS.get(section_name or "", "full band arrangement, emotional vocal delivery, clean production")


def normalize_lyrics_tags(full_lyrics: str, artist_preset: Dict[str, Any] | None = None) -> str:
    lines = []
    current_section = None
    for line in (full_lyrics or "").splitlines():
        section_match = SECTION_PATTERN.match(line)
        if section_match:
            current_section = section_match.group(1).strip()

        def replace(match: re.Match[str]) -> str:
            inner = match.group(1)
            fixed = normalize_instrument_tag(inner, current_section, artist_preset)
            return f"({fixed})"

        lines.append(PAREN_PATTERN.sub(replace, line))
    return "\n".join(lines)


def validate_english_only_tags(full_lyrics: str) -> Dict[str, Any]:
    thai_tags = []
    for line_number, line in enumerate((full_lyrics or "").splitlines(), start=1):
        for match in PAREN_PATTERN.finditer(line):
            if contains_thai(match.group(1)):
                thai_tags.append({"line": line_number, "tag": match.group(1)})
    fixed = normalize_lyrics_tags(full_lyrics)
    return {"ok": not thai_tags, "thai_tags_found": thai_tags, "fixed_lyrics": fixed}


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    output = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output
