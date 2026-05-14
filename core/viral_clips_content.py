from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name
from core.paths import resolve_project_folder
from core.visual_engine import apply_visual_engine_to_package
from providers.provider_manager import generate_text


SOURCE_TYPES = ["Music", "Seller Product", "Podcast", "General Idea"]
TARGET_PLATFORMS = ["TikTok", "Reels", "Shorts"]
TONE_STYLES = ["Emotional", "Funny", "Direct", "Review", "Storytelling", "Viral Energy"]
CLIP_LENGTHS = ["15 sec", "30 sec", "60 sec"]
GOALS = ["Awareness", "Sell", "Emotional", "Viral", "Storytelling"]


def _lines(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip(" -•\t") for part in re.split(r"[\n;]+", str(value or "")) if part.strip(" -•\t")]


def _offline_package(
    source_type: str,
    main_idea: str,
    target_platform: str,
    tone_style: str,
    clip_length: str,
    goal: str,
    provider: str = "offline",
    model_name: str = "",
) -> Dict[str, Any]:
    idea = (main_idea or "ไอเดียคอนเทนต์ใหม่").strip()
    source_type = source_type if source_type in SOURCE_TYPES else "General Idea"
    target_platform = target_platform if target_platform in TARGET_PLATFORMS else "TikTok"
    tone_style = tone_style if tone_style in TONE_STYLES else "Emotional"
    clip_length = clip_length if clip_length in CLIP_LENGTHS else "30 sec"
    goal = goal if goal in GOALS else "Viral"

    lead = {
        "Music": "ท่อนนี้ทำให้คนหยุดฟัง",
        "Seller Product": "ของชิ้นนี้แก้ปัญหาเล็ก ๆ ที่เจอบ่อย",
        "Podcast": "ประโยคนี้เหมือนพูดแทนใจคนฟัง",
        "General Idea": "ไอเดียนี้เปิดคลิปได้แรงมาก",
    }.get(source_type, "ไอเดียนี้เปิดคลิปได้แรงมาก")
    cta = {
        "Awareness": "คอมเมนต์ว่าคุณเคยเจอแบบนี้ไหม",
        "Sell": "ถ้าอยากลอง เก็บคลิปนี้ไว้ก่อน",
        "Emotional": "ส่งให้คนที่กำลังรู้สึกแบบเดียวกัน",
        "Viral": "ฟังให้จบแล้วบอกว่าคิดเหมือนกันไหม",
        "Storytelling": "ติดตามตอนต่อไป เดี๋ยวเล่าให้ฟังต่อ",
    }.get(goal, "ฟังให้จบแล้วบอกว่าคิดเหมือนกันไหม")

    viral_hooks = [
        f"{lead}: {idea}",
        f"ถ้าคุณเคยเจอเรื่องนี้ คลิปนี้พูดแทนใจคุณ",
        f"อย่าเพิ่งเลื่อน ถ้าเรื่อง {idea} เคยเกิดกับคุณ",
        f"POV: คุณกำลังเจอ {idea} แต่ไม่รู้จะพูดยังไง",
        f"นี่คือสิ่งที่คนส่วนใหญ่ไม่พูดเกี่ยวกับ {idea}",
    ]
    short_script = [
        f"เปิดคลิปด้วยประโยคสั้น ๆ: '{viral_hooks[0]}'",
        f"เล่า pain point หรืออารมณ์หลักของ {idea} แบบภาษาคนพูดจริง",
        "ยกตัวอย่างหนึ่งภาพที่คนดูนึกตามได้ทันที",
        f"ปิดด้วยข้อคิดหรือ action ที่ตรงกับเป้าหมาย: {goal}",
        cta,
    ]
    if clip_length == "15 sec":
        short_script = short_script[:3] + [cta]
    elif clip_length == "60 sec":
        short_script.insert(3, "ขยายด้วยรายละเอียดอีกหนึ่งจังหวะ แต่ยังไม่ให้ยืด")

    subtitle_lines = [
        "อย่าเพิ่งเลื่อน",
        f"เรื่องนี้คือ {idea}",
        "หลายคนเจอ แต่ไม่ค่อยพูด",
        "ฟังประโยคนี้ให้จบ",
        cta,
    ]
    hashtags = [
        "#VelaFlow",
        "#TikTokไทย",
        "#ReelsThailand",
        "#Shorts",
        "#คอนเทนต์ไวรัล",
        "#เล่าเรื่อง",
        "#ครีเอเตอร์",
        "#คลิปสั้น",
    ]
    if goal == "Sell":
        hashtags.extend(["#รีวิวสินค้า", "#Affiliate"])
    if source_type == "Music":
        hashtags.extend(["#เพลงไทย", "#เพลงใหม่"])
    if source_type == "Podcast":
        hashtags.extend(["#Podcastไทย", "#เรื่องเล่า"])

    scene_ideas = [
        "เปิดด้วย close-up สีหน้าหรือสินค้าหลัก",
        "ตัดไป b-roll สั้น ๆ ที่สื่อปัญหาหรืออารมณ์",
        "ใส่ subtitle ใหญ่ตรง hook แรก",
        "ใช้ jump cut ตอน punchline",
        "จบด้วย frame ที่จำง่ายและ CTA ชัด",
    ]
    broll = [
        "มือหยิบโทรศัพท์แล้วหยุดเลื่อน",
        "เดินผ่านไฟเมืองตอนกลางคืน",
        "โต๊ะทำงานหรือห้องนอนที่ดูจริง",
        "close-up รายละเอียดสินค้าหรือสีหน้าคนเล่า",
        "reaction shot สั้น ๆ ก่อนจบคลิป",
    ]
    ai_video_prompt = (
        f"vertical 9:16 short-form video, Thai creator style, {tone_style.lower()} tone, "
        f"concept about {idea}, concise cinematic realistic shots, fast readable subtitles, "
        f"optimized for {target_platform}, no random text, no watermark"
    )
    thumbnail_prompt = (
        f"high quality vertical thumbnail for {target_platform}, Thai creator emotional expression, "
        f"concept: {idea}, bold clean composition, short title space only, no logo, no watermark"
    )
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "workflow_type": "clips",
        "source_type": source_type,
        "main_idea": idea,
        "target_platform": target_platform,
        "tone_style": tone_style,
        "clip_length": clip_length,
        "goal": goal,
        "viral_hooks": viral_hooks,
        "short_script": short_script,
        "subtitle_lines": subtitle_lines,
        "caption": f"{viral_hooks[1]} {cta}",
        "hashtags": hashtags[:18],
        "scene_ideas": scene_ideas,
        "broll_ideas": broll,
        "ai_video_prompt": ai_video_prompt,
        "thumbnail_prompt": thumbnail_prompt,
        "cta": cta,
        "active_ai_provider": provider,
        "active_ai_model": model_name,
    }


