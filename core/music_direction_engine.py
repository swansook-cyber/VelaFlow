from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


SECTION_ORDER = ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Bridge", "Final Chorus", "Outro"]


def _text(value: Any, default: str = "") -> str:
    return str(value or default).strip()


def _contains_any(text: str, words: list[str]) -> bool:
    lower = text.lower()
    return any(word.lower() in lower for word in words)


def _pick_bpm(genre: str, mood: str, style_preset: dict[str, Any] | None = None) -> int:
    source = " ".join([genre, mood, _text((style_preset or {}).get("genre")), _text((style_preset or {}).get("mood"))])
    if _contains_any(source, ["ballad", "acoustic", "soft", "emotional", "sad", "lonely"]):
        return 78
    if _contains_any(source, ["rock", "pop rock", "anthem"]):
        return 92
    if _contains_any(source, ["dance", "edm", "viral", "tiktok", "fast"]):
        return 112
    if _contains_any(source, ["r&b", "lofi", "chill"]):
        return 84
    return 88


def _instrument_palette(genre: str, mood: str, style_preset: dict[str, Any] | None = None) -> list[str]:
    source = " ".join([genre, mood, _text((style_preset or {}).get("arrangement")), _text((style_preset or {}).get("prompt_suffix"))])
    palette = ["soft piano", "warm acoustic guitar", "ambient pad", "subtle bass", "cinematic drums"]
    if _contains_any(source, ["rock", "pop rock", "band"]):
        palette = ["clean electric guitar", "warm acoustic guitar", "live bass", "tight pop rock drums", "cinematic strings"]
    elif _contains_any(source, ["r&b", "lofi", "chill"]):
        palette = ["soft rhodes piano", "lofi drum groove", "round sub bass", "warm guitar plucks", "vinyl texture pad"]
    elif _contains_any(source, ["dance", "edm", "viral", "tiktok"]):
        palette = ["bright synth plucks", "punchy kick", "sidechain pad", "modern pop bass", "clap/snare stack"]
    elif _contains_any(source, ["acoustic", "folk"]):
        palette = ["fingerpicked acoustic guitar", "soft piano", "brush snare", "upright bass warmth", "ambient reverb pad"]
    return palette


def _vocal_tone(vocal: str, mood: str, artist_preset: dict[str, Any] | None = None, style_preset: dict[str, Any] | None = None) -> str:
    preset_vocal = _text((artist_preset or {}).get("vocal_feeling") or (artist_preset or {}).get("vocal_style"))
    style_vocal = _text((style_preset or {}).get("vocal_style"))
    parts = [part for part in [vocal, style_vocal, preset_vocal] if part]
    base = ", ".join(parts) or "intimate emotional lead vocal"
    if _contains_any(mood, ["sad", "lonely", "heartbreak", "emotional"]):
        return f"{base}, close-mic delivery, fragile first verse, wider harmony release in chorus"
    if _contains_any(mood, ["hope", "motivational", "uplifting"]):
        return f"{base}, warm confident delivery, gradual lift, bright final chorus"
    return f"{base}, modern commercial delivery, clear diction, emotional chorus emphasis"


