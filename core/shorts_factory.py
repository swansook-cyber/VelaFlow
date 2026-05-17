from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from core.automatic_hook_clip import quick_generate_hook_clip
from core.error_recovery import friendly_error_message
from core.paths import workflow_project_root
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir
from core.render_queue import complete_render_job, start_render_job


SHORTS_VARIATIONS = [
    {
        "variation_id": "v1_emotional",
        "label": "V1 Emotional",
        "preset_id": "emotional_story",
        "prompt_suffix": "Make this version more emotional, intimate, and relatable.",
        "subtitle_preset": "Thai Emotional MV",
        "duration": 20,
    },
    {
        "variation_id": "v2_aggressive_hook",
        "label": "V2 Aggressive Hook",
        "preset_id": "viral_meme",
        "prompt_suffix": "Make the first line stronger, more direct, and scroll-stopping.",
        "subtitle_preset": "TikTok Meme",
        "duration": 15,
    },
    {
        "variation_id": "v3_fast_pacing",
        "label": "V3 Fast Pacing",
        "preset_id": "viral_meme",
        "prompt_suffix": "Use faster pacing, quicker cuts, tighter subtitles, and stronger first 3 seconds.",
        "subtitle_preset": "Fast Punch",
        "duration": 15,
    },
    {
        "variation_id": "v4_stronger_cta",
        "label": "V4 Stronger CTA",
        "preset_id": "affiliate_sell",
        "prompt_suffix": "Make the CTA clearer, more conversion-focused, and easier to act on.",
        "subtitle_preset": "Affiliate CTA",
        "duration": 20,
    },
    {
        "variation_id": "v5_alt_thumbnail",
        "label": "V5 Alternate Thumbnail",
        "preset_id": "affiliate_sell",
        "prompt_suffix": "Use a different scene order and create a stronger thumbnail moment with product close-up.",
        "subtitle_preset": "Affiliate CTA",
        "duration": 20,
    },
]


def list_shorts_variations() -> list[dict[str, Any]]:
    return [dict(item) for item in SHORTS_VARIATIONS]


def _variation_prompt(base_prompt: str, variation: dict[str, Any]) -> str:
    return "\n".join(
        [
            str(base_prompt or ""),
            "",
            f"Shorts Factory variation: {variation['label']}",
            variation["prompt_suffix"],
            "Vary hook wording, subtitle emphasis, pacing, scene order, zoom intensity, thumbnail frame, and CTA timing.",
            "Keep output vertical 9:16 and TikTok-ready.",
        ]
    ).strip()


