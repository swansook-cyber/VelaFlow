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
        "style": "Core Genre: Thai emotional pop rock, Spotify-friendly modern Thai radio feel. Vocal Direction: Thai male vocal, warm expressive tone, clear pronunciation, intimate verse vocal and emotional final chorus. Instrumentation: acoustic guitar-led arrangement, clean electric guitar melodic fills, soft piano support, warm cinematic pad. Arrangement Progression: acoustic intro, intimate verse, restrained pre-chorus build, wide dynamic chorus lift, bridge opens space, emotional final chorus. Drum/Bass Direction: smooth bass, mid-tempo drum kit around 85 BPM, gentle cymbal swells, steady pop rock groove. Guitar/Piano/Pad Layers: acoustic guitar pulse, electric guitar hook accents, soft piano emotional support, warm pad glue. Chorus Lift: wide singable hook with layered harmony and stronger emotional release. Bridge / Final Chorus Direction: vulnerable bridge breakdown into bigger final chorus. Mix & Master Feel: warm Spotify-ready mix, clear vocal focus, modern Thai pop rock radio feel.",
        "visual": "warm rehearsal room, acoustic guitar, clean electric guitar, soft piano corner, comforting cinematic light, Vela Moon signature pop rock mood",
        "hook_direction": "comforting emotional hook, singable first line, dynamic chorus lift, easy to remember on TikTok",
        "lyrics_direction": "relatable Thai emotional lyrics with a warm male vocal perspective, honest pain, and a hopeful release in the final chorus",
        "caption_direction": "Spotify-friendly Thai pop rock release with a short emotional TikTok hook",
    },
    "Vela Moon Late Night Drive": {
        "mood": "lonely night drive, nostalgic, emotional but not too sad",
        "style": "Core Genre: atmospheric Thai pop rock with lonely night-drive emotion. Vocal Direction: warm Thai male vocal, relaxed intimate phrasing, nostalgic but controlled emotion. Instrumentation: smooth electric guitar lead, acoustic guitar texture, soft piano shadows, cinematic pad, rounded bass. Arrangement Progression: quiet intro, reflective verse, gradual pre-chorus lift, open chorus, bridge with spacious night atmosphere, soft final chorus release. Drum/Bass Direction: 82 BPM restrained drum kit, soft kick, light snare, smooth bass movement. Guitar/Piano/Pad Layers: clean electric guitar melodies, subtle acoustic rhythm, piano color notes, wide pad ambience. Chorus Lift: emotional but not too sad, memorable night-drive melody. Bridge / Final Chorus Direction: half-time emotional space before a warmer final chorus. Mix & Master Feel: warm late-night Spotify-ready mix, clear vocal center, cinematic road-trip width.",
        "visual": "late night car interior, soft dashboard glow, wet street reflections, warm vocal mood, cinematic Thai night-drive palette",
        "hook_direction": "night-drive hook with a nostalgic melody and a phrase listeners can hum after one play",
        "lyrics_direction": "lyrics about driving through the city at night, missing someone quietly, and finding calm instead of collapse",
        "caption_direction": "for late-night listeners, lonely drives, and emotional playlist saves",
    },
    "Vela Moon Heartbroken Anthem": {
        "mood": "heartbroken anthem, slow build, dramatic emotional release",
        "style": "Core Genre: modern Thai pop rock ballad with anthem-sized heartbreak. Vocal Direction: emotional Thai male vocal, vulnerable verse tone, rising pre-chorus tension, powerful chorus delivery. Instrumentation: acoustic guitar foundation, electric guitar layers, emotional piano, warm strings and cinematic pad, supportive bass. Arrangement Progression: sparse intro, intimate verse, slow pre-chorus build, powerful chorus, stripped bridge, dramatic expanded final chorus. Drum/Bass Direction: 78 BPM slow-build drum kit, deep kick, restrained verse percussion, bigger chorus crashes, smooth bass support. Guitar/Piano/Pad Layers: acoustic guitar pulse, electric guitar swells, piano lead emotions, warm string pad underneath. Chorus Lift: big singalong hook with layered harmony and strong emotional release. Bridge / Final Chorus Direction: cinematic breakdown into the most dramatic final chorus. Mix & Master Feel: warm radio-ready ballad mix, vocal-forward, wide emotional chorus, streaming-ready loudness.",
        "visual": "empty bedroom after heartbreak, guitar by the bed, dramatic warm shadows, cinematic final chorus energy, modern Thai pop rock ballad cover",
        "hook_direction": "anthemic heartbreak chorus, repeatable title phrase, bigger final chorus, emotional singalong",
        "lyrics_direction": "a broken relationship story that starts vulnerable, builds through regret, and explodes into a powerful final chorus",
        "caption_direction": "big heartbreak chorus for people who still cannot let go",
    },
    "Vela Moon Easy Listening Pop Rock": {
        "mood": "commercial easy listening, clean, catchy, mainstream",
        "style": "Core Genre: commercial Thai easy listening pop rock, clean mainstream Spotify style. Vocal Direction: Thai male vocal, friendly clear tone, relaxed verse, bright chorus confidence. Instrumentation: acoustic guitar groove, clean electric guitar, soft piano, smooth bass, light pad texture. Arrangement Progression: clean intro, simple verse, natural pre-chorus lift, catchy chorus, short bridge, polished final chorus. Drum/Bass Direction: 88 BPM radio-friendly drum kit, tight kick/snare, smooth bass pocket, light cymbal movement. Guitar/Piano/Pad Layers: acoustic strum, clean electric counter-melody, soft piano support, subtle pad warmth. Chorus Lift: simple melodic hook, easy to sing, repeat-friendly. Bridge / Final Chorus Direction: concise bridge leading to a brighter final chorus. Mix & Master Feel: clean radio feel, Spotify-ready balance, clear vocal focus, polished mainstream finish.",
        "visual": "clean daylight studio, acoustic guitar and soft piano, friendly mainstream Spotify cover, warm easy listening mood",
        "hook_direction": "simple catchy hook with natural Thai phrasing, radio-friendly melody, easy to sing",
        "lyrics_direction": "clear mainstream Thai lyrics, simple emotional images, positive forward motion, and a clean chorus",
        "caption_direction": "easy listening Thai pop rock for daily playlists and repeat listening",
    },
    "Vela Moon Office Life Story": {
        "mood": "Thai working-life storytelling, office burnout, relatable but hopeful",
        "style": "Core Genre: Thai working-life storytelling pop rock with hopeful emotional release. Vocal Direction: warm Thai male vocal, conversational verse delivery, tired but sincere emotion, hopeful final chorus. Instrumentation: acoustic guitar, clean electric guitar, soft piano, smooth bass, warm pad, steady drum kit. Arrangement Progression: quiet office-like intro, story verse, lifting pre-chorus, relatable chorus, reflective bridge, hopeful final chorus. Drum/Bass Direction: 84 BPM steady pop rock drums, soft verse groove, stronger chorus backbeat, smooth supportive bass. Guitar/Piano/Pad Layers: acoustic guitar pulse, clean electric guitar emotional fills, soft piano for office-night mood, warm pad glue. Chorus Lift: relatable singalong hook for tired workers, warmer and wider each repeat. Bridge / Final Chorus Direction: vulnerable bridge turns into hopeful final chorus. Mix & Master Feel: warm Spotify-ready mix, clear vocal storytelling, polished Thai pop rock comfort.",
        "visual": "late office desk, city window, tired worker with warm hope, acoustic guitar mood, cinematic working-life Thai pop rock cover",
        "hook_direction": "relatable office-life hook, burnout emotion, warm hopeful final line, TikTok caption-ready",
        "lyrics_direction": "Thai working-life story about being tired at the desk, feeling unseen, and recovering hope in the final chorus",
        "caption_direction": "for office workers who are tired but still trying",
    },
}


