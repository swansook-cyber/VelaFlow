from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.affiliate_caption_engine import build_affiliate_caption_package
from core.beat_timing_engine import create_affiliate_retention_timing
from core.file_naming import build_export_filename, ensure_unique_path
from core.paths import workflow_project_root
from core.product_prompt_engine import build_product_scene_prompts
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir


AFFILIATE_MODES = ["TikTok Affiliate", "Seller Product Clip", "Viral Product Hook"]
TRENDING_AFFILIATE_IDEAS = [
    {"category": "Beauty", "idea": "Everyday serum or sunscreen proof", "viral_potential": 88, "easy_to_shoot": 86, "emotional_sell": 82, "before_after_strength": 84, "content_difficulty": "Easy", "recommended_style": "before/after + close-up texture"},
    {"category": "Home", "idea": "Small home item that saves morning time", "viral_potential": 84, "easy_to_shoot": 90, "emotional_sell": 76, "before_after_strength": 80, "content_difficulty": "Easy", "recommended_style": "problem/solution demo"},
    {"category": "Kitchen", "idea": "Kitchen tool that makes food look cleaner", "viral_potential": 82, "easy_to_shoot": 78, "emotional_sell": 70, "before_after_strength": 88, "content_difficulty": "Medium", "recommended_style": "satisfying b-roll"},
    {"category": "Pet", "idea": "Small comfort product for pets", "viral_potential": 86, "easy_to_shoot": 72, "emotional_sell": 90, "before_after_strength": 76, "content_difficulty": "Medium", "recommended_style": "cute reaction + proof"},
    {"category": "Fashion", "idea": "One accessory that changes the whole look", "viral_potential": 80, "easy_to_shoot": 74, "emotional_sell": 75, "before_after_strength": 86, "content_difficulty": "Medium", "recommended_style": "outfit reveal"},
    {"category": "Wellness", "idea": "Low-cost item that makes a routine feel calmer", "viral_potential": 78, "easy_to_shoot": 88, "emotional_sell": 86, "before_after_strength": 68, "content_difficulty": "Easy", "recommended_style": "soft lifestyle review"},
    {"category": "Gadgets", "idea": "Tiny gadget that solves one daily annoyance", "viral_potential": 87, "easy_to_shoot": 82, "emotional_sell": 72, "before_after_strength": 90, "content_difficulty": "Easy", "recommended_style": "quick demo + reaction"},
    {"category": "Organization", "idea": "Messy-to-clean desk or room fix", "viral_potential": 83, "easy_to_shoot": 84, "emotional_sell": 78, "before_after_strength": 92, "content_difficulty": "Easy", "recommended_style": "messy-to-clean reveal"},
]


def _field(product: dict[str, Any], key: str, fallback: str) -> str:
    return str(product.get(key) or fallback).strip()


def normalize_affiliate_product(product: dict[str, Any]) -> dict[str, Any]:
    title = _field(product, "product_name", _field(product, "title", "สินค้านี้"))
    return {
        "product_name": title,
        "product_type": _field(product, "product_type", _field(product, "category", "สินค้าไลฟ์สไตล์")),
        "target_audience": _field(product, "target_audience", "คนที่อยากแก้ปัญหานี้"),
        "emotional_angle": _field(product, "emotional_angle", "ชีวิตง่ายขึ้น"),
        "pain_point": _field(product, "pain_point", "ปัญหาที่เจอบ่อย"),
        "cta_style": _field(product, "cta_style", "soft sell"),
        "description": _field(product, "description", _field(product, "product_description", "")),
        "benefits": _field(product, "benefits", ""),
        "creator_notes": _field(product, "creator_notes", ""),
        "price": _field(product, "price", _field(product, "pricing", "")),
        "rating": _field(product, "rating", ""),
        "category": _field(product, "category", ""),
        "image": _field(product, "image", ""),
        "url": _field(product, "url", ""),
        "platform": _field(product, "platform", "manual"),
    }