def _extract_json(text: str) -> Dict[str, Any]:
    match = re.search(r"(\{.*\})", text or "", re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")
    return json.loads(match.group(1))


def generate_viral_clips_content(
    source_type: str,
    main_idea: str,
    target_platform: str,
    tone_style: str,
    clip_length: str,
    goal: str,
    *,
    provider: str = "gemini",
    api_key: str = "",
    model_name: str = "",
    visual_settings: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    try:
        fallback = _offline_package(source_type, main_idea, target_platform, tone_style, clip_length, goal, provider, model_name)
        prompt = f"""
Create a concise Thai short-form content package for VelaFlow Viral Clips Studio.
Return JSON only. Natural Thai creator tone. Keep it short and usable.

Input:
- Source Type: {source_type}
- Main Idea: {main_idea}
- Target Platform: {target_platform}
- Tone Style: {tone_style}
- Clip Length: {clip_length}
- Goal: {goal}

JSON keys:
viral_hooks, short_script, subtitle_lines, caption, hashtags, scene_ideas,
broll_ideas, ai_video_prompt, thumbnail_prompt, cta
"""
        if api_key:
            try:
                text = generate_text(
                    provider=provider,
                    api_key=api_key,
                    prompt=prompt,
                    primary_model=model_name,
                    offline_factory=lambda: json.dumps(fallback, ensure_ascii=False),
                )
                data = {**fallback, **_extract_json(text)}
            except Exception:
                data = fallback
        else:
            data = fallback
        for key in ["viral_hooks", "short_script", "subtitle_lines", "hashtags", "scene_ideas", "broll_ideas"]:
            data[key] = _lines(data.get(key))[:18]
        data["active_ai_provider"] = provider
        data["active_ai_model"] = model_name
        data = apply_visual_engine_to_package(data, "clips", visual_settings)
        return {"ok": True, "message": "Viral clips package generated", "data": data, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Viral clips generation failed", "data": {}, "error": str(exc)}


def viral_clips_to_text(package: Dict[str, Any]) -> str:
    def section(title: str, value: Any) -> str:
        if isinstance(value, list):
            body = "\n".join(f"- {item}" for item in value) if value else "-"
        else:
            body = str(value or "-")
        return f"====================\n{title}\n====================\n{body}\n"

    return "\n".join([
        section("VIRAL CLIPS METADATA", [
            f"Source Type: {package.get('source_type', '')}",
            f"Main Idea: {package.get('main_idea', '')}",
            f"Target Platform: {package.get('target_platform', '')}",
            f"Tone Style: {package.get('tone_style', '')}",
            f"Clip Length: {package.get('clip_length', '')}",
            f"Goal: {package.get('goal', '')}",
            f"AI Provider: {package.get('active_ai_provider', '')}",
            f"Camera Preset: {(package.get('visual_engine') or {}).get('camera_preset', '-')}",
            f"Lighting Preset: {(package.get('visual_engine') or {}).get('lighting_preset', '-')}",
            f"Motion Preset: {(package.get('visual_engine') or {}).get('motion_preset', '-')}",
            f"Visual Mood: {(package.get('visual_engine') or {}).get('visual_mood', '-')}",
        ]),
        section("VIRAL HOOKS", package.get("viral_hooks", [])),
        section("SHORT SCRIPT", package.get("short_script", [])),
        section("SUBTITLE LINES", package.get("subtitle_lines", [])),
        section("CAPTION", package.get("caption", "")),
        section("HASHTAGS", " ".join(package.get("hashtags", []))),
        section("SCENE IDEAS", package.get("scene_ideas", [])),
        section("B-ROLL IDEAS", package.get("broll_ideas", [])),
        section("AI VIDEO PROMPT", package.get("ai_video_prompt", "")),
        section("THUMBNAIL PROMPT", package.get("thumbnail_prompt", "")),
        section("CTA", package.get("cta", "")),
    ]).strip() + "\n"


def export_viral_clips_content(project_name: str, package: Dict[str, Any], base_dir: str | Path | None = None) -> Dict[str, Any]:
    try:
        folder = Path(base_dir) / safe_name(project_name or package.get("main_idea") or "viral_clips_project") if base_dir else resolve_project_folder(project_name or package.get("main_idea") or "viral_clips_project", "clips")
        export_dir = folder / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        txt_path = export_dir / "viral_clips_package.txt"
        json_path = export_dir / "viral_clips_package.json"
        txt_path.write_text(viral_clips_to_text(package), encoding="utf-8")
        json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "Viral clips package exported", "data": {"txt_path": str(txt_path), "json_path": str(json_path), "export_dir": str(export_dir)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Viral clips export failed", "data": {}, "error": str(exc)}


def build_viral_clips_dashboard_status(project: Dict[str, Any]) -> Dict[str, Any]:
    package = (project.get("viral_clips_studio", {}) or {}).get("content_package", {}) or {}
    export_data = (project.get("viral_clips_studio", {}) or {}).get("export", {}) or {}
    stages = [
        {"name": "Hooks", "ok": bool(package.get("viral_hooks")), "detail": f"{len(package.get('viral_hooks', []))} hooks"},
        {"name": "Script", "ok": bool(package.get("short_script")), "detail": package.get("clip_length", "-")},
        {"name": "Subtitles", "ok": bool(package.get("subtitle_lines")), "detail": f"{len(package.get('subtitle_lines', []))} lines"},
        {"name": "Video Prompt", "ok": bool(package.get("ai_video_prompt")), "detail": package.get("target_platform", "-")},
        {"name": "Export Package", "ok": bool(export_data.get("txt_path")), "detail": "viral_clips_package.txt" if export_data.get("txt_path") else "not exported"},
    ]
    return {
        "ok": True,
        "message": "Viral clips dashboard ready",
        "data": {
            "campaign_name": project.get("title") or "New Viral Clip",
            "main_idea": package.get("main_idea") or "No idea selected",
            "content_items": sum(1 for stage in stages if stage["ok"]),
            "stages": stages,
        },
        "next_step": {"stage": "Viral Clips", "label": "Generate viral clips", "page": "Viral Clips Studio"},
        "error": "",
    }
