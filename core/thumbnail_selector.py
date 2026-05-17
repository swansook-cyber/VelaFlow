from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def _score_scene(scene: dict[str, Any], image_result: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        [
            str(scene.get("subtitle", "")),
            str(scene.get("visual_prompt", "")),
            str(scene.get("visual_metaphor", "")),
            str(image_result.get("prompt", "")),
        ]
    ).lower()
    score = 50
    reasons: list[str] = []
    for marker in ["hook", "emotional", "peak", "close-up", "face", "neon", "rain", "meme", "character"]:
        if marker in text:
            score += 7
            reasons.append(marker)
    if scene.get("scene_id") == "scene_02":
        score += 6
        reasons.append("middle-emotional-frame")
    if scene.get("scene_id") == "scene_03":
        score += 10
        reasons.append("ending-strongest-frame")
    for marker in ["center", "centered", "contrast", "thumbnail", "face priority", "silhouette"]:
        if marker in text:
            score += 5
            reasons.append(marker)
    validation = image_result.get("validation") or {}
    if validation.get("aspect_ratio"):
        score += 4
        reasons.append("validated-image")
    return {
        "score": max(0, min(100, score)),
        "reasons": reasons[:8] or ["available scene image"],
        "mobile_readability": max(0, min(100, score + (8 if "subtitle-safe" in text else 0))),
        "cinematic_contrast": max(0, min(100, score + (10 if "contrast" in text or "rim light" in text else 0))),
        "face_priority": any(marker in text for marker in ["face", "close-up", "portrait", "character"]),
    }


def select_thumbnail_source(package: dict[str, Any], image_results: list[dict[str, Any]]) -> dict[str, Any]:
    scenes = package.get("scene_sequence") or []
    best: dict[str, Any] = {"path": "", "scene_id": "", "score": 0, "reason": "No scene image available", "candidates": []}
    for index, image_result in enumerate(image_results or []):
        path = Path(str(image_result.get("path") or ""))
        if not path.is_file():
            continue
        scene = scenes[index] if index < len(scenes) else {}
        score_data = _score_scene(scene, image_result)
        candidate = {
            "path": str(path),
            "scene_id": scene.get("scene_id") or image_result.get("scene_id") or f"scene_{index + 1:02d}",
            **score_data,
        }
        best.setdefault("candidates", []).append(candidate)
        if int(score_data.get("score", 0)) > int(best.get("score", 0)):
            best = {
                "path": str(path),
                "scene_id": scene.get("scene_id") or image_result.get("scene_id") or f"scene_{index + 1:02d}",
                "score": score_data["score"],
                "reason": "Best emotional/contrast candidate with subtitle-safe framing",
                "mobile_readability": score_data["mobile_readability"],
                "cinematic_contrast": score_data["cinematic_contrast"],
                "face_priority": score_data["face_priority"],
                "reasons": score_data["reasons"],
                "candidates": best.get("candidates", []),
            }
    return best


def export_thumbnail(package: dict[str, Any], image_results: list[dict[str, Any]], output_path: str | Path) -> dict[str, Any]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    selected = select_thumbnail_source(package, image_results)
    source = Path(str(selected.get("path") or ""))
    if not source.is_file():
        return {"ok": False, "message": "Thumbnail source missing", "data": {"path": str(output), **selected}, "error": "missing_thumbnail_source"}
    try:
        from PIL import Image

        with Image.open(source) as image:
            image = image.convert("RGB")
            target_w, target_h = 1080, 1920
            ratio = max(target_w / image.width, target_h / image.height)
            resized = image.resize((int(image.width * ratio), int(image.height * ratio)))
            left = max(0, (resized.width - target_w) // 2)
            top = max(0, (resized.height - target_h) // 2)
            cropped = resized.crop((left, top, left + target_w, top + target_h))
            cropped.save(output, "JPEG", quality=92)
    except Exception:
        shutil.copy2(source, output)
    score_path = output.with_name("thumbnail_score.json")
    score_payload = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "thumbnail_path": str(output) if output.is_file() else "",
        "selected": selected,
        "quality": {
            "thumbnail_quality": selected.get("score", 0),
            "mobile_readability": selected.get("mobile_readability", selected.get("score", 0)),
            "cinematic_contrast": selected.get("cinematic_contrast", selected.get("score", 0)),
            "face_priority": bool(selected.get("face_priority")),
        },
    }
    score_path.write_text(json.dumps(score_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": output.is_file(), "message": "Thumbnail exported", "data": {"path": str(output), "score_path": str(score_path), **selected}, "error": "" if output.is_file() else "thumbnail_export_failed"}


def score_affiliate_thumbnail_candidates(package: dict[str, Any], image_results: list[dict[str, Any]]) -> dict[str, Any]:
    selected = select_thumbnail_source(package, image_results)
    candidates = []
    for item in selected.get("candidates", []) or []:
        prompt_text = str(item.get("path", "")).lower()
        base = int(item.get("score", 0) or 0)
        scroll_stop = min(100, base + (10 if "scene_01" in prompt_text else 5))
        mobile = int(item.get("mobile_readability", base) or base)
        emotional = min(100, base + (8 if item.get("face_priority") else 0))
        candidates.append(
            {
                **item,
                "thumbnail_score": base,
                "scroll_stop_score": scroll_stop,
                "emotional_readability": emotional,
                "mobile_visibility_score": mobile,
            }
        )
    best = max(candidates, key=lambda row: int(row.get("scroll_stop_score", 0) or 0), default={})
    return {
        "generated_by": "VelaFlow",
        "best_thumbnail": best,
        "thumbnail_set": candidates,
        "thumbnail_score": best.get("thumbnail_score", 0),
        "scroll_stop_score": best.get("scroll_stop_score", 0),
        "emotional_readability": best.get("emotional_readability", 0),
        "mobile_visibility_score": best.get("mobile_visibility_score", 0),
    }
