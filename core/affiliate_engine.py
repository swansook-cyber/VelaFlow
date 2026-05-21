from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.affiliate_caption_engine import build_affiliate_caption_package
from core.beat_timing_engine import create_affiliate_retention_timing
from core.paths import workflow_project_root
from core.product_prompt_engine import build_product_scene_prompts
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir


AFFILIATE_MODES = ["TikTok Affiliate", "Seller Product Clip", "Viral Product Hook"]
TRENDING_AFFILIATE_IDEAS = [
    {"category": "Beauty", "idea": "กันแดด/เซรั่มที่เห็นผลในชีวิตประจำวัน", "viral_potential": 88, "content_difficulty": "Easy", "recommended_style": "before/after + close-up texture"},
    {"category": "Home gadgets", "idea": "ของช่วยประหยัดเวลาตอนเช้า", "viral_potential": 84, "content_difficulty": "Easy", "recommended_style": "problem/solution demo"},
    {"category": "Kitchen", "idea": "อุปกรณ์ครัวที่ทำให้เมนูดูโปรขึ้น", "viral_potential": 82, "content_difficulty": "Medium", "recommended_style": "satisfying b-roll"},
    {"category": "Pet products", "idea": "ของเล็กๆ ที่ทำให้สัตว์เลี้ยงสบายขึ้น", "viral_potential": 86, "content_difficulty": "Medium", "recommended_style": "cute reaction + proof"},
    {"category": "Fashion", "idea": "ไอเท็มเปลี่ยนลุคใน 10 วินาที", "viral_potential": 80, "content_difficulty": "Medium", "recommended_style": "transition outfit reveal"},
    {"category": "Organization", "idea": "ของจัดบ้านที่แก้ความรกแบบเห็นชัด", "viral_potential": 83, "content_difficulty": "Easy", "recommended_style": "messy-to-clean reveal"},
    {"category": "Wellness", "idea": "ไอเท็มทำให้ routine ผ่อนคลายขึ้น", "viral_potential": 78, "content_difficulty": "Easy", "recommended_style": "soft emotional lifestyle"},
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
        "price": _field(product, "price", _field(product, "pricing", "")),
        "rating": _field(product, "rating", ""),
        "category": _field(product, "category", ""),
        "image": _field(product, "image", ""),
        "url": _field(product, "url", ""),
        "platform": _field(product, "platform", "manual"),
    }


def analyze_affiliate_product(product: dict[str, Any]) -> dict[str, Any]:
    product = normalize_affiliate_product(product)
    text = " ".join(str(product.get(key, "")) for key in ["product_name", "product_type", "description", "pain_point", "emotional_angle"]).lower()
    useful_terms = ["clean", "easy", "quick", "portable", "ช่วย", "ง่าย", "ประหยัด", "สบาย", "รีวิว", "แก้"]
    visual_terms = ["beauty", "fashion", "kitchen", "pet", "home", "สี", "ดีไซน์", "แสง", "แต่ง"]
    emotional_terms = ["เหนื่อย", "มั่นใจ", "สบาย", "ชีวิต", "เจ็บ", "เครียด", "รัก", "ดูแล"]
    utility = sum(1 for term in useful_terms if term in text)
    visual = sum(1 for term in visual_terms if term in text)
    emotional = sum(1 for term in emotional_terms if term in text)
    base = min(100, 64 + utility * 5 + visual * 4 + emotional * 5)
    creator_difficulty = max(20, 62 - visual * 5 + (8 if len(product.get("description", "")) < 30 else 0))
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
        ("shock", f"ก่อนซื้อคิดว่าไร้สาระ...แต่ {name} แก้เรื่องนี้ได้จริง"),
        ("curiosity", f"ทำไมคนที่เจอ{pain}ถึงเริ่มใช้ {name}?"),
        ("pain_point", f"ถ้า{pain}อยู่ทุกวัน คลิปนี้ช่วยตัดสินใจได้"),
        ("problem_solution", f"ปัญหา{pain} แก้ง่ายกว่าที่คิดด้วย {name}"),
        ("emotional", f"{audience}ที่เหนื่อยกับ{pain} น่าจะเข้าใจสิ่งนี้"),
        ("social_proof", f"อันนี้คือของที่ TikTok ป้ายยาถูกจริง: {name}"),
        ("urgency", f"ถ้าอยากให้{angle} รีบเช็ก {name} ก่อนพลาด"),
        ("pov", f"POV: คุณเจอ{pain}ทุกวัน แล้วลอง {name} ครั้งแรก"),
        ("before_after", f"ก่อนใช้กับหลังใช้ {name} ต่างกันตรงนี้"),
        ("tiktok_opener", f"99 บาทก็ยังต้องถามว่า...ทำไม {name} ดีขนาดนี้?"),
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


