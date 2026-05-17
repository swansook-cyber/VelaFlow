from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from core.affiliate_caption_engine import build_affiliate_caption_package
from core.paths import workflow_project_root
from core.product_prompt_engine import build_product_scene_prompts
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir


AFFILIATE_MODES = ["TikTok Affiliate", "Seller Product Clip", "Viral Product Hook"]


def generate_affiliate_hooks(product: dict[str, Any], mode: str = "TikTok Affiliate") -> list[dict[str, Any]]:
    name = str(product.get("product_name") or "สินค้านี้").strip()
    audience = str(product.get("target_audience") or "คนที่เจอปัญหานี้").strip()
    pain = str(product.get("pain_point") or "ปัญหานี้").strip()
    angle = str(product.get("emotional_angle") or "ชีวิตง่ายขึ้น").strip()
    hooks = [
        ("curiosity", f"ทำไมคนที่{pain}ถึงเริ่มใช้ {name}?"),
        ("pain_point", f"ถ้า{pain}อยู่ทุกวัน คลิปนี้ช่วยได้"),
        ("before_after", f"ก่อนมี {name} กับหลังใช้ ต่างกันชัดมาก"),
        ("emotional", f"{audience}ที่เหนื่อยกับ{pain} น่าจะเข้าใจสิ่งนี้"),
        ("fast_tiktok", f"หยุดก่อน ถ้าอยากให้{angle}"),
    ]
    boosted = 6 if mode == "Viral Product Hook" else 0
    return [
        {
            "hook_type": hook_type,
            "hook_text": text,
            "hook_strength": min(100, 78 + index * 3 + boosted),
            "cta_strength": min(100, 72 + index * 4),
            "replay_potential": min(100, 70 + index * 5 + boosted),
            "conversion_pacing": min(100, 74 + index * 3),
            "scroll_stop_score": min(100, 80 + index * 2 + boosted),
        }
        for index, (hook_type, text) in enumerate(hooks)
    ]


def score_affiliate_package(hooks: list[dict[str, Any]]) -> dict[str, Any]:
    if not hooks:
        return {"hook_strength": 0, "cta_strength": 0, "replay_potential": 0, "conversion_pacing": 0, "scroll_stop_score": 0}
    best = max(hooks, key=lambda item: int(item.get("scroll_stop_score", 0) or 0))
    return {
        "hook_strength": best.get("hook_strength", 0),
        "cta_strength": best.get("cta_strength", 0),
        "replay_potential": best.get("replay_potential", 0),
        "conversion_pacing": best.get("conversion_pacing", 0),
        "scroll_stop_score": best.get("scroll_stop_score", 0),
        "best_hook": best,
    }


def build_affiliate_clip_brief(product: dict[str, Any], mode: str = "TikTok Affiliate") -> dict[str, Any]:
    hooks = generate_affiliate_hooks(product, mode)
    scene_prompt_plan = build_product_scene_prompts(product, mode)
    captions = build_affiliate_caption_package(product, hooks)
    score = score_affiliate_package(hooks)
    best_hook = score.get("best_hook", hooks[0] if hooks else {})
    product_name = str(product.get("product_name") or "the product").strip()
    prompt = "\n".join(
        [
            f"Affiliate mode: {mode}",
            f"Product: {product_name}",
            f"Product type: {product.get('product_type', '')}",
            f"Target audience: {product.get('target_audience', '')}",
            f"Pain point: {product.get('pain_point', '')}",
            f"Emotional angle: {product.get('emotional_angle', '')}",
            f"CTA style: {product.get('cta_style', '')}",
            f"Best hook: {best_hook.get('hook_text', '')}",
            "Create a 3-scene vertical TikTok affiliate clip with UGC product energy, product close-ups, lifestyle proof, and clear CTA.",
            "Scene visual guidance:",
            *[f"- {item['scene_id']}: {item['prompt']}" for item in scene_prompt_plan.get("scene_prompts", [])],
        ]
    )
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "product": product,
        "hooks": hooks,
        "scene_prompt_plan": scene_prompt_plan,
        "caption_package": captions,
        "viral_score": score,
        "prompt": prompt,
    }


def export_affiliate_package(project_name: str, brief: dict[str, Any], quick_data: dict[str, Any]) -> dict[str, Any]:
    try:
        project_dir = workflow_project_root("clips") / safe_name(project_name or "affiliate_clip")
        final_dir = project_dir / "exports" / "affiliate_final"
        final_dir.mkdir(parents=True, exist_ok=True)
        tiktok_final_dir = Path(str((quick_data.get("tiktok_package") or {}).get("final_dir") or ""))
        if tiktok_final_dir.exists():
            for path in tiktok_final_dir.iterdir():
                if path.is_file():
                    shutil.copy2(path, ensure_parent_dir(final_dir / path.name))
        caption_package = brief.get("caption_package") or {}
        files = {
            "affiliate_hooks.json": brief.get("hooks", []),
            "affiliate_scene_prompts.json": brief.get("scene_prompt_plan", {}),
            "affiliate_score.json": brief.get("viral_score", {}),
            "affiliate_brief.json": brief,
        }
        for filename, payload in files.items():
            (final_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (final_dir / "captions.txt").write_text("\n\n".join(caption_package.get("captions", [])), encoding="utf-8-sig")
        (final_dir / "hashtags.txt").write_text(" ".join(caption_package.get("hashtags", [])), encoding="utf-8-sig")
        (final_dir / "cta_text.txt").write_text("\n".join(caption_package.get("cta_variants", [])), encoding="utf-8-sig")
        manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "final_dir": str(final_dir),
            "final_mp4": str(final_dir / "final_hook_clip.mp4"),
            "viral_score": brief.get("viral_score", {}),
        }
        (final_dir / "affiliate_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "Affiliate package exported", "data": {**manifest, "caption_package": caption_package}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Affiliate package export failed", "data": {}, "error": str(exc)}
