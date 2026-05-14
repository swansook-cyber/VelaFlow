from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name
from core.paths import resolve_project_folder
from core.visual_engine import apply_visual_engine_to_package


STORY_TONES = [
    "Emotional",
    "Dark Office",
    "Funny",
    "Motivational",
    "Reflective",
    "Viral Rant",
]

NARRATION_STYLES = [
    "Calm Storytelling",
    "Deep Emotional",
    "Energetic Podcast",
    "Soft Spoken",
    "Documentary Style",
]

EPISODE_LENGTHS = ["3 min", "5 min", "10 min", "20 min"]

TONE_GUIDES = {
    "Emotional": "เล่าแบบจริงใจ มีจังหวะพัก และค่อย ๆ พาคนฟังเข้าใจความรู้สึก",
    "Dark Office": "โทนออฟฟิศหม่น ๆ เหนื่อยกับคนและระบบ แต่ยังฟังง่าย",
    "Funny": "เล่าแบบขำปนจริง เหมือนคุยกับเพื่อนสนิท",
    "Motivational": "ให้กำลังใจแบบไม่ขายฝัน มีประโยคจำง่าย",
    "Reflective": "ชวนคิด ทบทวนชีวิต และปิดด้วยความเข้าใจ",
    "Viral Rant": "เปิดแรง ตรงประเด็น เหมาะตัดเป็นคลิปสั้น",
}

STYLE_GUIDES = {
    "Calm Storytelling": "เสียงเล่าใจเย็น จังหวะนุ่ม ฟังต่อเนื่องสบาย",
    "Deep Emotional": "เสียงลึก อารมณ์หนักแน่น คุมความเศร้าแบบมีชั้นเชิง",
    "Energetic Podcast": "จังหวะกระชับ เปิดประเด็นไว เหมาะคลิปไวรัล",
    "Soft Spoken": "เสียงเบา ใกล้ไมค์ เหมาะเรื่องส่วนตัวและปลอบใจ",
    "Documentary Style": "เล่าเป็นลำดับ มีภาพในหัว และสรุปชัด",
}


def _split_keywords(text: str | List[str]) -> List[str]:
    if isinstance(text, list):
        raw = text
    else:
        raw = str(text or "").replace(",", "\n").replace(";", "\n").splitlines()
    items = [item.strip(" -•\t") for item in raw if str(item).strip(" -•\t")]
    return items[:8] or ["เรื่องที่หลายคนกำลังเจอ", "ความรู้สึกที่พูดออกมายาก", "บทเรียนที่อยากเล่า"]


def _length_detail(length: str) -> Dict[str, Any]:
    return {
        "3 min": {"beats": 4, "words": "สั้น กระชับ เน้น hook และ punchline"},
        "5 min": {"beats": 5, "words": "เล่าครบ มีจังหวะ build และสรุป"},
        "10 min": {"beats": 7, "words": "ลงรายละเอียดมากขึ้น มีตัวอย่างและ reflection"},
        "20 min": {"beats": 9, "words": "แบ่งเป็นหลายช่วง เหมือน episode เต็ม"},
    }.get(length, {"beats": 5, "words": "เล่าครบ มีจังหวะ build และสรุป"})


def _episode_title(topic: str, theme: str, tone: str) -> str:
    topic = topic.strip() or "เรื่องที่อยากเล่า"
    if tone == "Viral Rant":
        return f"พอกันทีกับ{topic}"
    if tone == "Dark Office":
        return f"ทำไม{topic}ถึงเหนื่อยกว่าที่คิด"
    if tone == "Motivational":
        return f"วันที่{topic}สอนให้เราโตขึ้น"
    if theme:
        return f"{topic}: {theme}"
    return topic


