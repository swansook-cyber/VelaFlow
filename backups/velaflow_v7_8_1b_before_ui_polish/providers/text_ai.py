import json
import re
from typing import Any, Dict
import google.generativeai as genai

from core.artist_presets import get_artist_preset
from core.instrument_tag_normalizer import normalize_lyrics_tags, validate_english_only_tags
from providers.provider_manager import generate_text


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip().replace("```json", "```").replace("```JSON", "```")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("AI response ไม่มี JSON ที่อ่านได้")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON จาก AI อ่านไม่ได้: {e}")


def _model(api_key: str, model_name: str):
    if not api_key:
        raise ValueError("ยังไม่ได้ใส่ GEMINI_API_KEY ในไฟล์ .env")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name or "gemini-2.5-flash")


def _default_instrument_tags(artist_preset: Dict[str, Any] | None = None) -> Dict[str, str]:
    preset_tags = (artist_preset or {}).get("section_instrument_tags")
    if isinstance(preset_tags, dict) and preset_tags:
        return dict(preset_tags)
    return {
        "Intro": "warm acoustic guitar fingerpicking, soft ambient pad, intimate atmosphere",
        "Verse 1": "acoustic guitar strumming, warm bass, intimate male vocal",
        "Pre-Chorus": "building tom drums, emotional electric guitar swells",
        "Chorus": "full pop rock arrangement, powerful drums, wide stereo guitars, emotional vocal delivery",
        "Post-Chorus": "wide synth pad, melodic guitar hook, airy backing vocals",
        "Verse 2": "steady groove, warm bass, subtle percussion, intimate vocal",
        "Bridge": "music drops down, intimate piano and bass, emotional tension",
        "Final Chorus": "maximum emotional energy, layered backing vocals, soaring electric guitars",
        "Outro": "soft piano tail, fading guitar ambience, warm room texture",
    }


def _default_energy_curve() -> Dict[str, int]:
    return {
        "Intro": 25,
        "Verse 1": 35,
        "Pre-Chorus": 60,
        "Chorus": 88,
        "Post-Chorus": 78,
        "Verse 2": 42,
        "Bridge": 50,
        "Final Chorus": 98,
        "Outro": 20,
    }


def _normalize_song(data: Dict[str, Any], artist_preset: Dict[str, Any] | None = None, force_english_instrument_tags: bool = True) -> Dict[str, Any]:
    artist_preset = artist_preset or get_artist_preset("vela_moon")
    data.setdefault("title", "")
    data.setdefault("target_analysis", "")
    data.setdefault("candidate_hooks", [])
    data.setdefault("selected_hook", "")
    data.setdefault("instrument_selection", {})
    if not data.get("music_style_prompt"):
        data["music_style_prompt"] = artist_preset.get("default_music_style_prompt", "")
    if not data.get("advanced_settings"):
        data["advanced_settings"] = artist_preset.get("suno_advanced_settings") or {"weirdness": "35%", "style_influence": "70%", "reason": ""}
    data.setdefault("complete_lyrics", "")
    data.setdefault("tiktok_clip_cut_recommendation", [])
    data.setdefault("instrument_tags", _default_instrument_tags(artist_preset))
    data.setdefault("energy_curve", _default_energy_curve())
    data.setdefault("arrangement_preset", "")
    data["artist_preset"] = artist_preset.get("artist_id", "vela_moon")
    data["artist_preset_name"] = artist_preset.get("artist_name", "Vela Moon")
    data["instrument_tags_language"] = "English only"
    data["original_song_output"] = data.get("original_song_output") or data.get("complete_lyrics", "")
    if force_english_instrument_tags:
        normalized = normalize_lyrics_tags(data.get("complete_lyrics", ""), artist_preset)
        data["normalized_song_output"] = normalized
        data["complete_lyrics"] = normalized
        data["instrument_tag_validation"] = validate_english_only_tags(normalized)
    return data


