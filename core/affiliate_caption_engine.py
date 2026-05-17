from __future__ import annotations

from datetime import datetime
from typing import Any


def _hashtag(text: str) -> str:
    cleaned = "".join(ch for ch in str(text or "") if ch.isalnum() or ch in {"_", " "}).strip().replace(" ", "")
    return f"#{cleaned}" if cleaned else ""


def build_affiliate_caption_package(product: dict[str, Any], hooks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    name = str(product.get("product_name") or "สินค้านี้").strip()
    product_type = str(product.get("product_type") or "ของใช้ดี").strip()
    audience = str(product.get("target_audience") or "คนที่อยากแก้ปัญหานี้").strip()
    pain = str(product.get("pain_point") or "ปัญหาที่เจอบ่อย").strip()
    cta_style = str(product.get("cta_style") or "soft sell").strip()
    top_hook = (hooks or [{}])[0].get("hook_text") if hooks else f"ใครเจอ{pain} ต้องดู"
    captions = [
        f"{top_hook} ลองดู {name} แล้วจะเข้าใจว่าทำไมคนพูดถึงเยอะ",
        f"ถ้า{pain}กวนใจ นี่คือไอเท็มที่อยากให้ลองสักครั้ง",
        f"{name} เหมาะกับ{audience}ที่อยากได้ตัวช่วยแบบง่าย ๆ",
    ]
    ctas = [
        "ดูรายละเอียดก่อนของหมด",
        "กดดูโปรในตะกร้า",
        "ลองเช็กรีวิวแล้วค่อยตัดสินใจ",
    ]
    if "hard" in cta_style.lower() or "urgent" in cta_style.lower():
        ctas = ["กดดูโปรตอนนี้", "ของหมดแล้วต้องรอรอบหน้า", "รีบเช็กก่อนโปรหาย"]
    hashtags = [
        "#TikTokAffiliate",
        "#ของดีบอกต่อ",
        "#รีวิวสินค้า",
        "#ป้ายยา",
        "#ของใช้ดี",
        _hashtag(name),
        _hashtag(product_type),
    ]
    hashtags = [tag for tag in hashtags if tag]
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "captions": captions,
        "cta_variants": ctas,
        "hashtags": hashtags,
        "short_product_description": f"{name} สำหรับ{audience}ที่เจอ{pain} ใช้เล่าแบบ creator-friendly และเข้าใจง่าย",
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
