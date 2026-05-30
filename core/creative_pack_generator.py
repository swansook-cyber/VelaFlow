from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.file_naming import build_export_filename, ensure_unique_path, sanitize_filename
from core.paths import workflow_project_root
from core.song_title_engine import generate_song_title_candidates, generate_song_title_from_idea, score_song_title_candidate
from core.thai_quality_filter import build_thai_quality_report, clean_thai_output


CREATIVE_PACK_PRESETS: dict[str, dict[str, str]] = {
    "Thai Sad Pop": {
        "mood": "เศร้า ละมุน คิดถึง",
        "style": "cinematic emotional Thai pop, warm piano, soft drums, intimate vocal, memorable chorus",
        "visual": "rainy apartment window, warm shadows, lonely realistic character, premium Thai pop cover",
    },
    "Office Burnout": {
        "mood": "เหนื่อยล้าในออฟฟิศ แต่ยังอยากมีแรงไปต่อ",
        "style": "dark office pop, soft synth pulse, low piano, tired spoken verse, emotional chorus lift",
        "visual": "late night office, monitor glow, empty desk, city lights, cinematic burnout mood",
    },
    "Lonely Night Drive": {
        "mood": "ขับรถกลางคืน เหงา คิดถึงคนเก่า",
        "style": "night drive synth pop, mellow bass, airy pads, emotional male vocal, late-night hook",
        "visual": "car interior at night, blurred city lights, wet windshield, cinematic neon realism",
    },
    "Broken Relationship": {
        "mood": "รักพัง ยังลืมไม่ได้",
        "style": "modern heartbreak ballad, acoustic guitar, emotional strings, layered chorus harmony",
        "visual": "quiet bedroom after breakup, soft morning light, empty side of bed, realistic emotion",
    },
    "TikTok Emotional Hook": {
        "mood": "ฮุกสั้น จำง่าย เจ็บเร็ว",
        "style": "TikTok emotional hook, instant chorus intro, strong vocal phrase, punchy modern pop drums",
        "visual": "close-up emotional face, vertical cinematic frame, strong first-second visual hook",
    },
    "Indie Acoustic": {
        "mood": "อบอุ่น จริงใจ เหงาแบบเรียบง่าย",
        "style": "indie acoustic pop, fingerpicked guitar, soft vocal, organic room tone, gentle chorus",
        "visual": "small room with guitar, natural window light, film grain, cozy indie album cover",
    },
    "Dark Podcast Intro": {
        "mood": "ดาร์ก ออฟฟิศ เหนื่อยกับชีวิตเมือง",
        "style": "dark podcast intro music, low pulse, cinematic drone, intimate narration bed",
        "visual": "dark desk setup, microphone silhouette, city night, dramatic office storytelling",
    },
    "Vela Moon Emotional Pop Rock": {
        "mood": "Vela Moon signature comfort, emotional Thai male vocal, warm but powerful",
        "style": "Thai male vocal, emotional modern Thai pop rock arrangement, acoustic guitar-led intro, clean electric guitar melodic hook, soft piano emotional layer, warm cinematic pad, smooth bass, mid-tempo drum kit around 85 BPM, intimate verse vocal, restrained pre-chorus build, wide emotional chorus lift, vulnerable bridge breakdown, bigger final chorus with layered harmony, warm Spotify-ready mix, clear vocal focus, radio-friendly Thai pop rock, TikTok-ready emotional hook.",
        "visual": "warm rehearsal room, acoustic guitar, clean electric guitar, soft piano corner, comforting cinematic light, Vela Moon signature pop rock mood",
        "hook_direction": "comforting emotional hook, singable first line, dynamic chorus lift, easy to remember on TikTok",
        "lyrics_direction": "relatable Thai emotional lyrics with a warm male vocal perspective, honest pain, and a hopeful release in the final chorus",
        "caption_direction": "Spotify-friendly Thai pop rock release with a short emotional TikTok hook",
    },
    "Vela Moon Late Night Drive": {
        "mood": "lonely night drive, nostalgic, emotional but not too sad",
        "style": "Thai male vocal, atmospheric Thai pop rock arrangement, smooth electric guitar lead, subtle acoustic rhythm, soft piano shadows, cinematic pad, rounded bass, restrained 82 BPM drum kit, reflective verse, gradual pre-chorus lift, open night-drive chorus, spacious bridge, warmer final chorus, warm late-night Spotify-ready mix, clear vocal center, cinematic road-trip width.",
        "visual": "late night car interior, soft dashboard glow, wet street reflections, warm vocal mood, cinematic Thai night-drive palette",
        "hook_direction": "night-drive hook with a nostalgic melody and a phrase listeners can hum after one play",
        "lyrics_direction": "lyrics about driving through the city at night, missing someone quietly, and finding calm instead of collapse",
        "caption_direction": "for late-night listeners, lonely drives, and emotional playlist saves",
    },
    "Vela Moon Heartbroken Anthem": {
        "mood": "heartbroken anthem, slow build, dramatic emotional release",
        "style": "Thai emotional male vocal, modern Thai pop rock ballad arrangement, acoustic guitar foundation, electric guitar layers, emotional piano, warm strings and cinematic pad, smooth bass, 78 BPM slow-build drum kit, vulnerable verse, rising pre-chorus tension, powerful chorus, stripped bridge, dramatic expanded final chorus, layered harmony, warm radio-ready ballad mix, vocal-forward, wide emotional chorus.",
        "visual": "empty bedroom after heartbreak, guitar by the bed, dramatic warm shadows, cinematic final chorus energy, modern Thai pop rock ballad cover",
        "hook_direction": "anthemic heartbreak chorus, repeatable title phrase, bigger final chorus, emotional singalong",
        "lyrics_direction": "a broken relationship story that starts vulnerable, builds through regret, and explodes into a powerful final chorus",
        "caption_direction": "big heartbreak chorus for people who still cannot let go",
    },
    "Vela Moon Easy Listening Pop Rock": {
        "mood": "commercial easy listening, clean, catchy, mainstream",
        "style": "Thai male vocal, commercial Thai easy listening pop rock arrangement, acoustic guitar groove, clean electric guitar counter-melody, soft piano support, smooth bass, subtle pad warmth, tight 88 BPM radio-friendly drum kit, relaxed verse, natural pre-chorus lift, catchy chorus, concise bridge, bright polished final chorus, clean Spotify-ready mix balance, clear vocal focus, mainstream radio feel.",
        "visual": "clean daylight studio, acoustic guitar and soft piano, friendly mainstream Spotify cover, warm easy listening mood",
        "hook_direction": "simple catchy hook with natural Thai phrasing, radio-friendly melody, easy to sing",
        "lyrics_direction": "clear mainstream Thai lyrics, simple emotional images, positive forward motion, and a clean chorus",
        "caption_direction": "easy listening Thai pop rock for daily playlists and repeat listening",
    },
    "Vela Moon Office Life Story": {
        "mood": "Thai working-life storytelling, office burnout, relatable but hopeful",
        "style": "Warm Thai male vocal, Thai working-life storytelling pop rock arrangement, acoustic guitar pulse, clean electric guitar emotional fills, soft piano, smooth bass, warm pad, steady 84 BPM pop rock drums, conversational verse, lifting pre-chorus, relatable chorus, reflective bridge, hopeful final chorus, warmer and wider each repeat, warm Spotify-ready mix, clear vocal storytelling, polished Thai pop rock comfort.",
        "visual": "late office desk, city window, tired worker with warm hope, acoustic guitar mood, cinematic working-life Thai pop rock cover",
        "hook_direction": "relatable office-life hook, burnout emotion, warm hopeful final line, TikTok caption-ready",
        "lyrics_direction": "Thai working-life story about being tired at the desk, feeling unseen, and recovering hope in the final chorus",
        "caption_direction": "for office workers who are tired but still trying",
    },
}