def _normalize_mv(data: Dict[str, Any]) -> Dict[str, Any]:
    data.setdefault("song_mood", "")
    data.setdefault("visual_style", "")
    data.setdefault("color_palette", [])
    data.setdefault("story_concept", "")
    data.setdefault("director_notes", "")
    data.setdefault("character_lock", {})
    data.setdefault("storyboard", [])
    data.setdefault("cover_prompts", {})
    data.setdefault("promo_clips", [])
    data.setdefault("captions", {})
    for i, item in enumerate(data.get("storyboard", []) or [], start=1):
        item.setdefault("scene", i)
        item.setdefault("time_range", "")
        item.setdefault("lyric_part", "")
        item.setdefault("emotion", "")
        item.setdefault("scene_visual", item.get("visual_description", ""))
        item.setdefault("visual_description", "")
        item.setdefault("duration_seconds", 8)
        item.setdefault("pacing_note", "")
        item.setdefault("camera", item.get("camera_motion", ""))
        item.setdefault("camera_motion", "")
        item.setdefault("lighting", "")
        item.setdefault("transition", "")
        item.setdefault("subtitle_style", "")
        item.setdefault("prompt_core", item.get("image_prompt", ""))
        item.setdefault("expanded_prompt", item.get("image_prompt", ""))
        item.setdefault("image_prompt", "")
        item.setdefault("video_prompt", "")
        item.setdefault("negative_prompt", "bad anatomy, deformed hands, extra fingers, blurry face, inconsistent character, low quality, watermark, text artifacts")
    return data


def _offline_song(idea: str, genre: str, mood: str, vocal: str, viral_level: str, artist_preset: Dict[str, Any] | None = None) -> str:
    artist_preset = artist_preset or get_artist_preset("vela_moon")
    tags = _default_instrument_tags(artist_preset)
    return json.dumps({
        "title": "Demo Song",
        "target_analysis": f"Offline draft for {idea}",
        "hook_type": "emotional direct hook",
        "candidate_hooks": [
            {"name": "Hook A", "text": "ยังคิดถึงเธอทุกคืน"},
            {"name": "Hook B", "text": "ฝนตกในใจฉัน"},
            {"name": "Hook C", "text": "กลับมาได้ไหม"},
        ],
        "selected_hook": "ยังคิดถึงเธอทุกคืน",
        "selected_hook_reason": "Simple, repeatable, emotional.",
        "instrument_selection": {
            "main_instruments": artist_preset.get("main_instruments", ["clean electric guitar", "acoustic guitar strumming"]),
            "supporting_instruments": artist_preset.get("supporting_instruments", ["light rhodes piano", "soft synth pad"]),
            "atmosphere_texture_elements": artist_preset.get("atmosphere_elements", ["relaxed emotional atmosphere"]),
            "reason": f"Fits {genre}, {mood}, {vocal}, {viral_level}.",
        },
        "music_style_prompt": artist_preset.get("default_music_style_prompt") or f"{genre}, {mood}, {vocal}, emotional Thai pop ballad, full-length arrangement",
        "advanced_settings": artist_preset.get("suno_advanced_settings") or {"weirdness": "30%", "style_influence": "70%", "reason": "Offline safe default."},
        "instrument_tags": tags,
        "complete_lyrics": f"[Intro]\n({tags.get('Intro', 'acoustic guitar strumming, soft ambient pad')})\n\n[Verse 1]\nคืนที่เงียบงัน ฉันยังคิดถึงเธอ\n\n[Chorus]\n({tags.get('Chorus', 'full band arrangement, emotional vocal delivery')})\nยังคิดถึงเธอทุกคืน แม้ไม่มีทางย้อนมา",
        "tiktok_clip_cut_recommendation": [{"rank": 1, "section": "Chorus", "lyric_excerpt": "ยังคิดถึงเธอทุกคืน", "reason": "Hook is direct.", "clip_type": "emotional hook"}],
        "thai_quality_check": "offline fallback draft",
    }, ensure_ascii=False)

