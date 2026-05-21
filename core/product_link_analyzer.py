from __future__ import annotations

import re
import json
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urlparse

import requests

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


SUPPORTED_PRODUCT_DOMAINS = {
    "shopee": ["shopee.co.th", "shopee.com", "shopee.ph", "shopee.sg", "s.shopee.co.th"],
    "tiktok_shop": ["shop.tiktok.com", "tiktok.com", "vt.tiktok.com"],
    "lazada": ["lazada.co.th", "lazada.com", "lazada.sg", "lazada.ph"],
    "amazon": ["amazon.com", "amazon.co.jp", "amazon.co.uk"],
}
SHORT_LINK_DOMAINS = ["s.shopee.co.th", "vt.tiktok.com", "tinyurl.com", "bit.ly", "cutt.ly", "shorturl.at", "t.co"]


def detect_product_platform(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    host = parsed.netloc.lower()
    for platform, domains in SUPPORTED_PRODUCT_DOMAINS.items():
        if any(domain in host for domain in domains):
            return platform
    return "unknown"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _request_headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def _is_short_link(url: str) -> bool:
    host = urlparse(str(url or "").strip()).netloc.lower()
    return any(domain in host for domain in SHORT_LINK_DOMAINS)


def _slug_title(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    path_bits = [unquote(bit) for bit in parsed.path.split("/") if bit.strip()]
    guess = path_bits[-1] if path_bits else parsed.netloc
    guess = re.sub(r"\.[a-zA-Z0-9]{2,5}$", "", guess)
    guess = re.sub(r"[-_+]+", " ", guess)
    guess = re.sub(r"[^0-9A-Za-zก-๙ ]+", " ", guess)
    return _clean_text(guess)[:120] or "Product from link"


def _json_ld_values(html: str) -> dict[str, str]:
    values = {"title": "", "description": "", "image": "", "price": "", "rating": "", "category": ""}
    blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html or "", flags=re.IGNORECASE | re.DOTALL)
    for block in blocks:
        try:
            payload = json.loads(block.strip())
        except Exception:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if isinstance(item, dict) and "@graph" in item and isinstance(item["@graph"], list):
                candidates.extend(item["@graph"])
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            if isinstance(item_type, list):
                item_type = " ".join(str(value) for value in item_type)
            if "Product" not in str(item_type) and not any(key in item for key in ["offers", "aggregateRating", "brand"]):
                continue
            values["title"] = values["title"] or _clean_text(str(item.get("name", "")))
            values["description"] = values["description"] or _clean_text(str(item.get("description", "")))
            image = item.get("image", "")
            if isinstance(image, list):
                image = image[0] if image else ""
            values["image"] = values["image"] or _clean_text(str(image))
            values["category"] = values["category"] or _clean_text(str(item.get("category", "")))
            offers = item.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if isinstance(offers, dict):
                values["price"] = values["price"] or _clean_text(str(offers.get("price") or offers.get("lowPrice") or ""))
            rating = item.get("aggregateRating", {})
            if isinstance(rating, dict):
                values["rating"] = values["rating"] or _clean_text(str(rating.get("ratingValue", "")))
    return values


def _extract_meta(html: str) -> dict[str, Any]:
    sources = {key: "" for key in ["title", "description", "image", "price", "rating", "category"]}
    json_ld = _json_ld_values(html)
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
        extracted = {
            "title": raw_meta("og:title", "twitter:title") or (_clean_text(title_match.group(1)) if title_match else ""),
            "description": raw_meta("og:description", "description", "twitter:description"),
            "image": raw_meta("og:image", "twitter:image"),
            "price": raw_meta("product:price:amount", "og:price:amount", "twitter:data1"),
            "rating": raw_meta("product:rating:value", "rating"),
            "category": raw_meta("product:category", "article:section"),
        }
        for key, value in list(extracted.items()):
            if value:
                sources[key] = "meta_or_title"
            elif json_ld.get(key):
                extracted[key] = json_ld[key]
                sources[key] = "json_ld"
        extracted["sources"] = sources
        return extracted

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
    extracted = {
        "title": title,
        "description": description,
        "image": image,
        "price": price,
        "rating": rating,
        "category": category,
    }
    for key, value in list(extracted.items()):
        if value:
            sources[key] = "opengraph_twitter_or_title"
        elif json_ld.get(key):
            extracted[key] = json_ld[key]
            sources[key] = "json_ld"
    extracted["sources"] = sources
    return extracted


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
    parsed = urlparse(cleaned)
    valid_url = bool(parsed.scheme in {"http", "https"} and parsed.netloc)
    platform = detect_product_platform(cleaned)
    extraction_status = "manual_fallback"
    fetch_error = ""
    meta: dict[str, Any] = {}
    resolved_url = cleaned
    response_status = 0
    if cleaned and not valid_url:
        extraction_status = "invalid_url"
        fetch_error = "Invalid URL. Paste a full product link starting with https://"
    elif cleaned and platform == "unknown" and not _is_short_link(cleaned):
        extraction_status = "unsupported_domain"
        fetch_error = "Unsupported domain. Use manual product details instead."
    elif cleaned and fetch:
        attempts = max(1, int(retry_count or 1) + 1)
        for attempt in range(attempts):
            try:
                response = requests.get(
                    cleaned,
                    timeout=timeout_seconds,
                    headers=_request_headers(),
                    allow_redirects=True,
                )
                response_status = int(getattr(response, "status_code", 0) or 0)
                resolved_url = str(getattr(response, "url", "") or cleaned)
                platform = detect_product_platform(resolved_url) if detect_product_platform(resolved_url) != "unknown" else platform
                response.raise_for_status()
                meta = _extract_meta(response.text)
                field_values = {key: value for key, value in meta.items() if key != "sources"}
                found_count = sum(1 for value in field_values.values() if value)
                extraction_status = "metadata_extracted" if found_count >= 2 else "partial_metadata" if found_count == 1 else "metadata_empty"
                fetch_error = "" if found_count else "No public metadata found on this product page."
                break
            except Exception as exc:
                fetch_error = f"{type(exc).__name__}: {_clean_text(str(exc))[:180]}"
                extraction_status = "metadata_unavailable"
                if attempt + 1 >= attempts:
                    break

    extracted_title = _clean_text(str(meta.get("title") or ""))
    extracted_description = _clean_text(str(meta.get("description") or ""))
    extracted_image = _clean_text(str(meta.get("image") or ""))
    extracted_success = bool(extracted_title or extracted_description or extracted_image)
    title = extracted_title
    description = extracted_description or _clean_text(notes)
    category = meta.get("category") or ("affiliate product" if platform != "unknown" else "manual product")
    price = meta.get("price") or ""
    rating = meta.get("rating") or ""
    image = extracted_image
    failure_reason = ""
    if cleaned and not extracted_success:
        failure_reason = fetch_error or "empty_metadata"
    return {
        "ok": bool(cleaned),
        "message": "Product metadata extracted." if extracted_success else "Automatic extraction unavailable. Please enter product details manually.",
        "data": {
            "url": cleaned,
            "original_url": cleaned,
            "resolved_url": resolved_url,
            "platform": platform,
            "valid_url": valid_url,
            "supported_domain": platform != "unknown",
            "extracted_success": extracted_success,
            "extracted_title_exists": bool(extracted_title),
            "extracted_description_exists": bool(extracted_description),
            "extracted_image_exists": bool(extracted_image),
            "title": title,
            "product_title": title,
            "fallback_title_guess": _slug_title(resolved_url or cleaned) if cleaned else "",
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
            "extraction_source": meta.get("sources", {}),
            "response_status": response_status,
            "missing_fields": [key for key, value in {"title": title, "description": description, "image": image, "price": price, "category": category}.items() if not value],
            "failure_reason": failure_reason,
            "fetch_error": fetch_error,
            "manual_fallback_message": "ไม่สามารถดึงข้อมูลจากลิงก์นี้ได้ กรุณาวางชื่อสินค้า/รายละเอียดสินค้าเอง" if not extracted_success else "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
        "error": fetch_error,
    }
