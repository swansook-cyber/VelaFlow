from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name
from core.visual_engine import apply_visual_engine_to_package
from providers.provider_manager import generate_text


TONE_GUIDES = {
    "Friendly Creator": "friendly, conversational, relatable creator-style selling",
    "Energetic TikTok": "fast, punchy, trend-aware short-form selling",
    "Trust Builder": "clear, helpful, confidence-building product explanation",
    "Problem Solution": "problem-first storytelling with a practical product payoff",
    "Soft Lifestyle": "warm lifestyle tone with gentle product recommendation",
}

HOOK_STYLES = ["Problem/Solution", "Curiosity", "POV", "Review", "Soft Sell", "Viral Energy"]
SONG_DEFAULT_TITLES = {"", "เพลงใหม่ของฉัน", "โปรเจกต์เพลงใหม่"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _split_points(value: str) -> List[str]:
    parts = re.split(r"[\n,;]+", value or "")
    return [part.strip(" -•\t") for part in parts if part.strip(" -•\t")]


def compress_selling_points(key_selling_points: str | List[str], limit: int = 6) -> List[str]:
    raw_points = key_selling_points if isinstance(key_selling_points, list) else _split_points(str(key_selling_points or ""))
    raw_points = [_clean(point) for point in raw_points if _clean(point)]
    text = " ".join(raw_points).lower()
    benefit_map = [
        ("นุ่ม", ["นุ่ม", "soft", "ละมุน"]),
        ("ไม่ร้อน", ["ไม่ร้อน", "ระบาย", "breathable", "เย็น", "อากาศ"]),
        ("กันไรฝุ่น", ["ไรฝุ่น", "dust mite", "ภูมิแพ้", "allergenic"]),
        ("นอนสบาย", ["นอน", "หลับ", "sleep", "comfort", "สบาย"]),
        ("พกง่าย", ["พก", "เบา", "portable", "เดินทาง", "carry"]),
        ("ใช้ง่าย", ["ใช้ง่าย", "ง่าย", "easy", "สะดวก"]),
        ("ประหยัดเวลา", ["ประหยัดเวลา", "เร็ว", "quick", "ไว"]),
        ("คุ้มราคา", ["คุ้ม", "ราคา", "value", "ประหยัด"]),
        ("ดีไซน์สวย", ["ดีไซน์", "สวย", "minimal", "มินิมอล", "design"]),
        ("ใช้ได้ทุกวัน", ["ทุกวัน", "daily", "ประจำวัน"]),
        ("ใช้ได้ทุกเพศทุกวัย", ["ทุกเพศ", "ทุกวัย", "ครอบครัว", "family"]),
        ("ทำความสะอาดง่าย", ["ทำความสะอาด", "ซัก", "ล้าง", "clean"]),
    ]
    benefits: List[str] = []
    for label, keywords in benefit_map:
        if any(keyword.lower() in text for keyword in keywords) and label not in benefits:
            benefits.append(label)
    for point in raw_points:
        short = re.sub(r"\s+", " ", point)
        for separator in [" เพราะ", " ที่", " ซึ่ง", " โดย", " with ", " for ", " and ", ","]:
            if separator in short:
                short = short.split(separator, 1)[0].strip()
        short = short[:24].strip()
        if short and short not in benefits:
            benefits.append(short)
        if len(benefits) >= limit:
            break
    return benefits[:limit] or ["ใช้ง่าย", "คุ้มราคา", "เหมาะกับทุกวัน"]


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


def _image_metadata(product_image: Dict[str, Any] | None) -> Dict[str, Any]:
    image = product_image or {}
    path = _clean(image.get("path"))
    filename = _clean(image.get("filename")) or (Path(path).name if path else "")
    note = (
        "Product image attached. Use visual details from the image for shot ideas, thumbnail prompt, and video prompt."
        if path
        else ""
    )
    return {
        "path": path,
        "filename": filename,
        "original_filename": _clean(image.get("original_filename")),
        "content_type": _clean(image.get("content_type")),
        "attached": bool(path),
        "note": note,
    }


def _extract_json(text: str) -> Dict[str, Any]:
    match = re.search(r"(\{.*\})", text or "", re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")
    return json.loads(match.group(1))


def _hooks_for_style(name: str, category: str, audience: str, benefits: List[str], hook_style: str) -> List[str]:
    b1 = benefits[0]
    b2 = benefits[1] if len(benefits) > 1 else b1
    styles = {
        "Problem/Solution": [
            f"มีปัญหาเรื่อง {b1} ไหม? ลองดู {name}",
            f"ถ้าอยากได้ของที่ {b2} ตัวนี้ตอบโจทย์",
            f"{category} ที่ช่วยให้ชีวิตง่ายขึ้นแบบไม่ต้องคิดเยอะ",
        ],
        "Curiosity": [
            f"ตอนแรกไม่คิดว่า {name} จะช่วยได้ขนาดนี้",
            f"เห็นชิ้นนี้แล้วเข้าใจเลยว่าทำไมคนพูดถึง",
            "รายละเอียดเล็ก ๆ ของตัวนี้น่าสนใจกว่าที่คิด",
        ],
        "POV": [
            f"POV: เจอ {name} แล้วใช้ทุกวันจริง",
            f"POV: อยากได้ของที่ {b1} แล้วเจอตัวนี้",
            f"POV: ซื้อของให้ {audience} แล้วไม่ผิดหวัง",
        ],
        "Review": [
            f"รีวิวสั้น ๆ หลังลองใช้ {name}",
            f"จุดที่ชอบของตัวนี้คือ {b1}",
            f"ใช้จริงแล้วรู้สึกว่า {b2} มาก",
        ],
        "Soft Sell": [
            f"ไม่ได้จะป้ายยาแรง แต่ {name} น่าสนใจจริง",
            "ถ้ากำลังหาแนวนี้ เก็บตัวนี้ไว้ดูก่อนได้",
            f"ตัวนี้เหมาะกับคนที่อยากได้ {b1}",
        ],
        "Viral Energy": [
            "หยุดดูแป๊บ ตัวนี้คือดีเกินคาด",
            f"{name} ตัวนี้ควรอยู่ในตะกร้าไหม มาดู",
            f"ของชิ้นนี้ทำให้ {b1} ง่ายขึ้นมาก",
        ],
    }
    hooks = list(styles.get(hook_style, styles["Problem/Solution"]))
    while len(hooks) < 5:
        hooks.append(f"{name} สำหรับสาย {category} ที่อยากได้ {benefits[len(hooks) % len(benefits)]}")
    return hooks[:5]


def generate_seller_content(
    product_name: str,
    product_category: str,
    target_audience: str,
    key_selling_points: str | List[str],
    tone_style: str = "Friendly Creator",
    product_image: Dict[str, Any] | None = None,
    hook_style: str = "Problem/Solution",
    visual_settings: Dict[str, Any] | None = None,
    provider: str = "offline",
    api_key: str = "",
    model_name: str = "",
) -> Dict[str, Any]:
    try:
        name = _clean(product_name) or "สินค้าแนะนำ"
        category = _clean(product_category) or "Lifestyle Product"
        audience = _clean(target_audience) or "คนที่กำลังมองหาของใช้คุ้มค่า"
        raw_points = key_selling_points if isinstance(key_selling_points, list) else _split_points(str(key_selling_points or ""))
        raw_points = [_clean(point) for point in raw_points if _clean(point)]
        benefits = compress_selling_points(raw_points)
        hook_style = hook_style if hook_style in HOOK_STYLES else "Problem/Solution"
        tone = TONE_GUIDES.get(tone_style, tone_style or TONE_GUIDES["Friendly Creator"])
        image_meta = _image_metadata(product_image)
        image_note = image_meta["note"]
        b1 = benefits[0]
        b2 = benefits[1] if len(benefits) > 1 else b1
        b3 = benefits[2] if len(benefits) > 2 else b2

        hooks = _hooks_for_style(name, category, audience, benefits, hook_style)
        script_15 = [
            f"0-3s: ถือสินค้าให้เห็นชัด แล้วพูดว่า 'ตัวนี้ช่วยเรื่อง {b1} ได้ดีมาก'",
            f"3-10s: โชว์การใช้จริงสั้น ๆ เน้น {b2}",
            "10-15s: ปิดด้วยภาพผลลัพธ์ แล้วชวนกดดูรายละเอียด",
        ]
        script_30 = [
            f"เปิดคลิป: 'ใครกำลังหา {category} ที่ {b1} ลองดูตัวนี้'",
            f"โชว์สินค้า: '{name} ใช้ง่าย แล้วจุดที่ชอบคือ {b2}'",
            f"ตัดภาพดีเทล: 'อีกอย่างคือ {b3} ทำให้รู้สึกคุ้มขึ้น'",
            "ปิดคลิป: 'ถ้าสนใจ กดดูรายละเอียดไว้ก่อนได้เลย'",
        ]
        script_60 = [
            f"0-5s: เล่าปัญหาของ {audience} แบบสั้น ๆ ว่าอยากได้ของที่ {b1}",
            f"5-15s: หยิบ {name} ขึ้นมาให้เห็นชัด แล้วบอกว่าตัวนี้น่าสนใจตรงไหน",
            f"15-30s: สาธิตการใช้จริง เน้น {b2} โดยไม่พูดยาวเกินไป",
            f"30-45s: โชว์ดีเทลสินค้าและเล่าประโยชน์เรื่อง {b3}",
            "45-55s: สรุปว่าเหมาะกับใคร ใช้ตอนไหน และทำไมควรกดดู",
            "55-60s: จบด้วย hero shot และ CTA สั้น ๆ",
        ]
        ctas = [
            "กดดูรายละเอียดสินค้าไว้ก่อนได้เลย",
            "ถ้ากำลังหาไอเทมแบบนี้ ลองเช็กราคาในตะกร้า",
            "ดูโปรล่าสุดก่อนตัดสินใจนะ",
            "บันทึกคลิปนี้ไว้ เผื่อกลับมาดูทีหลัง",
        ]
        caption = f"{name} สำหรับสาย {category} ที่อยากได้ {', '.join(benefits[:3])} เล่าง่าย ใช้จริง เหมาะกับ {audience}"
        video_prompt = (
            f"vertical 9:16 TikTok product video for {name}, {category}, creator-style selling, "
            f"realistic handheld shots, clean product close-ups, natural lifestyle lighting, "
            f"show benefits: {', '.join(benefits[:4])}, quick cuts, conversational mood, optimized for Reels and Shorts"
        )
        thumbnail_prompt = (
            f"vertical TikTok/Reels thumbnail for {name}, realistic product hero shot, clean readable composition, "
            f"highlight benefit: {b1}, creator-style selling visual, trustworthy, high contrast product focus, no random text"
        )
        broll = [
            "product close-up on clean table with natural light",
            f"creator demonstrating benefit: {b1}",
            f"quick detail shot showing {b2}",
            "hands-on demonstration in a real everyday environment",
            "packaging reveal and texture/detail close-up",
            "final hero shot with product centered for vertical frame",
        ]
        if image_note:
            video_prompt = f"{video_prompt}. {image_note}"
            thumbnail_prompt = f"{thumbnail_prompt}. {image_note}"
            broll.insert(0, "use uploaded product image as visual reference for product shape, color, packaging, and hero angle")

        package = {
            "product_name": name,
            "product_category": category,
            "target_audience": audience,
            "raw_selling_points": raw_points,
            "key_selling_points": raw_points,
            "compressed_benefits": benefits,
            "hook_style": hook_style,
            "tone_style": tone_style,
            "tone_guide": tone,
            "product_image": image_meta,
            "tiktok_hooks": hooks,
            "script_15s": script_15,
            "script_30s": script_30,
            "script_60s": script_60,
            "short_video_script": script_30,
            "final_script": {"15s": script_15, "30s": script_30, "60s": script_60},
            "cta_suggestions": ctas,
            "caption": caption,
            "hashtags": _hashtags(name, category, audience),
            "ai_video_prompt": video_prompt,
            "thumbnail_prompt": thumbnail_prompt,
            "broll_shot_ideas": broll,
            "active_ai_provider": provider,
            "active_ai_model": model_name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        if api_key:
            try:
                prompt = f"""
Create a practical Thai seller content package for VelaFlow Seller Studio.
Return JSON only. Keep Thai creator speech natural, concise, and non-repetitive.

Input:
- Product Name: {name}
- Product Category: {category}
- Target Audience: {audience}
- Raw Selling Points: {raw_points}
- Compressed Benefits: {benefits}
- Tone Style: {tone_style}
- Hook Style: {hook_style}
- Product Image Note: {image_note or "No product image attached"}

JSON keys:
tiktok_hooks, script_15s, script_30s, script_60s, cta_suggestions, caption,
hashtags, ai_video_prompt, thumbnail_prompt, broll_shot_ideas
"""
                text = generate_text(
                    provider=provider,
                    api_key=api_key,
                    prompt=prompt,
                    primary_model=model_name,
                    offline_factory=lambda: json.dumps(package, ensure_ascii=False),
                )
                ai_data = _extract_json(text)
                for key in [
                    "tiktok_hooks",
                    "script_15s",
                    "script_30s",
                    "script_60s",
                    "cta_suggestions",
                    "hashtags",
                    "broll_shot_ideas",
                ]:
                    if key in ai_data:
                        ai_data[key] = [str(item).strip() for item in (ai_data.get(key) or []) if str(item).strip()]
                package.update({key: value for key, value in ai_data.items() if value})
                package["short_video_script"] = package.get("script_30s", [])
                package["final_script"] = {
                    "15s": package.get("script_15s", []),
                    "30s": package.get("script_30s", []),
                    "60s": package.get("script_60s", []),
                }
            except Exception:
                package["provider_fallback_used"] = True
        package = apply_visual_engine_to_package(package, "seller", visual_settings)
        return {"ok": True, "message": "Seller content generated", "data": package, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Seller content generation failed", "data": {}, "error": str(exc)}


def seller_content_to_text(package: Dict[str, Any]) -> str:
    image = package.get("product_image") or {}
    lines = [
        "SELLER CONTENT PACKAGE",
        "",
        f"Product Name: {package.get('product_name', '')}",
        f"Category: {package.get('product_category', '')}",
        f"Target Audience: {package.get('target_audience', '')}",
        f"Tone Style: {package.get('tone_style', '')}",
        f"Hook Style: {package.get('hook_style', '')}",
        f"Product Image: {image.get('path') or 'not attached'}",
        f"Product Image Filename: {image.get('filename') or '-'}",
        f"Image Note: {image.get('note') or '-'}",
        f"Camera Preset: {(package.get('visual_engine') or {}).get('camera_preset', '-')}",
        f"Lighting Preset: {(package.get('visual_engine') or {}).get('lighting_preset', '-')}",
        f"Motion Preset: {(package.get('visual_engine') or {}).get('motion_preset', '-')}",
        f"Visual Mood: {(package.get('visual_engine') or {}).get('visual_mood', '-')}",
        "",
        "====================",
        "RAW SELLING POINTS",
        "====================",
        *[f"- {item}" for item in package.get("raw_selling_points", []) or package.get("key_selling_points", [])],
        "",
        "====================",
        "COMPRESSED BENEFITS",
        "====================",
        *[f"- {item}" for item in package.get("compressed_benefits", [])],
        "",
        "====================",
        "TIKTOK HOOKS",
        "====================",
        *[f"- {item}" for item in package.get("tiktok_hooks", [])],
        "",
        "====================",
        "FINAL SCRIPT",
        "====================",
        "[15s]",
        *[f"{idx}. {item}" for idx, item in enumerate(package.get("script_15s", []) or package.get("short_video_script", []), start=1)],
        "",
        "[30s]",
        *[f"{idx}. {item}" for idx, item in enumerate(package.get("script_30s", []) or package.get("short_video_script", []), start=1)],
        "",
        "[60s]",
        *[f"{idx}. {item}" for idx, item in enumerate(package.get("script_60s", []), start=1)],
        "",
        "====================",
        "CTA",
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
        "VIDEO PROMPT",
        "====================",
        package.get("ai_video_prompt", ""),
        "",
        "====================",
        "THUMBNAIL PROMPT",
        "====================",
        package.get("thumbnail_prompt", ""),
        "",
        "====================",
        "B-ROLL IDEAS",
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


def build_seller_dashboard_status(project: Dict[str, Any]) -> Dict[str, Any]:
    seller = (project.get("seller_studio", {}) or {}).get("content_package", {}) or {}
    export_data = (project.get("seller_studio", {}) or {}).get("export", {}) or {}
    product_name = seller.get("product_name") or "No product selected"
    stages = [
        {"name": "Hooks", "ok": bool(seller.get("tiktok_hooks")), "detail": f"{len(seller.get('tiktok_hooks', []) or [])} hooks"},
        {"name": "Script", "ok": bool(seller.get("script_15s") and seller.get("script_30s") and seller.get("script_60s")), "detail": "15s / 30s / 60s"},
        {"name": "CTA", "ok": bool(seller.get("cta_suggestions")), "detail": f"{len(seller.get('cta_suggestions', []) or [])} options"},
        {"name": "Video Prompt", "ok": bool(seller.get("ai_video_prompt")), "detail": "ready" if seller.get("ai_video_prompt") else "needs seller content"},
        {"name": "Export Package", "ok": bool(export_data.get("txt_path")), "detail": "seller_content_package.txt" if export_data.get("txt_path") else "not exported"},
    ]
    missing = [stage["name"] for stage in stages if not stage["ok"]]
    return {
        "ok": not missing,
        "message": "Seller package ready" if not missing else f"Missing: {', '.join(missing)}",
        "data": {
            "campaign_name": project.get("title") if project.get("title") not in SONG_DEFAULT_TITLES else "New Seller Campaign",
            "product_name": product_name,
            "target_audience": seller.get("target_audience", ""),
            "content_items": sum(len(seller.get(key, []) or []) for key in ["tiktok_hooks", "script_15s", "script_30s", "script_60s", "cta_suggestions", "broll_shot_ideas"]),
            "stages": stages,
            "missing": missing,
        },
        "next_step": {
            "stage": "Seller Content",
            "page": "Seller Studio",
            "label": "Generate seller content" if missing else "Review seller package",
        },
        "error": "",
    }