def _offline_mv(title: str, artist: str, lyrics: str, style: str, scene_count: int, character_note: str) -> str:
    lines = [line.strip() for line in (lyrics or "").splitlines() if line.strip()]
    if not lines:
        lines = ["instrumental intro", "main hook", "bridge", "final chorus"]
    visuals = [
        "Thai male singer standing alone in heavy rain outside a convenience store at midnight",
        "dark bedroom with blue TV light reflecting on the singer's face",
        "lonely walk across a bridge at night with city lights behind",
        "wide cinematic rooftop shot during golden hour after the rain",
    ]
    storyboard = []
    for index in range(max(4, min(scene_count, 12))):
        visual = visuals[index % len(visuals)]
        lyric = lines[index % len(lines)]
        duration = 6 if index in {1, 2} else 10
        prompt = (
            f"{visual}, {character_note}, {style}, emotional atmosphere, 35mm film look, "
            "shallow depth of field, cinematic composition, ultra realistic"
        )
        storyboard.append({
            "scene": index + 1,
            "time_range": f"00:{index * duration:02d}-00:{(index + 1) * duration:02d}",
            "duration_seconds": duration,
            "pacing_note": "fast hook cut" if duration <= 6 else "slow emotional pacing",
            "lyric_part": lyric,
            "emotion": "lonely, reflective",
            "scene_visual": visual,
            "visual_description": visual,
            "camera": "slow dolly in",
            "camera_motion": "slow dolly in",
            "lighting": "cinematic dark with neon blue highlights",
            "transition": "blur dissolve",
            "subtitle_style": "small white Thai subtitle, bottom center",
            "prompt_core": f"{visual}, {character_note}",
            "expanded_prompt": prompt,
            "image_prompt": prompt,
            "video_prompt": f"{prompt}, slow cinematic camera movement, subtle subject motion, rain atmosphere",
            "negative_prompt": "bad anatomy, extra fingers, deformed face, low quality, blurry, duplicate character, watermark, text artifacts",
        })
    return json.dumps({
        "song_mood": "sad cinematic",
        "visual_style": style,
        "color_palette": ["neon blue", "wet asphalt black", "warm amber"],
        "story_concept": f"Offline simplified MV plan for {title} by {artist}.",
        "director_notes": "Generated locally because the AI provider was unavailable.",
        "character_lock": {
            "main_character": character_note,
            "outfit": "dark hoodie or simple black outfit",
            "hair": "short black hair",
            "face_style": "natural Thai features, emotional eyes",
            "key_props": ["rain", "phone", "street light"],
            "consistency_rule": "Keep the same person, outfit, mood, and lighting continuity in every scene.",
        },
        "storyboard": storyboard,
        "cover_prompts": {
            "spotify_1x1": f"{storyboard[0]['image_prompt']}, square album cover",
            "youtube_thumbnail_16x9": f"{storyboard[0]['image_prompt']}, cinematic YouTube thumbnail",
            "tiktok_cover_9x16": f"{storyboard[0]['image_prompt']}, vertical TikTok cover",
        },
        "promo_clips": [{"platform": "TikTok/Reels/Shorts", "duration": "15s", "hook_idea": "Use the chorus line with rain scene.", "caption_angle": "miss-you emotional hook", "recommended_scenes": [1, 2]}],
        "captions": {
            "youtube_title_options": [title, f"{title} - {artist}", f"{title} | Official MV"],
            "youtube_description": "Offline fallback description. Review before posting.",
            "tiktok_caption": "ยังคิดถึงอยู่ไหม #เพลงเศร้า #เพลงไทย",
            "facebook_caption": "เพลงเศร้าสำหรับคืนที่ยังคิดถึงใครบางคน",
            "pinned_comment": "ท่อนนี้ทำให้นึกถึงใคร?",
            "hashtags": ["#VelaFlow", "#เพลงเศร้า", "#ThaiPop"],
        },
    }, ensure_ascii=False)


