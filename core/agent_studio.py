from __future__ import annotations

from typing import Any


PROJECT_TYPES = [
    "Spotify Song Release",
    "TikTok Affiliate Clip",
    "AI Music Video Prompt",
    "Podcast Episode Idea",
    "General Creative Package",
]

LANGUAGES = ["Thai", "English", "Thai + English"]
TONES = ["Emotional", "Viral", "Commercial", "Funny", "Dark Office", "Soft Pop"]
AGENT_PROJECT_TYPES = PROJECT_TYPES
AGENT_LANGUAGES = LANGUAGES
AGENT_TONES = TONES

REQUIRED_AGENT_SECTIONS = [
    "Project Summary",
    "Best Title Ideas",
    "Main Creative Direction",
    "Lyrics or Script",
    "Suno / Music Style Prompt",
    "Video Prompt",
    "Cover Image Prompt",
    "TikTok Hook Ideas",
    "Caption",
    "Hashtags",
    "Next Action Checklist",
]


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _title_seed(user_idea: str) -> str:
    idea = _clean(user_idea, "ไอเดียใหม่")
    words = idea.replace("\n", " ").split()
    if 1 <= len(words) <= 5:
        return idea[:42]
    compact = idea.replace("เพลงเกี่ยวกับ", "").replace("คอนเทนต์เกี่ยวกับ", "").strip()
    return compact[:42] or "ไอเดียใหม่"


def _language_note(language: str) -> str:
    if language == "English":
        return "Write all creator-facing output in English."
    if language == "Thai + English":
        return "Use Thai as the main language and include concise English prompt wording where useful."
    return "ใช้ภาษาไทยเป็นหลัก พร้อมคำ prompt ภาษาอังกฤษเฉพาะจุดที่ต้องนำไปใช้กับ AI tools."


def _type_profile(project_type: str) -> dict[str, str]:
    profiles = {
        "Spotify Song Release": {
            "format": "release-ready emotional song package",
            "script_label": "Full song starter lyrics",
            "action": "Export Suno text, generate cover art, then prepare TikTok/Shorts promotion.",
        },
        "TikTok Affiliate Clip": {
            "format": "short affiliate content package",
            "script_label": "15-30s TikTok script",
            "action": "Film or generate product b-roll, copy hook/caption, then upload manually.",
        },
        "AI Music Video Prompt": {
            "format": "cinematic AI video prompt package",
            "script_label": "Scene-by-scene MV direction",
            "action": "Copy the video prompt into Flow, Veo, Runway, Kling, Pika, or Luma.",
        },
        "Podcast Episode Idea": {
            "format": "podcast episode starter pack",
            "script_label": "Episode intro and talking points",
            "action": "Record the episode, create 3 short clips, then post the strongest hook.",
        },
        "General Creative Package": {
            "format": "multi-platform creator package",
            "script_label": "Core creative script",
            "action": "Choose the strongest output section and turn it into a post, video, or song.",
        },
    }
    return profiles.get(project_type, profiles["General Creative Package"])


