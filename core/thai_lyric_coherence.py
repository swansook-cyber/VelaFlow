"""Conservative Thai lyric narrative checks; advisory only, no rewriting."""
from __future__ import annotations

import re
from typing import Any

_SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_TAG = re.compile(r"^\s*\([^\n]*\)\s*$")


def _lyric_lines(lyrics: str) -> list[tuple[str, str]]:
    section = ""
    result: list[tuple[str, str]] = []
    for raw in str(lyrics or "").splitlines():
        line = raw.strip()
        match = _SECTION.fullmatch(line)
        if match:
            section = match.group(1).strip().lower()
            continue
        if line and not _TAG.fullmatch(line) and not line.startswith("["):
            result.append((section, line))
    return result


def review_thai_story_coherence(lyrics: str, idea: str = "", selected_hook: str = "") -> dict[str, Any]:
    """Review likely narrative ambiguities, without changing authored lyrics.

    Heuristics are deliberately conservative: Thai subjects are often omitted
    and only the songwriter can decide whether a metaphor is intentional.
    """
    lines = _lyric_lines(lyrics)
    chorus = [line for section, line in lines if "chorus" in section and "pre" not in section and "post" not in section]
    hook = str(selected_hook or "").strip() or (chorus[0] if chorus else "")
    norm = lambda text: re.sub(r"\s+", "", str(text or ""))
    narrative = norm(idea) + "".join(norm(line) for _, line in lines)
    warnings: list[dict[str, str]] = []

    return_signals = ("เขากลับมา", "คนรักเก่ากลับมา", "ตัวจริงกลับมา")
    disappearance_signals = ("พอเขาหาย", "เมื่อเขาหาย", "เขาหายไป")
    if any(term in narrative for term in return_signals) and any(term in norm(hook) for term in disappearance_signals):
        warnings.append({
            "code": "hook_return_disappearance_ambiguity",
            "severity": "review",
            "message": "Hook พูดถึงการหายไป แต่เนื้อเรื่องกล่าวถึงการกลับมา ควรตรวจว่าหมายถึงเหตุการณ์เดียวกันหรือไม่",
            "suggestion": "ตรวจลำดับเหตุการณ์และสรรพนามก่อนเผยแพร่",
        })

    # Report long lines as *visual* character counts; this does NOT assert
    # syllable count or whether the line fits any particular melody or BPM.
    long_lines = [
        {"section": section, "text": line, "characters": len(norm(line))}
        for section, line in lines
        if len(norm(line)) >= 55
    ]
    if long_lines:
        warnings.append({
            "code": "long_lyric_lines",
            "severity": "review",
            "message": f"มี {len(long_lines)} บรรทัดยาวตั้งแต่ 55 ตัวอักษรขึ้นไป ควรทดลองร้องกับเมโลดี้จริง",
            "suggestion": "พิจารณาแบ่งวรรคหรือพักหายใจ โดยไม่ตัดคำอัตโนมัติ",
        })
    return {
        "passed": not warnings,
        "warnings": warnings,
        "checked_lines": len(lines),
        "advisory_only": True,
        "long_lines": long_lines,
        "method": "conservative_rule_based_v2",
    }
