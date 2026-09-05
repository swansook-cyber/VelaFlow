from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core.instrument_tag_normalizer import sanitize_production_tag_residue
from core.song_production_profile import resolve_song_production_profile


SECTION_ORDER = ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Bridge", "Final Chorus", "Outro"]
PRESERVE_ORIGINAL_MUSIC_DIRECTION = True


def _text(value: Any, default: str = "") -> str:
    return str(value or default).strip()


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
    explicit_genre = _text(genre)
    genre_fusion = explicit_genre or _text(style.get("genre")) or _text(preset.get("genre") or preset.get("category"), "modern Thai pop")
    mood_text = _text(mood, _text(style.get("mood"), _text(preset.get("mood"), "emotional cinematic")))
    stored_profile = preset.get("production_profile") if isinstance(preset.get("production_profile"), dict) else {}
    stored_matches = (
        _text(stored_profile.get("genre")) == genre_fusion
        and _text(stored_profile.get("mood")) == mood_text
        and _text(stored_profile.get("vocal_direction")) == _text(vocal, "natural lead vocal")
    )
    production_profile = dict(stored_profile) if stored_matches else resolve_song_production_profile(
        genre=genre_fusion,
        mood=mood_text,
        vocal=_text(vocal, "natural lead vocal"),
    )
    bpm = int(production_profile["recommended_bpm"])
    palette = list(production_profile["instrument_palette"])
    mood_character = str(production_profile["mood_character"])
    vocal_profile = dict(production_profile["vocal_profile"])
    vocal_tone = str(vocal_profile["style_direction"])
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
        "Intro": f"({palette[1]}, soft rhodes piano, warm ambient pad, {mood_character} atmosphere, intimate space)",
        "Verse 1": f"({palette[0]}, close vocal tone, soft kick/snare groove, restrained bass, detailed emotional storytelling)",
        "Pre-Chorus": "(building tension, rising toms, suspended chords, emotional lift, wider reverb tail)",
        "Chorus": f"(full band energy, catchy pop groove, layered harmony, {palette[-1]}, strong emotional release)",
        "Verse 2": f"(groove returns with more movement, {palette[2]}, subtle counter melody, vocal becomes more urgent)",
        "Bridge": "(cinematic breakdown, emotional piano lead, atmospheric texture, half-time drums, vulnerable vocal space)",
        "Final Chorus": "(big final chorus, stacked harmonies, stronger drums, wide cinematic lift, memorable singalong release)",
        "Outro": f"(emotional fade out, {palette[1]} echoes, ambient reverb tail, soft final vocal adlibs)",
    }
    vocal_energy_map = {
        "Intro": f"{vocal_profile['texture']}, {vocal_profile['intimacy']}",
        "Verse 1": f"{vocal_profile['delivery']}; {vocal_profile['diction']}",
        "Pre-Chorus": f"{vocal_profile['dynamic_behavior']}",
        "Chorus": f"{vocal_profile['chorus_behavior']}",
        "Verse 2": f"retain {vocal_profile['delivery']} with increased emotional intent",
        "Bridge": f"use contrast while preserving {vocal_profile['texture']}",
        "Final Chorus": f"{vocal_profile['chorus_behavior']}; {vocal_profile['harmony_behavior']}",
        "Outro": f"return to {vocal_profile['intimacy']} with a natural release",
    }
    master_prompt = (
        f"{production_profile['style_prompt']} "
        "Start with a focused intro, develop the selected groove through the verses, increase tension in the pre-chorus, "
        "open into a memorable chorus, create contrast in the bridge, then deliver the largest final chorus and a natural outro. "
        "Keep the production coherent, vocal-forward and free from unrelated genre changes."
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
        "production_profile": production_profile,
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


def has_rich_music_direction(text: str, style_prompt: str = "") -> bool:
    source = f"{text or ''}\n{style_prompt or ''}".lower()
    signals = [
        "bpm",
        "vocal",
        "instrument",
        "palette",
        "arrangement",
        "cinematic",
        "full band",
        "layered harmony",
        "emotional",
        "energy curve",
        "ambient",
        "piano",
        "guitar",
        "drums",
    ]
    return sum(1 for signal in signals if signal in source) >= 4


def _split_tag_lines(tag: str) -> list[str]:
    clean = str(tag or "").strip()
    if not clean:
        return []
    return [clean]


def normalize_section_direction_layout(lyrics: str, music_direction: dict[str, Any]) -> str:
    """Place arrangement tags directly below headers and remove mid-lyric duplicate tags."""
    lyrics = sanitize_production_tag_residue(lyrics)
    generated_tags = music_direction.get("section_tags") or {}
    existing_tags: dict[str, str] = {}
    scan_section = ""
    for raw in str(lyrics or "").replace("\r\n", "\n").splitlines():
        line = raw.strip()
        section_match = re.match(r"^\[([^\]]+)\]$", line)
        if section_match:
            scan_section = section_match.group(1).strip()
            continue
        if scan_section and line.startswith("(") and line.endswith(")") and len(line) > 12 and scan_section not in existing_tags:
            existing_tags[scan_section] = line
    tags = {**generated_tags, **existing_tags}
    output: list[str] = []
    current_section = ""
    inserted_for_section = False
    for raw in str(lyrics or "").replace("\r\n", "\n").splitlines():
        line = raw.strip()
        if not line:
            if output and output[-1] != "":
                output.append("")
            continue
        section_match = re.match(r"^\[([^\]]+)\]$", line)
        if section_match:
            current_section = section_match.group(1).strip()
            inserted_for_section = False
            if output and output[-1] != "":
                output.append("")
            output.append(f"[{current_section}]")
            for tag_line in _split_tag_lines(tags.get(current_section, "")):
                output.append(tag_line)
            if tags.get(current_section):
                output.append("")
                inserted_for_section = True
            continue
        is_direction_tag = line.startswith("(") and line.endswith(")")
        if is_direction_tag and current_section:
            if not inserted_for_section:
                output.append(line)
                output.append("")
                inserted_for_section = True
            continue
        output.append(raw.rstrip())
    return "\n".join(output).strip() + "\n"