RELEASE_PACK_FILES = {
    "song_concept.txt": "Song concept",
    "suggested_title.txt": "Suggested title",
    "hook.txt": "Hook",
    "full_lyrics.txt": "Full lyrics",
    "music_style_prompt.txt": "Music style prompt for Suno/Udio",
    "advanced_suno_settings.txt": "Advanced Suno Settings",
    "suno_copy_ready_block.txt": "Suno Copy-Ready Block",
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
    "tiktok hook friendly",
    "dynamic chorus lift",
    "easy to remember on tiktok",
]


def _lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _advanced_settings_for_preset(preset_name: str) -> dict[str, str]:
    settings = dict(DEFAULT_ADVANCED_SUNO_SETTINGS)
    settings.update(ADVANCED_SUNO_SETTINGS_BY_PRESET.get(preset_name, {}))
    return settings


def _advanced_settings_to_text(settings: dict[str, str]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in settings.items())


def _clean_lyric_text(text: str) -> str:
    cleaned: list[str] = []
    for line in str(text or "").splitlines():
        lowered = line.strip().lower()
        if any(phrase in lowered for phrase in INTERNAL_LYRIC_PHRASES):
            continue
        cleaned.append(line.rstrip())
    return "\n".join(cleaned).strip()


def _suno_copy_ready_block(title: str, lyrics: str, music_style_prompt: str, advanced_settings: dict[str, str]) -> str:
    return "\n\n".join(
        [
            "SONG TITLE\n" + title,
            "LYRICS ONLY\n" + _clean_lyric_text(lyrics),
            "MUSIC STYLE PROMPT\n" + music_style_prompt,
            "ADVANCED SUNO SETTINGS\n" + _advanced_settings_to_text(advanced_settings),
            "NOTES FOR GENERATION\nUse the full lyrics as the song body. Keep the vocal clear, preserve the emotional chorus, and generate 2-3 takes before choosing the strongest commercial version.",
        ]
    )


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