RELEASE_PACK_FILES = {
    "song_info.txt": "SONG INFO",
    "lyrics_only.txt": "SUNO LYRICS FIELD",
    "suno_style_prompt.txt": "SUNO STYLE OF MUSIC FIELD",
    "producer_notes.txt": "PRODUCER NOTES",
    "advanced_suno_settings.txt": "Advanced Suno Settings",
    "cover_prompt.txt": "Cover prompt",
    "mv_storyboard_prompt.txt": "MV storyboard prompt",
    "shorts_tiktok_ideas.txt": "Shorts/TikTok ideas",
    "caption.txt": "Caption",
    "hashtags.txt": "Hashtags",
    "youtube_description.txt": "YouTube description",
    "release_notes.txt": "Release notes",
}


DEFAULT_ADVANCED_SUNO_SETTINGS = {
    "BPM": "85",
    "Weirdness": "20%",
    "Style Influence": "70%",
    "Vocal Style Notes": "Thai emotional vocal, warm expressive tone, clear pronunciation",
    "Arrangement Notes": "acoustic guitar intro, soft piano support, clean chorus lift, smooth fade outro",
    "Commercial Direction": "Suno/Udio-ready emotional Thai pop, clean structure, memorable chorus",
}


ADVANCED_SUNO_SETTINGS_BY_PRESET = {
    "Vela Moon Emotional Pop Rock": {
        "BPM": "85",
        "Weirdness": "20%",
        "Style Influence": "70%",
        "Vocal Style Notes": "Thai emotional male vocal, warm expressive tone, clear pronunciation",
        "Arrangement Notes": "acoustic guitar intro, clean electric guitar hook accents, soft piano support, gentle cymbal swells, wide dynamic chorus, emotional final chorus, smooth fade outro",
        "Commercial Direction": "Spotify-friendly Thai pop rock, TikTok-ready emotional hook, radio-friendly structure",
    },
    "Vela Moon Late Night Drive": {
        "BPM": "82",
        "Weirdness": "25%",
        "Style Influence": "68%",
        "Vocal Style Notes": "Thai warm male vocal, intimate late-night delivery, soft emotional phrasing",
        "Arrangement Notes": "quiet intro, smooth electric guitar lead, nostalgic melody, cinematic pad, restrained drums, open chorus, soft night-drive outro",
        "Commercial Direction": "playlist-friendly Thai pop rock for late-night listening, emotional but not too sad",
    },
    "Vela Moon Heartbroken Anthem": {
        "BPM": "78",
        "Weirdness": "22%",
        "Style Influence": "72%",
        "Vocal Style Notes": "Thai emotional male vocal, vulnerable verse tone, powerful chorus release",
        "Arrangement Notes": "sparse intro, slow pre-chorus build, acoustic guitar, electric guitar layers, emotional piano, warm strings, dramatic expanded final chorus",
        "Commercial Direction": "modern Thai pop rock ballad with a big singalong heartbreak chorus",
    },
    "Vela Moon Easy Listening Pop Rock": {
        "BPM": "88",
        "Weirdness": "18%",
        "Style Influence": "75%",
        "Vocal Style Notes": "Thai clean male vocal, easy listening phrasing, friendly commercial tone",
        "Arrangement Notes": "clean intro, acoustic guitar groove, clean electric guitar counter-melody, soft piano, radio-friendly drums, short bridge, polished final chorus",
        "Commercial Direction": "mainstream Spotify Thai easy listening pop rock with a simple catchy hook",
    },
    "Vela Moon Office Life Story": {
        "BPM": "84",
        "Weirdness": "20%",
        "Style Influence": "70%",
        "Vocal Style Notes": "Thai warm male vocal, conversational storytelling, hopeful final chorus",
        "Arrangement Notes": "quiet office-like intro, acoustic guitar pulse, clean electric guitar emotional fills, soft piano, steady drums, warm pad, hopeful final chorus",
        "Commercial Direction": "relatable Thai working-life pop rock for office listeners and emotional short clips",
    },
}


INTERNAL_LYRIC_PHRASES = [
    "hook direction",
    "mood:",
    "lyrics direction:",
    "comforting emotional hook",
    "spotify-friendly",
    "tiktok-ready",
    "tiktok hook friendly",
    "dynamic chorus lift",
    "easy to remember on tiktok",
    "ให้ท่อนนี้",
    "ท่อนนี้ควร",
    "ร้องให้สุด",
    "producer prompt",
    "music style prompt",
]

REUSED_BREAKUP_MEMORY_LINES = [
    "ฉันเดินผ่านที่เดิม",
    "ทุกข้อความเก่า",
    "ถ้าความทรงจำมีประตูให้ปิด",
    "เสียงเมืองยังดัง",
    "หัวใจก็ยังจำว่าเคยรัก",
    "ปล่อยให้ชื่อเธอค่อย ๆ จางไป",
    "แม้เธอไม่อยู่ตรงนี้แล้ว",
]


