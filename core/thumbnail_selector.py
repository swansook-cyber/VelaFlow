from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def _score_scene(scene: dict[str, Any], image_result: dict[str, Any]) -> int:
    text = " ".join(
        [
            str(scene.get("subtitle", "")),
            str(scene.get("visual_prompt", "")),
            str(scene.get("visual_metaphor", "")),
            str(image_result.get("prompt", "")),
        ]
    ).lower()
    score = 50
    for marker in ["hook", "emotional", "peak", "close-up", "face", "neon", "rain", "meme", "character"]:
        if marker in text:
            score += 7
    if scene.get("scene_id") == "scene_02":
        score += 6
    return score


def select_thumbnail_source(package: dict[str, Any], image_results: list[dict[str, Any]]) -> dict[str, Any]:
    scenes = package.get("scene_sequence") or []
    best: dict[str, Any] = {"path": "", "scene_id": "", "score": 0, "reason": "No scene image available"}
    for index, image_result in enumerate(image_results or []):
        path = Path(str(image_result.get("path") or ""))
        if not path.is_file():
            continue
        scene = scenes[index] if index < len(scenes) else {}
        score = _score_scene(scene, image_result)
        if score > int(best.get("score", 0)):
            best = {
                "path": str(path),
                "scene_id": scene.get("scene_id") or image_result.get("scene_id") or f"scene_{index + 1:02d}",
                "score": score,
                "reason": "Best emotional/contrast candidate with subtitle-safe framing",
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
    return {"ok": output.is_file(), "message": "Thumbnail exported", "data": {"path": str(output), **selected}, "error": "" if output.is_file() else "thumbnail_export_failed"}
