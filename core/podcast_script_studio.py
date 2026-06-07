from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from providers.gemini_provider import GeminiProvider


PODCAST_SCRIPT_TONES = ["Vela After Work", "Dark Humor", "Emotional", "Motivational", "Storytelling", "Office Rant"]
PODCAST_NARRATORS = ["Male", "Female"]
PODCAST_EPISODE_LENGTHS = ["10 min", "20 min", "30 min"]

REQUIRED_PODCAST_SCRIPT_SECTIONS = [
    "Episode Title",
    "Cold Open",
    "Full Podcast Script",
    "AI Voice Version",
    "Viral Rant Engine",
    "Shorts Extraction",
    "YouTube Package",
    "Spotify Package",
    "Thumbnail Prompt",
    "AI Video Prompt",
]

WORD_TARGETS = {
    "10 min": {"min": 1500, "max": 2000, "target": 1650, "shorts": 10},
    "20 min": {"min": 3500, "max": 4300, "target": 3700, "shorts": 10},
    "30 min": {"min": 5000, "max": 6200, "target": 5200, "shorts": 10},
}


def _clean(value: str, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _word_count(text: str) -> int:
    return len([part for part in str(text or "").replace("\n", " ").split(" ") if part.strip()])


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip().replace("```json", "```").replace("```JSON", "```")
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _tone_profile(tone: str) -> dict[str, str]:
    profiles = {
        "Vela After Work": {
            "style": "office life, workplace politics, burnout, unspoken office stories, dark humor, relatable emotional storytelling",
            "voice": "เล่าเหมือนคนทำงานนั่งคุยหลังเลิกงาน เหนื่อยจริง ตลกร้ายจริง แต่ยังอ่อนโยนกับคนฟัง",
        },
        "Dark Humor": {
            "style": "dry office humor, quiet sarcasm, emotional truth under a tired smile",
            "voice": "ขำแห้งแบบคนที่ยังต้องเปิดคอมพรุ่งนี้ ทั้งที่ใจอยากปิดระบบทั้งชีวิต",
        },
        "Emotional": {
            "style": "soft emotional storytelling, vulnerable reflection, human workplace loneliness",
            "voice": "เล่านุ่ม ลึก ไม่เร่ง ให้คนฟังมีพื้นที่นึกถึงตัวเอง",
        },
        "Motivational": {
            "style": "grounded encouragement, no fake hustle, quiet self-respect",
            "voice": "ให้กำลังใจแบบไม่ขายฝัน เหมือนเพื่อนร่วมงานที่รู้ว่าเราเหนื่อยจริง",
        },
        "Storytelling": {
            "style": "scene-based office story, cinematic but conversational",
            "voice": "เล่าเป็นฉาก มีโต๊ะทำงาน ไฟเพดาน แชตค้าง และความเงียบหลังเลิกงาน",
        },
        "Office Rant": {
            "style": "sharp workplace rant, honest, contained anger, still human",
            "voice": "ระบายตรง คม แต่ไม่หยาบพร่ำเพรื่อ เหมือนพูดในรถหลังประชุมจบ",
        },
    }
    return profiles.get(tone, profiles["Vela After Work"])


def _narrator_voice(narrator: str) -> str:
    if narrator == "Female":
        return "เสียงผู้หญิงอบอุ่น นิ่ง เหนื่อยนิด ๆ แต่ชัดเจน เว้นวรรคเหมือนกำลังเล่าเรื่องที่เก็บมาทั้งวัน"
    return "เสียงผู้ชายอบอุ่น ปนเหนื่อยเล็ก ๆ เล่าเหมือนนั่งคุยกันหลังปิดคอม ไม่ประกาศ ไม่ฝืนสดใส"


def _title_candidates(topic: str, tone: str) -> list[str]:
    core = topic.strip(" .") or "เรื่องหลังเลิกงาน"
    candidates = [
        "หลังเลิกงานค่อยรู้สึก",
        "ประชุมจบ แต่ใจไม่จบ",
        "เรื่องที่เราไม่พูดในออฟฟิศ",
        "วันที่งานไม่ใช่เรื่องหนักที่สุด",
        "โต๊ะทำงานที่เก็บความเงียบไว้",
        "ยิ้มให้ทั้งวัน แล้วพังคนเดียว",
        "ชีวิตที่ซ่อนอยู่ในปฏิทินงาน",
        "สิ่งที่คนทำงานไม่ค่อยพูด",
        f"{core} หลังหกโมงเย็น",
        "ไม่ได้หมดไฟ แค่หมดใจ",
    ]
    if tone == "Dark Humor":
        candidates.insert(0, "ขำไม่ออก แต่ต้องส่งงาน")
    if tone == "Office Rant":
        candidates.insert(0, "ไม่ใช่งานหนัก แต่คนมันหนัก")
    if tone == "Motivational":
        candidates.insert(0, "เหนื่อยได้ แต่อย่าหายไป")
    if tone == "Vela After Work":
        candidates.insert(0, "เรื่องที่คิดหลังปิดคอม")
    return candidates


def _score_title(title: str, topic: str) -> int:
    score = 70
    if 2 <= len(title.split()) <= 8:
        score += 10
    if any(token in title for token in ["หลังเลิกงาน", "ไม่พูด", "ไม่จบ", "หมดใจ", "ปิดคอม"]):
        score += 14
    if title.strip() == topic.strip() or len(title.strip()) <= 3:
        score -= 50
    if len(title) > 44:
        score -= 10
    return max(0, min(100, score))


def _best_title(topic: str, tone: str) -> str:
    scored = sorted(((candidate, _score_title(candidate, topic)) for candidate in _title_candidates(topic, tone)), key=lambda item: item[1], reverse=True)
    return scored[0][0]


def _narrator_pronoun(narrator: str) -> str:
    return "ผม"


def _topic_aliases() -> list[str]:
    return [
        "เรื่องนี้",
        "ความรู้สึกนั้น",
        "สิ่งที่ค้างอยู่ในใจ",
        "ประเด็นที่ไม่มีใครพูดตรง ๆ",
        "ความเหนื่อยแบบนี้",
        "เรื่องเล็กที่ไม่เล็ก",
    ]


def _story_context(topic: str, tone: str) -> dict[str, str]:
    return {
        "topic": topic,
        "main_narrator": "ผม",
        "support_1": "เมย์",
        "support_1_role": "รุ่นน้องฝ่ายคอนเทนต์ที่ชอบขอโทษก่อนอธิบาย",
        "support_2": "พี่นนท์",
        "support_2_role": "หัวหน้าทีมที่พูดเบา แต่ทำให้ทั้งห้องเกร็งได้",
        "support_3": "พี่อร",
        "support_3_role": "HR ที่มักส่งข้อความด้วยถ้อยคำสุภาพจนอ่านแล้วเหนื่อยกว่าเดิม",
        "location": "ห้องประชุมกระจกข้าง pantry ชั้นสิบสอง",
        "incident": "รายงาน Excel เมื่อวานถูกเปิดขึ้นกลางประชุม แล้วชื่อคนทำงานจริงหายไปจากสไลด์สรุป",
        "first_message": "ขอคุยเรื่องรายงานเมื่อวานหน่อย",
        "politics": "ทุกคนรู้ว่าไฟล์ถูกแก้หลายรอบ แต่ไม่มีใครอยากพูดว่าใครเป็นคนสั่งแก้ เพราะคนสั่งแก้นั่งอยู่หัวโต๊ะ",
        "peak": "ห้องประชุมเงียบไปประมาณสามวินาที หลังจากพี่นนท์ถามว่า อันนี้ใครเป็นคนทำ",
        "after_work_place": "ลานจอดรถหลังฝนตก",
        "tone": tone,
    }


def _local_story_blueprint(topic: str, tone: str) -> dict[str, Any]:
    context = _story_context(topic, tone)
    return {
        "source": "local_fallback",
        "main_narrator_profile": {
            "name": "ผม",
            "role": "พนักงานออฟฟิศที่เหนื่อยแต่ยังพยายามเล่าเรื่องให้ตรง",
            "voice": "เล่าเหมือนเพื่อนร่วมงานคุยกันหลังเลิกงาน เหนื่อยนิด ๆ ประชดเบา ๆ แต่ไม่ดราม่าเกินจริง",
        },
        "supporting_characters": [
            {"name": context["support_1"], "role": context["support_1_role"], "tension": "คนทำงานจริงแต่ชื่อมักหายไปจากเครดิต"},
            {"name": context["support_2"], "role": context["support_2_role"], "tension": "หัวหน้าที่ใช้ความสุภาพทำให้คนอื่นพูดยาก"},
            {"name": context["support_3"], "role": context["support_3_role"], "tension": "คนกลางที่ถามว่าไม่เป็นไรใช่ไหม แต่ไม่ได้เปิดทางให้ตอบจริง"},
        ],
        "office_environment": context["location"],
        "conflict": context["incident"],
        "emotional_peak": context["peak"],
        "resolution": "ผมพิมพ์ข้อความขอใส่ชื่อคนเตรียมข้อมูลไว้ใน note ของสไลด์ แทนการรับทราบเงียบ ๆ เหมือนทุกครั้ง",
        "takeaway": "บางครั้งการไม่ปล่อยให้เครดิตของคนทำงานหายไป คือการปกป้องความเป็นมนุษย์เล็ก ๆ ในระบบงาน",
        "story_arc": [
            "เช้าวันทำงานธรรมดาเริ่มจากลิฟต์ กาแฟ และ work chat",
            "รายงาน Excel ถูกเปิดกลางประชุม แล้วชื่อคนทำงานจริงหายไป",
            "ห้องประชุมเงียบ ทุกคนรู้แต่ไม่มีใครอยากพูด",
            "การเมืองในทีมเริ่มชัดผ่านประโยคสุภาพและเครดิตที่หายไป",
            "เมย์พูดที่โต๊ะกินข้าวว่าไม่รู้ว่าครั้งหน้าควรทำเต็มที่แค่ไหน",
            "หลังเลิกงาน ผมยืนในลานจอดรถและตัดสินใจว่าครั้งหน้าจะไม่เงียบแบบเดิม",
        ],
        "scene_breakdown": [
            {"section": "Cold Open", "location": "ลิฟต์", "scene": "กาแฟในมือและแชตงานเด้งก่อนถึงโต๊ะ", "dialogue": context["first_message"]},
            {"section": "Act 1", "location": "โต๊ะทำงาน", "scene": "จอ Excel, printer, shared folder final_v7", "dialogue": "รายงานเมื่อวานอยู่ไหนนะ"},
            {"section": "Act 2", "location": context["location"], "scene": "สไลด์สรุปที่ชื่อคนทำงานหายไป", "dialogue": "อันนี้ใครเป็นคนทำ"},
            {"section": "Act 3", "location": context["location"], "scene": "ห้องประชุมเงียบไปประมาณสามวินาที", "dialogue": "เดี๋ยวคุยกันหลังประชุม"},
            {"section": "Act 4", "location": "หน้าห้องประชุม", "scene": "HR ถามด้วยเสียงสุภาพ", "dialogue": "ไม่เป็นไรใช่ไหม"},
            {"section": "Act 5", "location": "โต๊ะกินข้าว", "scene": "เมย์เขี่ยข้าวและพูดสิ่งที่เหนื่อยมานาน", "dialogue": "หนูไม่รู้ว่าครั้งหน้าควรทำเต็มที่แค่ไหน"},
            {"section": "Act 6", "location": context["after_work_place"], "scene": "ฝนหยุดตก มือถือมี unread messages", "dialogue": "ขอใส่ชื่อคนเตรียมข้อมูลไว้ใน note ด้วยนะครับ"},
        ],
        "context": context,
    }


def _gemini_story_prompt(topic: str, tone: str, episode_length: str) -> str:
    return f"""
You are the story brain for Vela After Work, a Thai office-life podcast.
Create a realistic story blueprint BEFORE the final podcast script.

Topic:
{topic}

Tone:
{tone}

Episode length:
{episode_length}

Required style:
- Thai first-person office storytelling.
- Feels like a tired coworker telling a real story after work.
- Human, tired, slightly sarcastic, emotionally honest.
- Concrete scenes, natural dialogue, office politics.
- Do not write generic self-help.
- Do not repeat the topic name.
- Avoid these phrases: จุดเปลี่ยนคือ, บทเรียนคือ, เริ่มจากจุดที่หลายคนคุ้น, สิ่งที่ทำให้.

Return JSON only with this schema:
{{
  "main_narrator_profile": {{"name":"ผม","role":"","voice":""}},
  "supporting_characters": [
    {{"name":"","role":"","tension":""}},
    {{"name":"","role":"","tension":""}},
    {{"name":"","role":"","tension":""}}
  ],
  "office_environment": "",
  "conflict": "",
  "emotional_peak": "",
  "resolution": "",
  "takeaway": "",
  "story_arc": ["", "", "", "", "", ""],
  "scene_breakdown": [
    {{"section":"Cold Open","location":"","scene":"","dialogue":""}},
    {{"section":"Act 1","location":"","scene":"","dialogue":""}},
    {{"section":"Act 2","location":"","scene":"","dialogue":""}},
    {{"section":"Act 3","location":"","scene":"","dialogue":""}},
    {{"section":"Act 4","location":"","scene":"","dialogue":""}},
    {{"section":"Act 5","location":"","scene":"","dialogue":""}},
    {{"section":"Act 6","location":"","scene":"","dialogue":""}}
  ]
}}
"""


def _normalize_story_blueprint(raw: dict[str, Any], topic: str, tone: str) -> dict[str, Any]:
    fallback = _local_story_blueprint(topic, tone)
    if not raw:
        return fallback
    context = dict(fallback["context"])
    narrator = raw.get("main_narrator_profile") if isinstance(raw.get("main_narrator_profile"), dict) else fallback["main_narrator_profile"]
    characters = raw.get("supporting_characters") if isinstance(raw.get("supporting_characters"), list) else fallback["supporting_characters"]
    characters = [item for item in characters if isinstance(item, dict) and item.get("name")] or fallback["supporting_characters"]
    scenes = raw.get("scene_breakdown") if isinstance(raw.get("scene_breakdown"), list) else fallback["scene_breakdown"]
    scenes = [item for item in scenes if isinstance(item, dict)] or fallback["scene_breakdown"]
    if characters:
        context["support_1"] = str(characters[0].get("name") or context["support_1"]).strip()
        context["support_1_role"] = str(characters[0].get("role") or context["support_1_role"]).strip()
    if len(characters) > 1:
        context["support_2"] = str(characters[1].get("name") or context["support_2"]).strip()
        context["support_2_role"] = str(characters[1].get("role") or context["support_2_role"]).strip()
    if len(characters) > 2:
        context["support_3"] = str(characters[2].get("name") or context["support_3"]).strip()
        context["support_3_role"] = str(characters[2].get("role") or context["support_3_role"]).strip()
    context["location"] = str(raw.get("office_environment") or context["location"]).strip()
    context["incident"] = str(raw.get("conflict") or context["incident"]).strip()
    context["peak"] = str(raw.get("emotional_peak") or context["peak"]).strip()
    first_dialogue = next((str(scene.get("dialogue") or "").strip() for scene in scenes if scene.get("dialogue")), "")
    if first_dialogue:
        context["first_message"] = first_dialogue.strip('"')
    return {
        "source": "gemini",
        "main_narrator_profile": narrator,
        "supporting_characters": characters[:4],
        "office_environment": context["location"],
        "conflict": context["incident"],
        "emotional_peak": context["peak"],
        "resolution": str(raw.get("resolution") or fallback["resolution"]).strip(),
        "takeaway": str(raw.get("takeaway") or fallback["takeaway"]).strip(),
        "story_arc": raw.get("story_arc") if isinstance(raw.get("story_arc"), list) and raw.get("story_arc") else fallback["story_arc"],
        "scene_breakdown": scenes[:8],
        "context": context,
    }


def _generate_story_blueprint(topic: str, tone: str, episode_length: str, gemini_api_key: str | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    provider = GeminiProvider(api_key=gemini_api_key)
    diagnostics = {
        "provider": "gemini",
        "model": provider.model,
        "used": "false",
        "fallback_reason": "",
    }
    if not provider.available:
        diagnostics["fallback_reason"] = provider.last_error or "GEMINI_API_KEY missing"
        return _local_story_blueprint(topic, tone), diagnostics
    text = provider.generate_text(_gemini_story_prompt(topic, tone, episode_length))
    if not text:
        diagnostics["fallback_reason"] = provider.last_error or "Gemini returned empty story blueprint"
        return _local_story_blueprint(topic, tone), diagnostics
    parsed = _extract_json_object(text)
    if not parsed:
        diagnostics["fallback_reason"] = "Gemini story blueprint was not valid JSON"
        return _local_story_blueprint(topic, tone), diagnostics
    diagnostics["used"] = "true"
    return _normalize_story_blueprint(parsed, topic, tone), diagnostics


def _office_scene_detail(index: int) -> str:
    scenes = [
        "ตอนนั้นไฟฟลูออเรสเซนต์บนเพดานยังสว่างเกินไป ทั้งที่คนในแผนกเริ่มกลับกันเกือบหมดแล้ว",
        "แก้วกาแฟบนโต๊ะเย็นจนจืด แต่มือยังจับมันไว้เหมือนต้องการอะไรสักอย่างให้ไม่ว่าง",
        "เสียงแชตงานเด้งขึ้นมาตอนใกล้เลิกงาน มันสั้นมาก แต่ทำให้บรรยากาศทั้งเย็นเปลี่ยนไปทันที",
        "ในลิฟต์หลังหกโมง ทุกคนยืนเงียบเหมือนกลัวว่าถ้าพูดออกมา ความเหนื่อยจะหลุดออกมาด้วย",
        "จอ Excel ยังเปิดค้างอยู่ แสงจากหน้าจอส่องหน้าเราแบบที่ทำให้รู้สึกเหมือนยังไม่หมดเวร",
        "ลานจอดรถหลังฝนตกเงียบกว่าปกติ และบางทีความเงียบนั่นแหละที่ทำให้เราได้ยินตัวเองชัดขึ้น",
        "บัตรพนักงานกระทบขอบโต๊ะเบา ๆ ตอนเก็บของ เสียงเล็กแค่นั้นกลับทำให้รู้ว่าวันนี้เราใช้แรงไปเยอะมาก",
        "ในห้องประชุมที่เพิ่งปิดโปรเจกเตอร์ กลิ่นแอร์เย็น ๆ ยังอยู่ แต่คำบางคำยังค้างอยู่ในอก",
    ]
    return scenes[index % len(scenes)]


def _human_transition(section: str, narrator: str, index: int) -> str:
    pronoun = _narrator_pronoun(narrator)
    transitions = {
        "Setup": [
            f"{pronoun}นั่งอยู่หน้าโต๊ะทำงานตอนนั้น และไม่ได้รู้ทันทีว่าวันนั้นจะกลายเป็นเรื่องที่จำได้ แค่รู้ว่ามันมีอะไรบางอย่างไม่เหมือนเดิม",
            f"ถ้าเล่าให้ตรงที่สุด {pronoun}คิดว่ามันเริ่มจากรายละเอียดเล็กมาก จนตอนแรกยังไม่กล้าเรียกว่าปัญหา",
        ],
        "Conflict": [
            f"ช่วงที่ยากไม่ใช่ตอนมีคนพูดแรง แต่เป็นตอนที่ {pronoun}ต้องแกล้งทำเหมือนไม่มีอะไรเกิดขึ้น",
            f"ความขัดแย้งแบบนี้ไม่ดัง แต่มันกัดช้า ๆ และคนฟังอาจรู้จักมันดีเกินกว่าจะต้องอธิบายยาว",
        ],
        "Escalation": [
            f"จากเรื่องที่ควรจบในห้องประชุม มันค่อย ๆ ตาม {pronoun} ออกมาถึงโต๊ะทำงาน ถึงลิฟต์ และถึงทางกลับบ้าน",
            f"ตอนแรก {pronoun}คิดว่าปล่อยผ่านได้ แต่พอมีแชตใหม่ มีประชุมใหม่ มีสีหน้าเดิม มันเริ่มไม่ใช่เรื่องเล็กแล้ว",
        ],
        "Emotional Breakdown": [
            f"พอถึงจุดหนึ่ง {pronoun}ไม่ได้อยากชนะใครแล้ว แค่อยากกลับถึงบ้านโดยไม่ต้องเข้มแข็งต่อ",
            f"มันมีวินาทีหนึ่งที่หน้าตายังนิ่ง แต่ข้างในเหมือนเอกสารทั้งกองหล่นลงพื้นพร้อมกัน",
        ],
        "Reflection": [
            f"พอมองย้อนกลับไป {pronoun}ไม่ได้เห็นแค่คนอื่นผิด เห็นตัวเองที่ฝืนเงียบอยู่นานเกินไปด้วย",
            f"สิ่งที่น่ากลัวคือเราชินกับการบอกว่าไม่เป็นไร จนลืมถามตัวเองว่าจริง ๆ แล้วเป็นอะไร",
        ],
        "Takeaway": [
            f"{pronoun}ไม่ได้อยากให้เรื่องนี้จบด้วยคำสอนสวย ๆ แค่อยากให้มันจบด้วยความซื่อสัตย์กับตัวเองมากขึ้น",
            "บางทีการดูแลใจตัวเองไม่ได้เริ่มจากการลาออก แต่มันเริ่มจากการยอมรับว่าเราเหนื่อยจริง",
        ],
        "Act 1: The Ordinary Office Day": [
            f"ผมจำได้ว่าวันนั้นมันเริ่มธรรมดามาก ธรรมดาจนถ้าไม่มีเรื่องหลังจากนั้น ผมคงลืมไปแล้วด้วยซ้ำ",
            f"ตอนนั้นผมนั่งอยู่กับเสียงแอร์ เสียงคีย์บอร์ด และความรู้สึกเล็ก ๆ ว่าวันนี้อาจไม่จบง่าย",
        ],
        "Act 2: The Incident": [
            f"พอไฟล์ถูกเปิดขึ้นบนจอ ผมรู้ทันทีว่ามีบางอย่างหายไป และมันไม่ใช่แค่ชื่อในสไลด์",
            f"เหตุการณ์จริงเริ่มตรงนั้น ตรงที่ทุกคนเห็นเหมือนกัน แต่ไม่มีใครอยากเป็นคนแรกที่พูด",
        ],
        "Act 3: The Awkward Silence": [
            f"ผมไม่ได้ตอบทันที เพราะความเงียบในห้องนั้นมันเหมือนมีน้ำหนักของมันเอง",
            f"ห้องประชุมเงียบไปประมาณสามวินาที และสามวินาทีนั้นทำให้ผมเข้าใจว่าออฟฟิศบางทีก็ดังที่สุดตอนไม่มีใครพูด",
        ],
        "Act 4: The Office Politics": [
            f"หลังจากนั้นเรื่องไม่ได้อยู่ที่ไฟล์แล้ว แต่อยู่ที่ว่าใครมีสิทธิ์พูดความจริงโดยไม่ถูกมองว่าเรื่องมาก",
            f"ผมเริ่มเห็นเกมเล็ก ๆ ในออฟฟิศชัดขึ้น เกมที่ไม่มีใครบอกว่ากำลังเล่น แต่ทุกคนรู้กติกา",
        ],
        "Act 5: The Breaking Point": [
            f"จังหวะที่ผมเริ่มไม่ไหวไม่ได้ดังเลย มันเป็นแค่ประโยคเบา ๆ จากคนที่เหนื่อยมานาน",
            f"ตอนนั้นผมนั่งอยู่เฉย ๆ แต่ข้างในเหมือนมีอะไรบางอย่างเดินมาถึงเส้นสุดท้าย",
        ],
        "Act 6: After Work Reflection": [
            f"หลังเลิกงาน ผมไม่ได้รู้สึกชนะหรือแพ้ ผมแค่รู้สึกว่าเรื่องนั้นยังเดินตามผมออกมาถึงลานจอดรถ",
            f"พอออกจากตึก ผมถึงเพิ่งได้ยินความคิดตัวเองชัดขึ้นกว่าทั้งวัน",
        ],
        "Ending": [
            f"คืนนี้ถ้าคุณฟังอยู่ระหว่างเดินทางกลับบ้าน {pronoun}จะเล่าให้จบแบบที่เพื่อนร่วมงานคนหนึ่งพูดกับอีกคนหลังปิดคอม",
            "และถ้าพรุ่งนี้ยังต้องกลับไปที่เดิม เรื่องนี้ก็ยังควรถูกจำในแบบที่มันเกิดขึ้นจริง",
        ],
    }
    options = transitions.get(section, transitions["Reflection"])
    return options[index % len(options)]


def _humanize_paragraph(base: str, section: str, topic: str, tone: str, narrator: str, index: int) -> str:
    pronoun = _narrator_pronoun(narrator)
    alias = _topic_aliases()[index % len(_topic_aliases())]
    text = base
    if topic and index % 2 == 1:
        text = text.replace(topic, alias, 1)
    if index % 2 == 0:
        text = f"{_office_scene_detail(index)} {text}"
    if index % 3 != 1:
        text = f"{_human_transition(section, narrator, index)} {text}"
    if tone in {"Dark Humor", "Office Rant", "Vela After Work"} and index % 4 == 2:
        text += f" ตลกร้ายตรงที่ {pronoun}ยังต้องพิมพ์คำว่า รับทราบ ให้ดูสุภาพที่สุด ทั้งที่ในใจอยากพิมพ์ว่า ขอเป็นมนุษย์ก่อนสักห้านาทีได้ไหม"
    return text


def _avoid_topic_repeat(text: str, topic: str, max_mentions: int = 5) -> str:
    topic = str(topic or "").strip()
    if not topic:
        return text
    parts = text.split(topic)
    if len(parts) <= max_mentions + 1:
        return text
    aliases = _topic_aliases()
    rebuilt = [parts[0]]
    for index, part in enumerate(parts[1:], start=1):
        replacement = topic if index <= max_mentions else aliases[index % len(aliases)]
        rebuilt.append(replacement + part)
    return "".join(rebuilt)


def _dedupe_exact_paragraphs(text: str) -> str:
    seen: set[str] = set()
    rows: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            rows.append("")
            continue
        if line.startswith("[") and line.endswith("]"):
            rows.append(line)
            continue
        key = re.sub(r"\s+", " ", line).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(line)
    cleaned = "\n".join(rows)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()


def _long_form_detail_paragraph(section: str, index: int, context: dict[str, str]) -> str:
    office_objects = [
        "แก้วกาแฟที่เย็นจนจืด",
        "ไฟห้องประชุมที่สว่างเกินจำเป็น",
        "เสียงแอร์ที่ดังเหมือนกลบความเงียบ",
        "ไฟล์ Excel ที่ชื่อเหมือน final แต่ไม่เคย final",
        "แจ้งเตือนแชตงานที่เด้งหลังหกโมง",
        "เก้าอี้ใน pantry ที่ไม่มีใครอยากนั่งนาน",
        "ลิฟต์ที่ทุกคนยืนเงียบเกินปกติ",
        "เครื่องพิมพ์ที่ค้างกระดาษเหมือนค้างอารมณ์",
        "โต๊ะกินข้าวที่บทสนทนาหายไปครึ่งหนึ่ง",
        "ลานจอดรถที่ฝนเพิ่งหยุดตก",
    ]
    inner_states = [
        "ผมไม่ได้โกรธทันที แค่รู้สึกเหมือนแรงในตัวค่อย ๆ ลดลง",
        "ตอนนั้นผมยิ้มได้ แต่ไม่แน่ใจว่าตัวเองยังโอเคจริงไหม",
        "ผมนั่งฟังอยู่เงียบ ๆ เพราะบางประโยคถ้าเถียงทันทีจะกลายเป็นเรื่องใหญ่",
        "สิ่งที่หนักไม่ใช่งาน แต่เป็นการทำเหมือนเรื่องนั้นไม่มีน้ำหนัก",
        "ผมจำได้ว่ามือยังอยู่บนคีย์บอร์ด แต่หัวไม่ได้อยู่กับหน้าจอแล้ว",
        "ความตลกร้ายคือทุกคนสุภาพมาก จนไม่มีใครต้องรับผิดชอบอะไรตรง ๆ",
        "ผมไม่ได้อยากชนะใคร แค่อยากให้ความจริงไม่ถูกเลื่อนออกไปอีกวัน",
        "ตอนนั้นผมเริ่มเข้าใจว่าความเงียบในออฟฟิศบางทีมันดังมาก",
        "มีบางวินาทีที่ผมอยากปิดคอมแล้วเดินออกไปโดยไม่ต้องอธิบายอะไร",
        "แต่สุดท้ายผมก็ยังนั่งอยู่ตรงนั้น เพราะชีวิตคนทำงานมักไม่ให้ฉากจบสวย ๆ ง่ายขนาดนั้น",
    ]
    character = [context.get("support_1", "เมย์"), context.get("support_2", "พี่นนท์"), context.get("support_3", "พี่อร")][index % 3]
    return (
        f"ในช่วง {section.replace('Act ', 'องก์ ')} ความทรงจำชิ้นที่ {index + 1} ที่ยังติดอยู่กับผมคือ {office_objects[index % len(office_objects)]}. "
        f"{inner_states[index % len(inner_states)]} "
        f"{character} ไม่ได้พูดอะไรยาว แค่ขยับตัวนิดเดียว แล้วบรรยากาศในห้องก็เปลี่ยนเหมือนทุกคนรู้พร้อมกันว่าเรื่องนี้ไม่ได้จบในประชุม."
    )


def _section_bank_key(section: str) -> str:
    return {
        "Setup": "Act 1: Setup",
        "Conflict": "Act 2: Conflict",
        "Escalation": "Act 2: Conflict",
        "Emotional Breakdown": "Act 3: Emotional Breakdown",
        "Reflection": "Act 4: Reflection",
        "Takeaway": "Act 5: Takeaway",
        "Act 1: The Ordinary Office Day": "Act 1: The Ordinary Office Day",
        "Act 2: The Incident": "Act 2: The Incident",
        "Act 3: The Awkward Silence": "Act 3: The Awkward Silence",
        "Act 4: The Office Politics": "Act 4: The Office Politics",
        "Act 5: The Breaking Point": "Act 5: The Breaking Point",
        "Act 6: After Work Reflection": "Act 6: After Work Reflection",
        "Ending": "Ending",
    }.get(section, section)


def _cold_open(topic: str, tone: str, context: dict[str, str] | None = None) -> str:
    context = context or _story_context(topic, tone)
    if tone == "Dark Humor":
        specific = "ถ้าชีวิตการทำงานมีปุ่ม mute เราคงกดค้างไว้ตั้งแต่บ่ายสาม"
    elif tone == "Office Rant":
        specific = "บางวันเราไม่ได้อยากลาออกจากงาน แค่อยากลาออกจากความอดทนที่ถูกใช้งานหนักเกินไป"
    else:
        specific = "บางวันเราเดินออกจากออฟฟิศแล้วรู้สึกเหมือนยังมีทั้งห้องประชุมเดินตามกลับบ้าน"
    return "\n".join(
        [
            "เช้าวันนั้น ผมเดินเข้าลิฟต์พร้อมกาแฟแก้วเดิมในมือ",
            "หน้าจอมือถือเด้งแจ้งเตือนจากกรุ๊ปงานตั้งแต่ยังไม่ถึงโต๊ะ",
            f"ประโยคแรกที่ผมเห็นคือ \"{context['first_message']}\"",
            f"ผมยืนอ่านมันอยู่ใต้ไฟฟลูออเรสเซนต์ที่สว่างเกินจำเป็น แล้วได้ยินเสียงเครื่องปรับอากาศในลิฟต์ดังเหมือนกำลังช่วยกลบความเงียบ",
            f"วันนั้นมี {context['support_1']} ยืนอยู่ข้างผม เธอมองหน้าจอของตัวเองแล้วพูดเบา ๆ ว่า \"พี่เห็นแชตหรือยัง\"",
            f"ผมไม่ได้ตอบทันที เพราะในหัวผมกำลังนึกถึง {context['incident']}",
            specific,
            "นี่ไม่ใช่เรื่องสอนใจ ไม่ใช่เรื่องให้ใครเลือกข้าง และไม่ใช่เรื่องดราม่าใหญ่โต",
            "มันเป็นแค่เช้าวันทำงานธรรมดา ที่ค่อย ๆ ทำให้คนคนหนึ่งรู้ว่าความเงียบในออฟฟิศบางทีมันเสียงดังมาก",
        ]
    )


def _story_act_bank(section: str, context: dict[str, str]) -> list[str]:
    return {
        "Act 1: The Ordinary Office Day": [
            f"ผมนั่งอยู่หน้าโต๊ะทำงานตอนนั้น แก้วกาแฟยังวางอยู่ข้างคีย์บอร์ด และจอ Excel ก็เปิดค้างอยู่เหมือนทุกเช้า {context['support_1']} เดินผ่านโต๊ะผมพร้อมแฟ้มเอกสารบาง ๆ แล้วทำหน้าที่คนในออฟฟิศรู้กันว่า แปลว่าอยากพูดแต่ยังไม่แน่ใจว่าควรพูดไหม",
            f"วันนั้นเริ่มธรรมดามากจนเกือบน่าขำ เครื่องพิมพ์ติดกระดาษ เสียงแอร์ดังเกินไป โต๊ะข้าง ๆ คุยเรื่องร้านข้าวเที่ยง และใน shared folder มีไฟล์ชื่อ final_v7 ที่ทุกคนรู้ว่าไม่น่าจะ final จริง {context['support_2']} เดินเข้ามาพร้อมแก้วกาแฟดำ แล้วถามว่า \"รายงานเมื่อวานอยู่ไหนนะ\" ด้วยเสียงที่ฟังเหมือนไม่มีอะไร แต่ทำให้หลังผมตรงขึ้นเอง",
            f"{context['support_1']} เป็นคนรวบรวมตัวเลขเกือบทั้งหมดเมื่อคืน เธอส่งไฟล์ตอนสามทุ่มกว่า แล้วพิมพ์ต่อท้ายว่า ถ้ามีอะไรแก้บอกได้นะคะ ประโยคสุภาพแบบนั้นในออฟฟิศบางทีมันไม่ได้แปลว่าเต็มใจเสมอไป มันแปลว่า เหนื่อยแล้วแต่ยังไม่กล้าปิดคอม",
            f"ผมจำได้ว่าตอนนั้น HR ส่งข้อความเข้ากรุ๊ปใหญ่เรื่องกิจกรรมสร้างความสัมพันธ์ในทีมพอดี ข้อความของ {context['support_3']} สุภาพมาก มี emoji ยิ้มหนึ่งตัว และบอกว่าอยากให้ทุกคนเปิดใจคุยกัน ผมอ่านแล้วเกือบหัวเราะ เพราะอีกห้านาทีต่อมา เรากำลังจะเข้าห้องประชุมที่ไม่มีใครเปิดใจจริง ๆ สักคน",
        ],
        "Act 2: The Incident": [
            f"เหตุการณ์เริ่มตอน {context['support_2']} เปิดสไลด์สรุปบนจอใหญ่ แล้วเลื่อนไปถึงหน้าที่มีกราฟยอดขายรายสัปดาห์ ผมเห็นทันทีว่าชื่อคนเตรียมข้อมูลหายไป เหลือแค่ชื่อคนพรีเซนต์กับโลโก้ทีมที่ดูสะอาดเกินจริง",
            f"เมย์นั่งอยู่ฝั่งตรงข้ามผม เธอมองจอประมาณสองวินาที แล้วก้มหน้าจดอะไรลงสมุด ทั้งที่ผมรู้ว่าเธอไม่ได้จด เธอแค่ต้องหาอะไรทำกับมือ เพื่อไม่ให้สีหน้าตัวเองตอบแทนปาก",
            f"{context['support_2']} หันมาถามห้องว่า \"อันนี้ใครเป็นคนทำ\" คำถามสั้นมาก แต่ทำให้เสียงแอร์ดังขึ้นทันทีแบบประหลาด ห้องประชุมเงียบไปประมาณสามวินาที ไม่มีใครมองใครตรง ๆ และสามวินาทีนั้นยาวกว่า deadline ทั้งสัปดาห์",
            f"ผมไม่ได้ตอบทันที เพราะคำตอบจริงมันไม่สวย เมย์ทำข้อมูล ผมช่วยเช็กสูตร พี่อีกคนแก้สไลด์ตอนดึก และคนที่กำลังถามอยู่ก็เป็นคนบอกให้ตัดชื่อออกเพราะอยากให้หน้าสรุปดู clean ขึ้น แต่ในห้องประชุม ไม่มีใครพูดคำว่า clean ด้วยความหมายเดียวกัน",
        ],
        "Act 3: The Awkward Silence": [
            f"ความเงียบหลังคำถามนั้นไม่ได้ว่างเปล่า มันมีเสียงเก้าอี้ขยับ เสียงปากกากระทบโต๊ะ และเสียง notification ที่ไม่มีใครกล้าหยิบขึ้นมาดู ผมนั่งอยู่ตรงนั้นแล้วรู้สึกเหมือนทั้งห้องกำลังรอให้ใครสักคนยอมรับบทคนผิด",
            f"{context['support_1']} เงยหน้าขึ้นนิดหนึ่งแล้วพูดว่า \"หนูทำไฟล์ตัวเลขค่ะ แต่สไลด์น่าจะมีคนช่วยปรับต่อ\" ประโยคนั้นสุภาพมาก สุภาพจนเจ็บ เพราะมันพยายามบอกความจริงโดยไม่ให้ใครเสียหน้า และในออฟฟิศ การไม่ให้ใครเสียหน้าบางทีแปลว่าเราต้องยอมเสียความรู้สึกเอง",
            f"{context['support_2']} พยักหน้าแล้วพูดว่า \"โอเค งั้นเดี๋ยวคุยกันหลังประชุม\" ไม่มีเสียงดุ ไม่มีคำแรง แต่ทุกคนในห้องรู้ทันทีว่า หลังประชุม ไม่ได้แปลว่าคุยกันเฉย ๆ มันแปลว่ามีบางคนต้องอธิบาย และบางคนจะยืนดูเหมือนไม่เกี่ยว",
            f"ผมมองไฟล์บนจออีกครั้ง เห็น cursor กระพริบอยู่ท้ายชื่อไฟล์ เหมือนมันกำลังถามแทนผมว่าเราจะปล่อยให้เรื่องนี้ผ่านไปเหมือนทุกครั้งไหม หรือวันนี้จะมีใครพูดอะไรที่ตรงกว่าคำว่า ไม่เป็นไร",
        ],
        "Act 4: The Office Politics": [
            f"การเมืองในออฟฟิศไม่จำเป็นต้องมีคนตะโกน มันอยู่ในประโยคอย่าง \"พี่ขอแก้นิดเดียวเอง\" อยู่ในชื่อที่หายไปจากสไลด์ อยู่ในคนที่ถูกขอบคุณตอนประชุมใหญ่ และคนที่ถูกเรียกไปแก้ไฟล์ตอนสามทุ่มโดยไม่มีใครจำได้ในเช้าวันถัดมา",
            f"หลังประชุม {context['support_3']} เดินผ่านหน้าห้องแล้วถามว่า \"ไม่เป็นไรใช่ไหม\" คำถามนั้นฟังดูห่วงใย แต่ก็เป็นคำถามที่ปิดทางตอบมากพอสมควร เพราะถ้าตอบว่าไม่เป็นไร ทุกอย่างก็จบ ถ้าตอบว่าเป็น ก็เหมือนเราเป็นคนทำให้บรรยากาศเสีย",
            f"ผมเห็นเมย์เก็บสมุดใส่กระเป๋าช้า ๆ เธอไม่ได้ร้องไห้ ไม่ได้ทำหน้าโกรธ แค่เงียบแบบคนที่เริ่มเข้าใจว่าบางงานไม่ได้เหนื่อยเพราะงาน แต่มันเหนื่อยเพราะต้องคอยวัดว่าความจริงพูดได้ดังแค่ไหน",
            f"{context['politics']} นี่แหละที่ทำให้เรื่องเล็กกลายเป็นเรื่องค้างในใจ ไม่ใช่เพราะกราฟ ไม่ใช่เพราะเครดิตบรรทัดเดียว แต่เพราะทุกคนเห็นเหมือนกัน แล้วพร้อมใจกันทำเหมือนไม่เห็น",
        ],
        "Act 5: The Breaking Point": [
            f"จุดที่ผมเริ่มไม่ไหวไม่ได้เกิดในห้องประชุม แต่มาเกิดตอนเที่ยงที่โต๊ะกินข้าว เมย์นั่งเขี่ยข้าวในจานแล้วพูดเบา ๆ ว่า \"หนูไม่รู้ว่าครั้งหน้าควรทำเต็มที่แค่ไหน\" ประโยคนั้นทำให้ผมวางช้อนลง",
            f"มันไม่ใช่ประโยคของคนขี้เกียจ มันเป็นประโยคของคนที่เคยตั้งใจ แล้วเริ่มกลัวว่าความตั้งใจของตัวเองจะถูกใช้จนหมดโดยไม่มีใครเห็น ผมฟังแล้วนึกถึงตัวเองหลายปีก่อน ตอนที่ยังคิดว่าถ้าเราทำดีพอ ระบบจะจำเราได้เอง",
            f"บ่ายนั้นแชตงานเด้งขึ้นมาอีกครั้ง {context['support_2']} ส่งข้อความว่า \"แก้ชื่อไฟล์ให้ตรง version ล่าสุดด้วยนะ\" ไม่มีคำขอโทษ ไม่มีการพูดถึงชื่อที่หายไป ไม่มีใครพูดถึงสามวินาทีในห้องประชุม เหมือนทุกอย่างถูกพับเก็บไว้ใน folder เดิม",
            f"ผมพิมพ์คำว่า รับทราบ ค้างไว้เกือบนาที แล้วลบออก ผมไม่ได้อยากมีเรื่อง แต่วันนั้นผมก็ไม่อยากเป็นคนที่ช่วยทำให้ทุกอย่างดูปกติอีก ผมเลยพิมพ์กลับไปว่า \"ขอใส่ชื่อคนเตรียมข้อมูลไว้ใน note ของสไลด์ด้วยนะครับ จะได้ตามงานถูก\" แค่นั้นเอง แค่นั้นจริง ๆ แต่สำหรับวันนั้น มันเหมือนยกโต๊ะทั้งตัวออกจากอก",
        ],
        "Act 6: After Work Reflection": [
            f"หลังเลิกงาน ผมเดินไปที่ {context['after_work_place']} ฝนเพิ่งหยุดตก พื้นยังสะท้อนแสงไฟจากตึก และมือถือผมยังมีข้อความที่ยังไม่ได้อ่านอีกหลายอัน ผมไม่ได้เปิดดูทันที เพราะบางครั้งเราต้องให้ตัวเองได้ยืนเฉย ๆ ก่อนจะกลับไปเป็นคนตอบไว",
            f"ผมคิดถึงเมย์ คิดถึงสีหน้าของเธอที่ไม่ได้แตกสลาย แต่มันแบนลง เหมือนความรู้สึกถูกลด resolution เพื่อให้ส่งต่อในที่ทำงานได้ง่ายขึ้น ผมคิดถึงพี่นนท์ด้วย ไม่ใช่ในฐานะตัวร้าย แต่ในฐานะคนที่อยู่ในระบบมานานจนบางทีแยกไม่ออกแล้วว่าอะไรคือความสะดวก และอะไรคือการลบคนอื่นออกจากเรื่อง",
            f"เรื่องแบบนี้มันเหนื่อยเพราะไม่มีฉากใหญ่ให้ชี้ ไม่มีประโยคหยาบให้แคป ไม่มีหลักฐานที่ดูดราม่าพอ มันมีแค่บรรยากาศในห้องประชุม ความเงียบหลังจากนั้น และคำถามที่กลับมาหาเราตอนขับรถว่า วันนี้เราปล่อยอะไรผ่านไปอีกแล้วหรือเปล่า",
            f"ผมไม่ได้กลับบ้านพร้อมคำตอบเท่มากมาย ผมแค่กลับบ้านพร้อมความรู้สึกว่า ครั้งหน้าถ้ามีชื่อใครหายไปจากงานที่เขาทำ ผมอาจต้องพูดให้เร็วขึ้นนิดหนึ่ง ไม่ใช่เพื่อเป็นคนกล้า แต่เพื่อไม่ให้ความเงียบกลายเป็นระบบอีกชั้นหนึ่ง",
        ],
        "Ending": [
            f"ตอนนี้ถ้าคุณกำลังฟังอยู่หลังเลิกงาน บางทีคุณอาจไม่ได้มีเรื่องเดียวกับผม แต่คุณอาจรู้จักบรรยากาศแบบเดียวกัน บรรยากาศที่ไม่มีใครทำร้ายเราตรง ๆ แต่เรากลับเหนื่อยเหมือนโดนอะไรบางอย่างขูดอยู่ทั้งวัน",
            f"ผมไม่อยากจบตอนนี้ด้วยคำแนะนำสวย ๆ เพราะเรื่องในออฟฟิศบางเรื่องไม่ได้ต้องการคำคม มันต้องการคนจำรายละเอียดให้ได้ จำว่าใครทำงาน จำว่าใครเงียบ จำว่าใครถูกตัดออกจากเครดิต และจำว่าเราเองเคยรู้สึกอย่างไรตอนนั่งอยู่ในห้องนั้น",
            f"พรุ่งนี้อาจมีประชุมอีก ไฟ Excel อาจยังเปิดค้าง และกรุ๊ปงานอาจเด้งตั้งแต่เช้าเหมือนเดิม แต่คืนนี้อย่างน้อยเราพูดเรื่องนี้ออกมาแล้ว แบบคนทำงานคนหนึ่งเล่าให้เพื่อนร่วมงานอีกคนฟังหลังปิดคอม",
            "แล้วเจอกันหลังเลิกงานครั้งหน้า กับเรื่องที่อาจไม่ได้อยู่ในรายงาน แต่ค้างอยู่ในใจคนทำงานหลายคน",
        ],
    }[section]


def _paragraph_bank(topic: str, tone: str) -> dict[str, list[str]]:
    profile = _tone_profile(tone)
    return {
        "Act 1: Setup": [
            f"เรื่องมันเริ่มธรรมดามาก เหมือนวันทำงานทั่วไปที่เราบอกตัวเองว่าเดี๋ยวก็ผ่านไป เราเปิดคอม ตอบข้อความ ดูปฏิทิน แล้วพยายามทำหน้าเหมือนทุกอย่างอยู่ในการควบคุม ทั้งที่ลึก ๆ มีบางอย่างเกี่ยวกับ {topic} ค้างอยู่ตรงอกตั้งแต่ยังไม่เที่ยง",
            "สิ่งที่น่าสนใจคือคนทำงานส่วนใหญ่ไม่ได้พังทันที เราพังแบบค่อย ๆ สุภาพขึ้น ค่อย ๆ เงียบขึ้น ค่อย ๆ ตอบสั้นลง แล้วก็ยังส่งงานตรงเวลาเหมือนเดิม จนไม่มีใครรู้ว่าข้างในเริ่มไม่มีพื้นที่ให้วางความรู้สึกแล้ว",
            "ในออฟฟิศ ทุกคนมีบทบาทของตัวเอง คนหนึ่งต้องเป็นคนใจเย็น คนหนึ่งต้องเป็นคนรับผิดชอบ คนหนึ่งต้องเป็นคนไม่เรื่องมาก และบางครั้งเราก็เล่นบทนั้นนานเกินไป จนลืมว่าตัวจริงของเราเหนื่อยเป็นเหมือนกัน",
            f"โทนของตอนนี้คือ {profile['voice']} ไม่ใช่เพื่อบ่นให้โลกดูแย่ลง แต่เพื่อยอมรับว่าหลายเรื่องในที่ทำงานมันหนัก เพราะเราไม่ค่อยได้รับอนุญาตให้พูดว่ามันหนัก",
        ],
        "Act 2: Conflict": [
            "ความขัดแย้งจริง ๆ ไม่ได้อยู่แค่ในห้องประชุม แต่อยู่ในใจตอนที่เราต้องเลือกระหว่างพูดความจริงกับรักษาบรรยากาศ เลือกระหว่างปกป้องตัวเองกับไม่ทำให้ใครลำบากใจ และสุดท้ายเรามักเลือกเงียบ เพราะความเงียบดูเป็นมืออาชีพกว่า",
            "ปัญหาคือความเงียบไม่ได้หายไป มันย้ายที่อยู่ จากปากมาอยู่ในไหล่ ในคอ ในการนอนที่ไม่สนิท และในความรู้สึกแปลก ๆ ตอนเห็น notification จากที่ทำงานเด้งขึ้นมาในวันหยุด",
            f"พอเรื่อง {topic} เกิดซ้ำ เราเริ่มสงสัยว่าหรือเราคิดมากไปเอง แต่คำถามนี้แหละที่ทำให้คนจำนวนมากเจ็บกว่าเดิม เพราะแทนที่จะได้พักจากเหตุการณ์ เรายังต้องสอบสวนความรู้สึกตัวเองอีกชั้นหนึ่ง",
            "บางคนในออฟฟิศไม่จำเป็นต้องเสียงดังเพื่อทำให้เรารู้สึกเล็กลง แค่ทำเหมือนสิ่งที่เราพูดไม่มีน้ำหนักพอ แค่ข้ามชื่อเราในเครดิตงาน แค่ชมคนอื่นในสิ่งที่เราทำ แล้วปล่อยให้เรายิ้มรับอย่างสุภาพ",
        ],
        "Act 3: Emotional Breakdown": [
            "จุดที่แตกจริง ๆ มักไม่ดราม่าเท่าในหนัง มันอาจเกิดตอนนั่งในรถ ตอนล้างแก้วกาแฟ หรือตอนปิดไฟห้องแล้วอยู่ ๆ น้ำตาก็มาแบบไม่มีพิธีการ เหมือนร่างกายพูดแทนใจว่า พอได้แล้ว",
            "เราไม่ได้ร้องไห้เพราะอ่อนแอ เราร้องไห้เพราะทั้งวันเราแข็งแรงเกินไป แข็งแรงตอนตอบว่าไม่เป็นไร แข็งแรงตอนยิ้ม แข็งแรงตอนรับงานเพิ่ม และแข็งแรงตอนเดินผ่านคนที่ทำให้เราเจ็บโดยไม่ให้สีหน้าหลุด",
            "ความตลกร้ายคือพรุ่งนี้เราก็อาจกลับไปทำเหมือนเดิมอีก เปิดคอมเหมือนเดิม ทักทายเหมือนเดิม ประชุมเหมือนเดิม แต่หลังจากคืนหนึ่งที่เราพังเงียบ ๆ เราจะรู้ว่าบางอย่างในใจไม่เหมือนเดิมแล้ว",
            "และบางที breakdown ไม่ได้แปลว่าทุกอย่างจบ มันอาจแปลว่าระบบข้างในกำลังปิดตัวเพื่อป้องกันไม่ให้เราเสียตัวเองไปมากกว่านี้",
        ],
        "Act 4: Reflection": [
            "พอมองย้อนกลับไป เราอาจพบว่าเราไม่ได้ต้องการให้ทุกคนเข้าใจทั้งหมด เราแค่อยากให้มีใครสักคนไม่รีบลดทอนความรู้สึกของเราให้เป็นคำว่า เรื่องเล็ก",
            "เรื่องเล็กสำหรับคนหนึ่ง อาจเป็นเรื่องที่สะสมมาหลายเดือนสำหรับอีกคน และในชีวิตการทำงาน สิ่งที่ทำร้ายเรามากที่สุดมักมาในรูปแบบที่ดูสุภาพพอจะไม่มีใครรับผิดชอบ",
            "นี่อาจเป็นเหตุผลที่ Vela After Work ต้องมีพื้นที่แบบนี้ พื้นที่ที่เราไม่ต้องเก่ง ไม่ต้องมีคำตอบครบ ไม่ต้องเปลี่ยนความเหนื่อยให้เป็นแรงบันดาลใจทันที แค่เล่ามันอย่างซื่อสัตย์ก่อน",
            "บางครั้งการเยียวยาไม่ได้เริ่มจากคำแนะนำ แต่มันเริ่มจากประโยคง่าย ๆ ว่า ใช่ มันหนักจริง และคุณไม่ได้คิดมากไปเอง",
        ],
        "Act 5: Takeaway": [
            "สิ่งที่อยากฝากไว้คือ อย่ารอให้ตัวเองพังก่อนถึงจะเชื่อว่าความเหนื่อยของคุณจริง ถ้าวันนี้อะไรบางอย่างหนักเกินไป คุณมีสิทธิ์ยอมรับมัน โดยไม่ต้องหาเหตุผลให้ใครอนุมัติ",
            "ลองเริ่มจากขอบเขตเล็ก ๆ สักอย่าง ตอบช้าลงเมื่อถึงเวลาพัก ปิด notification บางช่วง หรือพูดประโยคจริง ๆ กับตัวเองว่า วันนี้ฉันไม่ไหว และนั่นไม่ได้ทำให้ฉันแย่ลง",
            "เราอาจเปลี่ยนออฟฟิศทั้งระบบไม่ได้ในคืนเดียว แต่เราเริ่มไม่ทิ้งตัวเองไว้กลางระบบนั้นได้ และบางครั้ง แค่นั้นก็เป็นการกลับมายืนข้างตัวเองที่สำคัญมาก",
            "ถ้าคุณฟังถึงตรงนี้ ขอให้คืนนี้คุณใจดีกับตัวเองนิดหนึ่ง เพราะโลกการทำงานมีคนคอยวัดผลเรามากพอแล้ว อย่าให้ใจของเราเป็นอีกที่ที่เอาแต่ตำหนิตัวเอง",
        ],
        "Ending": [
            "นี่คือ Vela After Work เรื่องที่เราอาจคิดเหมือนกันหลังเลิกงาน แต่ไม่ค่อยพูดออกมา",
            "ถ้าตอนนี้คุณยังนั่งอยู่กับความเหนื่อยของตัวเอง ขอให้รู้ว่ามันไม่ใช่เรื่องน่าอาย และคุณไม่จำเป็นต้องรีบแปลงมันเป็นพลังบวกภายในคืนนี้",
            "บางคืน แค่ยอมรับว่าเหนื่อย แล้วพาตัวเองไปอาบน้ำ กินอะไรอุ่น ๆ และนอนให้ได้ ก็ถือว่าเราดูแลชีวิตได้ดีมากแล้ว",
            "เจอกันหลังเลิกงานครั้งหน้า กับเรื่องที่อาจไม่ได้อยู่ในรายงาน แต่ค้างอยู่ในใจคนทำงานหลายคน",
        ],
    }


def _expand_section(section: str, topic: str, tone: str, paragraphs_needed: int, narrator: str = "Male", start_index: int = 0, context: dict[str, str] | None = None) -> str:
    section_key = _section_bank_key(section)
    if context and section_key in {
        "Act 1: The Ordinary Office Day",
        "Act 2: The Incident",
        "Act 3: The Awkward Silence",
        "Act 4: The Office Politics",
        "Act 5: The Breaking Point",
        "Act 6: After Work Reflection",
        "Ending",
    }:
        bank = _story_act_bank(section_key, context)
    else:
        bank = _paragraph_bank(topic, tone)[section_key]
    rows = []
    for index in range(paragraphs_needed):
        effective_index = start_index + index
        base = bank[effective_index % len(bank)]
        if effective_index >= len(bank):
            base += " " + [
                "พอพูดออกมาแบบนี้ มันไม่ได้ทำให้เรื่องเบาลงทันที แต่มันทำให้เราไม่ต้องแบกมันแบบไม่มีชื่ออีกต่อไป",
                "และนั่นอาจเป็นจุดเริ่มต้นเล็ก ๆ ของการกลับมาฟังตัวเอง หลังจากฟังเสียงคนอื่นมาทั้งวัน",
                "บางทีคำตอบไม่ได้อยู่ที่การหนีไปไหน แต่อยู่ที่การเห็นให้ชัดว่าอะไรที่เราไม่ควรปล่อยให้กลายเป็นเรื่องปกติอีกแล้ว",
            ][effective_index % 3]
        rows.append(_humanize_paragraph(base, section_key, topic, tone, narrator, start_index + index))
    return "\n\n".join(rows)


def _full_script(topic: str, tone: str, narrator: str, length: str, context: dict[str, str] | None = None) -> str:
    context = context or _story_context(topic, tone)
    target = WORD_TARGETS.get(length, WORD_TARGETS["10 min"])["target"]
    sections = [
        "Cold Open",
        "Act 1: The Ordinary Office Day",
        "Act 2: The Incident",
        "Act 3: The Awkward Silence",
        "Act 4: The Office Politics",
        "Act 5: The Breaking Point",
        "Act 6: After Work Reflection",
        "Ending",
    ]
    paragraphs_by_section = max(3, target // 440)
    blocks = [f"[Cold Open]\n{_cold_open(topic, tone, context)}"]
    section_offset = 0
    for section in sections[1:]:
        extra = 1 if section in {"Act 3: The Awkward Silence", "Act 4: The Office Politics", "Act 5: The Breaking Point"} else 0
        count = paragraphs_by_section + extra
        blocks.append(f"[{section}]\n{_expand_section(section, topic, tone, count, narrator=narrator, start_index=section_offset, context=context)}")
        section_offset += count
    voice_note = f"\n\n[Narrator Direction]\n{_narrator_voice(narrator)}"
    script = _avoid_topic_repeat("\n\n".join(blocks) + voice_note, topic)
    extension_sections = ["Act 2: The Incident", "Act 3: The Awkward Silence", "Act 4: The Office Politics", "Act 5: The Breaking Point", "Act 6: After Work Reflection", "Ending"]
    extension_index = 0
    while _word_count(script) < target:
        section = extension_sections[extension_index % len(extension_sections)]
        script += "\n\n" + _expand_section(section, topic, tone, 1, narrator=narrator, start_index=section_offset + extension_index, context=context)
        script = _avoid_topic_repeat(script, topic)
        extension_index += 1
    script = _dedupe_exact_paragraphs(script)
    refill_count = 0
    while _word_count(script) < target and refill_count < 220:
        section = extension_sections[extension_index % len(extension_sections)]
        script += "\n\n" + _long_form_detail_paragraph(section, extension_index, context)
        script = _avoid_topic_repeat(_dedupe_exact_paragraphs(script), topic)
        extension_index += 1
        refill_count += 1
    return script


def _ai_voice_version(script: str) -> str:
    lines = []
    for raw in script.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        if line.lower().startswith("narrator direction"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()


def _rant_versions(topic: str) -> dict[str, str]:
    return {
        "emotional rant version": (
            "บางทีเราไม่ได้ต้องการให้ใครแก้ปัญหาให้เลย เราแค่อยากให้ใครสักคนยอมรับว่าเรื่องนี้มันหนักจริง "
            "เพราะการต้องทำตัวปกติทุกวัน ทั้งที่ข้างในไม่ปกติ มันเหนื่อยกว่าที่คนอื่นเห็นมาก"
        ),
        "angry rant version": (
            "ขอพูดตรง ๆ นะ สิ่งที่ทำให้คนทำงานพังไม่ใช่แค่งานเยอะ แต่มันคือการถูกคาดหวังให้รับทุกอย่างด้วยรอยยิ้ม "
            "แล้วพอเราเริ่มไม่ไหว กลับถูกถามว่าทำไมไม่จัดการอารมณ์ตัวเองให้ดีกว่านี้"
        ),
        "sarcastic office rant version": (
            "ใช่ครับ ทุกอย่างเร่งด่วนหมด ยกเว้นเงินเดือนกับความเข้าใจของคนบางคนที่ดูเหมือนจะเดินทางมาช้ากว่าอีเมลประมาณสามปี "
            "แต่ไม่เป็นไร เดี๋ยวเราก็กดรับทราบ แล้วไปนั่งหมดไฟต่อแบบมืออาชีพ"
        ),
    }


def _shorts(topic: str, count: int, context: dict[str, str] | None = None) -> list[dict[str, str]]:
    context = context or _story_context(topic, "Vela After Work")
    hooks = [
        "ห้องประชุมเงียบไปสามวินาที แล้วทุกคนรู้ว่าเรื่องไม่จบ",
        "ประโยคว่า อันนี้ใครเป็นคนทำ ทำให้ทั้งห้องไม่กล้ามองหน้ากัน",
        "ชื่อคนทำงานหายไปจากสไลด์ แต่ความเหนื่อยไม่ได้หายไปด้วย",
        "เมย์พูดว่า หนูไม่รู้ว่าครั้งหน้าควรทำเต็มที่แค่ไหน แล้วโต๊ะกินข้าวก็เงียบ",
        "คำว่า เดี๋ยวคุยกันหลังประชุม บางทีน่ากลัวกว่าการถูกดุ",
        "พี่ขอแก้นิดเดียวเอง คือประโยคที่ทำให้คนทำงานนอนดึกได้ทั้งคืน",
        "HR ถามว่า ไม่เป็นไรใช่ไหม และทุกคนรู้ว่าคำตอบที่ปลอดภัยคืออะไร",
        "ผมพิมพ์ รับทราบ ค้างไว้ แล้วลบออกเป็นครั้งแรก",
        "เรื่องนี้ไม่ได้ดัง แต่มันทำให้คนหนึ่งหมดแรงจะตั้งใจ",
        "หลังเลิกงานที่ลานจอดรถ ผมเพิ่งรู้ว่าเรื่องในห้องประชุมยังเดินตามมา",
    ]
    scripts = [
        f"ผมจำได้ว่าตอน {context['support_2']} ถามว่า \"อันนี้ใครเป็นคนทำ\" ห้องประชุมเงียบไปประมาณสามวินาที ไม่มีใครขยับเมาส์ ไม่มีใครจิบน้ำ และสามวินาทีนั้นทำให้เห็นชัดว่าในออฟฟิศ บางครั้งทุกคนรู้ความจริงพร้อมกัน แต่ไม่มีใครอยากเป็นคนแรกที่พูด",
        f"เมย์ไม่ได้โวยวาย เธอแค่พูดว่า \"หนูทำไฟล์ตัวเลขค่ะ แต่สไลด์น่าจะมีคนช่วยปรับต่อ\" ประโยคนี้สุภาพมาก สุภาพจนเจ็บ เพราะมันพยายามรักษาหน้าทุกคน ยกเว้นความรู้สึกของคนพูดเอง",
        f"เรื่องมันเริ่มจาก {context['incident']} ถ้ามองผ่าน ๆ อาจเป็นแค่สไลด์หนึ่งหน้า แต่สำหรับคนที่นั่งแก้สูตรจนสามทุ่ม มันคือชื่อของตัวเองที่ถูกลบออกจากเรื่อง",
        "ตอนเที่ยง เมย์เขี่ยข้าวในจานแล้วพูดว่า \"หนูไม่รู้ว่าครั้งหน้าควรทำเต็มที่แค่ไหน\" ผมวางช้อนลงเลย เพราะนั่นไม่ใช่เสียงของคนขี้เกียจ มันคือเสียงของคนที่เคยตั้งใจแล้วเริ่มไม่แน่ใจว่าความตั้งใจมีที่อยู่ไหม",
        "\"เดี๋ยวคุยกันหลังประชุม\" เป็นประโยคที่ฟังสุภาพ แต่คนทำงานรู้ดีว่ามันไม่ได้แปลว่าคุยเฉย ๆ มันแปลว่าจะมีใครบางคนต้องอธิบาย ในขณะที่อีกหลายคนทำเหมือนไม่เกี่ยว",
        "ในออฟฟิศ ประโยคว่า \"พี่ขอแก้นิดเดียวเอง\" บางทีไม่ได้เล็กตามคำพูด เพราะมันอาจหมายถึงแก้ไฟล์ตอนสามทุ่ม แก้ชื่อคนทำงานออก และแก้ความรู้สึกของคนหนึ่งให้เงียบลง",
        f"{context['support_3']} ถามว่า \"ไม่เป็นไรใช่ไหม\" คำถามนี้ดูห่วงใย แต่ก็ปิดทางตอบมากพอสมควร เพราะถ้าตอบว่าไม่เป็นไร ทุกอย่างก็จบ ถ้าตอบว่าเป็น เราอาจกลายเป็นคนทำให้บรรยากาศเสีย",
        "ผมพิมพ์คำว่า รับทราบ ค้างไว้เกือบนาที แล้วลบออก วันนั้นผมไม่ได้อยากเป็นฮีโร่ แค่ไม่อยากช่วยทำให้ความเงียบกลายเป็นระบบอีกชั้นหนึ่ง",
        "เรื่องแบบนี้ไม่ค่อยมีหลักฐานที่ดูดราม่า มันมีแค่บรรยากาศในห้องประชุม สีหน้าของคนที่ถูกตัดเครดิต และความรู้สึกว่าถ้าพูดตรง ๆ เราจะกลายเป็นคนเรื่องมากไหม",
        f"หลังเลิกงาน ผมยืนอยู่ที่ {context['after_work_place']} ฝนเพิ่งหยุดตก มือถือยังมี unread messages แต่ผมยังไม่เปิดดู เพราะบางครั้งเราต้องยืนเฉย ๆ ก่อนกลับไปเป็นคนตอบไวอีกครั้ง",
    ]
    items = []
    for index, hook in enumerate(hooks[:count], start=1):
        start = f"00:{(index - 1) * 35:02d}"
        end = f"00:{(index - 1) * 35 + 30:02d}"
        items.append(
            {
                "timestamp": f"{start}-{end}",
                "hook": hook,
                "caption": f"เรื่องนี้คนทำงานน่าจะเข้าใจ #{index} #VelaAfterWork",
                "script": f"{hook}\n\n{scripts[(index - 1) % len(scripts)]}",
            }
        )
    return items


def _youtube_package(title: str, topic: str, tone: str, context: dict[str, str] | None = None) -> dict[str, str]:
    context = context or _story_context(topic, tone)
    return {
        "YouTube Title": title,
        "YouTube Description": (
            f"Vela After Work ตอนนี้เป็นเรื่องเล่าในออฟฟิศโทน {tone} เกี่ยวกับรายงาน Excel หนึ่งไฟล์ ชื่อคนทำงานที่หายไปจากสไลด์ "
            f"และความเงียบใน {context['location']} ที่ทำให้ทุกคนรู้ว่าเรื่องเล็กไม่ได้เล็กเสมอไป\n\n"
            "ฟังเหมือนเพื่อนร่วมงานคนหนึ่งเล่าเรื่องหลังปิดคอม มีทั้งความเหนื่อย ความตลกร้าย การเมืองในทีม และประโยคที่ไม่มีใครกล้าพูดดัง ๆ"
        ),
        "Hashtags": "#VelaAfterWork #Podcastไทย #ชีวิตวัยทำงาน #OfficeStory #Burnout #เล่าเรื่อง",
        "Pinned Comment": "คุณเคยมีเรื่องที่ไม่กล้าพูดในออฟฟิศ แต่คิดถึงหลังเลิกงานไหม เล่าแบบไม่ต้องบอกชื่อใครก็ได้",
    }


def _spotify_package(topic: str, tone: str, length: str, context: dict[str, str] | None = None) -> dict[str, str]:
    context = context or _story_context(topic, tone)
    return {
        "Spotify title": "Vela After Work: ห้องประชุมเงียบไปสามวินาที",
        "Spotify description": (
            f"ตอนความยาวประมาณ {length} ในโทน {tone} เล่าเหตุการณ์ใน {context['location']} "
            "เมื่อรายงานหนึ่งไฟล์ทำให้เห็นทั้งเครดิตที่หายไป ความเงียบในทีม และการเมืองเล็ก ๆ ที่คนทำงานหลายคนรู้จักดี"
        ),
    }


def _thumbnail_prompt(topic: str, tone: str, context: dict[str, str] | None = None) -> str:
    context = context or _story_context(topic, tone)
    return (
        f"cinematic podcast cover for Vela After Work, Thai office worker after hours, tired but thoughtful expression, "
        f"dark warm office lighting, desk lamp, city window at night, emotional workplace story in {context['location']}, tone {tone}, "
        "premium podcast artwork, no random text, no watermark"
    )


def _ai_video_prompt(topic: str, tone: str, context: dict[str, str] | None = None) -> str:
    context = context or _story_context(topic, tone)
    return (
        f"vertical 9:16 cinematic b-roll prompt for a Vela After Work office story, {context['location']}, Excel report on projector, unread work chat, "
        f"workplace politics and burnout atmosphere, {tone} emotional storytelling, slow shots of empty desk, elevator, rainy window, "
        "coffee cup, phone notification, realistic Thai office, no subtitles, no logo, no watermark"
    )


def _is_bullet_heavy(text: str) -> bool:
    rows = [row.strip() for row in str(text or "").splitlines() if row.strip()]
    if len(rows) < 10:
        return False
    bullet_rows = [row for row in rows if row.startswith(("-", "*", "•")) or re.match(r"^\d+[\.)]\s", row)]
    return len(bullet_rows) / max(1, len(rows)) > 0.45


def _repeated_line_count(text: str) -> int:
    seen: set[str] = set()
    repeated = 0
    for raw in str(text or "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip().lower()
        if not line or line.startswith("["):
            continue
        if line in seen:
            repeated += 1
        seen.add(line)
    return repeated


def _nonempty_script_line_count(text: str) -> int:
    return len([line for line in str(text or "").splitlines() if line.strip() and not line.strip().startswith("[")])


def _polish_podcast_script(script: str) -> str:
    replacements = {
        "Hello everyone": "",
        "Today we will talk about": "",
        "In this episode, we will discuss": "",
    }
    polished = str(script or "")
    for bad, good in replacements.items():
        polished = polished.replace(bad, good)
    while "\n\n\n" in polished:
        polished = polished.replace("\n\n\n", "\n\n")
    return polished.strip()


def _podcast_quality_report(package: dict[str, Any], episode_length: str) -> dict[str, Any]:
    full_script = str(package.get("Full Podcast Script") or "")
    ai_voice = str(package.get("AI Voice Version") or "")
    text_export = podcast_script_package_to_text(package) if package else ""
    target = WORD_TARGETS.get(episode_length, WORD_TARGETS["10 min"])["min"]
    forbidden = [
        "Hello everyone",
        "Today we will talk about",
        "placeholder",
        "lorem ipsum",
        "จุดเปลี่ยนคือ",
        "บทเรียนคือ",
    ]
    return {
        "long_form_ready": _word_count(ai_voice) >= target,
        "not_bullet_outline": not _is_bullet_heavy(full_script),
        "required_sections": all(section in full_script for section in ["[Cold Open]", "[Act 1: The Ordinary Office Day]", "[Act 5: The Breaking Point]", "[Ending]"]),
        "voice_copy_ready": "[Cold Open]" not in ai_voice and "[Narrator Direction]" not in ai_voice and _word_count(ai_voice) >= target,
        "shorts_ready": len(package.get("Shorts Extraction", []) or []) >= 10,
        "no_placeholder_language": not any(token.lower() in text_export.lower() for token in forbidden),
        "low_repetition": _repeated_line_count(full_script) <= max(8, int(_nonempty_script_line_count(full_script) * 0.08)),
    }


def generate_podcast_script_package(
    topic: str,
    podcast_tone: str,
    narrator: str,
    episode_length: str,
    gemini_api_key: str | None = None,
    require_gemini_success: bool = False,
) -> dict[str, Any]:
    topic = _clean(topic, "เรื่องที่คนทำงานคิดถึงหลังเลิกงาน")
    podcast_tone = podcast_tone if podcast_tone in PODCAST_SCRIPT_TONES else "Vela After Work"
    narrator = narrator if narrator in PODCAST_NARRATORS else "Male"
    episode_length = episode_length if episode_length in PODCAST_EPISODE_LENGTHS else "10 min"
    story_blueprint, provider_diagnostics = _generate_story_blueprint(topic, podcast_tone, episode_length, gemini_api_key=gemini_api_key)
    if require_gemini_success and provider_diagnostics.get("used") != "true":
        error = provider_diagnostics.get("fallback_reason") or "Gemini Story Writer failed"
        return {"ok": False, "data": {}, "error": error}
    context = story_blueprint["context"]
    title = _best_title(topic, podcast_tone)
    full_script = _polish_podcast_script(_full_script(topic, podcast_tone, narrator, episode_length, context=context))
    word_count = _word_count(_ai_voice_version(full_script))
    package = {
        "Episode Title": title,
        "Cold Open": _cold_open(topic, podcast_tone, context),
        "Full Podcast Script": full_script,
        "AI Voice Version": _ai_voice_version(full_script),
        "Viral Rant Engine": _rant_versions(topic),
        "Shorts Extraction": _shorts(topic, WORD_TARGETS[episode_length]["shorts"], context),
        "YouTube Package": _youtube_package(title, topic, podcast_tone, context),
        "Spotify Package": _spotify_package(topic, podcast_tone, episode_length, context),
        "Thumbnail Prompt": _thumbnail_prompt(topic, podcast_tone, context),
        "AI Video Prompt": _ai_video_prompt(topic, podcast_tone, context),
        "metadata": {
            "topic": topic,
            "podcast_tone": podcast_tone,
            "narrator": narrator,
            "episode_length": episode_length,
            "word_count": word_count,
            "target_word_count_min": WORD_TARGETS[episode_length]["min"],
            "target_word_count_max": WORD_TARGETS[episode_length]["max"],
            "style": "Vela After Work",
            "story_engine": "Vela After Work AI Story Writer",
            "story_blueprint_source": story_blueprint.get("source", "local_fallback"),
            "story_provider": provider_diagnostics,
            "story_arc": story_blueprint.get("story_arc", []),
            "scene_breakdown": story_blueprint.get("scene_breakdown", []),
            "resolution": story_blueprint.get("resolution", ""),
            "takeaway": story_blueprint.get("takeaway", ""),
            "main_narrator": context["main_narrator"],
            "supporting_characters": [context["support_1"], context["support_2"], context["support_3"]],
            "office_location": context["location"],
            "specific_incident": context["incident"],
            "offline_safe": True,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
    }
    package["metadata"]["quality_report"] = _podcast_quality_report(package, episode_length)
    return {"ok": True, "data": package, "error": ""}


def podcast_script_package_to_text(package: dict[str, Any]) -> str:
    def block(title: str, body: Any) -> str:
        if isinstance(body, list):
            if body and isinstance(body[0], dict):
                rows = []
                for index, item in enumerate(body, start=1):
                    rows.append(
                        f"{index}. Timestamp: {item.get('timestamp', '')}\n"
                        f"Hook: {item.get('hook', item.get('Hook', ''))}\n"
                        f"Script: {item.get('script', item.get('Script', ''))}\n"
                        f"Caption: {item.get('caption', item.get('Suggested caption', ''))}"
                    )
                content = "\n\n".join(rows)
            else:
                content = "\n".join(f"- {item}" for item in body)
        elif isinstance(body, dict):
            content = "\n".join(f"{key}: {value}" for key, value in body.items())
        else:
            content = str(body or "")
        return f"====================\n{title}\n====================\n{content.strip()}\n"

    lines = ["VELAFLOW PODCAST SCRIPT STUDIO V4", "Vela After Work: Stories people think about after work but rarely say out loud.", ""]
    metadata = package.get("metadata") or {}
    lines.append(block("EPISODE METADATA", metadata))
    for section in REQUIRED_PODCAST_SCRIPT_SECTIONS:
        lines.append(block(section.upper(), package.get(section, "")))
    return "\n".join(lines).strip() + "\n"
