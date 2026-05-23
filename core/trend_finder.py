from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.file_naming import build_export_filename, ensure_unique_path
from core.paths import workflow_project_root
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir


TREND_PLATFORMS = ["TikTok Shop", "Shopee", "Lazada", "Multi Platform"]
TREND_CATEGORIES = ["Beauty", "Gadget", "Fashion", "Home", "Car", "Pet", "Food", "Random Viral"]
TREND_CONTENT_STYLES = ["Emotional", "Viral", "Luxury", "Review", "Problem/Solution", "POV", "Storytelling"]
TREND_AUDIENCES = ["Students", "Office Workers", "Women", "Men", "Parents", "Car Owners", "Gamers"]
TREND_PRICE_RANGES = ["Budget", "Mid", "Premium"]


_PRODUCT_SEEDS: dict[str, list[str]] = {
    "Beauty": ["Cooling sunscreen stick", "Hair smoothing brush", "Mini perfume atomizer", "Under-eye cooling roller"],
    "Gadget": ["Portable neck fan", "Mini desk vacuum", "Magnetic phone stand", "Cable organizer kit"],
    "Fashion": ["Clip-on waist adjuster", "Travel wrinkle-release spray", "Minimal daily tote", "No-show comfort socks"],
    "Home": ["Motion sensor night light", "Foldable storage box", "Sofa gap organizer", "Dehumidifier box"],
    "Car": ["Car seat gap filler", "Dashboard phone mount", "Mini car trash bin", "Sun visor organizer"],
    "Pet": ["Pet grooming glove", "Slow feeder bowl", "Portable pet water bottle", "Lint remover roller"],
    "Food": ["Protein snack box", "Instant coffee concentrate", "Air fryer liner", "Reusable smoothie cup"],
    "Random Viral": ["Mini thermal printer", "Satisfying cleaning gel", "LED mirror light", "Cute desk timer"],
}

_AUDIENCE_PAINS: dict[str, list[str]] = {
    "Students": ["limited budget", "messy dorm desk", "long study sessions"],
    "Office Workers": ["hot commute", "tired mornings", "cluttered work desk"],
    "Women": ["daily confidence", "busy routines", "small beauty fixes"],
    "Men": ["simple practical upgrades", "car or desk clutter", "low-maintenance routines"],
    "Parents": ["saving time", "keeping things clean", "making daily routines easier"],
    "Car Owners": ["traffic heat", "messy car space", "daily driving stress"],
    "Gamers": ["desk setup comfort", "cable clutter", "long-session convenience"],
}


def _choice(values: list[str], seed: str, offset: int) -> str:
    if not values:
        return ""
    return values[(sum(ord(ch) for ch in seed) + offset) % len(values)]


def _score(category: str, style: str, audience: str, price_range: str, index: int) -> int:
    score = 62 + index * 4
    if style in {"Emotional", "Problem/Solution", "POV"}:
        score += 8
    if category in {"Beauty", "Gadget", "Home", "Pet", "Car"}:
        score += 6
    if price_range == "Budget":
        score += 8
    elif price_range == "Mid":
        score += 4
    if audience in {"Office Workers", "Students", "Car Owners"}:
        score += 4
    return max(0, min(100, score))


