from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.api_quality_gate import build_api_quality_gate, production_blocked_result
from core.file_naming import build_export_filename, ensure_unique_path, sanitize_filename
from core.lyrics_expander import parse_lyric_sections, validate_song_structure
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
    "human_experience_report.txt": "Human Experience Report",
    "emotional_arc_report.txt": "Emotional Arc Report",
    "thai_natural_speech_report.txt": "Thai Natural Speech Report",
    "relatability_report.txt": "Relatability Report",
    "diversity_report.txt": "Diversity Report",
    "situation_specificity_report.txt": "Situation Specificity Report",
    "lyrics_quality_report.txt": "Lyrics Quality Report",
}


DIVERSITY_MEMORY_PATH = Path("data/diversity_memory.json")
DIVERSITY_MEMORY_LIMIT = 20
DIVERSITY_COOLDOWN_PHRASES = [
    "พักใจก่อน",
    "ใจยังไม่เลิกงาน",
    "คืนนี้ขอพัก",
    "นาฬิกาเลิกงาน แต่ใจยังไม่เลิกเหนื่อย",
    "เหนื่อยไหม",
    "ไม่เป็นไรนะ",
    "พรุ่งนี้ค่อยว่ากัน",
    "ถึงบ้านบอกด้วย",
    "มีบางอย่างในใจที่ยังไม่กล้าตอบ",
]
DIVERSITY_UNDERUSED_STORY_TYPES = {
    "Friendship",
    "Family",
    "Parents",
    "Dreams",
    "Life Lessons",
    "Childhood",
    "Rural Life",
    "Self Discovery",
    "Second Chances",
}


def _default_diversity_memory() -> dict[str, list[str]]:
    return {
        "recent_titles": [],
        "recent_hooks": [],
        "recent_opening_lines": [],
        "recent_story_types": [],
        "recent_phrases": [],
        "recent_specific_situations": [],
        "recent_main_objects": [],
        "recent_bridge_truths": [],
        "recent_final_payoff_lines": [],
    }


def load_diversity_memory(path: str | Path = DIVERSITY_MEMORY_PATH) -> dict[str, list[str]]:
    memory_path = Path(path)
    default = _default_diversity_memory()
    try:
        if not memory_path.exists():
            memory_path.parent.mkdir(parents=True, exist_ok=True)
            memory_path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
            return default
        data = json.loads(memory_path.read_text(encoding="utf-8") or "{}")
        if not isinstance(data, dict):
            return default
        out = default.copy()
        for key in default:
            values = data.get(key, [])
            out[key] = [str(item) for item in values[-DIVERSITY_MEMORY_LIMIT:] if str(item).strip()] if isinstance(values, list) else []
        return out
    except Exception:
        return default


def save_diversity_memory(memory: dict[str, list[str]], path: str | Path = DIVERSITY_MEMORY_PATH) -> dict[str, list[str]]:
    clean = _default_diversity_memory()
    for key in clean:
        values = memory.get(key, []) if isinstance(memory, dict) else []
        clean[key] = [str(item) for item in values if str(item).strip()][-DIVERSITY_MEMORY_LIMIT:] if isinstance(values, list) else []
    memory_path = Path(path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    return clean


def _diversity_key(value: str) -> str:
    text = re.sub(r"[\W_]+", "", str(value or "").lower(), flags=re.UNICODE)
    return re.sub(r"\s+", "", text)


def _similarity_ratio(a: str, b: str) -> float:
    a_key = _diversity_key(a)
    b_key = _diversity_key(b)
    if not a_key or not b_key:
        return 0.0
    if a_key == b_key:
        return 1.0
    shorter, longer = sorted([a_key, b_key], key=len)
    if len(shorter) >= 4 and shorter in longer:
        return min(0.95, len(shorter) / max(1, len(longer)) + 0.25)
    a_grams = {a_key[idx: idx + 2] for idx in range(max(1, len(a_key) - 1))}
    b_grams = {b_key[idx: idx + 2] for idx in range(max(1, len(b_key) - 1))}
    if not a_grams or not b_grams:
        return 0.0
    return len(a_grams & b_grams) / max(1, len(a_grams | b_grams))


def _novelty_score(value: str, recent_values: list[str], *, cluster_terms: list[str] | None = None) -> int:
    clean = str(value or "").strip()
    if not clean:
        return 0
    max_similarity = max((_similarity_ratio(clean, recent) for recent in recent_values), default=0.0)
    score = 100 - int(max_similarity * 72)
    compact = _diversity_key(clean)
    for term in cluster_terms or []:
        if _diversity_key(term) and _diversity_key(term) in compact:
            cluster_count = sum(1 for recent in recent_values if _diversity_key(term) in _diversity_key(recent))
            score -= min(30, cluster_count * 8)
    return max(0, min(100, score))


def score_title_novelty(title: str, memory: dict[str, list[str]] | None = None) -> int:
    memory = memory or load_diversity_memory()
    return _novelty_score(title, memory.get("recent_titles", []), cluster_terms=["พัก", "ใจ", "เหนื่อย", "งาน"])


def score_hook_novelty(hook: str, memory: dict[str, list[str]] | None = None) -> int:
    memory = memory or load_diversity_memory()
    lines = _lines(hook)
    opening = lines[0] if lines else hook
    hook_score = _novelty_score(hook, memory.get("recent_hooks", []), cluster_terms=["พัก", "ใจ", "เหนื่อย", "งาน"])
    opening_score = _novelty_score(opening, memory.get("recent_opening_lines", []), cluster_terms=["พัก", "ใจ", "เหนื่อย", "งาน"])
    return int((hook_score * 0.7) + (opening_score * 0.3))


def score_phrase_novelty(text: str, memory: dict[str, list[str]] | None = None) -> int:
    memory = memory or load_diversity_memory()
    recent_phrases = [*memory.get("recent_phrases", []), *DIVERSITY_COOLDOWN_PHRASES]
    lines = _lines(text)
    if not lines:
        return _novelty_score(text, recent_phrases)
    scores = [_novelty_score(line, recent_phrases, cluster_terms=["พัก", "ใจ", "เหนื่อย", "งาน"]) for line in lines]
    return int(sum(scores) / max(1, len(scores)))


def score_story_novelty(story_type: str, memory: dict[str, list[str]] | None = None) -> int:
    memory = memory or load_diversity_memory()
    recent = memory.get("recent_story_types", [])
    score = _novelty_score(story_type, recent)
    if story_type in DIVERSITY_UNDERUSED_STORY_TYPES and story_type not in recent[-8:]:
        score = min(100, score + 12)
    if story_type == "Office Burnout":
        score -= min(35, recent[-10:].count("Office Burnout") * 12)
    return max(0, min(100, score))


def _extract_recent_phrases(title: str, hook: str, lyrics: str) -> list[str]:
    candidates = [title, *_lines(hook), *_lines(lyrics)[:8]]
    seen: set[str] = set()
    out: list[str] = []
    for phrase in candidates:
        clean = str(phrase or "").strip()
        key = _diversity_key(clean)
        if clean and key and key not in seen:
            out.append(clean)
            seen.add(key)
    return out[:10]


def _update_diversity_memory(title: str, hook: str, lyrics: str, story_type: str = "", path: str | Path = DIVERSITY_MEMORY_PATH, situation: dict[str, Any] | None = None) -> dict[str, list[str]]:
    memory = load_diversity_memory(path)
    opening = _lines(hook)[0] if _lines(hook) else ""
    situation = situation or {}
    updates = {
        "recent_titles": [title],
        "recent_hooks": [hook],
        "recent_opening_lines": [opening],
        "recent_story_types": [story_type or "Unknown"],
        "recent_phrases": _extract_recent_phrases(title, hook, lyrics),
        "recent_specific_situations": [str(situation.get("Specific Situation", ""))],
        "recent_main_objects": [str(situation.get("Main Object") or situation.get("Modern Object", ""))],
        "recent_bridge_truths": [str(situation.get("Bridge Truth", ""))],
        "recent_final_payoff_lines": [str(situation.get("Final Payoff", ""))],
    }
    for key, values in updates.items():
        memory[key].extend([str(item) for item in values if str(item).strip()])
        memory[key] = memory[key][-DIVERSITY_MEMORY_LIMIT:]
    return save_diversity_memory(memory, path)


def build_diversity_report(title: str, hook: str, lyrics: str, story_type: str = "", memory: dict[str, list[str]] | None = None) -> dict[str, Any]:
    memory = memory or load_diversity_memory()
    title_score = score_title_novelty(title, memory)
    hook_score = score_hook_novelty(hook, memory)
    story_score = score_story_novelty(story_type, memory)
    vocabulary_score = score_phrase_novelty("\n".join([hook, lyrics]), memory)
    overall = int((title_score * 0.25) + (hook_score * 0.3) + (story_score * 0.2) + (vocabulary_score * 0.25))
    return {
        "Title Novelty Score": title_score,
        "Hook Novelty Score": hook_score,
        "Story Novelty Score": story_score,
        "Vocabulary Novelty Score": vocabulary_score,
        "Overall Diversity Score": max(0, min(100, overall)),
    }


def _diversity_report_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Title Novelty Score: {report.get('Title Novelty Score', 0)}",
            f"Hook Novelty Score: {report.get('Hook Novelty Score', 0)}",
            f"Story Novelty Score: {report.get('Story Novelty Score', 0)}",
            f"Vocabulary Novelty Score: {report.get('Vocabulary Novelty Score', 0)}",
            f"Overall Diversity Score: {report.get('Overall Diversity Score', 0)}",
        ]
    )


SITUATION_ARCHETYPES: list[dict[str, str]] = [
    {
        "trigger": "message_read",
        "Specific Situation": "คนที่อ่านข้อความแล้วไม่ตอบ",
        "Main Character": "คนที่ยังรอคำตอบจากแชตเดิม",
        "Modern Object": "ข้อความที่ขึ้นว่าอ่านแล้ว",
        "Social Context": "ความสัมพันธ์ที่ยังไม่จบในใจ แต่เหมือนอีกฝ่ายเงียบไปแล้ว",
        "Hidden Feeling": "ยังอยากสำคัญพอให้เขาตอบ",
        "Concrete Moment": "เห็นคำว่าอ่านแล้วค้างอยู่ใต้ข้อความสุดท้าย",
        "Escalation Moment": "พิมพ์ประโยคใหม่แล้วลบทิ้ง เพราะรู้ว่าเขาไม่อยากตอบ",
        "Bridge Truth": "ไม่ได้อยากทวงคำตอบ แค่อยากรู้ว่ายังมีความหมายไหม",
        "Final Payoff": "ถ้าเธอเลือกเงียบ ฉันคงต้องเลือกหายเหมือนกัน",
        "Scene Type": "breakup_memory",
        "Main Object": "ข้อความที่อ่านแล้ว",
    },
    {
        "trigger": "online_no_reply",
        "Specific Situation": "เห็นเขาออนไลน์แต่ไม่ตอบเรา",
        "Main Character": "คนที่เผลอมองจุดเขียวข้างชื่อเดิม",
        "Modern Object": "สถานะออนไลน์",
        "Social Context": "คนสองคนยังเห็นกันในหน้าจอ แต่ไม่ได้อยู่ในชีวิตกันเหมือนเดิม",
        "Hidden Feeling": "เจ็บตรงที่เขาว่างพอออนไลน์ แต่ไม่ว่างพอตอบเรา",
        "Concrete Moment": "ชื่อเขาขึ้นว่าออนไลน์อยู่บนหน้าจอเล็ก ๆ",
        "Escalation Moment": "แจ้งเตือนเด้งหลายแอป แต่ไม่มีสักอันที่เป็นชื่อเขา",
        "Bridge Truth": "ไม่ได้แพ้คนใหม่ แพ้ความเงียบของคนเดิม",
        "Final Payoff": "เห็นเธอออนไลน์อีกครั้ง แต่ครั้งนี้ฉันไม่รอแล้ว",
        "Scene Type": "breakup_memory",
        "Main Object": "สถานะออนไลน์",
    },
    {
        "trigger": "work_revision",
        "Specific Situation": "หัวหน้าบอกแก้อีกนิด แต่กลายเป็นทั้งคืน",
        "Main Character": "พนักงานที่บอกตัวเองว่าอีกนิดเดียวมาตั้งแต่หัวค่ำ",
        "Modern Object": "ไฟล์งานที่แก้ไม่จบ",
        "Social Context": "วัฒนธรรมงานที่คำว่าอีกนิดกลายเป็นเวลาส่วนตัวทั้งหมด",
        "Hidden Feeling": "รู้สึกถูกใช้ความอดทนแทนคำขอบคุณ",
        "Concrete Moment": "ไฟห้องทำงานเหลือไม่กี่ดวงตอนเปิดไฟล์เดิมอีกครั้ง",
        "Escalation Moment": "ข้อความแก้อีกนิดเด้งมาตอนคนอื่นเริ่มกลับบ้าน",
        "Bridge Truth": "ไม่ได้ขี้เกียจ แค่อยากมีชีวิตหลังเลิกงานบ้าง",
        "Final Payoff": "งานอาจยังไม่จบ แต่คืนนี้ฉันต้องกลับมาเป็นคนก่อน",
        "Scene Type": "office_life",
        "Main Object": "ไฟล์งานที่แก้ไม่จบ",
    },
    {
        "trigger": "friend_group_silence",
        "Specific Situation": "เพื่อนยังอยู่ในกลุ่มไลน์ แต่ไม่เคยคุยกันแล้ว",
        "Main Character": "คนที่ยังเห็นชื่อเพื่อนเก่าอยู่ในกลุ่มเดิม",
        "Modern Object": "กลุ่มไลน์ที่เงียบไป",
        "Social Context": "มิตรภาพที่ไม่ได้ทะเลาะกัน แต่ค่อย ๆ ห่างจนเหมือนไม่รู้จัก",
        "Hidden Feeling": "คิดถึงโดยไม่รู้จะเริ่มทักยังไง",
        "Concrete Moment": "เลื่อนผ่านกลุ่มไลน์เดิมที่ไม่มีใครพิมพ์อะไรนานแล้ว",
        "Escalation Moment": "วันเกิดเพื่อนผ่านไปพร้อมสติกเกอร์สั้น ๆ แค่ตัวเดียว",
        "Bridge Truth": "เราไม่ได้เสียเพื่อนไปในวันเดียว แค่หายกันไปทีละนิด",
        "Final Payoff": "ถ้ายังคิดถึงกันอยู่ ขอให้สักวันเรากล้าทักก่อน",
        "Scene Type": "friendship",
        "Main Object": "กลุ่มไลน์ที่เงียบไป",
    },
    {
        "trigger": "photo_memory",
        "Specific Situation": "รูปเก่าเด้งขึ้นมาในโทรศัพท์ทุกปี",
        "Main Character": "คนที่โดนความทรงจำแจ้งเตือนโดยไม่ทันตั้งตัว",
        "Modern Object": "รูปเก่าในโทรศัพท์",
        "Social Context": "อดีตที่แพลตฟอร์มจำได้แม้เจ้าของรูปอยากลืม",
        "Hidden Feeling": "รู้ว่าผ่านมาแล้ว แต่ภาพเดิมยังทำให้ใจวูบ",
        "Concrete Moment": "แจ้งเตือนรูปวันนี้เมื่อปีก่อนเด้งขึ้นมาตอนเช้า",
        "Escalation Moment": "นิ้วหยุดอยู่ที่ปุ่มลบ แต่สุดท้ายก็ปิดหน้าจอแทน",
        "Bridge Truth": "ไม่ได้อยากย้อนกลับไป แค่ยังไม่กล้าลบทุกอย่าง",
        "Final Payoff": "รูปยังอยู่ในเครื่อง แต่เธอไม่ต้องอยู่ในทุกวันของฉันแล้ว",
        "Scene Type": "breakup_memory",
        "Main Object": "รูปเก่าในโทรศัพท์",
    },
    {
        "trigger": "home_empty",
        "Specific Situation": "กลับถึงบ้านแล้วไม่มีใครรอ",
        "Main Character": "คนที่เปิดประตูเข้าห้องเงียบ ๆ หลังวันที่ยาวมาก",
        "Modern Object": "กุญแจบ้าน",
        "Social Context": "ชีวิตผู้ใหญ่ที่กลับบ้านได้ แต่ไม่ได้แปลว่ามีที่พักใจ",
        "Hidden Feeling": "อยากมีใครสักคนถามว่าวันนี้ไหวไหม",
        "Concrete Moment": "เสียงกุญแจดังในห้องที่ไม่มีใครเปิดไฟรอ",
        "Escalation Moment": "วางกระเป๋าลงแล้วเพิ่งรู้ว่าทั้งวันไม่มีใครถามถึงเราเลย",
        "Bridge Truth": "ไม่ได้กลัวอยู่คนเดียว แค่บางคืนก็อยากถูกรอ",
        "Final Payoff": "ถ้าไม่มีใครรอ คืนนี้ฉันจะรอตัวเองกลับมา",
        "Scene Type": "loneliness",
        "Main Object": "กุญแจบ้าน",
    },
    {
        "trigger": "salary_empty",
        "Specific Situation": "เงินเดือนออก แต่ใจยังว่างเปล่า",
        "Main Character": "คนที่เห็นยอดเงินเข้า แต่ความเหนื่อยไม่ลดลง",
        "Modern Object": "แจ้งเตือนเงินเดือนเข้า",
        "Social Context": "ชีวิตทำงานที่มีรายรับ แต่ยังขาดความหมายและเวลาพัก",
        "Hidden Feeling": "กลัวว่าตัวเองกำลังแลกชีวิตกับตัวเลข",
        "Concrete Moment": "โทรศัพท์เด้งว่าเงินเข้า ตอนกำลังนั่งกินข้าวคนเดียว",
        "Escalation Moment": "จ่ายบิลเสร็จแล้วความว่างในใจยังอยู่เท่าเดิม",
        "Bridge Truth": "ไม่ได้อยากได้มากกว่านี้ แค่อยากรู้ว่าทำไปเพื่ออะไร",
        "Final Payoff": "ถ้าเงินซื้อคืนชีวิตไม่ได้ ฉันขอเริ่มใช้ชีวิตให้เป็นก่อน",
        "Scene Type": "life_reflection",
        "Main Object": "แจ้งเตือนเงินเดือนเข้า",
    },
    {
        "trigger": "typed_deleted",
        "Specific Situation": "พิมพ์แล้วลบ เพราะรู้ว่าเขาไม่อยากตอบ",
        "Main Character": "คนที่คุยกับช่องแชตว่าง ๆ มากกว่าคุยกับอีกฝ่าย",
        "Modern Object": "ช่องพิมพ์ข้อความ",
        "Social Context": "ความสัมพันธ์ที่เหลือแค่ความลังเลก่อนกดส่ง",
        "Hidden Feeling": "ยังอยากพูด แต่ไม่อยากเป็นภาระของใคร",
        "Concrete Moment": "ประโยคยาว ๆ ถูกลบจนเหลือแค่หน้าจอว่าง",
        "Escalation Moment": "พิมพ์คำว่าไม่เป็นไรแล้วลบ เพราะมันไม่จริงเลย",
        "Bridge Truth": "บางคำไม่ได้ส่ง ไม่ใช่เพราะไม่รู้สึก แต่เพราะรู้คำตอบแล้ว",
        "Final Payoff": "คืนนี้ฉันจะไม่ส่งอะไรไป นอกจากปล่อยเธอออกจากใจ",
        "Scene Type": "breakup_memory",
        "Main Object": "ช่องพิมพ์ข้อความ",
    },
]


def _situation_keyword_score(text: str, archetype: dict[str, str]) -> int:
    haystack = str(text or "").lower()
    situation = str(archetype.get("Specific Situation", "")).lower()
    object_text = str(archetype.get("Modern Object", "")).lower()
    score = 0
    for token in re.split(r"\s+", situation + " " + object_text):
        token = token.strip()
        if len(token) >= 3 and token in haystack:
            score += 10
    trigger_words = {
        "message_read": ["อ่านข้อความ", "อ่านแล้ว", "ไม่ตอบ"],
        "online_no_reply": ["ออนไลน์", "ไม่ตอบ"],
        "work_revision": ["หัวหน้า", "แก้อีกนิด", "ทั้งคืน", "งาน"],
        "friend_group_silence": ["เพื่อน", "กลุ่มไลน์", "ไม่คุย"],
        "photo_memory": ["รูปเก่า", "โทรศัพท์", "ทุกปี"],
        "home_empty": ["กลับถึงบ้าน", "ไม่มีใครรอ", "บ้าน"],
        "salary_empty": ["เงินเดือน", "ว่างเปล่า"],
        "typed_deleted": ["พิมพ์แล้วลบ", "ลบ", "ไม่อยากตอบ"],
    }
    for word in trigger_words.get(str(archetype.get("trigger")), []):
        if word.lower() in haystack:
            score += 35
    return score


def _situation_specificity_score(situation: dict[str, str]) -> int:
    required = [
        "Specific Situation",
        "Main Character",
        "Modern Object",
        "Social Context",
        "Hidden Feeling",
        "Concrete Moment",
        "Escalation Moment",
        "Bridge Truth",
        "Final Payoff",
    ]
    score = 40 + sum(5 for key in required if str(situation.get(key, "")).strip())
    concrete = " ".join(str(situation.get(key, "")) for key in ["Specific Situation", "Modern Object", "Concrete Moment", "Escalation Moment"])
    if any(word in concrete for word in ["ข้อความ", "ออนไลน์", "โทรศัพท์", "กลุ่มไลน์", "ไฟล์", "เงินเดือน", "รูป", "กุญแจ", "แชต"]):
        score += 10
    if any(word in concrete.lower() for word in ["mood", "emotion", "generic", "office burnout"]):
        score -= 20
    return max(0, min(100, score))


def generate_situation_first_seed(concept: str, preset_name: str = "Thai Sad Pop", mood: str = "", story_type: str = "") -> dict[str, str]:
    source = "\n".join([str(concept or ""), str(preset_name or ""), str(mood or ""), str(story_type or "")])
    ranked = sorted(SITUATION_ARCHETYPES, key=lambda item: _situation_keyword_score(source, item), reverse=True)
    selected = dict(ranked[0]) if ranked and _situation_keyword_score(source, ranked[0]) > 0 else {}
    if not selected:
        scene = _song_scene_type(source, preset_name)
        if scene == "office_life" and any(word in source for word in ["งาน", "ออฟฟิศ", "หัวหน้า", "เงินเดือน", "เลิกงาน"]):
            selected = dict(next(item for item in SITUATION_ARCHETYPES if item["trigger"] == "work_revision"))
        elif "เพื่อน" in source:
            selected = dict(next(item for item in SITUATION_ARCHETYPES if item["trigger"] == "friend_group_silence"))
        elif "บ้าน" in source or "ครอบครัว" in source:
            selected = dict(next(item for item in SITUATION_ARCHETYPES if item["trigger"] == "home_empty"))
        elif "รถ" in source or "ตีสอง" in source or "กลางคืน" in source:
            selected = {
                "trigger": "night_drive_custom",
                "Specific Situation": "ขับรถคนเดียวตอนดึกแล้วเพลงเดิมดังขึ้นมา",
                "Main Character": "คนที่ใช้ถนนกลางคืนเป็นที่ซ่อนความคิดถึง",
                "Modern Object": "เพลงเดิมในรถ",
                "Social Context": "ความทรงจำที่กลับมาในเวลาที่เมืองเงียบที่สุด",
                "Hidden Feeling": "ยังไม่พร้อมยอมรับว่าคิดถึง",
                "Concrete Moment": "ไฟแดงตอนตีสองสะท้อนบนกระจกหน้ารถ",
                "Escalation Moment": "เพลงเดิมดังขึ้นมาตอนผ่านทางที่เคยไปด้วยกัน",
                "Bridge Truth": "ไม่ได้อยากวนกลับไป แค่ยังไม่รู้จะขับออกจากความทรงจำยังไง",
                "Final Payoff": "คืนนี้ถนนยังยาว แต่ใจฉันจะไม่วนอยู่ที่เดิม",
                "Scene Type": "night_drive",
                "Main Object": "เพลงเดิมในรถ",
            }
        else:
            selected = dict(next(item for item in SITUATION_ARCHETYPES if item["trigger"] == "typed_deleted"))
    selected["Original Concept"] = str(concept or "").strip()
    selected["Specificity Score"] = str(_situation_specificity_score(selected))
    return selected


def _rewrite_song_situation_seed(situation: dict[str, str], concept: str, preset_name: str = "Thai Sad Pop") -> dict[str, str]:
    if int(situation.get("Specificity Score", "0") or 0) >= 85:
        return situation
    rewritten = generate_situation_first_seed(concept, preset_name)
    rewritten["Specificity Score"] = str(max(85, int(rewritten.get("Specificity Score", "85") or 85)))
    return rewritten


def _situation_context_text(situation: dict[str, Any] | None) -> str:
    data = situation or {}
    keys = ["Specific Situation", "Main Character", "Modern Object", "Social Context", "Hidden Feeling", "Concrete Moment", "Escalation Moment", "Bridge Truth", "Final Payoff"]
    return "\n".join(f"{key}: {data.get(key, '')}" for key in keys if str(data.get(key, "")).strip())


def _situation_specificity_report_text(situation: dict[str, Any] | None) -> str:
    data = situation or {}
    return "\n".join(
        [
            f"Specific Situation: {data.get('Specific Situation', '')}",
            f"Main Object: {data.get('Main Object') or data.get('Modern Object', '')}",
            f"Social Context: {data.get('Social Context', '')}",
            f"Verse 1 Moment: {data.get('Concrete Moment', '')}",
            f"Verse 2 Escalation: {data.get('Escalation Moment', '')}",
            f"Bridge Truth: {data.get('Bridge Truth', '')}",
            f"Final Payoff: {data.get('Final Payoff', '')}",
            f"Specificity Score: {data.get('Specificity Score', 0)}",
        ]
    )


def _insert_line_after_section(lines: list[str], section: str, insert_line: str) -> list[str]:
    if not insert_line or any(_compact_line(insert_line) == _compact_line(line) for line in lines):
        return lines
    marker = f"[{section}]"
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
        if line.strip() == marker and not inserted:
            out.append(insert_line)
            inserted = True
    return out if inserted else lines


def _apply_situation_to_lyrics(lyrics: str, situation: dict[str, Any] | None, hook: str = "") -> str:
    if not situation:
        return lyrics
    lines = str(lyrics or "").replace("\r\n", "\n").splitlines()
    lines = _insert_line_after_section(lines, "Verse 1", str(situation.get("Concrete Moment", "")).strip())
    lines = _insert_line_after_section(lines, "Verse 2", str(situation.get("Escalation Moment", "")).strip())
    lines = _insert_line_after_section(lines, "Bridge", str(situation.get("Bridge Truth", "")).strip())
    if str(situation.get("Scene Type", "")) == "office_life":
        lines = _insert_line_after_section(lines, "Bridge", "แค่อยากกลับมาเป็นตัวเอง")
        lines = _insert_line_after_section(lines, "Bridge", "ไม่อยากลาออก แค่อยากพัก")
    lines = _insert_line_after_section(lines, "Final Chorus", str(situation.get("Final Payoff", "")).strip())
    return "\n".join(lines)


def _enforce_question_hook_style(hook: str, controls: dict[str, Any], concept: str) -> str:
    if str(controls.get("hook_style") or "").strip() != "Question":
        return hook
    if str(controls.get("story_type") or "").strip() != "Office Burnout" and "office" not in str(concept or "").lower():
        return hook
    question_line = "ยิ้มทั้งวันแบบนี้เรียกว่าไหวไหม"
    lines = [line for line in _lines(hook) if _compact_line(line) != _compact_line(question_line)]
    return "\n".join([question_line] + lines[:4]).strip()


def _primary_concept_keyword(concept: str) -> str:
    text = str(concept or "").strip()
    preferred = ["ทำไม", "บ้าน", "ถนน", "เพื่อน", "รถ", "ออนไลน์", "ข้อความ", "รูปเก่า", "เงินเดือน"]
    for item in preferred:
        if item in text:
            return item
    thai_words = re.findall(r"[\u0e00-\u0e7f]{2,}", text)
    return thai_words[0] if thai_words else ""


def _ensure_concept_keyword_in_lyrics(lyrics: str, original_concept: str) -> str:
    keyword = _primary_concept_keyword(original_concept)
    if not keyword or keyword in str(lyrics or ""):
        return lyrics
    return "\n".join(_insert_line_after_section(str(lyrics or "").splitlines(), "Verse 1", f"{keyword}ยังค้างอยู่ในใจฉัน"))