def generate_agent_package(user_idea: str, project_type: str, language: str, tone: str) -> dict[str, str]:
    idea = _clean(user_idea, "อยากสร้างโปรเจกต์ครีเอทีฟที่คนจำได้")
    project_type = project_type if project_type in PROJECT_TYPES else "General Creative Package"
    language = language if language in LANGUAGES else "Thai"
    tone = tone if tone in TONES else "Emotional"
    profile = _type_profile(project_type)
    seed = _title_seed(idea)
    title_ideas = [
        seed,
        f"{seed} ที่ยังอยู่ในใจ",
        f"ก่อนจะลืม {seed}",
    ]
    if tone == "Viral":
        title_ideas = [f"ทำไม {seed}", f"{seed} ไวรัล", f"คนต้องหยุดดู {seed}"]
    elif tone == "Commercial":
        title_ideas = [f"{seed} ที่ขายได้", f"คำตอบของ {seed}", f"เลือก {seed}"]
    elif tone == "Funny":
        title_ideas = [f"{seed} แบบงงๆ", f"เรื่องนี้ต้องเล่า", f"{seed} แต่ขำ"]

    direction = (
        f"Create a {profile['format']} from this raw idea: {idea}. "
        f"Tone: {tone}. Project type: {project_type}. {_language_note(language)} "
        "Keep it beginner-friendly, practical, and ready to copy into creator tools."
    )
    lyrics_or_script = "\n".join(
        [
            f"[Opening Hook]\n{title_ideas[0]}",
            "",
            f"[Main Idea]\n{idea}",
            "",
            f"[Development]\nBuild the emotion or selling point clearly in 3 short beats.",
            "",
            "[Ending]\nLeave one memorable line and a clear next action.",
        ]
    )
    if project_type == "Podcast Episode Idea":
        lyrics_or_script = "\n".join(
            [
                "[Episode Intro]",
                f"วันนี้เราจะคุยเรื่อง {idea}",
                "",
                "[Talking Points]",
                "1. ทำไมเรื่องนี้คนควรสนใจ",
                "2. ประสบการณ์หรือมุมมองที่คนอินได้",
                "3. บทเรียนหรือข้อสรุปที่เอาไปใช้ได้",
                "",
                "[Short Clip Hook]",
                f"มีสิ่งหนึ่งเกี่ยวกับ {seed} ที่คนส่วนใหญ่มองข้าม",
            ]
        )
    elif project_type == "TikTok Affiliate Clip":
        lyrics_or_script = "\n".join(
            [
                "[0-3s Hook]",
                f"ก่อนซื้อคิดว่าไม่จำเป็น แต่ {seed} เปลี่ยนความคิดเลย",
                "",
                "[3-12s Proof]",
                "โชว์ปัญหาก่อนใช้ แล้วตัดไปที่ผลลัพธ์หลังใช้แบบเห็นภาพ",
                "",
                "[12-20s CTA]",
                "ถ้าคุณเจอปัญหาเดียวกัน ลองกดดูรายละเอียดไว้ก่อน",
            ]
        )

    package = {
        "Project Summary": f"{project_type} package for: {idea}\nTone: {tone}\nLanguage: {language}",
        "Best Title Ideas": "\n".join(f"- {item}" for item in title_ideas),
        "Main Creative Direction": direction,
        "Lyrics or Script": lyrics_or_script,
        "Suno / Music Style Prompt": (
            f"modern emotional Thai pop, {tone.lower()} mood, memorable hook, clear vocal, warm production, "
            "commercial arrangement, strong chorus, cinematic atmosphere, TikTok-friendly first line, Suno-ready"
        ),
        "Video Prompt": (
            f"Vertical 9:16 cinematic video for {idea}. One clear subject, emotional progression, natural lighting, "
            "smooth camera movement, no text, no logo, no watermark, creator-ready shot pacing."
        ),
        "Cover Image Prompt": (
            f"Premium cover image for {seed}, cinematic lighting, strong focal point, emotional expression, "
            "clean composition, no random text, no watermark."
        ),
        "TikTok Hook Ideas": "\n".join(
            [
                f"- ถ้าคุณเคยรู้สึกแบบนี้กับ {seed}...",
                f"- เรื่องนี้ทำให้ {seed} กลับมามีความหมาย",
                f"- อย่าเพิ่งเลื่อน ถ้า {seed} ตรงกับใจคุณ",
            ]
        ),
        "Caption": f"{title_ideas[0]}\n\n{idea}\n\nสร้างด้วย VelaFlow",
        "Hashtags": "#VelaFlow #CreatorWorkflow #ThaiCreator #TikTokContent #AICreator",
        "Next Action Checklist": "\n".join(
            [
                "[ ] Pick one title",
                "[ ] Copy the script or lyrics",
                "[ ] Copy the video prompt into your AI video tool",
                "[ ] Generate or choose cover image",
                "[ ] Copy caption and hashtags",
                f"[ ] Next step: {profile['action']}",
            ]
        ),
    }
    return {key: _clean(package.get(key), f"{key} ready.") for key in REQUIRED_AGENT_SECTIONS}


def agent_package_to_text(package: dict[str, str]) -> str:
    blocks = []
    for section in REQUIRED_AGENT_SECTIONS:
        blocks.append(section)
        blocks.append("=" * len(section))
        blocks.append(_clean(package.get(section), "-"))
        blocks.append("")
    return "\n".join(blocks).strip() + "\n"