def _lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _concept_theme(idea: str) -> str:
    text = str(idea or "").lower()
    if any(word in text for word in ["ความจริง", "พูด", "ตรง ๆ", "ตรงๆ", "ไม่แรง", "วิธีพูด", "คำพูด", "สื่อสาร", "คุยกัน", "ฟังกัน"]):
        return "respectful_truth"
    if any(word in text for word in ["เลิก", "แฟนเก่า", "ลืม", "ไม่กลับมา", "ความทรงจำ", "คิดถึง", "อกหัก", "breakup", "memory"]):
        return "breakup_memory"
    return "general_emotional"


def _is_breakup_memory_concept(idea: str) -> bool:
    return _concept_theme(idea) == "breakup_memory"


def _advanced_settings_for_preset(preset_name: str) -> dict[str, str]:
    settings = dict(DEFAULT_ADVANCED_SUNO_SETTINGS)
    settings.update(ADVANCED_SUNO_SETTINGS_BY_PRESET.get(preset_name, {}))
    return settings


def _advanced_settings_to_text(settings: dict[str, str]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in settings.items())


def _producer_profile_for_preset(preset_name: str, preset: dict[str, str], settings: dict[str, str]) -> dict[str, str]:
    fallback = {
        "core_genre": preset.get("style", "modern Thai pop, emotional commercial structure"),
        "vocal_direction": settings.get("Vocal Style Notes", "clear emotional Thai vocal, intimate verse, open chorus release"),
        "instrumentation": "soft piano, warm acoustic guitar, smooth bass, cinematic pad, clean pop drums",
        "arrangement_progression": "Intro starts intimate, verse stays close, pre-chorus builds tension, chorus opens wider, bridge drops down, final chorus returns bigger, outro fades naturally",
        "drum_bass": "restrained verse groove, controlled kick and snare, bass follows vocal emotion, stronger chorus pocket",
        "layers": "acoustic guitar foundation, piano emotional support, warm pad glue, subtle melodic counter lines",
        "chorus_lift": "memorable chorus with wider drums, stronger harmony, emotional release, and clear title phrase",
        "bridge": "cinematic breakdown with reduced drums, exposed vocal, piano lead, and emotional space",
        "final_chorus": "largest dynamic section with layered harmonies, wider guitars, stronger drums, and a satisfying final hook payoff",
        "mix_master": "warm Spotify-ready mix, clear vocal focus, controlled low end, soft reverb tail, radio-friendly loudness",
        "reference": settings.get("Commercial Direction", "commercial Thai pop release, Suno/Udio-ready, playlist-friendly"),
    }
    profiles = {
        "Vela Moon Emotional Pop Rock": {
            "core_genre": "Thai emotional pop rock, Vela Moon signature warmth, commercial Spotify-friendly structure, TikTok-ready emotional hook",
            "vocal_direction": "Thai male vocal, warm expressive tone, close-mic intimate verse, restrained pre-chorus lift, open emotional chorus, clear pronunciation",
            "instrumentation": "fingerpicked acoustic guitar, felt piano, clean electric guitar melodic fills, warm cinematic pad, smooth live bass, mid-tempo pop rock drum kit",
            "arrangement_progression": "Intro: fingerpicked acoustic guitar + felt piano. Verse: intimate close-mic vocal over restrained guitar. Pre-Chorus: build tension with toms and pads. Chorus: full drum kit and layered guitars. Bridge: half-time emotional breakdown. Final Chorus: largest dynamic section with layered harmonies and electric guitar counter melody. Outro: natural acoustic fade.",
            "drum_bass": "85 BPM pocket, soft kick in verse, rising toms into pre-chorus, full snare and cymbal lift in chorus, smooth bass supporting vocal emotion",
            "layers": "acoustic guitar intro, clean electric guitar hook accents, soft piano emotional layer, warm pad behind chorus, gentle cymbal swells",
            "chorus_lift": "wide dynamic chorus lift with full band energy, layered harmony, electric guitar accents, strong emotional release, singable title phrase",
            "bridge": "half-time breakdown, emotional piano lead, reduced drums, vulnerable vocal space, warm pad atmosphere",
            "final_chorus": "biggest final chorus, stacked harmonies, stronger drums, electric guitar counter melody, final hook payoff, smooth fade outro",
            "mix_master": "warm Spotify-ready mix, vocal-forward, clear midrange, controlled bass, radio-friendly Thai pop rock loudness",
            "reference": "modern Thai pop rock ballad energy, Vela Moon signature comfort, playlist-friendly and emotional short-form ready",
        },
        "Vela Moon Late Night Drive": {
            "core_genre": "atmospheric Thai pop rock, lonely night-drive mood, nostalgic but not too sad",
            "vocal_direction": "warm Thai male vocal, intimate late-night delivery, reflective verse, open chorus with calm emotional release",
            "instrumentation": "smooth electric guitar lead, subtle acoustic rhythm, soft piano shadows, cinematic pad, rounded bass, restrained drums",
            "arrangement_progression": "Intro: soft dashboard-like pad and guitar. Verse: close vocal with sparse rhythm. Pre-Chorus: gentle lift. Chorus: open night-drive width. Bridge: spacious reflective pause. Final Chorus: warmer and wider. Outro: soft road-trip fade.",
            "drum_bass": "82 BPM restrained drum kit, rounded bass pulse, soft snare, cymbal shimmer only on emotional lifts",
            "layers": "electric guitar lead phrases, soft piano shadows, low cinematic pad, subtle acoustic movement",
            "chorus_lift": "chorus opens wider like city lights, with bigger vocal harmony and smooth guitar melody",
            "bridge": "spacious bridge with pad, piano, and distant guitar echo",
            "final_chorus": "warmer final chorus, wider stereo guitars, fuller harmony, emotional but controlled release",
            "mix_master": "warm late-night Spotify-ready mix, clear vocal center, cinematic width, smooth low end",
            "reference": "Thai night-drive playlist feel, nostalgic road-trip pop rock, soft cinematic realism",
        },
        "Vela Moon Heartbroken Anthem": {
            "core_genre": "modern Thai pop rock ballad, heartbroken anthem, slow build into dramatic final chorus",
            "vocal_direction": "Thai emotional male vocal, fragile verse tone, rising pre-chorus, powerful chorus release, dramatic final chorus",
            "instrumentation": "acoustic guitar foundation, electric guitar layers, emotional piano, warm strings, cinematic pad, smooth bass, slow-build drums",
            "arrangement_progression": "Intro: sparse guitar and piano. Verse: vulnerable vocal. Pre-Chorus: rising tension. Chorus: powerful full-band release. Bridge: stripped emotional breakdown. Final Chorus: dramatic expanded singalong. Outro: warm reverb tail.",
            "drum_bass": "78 BPM slow-build drum kit, quiet verse pulse, stronger tom/snare lift into chorus, bass widens final chorus",
            "layers": "acoustic guitar bed, electric guitar swells, piano lead, warm string pad, layered harmony in choruses",
            "chorus_lift": "anthemic heartbreak chorus with full band, layered harmony, and repeatable title phrase",
            "bridge": "stripped piano-led breakdown with vulnerable vocal and half-time feel",
            "final_chorus": "dramatic expanded final chorus, stacked harmony, stronger guitars, cymbal lift, emotional peak",
            "mix_master": "warm radio-ready ballad mix, vocal-forward, wide emotional chorus, polished low end",
            "reference": "big Thai heartbreak singalong, modern ballad production, strong final chorus payoff",
        },
        "Vela Moon Easy Listening Pop Rock": {
            "core_genre": "commercial Thai easy listening pop rock, clean mainstream Spotify style, catchy hook",
            "vocal_direction": "clean Thai male vocal, friendly phrasing, relaxed verse, natural chorus lift, polished final chorus",
            "instrumentation": "acoustic guitar groove, clean electric guitar counter-melody, soft piano, smooth bass, subtle pad warmth, radio-friendly drums",
            "arrangement_progression": "Intro: clean acoustic groove. Verse: relaxed vocal and light rhythm. Pre-Chorus: natural lift. Chorus: catchy and open. Bridge: concise reset. Final Chorus: bright polished repeat. Outro: clean ending.",
            "drum_bass": "88 BPM tight pop rock drums, steady bass, light verse groove, polished chorus pocket",
            "layers": "acoustic rhythm guitar, clean electric counter-melody, soft piano support, subtle pad glue",
            "chorus_lift": "catchy chorus with simple melody, wider drums, light harmony, and radio-friendly energy",
            "bridge": "short bridge with reduced drums and melodic guitar answer",
            "final_chorus": "polished final chorus with brighter harmony, fuller guitars, and clean commercial finish",
            "mix_master": "clean Spotify-ready mix balance, vocal clarity, radio feel, controlled brightness",
            "reference": "mainstream Thai easy listening pop rock, daily playlist friendly, commercial hook focus",
        },
        "Vela Moon Office Life Story": {
            "core_genre": "Thai working-life storytelling pop rock, office burnout emotion, relatable but hopeful",
            "vocal_direction": "warm Thai male vocal, conversational verse, tired but sincere delivery, hopeful final chorus",
            "instrumentation": "acoustic guitar pulse, clean electric guitar emotional fills, soft piano, smooth bass, warm pad, steady pop rock drums",
            "arrangement_progression": "Intro: quiet office-like pulse. Verse: conversational storytelling. Pre-Chorus: emotional lift from exhaustion. Chorus: relatable singalong. Bridge: reflective pause. Final Chorus: hopeful and wider. Outro: warm release.",
            "drum_bass": "84 BPM steady pop rock drums, grounded bass, restrained verse groove, hopeful chorus lift",
            "layers": "acoustic pulse, clean electric fills, soft piano, warm pad, subtle cymbal lift",
            "chorus_lift": "relatable chorus with warmer harmony, stronger drums, and a final line that feels hopeful",
            "bridge": "reflective bridge with piano and pad, space for tired vocal honesty",
            "final_chorus": "hopeful final chorus, wider guitars, brighter harmony, warm emotional payoff",
            "mix_master": "warm Spotify-ready mix, clear vocal storytelling, polished Thai pop rock comfort",
            "reference": "office-life Thai pop rock, relatable working adult story, comfort after burnout",
        },
    }
    profile = dict(fallback)
    profile.update(profiles.get(preset_name, {}))
    return profile