def generate_song_with_gemini(
    api_key: str,
    model_name: str,
    idea: str,
    genre: str,
    mood: str,
    vocal: str,
    viral_level: str,
    language: str = "thai",
    artist_preset: Dict[str, Any] | None = None,
    music_style_override: str = "",
    force_english_instrument_tags: bool = True,
) -> Dict[str, Any]:
    artist_preset = artist_preset or get_artist_preset("vela_moon")
    style_prompt = music_style_override.strip() or artist_preset.get("default_music_style_prompt", "")
    preset_json = json.dumps(artist_preset, ensure_ascii=False, indent=2)
    prompt = f"""
คุณคือผู้เชี่ยวชาญด้านการแต่งเพลงและโปรดิวเซอร์ดนตรีสำหรับ Suno Custom Mode
หน้าที่คือเปลี่ยนไอเดียให้เป็นเพลงไทยเต็ม 3-4 นาที ฟังติดหู มีฮุกจำง่าย พร้อม Music Style Prompt ภาษาอังกฤษ

INPUT:
- Song idea/theme: {idea}
- Genre: {genre}
- Mood: {mood}
- Vocal: {vocal}
- Viral level: {viral_level}
- Language: {language}
- Artist Preset: {artist_preset.get('artist_name', 'Vela Moon')}
- Default Music Style Prompt: {style_prompt}

ARTIST PRESET JSON:
{preset_json}

กติกา:
1) ชื่อเพลงไทยสั้น 2-4 พยางค์
2) Music Style Prompt ต้องเป็นภาษาอังกฤษเท่านั้น
3) เนื้อเพลงใช้ Suno tags: [Intro], [Verse 1], [Pre-Chorus], [Chorus], [Post-Chorus], [Verse 2], [Bridge], [Final Chorus], [Outro]
4) เพลงต้องเป็น full-length 3-5 minute arrangement ไม่ใช่เพลงสั้น
5) Candidate Hooks อย่างน้อย 3 แบบ แล้วเลือก 1 แบบดีที่สุด
6) เลือกเครื่องดนตรีแบบ Main / Supporting / Atmosphere ให้เข้ากับ genre + mood ห้ามยัดแน่นเกิน
7) ตรวจภาษาไทยให้เป็นธรรมชาติ เหมือนคนไทยพูดจริง ฮุกต้องร้องง่าย
8) แนะนำ TikTok clip cut 1-3 ท่อน

IMPORTANT LANGUAGE RULE:
- Lyrics must be Thai.
- Music Style Prompt must be English only.
- All instrument tags, arrangement notes, production notes, vocal notes, mood notes, and text inside parentheses must be English only.
- Do not write Thai inside parentheses.
- Do not translate Thai lyrics into English.
- Keep Thai lyrics natural and conversational.
- Use the selected Artist Preset as the main style identity.

Vela Moon style rule:
- Use mid-tempo easy-listening Thai pop rock.
- Smooth emotional male vocal.
- Clean electric guitar and acoustic strumming.
- Warm bass and soft drum kit.
- Light rhodes piano or soft pad when needed.
- Catchy melody, relaxed but emotional.
- Full song structure, not short demo.
- Hook should be memorable and caption-friendly.
- Use section_instrument_tags from the artist preset for Suno arrangement parentheses unless you create better English-only tags.

ตอบเป็น JSON เท่านั้นตาม schema นี้:
{{
  "title": "",
  "target_analysis": "",
  "hook_type": "",
  "candidate_hooks": [{{"name":"Hook A","text":""}}, {{"name":"Hook B","text":""}}, {{"name":"Hook C","text":""}}],
  "selected_hook": "",
  "selected_hook_reason": "",
  "instrument_selection": {{
    "main_instruments": [""],
    "supporting_instruments": [""],
    "atmosphere_texture_elements": [""],
    "reason": ""
  }},
  "music_style_prompt": "English only Suno style prompt with genre, instrumentation, BPM, vocal type, mood, production texture, full-length arrangement direction",
  "advanced_settings": {{"weirdness":"", "style_influence":"", "reason":""}},
  "complete_lyrics": "",
  "tiktok_clip_cut_recommendation": [
    {{"rank":1, "section":"", "lyric_excerpt":"", "reason":"", "clip_type":""}}
  ],
  "thai_quality_check": "ผ่านการตรวจคำไทย/ความลื่น/ฮุก/ความเป็นธรรมชาติแล้ว"
}}
"""
    text = generate_text(
        provider="gemini",
        api_key=api_key,
        prompt=prompt,
        primary_model=model_name,
        offline_factory=lambda: _offline_song(idea, genre, mood, vocal, viral_level, artist_preset),
    )
    song = _extract_json(text)
    song["music_style_prompt"] = song.get("music_style_prompt") or style_prompt
    return _normalize_song(song, artist_preset, force_english_instrument_tags)