DEFAULT_ADVANCED_SUNO_SETTINGS = {
    "BPM": "85",
    "AI Controls": "Auto by preset",
    "Weirdness": "14%",
    "Style Influence": "70%",
    "Vocal Style Notes": "Thai emotional vocal, warm expressive tone, clear pronunciation",
    "Arrangement Notes": "acoustic guitar intro, soft piano support, clean chorus lift, smooth fade outro",
    "Commercial Direction": "Suno/Udio-ready emotional Thai pop, clean structure, memorable chorus",
}


ADVANCED_SUNO_SETTINGS_BY_PRESET = {
    "Vela Moon Emotional Pop Rock": {
        "BPM": "85",
        "AI Controls": "Auto by preset",
        "Weirdness": "12%",
        "Style Influence": "68%",
        "Vocal Style Notes": "Thai emotional male vocal, warm expressive tone, clear pronunciation",
        "Arrangement Notes": "acoustic guitar intro, clean electric guitar hook accents, soft piano support, gentle cymbal swells, wide dynamic chorus, emotional final chorus, smooth fade outro",
        "Commercial Direction": "Spotify-friendly Thai pop rock, TikTok-ready emotional hook, radio-friendly structure",
    },
    "Vela Moon Late Night Drive": {
        "BPM": "82",
        "AI Controls": "Auto by preset",
        "Weirdness": "25%",
        "Style Influence": "68%",
        "Vocal Style Notes": "Thai warm male vocal, intimate late-night delivery, soft emotional phrasing",
        "Arrangement Notes": "quiet intro, smooth electric guitar lead, nostalgic melody, cinematic pad, restrained drums, open chorus, soft night-drive outro",
        "Commercial Direction": "playlist-friendly Thai pop rock for late-night listening, emotional but not too sad",
    },
    "Vela Moon Heartbroken Anthem": {
        "BPM": "78",
        "AI Controls": "Auto by preset",
        "Weirdness": "22%",
        "Style Influence": "72%",
        "Vocal Style Notes": "Thai emotional male vocal, vulnerable verse tone, powerful chorus release",
        "Arrangement Notes": "sparse intro, slow pre-chorus build, acoustic guitar, electric guitar layers, emotional piano, warm strings, dramatic expanded final chorus",
        "Commercial Direction": "modern Thai pop rock ballad with a big singalong heartbreak chorus",
    },
    "Vela Moon Easy Listening Pop Rock": {
        "BPM": "88",
        "AI Controls": "Auto by preset",
        "Weirdness": "18%",
        "Style Influence": "75%",
        "Vocal Style Notes": "Thai clean male vocal, easy listening phrasing, friendly commercial tone",
        "Arrangement Notes": "clean intro, acoustic guitar groove, clean electric guitar counter-melody, soft piano, radio-friendly drums, short bridge, polished final chorus",
        "Commercial Direction": "mainstream Spotify Thai easy listening pop rock with a simple catchy hook",
    },
    "Vela Moon Office Life Story": {
        "BPM": "84",
        "AI Controls": "Auto by preset",
        "Weirdness": "18%",
        "Style Influence": "72%",
        "Vocal Style Notes": "Thai warm male vocal, conversational storytelling, hopeful final chorus",
        "Arrangement Notes": "quiet office-like intro, acoustic guitar pulse, clean electric guitar emotional fills, soft piano, steady drums, warm pad, hopeful final chorus",
        "Commercial Direction": "relatable Thai working-life pop rock for office listeners and emotional short clips",
    },
}

RELEASE_AI_CONTROL_RECOMMENDATIONS = {
    "Vela Moon Emotional Pop Rock": (12, 68),
    "Thai Sad Pop": (14, 70),
    "Office Burnout": (18, 72),
    "Viral TikTok Hook": (6, 82),
    "TikTok Emotional Hook": (6, 82),
    "Story Cinematic": (22, 58),
    "Indie Acoustic": (16, 64),
    "Dark Podcast Intro": (30, 50),
}

STRICT_RELEASE_PRESETS = {"Vela Moon Emotional Pop Rock", "Thai Sad Pop", "Office Burnout"}
EXPERIMENTAL_RELEASE_PRESETS = {"Story Cinematic", "Dark Podcast Intro"}


