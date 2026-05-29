from __future__ import annotations

import re
from typing import Any


AWKWARD_PATTERNS = [
    "ในหัวใจของฉันนั้น",
    "ความรู้สึกของฉัน",
    "ไม่สามารถที่จะ",
    "ทำให้ฉันนั้น",
    "อย่างมากมาย",
    "ณ ตอนนี้",
]

REWRITE_MAP = {
    "ในหัวใจของฉันนั้น": "ในใจฉัน",
    "ความรู้สึกของฉัน": "ใจฉัน",
    "ไม่สามารถที่จะ": "ไม่อาจ",
    "ทำให้ฉันนั้น": "ทำให้ฉัน",
    "อย่างมากมาย": "เหลือเกิน",
    "ณ ตอนนี้": "ตอนนี้",
}


def rewrite_thai_line(line: str) -> str:
    text = str(line or "").strip()
    for awkward, natural in REWRITE_MAP.items():
        text = text.replace(awkward, natural)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(นะครับ|ค่ะค่ะ|ครับครับ)$", "", text).strip()
    return text


def detect_thai_quality_issues(text: str) -> list[str]:
    lowered = str(text or "")
    issues = [pattern for pattern in AWKWARD_PATTERNS if pattern in lowered]
    if re.search(r"(ฉันนั้น|เธอนั้น|ใจนั้น).*(นั้น)", lowered):
        issues.append("repetitive_that_ending")
    if re.search(r"(จะทำการ|ได้ทำการ)", lowered):
        issues.append("formal_translated_wording")
    return sorted(set(issues))


def clean_thai_output(text: str) -> str:
    lines = [rewrite_thai_line(line) if line.strip() and not line.strip().startswith("[") and not line.strip().startswith("(") else line.rstrip() for line in str(text or "").splitlines()]
    return "\n".join(lines).strip()


def build_thai_quality_report(text: str) -> dict[str, Any]:
    before = str(text or "")
    after = clean_thai_output(before)
    issues = detect_thai_quality_issues(before)
    return {
        "issues": issues,
        "rewritten": before != after,
        "line_count": len([line for line in after.splitlines() if line.strip()]),
        "quality_ok": not issues,
    }
