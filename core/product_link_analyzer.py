from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urlparse

import requests

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


SUPPORTED_PRODUCT_DOMAINS = {
    "shopee": ["shopee.co.th", "shopee.com", "shopee.ph", "shopee.sg"],
    "tiktok_shop": ["shop.tiktok.com", "tiktok.com"],
    "lazada": ["lazada.co.th", "lazada.com", "lazada.sg", "lazada.ph"],
    "amazon": ["amazon.com", "amazon.co.jp", "amazon.co.uk"],
}


def detect_product_platform(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    host = parsed.netloc.lower()
    for platform, domains in SUPPORTED_PRODUCT_DOMAINS.items():
        if any(domain in host for domain in domains):
            return platform
    return "unknown"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _slug_title(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    path_bits = [unquote(bit) for bit in parsed.path.split("/") if bit.strip()]
    guess = path_bits[-1] if path_bits else parsed.netloc
    guess = re.sub(r"\.[a-zA-Z0-9]{2,5}$", "", guess)
    guess = re.sub(r"[-_+]+", " ", guess)
    guess = re.sub(r"[^0-9A-Za-zก-๙ ]+", " ", guess)
    return _clean_text(guess)[:120] or "Product from link"


def _extract_meta(html: str) -> dict[str, Any]:
    if BeautifulSoup is None:
        def raw_meta(*keys: str) -> str:
            for key in keys:
                patterns = [
                    rf'<meta[^>]+(?:property|name)=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
                    rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(key)}["\']',
                ]
                for pattern in patterns:
                    match = re.search(pattern, html or "", flags=re.IGNORECASE)
                    if match:
                        return _clean_text(match.group(1))
            return ""

        title_match = re.search(r"<title[^>]*>(.*?)</title>", html or "", flags=re.IGNORECASE | re.DOTALL)
        return {
            "title": raw_meta("og:title", "twitter:title") or (_clean_text(title_match.group(1)) if title_match else ""),
            "description": raw_meta("og:description", "description", "twitter:description"),
            "image": raw_meta("og:image", "twitter:image"),
            "price": raw_meta("product:price:amount", "og:price:amount", "twitter:data1"),
            "rating": raw_meta("product:rating:value", "rating"),
            "category": raw_meta("product:category", "article:section"),
        }

    soup = BeautifulSoup(html or "", "html.parser")

    def meta_value(*keys: str) -> str:
        for key in keys:
            tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
            if tag and tag.get("content"):
                return _clean_text(str(tag.get("content")))
        return ""

    title = meta_value("og:title", "twitter:title")
    if not title and soup.title and soup.title.text:
        title = _clean_text(soup.title.text)
    description = meta_value("og:description", "description", "twitter:description")
    image = meta_value("og:image", "twitter:image")
    price = meta_value("product:price:amount", "og:price:amount", "twitter:data1")
    category = meta_value("product:category", "article:section")
    rating = meta_value("product:rating:value", "rating")
    return {
        "title": title,
        "description": description,
        "image": image,
        "price": price,
        "rating": rating,
        "category": category,
    }


def _keywords(*values: str) -> list[str]:
    joined = " ".join(_clean_text(value) for value in values if value)
    words = re.split(r"[\s,;|/]+", joined)
    blocked = {"the", "and", "for", "with", "product", "shop", "buy"}
    keywords = []
    for word in words:
        cleaned = word.strip(" .,:;!?()[]{}\"'")
        if len(cleaned) < 3 or cleaned.lower() in blocked:
            continue
        keywords.append(cleaned)
    return list(dict.fromkeys(keywords))[:14]


def analyze_product_link(url: str, notes: str = "", *, timeout_seconds: float = 5.0, fetch: bool = True, retry_count: int = 1) -> dict[str, Any]:
    cleaned = str(url or "").strip()
    platform = detect_product_platform(cleaned)
    parsed = urlparse(cleaned)
    valid_url = bool(parsed.scheme in {"http", "https"} and parsed.netloc)
    extraction_status = "manual_fallback"
    fetch_error = ""
    meta: dict[str, Any] = {}
    if cleaned and not valid_url:
        extraction_status = "invalid_url"
        fetch_error = "Invalid URL. Paste a full product link starting with https://"
    elif cleaned and platform == "unknown":
        extraction_status = "unsupported_domain"
        fetch_error = "Unsupported domain. Use manual product details instead."
    elif cleaned and fetch:
        attempts = max(1, int(retry_count or 1) + 1)
        for attempt in range(attempts):
            try:
                response = requests.get(
                    cleaned,
                    timeout=timeout_seconds,
                    headers={
                        "User-Agent": "VelaFlow/1.0 creator metadata preview",
                        "Accept": "text/html,application/xhtml+xml",
                    },
                    allow_redirects=True,
                )
                response.raise_for_status()
                meta = _extract_meta(response.text)
                extraction_status = "metadata_extracted" if any(meta.values()) else "metadata_empty"
                fetch_error = "" if any(meta.values()) else "No public metadata found on this product page."
                break
            except Exception as exc:
                fetch_error = f"{type(exc).__name__}: {_clean_text(str(exc))[:180]}"
                extraction_status = "metadata_unavailable"
                if attempt + 1 >= attempts:
                    break

    title = meta.get("title") or _slug_title(cleaned)
    description = meta.get("description") or _clean_text(notes)
    category = meta.get("category") or ("affiliate product" if platform != "unknown" else "manual product")
    price = meta.get("price") or ""
    rating = meta.get("rating") or ""
    image = meta.get("image") or ""
    return {
        "ok": bool(cleaned),
        "message": "Product metadata checked. Manual fallback is available." if cleaned else "Paste a product URL or enter product details manually.",
        "data": {
            "url": cleaned,
            "platform": platform,
            "valid_url": valid_url,
            "supported_domain": platform != "unknown",
            "title": title,
            "product_title": title,
            "description": description,
            "product_description": description,
            "image": image,
            "images": [image] if image else [],
            "price": price,
            "pricing": price,
            "rating": rating,
            "category": category,
            "keywords": _keywords(title, description, notes),
            "target_audience": "TikTok shoppers",
            "pain_points": ["ลังเลว่าคุ้มไหม", "อยากเห็นการใช้งานจริง", "อยากรู้จุดเด่นแบบสั้นๆ"],
            "cta_direction": "creator-style soft CTA",
            "extraction_status": extraction_status,
            "fetch_error": fetch_error,
            "manual_fallback_message": "Could not extract product automatically. Paste product title and description manually." if fetch_error or extraction_status != "metadata_extracted" else "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
        "error": fetch_error,
    }