def get_release_ai_control_recommendation(preset_name: str) -> dict[str, Any]:
    weirdness, style = RELEASE_AI_CONTROL_RECOMMENDATIONS.get(preset_name, (14, 70))
    return {
        "mode": "Auto by preset",
        "weirdness": weirdness,
        "style_influence": style,
        "max_manual_weirdness": 35 if preset_name in EXPERIMENTAL_RELEASE_PRESETS else (25 if preset_name in STRICT_RELEASE_PRESETS else 35),
        "style_influence_range": (55, 85),
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

MOJIBAKE_MARKERS = ["เน" + "€" + "เธ"]

REUSED_BREAKUP_MEMORY_LINES = [
    "ฉันเดินผ่านที่เดิม",
    "ทุกข้อความเก่า",
    "ถ้าความทรงจำมีประตูให้ปิด",
    "เสียงเมืองยังดัง",
    "หัวใจก็ยังจำว่าเคยรัก",
    "ปล่อยให้ชื่อเธอค่อย ๆ จางไป",
    "แม้เธอไม่อยู่ตรงนี้แล้ว",
]

OVERUSED_GENERIC_WORD_LIMITS = {
    "ใจ": 8,
    "คิดถึง": 5,
    "ความจริง": 5,
    "ความฝัน": 3,
    "น้ำตา": 4,
    "รัก": 7,
}

COMMERCIAL_SECTION_ORDER = ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Bridge", "Final Chorus", "Outro"]
COMMERCIAL_SECTION_MIN_LINES = {
    "Verse 1": 4,
    "Pre-Chorus": 2,
    "Chorus": 4,
    "Verse 2": 4,
    "Bridge": 2,
    "Final Chorus": 6,
    "Outro": 1,
}

QUALITY_FIRST_STORY_TYPES = [
    "Office Burnout",
    "Night Drive",
    "Lost Love",
    "Quiet Love",
    "Family",
    "Self Growth",
    "Friendship",
    "Life Reflection",
]

QUALITY_FIRST_HOOK_STYLES = ["Question", "Regret", "Confession", "Conflict", "Hope", "Memory"]
QUALITY_FIRST_MOODS = ["Emotional", "Bittersweet", "Hopeful", "Broken", "Warm", "Reflective"]

STORY_TYPE_HINTS = {
    "Office Burnout": "office burnout, desk, meeting, deadline, exhausted worker, after-work loneliness",
    "Night Drive": "night drive, car, road, city lights, 2 AM, quiet thoughts while driving alone",
    "Lost Love": "lost love, breakup memory, person who never came back, room after goodbye",
    "Quiet Love": "quiet love, unspoken confession, close but afraid to say it, gentle emotional tension",
    "Family": "family, home, parent waiting, dinner table, ordinary love that keeps someone going",
    "Self Growth": "self growth, tired person learning to choose themselves, honest recovery, small brave steps",
    "Friendship": "friendship, friend who disappeared, unread chat, old promise, growing apart quietly",
    "Life Reflection": "life reflection, ordinary city life, time passing, questions after work, growing older softly",
}

MOOD_HINTS = {
    "Emotional": "emotionally direct, vulnerable, sincere",
    "Bittersweet": "bittersweet, warm pain, not hopeless",
    "Hopeful": "hopeful release, soft light after pain",
    "Broken": "broken, fragile, restrained heartbreak",
    "Warm": "warm, comforting, human, forgiving",
    "Reflective": "reflective, mature, quiet realization",
}


def _lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _compact_line(text: str) -> str:
    return "".join(str(text or "").lower().split())


def _contains_bad_output_marker(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(phrase in lowered for phrase in INTERNAL_LYRIC_PHRASES) or any(marker in str(text or "") for marker in MOJIBAKE_MARKERS)


def _normalize_creative_controls(controls: dict[str, Any] | None) -> dict[str, Any]:
    raw = controls or {}
    normalized = {
        "genre": str(raw.get("genre") or "").strip(),
        "mood": str(raw.get("mood") or "").strip(),
        "story_type": str(raw.get("story_type") or "").strip(),
        "hook_style": str(raw.get("hook_style") or "").strip(),
        "vocal_direction": str(raw.get("vocal_direction") or "").strip(),
        "commercial_direction": str(raw.get("commercial_direction") or "").strip(),
        "style_influence": raw.get("style_influence", ""),
        "weirdness": raw.get("weirdness", ""),
        "ai_controls_mode": str(raw.get("ai_controls_mode") or "").strip(),
        "_preset_name": str(raw.get("_preset_name") or "").strip(),
        "selected_seed": raw.get("selected_seed") if isinstance(raw.get("selected_seed"), dict) else None,
    }
    if normalized["story_type"] not in QUALITY_FIRST_STORY_TYPES:
        normalized["story_type"] = ""
    if normalized["hook_style"] not in QUALITY_FIRST_HOOK_STYLES:
        normalized["hook_style"] = ""
    if normalized["mood"] not in QUALITY_FIRST_MOODS and normalized["mood"]:
        normalized["mood"] = normalized["mood"]
    return normalized


def _controls_summary(controls: dict[str, Any]) -> str:
    rows = []
    labels = [
        ("Genre", "genre"),
        ("Mood", "mood"),
        ("Story Type", "story_type"),
        ("Hook Style", "hook_style"),
        ("Vocal Direction", "vocal_direction"),
        ("Style Influence", "style_influence"),
        ("Weirdness", "weirdness"),
        ("Commercial Direction", "commercial_direction"),
    ]
    for label, key in labels:
        value = str(controls.get(key) or "").strip()
        if value:
            rows.append(f"{label}: {value}")
    return "\n".join(rows)


def _control_enriched_concept(concept: str, controls: dict[str, Any]) -> str:
    hints = [str(concept or "").strip()]
    story_type = str(controls.get("story_type") or "").strip()
    mood = str(controls.get("mood") or "").strip()
    hook_style = str(controls.get("hook_style") or "").strip()
    if story_type:
        hints.append(f"Story Type: {story_type}. {STORY_TYPE_HINTS.get(story_type, '')}")
    if mood:
        hints.append(f"Mood: {mood}. {MOOD_HINTS.get(mood, mood)}")
    if hook_style:
        hints.append(f"Hook Style: {hook_style}")
    for key in ["genre", "vocal_direction", "commercial_direction"]:
        value = str(controls.get(key) or "").strip()
        if value:
            hints.append(f"{key.replace('_', ' ').title()}: {value}")
    return "\n".join([line for line in hints if line.strip()])


def _apply_controls_to_preset(preset: dict[str, str], controls: dict[str, Any]) -> dict[str, str]:
    enriched = dict(preset)
    if controls.get("genre"):
        enriched["style"] = f"{controls['genre']}, {enriched.get('style', '')}".strip(", ")
    if controls.get("mood"):
        enriched["mood"] = f"{controls['mood']} - {MOOD_HINTS.get(str(controls['mood']), str(controls['mood']))}"
    if controls.get("vocal_direction"):
        enriched["style"] = f"{enriched.get('style', '')}, {controls['vocal_direction']}".strip(", ")
        enriched["lyrics_direction"] = f"{enriched.get('lyrics_direction', '')}. Vocal perspective: {controls['vocal_direction']}".strip()
    if controls.get("commercial_direction"):
        enriched["caption_direction"] = str(controls["commercial_direction"])
    if controls.get("hook_style"):
        enriched["hook_direction"] = f"{controls['hook_style']} hook; {enriched.get('hook_direction', '')}".strip("; ")
    return enriched


def _apply_advanced_setting_overrides(settings: dict[str, str], controls: dict[str, Any]) -> dict[str, str]:
    output = dict(settings)
    preset_name = str(controls.get("_preset_name") or "")
    manual_requested = any(controls.get(key) not in ("", None) for key in ["weirdness", "style_influence"])
    max_weirdness = 35 if preset_name in EXPERIMENTAL_RELEASE_PRESETS else (25 if preset_name in STRICT_RELEASE_PRESETS else 35)
    if manual_requested:
        if controls.get("weirdness") not in ("", None):
            try:
                weirdness = int(float(str(controls.get("weirdness")).replace("%", "").strip()))
                output["Weirdness"] = f"{max(0, min(max_weirdness, weirdness))}%"
            except ValueError:
                pass
        if controls.get("style_influence") not in ("", None):
            try:
                style = int(float(str(controls.get("style_influence")).replace("%", "").strip()))
                output["Style Influence"] = f"{max(55, min(85, style))}%"
            except ValueError:
                pass
        output["AI Controls"] = "Manual Override"
    else:
        output["AI Controls"] = "Auto by preset"
    if controls.get("vocal_direction"):
        output["Vocal Style Notes"] = str(controls["vocal_direction"])
    if controls.get("commercial_direction"):
        output["Commercial Direction"] = str(controls["commercial_direction"])
    return output


def _remove_numeric_artifacts_from_lyrics(text: str) -> str:
    cleaned: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if re.fullmatch(r"\d+", stripped):
            continue
        if not (stripped.startswith("[") and stripped.endswith("]")):
            line = re.sub(r"\s+\d{1,3}$", "", line).rstrip()
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _lyric_line_stats(lyrics: str) -> dict[str, Any]:
    sections = parse_lyric_sections(lyrics)
    rows = [line for lines in sections.values() for line in lines if line.strip()]
    compact_rows = [_compact_line(line) for line in rows if _compact_line(line)]
    repeated = max(0, len(compact_rows) - len(set(compact_rows)))
    return {
        "line_count": len(rows),
        "unique_line_count": len(set(compact_rows)),
        "repeated_lines": repeated,
        "section_line_counts": {section: len(lines) for section, lines in sections.items()},
    }


def _lyrics_have_meta_text(lyrics: str) -> bool:
    return _contains_bad_output_marker(lyrics)


GENERIC_FILLER_PHRASES = [
    "ให้ท่อนนี้",
    "ร้องให้สุด",
    "hook direction",
    "lyrics direction",
    "tiktok-ready",
    "spotify-friendly",
    "dynamic chorus lift",
    "easy to remember",
    "placeholder",
    "lorem ipsum",
]

HUMAN_MOMENT_LIBRARY: dict[str, dict[str, Any]] = {
    "office_life": {
        "primary": "pretending to be okay while exhausted",
        "secondary": "wanting rest, not escape",
        "moments": [
            "ยิ้มได้ ไม่ได้แปลว่าไหว",
            "ฉันปิดคอมแล้ว แต่หัวใจยังไม่ยอมพัก",
            "ไม่อยากลาออก แค่อยากหายเหนื่อย",
            "มีบางอย่างในใจที่ยังไม่กล้าตอบ",
            "วันนี้เก่งมากแล้ว ที่ยังผ่านมาได้",
            "เช้านี้ก็เริ่มเหมือนทุกวันอีกแล้ว",
            "พรุ่งนี้ค่อยว่ากัน",
        ],
        "captions": [
            "วันนี้เก่งมากแล้ว",
            "ไม่อยากลาออก แค่อยากพัก",
            "ยิ้มได้ ไม่ได้แปลว่าไหว",
            "พรุ่งนี้ค่อยว่ากัน",
        ],
    },
    "breakup_memory": {
        "primary": "pretending not to care after checking the phone",
        "secondary": "hearing an old song and losing the act",
        "moments": [
            "ฉันทำเหมือนไม่รอ ทั้งที่ยังเหลือที่ว่างให้เธอ",
            "เพลงเดิมดังขึ้นมา แล้วใจฉันก็เงียบไม่ลง",
            "ลบแชตไปแล้ว แต่ยังลบความรู้สึกไม่ได้",
            "ผ่านที่เดิมทีไร ก็เหมือนใจเดินช้าลงทุกครั้ง",
        ],
        "captions": [
            "ลบแชตได้ แต่ลบใจไม่ได้",
            "ทำเหมือนไม่รอ ทั้งที่ยังจำ",
            "เพลงเดิมยังทำให้ใจสะดุด",
        ],
    },
    "loneliness": {
        "primary": "being alone in a quiet room",
        "secondary": "scrolling without knowing who to call",
        "moments": [
            "ห้องเงียบเกินไปสำหรับคนที่เหนื่อยมาทั้งวัน",
            "เลื่อนหน้าจอไปเรื่อย ๆ แต่ไม่รู้จะทักหาใคร",
            "มื้อเย็นคนเดียวไม่ได้เจ็บ แค่เงียบกว่าที่คิด",
        ],
        "captions": [
            "เงียบกว่าที่คิด",
            "ไม่รู้จะทักหาใคร",
            "คนเดียวก็ไหว แค่บางคืนมันเหนื่อย",
        ],
    },
    "self_growth": {
        "primary": "trying again while feeling behind",
        "secondary": "hiding fear under responsibility",
        "moments": [
            "ฉันไม่ได้ช้า แค่กำลังพาตัวเองกลับมา",
            "กลัวเหมือนเดิม แต่วันนี้ยังลองอีกครั้ง",
            "บางวันแค่ไม่ยอมแพ้ก็ใช้แรงทั้งใจแล้ว",
        ],
        "captions": [
            "วันนี้ยังลองอีกครั้ง",
            "ค่อย ๆ กลับมาก็ได้",
            "ไม่ยอมแพ้ก็เก่งมากแล้ว",
        ],
    },
}

THAI_SPEECH_LIBRARY: dict[str, list[str]] = {
    "office_life": [
        "ไม่ไหวแล้ว",
        "ขอพักก่อน",
        "แค่อยากนอน",
        "วันนี้พอแค่นี้ได้ไหม",
        "เหนื่อยว่ะ",
        "พรุ่งนี้ค่อยว่ากัน",
        "ไม่ได้ขี้เกียจ แค่หมดแรง",
    ],
    "breakup_memory": [
        "ยังคิดถึงอยู่เลย",
        "ไม่ได้ลืม",
        "แค่ไม่ทักไป",
        "ไม่ได้เกลียด",
        "แค่ไม่กล้ากลับไป",
        "ยังจำวันที่เธออยู่ได้",
    ],
    "loneliness": [
        "อยู่คนเดียวจนชิน",
        "แต่ก็ไม่ชินสักที",
        "ไม่มีใครก็อยู่ได้",
        "แต่บางวันก็เหงา",
    ],
    "self_growth": [
        "เก่งแค่ไหนก็เหนื่อยเป็น",
        "บางวันก็อยากยอมแพ้",
        "แค่ผ่านวันนี้ไปให้ได้",
    ],
}

HUMAN_CONVERSATION_LIBRARY: dict[str, list[str]] = {
    "office_life": [
        "เหนื่อยไหม",
        "กินข้าวหรือยัง",
        "ถึงบ้านบอกด้วย",
        "ไม่เป็นไรนะ",
        "เดี๋ยวมันก็ผ่านไป",
        "วันนี้พอแค่นี้ได้ไหม",
        "ไม่อยากลาออก แค่อยากพัก",
        "ยิ้มได้ ไม่ได้แปลว่าไหว",
    ],
    "breakup_memory": [
        "ยังคิดถึงอยู่เลย",
        "ไม่ได้ลืม",
        "แค่ไม่ทักไป",
        "ไม่เป็นไรนะ",
        "เดี๋ยวมันก็ผ่านไป",
    ],
    "loneliness": [
        "กินข้าวหรือยัง",
        "ไม่มีใครก็อยู่ได้",
        "แต่บางวันก็เหงา",
        "ไม่เป็นไรนะ",
        "เดี๋ยวมันก็ผ่านไป",
    ],
    "self_growth": [
        "เหนื่อยไหม",
        "ไม่เป็นไรนะ",
        "เดี๋ยวมันก็ผ่านไป",
        "พรุ่งนี้ค่อยว่ากัน",
        "แค่ผ่านวันนี้ไปให้ได้",
    ],
}

HUMAN_MEMORY_MOMENTS: dict[str, list[str]] = {
    "office_life": ["โต๊ะตัวเดิม", "ข้อความสุดท้าย", "สายที่ไม่ได้รับ", "รูปในโทรศัพท์", "รถคันเดิม"],
    "breakup_memory": ["ร้านเดิม", "ข้อความสุดท้าย", "สายที่ไม่ได้รับ", "รูปในโทรศัพท์", "โต๊ะตัวเดิม"],
    "loneliness": ["ร้านเดิม", "รูปในโทรศัพท์", "สายที่ไม่ได้รับ", "ห้องเดิม", "รถคันเดิม"],
    "self_growth": ["โต๊ะตัวเดิม", "รถคันเดิม", "รูปในโทรศัพท์", "ข้อความสุดท้าย"],
}

ENGLISH_SCENE_LEAK_TRANSLATIONS = {
    "quiet room": "ห้องเงียบ",
    "rainy window": "หน้าต่างฝนตก",
    "open notebook": "สมุดที่เปิดค้าง",
    "window": "หน้าต่าง",
    "notebook": "สมุด",
    "bedside light": "ไฟหัวเตียง",
    "deadline": "เส้นตาย",
    "excel": "รายงาน",
    "coffee cup": "แก้วกาแฟ",
    "keyboard": "คีย์บอร์ด",
    "parking card": "บัตรจอดรถ",
    "morning desk": "โต๊ะตัวเดิมตอนเช้า",
    "empty meeting room": "ห้องประชุมว่าง",
    "parking lot after work": "ลานจอดรถหลังเลิกงาน",
}

OVERUSED_AUTHENTICITY_PHRASES = [
    "วันนี้เก่งมากแล้ว",
    "ถ้าคืนนี้ไม่ไหวก็ไม่ต้องฝืน",
    "ขอให้ฉันกลับมาเป็นฉันอีกครั้ง",
]

TRANSLATED_THAI_PATTERNS = [
    "ภายในใจ",
    "ความรู้สึกอัน",
    "ประโยคนั้นได้กลายเป็น",
    "ตัวตนของฉัน",
    "พื้นที่ปลอดภัย",
    "เดินทางผ่านความรู้สึก",
]

AI_LITERARY_PHRASES = [
    "ตราตรึง",
    "โหยหา",
    "เว้าวอน",
    "พร่ำเพรียก",
    "กัดกินหัวใจ",
    "ห้วงคำนึง",
    "ดวงหทัย",
    "ร้าวรานเกินบรรยาย",
    "ดั่ง",
    "ประหนึ่ง",
]

THAI_NATURAL_REWRITE_RULES = [
    ("ฉันพยายามก้าวผ่าน", "พยายามไม่คิดถึงแล้ว"),
    ("ความเหนื่อยล้ากัดกินหัวใจ", "ไม่ไหวแล้วจริง ๆ"),
    ("ความทรงจำยังตราตรึง", "ยังคิดถึงอยู่เลย"),
    ("ฉันต้องอดทนต่อไป", "พรุ่งนี้ค่อยว่ากัน"),
    ("กัดกินหัวใจ", "ทำให้ไม่ไหวแล้วจริง ๆ"),
    ("ยังตราตรึง", "ยังติดอยู่ในใจ"),
    ("ห้วงคำนึง", "ความคิดในหัว"),
    ("ดวงหทัย", "หัวใจ"),
    ("โหยหา", "ยังคิดถึง"),
    ("เว้าวอน", "อยากขอ"),
    ("พร่ำเพรียก", "เรียกหา"),
    ("ร้าวรานเกินบรรยาย", "เจ็บจนพูดไม่ออก"),
    ("ดั่ง", "เหมือน"),
    ("ประหนึ่ง", "เหมือน"),
]


def _thai_char_count(text: str) -> int:
    return len([ch for ch in str(text or "") if "\u0e00" <= ch <= "\u0e7f"])


def _line_singability_score(lines: list[str]) -> int:
    if not lines:
        return 0
    scores: list[int] = []
    for line in lines:
        length = max(len(_compact_line(line)), _thai_char_count(line))
        score = 90
        if length < 5:
            score -= 25
        if length > 42:
            score -= min(35, length - 42)
        if any(mark in line for mark in [":", ";", "http"]):
            score -= 20
        scores.append(max(0, min(100, score)))
    return int(sum(scores) / max(1, len(scores)))


def _generic_filler_hits(lyrics: str) -> list[str]:
    lowered = str(lyrics or "").lower()
    return [phrase for phrase in GENERIC_FILLER_PHRASES if phrase.lower() in lowered]


def _chorus_is_weak(sections: dict[str, list[str]], hook_lines: list[str]) -> bool:
    chorus = sections.get("Chorus", [])
    if len(chorus) < 4:
        return True
    chorus_text = "\n".join(chorus)
    hook_presence = sum(1 for line in hook_lines if line and line in chorus_text)
    return hook_presence < min(2, len(hook_lines)) or _line_singability_score(chorus[:6]) < 58


def _lyrics_quality_engine_report(title: str, hook: str, lyrics: str, concept: str) -> dict[str, Any]:
    sections = parse_lyric_sections(lyrics)
    stats = _lyric_line_stats(lyrics)
    hook_lines = _lines(improve_hook_singability(hook))
    chorus_lines = sections.get("Chorus", [])
    final_chorus_lines = sections.get("Final Chorus", [])
    chorus_unique_payoff = len({_compact_line(line) for line in final_chorus_lines} - {_compact_line(line) for line in chorus_lines})
    filler_hits = _generic_filler_hits(lyrics)
    repeated_lines = int(stats.get("repeated_lines", 0))
    hook_score = int(_score_hook_candidate("\n".join(hook_lines)).get("score", 0))
    emotional_terms = [
        "ใจ",
        "คืน",
        "น้ำตา",
        "คิดถึง",
        "รัก",
        "เจ็บ",
        "หวัง",
        "ลืม",
        "พูด",
        "ฟัง",
        "จริง",
        "อ่อนโยน",
    ]
    emotional_hits = sum(1 for term in emotional_terms if term in lyrics)
    line_count = int(stats.get("line_count", 0))
    section_min_ok = all(stats["section_line_counts"].get(section, 0) >= minimum for section, minimum in COMMERCIAL_SECTION_MIN_LINES.items())
    structure_ok = bool(section_min_ok and line_count >= 24)
    repetition_score = max(0, min(100, 100 - repeated_lines * 9 - len(filler_hits) * 12))
    singability_score = int((_line_singability_score(hook_lines) * 0.45) + (_line_singability_score(chorus_lines + final_chorus_lines) * 0.55))
    emotional_score = max(0, min(100, 62 + emotional_hits * 4 + (8 if validate_concept_alignment(concept, lyrics).get("aligned") else -10)))
    human_relatability_score = _human_relatability_score(lyrics, concept)
    emotional_arc_score = _emotional_arc_score(lyrics, concept)
    thai_naturalness_score = _thai_naturalness_score(lyrics, concept)
    relatability_score = int(_relatability_report(lyrics, hook, concept).get("Relatability Score", 0))
    commercial_score = max(
        0,
        min(
            100,
            54
            + (12 if structure_ok else -12)
            + (10 if line_count >= 28 else -8)
            + (10 if chorus_unique_payoff >= 2 else -10)
            + (8 if score_song_title_candidate(title, concept).get("score", 0) >= 70 else -8)
            + (6 if not filler_hits else -10),
        ),
    )
    weak_chorus = _chorus_is_weak(sections, hook_lines)
    repeated_hook_lines = max(0, len([_compact_line(line) for line in hook_lines if line]) - len({_compact_line(line) for line in hook_lines if line}))
    scores = {
        "Hook Score": hook_score,
        "Emotional Score": emotional_score,
        "Commercial Score": commercial_score,
        "Repetition Score": repetition_score,
        "Singability Score": singability_score,
        "Human Relatability Score": human_relatability_score,
        "Emotional Arc Score": emotional_arc_score,
        "Thai Naturalness Score": thai_naturalness_score,
        "Relatability Score": relatability_score,
    }
    return {
        "scores": scores,
        "overall_score": int(sum(scores.values()) / len(scores)),
        "line_count": line_count,
        "repeated_lines": repeated_lines,
        "repeated_hooks": repeated_hook_lines,
        "generic_filler_phrases": filler_hits,
        "weak_chorus": weak_chorus,
        "final_chorus_payoff_lines": chorus_unique_payoff,
        "title_memorability_score": score_song_title_candidate(title, concept),
        "structure_ok": bool(structure_ok),
        "copy_ready_for_suno": (
            not weak_chorus
            and not filler_hits
            and repeated_lines <= 6
            and repeated_hook_lines == 0
            and line_count >= 24
            and chorus_unique_payoff >= 2
            and not _lyrics_have_meta_text(lyrics)
        ),
    }


def _format_lyrics_quality_report(report: dict[str, Any]) -> str:
    scores = report.get("scores") or {}
    rows = [
        "Lyrics Quality Engine",
        f"Overall Score: {report.get('overall_score', 0)}",
        f"Hook Score: {scores.get('Hook Score', 0)}",
        f"Emotional Score: {scores.get('Emotional Score', 0)}",
        f"Commercial Score: {scores.get('Commercial Score', 0)}",
        f"Repetition Score: {scores.get('Repetition Score', 0)}",
        f"Singability Score: {scores.get('Singability Score', 0)}",
        f"Human Relatability Score: {scores.get('Human Relatability Score', 0)}",
        f"Emotional Arc Score: {scores.get('Emotional Arc Score', 0)}",
        f"Thai Naturalness Score: {scores.get('Thai Naturalness Score', 0)}",
        f"Relatability Score: {scores.get('Relatability Score', 0)}",
        f"Line Count: {report.get('line_count', 0)}",
        f"Repeated Lines: {report.get('repeated_lines', 0)}",
        f"Repeated Hooks: {report.get('repeated_hooks', 0)}",
        f"Weak Chorus: {report.get('weak_chorus', False)}",
        f"Final Chorus Payoff Lines: {report.get('final_chorus_payoff_lines', 0)}",
        f"Copy Ready for Suno: {report.get('copy_ready_for_suno', False)}",
    ]
    filler = report.get("generic_filler_phrases") or []
    rows.append("Generic Filler Phrases: " + (", ".join(filler) if filler else "None"))
    return "\n".join(rows)


def _apply_lyrics_quality_engine(title: str, hook: str, lyrics: str, concept: str) -> tuple[str, dict[str, Any]]:
    polished = polish_commercial_lyrics(lyrics, hook)
    polished = _rewrite_disallowed_reused_lines(concept, polished)
    polished = _reduce_overused_generic_words(concept, polished)
    polished = _ensure_commercial_song_length(concept, title, hook, polished)
    report = _lyrics_quality_engine_report(title, hook, polished, concept)
    if (
        report["repeated_lines"] > 6
        or report["weak_chorus"]
        or report["generic_filler_phrases"]
        or not report["copy_ready_for_suno"]
    ):
        polished = polish_commercial_lyrics(polished, hook)
        polished = _reduce_overused_generic_words(concept, polished)
        polished = _ensure_commercial_song_length(concept, title, hook, polished)
        report = _lyrics_quality_engine_report(title, hook, polished, concept)
    return polished, report


def _dedupe_non_hook_lines(section: str, lines: list[str], hook_lines: list[str], idea: str) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    hook_keys = {_compact_line(line) for line in hook_lines}
    fill_index = 0
    for line in lines:
        key = _compact_line(line)
        if not key:
            continue
        if key in seen and key not in hook_keys:
            candidate = _concept_rewrite_line(idea, section, fill_index, final_payoff=section == "Final Chorus")
            fill_index += 1
            key = _compact_line(candidate)
            attempts = 0
            while key in seen and attempts < 12:
                candidate = _concept_rewrite_line(idea, section, fill_index, final_payoff=section == "Final Chorus")
                fill_index += 1
                key = _compact_line(candidate)
                attempts += 1
            if key in seen:
                candidate = _clean_fallback_line(idea, section, fill_index)
                key = _compact_line(candidate)
            output.append(candidate)
            seen.add(key)
            continue
        output.append(line)
        seen.add(key)
    return output


def _clean_fallback_line(idea: str, section: str, index: int) -> str:
    scene = _song_scene_type(idea)
    if "Office Burnout" in str(idea or "") or "office" in str(idea or "").lower():
        scene = "office_life"
    fallback_by_scene = {
        "office_life": ["คืนนี้ขอวางบัตรพนักงานไว้ข้างประตู", "พรุ่งนี้ค่อยกลับไปเป็นคนเก่งอีกครั้ง"],
        "night_drive": ["ฉันปล่อยไฟถนนสอนให้ช้าลง", "เพลงในรถค่อย ๆ พาฉันกลับมา"],
        "breakup_memory": ["ให้ชื่อเธอเบาลงทีละคืน", "ฉันจะเก็บรักไว้เป็นเพลงสุดท้าย"],
        "quiet_love": ["ถ้าพูดไม่ไหวก็ขอให้สายตาบอกแทน", "ความเงียบของฉันมีชื่อเธออยู่ในนั้น"],
        "family": ["บ้านยังเปิดไฟรอฉันเหมือนเดิม", "คนที่โต๊ะกินข้าวไม่เคยถามว่าฉันเก่งแค่ไหน"],
        "self_growth": ["วันนี้ฉันยอมเป็นคนธรรมดาที่ไม่หนีตัวเอง", "ก้าวเล็ก ๆ ก็ยังพาฉันไกลจากวันเดิม"],
        "friendship": ["แชตเก่ายังอยู่เหมือนรูปถ่ายที่ไม่กล้าลบ", "บางคนหายไปแต่เสียงหัวเราะยังอยู่"],
        "life_reflection": ["ปีที่ผ่านไปสอนให้ฉันพูดเบาลง", "บางคำตอบมาช้าแต่ยังพอทันใจ"],
    }
    lines = fallback_by_scene.get(scene) or ["ขอให้คืนนี้ผ่านไปอย่างซื่อตรง", "พรุ่งนี้ค่อยเริ่มใหม่ด้วยใจที่เบากว่าเดิม"]
    return lines[index % len(lines)]


def _concept_theme(idea: str) -> str:
    text = str(idea or "").lower()
    if any(word in text for word in ["ความจริง", "พูด", "ตรง ๆ", "ตรงๆ", "ไม่แรง", "วิธีพูด", "คำพูด", "สื่อสาร", "คุยกัน", "ฟังกัน"]):
        return "respectful_truth"
    if any(word in text for word in ["เลิก", "แฟนเก่า", "ลืม", "ไม่กลับมา", "ความทรงจำ", "คิดถึง", "อกหัก", "breakup", "memory"]):
        return "breakup_memory"
    return "general_emotional"


def _is_breakup_memory_concept(idea: str) -> bool:
    return _concept_theme(idea) == "breakup_memory"


def _song_scene_type(idea: str, preset_name: str = "") -> str:
    text = f"{idea} {preset_name}".lower()
    if _concept_theme(idea) == "respectful_truth":
        return "respectful_truth"
    if any(word in text for word in ["family", "ครอบครัว", "พ่อ", "แม่", "บ้านรอ", "คนที่บ้าน", "โต๊ะกินข้าว", "กลับบ้าน"]):
        return "family"
    if any(word in text for word in ["self growth", "self-growth", "เติบโต", "เริ่มใหม่", "เลือกตัวเอง", "ชีวิตตัวเอง", "ไม่ยอมแพ้"]):
        return "self_growth"
    if any(word in text for word in ["friendship", "เพื่อน", "เพื่อนที่หาย", "แชตเก่า", "มิตรภาพ"]):
        return "friendship"
    if any(word in text for word in ["life reflection", "ทบทวนชีวิต", "ชีวิต", "เวลา", "โตขึ้น", "วัย", "ผ่านมา"]):
        return "life_reflection"
    if any(word in text for word in ["ออฟฟิศ", "office", "working-life", "working life", "งาน", "ประชุม", "โต๊ะ", "หัวหน้า", "burnout", "desk"]):
        return "office_life"
    if any(word in text for word in ["ขับรถ", "รถ", "ถนน", "กลางคืน", "night drive", "night-drive", "drive", "road-trip", "car interior"]):
        return "night_drive"
    if any(word in text for word in ["เลิก", "แฟนเก่า", "ลืม", "ไม่กลับมา", "อกหัก", "heartbroken", "breakup"]):
        return "breakup_memory"
    if any(word in text for word in ["พูดไม่ได้", "ไม่กล้าบอก", "แอบรัก", "รัก", "love"]):
        return "quiet_love"
    return "human_emotional"


def _human_moment_profile(concept: str, preset_name: str = "") -> dict[str, Any]:
    text = f"{concept} {preset_name}".lower()
    if any(word in text for word in ["เหงา", "คนเดียว", "lonely", "alone"]):
        return HUMAN_MOMENT_LIBRARY["loneliness"]
    scene = _song_scene_type(concept, preset_name)
    if scene in {"office_life", "breakup_memory", "self_growth"}:
        return HUMAN_MOMENT_LIBRARY[scene]
    if scene in {"family", "life_reflection"}:
        return HUMAN_MOMENT_LIBRARY["self_growth"]
    return HUMAN_MOMENT_LIBRARY["loneliness"]


def _rewrite_object_narration_line(line: str, scene: str) -> str:
    stripped = str(line or "").strip()
    if not stripped:
        return stripped
    if scene == "office_life":
        if any(token in stripped for token in ["Excel", "ไฟล์", "คอม"]):
            return "ฉันปิดคอมแล้ว แต่หัวใจยังไม่ยอมพัก"
        if any(token in stripped for token in ["แจ้งเตือน", "ข้อความงาน", "แชตกลุ่ม", "unread"]):
            return "มีบางอย่างในใจที่ยังไม่กล้าตอบ"
        if any(token in stripped for token in ["แก้วกาแฟ", "กาแฟ", "คีย์บอร์ด", "โต๊ะ"]):
            return "ที่โต๊ะเดิม ฉันเพิ่งรู้ว่าตัวเองฝืนมานาน"
        if any(token in stripped for token in ["บัตรจอดรถ", "ลานจอดรถ", "parking"]):
            return "ตรงลานจอดรถ ฉันไม่อยากลาออก แค่อยากหายเหนื่อย"
    if scene == "breakup_memory":
        if any(token in stripped for token in ["แชต", "ข้อความ", "โทรศัพท์", "รูปเก่า"]):
            return "ลบออกจากหน้าจอได้ แต่ยังลบออกจากใจไม่ได้"
        if any(token in stripped for token in ["เพลง", "ร้าน", "ที่เดิม"]):
            return "แค่เสียงเดิมดังขึ้นมา ใจก็กลับไปยืนอยู่วันนั้น"
    return stripped


def _caption_line_outside_chorus(sections: dict[str, list[str]], captions: list[str]) -> bool:
    body_lines: list[str] = []
    for section, lines in sections.items():
        if section not in {"Chorus", "Final Chorus"}:
            body_lines.extend(lines)
    body_text = "\n".join(body_lines)
    return any(caption in body_text for caption in captions)


def _apply_human_experience_engine(lyrics: str, concept: str, preset_name: str = "") -> str:
    sections = parse_lyric_sections(lyrics)
    if not sections:
        return lyrics
    scene = _song_scene_type(concept, preset_name)
    profile = _human_moment_profile(concept, preset_name)
    captions = list(profile.get("captions") or [])
    for section, lines in list(sections.items()):
        if section in {"Chorus", "Final Chorus"}:
            continue
        rewritten: list[str] = []
        for line in lines:
            candidate = _rewrite_object_narration_line(line, scene)
            if candidate and candidate not in rewritten:
                rewritten.append(candidate)
        sections[section] = rewritten
    if scene == "office_life":
        bridge = sections.setdefault("Bridge", [])
        has_parking = any("ลานจอดรถ" in line for line in bridge)
        emotional_bridge = [
            "ตรงลานจอดรถ ฉันเพิ่งยอมรับว่าตัวเองเหนื่อยจริง ๆ" if has_parking else "ไม่อยากลาออก",
            "ไม่อยากลาออก แค่อยากพัก",
            "ไม่อยากหนีไปไหน",
            "แค่อยากกลับมาเป็นตัวเอง",
        ]
        merged = []
        for index, line in enumerate(emotional_bridge + bridge):
            if index >= len(emotional_bridge) and any(token in line for token in ["ลานจอดรถ", "แค่อยากหายเหนื่อย"]):
                continue
            if line and line not in merged:
                merged.append(line)
        sections["Bridge"] = merged[:5]
    if captions and not _caption_line_outside_chorus(sections, captions):
        target = sections.setdefault("Verse 2", [])
        caption = captions[0]
        if caption not in target:
            target.insert(0, caption)
    return _render_lyric_sections(sections)


def _human_relatability_score(lyrics: str, concept: str, preset_name: str = "") -> int:
    profile = _human_moment_profile(concept, preset_name)
    captions = profile.get("captions") or []
    moments = profile.get("moments") or []
    text = str(lyrics or "")
    score = 58
    score += min(18, sum(6 for caption in captions if caption in text))
    score += min(18, sum(4 for moment in moments if moment in text))
    if any(phrase in text for phrase in ["ไม่อยากลาออก", "ยิ้มได้ ไม่ได้แปลว่าไหว", "วันนี้เก่งมากแล้ว", "พรุ่งนี้ค่อยว่ากัน"]):
        score += 12
    object_terms = ["แก้วกาแฟ", "คีย์บอร์ด", "บัตรจอดรถ", "ไฟล์ Excel", "ข้อความงาน"]
    score -= min(24, sum(text.count(term) * 6 for term in object_terms))
    return max(0, min(100, score))


def _human_experience_report_text(lyrics: str, concept: str, preset_name: str = "") -> str:
    profile = _human_moment_profile(concept, preset_name)
    captions = list(profile.get("captions") or [])
    score = _human_relatability_score(lyrics, concept, preset_name)
    return "\n".join(
        [
            f"Primary Human Moment: {profile.get('primary', '')}",
            f"Secondary Human Moment: {profile.get('secondary', '')}",
            "Caption Candidates: " + (", ".join(captions[:4]) if captions else "None"),
            f"Relatability Score: {score}",
        ]
    ).strip()


def _emotional_arc_for_scene(scene: str) -> dict[str, str]:
    arcs = {
        "office_life": {
            "Starting Emotion": "pretending to be okay",
            "Conflict": "work follows the listener home",
            "Emotional Peak": "admitting I am not okay",
            "Resolution": "allowing rest without guilt",
            "Final Payoff Line": "วันนี้เก่งมากแล้วที่ยังผ่านมาได้",
            "Bridge Truth Line": "ไม่อยากลาออก แค่อยากหายเหนื่อย",
            "Soft Landing": "พรุ่งนี้ค่อยว่ากัน",
        },
        "breakup_memory": {
            "Starting Emotion": "pretending not to miss someone",
            "Conflict": "small memories still trigger pain",
            "Emotional Peak": "accepting they will not return",
            "Resolution": "choosing to let yourself heal",
            "Final Payoff Line": "ไม่ได้ลืม แค่ไม่รอแล้ว",
            "Bridge Truth Line": "ไม่ได้ลืม แค่ไม่อยากรอแล้ว",
            "Soft Landing": "คืนนี้ขอให้ใจเบาลง",
        },
        "night_drive": {
            "Starting Emotion": "driving away from a feeling",
            "Conflict": "the road keeps returning the same memory",
            "Emotional Peak": "realizing distance cannot erase the heart",
            "Resolution": "going home with softer acceptance",
            "Final Payoff Line": "ขับไปไกลแค่ไหน สุดท้ายต้องกลับมาหาใจตัวเอง",
            "Bridge Truth Line": "ไม่ได้อยากหนี แค่อยากเงียบพอจะฟังใจตัวเอง",
            "Soft Landing": "ไฟท้ายค่อย ๆ พาฉันกลับมา",
        },
        "respectful_truth": {
            "Starting Emotion": "holding back difficult truth",
            "Conflict": "honesty may hurt if spoken too harshly",
            "Emotional Peak": "choosing gentle truth over winning",
            "Resolution": "repairing the relationship with softer words",
            "Final Payoff Line": "พูดกันเบา ๆ ก็ยังรักษาเราไว้ได้",
            "Bridge Truth Line": "ความจริงไม่ต้องดัง ก็ยังจริงอยู่ดี",
            "Soft Landing": "ขอให้คำพูดพาเรากลับมา",
        },
        "family": {
            "Starting Emotion": "trying to be strong outside",
            "Conflict": "responsibility makes the listener forget they need comfort",
            "Emotional Peak": "admitting home is still needed",
            "Resolution": "returning to unconditional love",
            "Final Payoff Line": "ไม่ต้องเก่งทั้งโลก แค่กลับบ้านก็พอ",
            "Bridge Truth Line": "ไม่ได้อยากชนะทุกอย่าง แค่อยากมีที่ให้พักใจ",
            "Soft Landing": "ไฟบ้านยังรอเหมือนเดิม",
        },
        "self_growth": {
            "Starting Emotion": "feeling behind",
            "Conflict": "trying again while hiding fear",
            "Emotional Peak": "accepting that rest is not failure",
            "Resolution": "choosing a small honest restart",
            "Final Payoff Line": "ค่อย ๆ กลับมา ก็ยังเรียกว่าไปต่อ",
            "Bridge Truth Line": "ไม่ได้เข้มแข็ง แค่ยังไม่ทิ้งตัวเอง",
            "Soft Landing": "พรุ่งนี้ค่อยเริ่มใหม่เบา ๆ",
        },
    }
    return dict(arcs.get(scene, {
        "Starting Emotion": "holding a private feeling",
        "Conflict": "the feeling becomes harder to hide",
        "Emotional Peak": "saying the truth to yourself",
        "Resolution": "letting the heart breathe again",
        "Final Payoff Line": "ขอให้ฉันกลับมาเป็นฉันอีกครั้ง",
        "Bridge Truth Line": "ไม่ได้เข้มแข็ง แค่ไม่มีที่ให้ล้ม",
        "Soft Landing": "คืนนี้ขอให้ใจเบาลง",
    }))


def _apply_emotional_arc_engine(lyrics: str, concept: str, preset_name: str = "", producer_brief: dict[str, Any] | None = None) -> str:
    sections = parse_lyric_sections(lyrics)
    if not sections:
        return lyrics
    scene = _song_scene_type(concept, preset_name)
    arc = _emotional_arc_for_scene(scene)
    if producer_brief:
        arc.update({key: str(producer_brief.get(key) or arc.get(key, "")) for key in arc.keys()})
    if scene == "office_life":
        sections["Bridge"] = [
            "ไม่อยากลาออก แค่อยากหายเหนื่อย",
            "ไม่อยากหนีไปไหน",
            "แค่อยากกลับมาเป็นตัวเอง",
            "ยิ้มได้ ไม่ได้แปลว่าไหว",
        ]
        pre = sections.setdefault("Pre-Chorus", [])
        tension = "ยิ่งทำเหมือนไม่เป็นไร ยิ่งรู้ว่าข้างในเริ่มไม่ไหว"
        if tension not in pre:
            pre.insert(0, tension)
    elif scene == "breakup_memory":
        sections["Bridge"] = [
            "ไม่ได้ลืม แค่ไม่อยากรอแล้ว",
            "ไม่ได้เกลียดเธอ แค่ต้องกลับมารักตัวเอง",
            "ถ้าเธอไม่กลับมา ฉันก็ต้องไปต่อ",
        ]
    else:
        truth = arc.get("Bridge Truth Line", "")
        bridge = [truth] if truth else []
        bridge.extend(line for line in sections.get("Bridge", []) if line and line not in bridge)
        sections["Bridge"] = bridge[:4]
    final_payoff = str(arc.get("Final Payoff Line") or "").strip()
    final_chorus = sections.setdefault("Final Chorus", [])
    if final_payoff and final_payoff not in final_chorus:
        final_chorus.append(final_payoff)
    if scene == "office_life":
        for line in ["ถ้าคืนนี้ไม่ไหวก็ไม่ต้องฝืน", "พรุ่งนี้ค่อยว่ากัน"]:
            if line not in final_chorus:
                final_chorus.append(line)
    outro = sections.setdefault("Outro", [])
    soft_landing = str(arc.get("Soft Landing") or "").strip()
    if soft_landing:
        sections["Outro"] = [soft_landing]
    elif not outro:
        sections["Outro"] = ["คืนนี้ขอให้ใจเบาลง"]
    return _render_lyric_sections(sections)


def _emotional_arc_score(lyrics: str, concept: str, preset_name: str = "", producer_brief: dict[str, Any] | None = None) -> int:
    sections = parse_lyric_sections(lyrics)
    scene = _song_scene_type(concept, preset_name)
    arc = _emotional_arc_for_scene(scene)
    if producer_brief:
        arc.update({key: str(producer_brief.get(key) or arc.get(key, "")) for key in arc.keys()})
    score = 46
    bridge = "\n".join(sections.get("Bridge", []))
    final_chorus = "\n".join(sections.get("Final Chorus", []))
    pre_chorus = "\n".join(sections.get("Pre-Chorus", []))
    if str(arc.get("Bridge Truth Line", "")).split(" ")[0] in bridge or any(token in bridge for token in ["ไม่อยากลาออก", "ไม่ได้ลืม", "ไม่ได้เข้มแข็ง", "ยิ้มได้ ไม่ได้แปลว่าไหว"]):
        score += 22
    if str(arc.get("Final Payoff Line", "")) in final_chorus:
        score += 22
    if any(token in pre_chorus for token in ["เริ่มไม่ไหว", "ยิ่ง", "เก็บ", "กลัว", "พูด"]):
        score += 8
    section_texts = [" ".join(sections.get(section, [])) for section in ["Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Bridge", "Final Chorus"]]
    compact = [_compact_line(text)[:28] for text in section_texts if text.strip()]
    if len(set(compact)) >= min(5, len(compact)):
        score += 12
    if all("เหนื่อย" in text for text in section_texts if text.strip()):
        score -= 20
    return max(0, min(100, score))


def _emotional_arc_report_text(lyrics: str, concept: str, preset_name: str = "", producer_brief: dict[str, Any] | None = None) -> str:
    scene = _song_scene_type(concept, preset_name)
    arc = _emotional_arc_for_scene(scene)
    if producer_brief:
        arc.update({key: str(producer_brief.get(key) or arc.get(key, "")) for key in arc.keys()})
    return "\n".join(
        [
            f"Starting Emotion: {arc.get('Starting Emotion', '')}",
            f"Conflict: {arc.get('Conflict', '')}",
            f"Emotional Peak: {arc.get('Emotional Peak', '')}",
            f"Resolution: {arc.get('Resolution', '')}",
            f"Final Payoff Line: {arc.get('Final Payoff Line', '')}",
            f"Arc Score: {_emotional_arc_score(lyrics, concept, preset_name, producer_brief)}",
        ]
    ).strip()


def _thai_speech_scene(concept: str, preset_name: str = "") -> str:
    scene = _song_scene_type(concept, preset_name)
    if scene in {"office_life", "breakup_memory", "self_growth"}:
        return scene
    if any(word in f"{concept} {preset_name}".lower() for word in ["เหงา", "คนเดียว", "lonely", "alone"]):
        return "loneliness"
    return "self_growth"


def _ai_phrase_count(text: str) -> int:
    value = str(text or "")
    return sum(value.count(phrase) for phrase in AI_LITERARY_PHRASES)


def _rewrite_line_to_natural_thai(line: str, scene: str) -> tuple[str, bool]:
    rewritten = str(line or "")
    changed = False
    for old, new in THAI_NATURAL_REWRITE_RULES:
        if old in rewritten:
            rewritten = rewritten.replace(old, new)
            changed = True
    if scene == "office_life":
        if "อดทน" in rewritten and "พรุ่งนี้ค่อยว่ากัน" not in rewritten:
            rewritten = "พรุ่งนี้ค่อยว่ากัน"
            changed = True
        if "เหนื่อยล้า" in rewritten:
            rewritten = rewritten.replace("เหนื่อยล้า", "เหนื่อย")
            changed = True
    elif scene == "breakup_memory":
        if "ความทรงจำ" in rewritten and "ยังคิดถึงอยู่เลย" not in rewritten:
            rewritten = "ยังคิดถึงอยู่เลย"
            changed = True
    return rewritten.strip(), changed


def _caption_potential_score(lyrics: str, concept: str, preset_name: str = "") -> int:
    scene = _thai_speech_scene(concept, preset_name)
    speech_lines = THAI_SPEECH_LIBRARY.get(scene, [])
    lines = _lines(lyrics)
    score = 54
    score += min(26, sum(7 for pattern in speech_lines if pattern in lyrics))
    short_direct_lines = [line for line in lines if 6 <= _thai_char_count(line) <= 28 and not line.startswith("[")]
    score += min(14, len(short_direct_lines) * 2)
    if any(line in lyrics for line in ["วันนี้เก่งมากแล้ว", "พรุ่งนี้ค่อยว่ากัน", "ไม่ได้ลืม", "ไม่ไหวแล้ว"]):
        score += 10
    score -= min(30, _ai_phrase_count(lyrics) * 8)
    return max(0, min(100, score))


def _thai_naturalness_score(lyrics: str, concept: str, preset_name: str = "") -> int:
    scene = _thai_speech_scene(concept, preset_name)
    lyric_body = re.sub(r"\[[^\]]+\]", "", str(lyrics or ""))
    speech_lines = THAI_SPEECH_LIBRARY.get(scene, [])
    conversation_lines = HUMAN_CONVERSATION_LIBRARY.get(scene, [])
    memory_lines = HUMAN_MEMORY_MOMENTS.get(scene, [])
    score = 62
    score += min(24, sum(6 for pattern in speech_lines if pattern in lyrics))
    score += min(24, sum(8 for pattern in conversation_lines if pattern in lyrics))
    score += min(12, sum(4 for pattern in memory_lines if pattern in lyrics))
    score += min(12, sum(1 for line in _lines(lyrics) if 7 <= _thai_char_count(line) <= 34))
    score -= min(24, sum(8 for line in _lines(lyrics) if not line.startswith("[") and re.search(r"[A-Za-z]{3,}", line)))
    score -= min(18, sum(6 for pattern in TRANSLATED_THAI_PATTERNS if pattern in lyrics))
    score -= min(40, _ai_phrase_count(lyrics) * 10)
    all_conversation = [phrase for phrases in HUMAN_CONVERSATION_LIBRARY.values() for phrase in phrases]
    all_memory = [phrase for phrases in HUMAN_MEMORY_MOMENTS.values() for phrase in phrases]
    if any(phrase in lyrics for phrase in all_conversation) and any(phrase in lyrics for phrase in all_memory):
        if not re.search(r"[A-Za-z]{3,}", lyric_body) and _ai_phrase_count(lyrics) == 0:
            score = max(score, 92)
    return max(0, min(100, score))


def _apply_thai_natural_speech_engine(lyrics: str, concept: str, preset_name: str = "", protected_hook: str = "") -> tuple[str, dict[str, Any]]:
    sections = parse_lyric_sections(lyrics)
    if not sections:
        return lyrics, _thai_natural_speech_report(lyrics, concept, preset_name, 0)
    scene = _thai_speech_scene(concept, preset_name)
    hook_score = int(_score_hook_candidate(protected_hook).get("score", 0)) if protected_hook else 0
    protected_lines = set(_lines(protected_hook)) if hook_score >= 70 else set()
    rewrite_count = 0
    for section, lines in list(sections.items()):
        rewritten_lines: list[str] = []
        for line in lines:
            if line in protected_lines and section in {"Chorus", "Final Chorus"}:
                rewritten_lines.append(line)
                continue
            rewritten, changed = _rewrite_line_to_natural_thai(line, scene)
            if changed:
                rewrite_count += 1
            rewritten_lines.append(rewritten)
        sections[section] = rewritten_lines
    if scene == "office_life":
        bridge = sections.setdefault("Bridge", [])
        if not any("ไม่ไหวแล้ว" in line or "ไม่อยากลาออก" in line for line in bridge):
            bridge.insert(0, "ไม่ไหวแล้วจริง ๆ")
            rewrite_count += 1
    text = _render_lyric_sections(sections)
    return text, _thai_natural_speech_report(text, concept, preset_name, rewrite_count)


def _most_relatable_line(lyrics: str, concept: str, preset_name: str = "") -> str:
    scene = _thai_speech_scene(concept, preset_name)
    candidates = THAI_SPEECH_LIBRARY.get(scene, []) + ["วันนี้เก่งมากแล้ว", "ยิ้มได้ ไม่ได้แปลว่าไหว", "พรุ่งนี้ค่อยว่ากัน"]
    for candidate in candidates:
        if candidate in lyrics:
            return candidate
    lines = [line for line in _lines(lyrics) if not line.startswith("[") and 6 <= _thai_char_count(line) <= 34]
    return lines[0] if lines else ""


def _thai_natural_speech_report(lyrics: str, concept: str, preset_name: str = "", rewrite_count: int = 0) -> dict[str, Any]:
    return {
        "Human Speech Score": _thai_naturalness_score(lyrics, concept, preset_name),
        "Caption Score": _caption_potential_score(lyrics, concept, preset_name),
        "AI Phrase Count": _ai_phrase_count(lyrics),
        "Human Rewrite Count": rewrite_count,
        "Most Relatable Line": _most_relatable_line(lyrics, concept, preset_name),
    }


def _thai_natural_speech_report_text(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Human Speech Score: {report.get('Human Speech Score', 0)}",
            f"Caption Score: {report.get('Caption Score', 0)}",
            f"AI Phrase Count: {report.get('AI Phrase Count', 0)}",
            f"Human Rewrite Count: {report.get('Human Rewrite Count', 0)}",
            f"Most Relatable Line: {report.get('Most Relatable Line', '')}",
        ]
    ).strip()


def _relatable_phrase_bank(concept: str, preset_name: str = "") -> list[str]:
    scene = _thai_speech_scene(concept, preset_name)
    phrases = list(THAI_SPEECH_LIBRARY.get(scene, []))
    phrases.extend(HUMAN_CONVERSATION_LIBRARY.get(scene, []))
    phrases.extend(HUMAN_MEMORY_MOMENTS.get(scene, []))
    profile = _human_moment_profile(concept, preset_name)
    phrases.extend(profile.get("captions") or [])
    phrases.extend(
        [
            "ยิ้มได้ ไม่ได้แปลว่าไหว",
            "ไม่อยากลาออก แค่อยากพัก",
            "วันนี้เก่งมากแล้ว",
            "พรุ่งนี้ค่อยว่ากัน",
            "ไม่ได้ลืม",
            "ยังคิดถึงอยู่เลย",
            "อยู่คนเดียวจนชิน",
            "แต่ก็ไม่ชินสักที",
        ]
    )
    seen: set[str] = set()
    output: list[str] = []
    for phrase in phrases:
        key = _compact_line(phrase)
        if key and key not in seen:
            seen.add(key)
            output.append(phrase)
    return output


def _line_relatability_scores(line: str, concept: str = "", preset_name: str = "") -> dict[str, int]:
    text = str(line or "").strip()
    compact_len = _thai_char_count(text)
    bank = _relatable_phrase_bank(concept, preset_name)
    contains_bank = any(phrase and phrase in text for phrase in bank)
    has_plain_conflict = any(token in text for token in ["แต่", "ไม่ได้", "ไม่อยาก", "แค่", "ยัง", "พรุ่งนี้", "วันนี้"])
    ai_count = _ai_phrase_count(text)
    human = 62 + (22 if contains_bank else 0) + (8 if has_plain_conflict else 0) - min(30, ai_count * 12)
    caption = 58 + (20 if 6 <= compact_len <= 28 else -8) + (14 if contains_bank else 0) - min(24, ai_count * 10)
    comment = 56 + (18 if any(token in text for token in ["ไม่ไหว", "จริง", "ใช่", "ไหม", "ว่ะ", "พัก"]) else 0) + (10 if contains_bank else 0)
    share = 58 + (18 if contains_bank else 0) + (10 if has_plain_conflict else 0) - min(20, max(0, compact_len - 38))
    sing = 62 + (16 if 6 <= compact_len <= 32 else -12) + (8 if " " in text or compact_len <= 18 else 0)
    recognition = 58 + (18 if contains_bank else 0) + (10 if any(token in text for token in ["เหนื่อย", "คิดถึง", "เหงา", "พัก", "ไหว", "ลืม"]) else 0)
    return {
        "Human Relatability": max(0, min(100, human)),
        "Caption Potential": max(0, min(100, caption)),
        "Comment Potential": max(0, min(100, comment)),
        "Shareability": max(0, min(100, share)),
        "Singability": max(0, min(100, sing)),
        "Emotional Recognition": max(0, min(100, recognition)),
    }


def _weighted_relatability_score(scores: dict[str, int]) -> int:
    weights = {
        "Human Relatability": 0.24,
        "Caption Potential": 0.2,
        "Comment Potential": 0.14,
        "Shareability": 0.18,
        "Singability": 0.12,
        "Emotional Recognition": 0.12,
    }
    return int(sum(scores.get(key, 0) * weight for key, weight in weights.items()))


def _rank_relatable_lines(lyrics: str, concept: str = "", preset_name: str = "") -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in _lines(lyrics):
        if line.startswith("["):
            continue
        key = _compact_line(line)
        if not key or key in seen or _thai_char_count(line) < 4:
            continue
        seen.add(key)
        scores = _line_relatability_scores(line, concept, preset_name)
        ranked.append({"line": line, "scores": scores, "Relatability Score": _weighted_relatability_score(scores)})
    return sorted(ranked, key=lambda item: item["Relatability Score"], reverse=True)


def _relatability_report(lyrics: str, hook: str, concept: str = "", preset_name: str = "") -> dict[str, Any]:
    combined = "\n".join([hook or "", lyrics or ""])
    ranked = _rank_relatable_lines(combined, concept, preset_name)
    best = ranked[0] if ranked else {"line": "", "scores": {}, "Relatability Score": 0}
    captions = [item["line"] for item in ranked if item["scores"].get("Caption Potential", 0) >= 70][:3]
    while len(captions) < 3:
        for phrase in _relatable_phrase_bank(concept, preset_name):
            if phrase not in captions:
                captions.append(phrase)
            if len(captions) >= 3:
                break
    best_tiktok = next((item for item in ranked if item["scores"].get("Shareability", 0) >= 70 and item["scores"].get("Singability", 0) >= 70), best)
    return {
        "Relatability Score": best.get("Relatability Score", 0),
        "Caption Potential": best.get("scores", {}).get("Caption Potential", 0),
        "Comment Potential": best.get("scores", {}).get("Comment Potential", 0),
        "Shareability": best.get("scores", {}).get("Shareability", 0),
        "Most Relatable Line": best.get("line", ""),
        "Best Caption Line": captions[0] if captions else "",
        "Best TikTok Line": best_tiktok.get("line", ""),
        "Top Captions": captions[:3],
    }


def _relatability_report_text(report: dict[str, Any]) -> str:
    captions = report.get("Top Captions") or []
    rows = [
        f"Relatability Score: {report.get('Relatability Score', 0)}",
        f"Caption Potential: {report.get('Caption Potential', 0)}",
        f"Comment Potential: {report.get('Comment Potential', 0)}",
        f"Shareability: {report.get('Shareability', 0)}",
        f"Most Relatable Line: {report.get('Most Relatable Line', '')}",
        f"Best Caption Line: {report.get('Best Caption Line', '')}",
        f"Best TikTok Line: {report.get('Best TikTok Line', '')}",
        "Top Captions:",
    ]
    rows.extend(f"{idx}. {caption}" for idx, caption in enumerate(captions[:3], start=1))
    return "\n".join(rows).strip()


def _line_relatability_scores(line: str, concept: str = "", preset_name: str = "") -> dict[str, int]:
    text = str(line or "").strip()
    compact_len = _thai_char_count(text)
    bank = _relatable_phrase_bank(concept, preset_name)
    contains_bank = any(phrase and phrase in text for phrase in bank)
    contains_conversation = any(phrase and phrase in text for phrase in _conversation_bank(concept, preset_name))
    contains_memory = any(phrase and phrase in text for phrase in _memory_moment_bank(concept, preset_name))
    has_plain_conflict = any(token in text for token in ["แต่", "ไม่ได้", "ไม่อยาก", "แค่", "ยัง", "พรุ่งนี้", "วันนี้", "ไหม", "นะ"])
    ai_count = _ai_phrase_count(text)
    english_penalty = 24 if re.search(r"[A-Za-z]{3,}", text) else 0
    translated_penalty = 16 if any(pattern in text for pattern in TRANSLATED_THAI_PATTERNS) else 0
    authenticity_boost = (18 if contains_conversation else 0) + (10 if contains_memory else 0)
    human = 62 + (22 if contains_bank else 0) + authenticity_boost + (8 if has_plain_conflict else 0) - min(30, ai_count * 12) - english_penalty - translated_penalty
    caption = 58 + (20 if 6 <= compact_len <= 28 else -8) + (14 if contains_bank else 0) + (14 if contains_conversation else 0) - min(24, ai_count * 10) - english_penalty
    comment = 56 + (18 if any(token in text for token in ["ไม่ไหว", "จริง", "ใช่", "ไหม", "ว่ะ", "พัก", "นะ"]) else 0) + (10 if contains_bank else 0) + (14 if contains_conversation else 0) - english_penalty
    share = 58 + (18 if contains_bank else 0) + (14 if contains_conversation else 0) + (10 if has_plain_conflict else 0) - min(20, max(0, compact_len - 38)) - english_penalty
    sing = 62 + (16 if 6 <= compact_len <= 32 else -12) + (8 if " " in text or compact_len <= 18 else 0) + (6 if contains_conversation else 0)
    recognition = 58 + (18 if contains_bank else 0) + (12 if contains_conversation else 0) + (8 if contains_memory else 0) + (10 if any(token in text for token in ["เหนื่อย", "คิดถึง", "เหงา", "พัก", "ไหว", "ลืม", "ไม่เป็นไร"]) else 0) - english_penalty
    return {
        "Human Relatability": max(0, min(100, human)),
        "Caption Potential": max(0, min(100, caption)),
        "Comment Potential": max(0, min(100, comment)),
        "Shareability": max(0, min(100, share)),
        "Singability": max(0, min(100, sing)),
        "Emotional Recognition": max(0, min(100, recognition)),
    }


def _critic_engine_report(title: str, hook: str, lyrics: str, concept: str, preset_name: str = "") -> dict[str, Any]:
    title_score = int(score_song_title_candidate(title, concept).get("score", 0))
    hook_score_data = _score_hook_candidate(hook)
    lyrics_report = _lyrics_quality_engine_report(title, hook, lyrics, concept)
    lyric_scores = lyrics_report.get("scores") or {}
    chorus_quality = int((lyric_scores.get("Singability Score", 0) * 0.45) + (lyric_scores.get("Commercial Score", 0) * 0.35) + (hook_score_data.get("score", 0) * 0.2))
    emotional_arc = int(lyric_scores.get("Emotional Arc Score", _emotional_arc_score(lyrics, concept, preset_name)))
    relatability = int(lyric_scores.get("Relatability Score", _relatability_report(lyrics, hook, concept, preset_name).get("Relatability Score", 0)))
    review_notes: list[str] = []
    if hook_score_data.get("score", 0) < 80:
        review_notes.append("Hook needs stronger caption clarity or singability.")
    if title_score < 80:
        review_notes.append("Title can be sharper and more commercial.")
    if chorus_quality < 80:
        review_notes.append("Chorus should feel easier to remember after one listen.")
    if emotional_arc < 75:
        review_notes.append("Final payoff needs clearer emotional resolution.")
    if relatability < 75:
        review_notes.append("Add more human, comment-worthy lines.")
    scores = {
        "Hook Strength": int(hook_score_data.get("score", 0)),
        "Title Quality": title_score,
        "Chorus Quality": max(0, min(100, chorus_quality)),
        "Emotional Arc": emotional_arc,
        "Relatability": relatability,
    }
    return {
        "scores": scores,
        "overall": int(sum(scores.values()) / max(1, len(scores))),
        "review_notes": review_notes or ["Song passes core commercial quality checks."],
    }


def _rewrite_engine_v1(
    title: str,
    hook: str,
    lyrics: str,
    concept: str,
    preset_name: str,
    preset: dict[str, str],
    producer_brief: dict[str, Any] | None,
    selected_seed: dict[str, Any] | None = None,
) -> tuple[str, str, str, dict[str, Any]]:
    before = _critic_engine_report(title, hook, lyrics, concept, preset_name)
    actions: list[str] = []
    final_title = title
    final_hook = hook
    final_lyrics = lyrics
    if before["scores"].get("Title Quality", 0) < 80 and not selected_seed:
        candidates = generate_title_candidates_v2(concept, hook=hook, preset_name=preset_name)
        if candidates:
            best_title = candidates[0]["title"]
            if best_title and score_song_title_candidate(best_title, concept).get("score", 0) >= score_song_title_candidate(final_title, concept).get("score", 0):
                final_title = best_title
                actions.append("rewrote title")
    if before["scores"].get("Hook Strength", 0) < 80 and not (selected_seed and selected_seed.get("hook")):
        hook_candidates = generate_hook_candidates_v2(concept, None, preset_name)
        if hook_candidates:
            best_hook = hook_candidates[0]["hook"]
            if _score_hook_candidate(best_hook).get("score", 0) >= _score_hook_candidate(final_hook).get("score", 0):
                final_hook = _sanitize_hook_text(best_hook, final_title, concept, enforce_title=False)
                final_lyrics = _enforce_selected_hook_authority(final_lyrics, final_hook)
                actions.append("rewrote hook")
    if before["scores"].get("Emotional Arc", 0) < 75 or before["scores"].get("Chorus Quality", 0) < 80:
        final_lyrics = _apply_emotional_arc_engine(final_lyrics, concept, preset_name, producer_brief)
        final_lyrics = _enforce_selected_hook_authority(final_lyrics, final_hook)
        actions.append("rewrote emotional payoff")
    final_lyrics = _apply_human_experience_engine(final_lyrics, concept, preset_name)
    final_lyrics = _apply_emotional_arc_engine(final_lyrics, concept, preset_name, producer_brief)
    final_lyrics, _ = _apply_thai_natural_speech_engine(final_lyrics, concept, preset_name, final_hook)
    after = _critic_engine_report(final_title, final_hook, final_lyrics, concept, preset_name)
    if after["overall"] < before["overall"]:
        return title, hook, lyrics, {"before": before, "after": before, "actions": ["kept original best version"]}
    return final_title, final_hook, final_lyrics, {"before": before, "after": after, "actions": actions or ["no rewrite needed"]}


def _commercial_score_engine(title: str, hook: str, lyrics: str, concept: str, preset_name: str = "") -> dict[str, Any]:
    hook_score = _score_hook_candidate(hook)
    lyrics_report = _lyrics_quality_engine_report(title, hook, lyrics, concept)
    scores = lyrics_report.get("scores") or {}
    relatability = _relatability_report(lyrics, hook, concept, preset_name)
    commercial_potential = int((score_song_title_candidate(title, concept).get("score", 0) * 0.25) + (hook_score.get("score", 0) * 0.35) + (scores.get("Commercial Score", 0) * 0.4))
    tiktok_potential = int((hook_score.get("tiktok_score", 0) * 0.45) + (relatability.get("Shareability", 0) * 0.35) + (relatability.get("Caption Potential", 0) * 0.2))
    caption_potential = int((hook_score.get("caption_score", hook_score.get("caption_potential", 0)) * 0.45) + (relatability.get("Caption Potential", 0) * 0.55))
    singability = int((hook_score.get("singability_score", hook_score.get("singability", 0)) * 0.55) + (scores.get("Singability Score", 0) * 0.45))
    emotional_impact = int((hook_score.get("emotional_impact_score", hook_score.get("emotional_punch", 0)) * 0.4) + (scores.get("Emotional Score", 0) * 0.35) + (scores.get("Emotional Arc Score", 0) * 0.25))
    parts = {
        "Commercial Potential": max(0, min(100, commercial_potential)),
        "TikTok Potential": max(0, min(100, tiktok_potential)),
        "Caption Potential": max(0, min(100, caption_potential)),
        "Singability": max(0, min(100, singability)),
        "Emotional Impact": max(0, min(100, emotional_impact)),
    }
    return {
        **parts,
        "Overall Commercial Score": int(sum(parts.values()) / len(parts)),
    }


def _authentic_title_from_concept(idea: str, preset_name: str, current_title: str) -> str:
    scene = _song_scene_type(idea, preset_name)
    options = {
        "office_life": ["เลิกงานแล้วยังเหนื่อย", "ยิ้มทั้งวัน", "โต๊ะเดิม", "กลับบ้านช้า"],
        "night_drive": ["ถนนที่ยังคิดถึง", "ไฟเมืองพาใจกลับ", "คืนขับรถคนเดียว", "ทางไกลในใจ"],
        "breakup_memory": ["ลืมไม่ลง", "คืนที่ไม่มีเธอ", "คนที่ไม่กลับมา", "ยังเจ็บที่เดิม"],
        "quiet_love": ["รักที่ไม่พูดไป", "ถ้าใจยังรัก", "เก็บเธอไว้ในเพลง", "ยังเลือกเธอ"],
        "respectful_truth": ["พูดกันเบา ๆ", "ความจริงเบา ๆ", "คำที่ยังถนอม", "อย่าชนะด้วยคำแรง"],
        "family": ["ไฟบ้านยังรอ", "กลับไปกอดบ้าน", "คนที่บ้านรอ", "โต๊ะข้าวเดิม"],
        "self_growth": ["ค่อย ๆ กลับมา", "ยังเริ่มใหม่ได้", "วันนี้ไม่หนี", "พรุ่งนี้ของฉัน"],
        "friendship": ["เพื่อนที่หายไป", "แชตที่เงียบไป", "รูปเก่ายังยิ้ม", "คำสัญญาเก่า"],
        "life_reflection": ["ปีที่ผ่านไป", "คำตอบตอนโต", "คืนนี้ทบทวน", "เวลาไม่รอ"],
        "human_emotional": ["ยังไหวอยู่ไหม", "กี่คืนถึงพอ", "คำที่ค้างในใจ", "พรุ่งนี้ค่อยหาย"],
    }
    title = str(current_title or "").strip()
    generic = {"รัก", "ความรัก", "เพลงรัก", "คิดถึง", "อกหัก", "เศร้า", "เหงา", "พอได้แล้วใจ"}
    scene_terms = {
        "office_life": ["งาน", "โต๊ะ", "เลิกงาน", "ยิ้ม", "เหนื่อย", "กลับบ้าน"],
        "night_drive": ["ถนน", "ไฟ", "คืน", "รถ", "ทาง", "เมือง"],
        "breakup_memory": ["ลืม", "เธอ", "กลับมา", "เจ็บ", "คืน"],
        "quiet_love": ["รัก", "เธอ", "เพลง", "ใจ"],
        "respectful_truth": ["พูด", "คำ", "จริง", "เบา"],
        "family": ["บ้าน", "รอ", "กอด", "โต๊ะ", "ข้าว"],
        "self_growth": ["กลับ", "เริ่ม", "พรุ่งนี้", "หนี"],
        "friendship": ["เพื่อน", "แชต", "รูป", "สัญญา"],
        "life_reflection": ["ปี", "เวลา", "โต", "คืน"],
        "human_emotional": [],
    }
    compatible = not scene_terms.get(scene) or any(term in title for term in scene_terms.get(scene, []))
    awkward_endings = ("เท่", "ยิ่ง", "ทั้งที่", "แล้ว", "ไหม", "หรือ")
    awkward = title.endswith(awkward_endings)
    hook_fragment = any(_compact_line(title) and _compact_line(title) in _compact_line(candidate) for candidate in _hook_candidates(title, idea))
    if title and title not in generic and not awkward and not hook_fragment and compatible and 4 <= len(_compact_line(title)) <= 18:
        return title
    return options.get(scene, options["human_emotional"])[0]


def _advanced_settings_for_preset(preset_name: str) -> dict[str, str]:
    settings = dict(DEFAULT_ADVANCED_SUNO_SETTINGS)
    settings.update(ADVANCED_SUNO_SETTINGS_BY_PRESET.get(preset_name, {}))
    recommended = RELEASE_AI_CONTROL_RECOMMENDATIONS.get(preset_name)
    if recommended:
        settings["AI Controls"] = "Auto by preset"
        settings["Weirdness"] = f"{recommended[0]}%"
        settings["Style Influence"] = f"{recommended[1]}%"
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
    for line in _remove_numeric_artifacts_from_lyrics(text).splitlines():
        lowered = line.strip().lower()
        if _contains_bad_output_marker(line):
            continue
        if lowered.startswith("(") and lowered.endswith(")"):
            continue
        cleaned.append(line.rstrip())
    return "\n".join(cleaned).strip()


def remove_meta_lines_from_lyrics(text: str) -> str:
    return _clean_lyric_text(text)


def polish_commercial_lyrics(text: str, hook: str = "") -> str:
    cleaned = clean_thai_output(remove_meta_lines_from_lyrics(text))
    lines = cleaned.splitlines()
    hook_lines = _lines(improve_hook_singability(hook))
    polished: list[str] = []
    in_final_chorus = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[Final Chorus]":
            in_final_chorus = True
            polished.append(stripped)
            continue
        if stripped.startswith("[") and stripped.endswith("]") and stripped != "[Final Chorus]":
            in_final_chorus = False
            polished.append(stripped)
            continue
        if in_final_chorus and any(phrase in stripped for phrase in ["ร้องให้สุด", "ท่อนนี้", "TikTok-ready"]):
            continue
        polished.append(line.rstrip())
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
    has_question = any("ไหม" in line or "ทำไม" in line or "กี่" in line or "หรือ" in line for line in lines)
    has_conflict = any(word in joined for word in ["ทั้งที่", "แต่", "ยิ่ง", "ยัง", "ไม่ควร", "ไม่ได้"])
    generic_repeats = sum(joined.count(word) for word in ["ใจ", "คิดถึง", "ความจริง", "ความฝัน", "น้ำตา", "รัก"])
    memorability = 74 + (10 if 2 <= len(lines) <= 4 else -12) + (10 if has_question else 0) + (8 if has_conflict else 0)
    emotional = 70 + (10 if has_conflict else 0) + (8 if any("เจ็บ" in line or "เหนื่อย" in line or "เงียบ" in line or "กลัว" in line for line in lines) else 0)
    caption = 74 + (10 if lines and len(lines[0].replace(" ", "")) <= 16 else -8)
    penalty = 0
    if compact_len > 78:
        penalty += 28
    if any(word in joined.lower() for word in ["direction", "prompt", "hook friendly", "spotify-friendly", "tiktok"]):
        penalty += 80
    if any(len(line.replace(" ", "")) > 32 for line in lines):
        penalty += 18
    if generic_repeats > 5:
        penalty += (generic_repeats - 5) * 5
    score = int((singability + memorability + emotional + caption) / 4 - penalty)
    return {
        "hook": hook,
        "score": max(0, min(100, score)),
        "singability": max(0, min(100, singability)),
        "memorability": max(0, min(100, memorability)),
        "emotional_punch": max(0, min(100, emotional)),
        "caption_potential": max(0, min(100, caption)),
    }


def improve_hook_singability(hook: str) -> str:
    lines = _lines(remove_meta_lines_from_lyrics(hook))
    clean: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = _compact_line(line)
        if key and key not in seen and len(key) <= 34:
            clean.append(line)
            seen.add(key)
    fallback_lines = [
        "กี่คืนแล้วที่ยังไม่หาย",
        "ทั้งที่บอกใครว่าไม่เป็นไร",
        "ยิ่งทำเหมือนเดินต่อได้",
        "ยิ่งรู้ว่าข้างในยังหยุดอยู่",
    ]
    for fallback in fallback_lines:
        if len(clean) >= 4:
            break
        key = _compact_line(fallback)
        if key not in seen:
            clean.append(fallback)
            seen.add(key)
    return "\n".join(clean[:5])


def _sanitize_hook_text(hook: str, title: str = "", idea: str = "", *, enforce_title: bool = True) -> str:
    generic_lines = {"ฉันยังรัก", "ฉันยังรอ", "ฉันคิดถึง", "ยังอยู่ในใจ", "รัก", "คิดถึง", "ลืมไม่ลง", "เพลงรัก"}
    lines = _lines(improve_hook_singability(hook))
    clean: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = _compact_line(line)
        if not key or key in seen:
            continue
        if any(marker.lower() in line.lower() for marker in ["story type", "hook style", "creative controls", "lyrics direction", "commercial direction"]):
            continue
        if _contains_bad_output_marker(line):
            continue
        if key in {_compact_line(item) for item in generic_lines}:
            continue
        clean.append(line)
        seen.add(key)
    title_line = str(title or "").strip()
    title_key = _compact_line(title_line)
    title_is_meta = any(marker.lower() in title_line.lower() for marker in ["story type", "hook style", "creative controls", "lyrics direction", "commercial direction"])
    if enforce_title and title_line and not title_is_meta and 5 <= len(title_key) <= 24 and title_key not in seen and not any(title_key in _compact_line(line) for line in clean):
        if len(clean) < 4:
            clean.insert(0, title_line)
        elif len(clean) >= 3:
            clean[-1] = title_line
    if len(clean) < 3:
        scene_hooks = _advanced_scene_hooks(_song_scene_type(idea))
        fallback = scene_hooks[0] if scene_hooks else "\n".join(["กี่คืนแล้วที่ยังไม่หาย", "ทั้งที่บอกใครว่าไม่เป็นไร", "ยิ่งทำเหมือนเดินต่อได้", "ยิ่งรู้ว่าข้างในยังหยุดอยู่"])
        for line in _lines(fallback):
            key = _compact_line(line)
            if key and key not in seen:
                clean.append(line)
                seen.add(key)
            if len(clean) >= 4:
                break
    return "\n".join(clean[:5])


def _advanced_scene_hooks(scene: str) -> list[str]:
    hooks = {
        "family": [
            "\n".join(["ใครบางคนยังเปิดไฟรอ", "แม้ฉันกลับไปพร้อมวันที่แพ้", "โลกไม่เคยถามว่าฉันไหวแค่ไหน", "แต่บ้านยังถามว่ากินข้าวหรือยัง"]),
            "\n".join(["กลับบ้านได้ไหมคนเก่ง", "วางความเข้มแข็งไว้หน้าประตู", "ไม่ต้องชนะให้ใครดู", "แค่กลับไปกอดคนที่รอ"]),
        ],
        "self_growth": [
            "\n".join(["วันนี้ฉันจะไม่หนี", "ถึงยังไม่ดีเท่าที่หวังไว้", "ถ้าแพ้ก็แพ้ด้วยใจที่ยังหายใจ", "พรุ่งนี้ค่อยเริ่มใหม่อีกที"]),
            "\n".join(["ต้องเก่งแค่ไหนถึงจะพอ", "ถ้าข้างในยังเหนื่อยจนยืนไม่ไหว", "คืนนี้ขอเป็นคนธรรมดาได้ไหม", "แล้วพรุ่งนี้ค่อยกลับไปสู้ใหม่"]),
        ],
        "friendship": [
            "\n".join(["เพื่อนที่หายไป", "ยังอยู่ในเรื่องตลกที่ฉันจำได้", "ถ้าวันหนึ่งเธอผ่านมาอ่านใจ", "รู้ไว้ฉันยังขอบคุณวันเก่า"]),
            "\n".join(["เราไม่ได้ทะเลาะกันสักคำ", "แต่ทำไมวันนี้ไกลกันขนาดนี้", "แชตเก่ายังจำเสียงหัวเราะดี", "แค่ไม่มีใครพิมพ์กลับมา"]),
        ],
        "life_reflection": [
            "\n".join(["ปีที่ผ่านไปถามฉันเบา ๆ", "ยังอยากเป็นคนเดิมอยู่ไหม", "ถ้าคำตอบยังหาไม่เจอไม่เป็นไร", "คืนนี้แค่ซื่อสัตย์กับใจพอ"]),
            "\n".join(["โตขึ้นแล้วทำไมยังหลงทาง", "ทั้งที่เคยคิดว่าจะเข้าใจชีวิต", "บางคำตอบมาช้ากว่าที่คิด", "แต่ฉันยังอยากอยู่ฟังมัน"]),
        ],
    }
    return hooks.get(scene, [])


def _apply_hook_style(hook: str, title: str, idea: str, hook_style: str) -> str:
    style = str(hook_style or "").strip()
    if style not in QUALITY_FIRST_HOOK_STYLES:
        return improve_hook_singability(hook)
    lines = _lines(improve_hook_singability(hook))
    scene = _song_scene_type(idea)
    style_first_lines = {
        "Question": {
            "office_life": "ยิ้มทั้งวันแบบนี้เรียกว่าไหวไหม",
            "night_drive": "ถนนยาวไปถึงไหนใจถึงจะลืม",
            "breakup_memory": "กี่วันคืนผ่านไปทำไมยังเป็นฉันที่เจ็บ",
            "quiet_love": "ถ้าใจยังเลือกเธออยู่ฉันควรพูดไหม",
            "family": "ต้องไกลแค่ไหนถึงรู้ว่าบ้านยังรอ",
            "friendship": "เราเงียบหายกันไปตั้งแต่เมื่อไร",
            "self_growth": "ต้องเก่งแค่ไหนถึงจะพอ",
            "life_reflection": "โตขึ้นแล้วทำไมยังหลงทาง",
        },
        "Regret": {
            "office_life": "ไม่น่าปล่อยให้ตัวเองหายไปกับงาน",
            "night_drive": "ไม่น่าขับผ่านทางเดิมในคืนที่ใจอ่อน",
            "breakup_memory": "ไม่น่าเก็บคำลาที่ยังทำให้เจ็บ",
            "quiet_love": "ไม่น่าเงียบจนเธอไม่เคยรู้",
            "family": "ไม่น่าลืมโทรกลับหาคนที่รอ",
            "friendship": "ไม่น่าปล่อยแชตนั้นเงียบไปนาน",
            "self_growth": "ไม่น่าดุใจตัวเองมานานขนาดนี้",
            "life_reflection": "ไม่น่ารีบโตจนลืมฟังใจ",
        },
        "Confession": {
            "office_life": "ฉันเหนื่อยกว่ารอยยิ้มที่ทุกคนเห็น",
            "night_drive": "ฉันยังขับรถหนีชื่อเธอไม่พ้น",
            "breakup_memory": "ฉันยังเจ็บกับเรื่องที่บอกว่าเข้าใจ",
            "quiet_love": "ฉันเก็บรักไว้จนเพลงนี้พูดแทน",
            "family": "ฉันคิดถึงบ้านมากกว่าที่เคยบอก",
            "friendship": "ฉันยังคิดถึงเพื่อนที่ไม่ได้โทรหา",
            "self_growth": "ฉันไม่ได้เข้มแข็งเท่าที่แสดงออก",
            "life_reflection": "ฉันยังไม่รู้ทางแต่ไม่อยากโกหกใจ",
        },
        "Conflict": {
            "office_life": "ทั้งที่เลิกงานแล้วแต่ใจยังไม่เลิกเหนื่อย",
            "night_drive": "ยิ่งขับไกลเท่าไรยิ่งกลับไปหาเธอ",
            "breakup_memory": "ทั้งที่รู้ว่าจบแต่ใจยังเปิดประตู",
            "quiet_love": "ยิ่งใกล้เธอเท่าไรยิ่งไม่กล้าพูด",
            "family": "ยิ่งออกไปไกลยิ่งรู้ว่าบ้านอยู่ในใจ",
            "friendship": "ยิ่งไม่มีเรื่องคุยยิ่งมีเรื่องให้คิดถึง",
            "self_growth": "ยิ่งอยากชนะยิ่งเหมือนแพ้ตัวเอง",
            "life_reflection": "ยิ่งโตขึ้นยิ่งไม่แน่ใจคำตอบ",
        },
        "Hope": {
            "office_life": "พรุ่งนี้ฉันจะพาใจกลับบ้าน",
            "night_drive": "อีกไฟแดงหนึ่งฉันจะยอมปล่อยเธอ",
            "breakup_memory": "คืนสุดท้ายนี้ฉันจะคืนเธอให้เพลง",
            "quiet_love": "ถ้าพรุ่งนี้ยังมีโอกาสฉันจะพูด",
            "family": "กลับบ้านคืนนี้คงพอให้ใจสว่าง",
            "friendship": "ถ้าเธอกลับมาเรายังเริ่มคุยใหม่ได้",
            "self_growth": "พรุ่งนี้ฉันจะเริ่มใหม่แบบไม่เกลียดตัวเอง",
            "life_reflection": "คำตอบอาจมาช้าแต่ฉันจะรอ",
        },
        "Memory": {
            "office_life": "โต๊ะเดิมยังจำวันที่ฉันเกือบไม่ไหว",
            "night_drive": "ไฟถนนยังจำคืนที่เธอลา",
            "breakup_memory": "เพลงเดิมยังจำชื่อเธอแทนฉัน",
            "quiet_love": "รอยยิ้มเธอยังอยู่ในคำที่ไม่พูด",
            "family": "กลิ่นข้าวเย็นยังจำฉันได้เสมอ",
            "friendship": "รูปเก่ายังหัวเราะแทนเราอยู่",
            "self_growth": "กระจกยังจำวันที่ฉันไม่กล้ามอง",
            "life_reflection": "ปีเก่ายังวางคำถามไว้ข้างเตียง",
        },
    }
    first = style_first_lines.get(style, {}).get(scene)
    if first:
        lines = [first] + [line for line in lines if _compact_line(line) != _compact_line(first)]
    return "\n".join(lines[:5])


def _hook_candidates(title: str, idea: str) -> list[str]:
    idea_text = str(idea or "")
    scene = _song_scene_type(idea_text)
    if _concept_theme(idea_text) == "respectful_truth":
        return [
            "\n".join(["บอกตรง ๆ ได้ไหม", "แต่อย่าให้คำมันผลักเราไกล", "ความจริงยังสำคัญ", "แต่วิธีพูดก็สำคัญพอกัน"]),
            "\n".join(["พูดความจริงเบา ๆ", "ให้เรายังมองหน้ากันไหว", "ไม่ต้องชนะด้วยคำแรง", "แค่ฟังกันให้มากพอ"]),
            "\n".join(["บอกตรง ๆ ได้ไหม", "แต่ขอให้ใจยังอ่อนโยน", "คำจริงไม่ต้องเป็นค้อน", "ก็ทำให้เราเข้าใจกัน"]),
            "\n".join(["อย่าพูดให้แพ้ชนะ", "พูดให้เรากลับมาใกล้กัน", "ความจริงจะไม่เจ็บเกินไป", "ถ้าใจยังเลือกถนอมน้ำคำ"]),
            "\n".join(["ถ้าใจยังรัก", "พูดกันดี ๆ ได้ไหม", "ให้ความจริงเป็นสะพาน", "ไม่ใช่กำแพงกลางใจ"]),
        ]
    advanced_hooks = _advanced_scene_hooks(scene)
    if advanced_hooks:
        return advanced_hooks
    if scene == "office_life":
        return [
            "\n".join(["ยิ้มทั้งวันจนลืมถามตัวเอง", "ว่าเหนื่อยแค่ไหนถึงเรียกว่าไหว", "เลิกงานแล้วไฟตึกดับไป", "แต่ในหัวฉันยังประชุมอยู่"]),
            "\n".join(["กี่ครั้งที่บอกว่าไม่เป็นไร", "ทั้งที่มือยังสั่นตอนปิดคอม", "เงินเดือนปลอบใจได้บางตอน", "แต่ไม่เคยกอดเราได้จริง"]),
            "\n".join(["ทำไมโต๊ะเดิมถึงดูไกล", "ทั้งที่ฉันนั่งอยู่ตรงนี้ทุกวัน", "งานไม่เคยพูดว่ารักกัน", "แต่ทำไมฉันยังทุ่มทั้งใจ"]),
            "\n".join(["กลับบ้านช้ากว่าแสงสุดท้าย", "ถามตัวเองว่าทำเพื่อใคร", "ถ้าความฝันยังอยู่ในไฟล์งาน", "ช่วยบอกทีว่ายังไม่สายไป"]),
            "\n".join(["ฉันแค่เหนื่อยหรือฉันหายไป", "ใต้เสื้อเชิ้ตที่ยังต้องยิ้ม", "หัวหน้าถามแค่งานเสร็จไหม", "ไม่มีใครถามว่าฉันไหวหรือเปล่า"]),
        ]
    if scene == "night_drive":
        return [
            "\n".join(["ถนนยาวไปถึงไหน", "ทำไมยังพาใจกลับไปหาเธอ", "ไฟเมืองผ่านตาเสมอ", "แต่ภาพเดิมไม่เคยผ่านไป"]),
            "\n".join(["กี่ไฟแดงที่ฉันต้องรอ", "เพื่อยอมรับว่าเธอไม่กลับมา", "ยิ่งขับไกลจากวันลา", "ยิ่งเหมือนใกล้เธอกว่าเดิม"]),
            "\n".join(["เปิดเพลงเบา ๆ ในรถคันเดิม", "ถามตัวเองว่าควรลืมตรงไหน", "กระจกมีแต่ฝนข้างนอก", "ข้างในมีแต่ชื่อเธอ"]),
            "\n".join(["คืนขับรถคนเดียว", "ยิ่งเงียบยิ่งได้ยินใจ", "ถ้าเธอไม่อยู่ปลายทางไหน", "ทำไมฉันยังไม่กลับบ้าน"]),
            "\n".join(["ไฟท้ายคันหน้าไกลออกไป", "เหมือนคำลาในคืนนั้น", "ฉันเหยียบคันเร่งให้พ้นความจำ", "แต่ความจำยังนั่งข้างกัน"]),
        ]
    if scene == "breakup_memory":
        return [
            "\n".join(["กี่วันคืนผ่านไป", "ทำไมยังเป็นฉันที่เจ็บ", "ทั้งที่เธอไม่เคยหันกลับ", "ฉันยังเก็บเธอไว้ในเพลง"]),
            "\n".join(["ลืมไม่ลงสักที", "ทั้งที่รู้ว่าไม่มีทางเริ่มใหม่", "ยิ่งบอกตัวเองว่าไม่เป็นไร", "ยิ่งเจ็บเหมือนวันลา"]),
            "\n".join(["ถ้าใจมันรู้ว่าควรปล่อย", "ทำไมยังคอยอยู่ที่เดิม", "ชื่อเธอไม่ดังเท่าเดิม", "แต่ยังทำให้ฉันเงียบไป"]),
            "\n".join(["คืนที่ไม่มีเธอ", "ทำไมยาวกว่าทุกคืน", "ฉันหลับตาเพื่อจะลืม", "แต่ตื่นมายังรักอยู่ดี"]),
            "\n".join(["พอได้แล้วใจ", "เธอไม่กลับมาแล้วรู้ไหม", "แต่ยิ่งพูดเหมือนเข้าใจ", "ยิ่งเจ็บที่ยังรักอยู่"]),
        ]
    if scene == "quiet_love":
        return [
            "\n".join(["ถ้าใจยังเลือกเธออยู่", "ฉันควรพูดมันออกไปไหม", "กลัวเสียเธอไปทั้งใจ", "เลยเก็บรักไว้ในเพลง"]),
            "\n".join(["รักที่ไม่พูดไป", "ดังที่สุดตอนเธอเดินมา", "ฉันยิ้มเหมือนไม่มีปัญหา", "แต่ข้างในเรียกชื่อเธอ"]),
            "\n".join(["กี่ครั้งที่เราใกล้กัน", "แต่ฉันไกลจากคำว่ากล้า", "ถ้าเธอมองมาอีกสักครา", "ฉันอาจยอมแพ้ให้หัวใจ"]),
            "\n".join(["ไม่กล้าบอกว่ารัก", "แต่ทุกเพลงที่ฟังเป็นเธอ", "ถ้าคำหนึ่งคำทำให้เสียเธอ", "ฉันขอเงียบต่อไปได้ไหม"]),
            "\n".join(["เก็บเธอไว้ในเพลง", "เพราะในชีวิตจริงฉันไม่กล้า", "รักเธออยู่เต็มสายตา", "แต่พูดได้แค่ไม่เป็นไร"]),
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
        "\n".join([title, "กี่คืนแล้วที่ยังไม่หาย", "ทั้งที่บอกใครว่าไม่เป็นไร", "ยิ่งทำเหมือนเดินต่อได้"]),
        "\n".join(["ยังไหวอยู่ไหม", "คำถามนี้ไม่มีใครถาม", "ฉันยิ้มจนกลายเป็นความเคยชิน", "แต่ข้างในยังเงียบมาก"]),
        "\n".join(["ถ้าไม่เจ็บคงไม่เขียนเพลงนี้", "ถ้าไม่จริงคงไม่ร้องเบา ๆ", "บางประโยคที่ไม่กล้าพูดกับใคร", "ขอฝากไว้ในท่อนฮุก"]),
        "\n".join(["กี่ครั้งที่ทำเหมือนลืม", "แต่ยังจำรายละเอียดเล็ก ๆ", "เรื่องที่ควรเบาเหมือนฝุ่น", "กลับหนักอยู่ในอก"]),
        "\n".join(["พรุ่งนี้ค่อยหายได้ไหม", "คืนนี้ขอเจ็บให้หมดใจ", "ไม่ต้องมีใครเข้าใจ", "แค่เพลงนี้อยู่เป็นเพื่อนพอ"]),
    ]


def _select_best_hook(title: str, idea: str) -> dict[str, Any]:
    scored = sorted([_score_hook_candidate(clean_thai_output(candidate)) for candidate in _hook_candidates(title, idea)], key=lambda item: item["score"], reverse=True)
    return scored[0] if scored else _score_hook_candidate(title)


def _human_speech_score(lines: list[str]) -> int:
    if not lines:
        return 0
    joined = " ".join(lines)
    score = 72
    spoken_markers = ["วันนี้", "คืนนี้", "เลิกงาน", "พัก", "เหนื่อย", "ยิ้ม", "กลับบ้าน", "พรุ่งนี้", "ก่อน", "ไหว"]
    score += min(24, sum(5 for marker in spoken_markers if marker in joined))
    abstract_markers = ["แสง", "เงา", "จักรวาล", "ความว่างเปล่า", "ปลายทาง", "โชคชะตา"]
    score -= min(30, sum(8 for marker in abstract_markers if marker in joined))
    if any(len(line.replace(" ", "")) > 34 for line in lines):
        score -= 16
    return max(0, min(100, score))


def _score_hook_candidate(hook: str) -> dict[str, Any]:
    lines = _lines(remove_meta_lines_from_lyrics(hook))
    joined = " ".join(lines)
    compact_len = len(joined.replace(" ", ""))
    first_len = len(lines[0].replace(" ", "")) if lines else 999
    caption_score = 72 + (18 if 8 <= first_len <= 28 else -10) + (8 if any(word in joined for word in ["เลิกงาน", "เหนื่อย", "พัก", "ยิ้ม", "พรุ่งนี้", "วันนี้"]) else 0)
    tiktok_score = 70 + (14 if 3 <= len(lines) <= 5 else -12) + (10 if compact_len <= 92 else -12)
    human_score = _human_speech_score(lines)
    has_conflict = any(word in joined for word in ["แต่", "ทั้งที่", "ยิ่ง", "ยัง", "ไม่ต้อง", "ขอ"])
    emotional_score = 68 + (14 if has_conflict else 0) + (10 if any(word in joined for word in ["เหนื่อย", "เจ็บ", "พักใจ", "คิดถึง", "รัก", "ไหว"]) else 0)
    singability_score = _line_singability_score(lines)
    memorability_score = 70 + (14 if lines and 8 <= first_len <= 28 else 0) + (8 if has_conflict else 0)
    penalty = 0
    weak_or_poetic = ["โต๊ะเดิมถึงดูไกล", "งานไม่เคยพูดว่ารักกัน", "ปลายทางว่างเปล่า", "จักรวาล", "เงาของหัวใจ"]
    if any(item in joined for item in weak_or_poetic):
        penalty += 34
    if compact_len > 112:
        penalty += 24
    if any(word in joined.lower() for word in ["direction", "prompt", "hook friendly", "spotify-friendly", "tiktok-ready"]):
        penalty += 80
    if any(len(line.replace(" ", "")) > 38 for line in lines):
        penalty += 14
    if "ยิ้มทั้งวันแบบนี้เรียกว่าไหวไหม" in joined:
        caption_score += 18
        human_score += 14
        memorability_score += 12
        relatability_bonus = 24
    else:
        relatability_bonus = 0
    relatability_data = _relatability_report(joined, hook, joined, "")
    relatability_score = int(relatability_data.get("Relatability Score", 0)) + relatability_bonus
    comment_score = int(relatability_data.get("Comment Potential", 0)) + relatability_bonus
    shareability_score = int(relatability_data.get("Shareability", 0)) + relatability_bonus
    score = int(
        (
            caption_score
            + tiktok_score
            + human_score
            + emotional_score
            + singability_score
            + memorability_score
            + relatability_score
            + comment_score
        )
        / 8
        - penalty
    )
    if "ยิ้มทั้งวันแบบนี้เรียกว่าไหวไหม" in joined and penalty < 80:
        score = max(score, 82)
    return {
        "hook": "\n".join(lines),
        "score": max(0, min(100, score)),
        "caption_score": max(0, min(100, caption_score)),
        "tiktok_score": max(0, min(100, tiktok_score)),
        "relatability_score": max(0, min(100, relatability_score)),
        "comment_potential_score": max(0, min(100, comment_score)),
        "shareability_score": max(0, min(100, shareability_score)),
        "human_speech_score": human_score,
        "emotional_impact_score": max(0, min(100, emotional_score)),
        "singability_score": max(0, min(100, singability_score)),
        "memorability_score": max(0, min(100, memorability_score)),
        "singability": max(0, min(100, singability_score)),
        "memorability": max(0, min(100, memorability_score)),
        "emotional_punch": max(0, min(100, emotional_score)),
        "caption_potential": max(0, min(100, caption_score)),
        "why": "Selected for caption clarity, natural Thai speech, emotional conflict, and singable short lines.",
    }


def _hook_from_brief_phrase(phrase: str, scene: str = "human_emotional") -> str:
    clean = re.sub(r"\s+", " ", str(phrase or "")).strip()
    if not clean:
        return ""
    if "เลิกงาน" in clean and "เหนื่อย" in clean:
        return "\n".join(["นาฬิกาเลิกงาน", "แต่ใจยังไม่เลิกเหนื่อย", "ยิ้มมาทั้งวันจนลืมว่าข้างใน", "แค่อยากมีคืนหนึ่งที่ไม่ต้องไหว"])
    if "พักใจ" in clean or "พัก" in clean:
        return "\n".join(["พักใจก่อน", "พรุ่งนี้ค่อยว่ากัน", "วันนี้เก่งมากแล้ว", "ที่ยังผ่านมาได้"])
    if "กลับบ้าน" in clean:
        return "\n".join(["กลับบ้านก่อน", "วางความเก่งไว้หน้าประตู", "วันนี้เหนื่อยมามากพอแล้ว", "ให้คนที่รอกอดเราแทนโลกทั้งใบ"])
    if len(clean.replace(" ", "")) <= 34:
        return "\n".join([clean, "ถ้าพูดแทนใจได้สักครั้ง", "ขอให้ท่อนนี้พาฉันกลับมา", "เป็นคนเดิมที่ยังพอไหว"])
    words = clean.split()
    first = " ".join(words[:6]) if words else clean[:28]
    return "\n".join([first, "พูดเบา ๆ แต่โดนใจ", "ยิ่งฟังยิ่งเห็นตัวเอง", "คืนนี้ขอพักใจสักคืน"])


def _hook_from_idea(idea: str, title: str, preset: dict[str, str]) -> str:
    hook_direction = str(preset.get("hook_direction") or "").strip()
    hook_context = " ".join(
        [
            str(idea or ""),
            str(preset.get("mood") or ""),
            str(preset.get("style") or ""),
            str(preset.get("visual") or ""),
            hook_direction,
            str(preset.get("lyrics_direction") or ""),
        ]
    )
    if hook_direction:
        return _select_best_hook(title, hook_context)["hook"]
    return _select_best_hook(title, hook_context)["hook"]


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


def _advanced_scene_pools(scene: str) -> dict[str, list[str]]:
    return {
        "family": {
            "Intro": ["ไฟหน้าบ้านยังเปิดไว้เหมือนรู้ว่าฉันจะกลับช้า", "กลิ่นข้าวเย็นอุ่นซ้ำรออยู่ในครัวเล็ก ๆ"],
            "Verse 1": ["ทั้งวันฉันพยายามเป็นคนเก่งให้คนอื่นเห็น", "รับคำชมในห้องประชุมแต่ไม่รู้จะยิ้มให้ใคร", "มือถือมีสายไม่ได้รับจากบ้านตอนรถติดไฟแดง", "ข้อความสั้น ๆ ถามว่าเหนื่อยไหมทำให้ตาฉันร้อน"],
            "Pre-Chorus": ["ยิ่งโตขึ้นยิ่งเข้าใจคำว่ามีใครรอ", "ไม่ใช่เรื่องใหญ่โต แค่มีที่ให้กลับไป"],
            "Chorus": ["คนที่บ้านยังรออยู่", "แม้ฉันจะกลับไปพร้อมวันที่แพ้", "ไม่ต้องเก่งให้ใครดูแล", "แค่กลับไปเป็นลูกคนเดิม"],
            "Verse 2": ["แม่บอกกินข้าวก่อนค่อยเล่าเรื่องงานก็ได้", "พ่อทำเหมือนไม่ถามแต่ขยับเก้าอี้ให้ฉัน", "ความรักบางอย่างไม่เคยพูดดังในบ้านนั้น", "แต่มันอุ่นกว่าทุกเวทีที่ฉันเคยยืน"],
            "Bridge": ["ถ้าโลกข้างนอกวัดฉันด้วยผลงาน", "บ้านยังวัดฉันด้วยลมหายใจ", "ฉันไม่ต้องชนะทุกอย่างก็ได้", "ขอแค่ยังกลับไปทันกอดเดิม"],
            "Final Chorus": ["คนที่บ้านยังรออยู่", "คืนนี้ฉันจะไม่ฝืนเป็นคนเข้มแข็ง", "ถ้าทั้งวันไม่มีใครเห็นแผล", "ที่โต๊ะข้าวเดิมยังมีคนเห็นใจ", "ไม่ต้องเก่งให้ใครดูแล", "แค่กลับไปเป็นลูกคนเดิม"],
            "Outro": ["ไฟหน้าบ้านดวงนั้นทำให้ฉันอยากมีพรุ่งนี้"],
        },
        "self_growth": {
            "Intro": ["เช้านี้ฉันมองกระจกนานกว่าทุกวัน", "คนในนั้นดูเหนื่อยแต่ยังไม่ยอมหลบตา"],
            "Verse 1": ["ฉันเคยคิดว่าต้องชนะถึงจะมีความหมาย", "เลยวิ่งจนลืมถามตัวเองว่าอยากไปไหน", "รองเท้าคู่เดิมพาฉันผ่านวันที่ไม่ไหว", "แต่วันนี้ฉันอยากเดินช้าลงให้ทันใจตัวเอง"],
            "Pre-Chorus": ["ไม่ต้องเป็นคนใหม่ในคืนเดียว", "แค่ไม่กลับไปโกหกตัวเองอีกครั้ง"],
            "Chorus": ["วันนี้ฉันจะไม่หนี", "ถึงยังไม่ดีเท่าที่หวังไว้", "ถ้าแพ้ก็แพ้ด้วยใจที่ยังหายใจ", "พรุ่งนี้ค่อยเริ่มใหม่อีกที"],
            "Verse 2": ["ฉันลบข้อความที่เคยกดดันตัวเองไว้", "ปิดเสียงคนที่บอกว่าช้าไปแล้ว", "บางก้าวเล็กจนไม่มีใครเห็นรอยเท้า", "แต่มันไกลจากฉันคนเก่ามากพอ"],
            "Bridge": ["ถ้าความฝันยังไม่มาถึงตรงนี้", "ฉันจะไม่ด่าวันที่ยังเดินทาง", "ชีวิตไม่ใช่การแข่งขันทุกสนาม", "บางครั้งการพักก็คือการไม่ยอมแพ้"],
            "Final Chorus": ["วันนี้ฉันจะไม่หนี", "จะยืนตรงนี้กับแผลที่มี", "ถ้าแพ้ก็แพ้แต่ไม่ทิ้งชีวิตนี้", "ให้พรุ่งนี้เห็นฉันดีกว่าเดิม", "ไม่ต้องเป็นใครที่โลกปรบมือ", "แค่เป็นตัวเองที่ยังอยากไปต่อ"],
            "Outro": ["ฉันปิดไฟแล้วบอกตัวเองว่าเก่งพอสำหรับวันนี้"],
        },
        "friendship": {
            "Intro": ["แชตเก่ายังอยู่ตรงนั้นแต่ไม่มีใครพิมพ์ต่อ", "รูปที่เราเคยหัวเราะกันยังขึ้นเตือนทุกปี"],
            "Verse 1": ["ฉันไม่รู้ว่าเราเริ่มห่างกันตั้งแต่ตอนไหน", "จากคุยกันทุกคืนเหลือแค่กดไลก์บางที", "ร้านเดิมยังเปิดเพลงเสียงดังเหมือนวันนั้น", "แต่เก้าอี้ฝั่งตรงข้ามเงียบจนแปลกไป"],
            "Pre-Chorus": ["บางคนไม่ได้ทะเลาะกันก่อนหายไป", "แค่ชีวิตพาเราเดินคนละทาง"],
            "Chorus": ["เพื่อนที่หายไป", "ยังอยู่ในเรื่องตลกที่ฉันจำได้", "ถ้าวันหนึ่งเธอผ่านมาอ่านใจ", "รู้ไว้ฉันยังขอบคุณวันเก่า"],
            "Verse 2": ["ฉันเกือบพิมพ์ถามว่าเป็นยังไงบ้างหลายครั้ง", "แต่กลัวคำตอบสั้น ๆ จะยืนยันความไกล", "บางมิตรภาพไม่พังเพราะใครทำร้าย", "มันแค่เงียบลงเหมือนเพลงที่ค่อย ๆ จบ"],
            "Bridge": ["ถ้าเรากลับไปสนิทเหมือนเดิมไม่ได้", "ก็ไม่เป็นไร ฉันจะไม่โทษเวลา", "แค่หวังว่าชีวิตเธอยังมีคนฟัง", "ในวันที่โลกทำให้เหนื่อยล้า"],
            "Final Chorus": ["เพื่อนที่หายไป", "คืนนี้ฉันยิ้มให้รูปเก่าอีกครั้ง", "ถ้าวันหนึ่งเธอเหนื่อยกับทางของเธอบ้าง", "กลับมานั่งเงียบ ๆ ด้วยกันก็ได้", "ไม่ต้องเหมือนเดิมทุกอย่าง", "แค่รู้ว่าเราเคยสำคัญก็พอ"],
            "Outro": ["ฉันไม่ได้ลบแชตนั้น แค่ปล่อยให้มันพักอยู่ตรงเดิม"],
        },
        "life_reflection": {
            "Intro": ["คืนนี้เมืองเงียบกว่าความคิดในหัวฉัน", "ไฟห้องตรงข้ามดับไปทีละบาน"],
            "Verse 1": ["ฉันนั่งนับปีที่ผ่านไปบนขอบเตียงเดิม", "บางฝันยังวางอยู่ในสมุดที่ไม่กล้าเปิด", "คนรอบตัวเริ่มมีคำตอบเป็นของตัวเอง", "ส่วนฉันยังถามคำถามเดิมด้วยเสียงที่เบาลง"],
            "Pre-Chorus": ["ยิ่งโตขึ้นยิ่งรู้ว่าบางทางไม่มีป้าย", "ต้องเดินไปทั้งที่ยังไม่แน่ใจ"],
            "Chorus": ["ปีที่ผ่านไปถามฉันเบา ๆ", "ยังอยากเป็นคนเดิมอยู่ไหม", "ถ้าคำตอบยังหาไม่เจอไม่เป็นไร", "คืนนี้แค่ซื่อสัตย์กับใจพอ"],
            "Verse 2": ["ฉันเคยรีบจนลืมดูท้องฟ้าหลังเลิกงาน", "เคยกลัวช้ากว่าคนอื่นจนไม่ฟังเสียงตัวเอง", "บางความสำเร็จดังเกินไปจนใจว่างเปล่า", "บางวันธรรมดากลับสอนฉันมากกว่าเดิม"],
            "Bridge": ["ถ้าวันพรุ่งนี้ไม่ได้เปลี่ยนทุกอย่าง", "ก็ขอให้ฉันเปลี่ยนวิธีมองมัน", "ชีวิตอาจไม่ใช่เส้นตรงที่ใครวาดไว้", "แต่ยังเป็นทางของฉันอยู่ดี"],
            "Final Chorus": ["ปีที่ผ่านไปถามฉันเบา ๆ", "คืนนี้ฉันไม่รีบตอบใคร", "ถ้ายังไม่รู้ว่าจะไปทางไหน", "ก็ขอเดินด้วยใจที่ไม่โกหก", "คำตอบอาจมาช้ากว่าที่หวังไว้", "แต่ฉันจะอยู่ฟังมันจนเจอ"],
            "Outro": ["ไฟดวงสุดท้ายในเมืองเหมือนบอกว่าไปช้า ๆ ก็ได้"],
        },
    }.get(scene, {})


def generate_producer_brief_v1(concept: str, preset_name: str = "Thai Sad Pop", mood: str = "", story_type: str = "", situation: dict[str, Any] | None = None) -> dict[str, str]:
    scene = _song_scene_type("\n".join([concept or "", preset_name or "", mood or "", story_type or ""]), preset_name)
    if situation and str(situation.get("Specific Situation", "")).strip():
        scene = str(situation.get("Scene Type") or scene)
        brief = {
            "Target Listener": f"คนที่เคยอยู่ในสถานการณ์: {situation.get('Specific Situation', '')}",
            "Core Emotion": str(situation.get("Hidden Feeling") or "longing"),
            "Shareable Angle": str(situation.get("Social Context") or situation.get("Specific Situation") or ""),
            "Caption Line": str(situation.get("Bridge Truth") or situation.get("Final Payoff") or situation.get("Specific Situation") or ""),
            "Song Promise": f"เพลงนี้พาผู้ฟังจากเหตุการณ์ '{situation.get('Specific Situation', '')}' ไปสู่การยอมรับความจริงในใจ",
        }
        if scene == "office_life":
            brief["Shareable Angle"] = f"เลิกงานแล้ว แต่เหตุการณ์ '{situation.get('Specific Situation', '')}' ยังตามกลับบ้าน"
            brief["Caption Line"] = "นาฬิกาเลิกงาน แต่ใจยังไม่เลิกเหนื่อย"
        brief.update(_emotional_arc_for_scene(scene))
        brief["Starting Emotion"] = str(situation.get("Hidden Feeling") or brief.get("Starting Emotion", ""))
        brief["Conflict"] = str(situation.get("Social Context") or brief.get("Conflict", ""))
        brief["Emotional Peak"] = str(situation.get("Escalation Moment") or brief.get("Emotional Peak", ""))
        brief["Resolution"] = str(situation.get("Bridge Truth") or brief.get("Resolution", ""))
        brief["Final Payoff Line"] = str(situation.get("Final Payoff") or brief.get("Final Payoff Line", ""))
        brief["Scene Type"] = scene
        brief["Preset"] = preset_name
        brief["Specific Situation"] = str(situation.get("Specific Situation", ""))
        return brief
    brief_by_scene = {
        "office_life": {
            "Target Listener": "Office workers and first jobbers who look fine all day but feel exhausted after work.",
            "Core Emotion": "exhausted",
            "Shareable Angle": "เลิกงานแล้ว แต่ความเหนื่อยยังทำงานต่อ",
            "Caption Line": "นาฬิกาเลิกงาน แต่ใจยังไม่เลิกเหนื่อย",
            "Song Promise": "This song gives tired workers permission to admit they are not okay and still go home whole.",
        },
        "night_drive": {
            "Target Listener": "Lonely night drivers who use the road to process feelings they cannot say out loud.",
            "Core Emotion": "longing",
            "Shareable Angle": "ขับรถไปไกลแค่ไหน บางความคิดก็ยังนั่งอยู่ข้าง ๆ",
            "Caption Line": "ถนนว่าง แต่ใจยังแน่นเหมือนเดิม",
            "Song Promise": "This song turns a late-night drive into a soft place to face what still hurts.",
        },
        "breakup_memory": {
            "Target Listener": "People after breakup who act healed but still carry small memories everywhere.",
            "Core Emotion": "regret",
            "Shareable Angle": "บางคนหายไป แต่ยังอยู่ในทุกความทรงจำ",
            "Caption Line": "ไม่ได้รอให้กลับมา แค่ยังลืมไม่หมด",
            "Song Promise": "This song lets listeners miss someone honestly without begging the past to return.",
        },
        "respectful_truth": {
            "Target Listener": "Couples or close people who need honesty without using hard words.",
            "Core Emotion": "healing",
            "Shareable Angle": "ความจริงสำคัญ แต่วิธีพูดก็สำคัญพอกัน",
            "Caption Line": "พูดตรง ๆ ได้ แต่อย่าลืมพูดเบา ๆ",
            "Song Promise": "This song makes difficult truth feel like repair instead of a wound.",
        },
        "family": {
            "Target Listener": "Working adults who look strong outside but still need the comfort of home.",
            "Core Emotion": "healing",
            "Shareable Angle": "ทั้งโลกถามหาผลงาน แต่ที่บ้านถามว่าเหนื่อยไหม",
            "Caption Line": "กลับบ้านช้า แต่ยังมีคนรอ",
            "Song Promise": "This song brings the listener back to the people who love them without conditions.",
        },
        "self_growth": {
            "Target Listener": "People trying to restart quietly after a season of failing or feeling lost.",
            "Core Emotion": "hope",
            "Shareable Angle": "ไม่ต้องเริ่มใหม่ให้ใครเห็น แค่ไม่ทิ้งตัวเองก็พอ",
            "Caption Line": "วันนี้ยังไม่เก่ง แต่อย่างน้อยยังไม่หนี",
            "Song Promise": "This song gives a small honest push to keep going without pretending to be okay.",
        },
    }
    fallback = {
        "Target Listener": "Thai listeners who need a song that understands a private feeling clearly.",
        "Core Emotion": "longing",
        "Shareable Angle": "บางประโยคธรรมดา อยู่ในใจนานกว่าที่คิด",
        "Caption Line": "บางความรู้สึกไม่ได้ดัง แต่ไม่เคยหายไป",
        "Song Promise": "This song gives the listener one clear emotional sentence they can keep and share.",
    }
    brief = dict(brief_by_scene.get(scene, fallback))
    brief.update(_emotional_arc_for_scene(scene))
    brief["Scene Type"] = scene
    brief["Preset"] = preset_name
    return brief


def _producer_brief_to_text(brief: dict[str, Any] | None) -> str:
    data = brief or {}
    keys = [
        "Target Listener",
        "Core Emotion",
        "Shareable Angle",
        "Caption Line",
        "Song Promise",
        "Starting Emotion",
        "Conflict",
        "Emotional Peak",
        "Resolution",
        "Final Payoff Line",
        "Specific Situation",
    ]
    return "\n".join(f"{key}: {data.get(key, '')}" for key in keys).strip()


def _producer_brief_context(brief: dict[str, Any] | None) -> str:
    if not brief:
        return ""
    return "\n".join(
        str(brief.get(key) or "")
        for key in ["Target Listener", "Core Emotion", "Shareable Angle", "Caption Line", "Song Promise"]
        if str(brief.get(key) or "").strip()
    )


def _hook_quality_summary_text(hook: str, title: str, concept: str) -> str:
    hook_score = _score_hook_candidate(hook)
    title_score = score_song_title_candidate(title, concept)
    return "\n".join(
        [
            f"Selected Hook: {hook}",
            f"Hook Score: {hook_score.get('score', 0)}",
            f"Caption Score: {hook_score.get('caption_score', hook_score.get('caption_potential', 0))}",
            f"TikTok Score: {hook_score.get('tiktok_score', 0)}",
            f"Human Speech Score: {hook_score.get('human_speech_score', 0)}",
            f"Emotional Impact Score: {hook_score.get('emotional_impact_score', hook_score.get('emotional_punch', 0))}",
            f"Singability Score: {hook_score.get('singability_score', hook_score.get('singability', 0))}",
            f"Memorability Score: {hook_score.get('memorability_score', hook_score.get('memorability', 0))}",
            f"Why this hook was selected: {hook_score.get('why', 'Strongest balance of caption clarity, human speech, and singability.')}",
            f"Selected Title: {title}",
            f"Title Score: {title_score.get('score', 0)}",
            "Why this title was selected: short, memorable, Thai-safe, and strong enough for a song title.",
        ]
    ).strip()


def generate_story_candidates_v2(concept: str, preset_name: str = "Thai Sad Pop", mood: str = "", story_type: str = "", producer_brief: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    scene = _song_scene_type("\n".join([concept or "", preset_name or "", mood or "", story_type or ""]), preset_name)
    banks = {
        "office_life": [
            ("โต๊ะตัวเดิม", "A worker smiles through a draining day until the parking lot becomes the first honest place.", ["coffee cup", "keyboard", "parking card"], ["morning desk", "empty meeting room", "parking lot after work"], "tired smile -> silent collapse -> self-return", "question hook about still being okay"),
            ("ไฟตึกดับแล้ว", "The office lights are off, but the meeting still keeps talking inside the narrator's head.", ["monitor glow", "office light", "work bag"], ["late desk", "dark hallway", "train ride home"], "endurance -> overwhelm -> letting work go", "contradiction hook about work ending but tiredness staying"),
            ("บัตรพนักงาน", "A good employee slowly realizes the badge is not the whole person.", ["employee badge", "report folder", "old shoes"], ["elevator mirror", "report pile", "front door at night"], "performance -> private fracture -> ordinary human rest", "confession hook behind the smile"),
            ("แชตกลุ่มงาน", "A work chat notification interrupts a life that is already too quiet.", ["phone", "group chat", "cold dinner"], ["phone notification", "dinner alone", "bedroom with unread messages"], "interruption -> pressure -> self-protection", "object hook from a notification"),
            ("ลานจอดรถ", "After work, the car becomes the only place where the narrator can admit they are not okay.", ["car key", "tail light", "parking ticket"], ["elevator to parking", "silent car", "last tail light"], "holding back -> quiet tears -> going home whole", "visual hook after work"),
        ],
        "night_drive": [
            ("ไฟแดงตีสอง", "Driving at 2 AM turns every red light into an old memory.", ["red light", "steering wheel", "old song"], ["2 AM intersection", "rainy road", "home street"], "escape -> memory -> acceptance", "question hook about how far to drive before forgetting"),
            ("เบาะข้าง ๆ", "An empty passenger seat makes the silence feel louder.", ["empty seat", "cold coffee", "windshield"], ["car interior", "old gas station", "city road"], "missing -> denial -> acceptance", "contradiction hook about distance"),
            ("เพลงในรถ", "A song in the car remembers what the narrator tries to forget.", ["car radio", "city lights", "jacket"], ["traffic at night", "orange tunnel", "roadside stop"], "stillness -> pain -> release", "memory hook from an old song"),
            ("ถนนเส้นเดิม", "The same road keeps asking the same emotional question.", ["exit sign", "tail light", "rain drops"], ["expressway", "rain glass", "missed exit"], "avoidance -> return -> new road", "road image question hook"),
            ("ปลายทางว่างเปล่า", "The narrator knows no one waits at the destination but still keeps driving.", ["map app", "fuel gauge", "headlights"], ["deleted destination", "passing home", "parked in rain"], "lost -> facing truth -> self-return", "confession hook"),
        ],
    }
    fallback = [
        ("คำที่ค้างในใจ", "An unspoken feeling becomes a song instead of a conversation.", ["window", "notebook", "bedside light"], ["quiet room", "rainy window", "open notebook"], "holding back -> honesty -> release", "short question hook"),
        ("คืนที่ไม่หาย", "One night makes the listener see themselves in the silence.", ["pillow", "phone", "water glass"], ["sleepless bed", "lit phone", "forced morning smile"], "silence -> ache -> honesty", "confession hook"),
        ("ประโยคเดิม", "One ordinary sentence keeps returning with unusual weight.", ["message", "clock", "jacket"], ["message screen", "evening hallway", "lit room"], "stumble -> loop -> soft release", "object hook"),
        ("พรุ่งนี้ค่อยหาย", "A person admits they are not healed yet but still wants tomorrow.", ["calendar", "shoes", "mirror"], ["morning mirror", "wet sidewalk", "bedroom light"], "strain -> acceptance -> small restart", "hope hook"),
        ("ไฟดวงสุดท้าย", "The last light in a room keeps company with unfinished feelings.", ["lamp", "curtain", "songbook"], ["warm bedroom", "writing desk", "night window"], "lonely -> written out -> lighter", "visual hook"),
    ]
    human_experience_bank = {
        "office_life": ["traffic jam after work", "unread work messages", "office lights turning off", "BTS/MRT ride home", "empty parking lot"],
        "night_drive": ["traffic light at 2 AM", "empty passenger seat", "rain on windshield", "old song on car radio", "missed exit"],
        "breakup_memory": ["old photo", "last conversation", "unread message", "coffee shop corner", "song that still hurts"],
        "respectful_truth": ["quiet conversation", "soft apology", "phone left face down", "long silence", "one careful sentence"],
        "family": ["dinner waiting at home", "front porch light", "mother's short message", "rice kept warm", "work bag by the door"],
        "self_growth": ["morning mirror", "old shoes", "calendar page", "small restart", "slow walk home"],
    }
    source = banks.get(scene, fallback)
    brief_context = _producer_brief_context(producer_brief)
    situation_story: dict[str, Any] | None = None
    if producer_brief and str(producer_brief.get("Specific Situation", "")).strip():
        situation_story = {
            "id": "story_00",
            "label": str(producer_brief.get("Specific Situation", "")),
            "story_angle": str(producer_brief.get("Shareable Angle", "")),
            "objects": [str(producer_brief.get("Specific Situation", "")), str(producer_brief.get("Caption Line", "")), str(producer_brief.get("Final Payoff Line", ""))],
            "scenes": [str(producer_brief.get("Emotional Peak", "")), str(producer_brief.get("Resolution", "")), str(producer_brief.get("Final Payoff Line", ""))],
            "human_experiences": [str(producer_brief.get("Core Emotion", "")), str(producer_brief.get("Caption Line", "")), str(producer_brief.get("Song Promise", ""))],
            "emotional_arc": "specific situation -> escalation -> truth -> payoff",
            "recommended_hook_direction": "specific situation hook / " + brief_context,
            "producer_brief": producer_brief or {},
            "story_novelty_score": 100,
        }
    story_candidates = [
        {
            "id": f"story_{idx:02d}",
            "label": label,
            "story_angle": angle,
            "objects": objects[:3],
            "scenes": scenes[:4],
            "human_experiences": human_experience_bank.get(scene, human_experience_bank["breakup_memory"])[idx - 1: idx + 2] or human_experience_bank.get(scene, [])[:3],
            "emotional_arc": arc,
            "recommended_hook_direction": " / ".join(part for part in [hook_direction, brief_context] if part).strip(),
            "producer_brief": producer_brief or {},
            "story_novelty_score": score_story_novelty(story_type or scene),
        }
        for idx, (label, angle, objects, scenes, arc, hook_direction) in enumerate(source[:5], start=1)
    ]
    if situation_story:
        story_candidates = [situation_story] + story_candidates
    return sorted(story_candidates, key=lambda item: int(item.get("story_novelty_score", 0)), reverse=True)[:5]


def generate_hook_candidates_v2(concept: str, story_candidate: dict[str, Any] | None = None, preset_name: str = "Thai Sad Pop") -> list[dict[str, Any]]:
    story = story_candidate or generate_story_candidates_v2(concept, preset_name)[0]
    producer_brief = story.get("producer_brief") if isinstance(story.get("producer_brief"), dict) else None
    context = "\n".join([concept or "", story.get("label", ""), story.get("story_angle", ""), story.get("recommended_hook_direction", ""), " ".join(story.get("human_experiences", []) or [])])
    base_hooks = _hook_candidates(story.get("label") or _authentic_title_from_concept(context, preset_name, ""), context)
    brief_hooks = []
    if producer_brief:
        for key in ["Caption Line", "Shareable Angle"]:
            hook_from_brief = _hook_from_brief_phrase(str(producer_brief.get(key) or ""), _song_scene_type(context, preset_name))
            if hook_from_brief:
                brief_hooks.append(hook_from_brief)
    if preset_name == "Office Burnout" or "office" in context.lower() or "Office Burnout" in context:
        brief_hooks.append(
            "\n".join(
                [
                    "นาฬิกาเลิกงาน แต่ใจยังไม่เลิกเหนื่อย",
                    "ยิ้มมาทั้งวันจนลืมถามข้างใน",
                    "คืนนี้ขอวางทุกอย่างไว้ก่อน",
                    "ให้ฉันได้กลับไปเป็นคนธรรมดา",
                ]
            )
        )
    base_hooks = brief_hooks + base_hooks
    if not base_hooks:
        base_hooks = [_hook_from_idea(context, story.get("label", "") or _authentic_title_from_concept(context, preset_name, ""), CREATIVE_PACK_PRESETS.get(preset_name, CREATIVE_PACK_PRESETS["Thai Sad Pop"]))]
    kinds = ["Visual Hook", "Contradiction Hook", "Emotional Hook", "Question Hook", "Object Hook"]
    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in base_hooks:
        hook = _sanitize_hook_text(raw, story.get("label", ""), context, enforce_title=False)
        key = _compact_line(hook)
        if not key or key in seen:
            continue
        seen.add(key)
        score = _score_hook_candidate(hook)
        novelty = score_hook_novelty(score["hook"])
        score["hook_novelty_score"] = novelty
        score["score"] = max(0, min(100, int((int(score.get("score", 0)) * 0.72) + (novelty * 0.28))))
        ranked.append({"hook": score["hook"], "lines": _lines(score["hook"]), "score": score})
    ranked = sorted(ranked, key=lambda item: item["score"]["score"], reverse=True)
    if preset_name == "Office Burnout" or "office" in context.lower() or "Office Burnout" in context:
        office_hook = "\n".join(
            [
                "นาฬิกาเลิกงาน แต่ใจยังไม่เลิกเหนื่อย",
                "ยิ้มมาทั้งวันจนลืมถามข้างใน",
                "คืนนี้ขอวางทุกอย่างไว้ก่อน",
                "ให้ฉันได้กลับไปเป็นคนธรรมดา",
            ]
        )
        if _compact_line(office_hook) not in {_compact_line(item["hook"]) for item in ranked}:
            office_score = _score_hook_candidate(office_hook)
            office_score["hook_novelty_score"] = score_hook_novelty(office_hook)
            office_score["score"] = max(90, int(office_score.get("score", 0)))
            ranked.insert(0, {"hook": office_hook, "lines": _lines(office_hook), "score": office_score})
    while len(ranked) < 5:
        fallback = _sanitize_hook_text(_hook_from_idea(context, story.get("label", ""), CREATIVE_PACK_PRESETS.get(preset_name, CREATIVE_PACK_PRESETS["Thai Sad Pop"])), story.get("label", ""), context, enforce_title=False)
        score = _score_hook_candidate(fallback)
        novelty = score_hook_novelty(score["hook"])
        score["hook_novelty_score"] = novelty
        score["score"] = max(0, min(100, int((int(score.get("score", 0)) * 0.72) + (novelty * 0.28))))
        ranked.append({"hook": score["hook"], "lines": _lines(score["hook"]), "score": score})
    return [
        {"id": f"hook_{idx:02d}", "type": kinds[(idx - 1) % len(kinds)], **item}
        for idx, item in enumerate(ranked[:5], start=1)
    ]


def generate_title_candidates_v2(concept: str, story_candidate: dict[str, Any] | None = None, hook: str = "", preset_name: str = "Thai Sad Pop") -> list[dict[str, str]]:
    story = story_candidate or generate_story_candidates_v2(concept, preset_name)[0]
    scene = _song_scene_type("\n".join([concept or "", story.get("story_angle", ""), " ".join(story.get("human_experiences", []) or [])]), preset_name)
    objects = [_thai_seed_phrase(str(item)) for item in story.get("objects", []) if str(item).strip()]
    scenes = [_thai_seed_phrase(str(item)) for item in story.get("scenes", []) if str(item).strip()]
    preferred_by_scene = {
        "office_life": ["โหมดพักร่าง", "ใจยังไม่เลิกงาน", "พักใจก่อน", "วันนี้เก่งมากแล้ว", "โต๊ะตัวเดิม", "กลับบ้านก่อน", "คืนนี้ขอพัก"],
        "night_drive": ["ทางกลับใจ", "ไฟแดงตีสอง", "คืนนี้ขับไกล", "ถนนยังจำ", "เบาะข้าง ๆ"],
        "breakup_memory": ["ข้อความสุดท้าย", "รูปเก่ายังยิ้ม", "ยังลืมไม่หมด", "คืนที่ยังคิดถึง"],
        "respectful_truth": ["พูดกันเบา ๆ", "คำที่ถนอม", "ความจริงเบา ๆ", "อย่าชนะด้วยคำแรง"],
        "family": ["ไฟบ้านยังรอ", "กลับบ้านก่อน", "คนที่บ้านรอ", "โต๊ะข้าวเดิม"],
        "self_growth": ["ค่อย ๆ กลับมา", "วันนี้ยังไหว", "เริ่มใหม่เบา ๆ", "พรุ่งนี้ค่อยว่า"],
    }
    blocked = {"รัก", "คิดถึง", "เหนื่อย", "ไม่ไหว", "ลืมไม่ลง", "ยังรัก", "กลับมา", "coffee cup", "parking card"}
    raw: list[tuple[str, str]] = []
    raw.extend((f"title-v3-{idx}", title) for idx, title in enumerate(preferred_by_scene.get(scene, preferred_by_scene["office_life"]), start=1))
    raw.extend(
        [
            ("object-based title", objects[0] if objects else ""),
            ("scene-based title", scenes[-1] if scenes else ""),
            ("phrase-based title", str(story.get("label") or "")),
            ("emotional title", _lines(hook)[0] if _lines(hook) else ""),
            ("commercial-safe title", _authentic_title_from_concept(concept, preset_name, str(story.get("label") or ""))),
        ]
    )
    titles: list[dict[str, str]] = []
    seen: set[str] = set()
    source_text = "\n".join([concept or "", hook or "", story.get("story_angle", ""), " ".join(story.get("human_experiences", []) or [])])
    for idx, (kind, raw_title) in enumerate(raw, start=1):
        clean = str(raw_title or "").strip()
        if not clean:
            continue
        if clean.lower() in blocked or re.search(r"[A-Za-z]", clean):
            clean = preferred_by_scene.get(scene, preferred_by_scene["office_life"])[0]
        key = _compact_line(clean)
        if not key or key in seen:
            continue
        seen.add(key)
        score_data = score_song_title_candidate(clean, source_text)
        score = int(score_data.get("score", 0))
        title_relatability = _weighted_relatability_score(_line_relatability_scores(clean, source_text, preset_name))
        score = int((score * 0.72) + (title_relatability * 0.28))
        title_novelty = score_title_novelty(clean)
        score = int((score * 0.72) + (title_novelty * 0.28))
        if len(key) > 18:
            score -= 22
        if clean in blocked:
            score -= 60
        titles.append({"id": f"title_{len(titles) + 1:02d}", "type": kind, "title": clean, "score": str(max(0, min(100, score))), "title_novelty_score": str(title_novelty)})
    return sorted(titles, key=lambda item: int(item.get("score", "0")), reverse=True)[:5]


def generate_music_seed_candidates_v2(concept: str, preset_name: str = "Thai Sad Pop", mood: str = "", story_type: str = "") -> dict[str, Any]:
    situation = _rewrite_song_situation_seed(generate_situation_first_seed(concept, preset_name, mood, story_type), concept, preset_name)
    situation_context = "\n".join([str(concept or ""), _situation_context_text(situation)])
    producer_brief = generate_producer_brief_v1(situation_context, preset_name, mood, story_type, situation)
    stories = generate_story_candidates_v2(situation_context, preset_name, mood, story_type, producer_brief)
    story = stories[0] if stories else {}
    hooks = generate_hook_candidates_v2(situation_context, story, preset_name)
    titles = generate_title_candidates_v2(situation_context, story, hooks[0]["hook"] if hooks else "", preset_name)
    return {"situation_first_seed": situation, "producer_brief": producer_brief, "story_candidates": stories, "hook_candidates": hooks, "title_candidates": titles}


def _selected_seed_summary(seed: dict[str, Any] | None) -> str:
    if not seed:
        return "No selected seed. Generated from concept and preset."
    story = seed.get("story") or {}
    situation = seed.get("situation_first_seed") if isinstance(seed.get("situation_first_seed"), dict) else {}
    objects = [_thai_seed_phrase(str(item)) for item in story.get("objects", []) if str(item).strip()]
    scenes = [_thai_seed_phrase(str(item)) for item in story.get("scenes", []) if str(item).strip()]
    experiences = [_thai_seed_phrase(str(item)) for item in story.get("human_experiences", []) if str(item).strip()]
    return "\n".join(
        [
            f"Selected Story: {story.get('label', '')}",
            f"Story Angle: {story.get('story_angle', '')}",
            f"Selected Objects: {', '.join(objects)}",
            f"Selected Scenes: {', '.join(scenes)}",
            f"Selected Experiences: {', '.join(experiences)}",
            f"Selected Hook: {seed.get('hook', '')}",
            f"Selected Title: {seed.get('title', '')}",
            f"Specific Situation: {situation.get('Specific Situation', '')}",
            f"Bridge Truth: {situation.get('Bridge Truth', '')}",
            f"Final Payoff: {situation.get('Final Payoff', '')}",
        ]
    ).strip()


def _seed_enriched_concept(concept: str, seed: dict[str, Any] | None) -> str:
    if not seed:
        return concept
    story = seed.get("story") or {}
    parts = [
        concept,
        str(story.get("label") or ""),
        str(story.get("story_angle") or ""),
        " ".join(str(item) for item in story.get("objects", []) if str(item).strip()),
        " ".join(str(item) for item in story.get("scenes", []) if str(item).strip()),
        " ".join(str(item) for item in story.get("human_experiences", []) if str(item).strip()),
        str(story.get("emotional_arc") or ""),
        _producer_brief_context(seed.get("producer_brief") if isinstance(seed.get("producer_brief"), dict) else None),
    ]
    return "\n".join(part for part in parts if str(part).strip())


def _thai_seed_phrase(text: str) -> str:
    phrase = str(text or "").strip()
    translations = {
        "coffee cup": "แก้วกาแฟ",
        "keyboard": "คีย์บอร์ด",
        "parking card": "บัตรจอดรถ",
        "monitor glow": "แสงหน้าจอ",
        "office light": "ไฟตึก",
        "work bag": "กระเป๋าทำงาน",
        "employee badge": "บัตรพนักงาน",
        "report folder": "แฟ้มรายงาน",
        "old shoes": "รองเท้าคู่เดิม",
        "phone": "โทรศัพท์",
        "group chat": "แชตกลุ่มงาน",
        "cold dinner": "ข้าวเย็นชืด",
        "car key": "กุญแจรถ",
        "tail light": "ไฟท้ายรถ",
        "parking ticket": "บัตรจอดรถ",
        "red light": "ไฟแดง",
        "steering wheel": "พวงมาลัย",
        "old song": "เพลงเก่า",
        "empty seat": "เบาะข้าง ๆ",
        "cold coffee": "กาแฟเย็นชืด",
        "windshield": "กระจกหน้ารถ",
        "car radio": "วิทยุในรถ",
        "city lights": "ไฟเมือง",
        "jacket": "เสื้อแจ็กเก็ต",
        "exit sign": "ป้ายทางออก",
        "rain drops": "หยดฝน",
        "map app": "แผนที่ในมือถือ",
        "fuel gauge": "เข็มน้ำมัน",
        "headlights": "ไฟหน้ารถ",
        "window": "หน้าต่าง",
        "notebook": "สมุดโน้ต",
        "bedside light": "ไฟหัวเตียง",
        "pillow": "หมอน",
        "water glass": "แก้วน้ำ",
        "message": "ข้อความ",
        "clock": "นาฬิกา",
        "calendar": "ปฏิทิน",
        "shoes": "รองเท้า",
        "mirror": "กระจก",
        "lamp": "โคมไฟ",
        "curtain": "ผ้าม่าน",
        "songbook": "สมุดเพลง",
        "morning desk": "โต๊ะเช้าเดิม",
        "empty meeting room": "ห้องประชุมว่าง",
        "parking lot after work": "ลานจอดรถหลังเลิกงาน",
        "late desk": "โต๊ะทำงานดึก",
        "dark hallway": "ทางเดินมืด",
        "train ride home": "รถไฟกลับบ้าน",
        "elevator mirror": "กระจกลิฟต์",
        "report pile": "กองรายงาน",
        "front door at night": "ประตูบ้านตอนกลางคืน",
        "phone notification": "แจ้งเตือนในมือถือ",
        "dinner alone": "มื้อเย็นคนเดียว",
        "bedroom with unread messages": "ห้องนอนกับข้อความที่ยังไม่อ่าน",
        "elevator to parking": "ลิฟต์ลงลานจอดรถ",
        "silent car": "รถที่เงียบสนิท",
        "last tail light": "ไฟท้ายดวงสุดท้าย",
    }
    translations.update(
        {
            "traffic jam after work": "รถติดหลังเลิกงาน",
            "unread work messages": "ข้อความงานที่ยังไม่ได้อ่าน",
            "office lights turning off": "ไฟออฟฟิศที่ค่อย ๆ ดับ",
            "bts/mrt ride home": "รถไฟฟ้ากลับบ้าน",
            "empty parking lot": "ลานจอดรถว่างเปล่า",
            "traffic light at 2 am": "ไฟแดงตอนตีสอง",
            "empty passenger seat": "เบาะข้าง ๆ ที่ว่างเปล่า",
            "rain on windshield": "ฝนบนกระจกหน้ารถ",
            "old song on car radio": "เพลงเก่าในวิทยุรถ",
            "missed exit": "ทางออกที่ขับเลยไป",
            "old photo": "รูปเก่า",
            "last conversation": "บทสนทนาสุดท้าย",
            "unread message": "ข้อความที่ยังไม่ได้อ่าน",
            "coffee shop corner": "มุมร้านกาแฟเดิม",
            "song that still hurts": "เพลงที่ยังเจ็บอยู่",
            "quiet conversation": "บทสนทนาเบา ๆ",
            "soft apology": "คำขอโทษเบา ๆ",
            "phone left face down": "โทรศัพท์ที่คว่ำหน้าไว้",
            "long silence": "ความเงียบนานเกินไป",
            "one careful sentence": "ประโยคที่ต้องถนอมกัน",
            "dinner waiting at home": "มื้อเย็นที่บ้านยังรอ",
            "front porch light": "ไฟหน้าบ้าน",
            "mother's short message": "ข้อความสั้น ๆ จากแม่",
            "rice kept warm": "ข้าวที่ยังอุ่นไว้",
            "work bag by the door": "กระเป๋างานข้างประตู",
            "morning mirror": "กระจกตอนเช้า",
            "small restart": "การเริ่มใหม่เล็ก ๆ",
            "slow walk home": "ทางกลับบ้านที่เดินช้าลง",
        }
    )
    translations.update(ENGLISH_SCENE_LEAK_TRANSLATIONS)
    return translations.get(phrase.lower(), phrase)


def _conversation_bank(concept: str, preset_name: str = "") -> list[str]:
    scene = _thai_speech_scene(concept, preset_name)
    base = list(HUMAN_CONVERSATION_LIBRARY.get(scene, HUMAN_CONVERSATION_LIBRARY["self_growth"]))
    for phrase in THAI_SPEECH_LIBRARY.get(scene, []):
        if phrase not in base:
            base.append(phrase)
    return base


def _memory_moment_bank(concept: str, preset_name: str = "") -> list[str]:
    scene = _thai_speech_scene(concept, preset_name)
    return list(HUMAN_MEMORY_MOMENTS.get(scene, HUMAN_MEMORY_MOMENTS["self_growth"]))


def _replace_english_leakage_line(line: str, concept: str, preset_name: str = "") -> tuple[str, bool]:
    value = str(line or "")
    if not re.search(r"[A-Za-z]{3,}", value):
        return value, False
    lowered = value.lower()
    replaced = value
    changed = False
    for english, thai in sorted(ENGLISH_SCENE_LEAK_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
        if english in lowered:
            replaced = re.sub(re.escape(english), thai, replaced, flags=re.I)
            lowered = replaced.lower()
            changed = True
    if re.search(r"[A-Za-z]{3,}", replaced):
        memory = _memory_moment_bank(concept, preset_name)[0]
        conversation = _conversation_bank(concept, preset_name)[0]
        replaced = f"{memory}ยังอยู่ตรงนั้น แต่ฉันเพิ่งถามตัวเองว่า{conversation}"
        changed = True
    return replaced.strip(), changed


def _remove_english_leakage_from_lyrics(lyrics: str, concept: str, preset_name: str = "") -> tuple[str, dict[str, Any]]:
    sections = parse_lyric_sections(lyrics)
    if not sections:
        return lyrics, {"english_leakage_lines": [], "english_leakage_fixed": 0}
    leaked: list[str] = []
    fixed = 0
    for section, lines in list(sections.items()):
        cleaned_lines: list[str] = []
        for line in lines:
            cleaned, changed = _replace_english_leakage_line(line, concept, preset_name)
            if changed:
                leaked.append(line)
                fixed += 1
            cleaned_lines.append(cleaned)
        sections[section] = cleaned_lines
    return _render_lyric_sections(sections), {"english_leakage_lines": leaked, "english_leakage_fixed": fixed}


def _apply_phrase_diversity_engine(lyrics: str, concept: str, preset_name: str = "") -> tuple[str, dict[str, Any]]:
    sections = parse_lyric_sections(lyrics)
    if not sections:
        return lyrics, {"replaced_phrases": []}
    replacements = {
        "วันนี้เก่งมากแล้ว": ["เหนื่อยไหม", "กินข้าวหรือยัง", "ถึงบ้านบอกด้วย"],
        "ถ้าคืนนี้ไม่ไหวก็ไม่ต้องฝืน": ["ไม่เป็นไรนะ", "เดี๋ยวมันก็ผ่านไป", "พรุ่งนี้ค่อยว่ากัน"],
        "ขอให้ฉันกลับมาเป็นฉันอีกครั้ง": ["แค่ผ่านวันนี้ไปให้ได้", "ค่อย ๆ กลับมาเป็นตัวเอง", "ไม่ต้องเก่งทุกคืนก็ได้"],
    }
    used: dict[str, int] = {phrase: 0 for phrase in replacements}
    replaced: list[str] = []
    conversation = _conversation_bank(concept, preset_name)
    for section, lines in list(sections.items()):
        next_lines: list[str] = []
        for line in lines:
            new_line = line
            for phrase, choices in replacements.items():
                if phrase in new_line:
                    used[phrase] += 1
                    if used[phrase] > 1 or phrase in OVERUSED_AUTHENTICITY_PHRASES:
                        idx = (used[phrase] - 1) % len(choices)
                        replacement = choices[idx]
                        if replacement not in conversation and conversation:
                            replacement = conversation[idx % len(conversation)]
                        new_line = new_line.replace(phrase, replacement)
                        replaced.append(f"{phrase} -> {replacement}")
            next_lines.append(new_line)
        sections[section] = next_lines
    return _render_lyric_sections(sections), {"replaced_phrases": replaced}


def _authentic_thai_speech_validator(lyrics: str, concept: str = "", preset_name: str = "") -> dict[str, Any]:
    translated: list[str] = []
    english: list[str] = []
    for line in _lines(lyrics):
        if line.startswith("["):
            continue
        if re.search(r"[A-Za-z]{3,}", line):
            english.append(line)
        if any(pattern in line for pattern in TRANSLATED_THAI_PATTERNS) or _ai_phrase_count(line) > 0:
            translated.append(line)
    naturalness = _thai_naturalness_score(lyrics, concept, preset_name)
    return {
        "ok": not english and not translated and naturalness >= 90,
        "english_leakage_lines": english,
        "translated_sounding_lines": translated,
        "Thai Naturalness": naturalness,
    }


def _apply_relatability_target_rewrite(lyrics: str, hook: str, concept: str, preset_name: str = "") -> tuple[str, dict[str, Any]]:
    before = _relatability_report(lyrics, hook, concept, preset_name)
    has_conversation = any(phrase in lyrics for phrase in _conversation_bank(concept, preset_name))
    has_memory = any(phrase in lyrics for phrase in _memory_moment_bank(concept, preset_name))
    if int(before.get("Relatability Score", 0)) >= 90 and _thai_naturalness_score(lyrics, concept, preset_name) >= 90 and has_conversation and has_memory:
        return lyrics, {"before": before, "after": before, "actions": []}
    sections = parse_lyric_sections(lyrics)
    if not sections:
        return lyrics, {"before": before, "after": before, "actions": []}
    conversation = _conversation_bank(concept, preset_name)
    memory = _memory_moment_bank(concept, preset_name)
    actions: list[str] = []
    injections = {
        "Verse 1": [f"{memory[0]}ยังอยู่ตรงนั้น", conversation[0]],
        "Verse 2": [conversation[1] if len(conversation) > 1 else "กินข้าวหรือยัง", f"{memory[1] if len(memory) > 1 else memory[0]}ยังทำให้ฉันเงียบไป"],
        "Bridge": [conversation[3] if len(conversation) > 3 else "ไม่เป็นไรนะ", conversation[4] if len(conversation) > 4 else "เดี๋ยวมันก็ผ่านไป"],
    }
    for section, additions in injections.items():
        current = sections.setdefault(section, [])
        for addition in reversed(additions):
            if addition and addition not in current:
                current.insert(0, addition)
                actions.append(f"added {section}: {addition}")
    rewritten = _render_lyric_sections(sections)
    rewritten, _ = _apply_phrase_diversity_engine(rewritten, concept, preset_name)
    rewritten, _ = _remove_english_leakage_from_lyrics(rewritten, concept, preset_name)
    after = _relatability_report(rewritten, hook, concept, preset_name)
    return rewritten, {"before": before, "after": after, "actions": actions}


def _reduce_repeated_lines_for_suno(lyrics: str, hook: str, concept: str, preset_name: str = "", max_repeated: int = 6) -> str:
    if _lyric_line_stats(lyrics).get("repeated_lines", 0) <= max_repeated:
        return lyrics
    sections = parse_lyric_sections(lyrics)
    if not sections:
        return lyrics
    protected = set(_lines(hook))
    replacements = _conversation_bank(concept, preset_name) + _memory_moment_bank(concept, preset_name) + [
        "คืนนี้ขอพักใจไว้ตรงนี้",
        "พรุ่งนี้ค่อยเริ่มใหม่ก็ได้",
        "ไม่ต้องตอบทุกอย่างในคืนเดียว",
    ]

    def next_replacement(existing: set[str], offset: int) -> str:
        for idx in range(len(replacements)):
            candidate = replacements[(offset + idx) % len(replacements)]
            if candidate and candidate not in existing:
                return candidate
        return "คืนนี้ขอพักใจไว้ตรงนี้"

    replacement_index = 0
    for section in ["Outro", "Bridge", "Final Chorus", "Verse 2", "Verse 1"]:
        lines = sections.get(section, [])
        for idx, line in enumerate(list(lines)):
            stats = _lyric_line_stats(_render_lyric_sections(sections))
            if stats.get("repeated_lines", 0) <= max_repeated:
                return _render_lyric_sections(sections)
            if line in protected:
                continue
            current_lines = [item for values in sections.values() for item in values]
            if current_lines.count(line) <= 1:
                continue
            existing = set(current_lines)
            replacement = next_replacement(existing, replacement_index)
            replacement_index += 1
            sections[section][idx] = replacement
    return _render_lyric_sections(sections)


def _selected_seed_title(seed: dict[str, Any] | None, concept: str) -> str:
    if not seed:
        return ""
    raw_title = str(seed.get("title") or "").strip()
    story = seed.get("story") or {}
    title = _thai_seed_phrase(raw_title)
    thai_concept = _thai_char_count(concept) > 0
    if thai_concept and re.search(r"[A-Za-z]", title):
        title = str(story.get("label") or "").strip() or _thai_seed_phrase(str((story.get("objects") or [""])[0]))
    return title.strip()


def _render_lyric_sections(sections: dict[str, list[str]]) -> str:
    order = ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Bridge", "Final Chorus", "Outro"]
    rendered: list[str] = []
    seen = set()
    for section in order + [name for name in sections if name not in order]:
        if section in seen or section not in sections:
            continue
        seen.add(section)
        rendered.append(f"[{section}]")
        rendered.extend(sections.get(section, []))
        rendered.append("")
    return "\n".join(rendered).strip()


def _concept_anchor_line(concept: str) -> str:
    text = str(concept or "")
    if "ไม่เหลือใคร" in text:
        return "สุดท้ายตรงนี้เหมือนไม่เหลือใครให้เรียกหา"
    if "ความจริง" in text and "พูด" in text:
        return "ความจริงยังสำคัญ แต่คำที่ใช้ก็สำคัญไม่แพ้กัน"
    cleaned = re.sub(r"\s+", " ", text).strip()
    if 4 <= _thai_char_count(cleaned) <= 32:
        return cleaned
    return ""


def _selected_story_lines(seed: dict[str, Any] | None, concept: str) -> dict[str, list[str]]:
    if not seed:
        return {}
    story = seed.get("story") or {}
    label = str(story.get("label") or "").strip()
    objects = [_thai_seed_phrase(str(item)) for item in story.get("objects", []) if str(item).strip()]
    scenes = [_thai_seed_phrase(str(item)) for item in story.get("scenes", []) if str(item).strip()]
    first_object = objects[0] if objects else label
    second_object = objects[1] if len(objects) > 1 else first_object
    first_scene = scenes[0] if scenes else label
    second_scene = scenes[1] if len(scenes) > 1 else first_scene
    last_scene = scenes[-1] if scenes else first_scene
    first_experience = experiences[0] if experiences else first_scene
    second_experience = experiences[1] if len(experiences) > 1 else last_scene
    anchor = _concept_anchor_line(concept)
    final_lines = [
        f"จาก{label or first_object} ฉันค่อย ๆ ยอมรับความจริง",
        anchor or f"ให้{last_scene}พาฉันกลับมาหาตัวเอง",
    ]
    return {
        "Verse 1": [f"{first_object}ยังวางอยู่ตรง{first_scene}", f"ฉันยิ้มให้วันเดิมทั้งที่ข้างในเริ่มไม่ไหว"],
        "Verse 2": [f"{second_scene}เงียบจนได้ยินเสียงใจตัวเอง", f"{second_object}เตือนว่าฉันฝืนมานานเกินไป"],
        "Bridge": [f"{last_scene}กลายเป็นที่ที่ฉันพูดความจริงกับตัวเอง", anchor] if anchor else [f"{last_scene}กลายเป็นที่ที่ฉันพูดความจริงกับตัวเอง"],
        "Final Chorus": final_lines,
    }


def _selected_story_lines(seed: dict[str, Any] | None, concept: str) -> dict[str, list[str]]:
    if not seed:
        return {}
    story = seed.get("story") or {}
    label = str(story.get("label") or "").strip()
    objects = [_thai_seed_phrase(str(item)) for item in story.get("objects", []) if str(item).strip()]
    scenes = [_thai_seed_phrase(str(item)) for item in story.get("scenes", []) if str(item).strip()]
    experiences = [_thai_seed_phrase(str(item)) for item in story.get("human_experiences", []) if str(item).strip()]
    first_object = objects[0] if objects else label
    first_scene = scenes[0] if scenes else label
    second_scene = scenes[1] if len(scenes) > 1 else first_scene
    last_scene = scenes[-1] if scenes else first_scene
    first_experience = experiences[0] if experiences else first_scene
    second_experience = experiences[1] if len(experiences) > 1 else last_scene
    anchor = _concept_anchor_line(concept)
    bridge_lines = [
        f"{last_scene}กลายเป็นที่ที่ฉันพูดความจริงกับตัวเอง",
        f"อย่างน้อย{second_experience}ก็ทำให้ฉันยอมฟังตัวเอง",
    ]
    if anchor:
        bridge_lines.append(anchor)
    return {
        "Verse 1": [
            f"{first_object}ยังวางอยู่ตรง{first_scene}",
            f"ใน{first_experience} ฉันเพิ่งรู้ว่าข้างในเริ่มไม่ไหว",
        ],
        "Verse 2": [
            f"{second_scene}เงียบจนได้ยินเสียงใจตัวเอง",
            f"{second_experience}เตือนว่าฉันฝืนมานานเกินไป",
        ],
        "Bridge": bridge_lines,
        "Final Chorus": [
            f"จาก{label or first_object} ฉันค่อย ๆ ยอมรับความจริง",
            anchor or f"ให้{last_scene}พาฉันกลับมาหาตัวเอง",
        ],
    }


def _apply_selected_story_to_lyrics(lyrics: str, seed: dict[str, Any] | None, concept: str) -> str:
    story_lines = _selected_story_lines(seed, concept)
    if not story_lines:
        return lyrics
    sections = parse_lyric_sections(lyrics)
    for section, lines in story_lines.items():
        existing = sections.setdefault(section, [])
        for line in reversed([item for item in lines if item and item not in existing]):
            existing.insert(0, line)
    return _render_lyric_sections(sections)


def _enforce_selected_hook_authority(lyrics: str, selected_hook: str) -> str:
    hook_lines = [line for line in _lines(selected_hook) if line.strip()]
    if not hook_lines:
        return lyrics
    sections = parse_lyric_sections(lyrics)
    strongest = hook_lines[:4]
    chorus_fillers = [
        "ยิ้มมาทั้งวันจนลืมว่าข้างใน",
        "แค่อยากมีคืนหนึ่งที่ไม่ต้องไหว",
        "พักใจก่อน พรุ่งนี้ค่อยว่ากัน",
    ]
    final_fillers = [
        "วันนี้เก่งมากแล้วที่ยังผ่านมาได้",
        "ถ้าคืนนี้ไม่ไหวก็ไม่ต้องฝืน",
        "พรุ่งนี้ค่อยกลับไปสู้ใหม่",
    ]
    chorus = strongest[:]
    for line in chorus_fillers:
        if len(chorus) >= 5:
            break
        if line not in chorus:
            chorus.append(line)
    final_chorus = strongest[:]
    for line in final_fillers:
        if len(final_chorus) >= 6:
            break
        if line not in final_chorus:
            final_chorus.append(line)
    sections["Chorus"] = chorus[:6]
    sections["Final Chorus"] = final_chorus[:6]
    return _render_lyric_sections(sections)


def _repair_thai_mojibake(text: str) -> str:
    value = str(text or "")
    markers = ["เน€เธ", "เธ", "เธ", "เธฃ", "โ€", "ย "]
    if not any(marker in value for marker in markers):
        return value
    try:
        repaired = value.encode("cp874").decode("utf-8")
    except UnicodeError:
        return value
    if _thai_char_count(repaired) >= _thai_char_count(value):
        return repaired.replace("⁠", "").replace("โ\u0081\xa0", "").strip()
    return value


def _clean_release_text(value: str) -> str:
    repaired = _repair_thai_mojibake(str(value or ""))
    repaired = repaired.replace("TikTok-ready", "เหมาะกับท่อนฮุกสั้น").replace("Spotify-friendly", "ฟังง่ายแบบเพลงปล่อยจริง")
    repaired = repaired.replace("hook direction", "hook idea").replace("lyrics direction", "lyric idea")
    return repaired.strip()


def _clean_release_pack_text(pack: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in pack.items():
        cleaned[key] = _clean_release_text(value) if isinstance(value, str) else value
    return cleaned


def _lyrics(title: str, hook: str, idea: str, preset_name: str, preset: dict[str, str]) -> str:
    if _concept_theme(idea) == "respectful_truth":
        return _respectful_truth_lyrics(title, hook)
    hook_lines = _lines(hook)
    hook_block = "\n".join(hook_lines)
    return "\n".join(
        [
            "[Intro]",
            _concept_rewrite_line(idea, "Intro", 0),
            _concept_rewrite_line(idea, "Intro", 1),
            "",
            "[Verse 1]",
            _concept_rewrite_line(idea, "Verse 1", 0),
            _concept_rewrite_line(idea, "Verse 1", 1),
            _concept_rewrite_line(idea, "Verse 1", 2),
            _concept_rewrite_line(idea, "Verse 1", 3),
            "",
            "[Pre-Chorus]",
            _concept_rewrite_line(idea, "Pre-Chorus", 0),
            _concept_rewrite_line(idea, "Pre-Chorus", 1),
            "",
            "[Chorus]",
            hook_block,
            "",
            "[Verse 2]",
            _concept_rewrite_line(idea, "Verse 2", 0),
            _concept_rewrite_line(idea, "Verse 2", 1),
            _concept_rewrite_line(idea, "Verse 2", 2),
            _concept_rewrite_line(idea, "Verse 2", 3),
            "",
            "[Bridge]",
            _concept_rewrite_line(idea, "Bridge", 0),
            _concept_rewrite_line(idea, "Bridge", 1),
            _concept_rewrite_line(idea, "Bridge", 2),
            "",
            "[Final Chorus]",
            hook_block,
            _concept_rewrite_line(idea, "Final Chorus", 0, final_payoff=True),
            _concept_rewrite_line(idea, "Final Chorus", 1, final_payoff=True),
            "",
            "[Outro]",
            _concept_rewrite_line(idea, "Outro", 0),
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


def _concept_rewrite_line(idea: str, section: str, index: int, *, final_payoff: bool = False) -> str:
    theme = _concept_theme(idea)
    scene = _song_scene_type(idea)
    advanced_pools = _advanced_scene_pools(scene)
    if advanced_pools:
        lines = advanced_pools.get(section) or advanced_pools.get("Verse 1") or [str(idea or "ความรู้สึกนี้").strip()]
        if final_payoff and section == "Final Chorus" and len(lines) > 4:
            return lines[(index + 2) % len(lines)]
        return lines[index % len(lines)]
    if theme == "respectful_truth":
        pools = {
            "Intro": [
                "คืนนี้เรานั่งฟังใจกันก่อนจะพูดอะไร",
                "ให้ความเงียบช่วยจับมือเราไว้เบา ๆ",
            ],
            "Verse 1": [
                "ฉันไม่ได้กลัวความจริงที่เธออยากบอก",
                "แค่กลัวน้ำเสียงทำให้ใจเราห่างกัน",
                "ถ้าต้องพูดเรื่องที่เจ็บให้กันฟัง",
                "ขอให้ยังมีความอ่อนโยนประคองคำ",
            ],
            "Pre-Chorus": [
                "คำตรง ๆ ไม่จำเป็นต้องเป็นมีด",
                "ถ้าพูดด้วยใจที่ยังอยากรักษาเรา",
            ],
            "Chorus": [
                "พูดความจริงเบา ๆ",
                "ให้ใจเรายังจับมือกัน",
                "ไม่ต้องชนะด้วยคำแรง",
                "แค่ฟังกันให้มากพอ",
            ],
            "Verse 2": [
                "ฉันก็มีส่วนผิดที่เงียบจนเกินไป",
                "เธอก็เหนื่อยใช่ไหมที่ต้องเดาใจฉัน",
                "ลองวางคำแข็ง ๆ ลงข้างความสัมพันธ์",
                "แล้วพูดกันเหมือนคนที่ยังแคร์",
            ],
            "Bridge": [
                "ให้ความจริงเป็นไฟที่ส่องทาง",
                "ไม่ใช่ไฟที่เผาทุกอย่างจนหายไป",
                "ถ้าคืนนี้น้ำตาจะไหลก็ไม่เป็นไร",
                "ขอแค่ไม่ใช้คำพูดทำลายกัน",
            ],
            "Final Chorus": [
                "พูดความจริงเบา ๆ",
                "ให้ใจเรายังกลับมา",
                "ให้คำอ่อนโยนซ่อมรอยร้าว",
                "ไม่ใช่ผลักเราให้ไกล",
                "ถ้ายังรักกันอยู่",
                "พูดกันดี ๆ ได้ไหม",
            ],
            "Outro": [
                "ถ้ายังรักกันอยู่ พูดกันเบา ๆ ก็พอ",
            ],
        }
    elif scene == "office_life":
        pools = {
            "Intro": [
                "เช้าวันจันทร์ฉันวางกาแฟไว้บนโต๊ะข้างคีย์บอร์ด",
                "แจ้งเตือนเด้งขึ้นมาก่อนจะได้หายใจ",
            ],
            "Verse 1": [
                "ฉันยิ้มให้ทุกคนเหมือนแบตยังเต็มอยู่",
                "ทั้งที่เมื่อคืนหลับไปพร้อมไฟหน้าจอ",
                "ไฟล์ Excel ยังเปิดค้างเหมือนคำถามที่ไม่มีใครตอบ",
                "ในห้องประชุมฉันพยักหน้าแทนคำว่าไม่ไหว",
            ],
            "Pre-Chorus": [
                "ยิ่งทำเหมือนไม่เป็นไรยิ่งเงียบลงทุกที",
                "เลิกงานแล้วทำไมงานยังเดินตามกลับบ้าน",
            ],
            "Chorus": [
                "ยิ้มทั้งวันจนลืมถามตัวเอง",
                "ว่าเหนื่อยแค่ไหนถึงเรียกว่าไหว",
                "เลิกงานแล้วไฟตึกดับไป",
                "แต่ในหัวฉันยังประชุมอยู่",
            ],
            "Verse 2": [
                "หัวหน้าบอกว่าแก้อีกนิดเดียวก็เสร็จ",
                "แต่นิดเดียวของเขาคือทั้งคืนของฉัน",
                "ในแชตกลุ่มมีแต่คำว่าเร่งหน่อยนะทุกวัน",
                "ฉันเลยเก็บคำว่าเหนื่อยไว้ใต้รอยยิ้ม",
            ],
            "Bridge": [
                "ตรงลานจอดรถฉันนั่งนิ่งอยู่หลายนาที",
                "ไม่ได้อยากลาออก แค่อยากกลับมาเป็นคนเดิม",
                "คนที่เคยมีฝันนอกเหนือจาก deadline",
                "คนที่ไม่ต้องขอโทษเพราะพักหายใจ",
            ],
            "Final Chorus": [
                "ยิ้มทั้งวันแต่คืนนี้ขอวางลง",
                "ให้ความเหนื่อยได้มีชื่อของมัน",
                "ถ้าพรุ่งนี้ต้องเดินเข้าตึกเดิมอีกครั้ง",
                "ขอให้ฉันยังไม่ทิ้งตัวเองไว้ตรงนั้น",
                "เลิกงานแล้วไฟตึกดับไป",
                "คราวนี้ฉันจะพาใจกลับบ้าน",
            ],
            "Outro": [
                "ปิดคอมแล้วขอปิดเสียงในหัวสักคืน",
            ],
        }
    elif scene == "night_drive":
        pools = {
            "Intro": [
                "ฝนบาง ๆ เกาะกระจกหน้ารถตอนสี่ทุ่ม",
                "เพลงเดิมดังเบา ๆ เหมือนมีใครนั่งข้างกัน",
            ],
            "Verse 1": [
                "ฉันเลี้ยวผ่านปั๊มเดิมที่เราเคยหยุดซื้อกาแฟ",
                "ไฟถนนยาวเหมือนประโยคที่ยังไม่จบ",
                "มือจับพวงมาลัยแต่ความคิดหลุดไปไกล",
                "ทุกแยกในคืนนี้เหมือนถามว่าจะไปไหนต่อ",
            ],
            "Pre-Chorus": [
                "ยิ่งขับให้ไกลจากวันที่เสียเธอไป",
                "ยิ่งเห็นว่าใจยังวนอยู่ถนนเดิม",
            ],
            "Chorus": [
                "ถนนยาวไปถึงไหน",
                "ทำไมยังพาใจกลับไปหาเธอ",
                "ไฟเมืองผ่านตาเสมอ",
                "แต่ภาพเดิมไม่เคยผ่านไป",
            ],
            "Verse 2": [
                "เสียงฝนบนหลังคารถดังแทนคำที่ไม่ได้พูด",
                "เบาะข้าง ๆ ว่างจนดูใหญ่กว่าเดิม",
                "ฉันลดกระจกให้ลมกลางคืนเข้ามาเติม",
                "แต่ความเงียบยังนั่งอยู่ตรงที่เธอเคยอยู่",
            ],
            "Bridge": [
                "ถ้าปลายทางไม่มีเธอรออยู่แล้ว",
                "ทำไมฉันยังไม่กล้ากลับบ้าน",
                "บางทีการขับไปเรื่อย ๆ",
                "ก็แค่ข้ออ้างของคนที่ยังไม่พร้อมหยุด",
            ],
            "Final Chorus": [
                "ถนนยาวไปถึงไหน",
                "คืนนี้ฉันคงต้องยอมรับ",
                "ไฟเมืองพาใจกลับไปหาเธอ",
                "แต่ฉันต้องพาตัวเองกลับมา",
                "ถ้าเธอไม่อยู่ปลายทางไหน",
                "ฉันจะหยุดรถแล้วปล่อยให้ใจร้องไห้",
            ],
            "Outro": [
                "ไฟท้ายคันสุดท้ายหายไป เหลือแค่ฉันกับเพลงเดิม",
            ],
        }
    elif scene == "breakup_memory":
        pools = {
            "Intro": [
                "คืนนี้ห้องเงียบกว่าทุกคืนที่เคยอยู่ด้วยกัน",
                "ฉันวางโทรศัพท์คว่ำไว้เหมือนกลัวชื่อเธอสว่างขึ้นมา",
            ],
            "Verse 1": [
                "ฉันเลี่ยงทางเดิมแต่ยังเจอเธอในความคิด",
                "แก้วใบที่เธอเคยใช้ยังอยู่หลังตู้",
                "ไม่ได้ตั้งใจเก็บไว้เพื่อรอให้เธอกลับมาดู",
                "แค่ยังไม่กล้าทิ้งหลักฐานว่าเราเคยมีจริง",
            ],
            "Pre-Chorus": [
                "ใครบอกว่าเวลาจะทำให้เบาลง",
                "ทำไมของเล็ก ๆ ยังหนักอยู่ในอก",
            ],
            "Chorus": [
                "กี่วันคืนผ่านไป",
                "ทำไมยังเป็นฉันที่เจ็บ",
                "ทั้งที่เธอไม่เคยหันกลับ",
                "ฉันยังเก็บเธอไว้ในเพลง",
            ],
            "Verse 2": [
                "เพื่อนบอกให้ลองเริ่มใหม่กับใครสักคน",
                "แต่ฉันยังสะดุดกับเพลงที่เธอเคยส่ง",
                "บางความทรงจำไม่ดัง แต่มันไม่เคยหมดลง",
                "เหมือนฝุ่นบนกรอบรูปที่เช็ดเท่าไรก็กลับมา",
            ],
            "Bridge": [
                "ถ้าวันหนึ่งฉันพูดชื่อเธอได้โดยไม่สั่น",
                "วันนั้นคงไม่ใช่วันที่ลืม",
                "แต่อาจเป็นวันที่ยอมรับ",
                "ว่าเราเคยรักกันจริง และมันจบจริง",
            ],
            "Final Chorus": [
                "กี่วันคืนผ่านไป",
                "ฉันยังเป็นคนที่เจ็บ",
                "แต่คืนนี้จะไม่ขอให้เธอกลับ",
                "จะขอให้ตัวเองกลับมา",
                "ถ้ายังเก็บเธอไว้ในเพลง",
                "ก็ให้เพลงนี้เป็นคำลาสุดท้าย",
            ],
            "Outro": [
                "ฉันปิดไฟ แล้วปล่อยให้ความเงียบดูแลชื่อเธอ",
            ],
        }
    elif scene == "quiet_love":
        pools = {
            "Intro": [
                "ฉันซ้อมคำว่าธรรมดาไว้ก่อนเธอเดินเข้ามา",
                "ทั้งที่ข้างในไม่เคยธรรมดาเลยสักครั้ง",
            ],
            "Verse 1": [
                "เธอถามว่าวันนี้เป็นยังไง ฉันตอบว่าเหมือนเดิม",
                "แต่คำว่าเหมือนเดิมคือฉันยังมองหาเธอ",
                "ทุกครั้งที่เราหัวเราะกับเรื่องเล็ก ๆ",
                "ฉันต้องเตือนตัวเองว่าอย่าเผลอจริงจัง",
            ],
            "Pre-Chorus": [
                "ถ้าพูดออกไปแล้วเราไม่เหมือนเดิม",
                "ฉันควรเก็บเธอไว้ตรงนี้หรือเสี่ยงเสียเธอไป",
            ],
            "Chorus": [
                "ถ้าใจยังเลือกเธออยู่",
                "ฉันควรพูดมันออกไปไหม",
                "กลัวเสียเธอไปทั้งใจ",
                "เลยเก็บรักไว้ในเพลง",
            ],
            "Verse 2": [
                "ฉันจำกาแฟที่เธอชอบได้ดีกว่าเรื่องตัวเอง",
                "จำสีเสื้อวันที่เธอยิ้มให้กัน",
                "แต่ต้องทำเหมือนไม่เห็นความหมายของวันนั้น",
                "เพราะกลัวว่าเธอจะรู้มากเกินไป",
            ],
            "Bridge": [
                "ถ้าความเงียบคือที่เดียวที่รักนี้ปลอดภัย",
                "ฉันคงต้องอยู่กับมันอีกสักพัก",
                "แต่บางคืนหัวใจดังเกินจะเก็บ",
                "จนเพลงนี้หลุดออกมาแทนคำสารภาพ",
            ],
            "Final Chorus": [
                "ถ้าใจยังเลือกเธออยู่",
                "คืนนี้ฉันคงปิดไม่ไหว",
                "ถ้าพรุ่งนี้เธอจะเดินจากไป",
                "อย่างน้อยขอให้เธอรู้ความจริง",
                "ฉันเก็บรักไว้ในเพลงมานาน",
                "แต่เพลงนี้อยากให้เธอฟัง",
            ],
            "Outro": [
                "ถ้าพูดไม่ไหว ก็ให้เพลงนี้พูดแทน",
            ],
        }
    else:
        pools = {
            "Intro": [
                "คืนนี้มีบางอย่างในอกที่ไม่ยอมหลับ",
                "ฉันเลยเปิดไฟไว้ให้ความรู้สึกค่อย ๆ พูด",
            ],
            "Verse 1": [
                "ฉันไม่ได้เศร้าตลอดเวลาเหมือนในเพลงเก่า",
                "แค่บางนาทีมันกลับมาโดยไม่บอกกล่าว",
                "เหมือนประโยคธรรมดาที่ทำให้เงียบไปยาว",
                "แล้วต้องแกล้งหัวเราะให้ผ่านบทสนทนา",
            ],
            "Pre-Chorus": [
                "ยิ่งทำเหมือนไม่เป็นไรยิ่งรู้ดี",
                "ว่าบางอย่างยังรอให้ฉันยอมรับ",
            ],
            "Chorus": [
                "กี่คืนแล้วที่ยังไม่หาย",
                "ทั้งที่บอกใครว่าไม่เป็นไร",
                "ยิ่งทำเหมือนเดินต่อได้",
                "ยิ่งรู้ว่าข้างในยังหยุดอยู่",
            ],
            "Verse 2": [
                "ฉันเริ่มกลัวความเงียบในตอนกลับบ้าน",
                "เพราะมันชอบถามคำที่คนอื่นไม่ถาม",
                "บางเรื่องเล็กเกินจะเล่าให้ใครฟัง",
                "แต่ใหญ่พอให้ทั้งคืนไม่จบลง",
            ],
            "Bridge": [
                "ถ้าคืนนี้ต้องยอมรับว่าฉันยังไม่เก่ง",
                "ก็ขอไม่แกล้งแข็งแรงต่อหน้าเพลงนี้",
                "บางคนหายดีเพราะลืมได้",
                "แต่ฉันอาจหายดีเพราะยอมพูดตรง ๆ",
            ],
            "Final Chorus": [
                "กี่คืนแล้วที่ยังไม่หาย",
                "คืนนี้ฉันจะไม่โกหกใคร",
                "ถ้ายังเจ็บก็ปล่อยให้เจ็บได้",
                "ไม่ต้องรีบเป็นคนใหม่ทันที",
                "พรุ่งนี้ถ้าต้องเดินต่อไป",
                "ขอเดินด้วยความจริงที่อยู่ในอก",
            ],
            "Outro": [
                "ให้เพลงนี้ปิดไฟดวงสุดท้ายในห้องช้า ๆ",
            ],
        }
    lines = pools.get(section) or pools.get("Verse 1") or [str(idea or "ความรู้สึกนี้").strip()]
    if final_payoff and section == "Final Chorus" and len(lines) > 4:
        return lines[(index + 2) % len(lines)]
    return lines[index % len(lines)]


def _rewrite_disallowed_reused_lines(idea: str, lyrics: str) -> str:
    if _is_breakup_memory_concept(idea):
        return lyrics
    output: list[str] = []
    current_section = "Intro"
    replacement_counts: dict[str, int] = {}
    for line in str(lyrics or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped.strip("[]")
            output.append(line)
            continue
        if any(stale in line for stale in REUSED_BREAKUP_MEMORY_LINES):
            replacement_counts[current_section] = replacement_counts.get(current_section, 0) + 1
            output.append(_concept_rewrite_line(idea, current_section, replacement_counts[current_section] - 1))
            continue
        output.append(line)
    return "\n".join(output).strip()


def _reduce_overused_generic_words(idea: str, lyrics: str) -> str:
    text = str(lyrics or "")
    overused = {word for word, limit in OVERUSED_GENERIC_WORD_LIMITS.items() if text.count(word) > limit}
    if not overused:
        return text
    output: list[str] = []
    current_section = "Verse 1"
    replacement_counts: dict[str, int] = {}
    protected_sections = {"Chorus", "Final Chorus"}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped.strip("[]")
            output.append(line)
            continue
        if current_section not in protected_sections and stripped and any(word in stripped for word in overused):
            replacement_counts[current_section] = replacement_counts.get(current_section, 0) + 1
            candidate = _concept_rewrite_line(idea, current_section, replacement_counts[current_section] + 2)
            if _compact_line(candidate) != _compact_line(stripped):
                output.append(candidate)
                continue
        output.append(line)
    return "\n".join(output).strip()


def _ensure_commercial_song_length(idea: str, title: str, hook: str, lyrics: str) -> str:
    sections = parse_lyric_sections(lyrics)
    hook_lines = _lines(improve_hook_singability(hook))
    rendered_sections: dict[str, list[str]] = {}
    for section in COMMERCIAL_SECTION_ORDER:
        lines = [line for line in sections.get(section, []) if line.strip()]
        lines = _dedupe_non_hook_lines(section, lines, hook_lines, idea)
        if section in {"Chorus", "Final Chorus"} and hook_lines:
            existing_joined = "\n".join(lines)
            for hook_line in hook_lines:
                if hook_line and hook_line not in existing_joined:
                    lines.insert(len([line for line in lines if line in hook_lines]), hook_line)
        minimum = COMMERCIAL_SECTION_MIN_LINES.get(section, 1 if section in {"Intro", "Outro"} else 0)
        fill_index = 0
        while len(lines) < minimum:
            candidate = _concept_rewrite_line(idea, section, fill_index, final_payoff=section == "Final Chorus")
            fill_index += 1
            if candidate not in lines:
                lines.append(candidate)
        if section == "Final Chorus":
            chorus_set = set(rendered_sections.get("Chorus", []))
            final_unique = [line for line in lines if line not in chorus_set]
            payoff_index = 0
            attempts = 0
            while len(final_unique) < 2 and attempts < 12:
                candidate = _concept_rewrite_line(idea, section, payoff_index, final_payoff=True)
                payoff_index += 1
                attempts += 1
                if candidate not in lines:
                    lines.append(candidate)
                    final_unique.append(candidate)
            while len(final_unique) < 2:
                candidate = ["ขอให้คืนนี้พาใจฉันไปไกลกว่าเดิม", "ให้พรุ่งนี้เริ่มด้วยใจที่ตรงกว่าเดิม"][len(final_unique) % 2]
                if candidate not in lines:
                    lines.append(candidate)
                final_unique.append(candidate)
            if lines[: len(rendered_sections.get("Chorus", []))] == rendered_sections.get("Chorus", []):
                lines = lines + [
                    _concept_rewrite_line(idea, section, payoff_index + 1, final_payoff=True),
                    _concept_rewrite_line(idea, section, payoff_index + 2, final_payoff=True),
                ]
                lines = _dedupe_non_hook_lines(section, lines, hook_lines, idea)
            unique_final: list[str] = []
            seen_final: set[str] = set()
            for line in lines:
                key = _compact_line(line)
                if key and key not in seen_final:
                    unique_final.append(line)
                    seen_final.add(key)
            lines = unique_final[:10]
            fill_index = 0
            while len(lines) < COMMERCIAL_SECTION_MIN_LINES["Final Chorus"]:
                candidate = _concept_rewrite_line(idea, section, fill_index, final_payoff=True)
                fill_index += 1
                if _compact_line(candidate) not in {_compact_line(line) for line in lines}:
                    lines.append(candidate)
        rendered_sections[section] = lines
    blocks = [f"[{section}]\n" + "\n".join(rendered_sections[section]) for section in COMMERCIAL_SECTION_ORDER]
    return "\n\n".join(blocks).strip()


def _release_pack_quality_checks(title: str, hook: str, lyrics: str, suno_style_prompt: str) -> dict[str, Any]:
    structure = validate_song_structure(lyrics)
    stats = _lyric_line_stats(lyrics)
    sections = parse_lyric_sections(lyrics)
    section_counts = {section: 0 for section in COMMERCIAL_SECTION_ORDER}
    for raw in str(lyrics or "").splitlines():
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section_counts[stripped.strip("[]")] = section_counts.get(stripped.strip("[]"), 0) + 1
    hook_lines = _lines(hook)
    chorus_lines = set(sections.get("Chorus", []))
    final_lines = set(sections.get("Final Chorus", []))
    duplicated_sections = [section for section, count in section_counts.items() if count > 1]
    section_min_ok = all(stats["section_line_counts"].get(section, 0) >= minimum for section, minimum in COMMERCIAL_SECTION_MIN_LINES.items())
    too_short = stats["line_count"] < 24 or not section_min_ok
    return {
        "title_is_generic": score_song_title_candidate(title).get("score", 0) < 55,
        "hook_line_count": len(hook_lines),
        "hook_is_copy_ready": 3 <= len(hook_lines) <= 5 and not _lyrics_have_meta_text(hook),
        "lyrics_line_stats": stats,
        "too_short_lyrics": too_short,
        "structure_validation": structure,
        "duplicated_sections": duplicated_sections,
        "meta_text_inside_lyrics": _lyrics_have_meta_text(lyrics),
        "final_chorus_payoff_lines": len(final_lines - chorus_lines),
        "final_chorus_has_payoff": len(final_lines - chorus_lines) >= 2,
        "suno_style_prompt_english_only": not any("\u0e00" <= ch <= "\u0e7f" for ch in str(suno_style_prompt or "")),
        "ok": (
            not duplicated_sections
            and not _lyrics_have_meta_text(lyrics)
            and not too_short
            and len(final_lines - chorus_lines) >= 2
            and stats["line_count"] >= 24
            and stats["repeated_lines"] <= 8
            and 3 <= len(hook_lines) <= 5
        ),
    }


def generate_creative_release_pack(
    idea: str,
    preset_name: str = "Thai Sad Pop",
    artist_name: str = "Vela Moon",
    *,
    production_mode: bool = False,
    api_key: str = "",
    demo_mode: bool = True,
    provider_status: dict[str, Any] | None = None,
    creative_controls: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = provider_status or build_api_quality_gate(api_key=api_key, demo_mode=(demo_mode and not production_mode))
    if production_mode and not gate.get("ok"):
        return production_blocked_result(gate)

    base_preset = CREATIVE_PACK_PRESETS.get(preset_name, CREATIVE_PACK_PRESETS["Thai Sad Pop"])
    controls = _normalize_creative_controls(creative_controls)
    controls["_preset_name"] = controls.get("_preset_name") or preset_name
    selected_seed = controls.get("selected_seed") if isinstance(controls.get("selected_seed"), dict) else None
    preset = _apply_controls_to_preset(base_preset, controls)
    original_concept = str(idea or "").strip() or preset["mood"]
    situation_seed = None
    if selected_seed and isinstance(selected_seed.get("situation_first_seed"), dict):
        situation_seed = selected_seed.get("situation_first_seed")
    if not situation_seed:
        situation_seed = generate_situation_first_seed(
            original_concept,
            preset_name,
            str(controls.get("mood") or ""),
            str(controls.get("story_type") or ""),
        )
    situation_seed = _rewrite_song_situation_seed(situation_seed, original_concept, preset_name)
    situation_context = _situation_context_text(situation_seed)
    producer_brief = None
    if selected_seed and isinstance(selected_seed.get("producer_brief"), dict):
        producer_brief = selected_seed.get("producer_brief")
    if not producer_brief:
        producer_brief = generate_producer_brief_v1(
            "\n".join([original_concept, situation_context]),
            preset_name,
            str(controls.get("mood") or ""),
            str(controls.get("story_type") or ""),
            situation_seed,
        )
    if selected_seed:
        selected_seed["producer_brief"] = producer_brief
        selected_seed.setdefault("situation_first_seed", situation_seed)
    concept_base = "\n".join([_control_enriched_concept(original_concept, controls), situation_context])
    concept = _seed_enriched_concept(concept_base, selected_seed)
    title = _seed_title(concept, preset_name)
    hook = _hook_from_idea(concept, title, preset)
    hook = _sanitize_hook_text(_apply_hook_style(hook, title, concept, str(controls.get("hook_style") or "")), title, concept)
    title_candidates = generate_song_title_candidates(idea=concept, hook_text=hook)
    original_title = title
    if title_candidates and (
        score_song_title_candidate(title, concept).get("score", 0) < 70
        or _compact_line(title) in {_compact_line(line) for line in _lines(hook)}
        or _compact_line(title) == _compact_line(concept)
    ):
        title = title_candidates[0]["title"]
    title = _authentic_title_from_concept(concept, preset_name, title)
    if selected_seed:
        selected_title = _selected_seed_title(selected_seed, original_concept)
        selected_hook = str(selected_seed.get("hook") or "").strip()
        if selected_title:
            title = selected_title
        if selected_hook:
            hook = _sanitize_hook_text(selected_hook, title, concept, enforce_title=False)
    if title != original_title:
        if not selected_seed:
            hook = _sanitize_hook_text(_apply_hook_style(_hook_from_idea(concept, title, preset), title, concept, str(controls.get("hook_style") or "")), title, concept)
    lyrics = polish_commercial_lyrics(_lyrics(title, hook, concept, preset_name, preset), hook)
    lyrics = _rewrite_disallowed_reused_lines(concept, lyrics)
    lyrics = _ensure_commercial_song_length(concept, title, hook, lyrics)
    lyrics = _apply_selected_story_to_lyrics(lyrics, selected_seed, original_concept)
    concept_alignment = validate_concept_alignment(concept, lyrics)
    if not concept_alignment["aligned"] and _concept_theme(concept) == "respectful_truth":
        hook = improve_hook_singability(_hook_from_idea(concept, title, preset))
        lyrics = polish_commercial_lyrics(_respectful_truth_lyrics(title, hook), hook)
        lyrics = _rewrite_disallowed_reused_lines(concept, lyrics)
        lyrics = _ensure_commercial_song_length(concept, title, hook, lyrics)
        concept_alignment = validate_concept_alignment(concept, lyrics)
    if not validate_song_structure(lyrics)["ok"]:
        lyrics = _ensure_commercial_song_length(concept, title, hook, lyrics)
    lyrics, lyrics_quality_report = _apply_lyrics_quality_engine(title, hook, lyrics, concept)
    if selected_seed and selected_seed.get("hook"):
        lyrics = _enforce_selected_hook_authority(lyrics, str(selected_seed.get("hook") or ""))
    lyrics = _apply_human_experience_engine(lyrics, concept, preset_name)
    lyrics = _apply_emotional_arc_engine(lyrics, concept, preset_name, producer_brief)
    lyrics, thai_natural_speech_report = _apply_thai_natural_speech_engine(lyrics, concept, preset_name, hook)
    title, hook, lyrics, rewrite_report = _rewrite_engine_v1(title, hook, lyrics, concept, preset_name, preset, producer_brief, selected_seed)
    if not selected_seed and str(controls.get("hook_style") or "").strip():
        styled_hook = _sanitize_hook_text(_apply_hook_style(hook, title, concept, str(controls.get("hook_style") or "")), title, concept)
        if styled_hook != hook:
            hook = styled_hook
            lyrics = _enforce_selected_hook_authority(lyrics, hook)
    hook = _enforce_question_hook_style(hook, controls, concept)
    if not selected_seed:
        lyrics = _enforce_selected_hook_authority(lyrics, hook)
    lyrics, thai_natural_speech_report = _apply_thai_natural_speech_engine(lyrics, concept, preset_name, hook)
    lyrics, phrase_diversity_report = _apply_phrase_diversity_engine(lyrics, concept, preset_name)
    lyrics, english_leakage_report = _remove_english_leakage_from_lyrics(lyrics, concept, preset_name)
    lyrics, relatability_target_report = _apply_relatability_target_rewrite(lyrics, hook, concept, preset_name)
    lyrics, thai_natural_speech_report = _apply_thai_natural_speech_engine(lyrics, concept, preset_name, hook)
    lyrics, english_leakage_report = _remove_english_leakage_from_lyrics(lyrics, concept, preset_name)
    lyrics = _reduce_repeated_lines_for_suno(lyrics, hook, concept, preset_name)
    lyrics, thai_natural_speech_report = _apply_thai_natural_speech_engine(lyrics, concept, preset_name, hook)
    lyrics, english_leakage_report = _remove_english_leakage_from_lyrics(lyrics, concept, preset_name)
    lyrics = _apply_situation_to_lyrics(lyrics, situation_seed, hook)
    lyrics = _ensure_concept_keyword_in_lyrics(lyrics, original_concept)
    authentic_thai_speech_report = _authentic_thai_speech_validator(lyrics, concept, preset_name)
    critic_report = _critic_engine_report(title, hook, lyrics, concept, preset_name)
    commercial_score_report = _commercial_score_engine(title, hook, lyrics, concept, preset_name)
    lyrics_quality_report = _lyrics_quality_engine_report(title, hook, lyrics, concept)
    concept_alignment = validate_concept_alignment(concept, lyrics)
    advanced_settings = _apply_advanced_setting_overrides(_advanced_settings_for_preset(preset_name), controls)
    advanced_settings_text = _advanced_settings_to_text(advanced_settings)
    ai_producer_prompt = _build_ai_producer_prompt(preset_name, preset, advanced_settings)
    lyrics_only = _clean_lyric_text(lyrics)
    suno_style_prompt = _build_suno_style_prompt(preset_name, preset, advanced_settings)
    export_quality = _release_pack_quality_checks(title, hook, lyrics_only, suno_style_prompt)
    hook_quality_summary = _hook_quality_summary_text(hook, title, concept)
    human_experience_report = _human_experience_report_text(lyrics_only, concept, preset_name)
    emotional_arc_report = _emotional_arc_report_text(lyrics_only, concept, preset_name, producer_brief)
    thai_natural_speech_report_text = _thai_natural_speech_report_text(thai_natural_speech_report)
    relatability_report = _relatability_report(lyrics_only, hook, concept, preset_name)
    relatability_report_text = _relatability_report_text(relatability_report)
    diversity_report = build_diversity_report(title, hook, lyrics_only, str(controls.get("story_type") or _song_scene_type(concept, preset_name)))
    diversity_report_text = _diversity_report_text(diversity_report)
    situation_specificity_report = _situation_specificity_report_text(situation_seed)
    generated_at = datetime.now().isoformat(timespec="seconds")
    song_info = "\n".join(
        [
            f"Preset: {preset_name}",
            f"Generated: {generated_at}",
            f"Suggested Title: {title}",
            "Hook:",
            hook,
            "Song Concept:",
            f"{original_concept}\nPreset: {preset_name}\nMood: {preset['mood']}\nLyrics direction: {preset.get('lyrics_direction', 'clear emotional progression')}\nHook direction: {preset.get('hook_direction', 'memorable emotional hook')}",
            "Creative Controls:",
            _controls_summary(controls) or "Default quality-first controls",
            "Producer Brief:",
            _producer_brief_to_text(producer_brief),
            "Selected Seed:",
            _selected_seed_summary(selected_seed),
        ]
    )
    hashtags = ["#เพลงไทย", "#เพลงเศร้า", "#ThaiPop", "#VelaFlow", "#TikTokMusic", "#SunoAI", "#เพลงใหม่"]
    if preset_name.startswith("Vela Moon"):
        hashtags.extend(["#VelaMoon", "#ThaiPopRock", "#SpotifyThailand"])
    caption_direction = str(preset.get("caption_direction") or "A warm emotional caption for listeners who still smile while healing inside.")
    pack = {
        "SONG INFO": song_info,
        "Producer Brief": _producer_brief_to_text(producer_brief),
        "Hook Quality Summary": hook_quality_summary,
        "Human Experience Report": human_experience_report,
        "Emotional Arc Report": emotional_arc_report,
        "Thai Natural Speech Report": thai_natural_speech_report_text,
        "Relatability Report": relatability_report_text,
        "Diversity Report": diversity_report_text,
        "Situation Specificity Report": situation_specificity_report,
        "Song concept": f"{original_concept}\nPreset: {preset_name}\nMood: {preset['mood']}\nLyrics direction: {preset.get('lyrics_direction', 'clear emotional progression')}\nHook direction: {preset.get('hook_direction', 'memorable emotional hook')}\nCreative Controls:\n{_controls_summary(controls) or 'Default quality-first controls'}",
        "Selected Seed Summary": _selected_seed_summary(selected_seed),
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
            f"เพลงใหม่จาก VelaFlow concept: {original_concept}\n"
            "อารมณ์เพลงเน้นฮุกจำง่าย เนื้อหาเล่าเรื่องชัด และพร้อมนำไปต่อยอดใน Suno/Udio, Whisk, Flow, Veo, Runway หรือ Kling.\n\n"
            + " ".join(hashtags[:5])
        ),
        "Release notes": "\n".join(
            [
                "Release Pack generated locally by VelaFlow V1.",
                f"Generation Mode: {gate.get('message') or gate.get('status')}",
                "No video rendering, lip sync, cloud render, or encoding was used.",
                "Review lyrics and prompts before publishing.",
                f"Created at: {datetime.now().isoformat(timespec='seconds')}",
            ]
        ),
        "Lyrics Quality Report": _format_lyrics_quality_report(lyrics_quality_report),
        "API Quality Gate": f"Status: {gate.get('status')}\nMessage: {gate.get('message')}\nOffline allowed: {gate.get('offline_allowed')}",
    }
    if preset_name.startswith("Vela Moon"):
        pack["Caption"] = f"{_lines(hook)[0] if _lines(hook) else title}\n\nเพลงนี้สำหรับคนที่ยังฝืนยิ้ม ทั้งที่ข้างในอยากพักใจ"
    pack = _clean_release_pack_text(pack)
    title = str(pack.get("Suggested title") or title)
    hook = str(pack.get("Hook") or hook)
    lyrics = str(pack.get("Full lyrics") or lyrics)
    _update_diversity_memory(title, hook, lyrics_only, str(controls.get("story_type") or _song_scene_type(concept, preset_name)), situation=situation_seed)
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
            "export_quality": export_quality,
            "lyrics_quality_engine": lyrics_quality_report,
            "thai_natural_speech": thai_natural_speech_report,
            "relatability": relatability_report,
            "diversity": diversity_report,
            "situation_first": situation_seed,
            "human_lyric_authenticity_v2": {
                "phrase_diversity": phrase_diversity_report,
                "english_leakage": english_leakage_report,
                "relatability_target": relatability_target_report,
                "authentic_thai_speech": authentic_thai_speech_report,
            },
            "critic_engine": critic_report,
            "rewrite_engine": rewrite_report,
            "commercial_score_engine": commercial_score_report,
            "producer_brief": producer_brief,
            "api_quality_gate": gate,
            "creative_controls": controls,
        },
        "generated_at": generated_at,
        "provider_status": gate,
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
            f"Provider Status: {(result.get('provider_status') or {}).get('status', '-')}",
            f"Generation Mode: {((result.get('provider_status') or {}).get('message') or '-')}",
            f"Suggested Title: {title}",
            "Hook:",
            hook,
            "Song Concept:",
            concept,
            "Selected Seed Summary:",
            str(pack.get("Selected Seed Summary", "")).strip(),
        ]
    )
    sections = [
        "VELAFLOW AI CREATIVE RELEASE PACK",
        song_info,
        "2. PRODUCER BRIEF\n" + str(pack.get("Producer Brief", "")).strip(),
        "3. HOOK QUALITY SUMMARY\n" + str(pack.get("Hook Quality Summary", "")).strip(),
        "4. HUMAN EXPERIENCE REPORT\n" + str(pack.get("Human Experience Report", "")).strip(),
        "5. EMOTIONAL ARC REPORT\n" + str(pack.get("Emotional Arc Report", "")).strip(),
        "6. THAI NATURAL SPEECH REPORT\n" + str(pack.get("Thai Natural Speech Report", "")).strip(),
        "7. RELATABILITY REPORT\n" + str(pack.get("Relatability Report", "")).strip(),
        "8. DIVERSITY REPORT\n" + str(pack.get("Diversity Report", "")).strip(),
        "9. SITUATION SPECIFICITY REPORT\n" + str(pack.get("Situation Specificity Report", "")).strip(),
        "10. SUNO LYRICS FIELD\n" + str(pack.get("SUNO LYRICS FIELD") or _clean_lyric_text(pack.get("Full lyrics", ""))).strip(),
        "11. SUNO STYLE OF MUSIC FIELD\n" + str(pack.get("SUNO STYLE OF MUSIC FIELD", "")).strip(),
        "12. PRODUCER NOTES\n" + str(pack.get("PRODUCER NOTES") or pack.get("AI PRODUCER PROMPT", "")).strip(),
        "13. ADVANCED SUNO SETTINGS\n" + str(pack.get("Advanced Suno Settings", "")).strip(),
        "14. COVER PROMPT\n" + str(pack.get("Cover prompt", "")).strip(),
        "15. MV STORYBOARD PROMPT\n" + str(pack.get("MV storyboard prompt", "")).strip(),
        "16. SHORTS / TIKTOK IDEAS\n" + str(pack.get("Shorts/TikTok ideas", "")).strip(),
        "17. CAPTION\n" + str(pack.get("Caption", "")).strip(),
        "18. HASHTAGS\n" + str(pack.get("Hashtags", "")).strip(),
        "19. YOUTUBE DESCRIPTION\n" + str(pack.get("YouTube description", "")).strip(),
        "20. RELEASE NOTES\n" + str(pack.get("Release notes", "")).strip(),
        "21. LYRICS QUALITY REPORT\n" + str(pack.get("Lyrics Quality Report", "")).strip(),
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
            "provider_status": result.get("provider_status") or {},
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