def _score_result(result: dict[str, Any], variation: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data", {}) or {}
    metrics = data.get("viral_metrics") or ((data.get("package") or {}).get("viral_metrics") or {})
    thumbnail = data.get("thumbnail") or {}
    hook_score = int(metrics.get("hook_score", metrics.get("hook_power", 0)) or 0)
    retention = int(metrics.get("tiktok_retention_potential", metrics.get("retention_estimate", 0)) or 0)
    emotional = int(metrics.get("emotional_impact", metrics.get("emotional_pacing", 0)) or 0)
    pacing = int(metrics.get("viral_pacing", metrics.get("conversion_pacing", 0)) or 0)
    thumb_score = int(thumbnail.get("score", 0) or 0)
    cta = int(metrics.get("cta_power", metrics.get("cta_strength", 0)) or 0)
    overall = round((hook_score + retention + emotional + pacing + thumb_score + cta) / 6)
    return {
        "variation_id": variation["variation_id"],
        "label": variation["label"],
        "ok": bool(result.get("ok")),
        "overall_score": overall,
        "retention_estimate": retention,
        "hook_score": hook_score,
        "emotional_score": emotional,
        "pacing_score": pacing,
        "thumbnail_score": thumb_score,
        "cta_score": cta,
        "hook_category": ((data.get("hook_analysis") or {}).get("hook_style") or variation["variation_id"]),
        "pacing_profile": ((data.get("beat_timing") or {}).get("timing_profile") or ""),
        "final_mp4": data.get("final_mp4", ""),
        "thumbnail": data.get("thumbnail_path", ""),
        "safe_error_message": "" if result.get("ok") else friendly_error_message(result.get("error") or result.get("message")),
    }


def build_shorts_comparison(results: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [item.get("score", {}) for item in results]
    successful = [score for score in scores if score.get("ok")]

    def best_by(key: str) -> dict[str, Any]:
        return max(successful, key=lambda row: int(row.get(key, 0) or 0), default={})

    best_overall = best_by("overall_score")
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "variation_count": len(results),
        "successful_count": len(successful),
        "best_overall": best_overall,
        "best_retention_estimate": best_by("retention_estimate"),
        "strongest_hook": best_by("hook_score"),
        "best_thumbnail": best_by("thumbnail_score"),
        "best_cta": best_by("cta_score"),
        "most_emotional_version": best_by("emotional_score"),
        "best_variation_type": best_overall.get("variation_id", ""),
        "top_hook_category": (best_by("hook_score") or {}).get("hook_category", ""),
        "most_successful_pacing_profile": (best_by("pacing_score") or {}).get("pacing_profile", ""),
        "scores": scores,
    }


def export_shorts_factory_package(project_name: str, results: list[dict[str, Any]], comparison: dict[str, Any], workflow_type: str = "clips") -> dict[str, Any]:
    try:
        project_dir = workflow_project_root(workflow_type or "clips") / safe_name(project_name or "shorts_factory")
        final_dir = project_dir / "exports" / "shorts_factory"
        final_dir.mkdir(parents=True, exist_ok=True)
        hook_reports = []
        cta_reports = []
        copied = []
        for item in results:
            variation = item.get("variation", {})
            score = item.get("score", {})
            data = item.get("data", {}) or {}
            variation_id = variation.get("variation_id", "variation")
            mp4 = Path(str(score.get("final_mp4") or data.get("final_mp4") or ""))
            if mp4.is_file():
                target = ensure_parent_dir(final_dir / f"{variation_id}.mp4")
                shutil.copy2(mp4, target)
                copied.append(str(target))
            thumb = Path(str(score.get("thumbnail") or data.get("thumbnail_path") or ""))
            if thumb.is_file():
                shutil.copy2(thumb, ensure_parent_dir(final_dir / f"{variation_id}_thumbnail.jpg"))
            hook_reports.append({"variation_id": variation_id, "hook_analysis": data.get("hook_analysis", {}), "score": score})
            cta_reports.append({"variation_id": variation_id, "cta_score": score.get("cta_score", 0), "package_hook": (data.get("package") or {}).get("hook_text", "")})
        files = {
            "shorts_factory_comparison.json": comparison,
            "hook_reports.json": hook_reports,
            "cta_reports.json": cta_reports,
            "viral_score_comparison.json": comparison.get("scores", []),
        }
        for filename, payload in files.items():
            (final_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest = {
            "generated_by": "VelaFlow",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "project_name": project_name,
            "final_dir": str(final_dir),
            "mp4_versions": copied,
            "comparison": comparison,
        }
        (final_dir / "shorts_factory_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "message": "Shorts Factory package exported", "data": manifest, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Shorts Factory export failed", "data": {}, "error": str(exc)}


def generate_shorts_factory(
    project_name: str,
    base_prompt: str,
    *,
    source_workflow: str = "seller",
    workflow_type: str = "clips",
    image_provider: str = "offline",
    image_settings: dict[str, Any] | None = None,
    max_variations: int = 5,
) -> dict[str, Any]:
    queue = start_render_job(project_name, workflow_type, stage="shorts_factory_batch", metadata={"variation_count": max_variations})
    if not queue.get("ok"):
        return {"ok": False, "message": queue.get("message", ""), "data": {}, "error": queue.get("error", "active_render_job")}
    job_id = ((queue.get("data") or {}).get("job") or {}).get("job_id", "")
    results: list[dict[str, Any]] = []
    try:
        for variation in SHORTS_VARIATIONS[: max(1, min(5, int(max_variations or 5)))]:
            result = quick_generate_hook_clip(
                project_name,
                _variation_prompt(base_prompt, variation),
                source_workflow=source_workflow,
                clip_mode="Fast Hook",
                duration_seconds=int(variation.get("duration", 15)),
                image_provider=image_provider,
                image_settings=image_settings or {},
                preset_id=str(variation.get("preset_id") or "viral_meme"),
                subtitle_preset=str(variation.get("subtitle_preset") or "TikTok Meme"),
                force_cache_refresh=True,
                force_final_render=True,
                variation=str(variation.get("variation_id")),
            )
            data = result.get("data", {}) or {}
            score = _score_result(result, variation)
            results.append({"variation": variation, "ok": bool(result.get("ok")), "data": data, "score": score, "error": result.get("error", "")})
        comparison = build_shorts_comparison(results)
        export = export_shorts_factory_package(project_name, results, comparison, workflow_type)
        complete_render_job(
            project_name,
            workflow_type,
            job_id,
            status="completed" if comparison.get("successful_count", 0) else "failed",
            result={"final_dir": (export.get("data") or {}).get("final_dir", ""), "successful_count": comparison.get("successful_count", 0)},
            safe_error_message="" if comparison.get("successful_count", 0) else "No shorts variations completed. Please retry.",
        )
        return {"ok": bool(comparison.get("successful_count", 0)), "message": "Shorts Factory generated", "data": {"results": results, "comparison": comparison, "export": export.get("data", {})}, "error": ""}
    except Exception as exc:
        complete_render_job(project_name, workflow_type, job_id, status="failed", error=str(exc), safe_error_message=friendly_error_message(str(exc)))
        return {"ok": False, "message": "Shorts Factory failed", "data": {"results": results}, "error": str(exc)}