def generate_podcast_content(
    topic: str,
    episode_theme: str,
    story_tone: str,
    target_audience: str,
    episode_length: str,
    narration_style: str,
    visual_settings: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    try:
        topic = (topic or "เรื่องที่อยากเล่า").strip()
        episode_theme = (episode_theme or "เล่าเรื่องจริงให้คนฟังรู้สึกว่าไม่ได้อยู่คนเดียว").strip()
        story_tone = story_tone if story_tone in STORY_TONES else STORY_TONES[0]
        narration_style = narration_style if narration_style in NARRATION_STYLES else NARRATION_STYLES[0]
        episode_length = episode_length if episode_length in EPISODE_LENGTHS else "5 min"
        target_audience = (target_audience or "คนที่กำลังผ่านเรื่องคล้ายกัน").strip()
        keywords = _split_keywords(episode_theme)
        length_detail = _length_detail(episode_length)
        title = _episode_title(topic, episode_theme, story_tone)
        tone_note = TONE_GUIDES.get(story_tone, TONE_GUIDES["Emotional"])
        style_note = STYLE_GUIDES.get(narration_style, STYLE_GUIDES["Calm Storytelling"])

        episode_hooks = [
            f"เคยไหม...เรื่อง {topic} มันไม่ได้จบตรงเหตุการณ์ แต่มันค้างอยู่ในใจ",
            f"วันนี้อยากเล่าเรื่อง {topic} แบบที่หลายคนอาจไม่กล้าพูดออกมา",
            f"ถ้าคุณกำลังเจอ {keywords[0]} ตอนนี้ episode นี้อาจพูดแทนใจคุณ",
            f"เรื่องนี้เริ่มจากเรื่องเล็ก ๆ แต่สุดท้ายมันเปลี่ยนวิธีมองชีวิตไปเลย",
        ]
        if story_tone == "Viral Rant":
            episode_hooks.insert(0, f"ขอพูดตรง ๆ นะ เรื่อง {topic} มันไม่ควรปกติขนาดนี้")
        if story_tone == "Funny":
            episode_hooks.insert(0, f"เรื่อง {topic} นี่ตอนแรกคิดว่าขำ ๆ แต่เอาจริงคือชีวิตมาก")

        intro = [
            f"สวัสดีครับ วันนี้เราจะคุยกันเรื่อง {topic}",
            f"ธีมของตอนนี้คือ {episode_theme}",
            f"ผมอยากเล่าให้ฟังแบบไม่เร่ง เพราะบางเรื่องต้องค่อย ๆ แกะ ถึงจะเข้าใจว่ามันกระทบใจเรายังไง",
        ]

        beats = [
            f"เริ่มจากจุดที่หลายคนคุ้นมาก คือ {keywords[0]}",
            f"สิ่งที่ทำให้เรื่องนี้หนักขึ้นคือ มันไม่ได้เกิดแค่ครั้งเดียว แต่มันสะสมจนเราเริ่มสงสัยตัวเอง",
            f"พอเวลาผ่านไป เราจะเริ่มเห็นว่าเรื่อง {topic} ไม่ได้เกี่ยวกับคนอื่นอย่างเดียว แต่มันเกี่ยวกับขอบเขตของเราด้วย",
            f"จุดเปลี่ยนคือวันที่เราเริ่มถามตัวเองว่า เราต้องทนสิ่งนี้ไปเพื่ออะไร",
            f"สุดท้ายบทเรียนของเรื่องนี้อาจไม่ใช่การชนะใคร แต่คือการกลับมาเลือกตัวเองแบบไม่รู้สึกผิด",
        ]
        if length_detail["beats"] > 5:
            beats.extend([
                f"อีกมุมหนึ่งที่น่าสนใจคือ คนฟังหลายคนอาจเคยผ่าน {keywords[-1]} แต่ไม่เคยเรียกมันออกมาตรง ๆ",
                "ช่วงนี้คือพื้นที่ให้เรายอมรับว่า เหนื่อยก็คือเหนื่อย ไม่ต้องรีบทำตัวเข้มแข็งตลอดเวลา",
                "ถ้าจะเริ่มใหม่ อาจเริ่มจากสิ่งเล็ก ๆ เช่น พูดความจริงกับตัวเองหนึ่งประโยค",
                "และบางครั้งการเงียบ ไม่ได้แปลว่าแพ้ แต่มันคือการไม่เอาพลังชีวิตไปทิ้งกับเรื่องเดิม",
            ])
        main_script = beats[: length_detail["beats"]]

        emotional_monologue = [
            f"บางทีสิ่งที่เจ็บที่สุดในเรื่อง {topic} ไม่ใช่เหตุการณ์วันนั้น",
            "แต่มันคือความรู้สึกที่เราต้องเก็บไว้คนเดียว",
            "เราไม่ได้ต้องการให้ใครเข้าใจทั้งหมด แค่ต้องการให้มีใครสักคนบอกว่า มันหนักจริงนะ",
            "และถ้าวันนี้คุณยังไม่ไหว ก็ไม่เป็นไร แค่ยังอยู่ตรงนี้ได้ ก็เก่งมากแล้ว",
        ]

        viral_rant = [
            f"ขอพูดแบบไม่อ้อมนะ เรื่อง {topic} มันเหนื่อยเพราะทุกคนทำเหมือนเราต้องรับไหวตลอด",
            "ทั้งที่บางครั้งสิ่งที่ควรถามไม่ใช่ว่าเราทนได้ไหม แต่คือทำไมเราต้องทน",
            "ถ้าความสัมพันธ์ งาน หรือสังคม ทำให้เรารู้สึกเล็กลงทุกวัน มันไม่ใช่เรื่องเล็กแล้ว",
            "และการเลือกเดินออกมา ไม่ได้แปลว่าอ่อนแอ มันแปลว่าเรายังเห็นค่าตัวเองอยู่",
        ]

        shorts = [
            "ตัดช่วงเปิด hook 8-12 วินาทีแรกเป็นคลิปตั้งคำถาม",
            "ตัด emotional monologue ช่วง 'มันหนักจริงนะ' เป็นคลิปปลอบใจ",
            "ตัด viral rant เป็นคลิป POV สำหรับ TikTok",
            "ตัดช่วงบทเรียนท้าย episode เป็น Shorts แบบ reflective",
        ]
        tiktok_hooks = [
            f"POV: คุณเหนื่อยกับ {topic} แต่ยังต้องทำเหมือนไม่เป็นไร",
            f"ประโยคเดียวที่ทำให้เรื่อง {topic} เจ็บขึ้นกว่าเดิม",
            "บางเรื่องไม่ได้ต้อง move on ไว แค่ต้องเข้าใจก่อนว่ามันเจ็บตรงไหน",
            "ถ้าคุณกำลังรู้สึกแบบนี้ ฟังให้จบ",
        ]
        title_ideas = [
            title,
            f"วันที่ {topic} ทำให้เราเปลี่ยนไป",
            f"เรื่อง {topic} ที่ไม่มีใครพูดตรง ๆ",
            f"ถ้าคุณกำลังเจอ {topic} อยู่",
        ]
        youtube_description = (
            f"ตอนนี้พูดถึง {topic} ผ่านมุมมอง {story_tone.lower()} สำหรับ {target_audience}\n\n"
            f"ธีมหลัก: {episode_theme}\n"
            f"สไตล์การเล่า: {narration_style} - {style_note}\n\n"
            "ฟังแบบช้า ๆ แล้วลองกลับไปถามตัวเองว่า เรื่องนี้กำลังบอกอะไรกับเรา\n\n"
            "#Podcastไทย #เล่าเรื่อง #VelaFlow"
        )
        hashtags = [
            "#Podcastไทย",
            "#เล่าเรื่อง",
            "#เรื่องเล่า",
            "#TikTokPodcast",
            "#Shorts",
            "#พัฒนาตัวเอง",
            "#ชีวิตวัยทำงาน",
            "#ความรู้สึก",
            "#VelaFlow",
        ]
        if story_tone == "Dark Office":
            hashtags.extend(["#ออฟฟิศ", "#ชีวิตทำงาน"])
        if story_tone == "Viral Rant":
            hashtags.extend(["#ระบาย", "#พูดตรงๆ"])
        ai_video_prompt = (
            f"vertical 9:16 cinematic podcast visual for an episode about {topic}, "
            f"Thai urban realistic mood, {story_tone.lower()} tone, close-up microphone, "
            "soft studio light, subtle b-roll of city night, office desk, reflective window, "
            "emotional storytelling, clean composition, no random text"
        )
        thumbnail_prompt = (
            f"high quality realistic podcast thumbnail about {topic}, emotional Thai storyteller, "
            f"{story_tone.lower()} mood, bold clean composition, space for episode title only, "
            "no logo, no watermark, no random text"
        )

        package = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "workflow_type": "podcast",
            "podcast_topic": topic,
            "episode_theme": episode_theme,
            "story_tone": story_tone,
            "target_audience": target_audience,
            "episode_length": episode_length,
            "narration_style": narration_style,
            "tone_note": tone_note,
            "narration_note": style_note,
            "episode_title": title,
            "episode_hooks": episode_hooks[:5],
            "podcast_intro": intro,
            "main_script": main_script,
            "emotional_monologue": emotional_monologue,
            "viral_rant_version": viral_rant,
            "shorts_extraction_ideas": shorts,
            "tiktok_clip_hooks": tiktok_hooks,
            "episode_title_ideas": title_ideas,
            "youtube_description": youtube_description,
            "hashtags": hashtags[:16],
            "ai_video_prompt": ai_video_prompt,
            "thumbnail_prompt": thumbnail_prompt,
            "script_note": length_detail["words"],
        }
        package = apply_visual_engine_to_package(package, "podcast", visual_settings)
        return {"ok": True, "message": "Podcast episode package generated", "data": package, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Podcast generation failed", "data": {}, "error": str(exc)}


def podcast_content_to_text(package: Dict[str, Any]) -> str:
    def lines(title: str, values: Any) -> str:
        if isinstance(values, list):
            body = "\n".join(f"- {item}" for item in values) if values else "-"
        else:
            body = str(values or "-")
        return f"====================\n{title}\n====================\n{body}\n"

    sections = [
        lines("PODCAST METADATA", [
            f"Episode Title: {package.get('episode_title', '')}",
            f"Topic: {package.get('podcast_topic', '')}",
            f"Theme: {package.get('episode_theme', '')}",
            f"Tone: {package.get('story_tone', '')}",
            f"Narration Style: {package.get('narration_style', '')}",
            f"Episode Length: {package.get('episode_length', '')}",
            f"Target Audience: {package.get('target_audience', '')}",
            f"Camera Preset: {(package.get('visual_engine') or {}).get('camera_preset', '-')}",
            f"Lighting Preset: {(package.get('visual_engine') or {}).get('lighting_preset', '-')}",
            f"Motion Preset: {(package.get('visual_engine') or {}).get('motion_preset', '-')}",
            f"Visual Mood: {(package.get('visual_engine') or {}).get('visual_mood', '-')}",
        ]),
        lines("EPISODE HOOKS", package.get("episode_hooks", [])),
        lines("PODCAST INTRO", package.get("podcast_intro", [])),
        lines("MAIN SCRIPT", package.get("main_script", [])),
        lines("EMOTIONAL MONOLOGUE", package.get("emotional_monologue", [])),
        lines("VIRAL RANT VERSION", package.get("viral_rant_version", [])),
        lines("SHORTS EXTRACTION IDEAS", package.get("shorts_extraction_ideas", [])),
        lines("TIKTOK CLIP HOOKS", package.get("tiktok_clip_hooks", [])),
        lines("EPISODE TITLE IDEAS", package.get("episode_title_ideas", [])),
        lines("YOUTUBE DESCRIPTION", package.get("youtube_description", "")),
        lines("HASHTAGS", " ".join(package.get("hashtags", []))),
        lines("AI VIDEO PROMPT", package.get("ai_video_prompt", "")),
        lines("THUMBNAIL PROMPT", package.get("thumbnail_prompt", "")),
    ]
    return "\n".join(sections).strip() + "\n"


def export_podcast_content(project_name: str, package: Dict[str, Any], base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        folder = Path(base_dir) / safe_name(project_name or package.get("episode_title") or "podcast_episode") if base_dir else resolve_project_folder(project_name or package.get("episode_title") or "podcast_episode", "podcast")
        export_dir = folder / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        txt_path = export_dir / "podcast_episode_package.txt"
        json_path = export_dir / "podcast_episode_package.json"
        txt_path.write_text(podcast_content_to_text(package), encoding="utf-8")
        json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "message": "Podcast package exported",
            "data": {"txt_path": str(txt_path), "json_path": str(json_path), "export_dir": str(export_dir)},
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "Podcast export failed", "data": {}, "error": str(exc)}


def build_podcast_dashboard_status(project: Dict[str, Any]) -> Dict[str, Any]:
    podcast = (project.get("podcast_studio", {}) or {}).get("content_package", {}) or {}
    export_data = (project.get("podcast_studio", {}) or {}).get("export", {}) or {}
    stages = [
        {"name": "Hooks", "ok": bool(podcast.get("episode_hooks")), "detail": f"{len(podcast.get('episode_hooks', []))} hooks"},
        {"name": "Intro", "ok": bool(podcast.get("podcast_intro")), "detail": "ready" if podcast.get("podcast_intro") else "not generated"},
        {"name": "Main Script", "ok": bool(podcast.get("main_script")), "detail": podcast.get("episode_length", "-")},
        {"name": "Shorts Ideas", "ok": bool(podcast.get("shorts_extraction_ideas")), "detail": f"{len(podcast.get('shorts_extraction_ideas', []))} ideas"},
        {"name": "Export Package", "ok": bool(export_data.get("txt_path")), "detail": "podcast_episode_package.txt" if export_data.get("txt_path") else "not exported"},
    ]
    return {
        "ok": True,
        "message": "Podcast dashboard ready",
        "data": {
            "episode_title": podcast.get("episode_title") or project.get("title") or "ตอนใหม่ของฉัน",
            "topic": podcast.get("podcast_topic") or "No topic selected",
            "content_items": sum(1 for stage in stages if stage["ok"]),
            "stages": stages,
        },
        "next_step": {"stage": "Podcast Script", "label": "Generate podcast episode", "page": "Podcast Studio"},
        "error": "",
    }
