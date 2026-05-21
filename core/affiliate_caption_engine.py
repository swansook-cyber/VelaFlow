from __future__ import annotations

from datetime import datetime
from typing import Any


def _field(product: dict[str, Any], key: str, fallback: str) -> str:
    return str(product.get(key) or fallback).strip()


def _hashtag(text: str) -> str:
    cleaned = "".join(ch for ch in str(text or "") if ch.isalnum() or ch in {"_", " "}).strip().replace(" ", "")
    return f"#{cleaned}" if cleaned else ""


def build_affiliate_caption_package(product: dict[str, Any], hooks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    name = _field(product, "product_name", "สินค้านี้")
    product_type = _field(product, "product_type", "ของใช้ดี")
    audience = _field(product, "target_audience", "คนที่อยากแก้ปัญหานี้")
    pain = _field(product, "pain_point", "ปัญหาที่เจอบ่อย")
    cta_style = _field(product, "cta_style", "soft sell")
    top_hook = (hooks or [{}])[0].get("hook_text") if hooks else f"ใครเจอ{pain} ต้องดู"
    captions = [
        f"{top_hook} ลองดู {name} แล้วจะเข้าใจว่าทำไมคนเริ่มพูดถึง",
        f"ถ้า{pain}กวนใจ นี่คือไอเท็มที่อยากให้ลองสักครั้ง",
        f"{name} เหมาะกับ{audience}ที่อยากได้ตัวช่วยแบบง่ายๆ",
    ]
    ctas = [
        "ลองดูรายละเอียดก่อนตัดสินใจ",
        "เช็กรีวิวเต็มแล้วค่อยเลือกก็ได้",
        "กดดูในตะกร้าไว้ก่อน เผื่ออยากกลับมาเทียบ",
    ]
    if "hard" in cta_style.lower() or "urgent" in cta_style.lower():
        ctas = ["เช็กโปรตอนนี้", "ของหมดแล้วต้องรอรอบหน้า", "รีบดูโปรก่อนเปลี่ยนราคา"]
    cta_variants = {
        "soft_cta": "ลองดูรายละเอียดก่อน ถ้าใช่ค่อยตัดสินใจ",
        "hard_cta": "กดดูโปรตอนนี้ ก่อนราคาเปลี่ยน",
        "comment_bait_cta": "คอมเมนต์มาว่าอยากให้เทียบกับตัวไหน",
        "fomo_cta": "เห็นคนใช้เยอะขึ้นเรื่อยๆ อย่ารอจนของหมด",
        "urgency_cta": "เช็กโปรวันนี้ก่อนหมดรอบ",
        "curiosity_cta": "ลองดูรีวิวเต็ม แล้วจะเข้าใจว่าทำไมคนพูดถึง",
    }
    hashtags = [
        "#TikTokAffiliate",
        "#ของดีบอกต่อ",
        "#รีวิวสินค้า",
        "#ป้ายยา",
        "#ของใช้ดี",
        _hashtag(name),
        _hashtag(product_type),
    ]
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "captions": captions,
        "cta_variants": ctas,
        "cta_optimization": cta_variants,
        "hashtags": [tag for tag in hashtags if tag],
        "short_product_description": f"{name} สำหรับ{audience}ที่เจอ{pain} เล่าแบบ creator-friendly และเข้าใจง่าย",
        "comment_bait": [
            "ใครเคยเจอแบบนี้บ้าง?",
            "อยากให้ลองเทียบกับตัวไหนดี?",
            "ใช้จริงแล้วอยากให้รีวิวมุมไหนต่อ?",
        ],
        "engagement_bait": [
            "เซฟไว้ก่อน เผื่อกลับมาดู",
            "ส่งให้คนที่กำลังหาของแบบนี้",
        ],
    }