def _build_ai_producer_prompt(preset_name: str, preset: dict[str, str], settings: dict[str, str]) -> str:
    profile = _producer_profile_for_preset(preset_name, preset, settings)
    ordered_sections = [
        ("CORE GENRE", profile["core_genre"]),
        ("VOCAL DIRECTION", profile["vocal_direction"]),
        ("INSTRUMENTATION", profile["instrumentation"]),
        ("ARRANGEMENT PROGRESSION", profile["arrangement_progression"]),
        ("DRUM & BASS DIRECTION", profile["drum_bass"]),
        ("GUITAR / PIANO / PAD LAYERS", profile["layers"]),
        ("CHORUS LIFT", profile["chorus_lift"]),
        ("BRIDGE DIRECTION", profile["bridge"]),
        ("FINAL CHORUS CLIMAX", profile["final_chorus"]),
        ("MIX & MASTER FEEL", profile["mix_master"]),
        ("REFERENCE FEEL", profile["reference"]),
    ]
    return "\n\n".join(f"{heading}\n{body}" for heading, body in ordered_sections)


def _build_suno_style_prompt(preset_name: str, preset: dict[str, str], settings: dict[str, str]) -> str:
    profile = _producer_profile_for_preset(preset_name, preset, settings)
    bpm = settings.get("BPM", "85")
    if preset_name == "Vela Moon Emotional Pop Rock":
        return (
            "Thai emotional pop rock, Thai male vocal, warm expressive tone, fingerpicked acoustic guitar and felt piano intro, "
            "intimate close-mic verse vocal, restrained pre-chorus build with toms and pads, full drum kit and layered guitars in chorus, "
            "half-time emotional bridge breakdown, biggest final chorus with stacked harmonies and electric guitar counter melody, warm Spotify-ready mix, "
            f"{bpm} BPM."
        )
    core = profile["core_genre"].split(",")[0].strip()
    vocal = ", ".join(profile["vocal_direction"].split(",")[:3]).strip()
    instrumentation = ", ".join(profile["instrumentation"].split(",")[:5]).strip()
    arrangement = profile["arrangement_progression"]
    arrangement_parts = [part.strip() for part in arrangement.split(".") if part.strip()]
    arrangement = ", ".join(arrangement_parts[:4])
    mix = ", ".join(profile["mix_master"].split(",")[:3]).strip()
    return (
        f"{core}, {vocal}, {instrumentation}, {arrangement}, {mix}, {bpm} BPM."
    )


def _clean_lyric_text(text: str) -> str:
    cleaned: list[str] = []
    for line in str(text or "").splitlines():
        lowered = line.strip().lower()
        if any(phrase in lowered for phrase in INTERNAL_LYRIC_PHRASES):
            continue
        if lowered.startswith("(") and lowered.endswith(")"):
            continue
        cleaned.append(line.rstrip())
    return "\n".join(cleaned).strip()


