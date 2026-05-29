from __future__ import annotations

import re
from typing import Any


PLACEHOLDER_TITLES = {
    "",
    "demo song",
    "untitled song",
    "new song",
    "song only",
    "current session",
    "project",
    "เพลงใหม่ของฉัน",
}

FALLBACK_TITLES = ["ลืมไม่ลง", "ยังอยู่ในใจ", "คืนที่ไม่มีเธอ", "พอได้แล้วใจ", "คนที่ไม่กลับมา"]


GENERIC_TITLE_TERMS = {"รัก", "ความรัก", "เพลงรัก", "คิดถึง", "อกหัก", "เศร้า", "เหงา", "love", "sad", "lonely", "heartbreak"}

COMMERCIAL_EMOTIONAL_TITLES = [
    "คืนที่ยังรัก",
    "เก็บรักไว้ในใจ",
    "รักที่ไม่พูดไป",
    "หัวใจยังรอ",
    "คนที่ใจเลือก",
    "ยังมีเธอในเพลง",
    "ถ้าใจยังรัก",
    "รักในวันที่สาย",
    "คำว่ารักยังอยู่",
    "ไม่กล้าลืมเธอ",
]


def is_placeholder_song_title(value: str | None) -> bool:
    normalized = re.sub(r"\s+", " ", str(value or "").strip()).lower()
    return normalized in PLACEHOLDER_TITLES or normalized.startswith("demo_song")