def analyze_affiliate_product(product: dict[str, Any]) -> dict[str, Any]:
    product = normalize_affiliate_product(product)
    text = " ".join(str(product.get(key, "")) for key in ["product_name", "product_type", "description", "benefits", "creator_notes", "pain_point", "emotional_angle"]).lower()
    useful_terms = ["clean", "easy", "quick", "portable", "ช่วย", "ง่าย", "ประหยัด", "สบาย", "รีวิว", "แก้"]
    visual_terms = ["beauty", "fashion", "kitchen", "pet", "home", "สี", "ดีไซน์", "แสง", "แต่ง"]
    emotional_terms = ["เหนื่อย", "มั่นใจ", "สบาย", "ชีวิต", "เจ็บ", "เครียด", "รัก", "ดูแล"]
    utility = sum(1 for term in useful_terms if term in text)
    visual = sum(1 for term in visual_terms if term in text)
    emotional = sum(1 for term in emotional_terms if term in text)
    base = min(100, 64 + utility * 5 + visual * 4 + emotional * 5)
    creator_difficulty = max(20, 62 - visual * 5 + (8 if len(product.get("description", "")) < 30 else 0))
    labels = []
    if creator_difficulty <= 52:
        labels.append("Beginner Friendly")
    if base >= 78:
        labels.append("Viral Friendly")
    if creator_difficulty >= 68:
        labels.append("Hard To Shoot")
    if emotional >= 1:
        labels.append("Strong Emotional Sell")
    if visual >= 1 or "before" in text or "after" in text:
        labels.append("Strong Before/After")
    if not labels:
        labels.append("Simple Review Angle")
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "scores": {
            "viral_potential": min(100, base + 5),
            "hook_potential": min(100, base + 8),
            "emotional_sell_strength": min(100, 60 + emotional * 8 + utility * 3),
            "visual_appeal": min(100, 58 + visual * 9 + (6 if product.get("image") else 0)),
            "creator_difficulty": creator_difficulty,
            "tiktok_compatibility": min(100, base + 10),
        },
        "recommended_content_style": "UGC review with close-up proof" if creator_difficulty < 55 else "simple product demo with clear before/after",
        "recommendation_labels": labels,
        "selling_angle": f"{product['product_name']} ช่วยให้{product['emotional_angle']} สำหรับคนที่เจอ{product['pain_point']}",
        "product": product,
    }


def generate_affiliate_hooks(product: dict[str, Any], mode: str = "TikTok Affiliate") -> list[dict[str, Any]]:
    product = normalize_affiliate_product(product)
    name = product["product_name"]
    audience = product["target_audience"]
    pain = product["pain_point"]
    angle = product["emotional_angle"]
    hooks = [
        ("shock", f"I thought {name} was overhyped until it fixed this one thing."),
        ("curiosity", f"Why are people with {pain} starting to use {name}?"),
        ("pain_point", f"If {pain} keeps happening, this is worth checking."),
        ("problem_solution", f"{pain} is easier to handle when {name} fits your routine."),
        ("emotional", f"If you are tired of {pain}, this small fix might make sense."),
        ("social_proof", f"This is the kind of TikTok recommendation that actually feels useful: {name}."),
        ("urgency", f"If you want {angle}, check {name} before you forget."),
        ("pov", f"POV: you deal with {pain} every day, then try {name} once."),
        ("before_after", f"Before vs after using {name}: this is the difference."),
        ("tiktok_opener", f"I did not expect {name} to be this useful."),
    ]
    boosted = 6 if mode == "Viral Product Hook" else 0
    rows: list[dict[str, Any]] = []
    for index, (hook_type, text) in enumerate(hooks):
        rows.append(
            {
                "hook_type": hook_type,
                "hook_text": text,
                "hook_strength": min(100, 78 + index + boosted + (7 if hook_type in {"shock", "curiosity", "tiktok_opener"} else 0)),
                "cta_strength": min(100, 72 + index * 2 + (8 if hook_type in {"urgency", "problem_solution"} else 0)),
                "replay_potential": min(100, 70 + index * 2 + boosted),
                "conversion_pacing": min(100, 74 + index * 2 + (6 if hook_type == "social_proof" else 0)),
                "scroll_stop_score": min(100, 80 + index + boosted + (8 if hook_type == "shock" else 0)),
                "retention_estimate": min(100, 76 + index + boosted),
            }
        )
    return rows


def score_affiliate_package(hooks: list[dict[str, Any]]) -> dict[str, Any]:
    if not hooks:
        return {"hook_strength": 0, "cta_strength": 0, "replay_potential": 0, "conversion_pacing": 0, "scroll_stop_score": 0, "conversion_potential": 0, "retention_estimate": 0, "replay_score": 0, "emotional_pacing": 0, "hook_power": 0, "cta_power": 0, "best_hook": {}}
    best = max(hooks, key=lambda item: int(item.get("scroll_stop_score", 0) or 0))
    return {
        "hook_strength": best.get("hook_strength", 0),
        "cta_strength": best.get("cta_strength", 0),
        "replay_potential": best.get("replay_potential", 0),
        "conversion_pacing": best.get("conversion_pacing", 0),
        "scroll_stop_score": best.get("scroll_stop_score", 0),
        "conversion_potential": round((int(best.get("cta_strength", 0)) + int(best.get("conversion_pacing", 0))) / 2),
        "retention_estimate": best.get("retention_estimate", 0),
        "replay_score": best.get("replay_potential", 0),
        "emotional_pacing": round((int(best.get("hook_strength", 0)) + int(best.get("replay_potential", 0))) / 2),
        "hook_power": best.get("hook_strength", 0),
        "cta_power": best.get("cta_strength", 0),
        "best_hook": best,
    }