def find_affiliate_trends(
    platform: str = "TikTok Shop",
    category: str = "Random Viral",
    content_style: str = "Problem/Solution",
    audience: str = "Office Workers",
    price_range: str = "Budget",
    *,
    count: int = 5,
) -> dict[str, Any]:
    platform = platform if platform in TREND_PLATFORMS else "Multi Platform"
    category = category if category in TREND_CATEGORIES else "Random Viral"
    content_style = content_style if content_style in TREND_CONTENT_STYLES else "Problem/Solution"
    audience = audience if audience in TREND_AUDIENCES else "Office Workers"
    price_range = price_range if price_range in TREND_PRICE_RANGES else "Budget"
    seeds = _PRODUCT_SEEDS.get(category) or _PRODUCT_SEEDS["Random Viral"]
    pains = _AUDIENCE_PAINS.get(audience) or _AUDIENCE_PAINS["Office Workers"]
    rows: list[dict[str, Any]] = []
    for idx in range(max(1, min(8, int(count or 5)))):
        product_name = _choice(seeds, f"{platform}-{category}-{audience}-{idx}", idx)
        pain = _choice(pains, product_name, idx)
        score = _score(category, content_style, audience, price_range, idx)
        competition = "Medium" if score < 82 else "High" if platform == "TikTok Shop" else "Medium-High"
        best_platform = platform if platform != "Multi Platform" else ("TikTok Shop" if price_range == "Budget" else "Shopee")
        rows.append(
            {
                "product_name": product_name,
                "category": category,
                "trend_score": score,
                "competition_level": competition,
                "audience_match": audience,
                "best_platform": best_platform,
                "why_it_may_convert": [
                    f"Solves a relatable {audience.lower()} pain point: {pain}",
                    "Easy to explain in the first 3 seconds",
                    "Works as impulse-buy content when shown with a real demo",
                ],
                "pain_points": [pain, "wasting time", "wanting a simple fix"],
                "viral_hooks": [
                    f"This tiny thing fixed my {pain}.",
                    f"I did not expect {product_name} to be this useful.",
                    f"POV: you finally stop dealing with {pain}.",
                ],
                "cta_lines": [
                    "Check it before it sells out.",
                    "Save this if you want to compare later.",
                    "Look at the details before you decide.",
                ],
                "thumbnail_ideas": [
                    f"Close-up reaction next to {product_name}",
                    f"Before/after frame showing {pain} solved",
                    "Clean product hero shot with human hand for scale",
                ],
                "shot_ideas": [
                    "0-2s pain-point close-up",
                    "2-6s product reveal in hand",
                    "6-12s real usage demo",
                    "12-15s result + soft CTA",
                ],
                "creator_notes": [
                    f"Best style: {content_style}",
                    f"Keep price framing: {price_range}",
                    "Use natural creator voice, not hard-sell wording",
                ],
            }
        )
    return {
        "ok": True,
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "filters": {
            "platform": platform,
            "category": category,
            "content_style": content_style,
            "audience": audience,
            "price_range": price_range,
        },
        "ideas": sorted(rows, key=lambda item: item["trend_score"], reverse=True),
    }


def export_trend_package(project_name: str, trend_result: dict[str, Any]) -> dict[str, Any]:
    try:
        ideas = trend_result.get("ideas") or []
        if not ideas:
            trend_result = find_affiliate_trends()
            ideas = trend_result["ideas"]
        project_dir = workflow_project_root("seller") / safe_name(project_name or "affiliate_trends")
        out_dir = project_dir / "exports" / "affiliate_trend_package"
        out_dir.mkdir(parents=True, exist_ok=True)
        top = ideas[0]
        report_lines = [
            "VelaFlow Affiliate Trend Finder",
            "",
            f"Platform: {trend_result.get('filters', {}).get('platform', '')}",
            f"Category: {trend_result.get('filters', {}).get('category', '')}",
            f"Audience: {trend_result.get('filters', {}).get('audience', '')}",
            "",
        ]
        for idea in ideas:
            report_lines.extend(
                [
                    f"Product: {idea['product_name']}",
                    f"Trend Score: {idea['trend_score']}",
                    f"Best Platform: {idea['best_platform']}",
                    "Why it may convert:",
                    *[f"- {item}" for item in idea["why_it_may_convert"]],
                    "",
                ]
            )
        files = {
            "trend_report.txt": "\n".join(report_lines),
            "viral_hooks.txt": "\n\n".join("\n".join(item["viral_hooks"]) for item in ideas),
            "cta_lines.txt": "\n".join(top["cta_lines"]),
            "thumbnail_ideas.txt": "\n".join(top["thumbnail_ideas"]),
            "shot_ideas.txt": "\n".join(top["shot_ideas"]),
            "creator_notes.txt": "\n".join(top["creator_notes"]),
        }
        for filename, content in files.items():
            (out_dir / filename).write_text(content, encoding="utf-8-sig")
        manifest = {
            "package_version": "affiliate_trend_finder_1",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "filters": trend_result.get("filters", {}),
            "idea_count": len(ideas),
            "top_product": top.get("product_name", ""),
            "generated_files": sorted([*files.keys(), "trend_manifest.json"]),
            "local_first": True,
            "automation_policy": "No scraping automation, no browser automation, no account automation.",
        }
        (out_dir / "trend_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        zip_path = ensure_parent_dir(ensure_unique_path(project_dir / "exports" / build_export_filename(project_name or "Affiliate Trends", "VelaFlow", "Affiliate_Trend_Package", "zip")))
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in out_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(out_dir).as_posix())
        return {"ok": True, "data": {"final_dir": str(out_dir), "zip_path": str(zip_path), "manifest": manifest}, "error": ""}
    except Exception as exc:
        return {"ok": False, "data": {}, "error": str(exc)}
