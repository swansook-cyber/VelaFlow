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
    """Return explainable, low-confidence warnings; never mutate authored text.

    A narrow contradiction heuristic flags a hook about someone disappearing
    when the user's story explicitly says that person *returns*. It cannot
    reliably identify every speaker or pronoun reference in Thai.
    """
    lines = _lyric_lines(lyrics)
    context = str(idea or "").replace(" ", "")
    hook = str(selected_hook or "").strip()
    chorus_lines = [line for section, line in lines if "chorus" in section and "pre" not in section]
    if not hook and chorus_lines:
        hook = chorus_lines[0]
    warnings: list[dict[str, str]] = []
    return_signals = ("เขากลับมา", "เขากลับไปหาเธอ", "คนรักเก่ากลับมา", "ตัวจริงกลับมา")
    disappearance_signals = ("พอเขาหาย", "เมื่อเขาหาย", "เขาหายไป")
    story_lines = " ".join(line for _, line in lines)
    story_context = (context + story_lines.replace(" ", ""))
    if any(signal in story_context for signal in return_signals) and any(signal in hook.replace(" ", "") for signal in disappearance_signals):
        warnings.append({
            "code": "hook_return_disappearance_ambiguity",
            "severity": "review",
            "message": "Hook พูดถึงการหายไป แต่เรื่องหลักกล่าวถึงการกลับมา ควรตรวจว่าหมายถึงเหตุการณ์เดียวกันหรือไม่",
            "suggestion": "ตรวจสรรพนามและลำดับเหตุการณ์ด้วยตนเองก่อนเผยแพร่",
        })
    return {"passed": not warnings, "warnings": warnings, "checked_lines": len(lines), "advisory_only": True}
