from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse


SUPPORTED_PRODUCT_DOMAINS = {
    "shopee": ["shopee.co.th", "shopee.com"],
    "tiktok_shop": ["tiktok.com", "shop.tiktok.com"],
}


def detect_product_platform(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    host = parsed.netloc.lower()
    for platform, domains in SUPPORTED_PRODUCT_DOMAINS.items():
        if any(domain in host for domain in domains):
            return platform
    return "unknown"


def analyze_product_link(url: str, notes: str = "") -> dict[str, Any]:
    cleaned = str(url or "").strip()
    platform = detect_product_platform(cleaned)
    parsed = urlparse(cleaned)
    slug = re.sub(r"[-_]+", " ", PathLikeName(parsed.path)).strip()
    title_guess = slug[:80] if slug else "Product from link"
    keywords = [word for word in re.split(r"\s+", title_guess) if len(word) > 2][:8]
    if notes:
        keywords += [word.strip(" ,") for word in re.split(r"[\n,;]+", notes) if word.strip(" ,")][:8]
    return {
        "ok": bool(cleaned),
        "message": "Product link analyzed locally. No scraping or browser automation was performed.",
        "data": {
            "url": cleaned,
            "platform": platform,
            "title": title_guess,
            "images": [],
            "description": notes,
            "category": "seller product" if platform != "unknown" else "unknown",
            "pricing": "",
            "keywords": list(dict.fromkeys(keywords))[:12],
            "pain_points": ["ไม่แน่ใจว่าคุ้มไหม", "อยากเห็นการใช้งานจริง", "อยากรู้จุดเด่นแบบสั้น ๆ"],
            "target_audience": "TikTok/Reels shoppers",
            "cta_direction": "soft creator-style CTA",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
        "error": "",
    }


def PathLikeName(path: str) -> str:
    value = str(path or "").strip("/").split("/")[-1]
    value = re.sub(r"\.[a-zA-Z0-9]{2,5}$", "", value)
    value = re.sub(r"[^0-9A-Za-zก-๙._-]+", " ", value)
    return value
