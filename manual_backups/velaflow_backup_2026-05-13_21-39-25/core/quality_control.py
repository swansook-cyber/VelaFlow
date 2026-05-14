from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from core.scene_scoring import score_scene, smart_tiktok_recommendations


def _storyboard(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(((project.get("mv", {}) or {}).get("storyboard", []) or []))


def _assets(project: Dict[str, Any]) -> Dict[str, Any]:
    return project.get("assets", {}) or {}


def _has_approved_visual(assets: Dict[str, Any], scene_id: str) -> bool:
    image = (assets.get("approved_images", {}) or {}).get(scene_id)
    video = (assets.get("videos", {}) or {}).get(scene_id)
    return bool((image and Path(str(image)).is_file()) or (video and Path(str(video)).is_file()))


def quality_rows(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    assets = _assets(project)
    rows = []
    for index, scene in enumerate(_storyboard(project)):
        item = score_scene(scene, index, assets)
        scene_id = item["scene_id"]
        lyric = str(scene.get("subtitle_text") or scene.get("lyric_part") or "")
        prompt = str(scene.get("image_prompt_with_character") or scene.get("expanded_prompt") or scene.get("image_prompt") or "")
        rows.append(
            {
                **item,
                "has_approved_visual": _has_approved_visual(assets, scene_id),
                "has_prompt": bool(prompt.strip()),
                "subtitle_too_long": len(lyric.strip()) > 90,
                "lyric_length": len(lyric.strip()),
            }
        )
    return rows


def recommend_regenerate_images(project: Dict[str, Any], limit: int = 8) -> Dict[str, Any]:
    picks = []
    for row in quality_rows(project):
        reasons = []
        if not row["has_approved_visual"]:
            reasons.append("missing approved visual")
        if row["quality_score"] < 55:
            reasons.append("weak quality score")
        if not row["has_prompt"]:
            reasons.append("missing image prompt")
        if row["subtitle_too_long"]:
            reasons.append("subtitle too long")
        if reasons:
            picks.append(
                {
                    "scene_id": row["scene_id"],
                    "status": row["status"],
                    "quality_score": row["quality_score"],
                    "reasons": reasons,
                    "recommended_action": "regenerate_image" if row["has_prompt"] else "edit_prompt_then_regenerate",
                }
            )
    picks = sorted(picks, key=lambda item: item["quality_score"])[: max(1, int(limit or 8))]
    return {
        "ok": True,
        "message": "Image regeneration recommendations created",
        "data": {"scenes": picks},
        "error": "",
    }


def build_quality_checklist(project: Dict[str, Any]) -> Dict[str, Any]:
    rows = quality_rows(project)
    storyboard_count = len(rows)
    approved_count = sum(1 for row in rows if row["has_approved_visual"])
    weak_count = sum(1 for row in rows if row["status"] == "Weak")
    review_count = sum(1 for row in rows if row["status"] == "Needs Review")
    missing_prompt_count = sum(1 for row in rows if not row["has_prompt"])
    long_subtitle_count = sum(1 for row in rows if row["subtitle_too_long"])
    tiktok = smart_tiktok_recommendations(project)
    regenerate = recommend_regenerate_images(project)
    checks = [
        {
            "name": "Storyboard scenes",
            "ok": storyboard_count > 0,
            "message": f"{storyboard_count} scenes",
            "level": "INFO" if storyboard_count else "ERROR",
        },
        {
            "name": "Approved visuals",
            "ok": storyboard_count > 0 and approved_count == storyboard_count,
            "message": f"{approved_count}/{storyboard_count} scenes approved",
            "level": "INFO" if storyboard_count and approved_count == storyboard_count else "WARN",
        },
        {
            "name": "Weak scenes",
            "ok": weak_count == 0,
            "message": f"{weak_count} weak scenes",
            "level": "INFO" if weak_count == 0 else "WARN",
        },
        {
            "name": "Review scenes",
            "ok": review_count <= max(1, storyboard_count // 3),
            "message": f"{review_count} scenes need review",
            "level": "INFO" if review_count <= max(1, storyboard_count // 3) else "WARN",
        },
        {
            "name": "Image prompts",
            "ok": missing_prompt_count == 0,
            "message": f"{missing_prompt_count} missing prompts",
            "level": "INFO" if missing_prompt_count == 0 else "WARN",
        },
        {
            "name": "Subtitle length",
            "ok": long_subtitle_count == 0,
            "message": f"{long_subtitle_count} long subtitle lines",
            "level": "INFO" if long_subtitle_count == 0 else "WARN",
        },
    ]
    ok = storyboard_count > 0 and all(check["ok"] for check in checks if check["level"] in {"ERROR", "WARN"})
    return {
        "ok": ok,
        "message": "Quality checklist complete",
        "data": {
            "checks": checks,
            "scenes": rows,
            "regenerate_images": regenerate["data"]["scenes"],
            "tiktok_recommendations": tiktok["data"]["recommended_scenes"],
        },
        "error": "",
    }
