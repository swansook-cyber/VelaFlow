from __future__ import annotations

from datetime import datetime
from typing import Any


PRODUCT_PROMPT_STYLES = {
    "TikTok Affiliate": "TikTok UGC style, handheld creator framing, quick product reveal",
    "Seller Product Clip": "clean product showcase, close-up detail, lifestyle context",
    "Viral Product Hook": "fast scroll-stopping opening, bold product close-up, energetic composition",
}


def build_product_scene_prompts(product: dict[str, Any], mode: str = "TikTok Affiliate") -> dict[str, Any]:
    name = str(product.get("product_name") or "the product").strip()
    product_type = str(product.get("product_type") or "lifestyle product").strip()
    audience = str(product.get("target_audience") or "everyday creators").strip()
    pain_point = str(product.get("pain_point") or "daily frustration").strip()
    angle = str(product.get("emotional_angle") or "simple useful solution").strip()
    style = PRODUCT_PROMPT_STYLES.get(mode, PRODUCT_PROMPT_STYLES["TikTok Affiliate"])
    base = (
        f"{style}, vertical 9:16 cinematic product video frame, {name}, {product_type}, "
        f"for {audience}, warm lighting, motion-friendly composition, realistic Thai creator content"
    )
    scenes = [
        {
            "scene_id": "scene_01",
            "title": "Problem Hook",
            "prompt": f"{base}, hand interaction with the product, packaging reveal, product close-up beside a relatable problem: {pain_point}, creator desk setup, strong foreground subject, clean background, scroll-stopping first frame",
            "purpose": "stop scroll with pain point",
        },
        {
            "scene_id": "scene_02",
            "title": "Product Proof",
            "prompt": f"{base}, before/after lifestyle usage, hands showing product benefit, creator reaction shot, practical demo, soft warm light, motion-friendly close-up",
            "purpose": "show product value",
        },
        {
            "scene_id": "scene_03",
            "title": "CTA Moment",
            "prompt": f"{base}, satisfying product hero shot, emotional reaction, lifestyle usage result, {angle}, mobile-safe framing, space for Thai subtitles, clear CTA composition, upbeat ending",
            "purpose": "push CTA and replay",
        },
    ]
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "product_name": name,
        "scene_prompts": scenes,
    }