def remove_meta_lines_from_lyrics(text: str) -> str:
    return _clean_lyric_text(text)


def improve_hook_singability(hook: str) -> str:
    lines = _lines(remove_meta_lines_from_lyrics(hook))
    if len(lines) < 3:
        lines.extend(["ยังดังซ้ำ ๆ ในหัวใจ", "หัวใจก็ยิ่งจำ"])
    return "\n".join(lines[:5])


def polish_commercial_lyrics(text: str, hook: str = "") -> str:
    cleaned = clean_thai_output(remove_meta_lines_from_lyrics(text))
    lines = cleaned.splitlines()
    hook_lines = _lines(improve_hook_singability(hook))
    polished: list[str] = []
    in_final_chorus = False
    final_has_payoff = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[Final Chorus]":
            in_final_chorus = True
            final_has_payoff = False
            polished.append(stripped)
            continue
        if stripped.startswith("[") and stripped.endswith("]") and stripped != "[Final Chorus]":
            if in_final_chorus and not final_has_payoff:
                polished.extend(["แม้เธอไม่อยู่ตรงนี้แล้ว", "หัวใจก็ยังจำว่าเคยรัก"])
            in_final_chorus = False
            polished.append(stripped)
            continue
        if in_final_chorus and any(phrase in stripped for phrase in ["ร้องให้สุด", "ท่อนนี้", "TikTok-ready"]):
            continue
        polished.append(line.rstrip())
    if in_final_chorus and not final_has_payoff:
        polished.extend(["แม้เธอไม่อยู่ตรงนี้แล้ว", "หัวใจก็ยังจำว่าเคยรัก"])
    # Keep first and final chorus related, but give the final chorus an emotional payoff.
    output = "\n".join(polished).strip()
    if hook_lines and "[Final Chorus]" in output:
        output = output.replace("[Final Chorus]\n" + "\n".join(hook_lines), "[Final Chorus]\n" + "\n".join(hook_lines), 1)
    return output


def _performance_intro_tag(preset_name: str, preset: dict[str, str]) -> str:
    settings = _advanced_settings_for_preset(preset_name)
    notes = settings.get("Arrangement Notes") or "acoustic guitar intro, soft piano support, clean chorus lift, smooth fade outro"
    blocked = ["Spotify-friendly", "TikTok-ready", "TikTok hook friendly", "Commercial Direction"]
    for word in blocked:
        notes = notes.replace(word, "").strip(" ,")
    if preset_name.startswith("Vela Moon"):
        return f"soft cinematic intro, {notes}"
    return f"soft cinematic intro, {preset.get('style', 'warm emotional pop')}"


def _seed_title(idea: str, preset_name: str) -> str:
    candidates = generate_song_title_candidates(idea=idea)
    title = candidates[0]["title"] if candidates else generate_song_title_from_idea(idea, "")
    title = str(title or "").strip()
    if title and title.lower() not in {"demo song", "untitled song", "new song"}:
        return title
    words = str(idea or preset_name).replace("\n", " ").split()
    return " ".join(words[:5]) or preset_name


def _score_hook_candidate(hook: str) -> dict[str, Any]:
    lines = _lines(hook)
    joined = " ".join(lines)
    compact_len = len(joined.replace(" ", ""))
    singability = 82 - max(0, compact_len - 54)
    memorability = 74 + (10 if 2 <= len(lines) <= 4 else -12) + (8 if any("ใจ" in line or "เธอ" in line or "รัก" in line for line in lines) else 0)
    emotional = 70 + (10 if any("ใจ" in line or "คืน" in line or "ลืม" in line or "รัก" in line for line in lines) else 0)
    caption = 74 + (10 if lines and len(lines[0].replace(" ", "")) <= 16 else -8)
    penalty = 0
    if compact_len > 78:
        penalty += 28
    if any(word in joined.lower() for word in ["direction", "prompt", "hook friendly", "spotify-friendly", "tiktok"]):
        penalty += 80
    if any(len(line.replace(" ", "")) > 32 for line in lines):
        penalty += 18
    score = int((singability + memorability + emotional + caption) / 4 - penalty)
    return {
        "hook": hook,
        "score": max(0, min(100, score)),
        "singability": max(0, min(100, singability)),
        "memorability": max(0, min(100, memorability)),
        "emotional_punch": max(0, min(100, emotional)),
        "caption_potential": max(0, min(100, caption)),
    }


def _hook_candidates(title: str, idea: str) -> list[str]:
    idea_text = str(idea or "")
    if _concept_theme(idea_text) == "respectful_truth":
        return [
            "\n".join(["พูดความจริงเบา ๆ", "ให้ใจเรายังจับมือกัน", "ไม่ต้องชนะด้วยคำแรง", "แค่ฟังกันให้มากพอ"]),
            "\n".join(["ความจริงยังสำคัญ", "แต่วิธีพูดก็สำคัญไม่แพ้กัน", "ถ้ารักยังอยากซ่อมใจ", "อย่าใช้คำไหนทำร้ายเรา"]),
            "\n".join(["บอกตรง ๆ ได้ไหม", "แต่ขอให้ใจยังอ่อนโยน", "คำจริงไม่ต้องเป็นค้อน", "ก็ทำให้เราเข้าใจกัน"]),
            "\n".join(["อย่าพูดให้แพ้ชนะ", "พูดให้เรากลับมาใกล้กัน", "ความจริงจะไม่เจ็บเกินไป", "ถ้าใจยังเลือกถนอมน้ำคำ"]),
            "\n".join(["ถ้าใจยังรัก", "พูดกันดี ๆ ได้ไหม", "ให้ความจริงเป็นสะพาน", "ไม่ใช่กำแพงกลางใจ"]),
        ]
    if "รัก" in idea_text and not any(word in idea_text for word in ["อกหัก", "เลิก", "ลืม"]):
        return [
            "\n".join([title, "ถ้าใจยังเลือกเธออยู่", "ฉันจะเรียกมันว่ารักได้ไหม"]),
            "\n".join(["รักที่ไม่พูดไป", "ยังดังอยู่ในใจ", "ทุกครั้งที่เจอเธอ"]),
            "\n".join(["เก็บรักไว้ในใจ", "ไม่กล้าบอกให้เธอรู้", "กลัวเสียเธอไป"]),
            "\n".join(["คืนที่ยังรัก", "ฉันยังเปิดเพลงเดิม", "ให้ใจมันคิดถึงเธอ"]),
            "\n".join(["คำว่ารักยังอยู่", "แม้ปากไม่เคยพูดไป", "แต่ใจจำเธอเสมอ"]),
        ]
    return [
        "\n".join([title, "ยังดังซ้ำ ๆ ในหัวใจ", "ยิ่งหนีไกล ยิ่งกลับไปคิดถึง"]),
        "\n".join(["คืนที่ไม่มีเธอ", "ยังยาวเกินจะผ่านไป", "ใจยังเรียกชื่อเดิม"]),
        "\n".join(["ถ้าลืมง่ายเหมือนพูดลา", "ฉันคงไม่เจ็บถึงวันนี้", "คงไม่ร้องเพลงนี้ซ้ำ ๆ"]),
        "\n".join(["ยังเก็บเธอไว้ในเพลง", "ทุกคำยังเหมือนวันเก่า", "ทุกเสียงยังพาใจกลับไป"]),
        "\n".join(["พอได้แล้วใจ", "อย่ารอคนที่ไม่กลับมา", "แต่ทำไมยังรักอยู่"]),
    ]


