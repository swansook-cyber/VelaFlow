from __future__ import annotations

import json
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
EMERGENCY_FALLBACK_TITLE = "เพลงที่ยังไม่จบ"

TITLE_SOURCE_WEIGHTS = {
    "provider_title": 100,
    "hook": 96,
    "final_chorus": 94,
    "chorus": 92,
    "idea": 82,
    "provisional": 76,
    "lyrics": 68,
    "fallback": 20,
}

_THAI_COMBINING_MARKS = "\u0e31\u0e34\u0e35\u0e36\u0e37\u0e38\u0e39\u0e3a\u0e47\u0e48\u0e49\u0e4a\u0e4b\u0e4c\u0e4d\u0e4e"
_INCOMPLETE_TITLE_ENDINGS = ("และ", "แต่", "เพราะ", "กับ", "ของ", "ที่", "ว่า", "ให้", "ก็", "แม้", "แล้ว")


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


_TITLE_LABEL_RE = re.compile(
    r"^\s*(?:song\s*title|title|ชื่อเพลง)\s*[:：-]\s*",
    re.IGNORECASE,
)


def clean_generated_song_title(value: str) -> str:
    """Return one conservative, display-safe title from generated text.

    This parser is intentionally limited to generated values. User-entered titles
    remain authoritative and are not passed through this cleanup path.
    """
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    text = re.sub(r"^```(?:json|text|markdown)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    if text.startswith(("{", "[")):
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                text = str(payload.get("title") or payload.get("song_title") or payload.get("Song Title") or "")
            elif isinstance(payload, list) and payload:
                first = payload[0]
                text = str((first.get("title") if isinstance(first, dict) else first) or "")
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"^\s*(?:[-*#]+|\d+[.)])\s*", "", raw).strip()
        line = _TITLE_LABEL_RE.sub("", line).strip(" `\"'“”‘’")
        if line:
            lines.append(line)
    if not lines:
        return ""

    # A generated response containing several candidates resolves to its first
    # clean candidate; downstream code must never receive the whole response.
    title = re.split(r"\s*(?:\||;| / )\s*", lines[0], maxsplit=1)[0].strip()
    title = re.sub(r"[*_`]+", "", title)
    title = re.sub(r"\s+", " ", title).strip(" ,.;:!?-–—\"'“”‘’")

    # Remove exact duplicated fragments without changing the title's meaning.
    words = title.split()
    if len(words) % 2 == 0 and words[: len(words) // 2] == words[len(words) // 2 :]:
        words = words[: len(words) // 2]

    # Character-count truncation in the legacy candidate path could leave a
    # short fragment of the opening Thai word at the end: "หมดใจของเธอ หม".
    if len(words) >= 2 and 1 <= len(words[-1]) <= 2 and words[0].startswith(words[-1]):
        words.pop()
    return re.sub(r"\s+", " ", " ".join(words)).strip()


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", _clean_phrase(value))


def _normalized_title_text(value: str) -> str:
    text = str(value or "").lower().replace("…", "...")
    text = re.sub(r"\.{2,}", " ", text)
    text = re.sub(r"[^a-z0-9\u0e00-\u0e7f]+", "", text)
    return text.strip()


def _character_ngrams(value: str, size: int = 3) -> set[str]:
    text = _normalized_title_text(value)
    if not text:
        return set()
    if len(text) <= size:
        return {text}
    return {text[index:index + size] for index in range(len(text) - size + 1)}


def title_context_similarity(left: str, right: str) -> float:
    left_text = _normalized_title_text(left)
    right_text = _normalized_title_text(right)
    if not left_text or not right_text:
        return 0.0
    if left_text == right_text:
        return 1.0
    if left_text in right_text or right_text in left_text:
        return min(len(left_text), len(right_text)) / max(len(left_text), len(right_text))
    left_grams = _character_ngrams(left_text)
    right_grams = _character_ngrams(right_text)
    if not left_grams or not right_grams:
        return 0.0
    return len(left_grams & right_grams) / len(left_grams | right_grams)


def _safe_clause_candidates(value: str) -> list[str]:
    """Extract whole Thai clauses without arbitrary character slicing."""
    clauses: list[str] = []
    for raw_line in str(value or "").replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = re.sub(r"\.{2,}|…+", " | ", raw_line)
        line = re.sub(r"\s*[,!?.:;|/\\—–-]+\s*", " | ", line)
        primary = [part.strip() for part in line.split("|") if part.strip()]
        for part in primary:
            natural_parts = re.split(r"\s+(?:แต่|เพราะ|ทั้งที่|กับ|แล้ว)\s+|\s+", part)
            clauses.append(part)
            clauses.extend(piece.strip() for piece in natural_parts if piece.strip() and piece.strip() != part)
            # Connectives are often written without spaces in Thai. Keep both
            # sides only when they are already complete compact phrases.
            for connective in ("แต่", "เพราะ", "ทั้งที่"):
                if connective in part:
                    left, right = part.split(connective, 1)
                    clauses.extend(piece.strip() for piece in (left, right) if piece.strip())
    output: list[str] = []
    for clause in clauses:
        clean = clean_generated_song_title(clause)
        compact = _compact(clean)
        if 3 <= len(compact) <= 24 and clean not in output:
            output.append(clean)
    return output


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
    # Never cut Thai by character count: it can leave a partial syllable that
    # then contaminates filenames and release metadata. Long source phrases are
    # already filtered by title validation; compact candidates come from the
    # keyword/fragment paths above.
    return []


def title_is_valid(title: str, source_text: str = "") -> bool:
    clean = clean_generated_song_title(title)
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
    if len(compact) < 3 or len(compact) > 24:
        return False
    if clean[0] in _THAI_COMBINING_MARKS or re.search(rf"(?:^|\s)[{_THAI_COMBINING_MARKS}]", clean):
        return False
    if re.search(r"[.!?,:;\-—–…]+$", clean):
        return False
    if any(clean.endswith(ending) for ending in _INCOMPLETE_TITLE_ENDINGS):
        return False
    if source and compact == source:
        return False
    if re.search(r"(.{2,})\1\1", compact):
        return False
    awkward = ["แม้", "ทั้งที่", "เพราะว่า", "อยากได้เพลง", "เพลงเกี่ยวกับ"]
    return not any(clean.startswith(word) for word in awkward)


def score_song_title_candidate(title: str, source_text: str = "") -> dict[str, Any]:
    title = clean_generated_song_title(title)
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
    context_similarity = title_context_similarity(title, source_text)
    penalty = 0
    if source and compact and compact in source and len(compact) > 16:
        penalty += 25
    if source and compact and compact in source and len(compact) <= 14:
        penalty -= 12
    if source and context_similarity < 0.12:
        penalty += 16
    if _clean_phrase(title).lower() in GENERIC_TITLE_TERMS:
        penalty += 60
    if "ไม่กลับมา" in source and _clean_phrase(title) == "คนที่ไม่กลับมา":
        penalty -= 12
    if not title_is_valid(title, source_text):
        penalty += 80
    total = int((brevity + emotional + memorability + caption + spotify + tiktok + uniqueness) / 7 + min(24, context_similarity * 28) - penalty)
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
        "context_relevance": max(0, min(100, round(context_similarity * 100))),
        "tiktok_spotify_friendliness": max(0, min(100, int((spotify + tiktok) / 2))),
    }


def _candidate_values(value: str) -> list[str]:
    values: list[str] = []
    for line in _usable_lines(value):
        values.extend(_keyword_candidates(line))
        values.extend(_fragment_candidates(line))
        values.extend(_simplified_candidates(line))
        values.extend(_safe_clause_candidates(line))
    return _dedupe(values)


def _source_support(title: str, sources: dict[str, str]) -> tuple[list[str], int]:
    support: list[str] = []
    weighted_scores: list[float] = []
    for source_name, source_text in sources.items():
        if not source_text:
            continue
        similarity = title_context_similarity(title, source_text)
        weighted_scores.append(similarity * TITLE_SOURCE_WEIGHTS.get(source_name, 60))
        if similarity >= 0.28 or _normalized_title_text(title) in _normalized_title_text(source_text):
            support.append(source_name)
    return support, round(max(weighted_scores, default=0.0))


def _prune_near_duplicate_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: (item.get("score", 0), item.get("context_relevance", 0)), reverse=True):
        duplicate = next((item for item in kept if title_context_similarity(candidate["title"], item["title"]) >= 0.92), None)
        if duplicate is None:
            kept.append(candidate)
    return kept


def _emergency_fallback(context: str) -> str:
    compact = _compact(context)
    if "ลืม" in compact:
        return "ลืมไม่ลง"
    if "คิดถึง" in compact or "คืน" in compact:
        return "คืนที่ไม่มีเธอ"
    if "กลับ" in compact:
        return "คนที่ไม่กลับมา"
    if "ใจ" in compact and ("พอ" in compact or "หยุด" in compact):
        return "พอได้แล้วใจ"
    return EMERGENCY_FALLBACK_TITLE


def generate_contextual_title_candidates(
    *,
    idea: str = "",
    hook_text: str = "",
    provider_title: str = "",
    chorus: str = "",
    final_chorus: str = "",
    provisional_title: str = "",
    lyrics: str = "",
    previous_title: str = "",
    previous_fingerprint: str = "",
    current_fingerprint: str = "",
    require_central_support: bool = False,
) -> list[dict[str, Any]]:
    sources = {
        "provider_title": provider_title,
        "hook": hook_text,
        "final_chorus": final_chorus,
        "chorus": chorus,
        "idea": idea,
        "provisional": provisional_title,
        "lyrics": lyrics,
    }
    source_text = "\n".join(value for value in sources.values() if value)
    candidate_sources: dict[str, set[str]] = {}
    candidate_titles: dict[str, str] = {}
    for source_name, source_value in sources.items():
        if not source_value:
            continue
        for candidate in _candidate_values(source_value):
            key = _normalized_title_text(candidate)
            if key:
                candidate_titles.setdefault(key, candidate)
                candidate_sources.setdefault(key, set()).add(source_name)

    contextual: list[dict[str, Any]] = []
    for key, title in candidate_titles.items():
        # Source-aware ranking already measures relevance. Validate the title's
        # shape independently so a concise, non-generic Idea may legitimately
        # become the title instead of being rejected as an exact source phrase.
        if not title_is_valid(title, ""):
            continue
        origin_sources = sorted(candidate_sources.get(key, set()), key=lambda name: TITLE_SOURCE_WEIGHTS.get(name, 0), reverse=True)
        support, contextual_relevance = _source_support(title, sources)
        support = sorted(set(support) | set(origin_sources), key=lambda name: TITLE_SOURCE_WEIGHTS.get(name, 0), reverse=True)
        if not support:
            continue
        base = score_song_title_candidate(title, source_text)
        source_quality = max((TITLE_SOURCE_WEIGHTS.get(name, 60) for name in origin_sources), default=60)
        support_bonus = min(12, max(0, len(support) - 1) * 4)
        final_score = round((base["score"] * 0.45) + (contextual_relevance * 0.42) + (source_quality * 0.13) + support_bonus)
        normalized_idea = _normalized_title_text(idea)
        normalized_title = _normalized_title_text(title)
        if (
            normalized_idea
            and normalized_title in normalized_idea
            and len(_compact(title)) > 14
            and len(normalized_title) / max(1, len(normalized_idea)) >= 0.7
        ):
            final_score -= 30
        previous_match = bool(previous_title and title_context_similarity(title, previous_title) >= 0.86)
        central_support = bool(set(support) & {"hook", "chorus", "final_chorus"})
        provider_context_support = "provider_title" in origin_sources and bool(set(support) & {"hook", "chorus", "final_chorus", "idea"})
        if require_central_support and not (central_support or provider_context_support):
            continue
        contextual.append({
            **base,
            "score": max(0, min(100, final_score)),
            "sources": origin_sources,
            "support_sources": support,
            "source_support": len(support),
            "context_relevance": contextual_relevance,
            "previous_title_match": previous_match,
            "fallback": False,
            "central_support": central_support or provider_context_support,
        })

    contextual = _prune_near_duplicate_candidates(contextual)
    fingerprint_changed = bool(previous_fingerprint and current_fingerprint and previous_fingerprint != current_fingerprint)
    if fingerprint_changed and previous_title and len(contextual) > 1:
        for candidate in contextual:
            if not candidate["previous_title_match"]:
                continue
            competitor_relevance = max((item["context_relevance"] for item in contextual if item is not candidate), default=-1)
            if competitor_relevance >= candidate["context_relevance"] - 4:
                candidate["score"] = max(0, candidate["score"] - 5)
                candidate["previous_title_penalty"] = 5

    contextual.sort(key=lambda item: (item["score"], item["context_relevance"], item["source_support"]), reverse=True)
    if contextual:
        return contextual[:10]

    fallback_title = _emergency_fallback(source_text)
    fallback = score_song_title_candidate(fallback_title, "")
    fallback.update({
        "sources": ["fallback"],
        "support_sources": [],
        "source_support": 0,
        "context_relevance": 0,
        "previous_title_match": bool(previous_title and title_context_similarity(fallback_title, previous_title) >= 0.86),
        "fallback": True,
        "central_support": False,
    })
    return [fallback]


def generate_song_title_candidates(idea: str = "", hook_text: str = "", lyrics: str = "") -> list[dict[str, Any]]:
    return generate_contextual_title_candidates(idea=idea, hook_text=hook_text, lyrics="\n".join(_usable_lines(lyrics)[:6]))


def extract_central_title_sections(lyrics: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"chorus": [], "final_chorus": []}
    active = ""
    for raw_line in str(lyrics or "").replace("\r\n", "\n").replace("\r", "\n").splitlines():
        header = re.match(r"^\s*\[([^\]]+)\]\s*$", raw_line)
        if header:
            name = re.sub(r"\s+", " ", header.group(1).strip().lower())
            if "final" in name and "chorus" in name:
                active = "final_chorus"
            elif "chorus" in name and "pre" not in name and "post" not in name:
                active = "chorus"
            else:
                active = ""
            continue
        line = _clean_phrase(raw_line)
        if active and line and not (raw_line.strip().startswith("(") and raw_line.strip().endswith(")")):
            sections[active].append(line)
    return {key: "\n".join(values) for key, values in sections.items()}


def generate_song_title_from_idea(idea: str = "", hook_text: str = "", lyrics: str = "") -> str:
    """Create a short commercial Thai title from idea + hook without needing an API."""
    candidates = generate_song_title_candidates(idea=idea, hook_text=hook_text, lyrics=lyrics)
    return candidates[0]["title"] if candidates else "ลืมไม่ลง"


def resolve_song_title(song: dict[str, Any], project_name: str = "") -> str:
    manual = str(song.get("title") or song.get("song_title") or "").strip()
    if manual and not is_placeholder_song_title(manual):
        blueprint = song.get("song_blueprint") if isinstance(song.get("song_blueprint"), dict) else {}
        hook_contract = blueprint.get("hook_contract") if isinstance(blueprint.get("hook_contract"), dict) else {}
        if hook_contract.get("title_is_manual") is True or song.get("manual_title") is True:
            return manual
        generated_provenance = hook_contract.get("title_is_manual") is False or song.get("title_generated_from_idea") is True
        if generated_provenance:
            cleaned = clean_generated_song_title(manual)
            if cleaned and title_is_valid(cleaned, str(song.get("idea") or song.get("song_idea") or "")):
                return cleaned
        else:
            # Legacy project titles predate title provenance and remain
            # authoritative for backward-compatible project/export naming.
            return manual
    return generate_song_title_from_idea(
        idea=str(song.get("idea") or song.get("song_idea") or song.get("concept") or project_name or ""),
        hook_text=str((song.get("selected_hook") or {}).get("hook_text") if isinstance(song.get("selected_hook"), dict) else song.get("selected_hook_text") or ""),
        lyrics=str(song.get("normalized_song_output") or song.get("complete_lyrics") or ""),
    )