def build_affiliate_scripts(product: dict[str, Any], hooks: list[dict[str, Any]] | None = None) -> dict[str, str]:
    product = normalize_affiliate_product(product)
    top_hook = (hooks or generate_affiliate_hooks(product))[0]["hook_text"]
    name = product["product_name"]
    pain = product["pain_point"]
    cta = "ลองดูรายละเอียดก่อนตัดสินใจ" if product["cta_style"] == "soft sell" else "เช็กโปรตอนนี้"
    return {
        "tiktok_script_15s": f"0-3s: {top_hook}\n3-8s: โชว์ {name} แบบใกล้ๆ ว่าแก้ {pain} ยังไง\n8-12s: ให้เห็นผลลัพธ์หรือ before/after\n12-15s: {cta}",
        "tiktok_script_30s": f"0-3s: {top_hook}\n3-10s: เล่าปัญหา {pain} แบบ relatable\n10-20s: สาธิต {name} ด้วยมือและ close-up\n20-26s: สรุปข้อดี 2-3 ข้อ\n26-30s: {cta}",
        "pov_script": f"POV: คุณเบื่อกับ{pain} แล้วลอง {name} ครั้งแรก\nพูดให้เหมือนเล่าให้เพื่อนฟัง สั้น จริง และไม่ขายแข็ง",
        "review_script": f"รีวิวจริง: {name}\nชอบตรงที่ช่วยให้{product['emotional_angle']}\nเหมาะกับ{product['target_audience']}\nปิดด้วย CTA: {cta}",
        "emotional_sell_script": f"ถ้า{pain}ทำให้วันของคุณยากขึ้น {name} อาจเป็นตัวช่วยเล็กๆ ที่ทำให้{product['emotional_angle']}",
        "aesthetic_script": f"เปิดด้วย close-up สวยๆ ของ {name}\nตัดไป lifestyle usage\nจบด้วย hero shot และ CTA นุ่มๆ",
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
    return {
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
            "analysis/viral_analysis.txt": f"Recommended style: {analysis.get('recommended_content_style')}\nSelling angle: {analysis.get('selling_angle')}\nScores: {json.dumps(analysis.get('scores', {}), ensure_ascii=False)}\n",
            "hooks/viral_hooks.txt": "\n".join(item["hook_text"] for item in hooks),
            "hooks/emotional_hooks.txt": "\n".join(item["hook_text"] for item in hooks if item["hook_type"] in {"emotional", "pov", "before_after"}),
            "hooks/curiosity_hooks.txt": "\n".join(item["hook_text"] for item in hooks if item["hook_type"] in {"curiosity", "shock", "tiktok_opener"}),
            "scripts/tiktok_script_15s.txt": scripts["tiktok_script_15s"],
            "scripts/tiktok_script_30s.txt": scripts["tiktok_script_30s"],
            "scripts/pov_script.txt": scripts["pov_script"],
            "scripts/review_script.txt": scripts["review_script"],
            "creator/captions.txt": "\n\n".join(captions.get("captions", [])),
            "creator/hashtags.txt": " ".join(captions.get("hashtags", [])),
            "creator/scene_breakdown.txt": shots["scene_breakdown"],
            "creator/thumbnail_prompt.txt": thumbnail_prompt,
            "creator/creator_tips.txt": "ถ่ายให้เห็นมือใช้จริง\nเปิด 2 วินาทีแรกด้วยปัญหาหรือผลลัพธ์\nอย่าขายแข็งเกินไป\nปิดด้วย CTA เดียวที่ชัดเจน\n",
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
            "automation_policy": "No posting automation, no account automation, no browser botting.",
        }
        _write_json(final_dir / "manifest/affiliate_package_manifest.json", manifest)
        if quick_data.get("final_mp4"):
            src = Path(str(quick_data.get("final_mp4")))
            if src.is_file():
                shutil.copy2(src, ensure_parent_dir(final_dir / "final_hook_clip.mp4"))
        zip_path = project_dir / "exports" / "affiliate_creator_package.zip"
        ensure_parent_dir(zip_path)
        if zip_path.exists():
            zip_path.unlink()
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
