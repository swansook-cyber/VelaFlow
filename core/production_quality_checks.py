from __future__ import annotations

import re
from collections import Counter
from typing import Any


SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
MAJOR_SECTIONS = ("verse", "pre-chorus", "chorus", "bridge", "final chorus", "outro")
GENERIC_HOOK_LINES = {
    "ฉันยังรักเธอ",
    "ฉันยังคิดถึงเธอ",
    "ยังอยู่ในใจ",
    "ลืมไม่ลง",
    "ไม่ไหวแล้ว",
}
META_MARKERS = (
    "hook direction",
    "lyrics direction",
    "tiktok-ready",
    "spotify-friendly",
    "style prompt",
    "music style prompt",
    "bpm:",
    "weirdness:",
    "style influence:",
)


def _clean_lines(lyrics: str) -> list[str]:
    return [line.strip() for line in str(lyrics or "").replace("\r\n", "\n").split("\n")]


def _section_name(raw: str) -> str:
    value = re.sub(r"\s+", " ", raw.strip().lower())
    if value.startswith("verse"):
        return "verse"
    if value.startswith("pre"):
        return "pre-chorus"
    if value.startswith("final chorus") or value.startswith("final hook"):
        return "final chorus"
    if value.startswith("chorus") or value == "hook":
        return "chorus"
    if value.startswith("bridge"):
        return "bridge"
    if value.startswith("outro"):
        return "outro"
    if value.startswith("intro"):
        return "intro"
    return value


def parse_lyrics_for_review(lyrics: str) -> dict[str, list[list[str]]]:
    sections: dict[str, list[list[str]]] = {}
    current = "untagged"
    block: list[str] = []
    for line in _clean_lines(lyrics):
        match = SECTION_RE.match(line)
        if match:
            if block:
                sections.setdefault(current, []).append(block)
            current = _section_name(match.group(1))
            block = []
        elif line and not (line.startswith("(") and line.endswith(")")):
            block.append(line)
    if block:
        sections.setdefault(current, []).append(block)
    return sections


def check_lyrics_quality(lyrics: str) -> dict[str, Any]:
    """Review copy readiness without changing the supplied lyrics."""
    raw = str(lyrics or "").strip()
    sections = parse_lyrics_for_review(raw)
    lyric_lines = [
        line
        for line in _clean_lines(raw)
        if line and not SECTION_RE.match(line) and not (line.startswith("(") and line.endswith(")"))
    ]
    normalized = [re.sub(r"[\s.,!?…]+", "", line).lower() for line in lyric_lines]
    counts = Counter(line for line in normalized if len(line) >= 4)
    repeated = sorted(((line, count) for line, count in counts.items() if count > 2), key=lambda row: row[1], reverse=True)
    tags = [_section_name(match.group(1)) for line in _clean_lines(raw) if (match := SECTION_RE.match(line))]
    findings: list[str] = []

    missing = [name for name in MAJOR_SECTIONS if name not in sections]
    if missing:
        findings.append("เพิ่ม section ที่ยังขาด: " + ", ".join(missing[:3]))
    if len(lyric_lines) < 24:
        findings.append(f"เนื้อเพลงสั้นเกินไป ({len(lyric_lines)} บรรทัด); ควรขยาย Verse และ Final Chorus")
    elif len(lyric_lines) > 80:
        findings.append(f"เนื้อเพลงยาวมาก ({len(lyric_lines)} บรรทัด); ตัดบรรทัดที่ไม่ช่วยเรื่องหรือฮุก")
    chorus_blocks = sections.get("chorus", [])
    final_blocks = sections.get("final chorus", [])
    chorus_lines = chorus_blocks[0] if chorus_blocks else []
    chorus_normalized = {re.sub(r"[\s.,!?…]+", "", line).lower() for line in chorus_lines}
    repeated_non_hook = [row for row in repeated if row[0] not in chorus_normalized]
    if repeated_non_hook:
        findings.append("ลดบรรทัดซ้ำที่อยู่นอกการย้ำฮุกโดยตั้งใจ")
    if len(chorus_lines) < 4:
        findings.append("Chorus ควรมีอย่างน้อย 4 บรรทัดและมีประโยคหลักที่จำง่าย")
    elif chorus_lines and all(re.sub(r"[\s.,!?…]+", "", line) in GENERIC_HOOK_LINES for line in chorus_lines):
        findings.append("ฮุกยังทั่วไปเกินไป; เพิ่มภาพหรือสถานการณ์เฉพาะของเพลง")
    if chorus_lines and final_blocks:
        first = {re.sub(r"[\s.,!?…]+", "", line) for line in chorus_lines}
        final = {re.sub(r"[\s.,!?…]+", "", line) for line in final_blocks[0]}
        if len(final - first) < 2:
            findings.append("Final Chorus ควรเพิ่ม payoff ใหม่อย่างน้อย 2 บรรทัด")

    lower = raw.lower()
    meta_found = [marker for marker in META_MARKERS if marker in lower]
    if meta_found:
        findings.append("ลบข้อความ prompt/production ที่ปนอยู่ในเนื้อเพลง")
    mojibake = bool(re.search(r"(?:เน€|เธ[ก-๙]|ï¿½|�)", raw))
    long_lines = [line for line in lyric_lines if len(line) > 72]
    thai_lines = [line for line in lyric_lines if re.search(r"[ก-๙]", line)]
    if raw and not thai_lines:
        findings.append("ตรวจภาษาเนื้อเพลง: ไม่พบบรรทัดภาษาไทยที่อ่านได้")
    elif mojibake or len(long_lines) > max(2, len(lyric_lines) // 5):
        findings.append("ปรับบรรทัดภาษาไทยที่ยาวหรืออ่านผิดปกติให้สั้นและเป็นธรรมชาติ")

    duplicate_tags = [tag for tag, count in Counter(tags).items() if count > 2 and tag not in {"chorus", "pre-chorus"}]
    if duplicate_tags and len(findings) < 5:
        findings.append("ตรวจ section tags ที่ซ้ำหรือขัดกัน: " + ", ".join(duplicate_tags))
    findings = findings[:5]
    return {
        "ok": not findings,
        "status": "Good" if not findings else "Needs Review",
        "findings": findings,
        "diagnostics": {
            "line_count": len(lyric_lines),
            "section_tags": tags,
            "missing_sections": missing,
            "repeated_lines": [{"line": line, "count": count} for line, count in repeated[:8]],
            "chorus_line_count": len(chorus_lines),
            "final_chorus_unique_payoff_lines": len(set(final_blocks[0]) - set(chorus_lines)) if final_blocks else 0,
            "meta_markers": meta_found,
            "mojibake": mojibake,
            "long_line_count": len(long_lines),
        },
    }


def build_lyrics_improvement_prompt(lyrics: str, review: dict[str, Any]) -> str:
    findings = "\n".join(f"- {item}" for item in review.get("findings", [])) or "- Preserve the current strengths."
    return (
        "You are a careful Thai songwriter and lyric editor. Improve only the issues below. "
        "Preserve the song's story, title-worthy hook, section order, Thai language, and strong existing lines. "
        "Return only the complete revised lyrics with section tags. Do not include explanations, markdown fences, "
        "production notes, English marketing language, or music prompts.\n\n"
        f"REVIEW FINDINGS\n{findings}\n\nLYRICS\n{lyrics.strip()}"
    )


def clean_lyrics_improvement_preview(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(r"^```(?:text|markdown)?\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*```$", "", value)
    first_tag = re.search(r"(?m)^\s*\[[^\]]+\]", value)
    if first_tag:
        value = value[first_tag.start() :]
    return value.strip()