def _clean_phrase(value: str) -> str:
    text = re.sub(r"[\[\]{}()\"'“”‘’!?.,:;|/\\]+", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", _clean_phrase(value))


def _usable_lines(value: str) -> list[str]:
    lines = []
    for raw in str(value or "").replace("\r\n", "\n").splitlines():
        line = _clean_phrase(raw)
        if line and not line.startswith("[") and not (line.startswith("(") and line.endswith(")")):
            lines.append(line)
    return lines


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        clean = _clean_phrase(value)
        key = _compact(clean)
        if clean and key and key not in seen and not is_placeholder_song_title(clean):
            out.append(clean)
            seen.add(key)
    return out


def _keyword_candidates(text: str) -> list[str]:
    compact = _compact(text)
    lowered = _clean_phrase(text).lower()
    candidates: list[str] = []
    if "เพลงรัก" in lowered or ("รัก" in lowered and not any(word in lowered for word in ["อกหัก", "เลิก", "ลืม", "ไม่กลับ", "กลับมา"])):
        candidates += COMMERCIAL_EMOTIONAL_TITLES
    if "เศร้า" in lowered or "เหงา" in lowered:
        candidates += ["คืนที่เงียบไป", "เหงาเกินจะนอน", "ใจที่ไม่มีใคร", "แสงสุดท้ายของเรา"]
    if "อกหัก" in lowered:
        candidates += ["รักในวันที่สาย", "แตกสลายช้า ๆ", "ยังเจ็บที่เดิม", "คนแพ้ที่ยังรัก"]
    if "พอได้แล้วใจ" in compact:
        candidates.append("พอได้แล้วใจ")
    if "ลืมแฟนเก่าไม่ได้" in compact or "ลืมเธอไม่ได้" in compact or ("ลืม" in compact and "ไม่ได้" in compact):
        candidates += ["ลืมไม่ลง", "ลืมเธอไม่ได้"]
    if "คิดถึง" in compact and "ทุกคืน" in compact:
        candidates += ["คืนที่ไม่มีเธอ", "ยังอยู่ในใจ"]
    elif "คิดถึง" in compact:
        candidates += ["ยังอยู่ในใจ", "คิดถึงเธอ"]
    if "ไม่กลับมา" in compact or "กลับมาไม่ได้" in compact:
        candidates += ["คนที่ไม่กลับมา", "ไม่มีทางกลับมา"]
    if "ไม่มีเธอ" in compact:
        candidates += ["คืนที่ไม่มีเธอ", "วันที่ไม่มีเธอ"]
    if "ใจ" in compact and ("พอ" in compact or "หยุด" in compact):
        candidates.append("พอได้แล้วใจ")
    if "ฝน" in compact and ("คิดถึง" in compact or "เธอ" in compact):
        candidates.append("คืนฝนพรำ")
    if "รัก" in compact and "ไม่เปลี่ยน" in compact:
        candidates.append("รักไม่เปลี่ยน")
    return candidates


def _fragment_candidates(text: str) -> list[str]:
    phrase = _clean_phrase(text)
    parts = re.split(r"\s*(?:แม้|ทั้งที่|แต่|เพราะ|ในวันที่|วันที่|ก็|และ)\s*", phrase)
    candidates = []
    for part in parts:
        part = _clean_phrase(part)
        if not part:
            continue
        compact = _compact(part)
        if 4 <= len(compact) <= 18:
            candidates.append(part)
        if "เธอ" in compact and len(compact) > 10:
            candidates.append("ไม่มีเธอ" if "ไม่มี" in compact else "ยังอยู่ในใจ")
    return candidates


def _simplified_candidates(text: str) -> list[str]:
    phrase = _clean_phrase(text)
    for prefix in ["เพลงเกี่ยวกับ", "เรื่อง", "อยากได้เพลง", "เพลง", "เกี่ยวกับ", "ยัง"]:
        if phrase.startswith(prefix) and len(phrase) > len(prefix) + 2:
            phrase = phrase[len(prefix):].strip()
    compact = _compact(phrase)
    if len(compact) <= 18:
        return [phrase]
    return [phrase[:14].strip()]


def title_is_valid(title: str, source_text: str = "") -> bool:
    clean = _clean_phrase(title)
    compact = _compact(clean)
    source = _compact(source_text)
    clean_lower = clean.lower()
    source_lower = _clean_phrase(source_text).lower()
    if not clean or is_placeholder_song_title(clean):
        return False
    if clean_lower in GENERIC_TITLE_TERMS:
        return False
    if source_lower and clean_lower == source_lower:
        return False
    if source_lower.startswith("เพลง") and clean_lower == source_lower.replace("เพลง", "", 1).strip():
        return False
    if len(clean.split()) > 6:
        return False
    if len(compact) < 3 or len(compact) > 20:
        return False
    if source and compact == source:
        return False
    if re.search(r"(.{2,})\1\1", compact):
        return False
    awkward = ["แม้", "ทั้งที่", "เพราะว่า", "อยากได้เพลง", "เพลงเกี่ยวกับ"]
    return not any(clean.startswith(word) for word in awkward)


def score_song_title_candidate(title: str, source_text: str = "") -> dict[str, Any]:
    compact = _compact(title)
    source = _compact(source_text)
    brevity = max(0, 100 - max(0, len(compact) - 8) * 8)
    emotional_terms = ["ใจ", "ลืม", "คิดถึง", "คืน", "เธอ", "รัก", "กลับมา", "เหงา", "ฝน"]
    emotional = 50 + min(40, sum(10 for term in emotional_terms if term in compact))
    memorability = 62 + (18 if 4 <= len(compact) <= 12 else 0) + (8 if any(term in compact for term in ["ใจ", "คืน", "เธอ"]) else 0)
    commercial = 68 + (12 if len(compact) <= 14 else -10) + (8 if title in FALLBACK_TITLES else 0)
    caption = 68 + (14 if 5 <= len(compact) <= 16 else 0) + (8 if any(term in compact for term in ["ใจ", "คืน", "เธอ", "รัก"]) else 0)
    spotify = 70 + (12 if len(compact) <= 16 else -8) + (8 if any(term in compact for term in ["ใจ", "คืน", "รัก", "เธอ"]) else 0)
    tiktok = 70 + (12 if len(compact) <= 14 else 0) + (8 if any(term in compact for term in ["ใจ", "รัก", "เธอ"]) else 0)
    uniqueness = 72 + (12 if title not in FALLBACK_TITLES else -4)
    relevance_terms = ["ใจ", "ลืม", "คิดถึง", "คืน", "เธอ", "รัก", "กลับมา", "ไม่มี", "ฝน", "พอ"]
    relevance = sum(1 for term in relevance_terms if term in compact and term in source)
    penalty = 0
    if source and compact and compact in source and len(compact) > 16:
        penalty += 25
    if source and compact and compact in source and len(compact) <= 14:
        penalty -= 12
    if source and relevance == 0:
        penalty += 16
    if _clean_phrase(title).lower() in GENERIC_TITLE_TERMS:
        penalty += 60
    if "ไม่กลับมา" in source and _clean_phrase(title) == "คนที่ไม่กลับมา":
        penalty -= 12
    if _clean_phrase(title) == "พอได้แล้วใจ":
        penalty -= 4
    if not title_is_valid(title, source_text):
        penalty += 80
    total = int((brevity + emotional + memorability + caption + spotify + tiktok + uniqueness) / 7 + min(24, relevance * 6) - penalty)
    return {
        "title": _clean_phrase(title),
        "score": max(0, min(100, total)),
        "memorability": max(0, min(100, memorability)),
        "emotional_impact": max(0, min(100, emotional)),
        "brevity": max(0, min(100, brevity)),
        "commercial_feel": max(0, min(100, commercial)),
        "caption_potential": max(0, min(100, caption)),
        "spotify_friendliness": max(0, min(100, spotify)),
        "tiktok_friendliness": max(0, min(100, tiktok)),
        "uniqueness": max(0, min(100, uniqueness)),
        "tiktok_spotify_friendliness": max(0, min(100, int((spotify + tiktok) / 2))),
    }


def generate_song_title_candidates(idea: str = "", hook_text: str = "", lyrics: str = "") -> list[dict[str, Any]]:
    sources = [hook_text, idea, lyrics]
    source_text = "\n".join(str(item or "") for item in sources)
    raw_candidates: list[str] = []
    for line in [*_usable_lines(hook_text), *_usable_lines(idea), *_usable_lines(lyrics)[:6]]:
        raw_candidates.extend(_keyword_candidates(line))
        raw_candidates.extend(_fragment_candidates(line))
        raw_candidates.extend(_simplified_candidates(line))
    raw_candidates.extend(FALLBACK_TITLES)
    scored = [score_song_title_candidate(candidate, source_text) for candidate in _dedupe(raw_candidates)]
    scored = [item for item in scored if item["score"] >= 45 and title_is_valid(item["title"], source_text)]
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:10]


def generate_song_title_from_idea(idea: str = "", hook_text: str = "", lyrics: str = "") -> str:
    """Create a short commercial Thai title from idea + hook without needing an API."""
    candidates = generate_song_title_candidates(idea=idea, hook_text=hook_text, lyrics=lyrics)
    return candidates[0]["title"] if candidates else "ลืมไม่ลง"


def resolve_song_title(song: dict[str, Any], project_name: str = "") -> str:
    manual = str(song.get("title") or song.get("song_title") or "").strip()
    if manual and not is_placeholder_song_title(manual):
        return manual
    return generate_song_title_from_idea(
        idea=str(song.get("idea") or song.get("song_idea") or song.get("concept") or project_name or ""),
        hook_text=str((song.get("selected_hook") or {}).get("hook_text") if isinstance(song.get("selected_hook"), dict) else song.get("selected_hook_text") or ""),
        lyrics=str(song.get("normalized_song_output") or song.get("complete_lyrics") or ""),
    )