def _select_best_hook(title: str, idea: str) -> dict[str, Any]:
    scored = sorted([_score_hook_candidate(clean_thai_output(candidate)) for candidate in _hook_candidates(title, idea)], key=lambda item: item["score"], reverse=True)
    return scored[0] if scored else _score_hook_candidate(title)


def _hook_from_idea(idea: str, title: str, preset: dict[str, str]) -> str:
    hook_direction = str(preset.get("hook_direction") or "").strip()
    if hook_direction:
        return _select_best_hook(title, idea)["hook"]
    return _select_best_hook(title, idea)["hook"]
    lowered = str(idea or "").strip()
    if "ออฟฟิศ" in lowered or "office" in lowered.lower():
        return "\n".join(["ทำไมใจยังติดอยู่ที่โต๊ะเดิม", "ทั้งที่ไฟในตึกดับไปนานแล้ว", "ฉันแค่เหนื่อย หรือฉันไม่เหลือใคร"])
    if "แฟน" in lowered or "เลิก" in lowered or "relationship" in lowered.lower():
        return "\n".join(["ลืมเธอไม่ได้สักที", "แม้รู้ว่าเธอไม่กลับมา", "ใจยังเรียกชื่อเดิมทุกคืน"])
    if "drive" in lowered.lower() or "ขับรถ" in lowered:
        return "\n".join(["ถนนคืนนี้ยาวเกินไป", "ไฟเมืองยังพาใจกลับไปหาเธอ", "ยิ่งขับไกล ยิ่งลืมไม่ลง"])
    return "\n".join([title, "ท่อนนี้ต้องจำได้ตั้งแต่ครั้งแรก", f"อารมณ์หลัก: {preset['mood']}"])


def _respectful_truth_lyrics(title: str, hook: str) -> str:
    hook_block = "\n".join(_lines(hook))
    return "\n".join(
        [
            "[Intro]",
            "คืนนี้เรานั่งเงียบกันนานกว่าทุกที",
            "เหมือนมีคำหนึ่งคำรอให้พูดออกมา",
            "",
            "[Verse 1]",
            "ฉันไม่ได้กลัวความจริงที่เธอเก็บไว้",
            "แค่กลัวน้ำเสียงทำให้ใจเราห่างกัน",
            "ถ้าต้องบอกอะไรที่เจ็บให้กันฟัง",
            "ขอให้ยังมีมือหนึ่งคอยประคอง",
            "",
            "[Pre-Chorus]",
            "คำตรง ๆ ไม่จำเป็นต้องเป็นมีด",
            "ถ้าพูดด้วยใจที่ยังอยากรักษาเรา",
            "",
            "[Chorus]",
            hook_block,
            "",
            "[Verse 2]",
            "ฉันก็มีส่วนผิดที่เงียบจนเกินไป",
            "เธอก็เหนื่อยใช่ไหมที่ต้องเดาใจฉัน",
            "ลองวางคำแข็ง ๆ ลงข้างความสัมพันธ์",
            "แล้วพูดกันเหมือนคนที่ยังแคร์",
            "",
            "[Pre-Chorus]",
            "ความจริงจะพาเราไปทางไหนก็ได้",
            "แต่คำอ่อนโยนจะพาเราไม่หลงทาง",
            "",
            "[Chorus]",
            hook_block,
            "",
            "[Bridge]",
            "ถ้าคืนนี้ต้องร้องไห้ก็ไม่เป็นไร",
            "ขอแค่เราไม่ใช้คำพูดทำลายกัน",
            "ให้ความจริงเป็นไฟที่ส่องทาง",
            "ไม่ใช่ไฟที่เผาทุกอย่างจนหายไป",
            "",
            "[Final Chorus]",
            hook_block,
            "พูดให้ใจยังมีที่ให้กลับมา",
            "ให้ความจริงซ่อมเรา ไม่ใช่แยกเราไกล",
            "",
            "[Outro]",
            "ถ้ายังรักกันอยู่",
            "พูดกันเบา ๆ ก็พอ",
        ]
    )


def _lyrics(title: str, hook: str, idea: str, preset_name: str, preset: dict[str, str]) -> str:
    if _concept_theme(idea) == "respectful_truth":
        return _respectful_truth_lyrics(title, hook)
    hook_lines = _lines(hook)
    hook_block = "\n".join(hook_lines)
    return "\n".join(
        [
            "[Intro]",
            f"({_performance_intro_tag(preset_name, preset)})",
            f"คืนหนึ่งที่ใจยังไม่ยอมพักจากเรื่อง {idea}",
            "",
            "[Verse 1]",
            "ฉันเดินผ่านที่เดิมเหมือนไม่มีอะไรเปลี่ยน",
            "แต่ข้างในกลับเงียบจนได้ยินเสียงใจ",
            "ทุกข้อความเก่าเหมือนแสงที่ยังไม่ดับไป",
            "ยิ่งพยายามลืมเท่าไร ยิ่งชัดขึ้นมา",
            "",
            "[Pre-Chorus]",
            "ถ้าความทรงจำมีประตูให้ปิด",
            "ฉันคงไม่ติดอยู่ตรงนี้ซ้ำ ๆ",
            "",
            "[Chorus]",
            hook_block,
            "ให้ท่อนนี้วนอยู่ในใจคนฟัง",
            "",
            "[Verse 2]",
            "เสียงเมืองยังดัง แต่ฉันกลับได้ยินแค่เธอ",
            "ทุกความเงียบทำให้คำลาเหมือนเพิ่งเกิดเมื่อวาน",
            "ฉันไม่รู้ว่าควรปล่อย หรือควรรอให้นาน",
            "เพราะหัวใจยังจำว่าเคยรักแค่ไหน",
            "",
            "[Bridge]",
            "ถ้าวันหนึ่งฉันยอมวางทุกอย่างลง",
            "ขอให้เพลงนี้เป็นคำสุดท้ายที่ยังอ่อนโยน",
            "",
            "[Final Chorus]",
            hook_block,
            "คราวนี้ร้องให้สุด เหมือนคืนสุดท้ายที่ยังคิดถึง",
            "",
            "[Outro]",
            "(emotional fade out, warm reverb tail, soft vocal ad-lib)",
            "ปล่อยให้ชื่อเธอค่อย ๆ จางไปกับเพลงนี้",
        ]
    )