def build_music_direction(
    *,
    genre: str = "",
    mood: str = "",
    vocal: str = "",
    artist_preset: dict[str, Any] | None = None,
    style_preset: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Suno/Udio-ready arrangement guidance for a complete song."""
    preset = artist_preset or {}
    style = style_preset or {}
    genre_fusion = " / ".join(
        part for part in [
            _text(genre, _text(preset.get("genre") or preset.get("category"), "modern Thai pop")),
            _text(style.get("genre")),
            _text(preset.get("brand_style")),
        ] if part
    )
    mood_text = _text(mood, _text(style.get("mood"), _text(preset.get("mood"), "emotional cinematic")))
    bpm = _pick_bpm(genre_fusion, mood_text, style)
    palette = _instrument_palette(genre_fusion, mood_text, style)
    vocal_tone = _vocal_tone(vocal, mood_text, preset, style)
    energy_curve = {
        "Intro": 22,
        "Verse 1": 34,
        "Pre-Chorus": 58,
        "Chorus": 84,
        "Verse 2": 46,
        "Bridge": 62,
        "Final Chorus": 94,
        "Outro": 24,
    }
    section_tags = {
        "Intro": f"({palette[1]}, soft rhodes piano, warm ambient pad, {mood_text} atmosphere, intimate space)",
        "Verse 1": f"({palette[0]}, close vocal tone, soft kick/snare groove, restrained bass, detailed emotional storytelling)",
        "Pre-Chorus": "(building tension, rising toms, suspended chords, emotional lift, wider reverb tail)",
        "Chorus": f"(full band energy, catchy pop groove, layered harmony, {palette[-1]}, strong emotional release)",
        "Verse 2": f"(groove returns with more movement, {palette[2]}, subtle counter melody, vocal becomes more urgent)",
        "Bridge": "(cinematic breakdown, emotional piano lead, atmospheric texture, half-time drums, vulnerable vocal space)",
        "Final Chorus": "(big final chorus, stacked harmonies, stronger drums, wide cinematic lift, memorable singalong release)",
        "Outro": f"(emotional fade out, {palette[1]} echoes, ambient reverb tail, soft final vocal adlibs)",
    }
    vocal_energy_map = {
        "Intro": "breathy and close",
        "Verse 1": "intimate, restrained, conversational",
        "Pre-Chorus": "rising tension and brighter projection",
        "Chorus": "open, memorable, emotionally released",
        "Verse 2": "more urgent but still controlled",
        "Bridge": "fragile, cinematic, almost whispered",
        "Final Chorus": "full emotional lift with layered harmonies",
        "Outro": "soft release, fading adlibs",
    }
    master_prompt = (
        f"{genre_fusion or 'modern cinematic Thai pop'} at around {bpm} BPM. "
        f"Mood: {mood_text}. Instrument palette: {', '.join(palette)}. "
        f"Vocal tone: {vocal_tone}. Arrangement should feel commercial, modern, emotionally cinematic, "
        "Suno-ready and Udio-ready. Start intimate, build through the pre-chorus, open into a memorable chorus, "
        "drop into a cinematic bridge, then return with a larger final chorus and a soft emotional outro. "
        "Keep production consistent across sections with warm space, clear vocal focus, and no random genre changes."
    )
    arrangement_map = [
        {
            "section": section,
            "arrangement_tag": section_tags[section],
            "energy": energy_curve[section],
            "vocal_direction": vocal_energy_map[section],
        }
        for section in SECTION_ORDER
    ]
    return {
        "bpm": bpm,
        "genre_fusion": genre_fusion or "modern cinematic Thai pop",
        "instrument_palette": palette,
        "vocal_tone": vocal_tone,
        "energy_curve": energy_curve,
        "mood_progression": "intimate intro -> emotional verse -> rising pre-chorus -> strong chorus -> cinematic bridge -> bigger final chorus -> soft outro",
        "section_tags": section_tags,
        "arrangement_map": arrangement_map,
        "vocal_energy_map": vocal_energy_map,
        "master_music_style_prompt": master_prompt,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def export_music_direction_files(base_dir: str | Path, direction: dict[str, Any]) -> dict[str, str]:
    folder = Path(base_dir)
    folder.mkdir(parents=True, exist_ok=True)
    arrangement_lines = []
    for row in direction.get("arrangement_map", []):
        arrangement_lines.append(f"[{row.get('section', '')}]")
        arrangement_lines.append(str(row.get("arrangement_tag", "")))
        arrangement_lines.append(f"Energy: {row.get('energy', '')}")
        arrangement_lines.append(f"Vocal: {row.get('vocal_direction', '')}")
        arrangement_lines.append("")
    files = {
        "music_style_prompt.txt": str(direction.get("master_music_style_prompt", "")),
        "arrangement_map.txt": "\n".join(arrangement_lines).strip() + "\n",
        "vocal_direction.txt": f"{direction.get('vocal_tone', '')}\n\n{json.dumps(direction.get('vocal_energy_map', {}), ensure_ascii=False, indent=2)}\n",
        "instrument_palette.txt": "\n".join(str(item) for item in direction.get("instrument_palette", [])) + "\n",
        "energy_curve.json": json.dumps(direction.get("energy_curve", {}), ensure_ascii=False, indent=2),
    }
    written: dict[str, str] = {}
    for filename, content in files.items():
        path = folder / filename
        path.write_text(content, encoding="utf-8")
        written[filename] = str(path)
    return written
