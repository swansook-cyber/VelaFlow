from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name


TONE_GUIDES = {
    "Friendly Creator": "friendly, conversational, relatable creator-style selling",
    "Energetic TikTok": "fast, punchy, trend-aware short-form selling",
    "Trust Builder": "clear, helpful, confidence-building product explanation",
    "Problem Solution": "problem-first storytelling with a practical product payoff",
    "Soft Lifestyle": "warm lifestyle tone with gentle product recommendation",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _split_points(value: str) -> List[str]:
    parts = re.split(r"[\n,;]+", value or "")
    return [part.strip(" -•\t") for part in parts if part.strip(" -•\t")]


def _hashtags(product_name: str, category: str, audience: str) -> List[str]:
    words = [word for word in re.split(r"\s+", f"{product_name} {category} {audience}") if word]
    tags = ["#TikTokShop", "#ของดีบอกต่อ", "#รีวิวสินค้า", "#ช้อปออนไลน์", "#ของมันต้องมี", "#โปรดี"]
    for word in words[:8]:
        clean = re.sub(r"[^\wก-๙]", "", word, flags=re.UNICODE)
        if clean:
            tag = f"#{clean}"
            if tag not in tags:
                tags.append(tag)
    return tags[:20]


def generate_seller_content(
    product_name: str,
    product_category: str,
    target_audience: str,
    key_selling_points: str | List[str],
    tone_style: str = "Friendly Creator",
) -> Dict[str, Any]:
    try:
        name = _clean(product_name) or "สินค้าแนะนำ"
        category = _clean(product_category) or "Lifestyle Product"
        audience = _clean(target_audience) or "คนที่กำลังมองหาของใช้คุ้มค่า"
        points = key_selling_points if isinstance(key_selling_points, list) else _split_points(str(key_selling_points or ""))
        points = [_clean(point) for point in points if _clean(point)] or ["ใช้ง่าย", "ช่วยประหยัดเวลา", "เหมาะกับการใช้ทุกวัน"]
        tone = TONE_GUIDES.get(tone_style, tone_style or TONE_GUIDES["Friendly Creator"])
        main_point = points[0]
        second_point = points[1] if len(points) > 1 else points[0]
        third_point = points[2] if len(points) > 2 else second_point

        hooks = [
            f"ถ้าคุณเป็นสาย {category} ต้องดู {name} ตัวนี้",
            f"ของชิ้นนี้ช่วยเรื่อง {main_point} ได้ง่ายกว่าที่คิด",
            f"ลองใช้ {name} แล้วเข้าใจเลยว่าทำไมคนพูดถึง",
            f"ใครที่อยากได้ของสำหรับ {audience} ตัวนี้น่าสนใจมาก",
            f"นี่คือไอเทมที่ทำให้ {second_point} ดูง่ายขึ้น",
        ]
        script = [
            f"เปิดคลิปด้วยภาพสินค้า: \"วันนี้เจอ {name} ที่เหมาะกับคนที่ต้องการ {main_point}\"",
            f"โชว์การใช้งานจริง: \"จุดที่ชอบคือ {second_point} ใช้แล้วเห็นภาพทันที\"",
            f"ซูมดีเทลหรือ before/after: \"อีกอย่างคือ {third_point} ทำให้รู้สึกคุ้มขึ้น\"",
            f"ปิดด้วย CTA: \"ใครกำลังหาแนวนี้ ลองกดดูรายละเอียดไว้ก่อนนะ\"",
        ]
        ctas = [
            "กดดูรายละเอียดสินค้าไว้ก่อนได้เลย",
            "ถ้ากำลังหาไอเทมแบบนี้ ลองเช็กราคาในตะกร้า",
            "ดูโปรล่าสุดก่อนตัดสินใจนะ",
            "บันทึกคลิปนี้ไว้ เผื่อกลับมาดูทีหลัง",
        ]
        caption = f"{name} สำหรับสาย {category} ที่อยากได้ตัวช่วยเรื่อง {main_point} ใช้ง่าย เล่าแบบจริงใจ เหมาะกับ {audience}"
        video_prompt = (
            f"vertical 9:16 TikTok product video for {name}, {category}, creator-style selling, "
            f"realistic handheld shots, clean product close-ups, natural lifestyle lighting, "
            f"show product use, quick cuts, conversational mood, optimized for Reels and Shorts"
        )
        broll = [
            "product close-up on clean table with natural light",
            "creator holding product and pointing to key detail",
            "before and after usage shot",
            "hands-on demonstration in real environment",
            "packaging reveal and texture/detail close-up",
            "final hero shot with product centered for vertical frame",
        ]
        package = {
            "product_name": name,
            "product_category": category,
            "target_audience": audience,
            "key_selling_points": points,
            "tone_style": tone_style,
            "tone_guide": tone,
            "tiktok_hooks": hooks,
            "short_video_script": script,
            "cta_suggestions": ctas,
            "caption": caption,
            "hashtags": _hashtags(name, category, audience),
            "ai_video_prompt": video_prompt,
            "broll_shot_ideas": broll,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        return {"ok": True, "message": "Seller content generated", "data": package, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Seller content generation failed", "data": {}, "error": str(exc)}


def seller_content_to_text(package: Dict[str, Any]) -> str:
    lines = [
        "SELLER CONTENT PACKAGE",
        "",
        f"Product Name: {package.get('product_name', '')}",
        f"Category: {package.get('product_category', '')}",
        f"Target Audience: {package.get('target_audience', '')}",
        f"Tone Style: {package.get('tone_style', '')}",
        "",
        "====================",
        "TIKTOK HOOKS",
        "====================",
        *[f"- {item}" for item in package.get("tiktok_hooks", [])],
        "",
        "====================",
        "SHORT VIDEO SCRIPT",
        "====================",
        *[f"{idx}. {item}" for idx, item in enumerate(package.get("short_video_script", []), start=1)],
        "",
        "====================",
        "CTA SUGGESTIONS",
        "====================",
        *[f"- {item}" for item in package.get("cta_suggestions", [])],
        "",
        "====================",
        "CAPTION",
        "====================",
        package.get("caption", ""),
        "",
        "====================",
        "HASHTAGS",
        "====================",
        " ".join(package.get("hashtags", [])),
        "",
        "====================",
        "AI VIDEO PROMPT",
        "====================",
        package.get("ai_video_prompt", ""),
        "",
        "====================",
        "B-ROLL SHOT IDEAS",
        "====================",
        *[f"- {item}" for item in package.get("broll_shot_ideas", [])],
        "",
    ]
    return "\n".join(lines).strip() + "\n"


def export_seller_content(
    project_name: str,
    package: Dict[str, Any],
    base_dir: str | Path = "project_data/projects",
) -> Dict[str, Any]:
    try:
        project_dir = Path(base_dir) / safe_name(project_name or package.get("product_name") or "seller_project")
        export_dir = project_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        txt_path = export_dir / "seller_content_package.txt"
        json_path = export_dir / "seller_content_package.json"
        txt_path.write_text(seller_content_to_text(package), encoding="utf-8")
        json_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "message": "Seller content exported",
            "data": {"txt_path": str(txt_path), "json_path": str(json_path)},
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "Seller content export failed", "data": {}, "error": str(exc)}