def _lyrics(title: str, hook: str, idea: str, preset_name: str, preset: dict[str, str]) -> str:
    hook_lines = _lines(hook)
    hook_block = "\n".join(hook_lines)
    first_hook = hook_lines[0] if hook_lines else title
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
            first_hook,
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


def generate_creative_release_pack(
    idea: str,
    preset_name: str = "Thai Sad Pop",
    artist_name: str = "Vela Moon",
) -> dict[str, Any]:
    preset = CREATIVE_PACK_PRESETS.get(preset_name, CREATIVE_PACK_PRESETS["Thai Sad Pop"])
    concept = str(idea or "").strip() or preset["mood"]
    title = _seed_title(concept, preset_name)
    hook = _hook_from_idea(concept, title, preset)
    lyrics = clean_thai_output(_clean_lyric_text(_lyrics(title, hook, concept, preset_name, preset)))
    advanced_settings = _advanced_settings_for_preset(preset_name)
    advanced_settings_text = _advanced_settings_to_text(advanced_settings)
    suno_copy_ready_block = _suno_copy_ready_block(title, lyrics, preset["style"], advanced_settings)
    hashtags = ["#เพลงไทย", "#เพลงเศร้า", "#ThaiPop", "#VelaFlow", "#TikTokMusic", "#SunoAI", "#เพลงใหม่"]
    if preset_name.startswith("Vela Moon"):
        hashtags.extend(["#VelaMoon", "#ThaiPopRock", "#SpotifyThailand"])
    caption_direction = str(preset.get("caption_direction") or "เน€เธเธฅเธเธเธตเนเธชเธณเธซเธฃเธฑเธเธเธเธ—เธตเนเธขเธฑเธเธขเธดเนเธกเนเธ”เน เนเธ•เนเธเนเธฒเธเนเธเธขเธฑเธเนเธกเนเธซเธฒเธขเธ”เธต")
    pack = {
        "Song concept": f"{concept}\nPreset: {preset_name}\nMood: {preset['mood']}\nLyrics direction: {preset.get('lyrics_direction', 'clear emotional progression')}\nHook direction: {preset.get('hook_direction', 'memorable emotional hook')}",
        "Suggested title": title,
        "Hook": hook,
        "Full lyrics": lyrics,
        "Music style prompt for Suno/Udio": preset["style"],
        "Advanced Suno Settings": advanced_settings_text,
        "Suno Copy-Ready Block": suno_copy_ready_block,
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
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def creative_release_pack_to_text(result: dict[str, Any]) -> str:
    pack = result.get("pack") or {}
    return "\n\n".join(
        [
            "VELAFLOW AI CREATIVE RELEASE PACK",
            f"Preset: {result.get('preset', '')}",
            f"Generated: {result.get('generated_at', '')}",
            *[f"====================\n{label}\n====================\n{pack.get(label, '')}" for label in RELEASE_PACK_FILES.values()],
        ]
    )


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