def validate_concept_alignment(idea: str, lyrics: str) -> dict[str, Any]:
    theme = _concept_theme(idea)
    text = str(lyrics or "")
    reused_lines = [line for line in REUSED_BREAKUP_MEMORY_LINES if line in text]
    if theme == "respectful_truth":
        required_terms = ["ความจริง", "พูด", "คำ", "อ่อนโยน", "ฟัง", "รักษา", "ซ่อม"]
        matched_terms = [term for term in required_terms if term in text]
        return {
            "theme": theme,
            "aligned": len(matched_terms) >= 4 and not reused_lines,
            "matched_terms": matched_terms,
            "reused_breakup_memory_lines": reused_lines,
            "reason": "lyrics focus on respectful truth and soft communication" if len(matched_terms) >= 4 and not reused_lines else "lyrics do not support the current communication concept strongly enough",
        }
    return {
        "theme": theme,
        "aligned": _is_breakup_memory_concept(idea) or not reused_lines,
        "matched_terms": [],
        "reused_breakup_memory_lines": reused_lines,
        "reason": "breakup/memory lines allowed for this concept" if _is_breakup_memory_concept(idea) else "no forbidden reused breakup-memory lines detected",
    }


def _remove_disallowed_reused_lines(idea: str, lyrics: str) -> str:
    if _is_breakup_memory_concept(idea):
        return lyrics
    output: list[str] = []
    for line in str(lyrics or "").splitlines():
        if any(stale in line for stale in REUSED_BREAKUP_MEMORY_LINES):
            continue
        output.append(line)
    return "\n".join(output).strip()


def generate_creative_release_pack(
    idea: str,
    preset_name: str = "Thai Sad Pop",
    artist_name: str = "Vela Moon",
) -> dict[str, Any]:
    preset = CREATIVE_PACK_PRESETS.get(preset_name, CREATIVE_PACK_PRESETS["Thai Sad Pop"])
    concept = str(idea or "").strip() or preset["mood"]
    title = _seed_title(concept, preset_name)
    hook = _hook_from_idea(concept, title, preset)
    hook = improve_hook_singability(hook)
    lyrics = polish_commercial_lyrics(_lyrics(title, hook, concept, preset_name, preset), hook)
    lyrics = _remove_disallowed_reused_lines(concept, lyrics)
    concept_alignment = validate_concept_alignment(concept, lyrics)
    if not concept_alignment["aligned"] and _concept_theme(concept) == "respectful_truth":
        hook = improve_hook_singability(_select_best_hook(title, concept)["hook"])
        lyrics = polish_commercial_lyrics(_respectful_truth_lyrics(title, hook), hook)
        lyrics = _remove_disallowed_reused_lines(concept, lyrics)
        concept_alignment = validate_concept_alignment(concept, lyrics)
    advanced_settings = _advanced_settings_for_preset(preset_name)
    advanced_settings_text = _advanced_settings_to_text(advanced_settings)
    ai_producer_prompt = _build_ai_producer_prompt(preset_name, preset, advanced_settings)
    lyrics_only = _clean_lyric_text(lyrics)
    suno_style_prompt = _build_suno_style_prompt(preset_name, preset, advanced_settings)
    generated_at = datetime.now().isoformat(timespec="seconds")
    song_info = "\n".join(
        [
            f"Preset: {preset_name}",
            f"Generated: {generated_at}",
            f"Suggested Title: {title}",
            "Hook:",
            hook,
            "Song Concept:",
            f"{concept}\nMood: {preset['mood']}\nLyrics direction: {preset.get('lyrics_direction', 'clear emotional progression')}\nHook direction: {preset.get('hook_direction', 'memorable emotional hook')}",
        ]
    )
    hashtags = ["#เพลงไทย", "#เพลงเศร้า", "#ThaiPop", "#VelaFlow", "#TikTokMusic", "#SunoAI", "#เพลงใหม่"]
    if preset_name.startswith("Vela Moon"):
        hashtags.extend(["#VelaMoon", "#ThaiPopRock", "#SpotifyThailand"])
    caption_direction = str(preset.get("caption_direction") or "เน€เธเธฅเธเธเธตเนเธชเธณเธซเธฃเธฑเธเธเธเธ—เธตเนเธขเธฑเธเธขเธดเนเธกเนเธ”เน เนเธ•เนเธเนเธฒเธเนเธเธขเธฑเธเนเธกเนเธซเธฒเธขเธ”เธต")
    pack = {
        "SONG INFO": song_info,
        "Song concept": f"{concept}\nPreset: {preset_name}\nMood: {preset['mood']}\nLyrics direction: {preset.get('lyrics_direction', 'clear emotional progression')}\nHook direction: {preset.get('hook_direction', 'memorable emotional hook')}",
        "Suggested title": title,
        "Hook": hook,
        "SUNO LYRICS FIELD": lyrics_only,
        "Full lyrics": lyrics,
        "SUNO STYLE OF MUSIC FIELD": suno_style_prompt,
        "AI PRODUCER PROMPT": ai_producer_prompt,
        "AI Producer Prompt": ai_producer_prompt,
        "PRODUCER NOTES": ai_producer_prompt,
        "Music style prompt for Suno/Udio": ai_producer_prompt,
        "Advanced Suno Settings": advanced_settings_text,
        "Cover prompt": f"premium cover artwork for '{title}', {preset['visual']}, cinematic realism, no watermark",
        "MV storyboard prompt": (
            f"Vertical 9:16 emotional MV storyboard for '{title}'. Scene 1: wide atmosphere. "
            "Scene 2: medium emotional action. Scene 3: close-up hook moment. Scene 4: soft release ending. "
            f"Keep continuity: {preset['visual']}. Hook direction: {preset.get('hook_direction', 'emotional hook moment')}."
        ),
        "Shorts/TikTok ideas": "\n".join(
            [
                "1. เปิดด้วยท่อนฮุกที่เจ็บที่สุดใน 2 วินาทีแรก",
                "2. ทำ lyric visualizer แนว cinematic vertical",
                "3. ใช้ฉาก close-up อารมณ์กับ caption สั้น",
                "4. ตัด 15s hook สำหรับ Reels/Shorts",
            ]
        ),
        "Caption": f"{_lines(hook)[0] if _lines(hook) else title}\n\nเพลงนี้สำหรับคนที่ยังยิ้มได้ แต่ข้างในยังไม่หายดี",
        "Hashtags": " ".join(hashtags),
        "YouTube description": (
            f"{title} - {artist_name}\n\n"
            f"เพลงใหม่จาก VelaFlow concept: {concept}\n"
            "อารมณ์เพลงเน้นฮุกจำง่าย เนื้อหาเล่าเรื่องชัด และพร้อมนำไปต่อยอดใน Suno/Udio, Whisk, Flow, Veo, Runway หรือ Kling.\n\n"
            + " ".join(hashtags[:5])
        ),
        "Release notes": "\n".join(
            [
                "Release Pack generated locally by VelaFlow V1.",
                "No video rendering, lip sync, cloud render, or encoding was used.",
                "Review lyrics and prompts before publishing.",
                f"Created at: {datetime.now().isoformat(timespec='seconds')}",
            ]
        ),
    }
    if preset_name.startswith("Vela Moon"):
        pack["Caption"] = f"{_lines(hook)[0] if _lines(hook) else title}\n\n{caption_direction}"
    title_score = score_song_title_candidate(title, concept)
    hook_score = _score_hook_candidate(hook)
    return {
        "ok": True,
        "preset": preset_name,
        "artist_name": artist_name,
        "pack": pack,
        "quality_report": {
            "selected_title_score": title_score,
            "selected_hook_score": hook_score,
            "thai_quality": build_thai_quality_report(lyrics),
            "producer_review": {
                "title_approved": title_score.get("score", 0) >= 60,
                "hook_approved": hook_score.get("score", 0) >= 60,
                "caption_ready": hook_score.get("caption_potential", 0) >= 60,
            },
            "concept_alignment": concept_alignment,
        },
        "generated_at": generated_at,
    }


