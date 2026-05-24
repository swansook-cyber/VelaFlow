from __future__ import annotations

from typing import Any

from core.agent_memory import load_agent_memory, update_agent_memory
from core.agent_workflows import WORKFLOW_MODES, get_workflow_profile, workflow_memory_hint


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
AGENT_WORKFLOW_MODES = WORKFLOW_MODES

REQUIRED_AGENT_SECTIONS = [
    "Project Summary",
    "Agent Strategy",
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
    "Memory Notes",
]


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _title_seed(user_idea: str) -> str:
    idea = _clean(user_idea, "ไอเดียใหม่")
    words = idea.replace("\n", " ").split()
    if 1 <= len(words) <= 5:
        return idea[:42]
    compact = (
        idea.replace("เพลงเกี่ยวกับ", "")
        .replace("คอนเทนต์เกี่ยวกับ", "")
        .replace("คลิปเกี่ยวกับ", "")
        .strip()
    )
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


def _title_ideas(seed: str, tone: str, workflow_mode: str) -> list[str]:
    titles = [
        seed,
        f"{seed} ที่ยังอยู่ในใจ",
        f"ก่อนจะลืม {seed}",
    ]
    if tone == "Viral" or workflow_mode == "TikTok Viral Mode":
        titles = [f"ทำไม {seed}", f"{seed} ต้องดู", f"คนต้องหยุดดู {seed}"]
    elif tone == "Commercial":
        titles = [f"{seed} ที่ขายได้", f"คำตอบของ {seed}", f"เลือก {seed}"]
    elif tone == "Funny":
        titles = [f"{seed} แบบงงๆ", "เรื่องนี้ต้องเล่า", f"{seed} แต่ขำ"]
    elif workflow_mode == "Spotify Commercial Mode":
        titles = [seed, f"คืนของ {seed}", f"{seed} ไม่หายไป"]
    elif workflow_mode == "Podcast Episode Mode":
        titles = [f"ทำไมเราต้องคุยเรื่อง {seed}", f"บทเรียนจาก {seed}", f"{seed} ในวันที่โตขึ้น"]
    return titles