def _affiliate_word_count(text: str) -> int:
    parts = [part for part in str(text or "").replace("\n", " ").split(" ") if part.strip()]
    thai_chars = len([ch for ch in str(text or "") if "\u0e00" <= ch <= "\u0e7f"])
    return max(len(parts), thai_chars // 6)


def validate_affiliate_output_quality(brief: dict[str, Any]) -> dict[str, Any]:
    hooks = brief.get("hooks") or []
    scripts = brief.get("scripts") or {}
    captions = (brief.get("caption_package") or {}).get("captions", [])
    prompt = str(brief.get("prompt") or "")
    joined = "\n".join(
        [str(item.get("hook_text", "")) for item in hooks]
        + [str(value or "") for value in scripts.values()]
        + [str(item or "") for item in captions]
        + [prompt]
    ).lower()
    return {
        "hooks_ready": len(hooks) >= 8 and all(_affiliate_word_count(item.get("hook_text", "")) >= 5 for item in hooks[:5]),
        "scripts_ready": all(_affiliate_word_count(scripts.get(key, "")) >= minimum for key, minimum in {"tiktok_script_15s": 24, "tiktok_script_30s": 38, "pov_script": 18, "review_script": 22}.items()),
        "cta_ready": bool((brief.get("caption_package") or {}).get("cta_variants")),
        "scene_plan_ready": len(brief.get("shot_list") or []) >= 4 and "vertical" in prompt.lower(),
        "caption_ready": len(captions) >= 3 and all(_affiliate_word_count(item) >= 6 for item in captions[:2]),
        "no_placeholder_text": not any(token in joined for token in ["placeholder", "lorem", "insert product", "todo"]),
    }


def build_affiliate_scripts(product: dict[str, Any], hooks: list[dict[str, Any]] | None = None) -> dict[str, str]:
    product = normalize_affiliate_product(product)
    top_hook = (hooks or generate_affiliate_hooks(product))[0]["hook_text"]
    name = product["product_name"]
    pain = product["pain_point"]
    cta = "Check the details before you decide" if product["cta_style"] == "soft sell" else "Check the deal while it is still live"
    return {
        "tiktok_script_15s": f"0-3s: {top_hook}\n3-8s: Hold {name} close to camera and show the exact problem: {pain}. Keep the voice casual, like a real creator testing it.\n8-12s: Show one proof moment or before/after detail with hands in frame.\n12-15s: End with one clear CTA: {cta}",
        "tiktok_script_30s": f"0-3s: {top_hook}\n3-10s: Tell the problem in a casual creator voice, then show why {pain} is annoying in daily life.\n10-20s: Demo {name} with hands, close-up b-roll, and one visible result.\n20-26s: Name 2 clear benefits without sounding spammy: {product['emotional_angle']} and a practical daily-use reason.\n26-30s: Close with soft proof and CTA: {cta}",
        "pov_script": f"POV: you are tired of {pain}, then try {name} for the first time.\nShow the small frustration first, then the product reveal, then the moment where it feels easier. Keep it conversational, short, and honest.",
        "review_script": f"Real review: {name}\nOpening: I did not expect this to help with {pain}.\nWhat I like: it helps with {product['emotional_angle']} without needing a complicated setup.\nBest for: {product['target_audience']} who want a practical fix.\nCTA: {cta}",
        "emotional_sell_script": f"If {pain} makes your day harder, {name} is a small helper that can make things feel more manageable.",
        "aesthetic_script": f"Open with a clean close-up of {name}\nCut to lifestyle use\nEnd with a simple hero shot and soft CTA",
    }


def build_affiliate_shot_list(product: dict[str, Any], hooks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    product = normalize_affiliate_product(product)
    top_hook = (hooks or generate_affiliate_hooks(product))[0]["hook_text"]
    shots = [
        {"shot_id": "shot_01", "time": "0:00-0:03", "visual": "product close-up with hand entering frame", "camera": "fast push-in", "purpose": "stop scroll", "hook": top_hook},
        {"shot_id": "shot_02", "time": "0:03-0:08", "visual": f"show the pain point: {product['pain_point']}", "camera": "handheld UGC angle", "purpose": "relatable problem"},
        {"shot_id": "shot_03", "time": "0:08-0:14", "visual": f"demo {product['product_name']} in real use", "camera": "close-up b-roll", "purpose": "proof"},
        {"shot_id": "shot_04", "time": "0:14-0:20", "visual": "before/after or reaction result", "camera": "soft pan to hero shot", "purpose": "conversion moment"},
    ]
    scene_breakdown = "\n\n".join(
        f"{item['shot_id']}\n{item['time']}\nVisual: {item['visual']}\nCamera: {item['camera']}\nPurpose: {item['purpose']}\nHook/CTA: {item['hook'] if item['shot_id'] == 'shot_01' else product['cta_style']}"
        for item in shots
    )
    return {"shot_list": shots, "scene_breakdown": scene_breakdown}


def build_affiliate_clip_brief(product: dict[str, Any], mode: str = "TikTok Affiliate", variation: str = "default") -> dict[str, Any]:
    product = normalize_affiliate_product(product)
    hooks = generate_affiliate_hooks(product, mode)
    if variation == "stronger_hook":
        hooks = [{**hook, "hook_strength": min(100, int(hook.get("hook_strength", 0)) + 8), "scroll_stop_score": min(100, int(hook.get("scroll_stop_score", 0)) + 6)} for hook in hooks]
    if variation == "aggressive_cta":
        product = {**product, "cta_style": "urgent deal"}
        hooks = [{**hook, "cta_strength": min(100, int(hook.get("cta_strength", 0)) + 10)} for hook in hooks]
    analysis = analyze_affiliate_product(product)
    scene_prompt_plan = build_product_scene_prompts(product, mode)
    captions = build_affiliate_caption_package(product, hooks)
    scripts = build_affiliate_scripts(product, hooks)
    shots = build_affiliate_shot_list(product, hooks)
    score = score_affiliate_package(hooks)
    best_hook = score.get("best_hook", hooks[0] if hooks else {})
    timing = create_affiliate_retention_timing(duration=20 if variation != "faster_tiktok" else 15, hook_type=str(best_hook.get("hook_type") or "curiosity"))
    prompt = "\n".join(
        [
            f"Affiliate mode: {mode}",
            f"Product: {product['product_name']}",
            f"Target audience: {product['target_audience']}",
            f"Pain point: {product['pain_point']}",
            f"Best hook: {best_hook.get('hook_text', '')}",
            "Create a creator package for a vertical TikTok affiliate video. No upload automation.",
            *[f"- {item['scene_id']}: {item['prompt']}" for item in scene_prompt_plan.get("scene_prompts", [])],
        ]
    )
    brief = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "variation": variation,
        "product": product,
        "analysis": analysis,
        "hooks": hooks,
        "scene_prompt_plan": scene_prompt_plan,
        "caption_package": captions,
        "scripts": scripts,
        "shot_list": shots["shot_list"],
        "scene_breakdown": shots["scene_breakdown"],
        "viral_score": score,
        "retention_timing": timing,
        "thumbnail_analysis": {},
        "prompt": prompt,
    }
    brief["quality_report"] = validate_affiliate_output_quality(brief)
    return brief


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8-sig")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def export_affiliate_package(project_name: str, brief: dict[str, Any], quick_data: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        quick_data = quick_data or {}
        project_dir = workflow_project_root("seller") / safe_name(project_name or "affiliate_product")
        final_dir = project_dir / "exports" / "affiliate_creator_package"
        if final_dir.exists():
            shutil.rmtree(final_dir)
        final_dir.mkdir(parents=True, exist_ok=True)
        product = normalize_affiliate_product(brief.get("product") or {})
        hooks = brief.get("hooks") or generate_affiliate_hooks(product)
        captions = brief.get("caption_package") or build_affiliate_caption_package(product, hooks)
        scripts = brief.get("scripts") or build_affiliate_scripts(product, hooks)
        shots = {"shot_list": brief.get("shot_list") or [], "scene_breakdown": brief.get("scene_breakdown") or ""}
        if not shots["shot_list"]:
            shots = build_affiliate_shot_list(product, hooks)
        analysis = brief.get("analysis") or analyze_affiliate_product(product)
        score = brief.get("viral_score") or score_affiliate_package(hooks)
        thumbnail_prompt = (
            f"TikTok affiliate thumbnail, single product hero shot of {product['product_name']}, "
            f"clear emotional benefit, warm creator lighting, no fake price text, mobile readable composition"
        )
        files = {
            "analysis/product_summary.txt": f"Product: {product['product_name']}\nType: {product['product_type']}\nAudience: {product['target_audience']}\nPain point: {product['pain_point']}\nAngle: {product['emotional_angle']}\nPrice: {product.get('price', '')}\nRating: {product.get('rating', '')}\nURL: {product.get('url', '')}\n",
        "analysis/viral_analysis.txt": f"Recommended style: {analysis.get('recommended_content_style')}\nLabels: {', '.join(analysis.get('recommendation_labels', []))}\nSelling angle: {analysis.get('selling_angle')}\nScores: {json.dumps(analysis.get('scores', {}), ensure_ascii=False)}\n",
            "hooks/viral_hooks.txt": "\n".join(item["hook_text"] for item in hooks),
            "hooks/emotional_hooks.txt": "\n".join(item["hook_text"] for item in hooks if item["hook_type"] in {"emotional", "pov", "before_after"}),
            "hooks/curiosity_hooks.txt": "\n".join(item["hook_text"] for item in hooks if item["hook_type"] in {"curiosity", "shock", "tiktok_opener"}),
            "scripts/tiktok_script_15s.txt": scripts["tiktok_script_15s"],
            "scripts/tiktok_script_30s.txt": scripts["tiktok_script_30s"],
            "scripts/pov_script.txt": scripts["pov_script"],
            "scripts/review_script.txt": scripts["review_script"],
            "captions/captions.txt": "\n\n".join(captions.get("captions", [])),
            "captions/hashtags.txt": " ".join(captions.get("hashtags", [])),
            "captions/cta_variants.txt": "\n".join(captions.get("cta_variants", [])),
            "creator/captions.txt": "\n\n".join(captions.get("captions", [])),
            "creator/hashtags.txt": " ".join(captions.get("hashtags", [])),
            "creator/scene_breakdown.txt": shots["scene_breakdown"],
            "creator/thumbnail_prompt.txt": thumbnail_prompt,
            "creator/creator_tips.txt": "Show real hands using the product.\nOpen with the pain point or result in the first 2 seconds.\nAvoid hard-selling in every line.\nEnd with one clear CTA.\n",
            "README_START_HERE.txt": "VelaFlow Affiliate Creator Package\n\n1. Open hooks/viral_hooks.txt and choose one opening line.\n2. Use creator/scene_breakdown.txt and creator/shot_list.json to film or generate the video.\n3. Copy captions/captions.txt and captions/hashtags.txt for your post.\n4. Use creator/thumbnail_prompt.txt if you need a cover image.\n5. Upload manually to TikTok, Reels, or Shorts. VelaFlow does not automate posting.\n",
        }
        for filename, content in files.items():
            _write_text(final_dir / filename, content)
        _write_json(final_dir / "analysis/hook_scores.json", hooks)
        _write_json(final_dir / "creator/shot_list.json", shots["shot_list"])
        manifest = {
            "package_version": "affiliate_mvp_1",
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "mode": brief.get("mode", "TikTok Affiliate"),
            "product_name": product["product_name"],
            "platform": product.get("platform", "manual"),
            "generated_files": sorted(files.keys()) + ["analysis/hook_scores.json", "creator/shot_list.json", "manifest/affiliate_package_manifest.json"],
            "target_platforms": ["TikTok", "Reels", "Shorts"],
            "scores": analysis.get("scores", {}),
            "best_hook": score.get("best_hook", {}),
            "quality_report": brief.get("quality_report") or validate_affiliate_output_quality(brief),
            "automation_policy": "No posting automation, no account automation, no browser botting.",
            "export_status": "complete",
        }
        _write_json(final_dir / "manifest/affiliate_package_manifest.json", manifest)
        if quick_data.get("final_mp4"):
            src = Path(str(quick_data.get("final_mp4")))
            if src.is_file():
                shutil.copy2(src, ensure_parent_dir(final_dir / "final_hook_clip.mp4"))
        zip_path = ensure_parent_dir(ensure_unique_path(project_dir / "exports" / build_export_filename(product["product_name"] or project_name, "VelaFlow", "Affiliate_Package", "zip")))
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in final_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(final_dir).as_posix())
        return {
            "ok": True,
            "message": "Affiliate creator package exported",
            "data": {
                "final_dir": str(final_dir),
                "zip_path": str(zip_path),
                "manifest": manifest,
                "caption_package": captions,
                "viral_score": score,
                "product_analysis": analysis,
                "thumbnail_prompt": thumbnail_prompt,
            },
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "Affiliate package export failed", "data": {}, "error": str(exc)}