def analyze_song_with_gemini(api_key: str, model_name: str, title: str, artist: str, lyrics: str, style: str, quality: str, image_ai: str = "manual", video_ai: str = "manual", scene_count: int = 10, character_note: str = "", language: str = "thai") -> Dict[str, Any]:
    scene_count = max(4, min(int(scene_count or 10), 32))
    character_note = character_note.strip() or "No fixed character yet. Keep visual continuity using consistent age, outfit, hair, mood, and lighting."
    prompt = f"""
คุณคือ AI Director + Music Video Producer + Social Media Strategist สำหรับศิลปิน {artist}
สร้างแผนผลิต MV และโปรโมทเพลงแบบมืออาชีพ ตอบเป็น JSON เท่านั้น ห้ามมีคำอธิบายนอก JSON

ข้อมูลโปรเจกต์:
- ชื่อเพลง: {title}
- ศิลปิน: {artist}
- แนวภาพ: {style}
- Quality Mode: {quality}
- Image AI ที่คาดว่าจะใช้: {image_ai}
- Video AI ที่คาดว่าจะใช้: {video_ai}
- จำนวนฉากที่ต้องการ: {scene_count}
- Character / Continuity Note: {character_note}
- ภาษาหลักของ Caption: {language}

เนื้อเพลง:
{lyrics}

กฎ V6:
1) storyboard ต้องมีประมาณ {scene_count} ฉาก และควรครอบคลุมทั้งเพลง
2) แต่ละฉากต้องต่างกันจริง ทั้ง visual, emotion, camera, lighting, action, transition
3) image_prompt และ video_prompt ต้องเป็นภาษาอังกฤษ ละเอียด พร้อมใช้กับ AI
4) ต้องรักษา character consistency ตาม Character Note
5) ต้องมี camera_motion, lighting, transition, subtitle_style ทุกฉาก
6) negative_prompt ทุกฉากต้องกันภาพเพี้ยน/หน้าตัวละครเปลี่ยน/มือเพี้ยน/watermark/text artifacts
7) Caption เป็นภาษาไทย เหมาะกับ YouTube/TikTok/Facebook
8) ไม่มี Auto Upload ให้คิดเฉพาะไฟล์/คำโปรโมทสำหรับตรวจเอง

ตอบเป็น JSON schema นี้เท่านั้น:
{{
  "song_mood": "",
  "visual_style": "",
  "color_palette": ["", "", ""],
  "story_concept": "",
  "director_notes": "",
  "character_lock": {{"main_character":"", "outfit":"", "hair":"", "face_style":"", "key_props":[""], "consistency_rule":""}},
  "storyboard": [
    {{
      "scene": 1,
      "time_range": "00:00-00:10",
      "duration_seconds": 10,
      "pacing_note": "slow emotional intro / fast hook cut / bridge breathing room",
      "lyric_part": "",
      "emotion": "",
      "scene_visual": "lonely Thai male singer standing in heavy rain outside a convenience store at midnight",
      "visual_description": "",
      "camera": "close-up / handheld / slow dolly in / wide cinematic shot / top-down emotional shot",
      "camera_motion": "",
      "lighting": "",
      "transition": "",
      "subtitle_style": "",
      "prompt_core": "short scene prompt",
      "expanded_prompt": "expanded cinematic prompt with subject, location, lighting, camera, lens, mood, composition, realism, continuity",
      "image_prompt": "English cinematic image prompt with same character, lens, lighting, mood, composition, aspect ratio guidance",
      "video_prompt": "English image-to-video prompt with camera movement, subject movement, atmosphere, duration feeling, cinematic continuity",
      "negative_prompt": "bad anatomy, deformed hands, extra fingers, blurry face, inconsistent character, low quality, watermark, text artifacts"
    }}
  ],
  "cover_prompts": {{"spotify_1x1":"English prompt", "youtube_thumbnail_16x9":"English prompt", "tiktok_cover_9x16":"English prompt"}},
  "promo_clips": [
    {{"platform":"TikTok/Reels/Shorts", "duration":"15s", "hook_idea":"", "caption_angle":"", "recommended_scenes":[1,2]}},
    {{"platform":"YouTube Shorts", "duration":"30s", "hook_idea":"", "caption_angle":"", "recommended_scenes":[1,2,3]}},
    {{"platform":"Facebook", "duration":"60s", "hook_idea":"", "caption_angle":"", "recommended_scenes":[1,2,3,4]}}
  ],
  "captions": {{"youtube_title_options":["", "", "", "", ""], "youtube_description":"", "tiktok_caption":"", "facebook_caption":"", "pinned_comment":"", "hashtags":["", "", ""]}}
}}
"""
    text = generate_text(
        provider="gemini",
        api_key=api_key,
        prompt=prompt,
        primary_model=model_name,
        offline_factory=lambda: _offline_mv(title, artist, lyrics, style, scene_count, character_note),
    )
    return _normalize_mv(_extract_json(text))