def _build_lyrics_or_script(project_type: str, idea: str, seed: str, title: str, workflow_mode: str) -> str:
    if workflow_mode == "Podcast Episode Mode" or project_type == "Podcast Episode Idea":
        return "\n".join(
            [
                "[Episode Intro]",
                f"วันนี้เราจะคุยเรื่อง {idea}",
                "",
                "[Segment 1: Why it matters]",
                f"เปิดด้วยเหตุผลที่ {seed} เกี่ยวกับชีวิตจริงของคนฟัง",
                "",
                "[Segment 2: Story / Example]",
                "เล่าเหตุการณ์หรือมุมมองที่ทำให้คนฟังรู้สึกว่า 'นี่แหละเรื่องของเรา'",
                "",
                "[Segment 3: Takeaway]",
                "สรุปบทเรียนที่เอาไปใช้ได้ทันที",
                "",
                "[Short Clip Extraction]",
                f"ตัดช่วงที่พูดว่า '{title}' เป็นคลิปสั้น 20-30 วินาที",
            ]
        )
    if project_type == "TikTok Affiliate Clip":
        return "\n".join(
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
    if workflow_mode == "MV Director Mode" or project_type == "AI Music Video Prompt":
        return "\n".join(
            [
                "[Scene 1]",
                f"Wide lonely opening for {idea}, slow camera drift, emotional atmosphere.",
                "",
                "[Scene 2]",
                "Medium shot, same character, stronger emotional realization.",
                "",
                "[Scene 3]",
                "Close-up eyes, strongest lyric moment, cinematic push-in.",
                "",
                "[Ending]",
                "Soft release shot, fade with lingering emotion.",
            ]
        )
    return "\n".join(
        [
            "[Opening Hook]",
            title,
            "",
            "[Verse / Setup]",
            f"เล่าอารมณ์หลักของ {idea} ให้จับต้องได้",
            "",
            "[Chorus / Main Message]",
            f"{title}",
            "ให้ประโยคนี้จำง่าย ร้องตามง่าย และกลับมาในหัวคนฟัง",
            "",
            "[Ending]",
            "ทิ้งหนึ่งประโยคที่ทำให้คนอยากฟังหรือดูต่อ",
        ]
    )


def generate_agent_package(
    user_idea: str,
    project_type: str,
    language: str,
    tone: str,
    workflow_mode: str = "Quick Generate",
    use_memory: bool = True,
) -> dict[str, str]:
    idea = _clean(user_idea, "อยากสร้างโปรเจกต์ครีเอทีฟที่คนจำได้")
    project_type = project_type if project_type in PROJECT_TYPES else "General Creative Package"
    language = language if language in LANGUAGES else "Thai"
    tone = tone if tone in TONES else "Emotional"
    workflow = get_workflow_profile(workflow_mode)
    memory = load_agent_memory() if use_memory else {}
    memory_hint = workflow_memory_hint(memory) if use_memory else "Agent memory was turned off for this generation."
    profile = _type_profile(project_type)
    seed = _title_seed(idea)
    titles = _title_ideas(seed, tone, workflow["workflow_mode"])
    title = titles[0]

    strategy = (
        f"Workflow: {workflow['workflow_mode']}\n"
        f"Strategy: {workflow['strategy']}\n"
        f"Focus: {', '.join(workflow['focus'])}\n"
        f"Memory guidance: {memory_hint}"
    )
    direction = (
        f"Create a {profile['format']} from this raw idea: {idea}. "
        f"Tone: {tone}. Project type: {project_type}. {_language_note(language)} "
        f"Use {workflow['workflow_mode']} pacing: {workflow['strategy']} "
        "Keep every section beginner-friendly, practical, and ready to copy."
    )
    video_focus = "storyboard, scenes, camera movement, lighting, and emotional progression"
    if workflow["workflow_mode"] == "TikTok Viral Mode":
        video_focus = "fast first-second hook, punchy cuts, bold visual contrast, replay value"
    elif workflow["workflow_mode"] == "Spotify Commercial Mode":
        video_focus = "cover-art consistency, release teaser pacing, strong chorus visual"
    elif workflow["workflow_mode"] == "Podcast Episode Mode":
        video_focus = "talking-head intro, clean segment graphics, shorts extraction moments"

    package = {
        "Project Summary": f"{project_type} package for: {idea}\nTone: {tone}\nLanguage: {language}\nWorkflow: {workflow['workflow_mode']}",
        "Agent Strategy": strategy,
        "Best Title Ideas": "\n".join(f"- {item}" for item in titles),
        "Main Creative Direction": direction,
        "Lyrics or Script": _build_lyrics_or_script(project_type, idea, seed, title, workflow["workflow_mode"]),
        "Suno / Music Style Prompt": (
            f"modern emotional Thai pop, {tone.lower()} mood, memorable hook, clear vocal, warm production, "
            "commercial arrangement, strong chorus, cinematic atmosphere, TikTok-friendly first line, Suno-ready"
        ),
        "Video Prompt": (
            f"Vertical 9:16 cinematic video for {idea}. Focus on {video_focus}. One clear subject, emotional progression, "
            "natural lighting, smooth camera movement, no text, no logo, no watermark, creator-ready shot pacing."
        ),
        "Cover Image Prompt": (
            f"Premium cover image for {title}, cinematic lighting, strong focal point, emotional expression, "
            "clean composition, no random text, no watermark."
        ),
        "TikTok Hook Ideas": "\n".join(
            [
                f"- ถ้าคุณเคยรู้สึกแบบนี้กับ {seed}...",
                f"- เรื่องนี้ทำให้ {seed} กลับมามีความหมาย",
                f"- อย่าเพิ่งเลื่อน ถ้า {seed} ตรงกับใจคุณ",
            ]
        ),
        "Caption": f"{title}\n\n{idea}\n\nสร้างด้วย VelaFlow",
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
        "Memory Notes": memory_hint,
    }
    output = {key: _clean(package.get(key), f"{key} ready.") for key in REQUIRED_AGENT_SECTIONS}
    if use_memory:
        update_agent_memory(project_type, language, tone, idea, output)
    return output


def agent_package_to_text(package: dict[str, str]) -> str:
    blocks = []
    for section in REQUIRED_AGENT_SECTIONS:
        blocks.append(section)
        blocks.append("=" * len(section))
        blocks.append(_clean(package.get(section), "-"))
        blocks.append("")
    return "\n".join(blocks).strip() + "\n"