def creative_release_pack_to_text(result: dict[str, Any]) -> str:
    pack = result.get("pack") or {}
    title = str(pack.get("Suggested title", "")).strip()
    hook = str(pack.get("Hook", "")).strip()
    concept = str(pack.get("Song concept", "")).strip()
    song_info = "\n".join(
        [
            "1. SONG INFO",
            f"Preset: {result.get('preset', '')}",
            f"Generated: {result.get('generated_at', '')}",
            f"Suggested Title: {title}",
            "Hook:",
            hook,
            "Song Concept:",
            concept,
        ]
    )
    sections = [
        "VELAFLOW AI CREATIVE RELEASE PACK",
        song_info,
        "2. SUNO LYRICS FIELD\n" + str(pack.get("SUNO LYRICS FIELD") or _clean_lyric_text(pack.get("Full lyrics", ""))).strip(),
        "3. SUNO STYLE OF MUSIC FIELD\n" + str(pack.get("SUNO STYLE OF MUSIC FIELD", "")).strip(),
        "4. PRODUCER NOTES\n" + str(pack.get("PRODUCER NOTES") or pack.get("AI PRODUCER PROMPT", "")).strip(),
        "5. ADVANCED SUNO SETTINGS\n" + str(pack.get("Advanced Suno Settings", "")).strip(),
        "6. COVER PROMPT\n" + str(pack.get("Cover prompt", "")).strip(),
        "7. MV STORYBOARD PROMPT\n" + str(pack.get("MV storyboard prompt", "")).strip(),
        "8. SHORTS / TIKTOK IDEAS\n" + str(pack.get("Shorts/TikTok ideas", "")).strip(),
        "9. CAPTION\n" + str(pack.get("Caption", "")).strip(),
        "10. HASHTAGS\n" + str(pack.get("Hashtags", "")).strip(),
        "11. YOUTUBE DESCRIPTION\n" + str(pack.get("YouTube description", "")).strip(),
        "12. RELEASE NOTES\n" + str(pack.get("Release notes", "")).strip(),
    ]
    return "\n\n".join(sections).strip() + "\n"


def export_creative_release_pack(
    project_name: str,
    result: dict[str, Any],
    artist_name: str = "Vela Moon",
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    try:
        pack = result.get("pack") or {}
        title = str(pack.get("Suggested title") or project_name or "VelaFlow Release")
        root = Path(base_dir) if base_dir else workflow_project_root("song") / sanitize_filename(project_name or title)
        export_dir = root / "exports" / "release_pack"
        export_dir.mkdir(parents=True, exist_ok=True)
        written: dict[str, str] = {}
        for filename, label in RELEASE_PACK_FILES.items():
            path = export_dir / filename
            path.write_text(str(pack.get(label, "")).strip() + "\n", encoding="utf-8-sig")
            written[filename] = str(path)
        release_pack_path = export_dir / "release_pack.txt"
        release_pack_path.write_text(creative_release_pack_to_text(result), encoding="utf-8-sig")
        written["release_pack.txt"] = str(release_pack_path)
        txt_path = ensure_unique_path(export_dir / build_export_filename(title, artist_name, "Release_Pack", "txt"))
        txt_path.write_text(creative_release_pack_to_text(result), encoding="utf-8-sig")
        manifest = {
            "package_type": "ai_creative_release_pack",
            "render_features_used": False,
            "project_name": project_name,
            "song_title": title,
            "preset": result.get("preset"),
            "generated_files": written,
            "txt_export": str(txt_path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        manifest_path = export_dir / "release_pack_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        zip_path = ensure_unique_path(export_dir / build_export_filename(title, artist_name, "Release_Pack", "zip"))
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in [Path(item) for item in written.values()] + [txt_path, manifest_path]:
                archive.write(path, path.name)
        return {
            "ok": True,
            "data": {
                "export_dir": str(export_dir),
                "txt_path": str(txt_path),
                "zip_path": str(zip_path),
                "manifest_path": str(manifest_path),
                "files": written,
            },
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "data": {}, "error": str(exc)}
