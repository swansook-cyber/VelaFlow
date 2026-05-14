from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.character_consistency import consistency_report, normalize_character
from core.final_package import inspect_final_package_inputs
from core.hook_intelligence import analyze_hooks
from core.marketing_package import build_marketing_package
from core.narrative_arc import analyze_narrative_arc
from core.project_io import safe_name
from core.quality_control import build_quality_checklist
from core.visual_story_consistency import analyze_visual_story_consistency


ROOT = Path(__file__).resolve().parents[1]


def run_full_project_audit(project: Dict[str, Any], render_dir: str | Path | None = None) -> Dict[str, Any]:
    checks = []
    checks.extend(_narrative_checks(project))
    checks.extend(_character_checks(project))
    checks.extend(_subtitle_checks(project))
    checks.extend(_hook_checks(project))
    checks.extend(_render_checks(project, render_dir))
    checks.extend(_asset_checks(project))
    checks.extend(_platform_checks(project, render_dir))
    checks.extend(_final_package_checks(project, render_dir))
    score = _weighted_score(checks)
    priority = _priorities(checks)
    verdict = _verdict(score, checks)
    data = {
        "project": project.get("title", "project"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "score": score,
        "verdict": verdict,
        "ready_for_final_render": score >= 78 and not any(item["level"] == "ERROR" and not item["ok"] for item in checks),
        "checks": checks,
        "fix_first": priority,
        "summary": _summary(checks),
    }
    return {"ok": True, "message": "Full project audit complete", "data": data, "error": ""}


def export_project_audit(project: Dict[str, Any], output_dir: str | Path | None = None, render_dir: str | Path | None = None) -> Dict[str, Any]:
    audit = run_full_project_audit(project, render_dir)
    output = Path(output_dir) if output_dir else ROOT / "outputs" / "audits" / safe_name(project.get("title", "project"))
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output / f"production_audit_{stamp}.json"
    md_path = output / f"production_audit_{stamp}.md"
    json_path.write_text(json.dumps(audit["data"], ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_audit_markdown(audit["data"]), encoding="utf-8")
    return {"ok": True, "message": "Production audit exported", "data": {"json": str(json_path), "markdown": str(md_path), "audit": audit["data"]}, "error": ""}


def _check(area: str, name: str, ok: bool, message: str, level: str = "WARN", weight: int = 5, fix: str = "") -> Dict[str, Any]:
    return {"area": area, "name": name, "ok": bool(ok), "message": message, "level": level, "weight": weight, "fix": fix}


def _storyboard(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(((project.get("mv", {}) or {}).get("storyboard", []) or []))


def _narrative_checks(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    narrative = analyze_narrative_arc(project).get("data", {})
    rows = narrative.get("rows", []) or []
    roles = {row.get("narrative_role") for row in rows}
    continuity = analyze_visual_story_consistency(project).get("data", {})
    return [
        _check("Narrative", "Storyboard exists", bool(rows), f"{len(rows)} scenes found", "ERROR", 10, "Generate storyboard in MV Director"),
        _check("Narrative", "Has setup and ending", {"setup", "resolution"} <= roles or len(rows) >= 2, f"roles: {', '.join(sorted(str(r) for r in roles if r))}", "WARN", 6, "Add clear opening and resolution scenes"),
        _check("Narrative", "Has emotional peak", bool({"climax", "emotional_peak"} & roles), f"peak scene: {narrative.get('emotional_peak', '-')}", "WARN", 8, "Strengthen chorus/final chorus scene role"),
        _check("Narrative", "Visual story consistency", continuity.get("score", 0) >= 70, f"score {continuity.get('score', 0)}", "WARN", 8, "Review character/color/emotion/lighting continuity"),
    ]


def _character_checks(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    character = normalize_character(project.get("character", {}) or {})
    storyboard = _storyboard(project)
    prompts = [
        str(scene.get("image_prompt_with_character") or scene.get("expanded_prompt") or scene.get("image_prompt") or "")
        for scene in storyboard
    ]
    scores = [consistency_report(prompt, character).get("score", 100) for prompt in prompts if prompt]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    has_character = any(character.get(key) for key in ["name", "gender", "hair", "outfit", "mood", "reference_notes"])
    return [
        _check("Character", "Character profile", has_character, "character lock metadata present" if has_character else "no character profile", "WARN", 5, "Fill Character Studio profile"),
        _check("Character", "Prompt character consistency", avg >= 65 or not has_character, f"average score {avg}", "WARN", 7, "Apply character lock to storyboard prompts"),
    ]


def _subtitle_checks(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    quality = build_quality_checklist(project).get("data", {})
    scenes = quality.get("scenes", []) or []
    long_lines = [row for row in scenes if row.get("subtitle_too_long")]
    missing = [row for row in scenes if not str(row.get("lyric_length", 0)).strip() and not row.get("lyric_length")]
    emotional = [scene for scene in _storyboard(project) if scene.get("subtitle_emotion_style") or scene.get("subtitle_ass_hint")]
    return [
        _check("Subtitle", "Readable subtitle length", not long_lines, f"{len(long_lines)} long subtitle lines", "WARN", 7, "Split long subtitle lines"),
        _check("Subtitle", "Subtitle text coverage", len(missing) == 0, f"{len(missing)} scenes may miss subtitle text", "WARN", 4, "Add lyric_part/subtitle_text to scenes"),
        _check("Subtitle", "Dynamic subtitle emotion", bool(emotional) or bool(scenes), f"{len(emotional)} scenes have emotion style", "INFO", 3, "Run Narrative Intelligence subtitle injection"),
    ]


def _hook_checks(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    hooks = analyze_hooks(project).get("data", {}).get("candidates", []) or []
    top = hooks[0] if hooks else {}
    tiktok = build_quality_checklist(project).get("data", {}).get("tiktok_recommendations", []) or []
    return [
        _check("Hook", "Hook candidate", bool(top), f"top hook score {top.get('hook_score', 0)}", "WARN", 8, "Clarify hook/chorus lyrics"),
        _check("Hook", "Hook clip readiness", top.get("hook_score", 0) >= 60 and bool(tiktok), f"{len(tiktok)} TikTok candidates", "WARN", 7, "Preview hook clip and strengthen subtitle emphasis"),
    ]


def _render_checks(project: Dict[str, Any], render_dir: str | Path | None) -> List[Dict[str, Any]]:
    assets = project.get("assets", {}) or {}
    render = inspect_final_package_inputs(project, render_dir).get("data", {})
    checks = render.get("checks", []) or []
    final_16 = next((item for item in checks if item.get("item") == "Final 16:9 MV"), {})
    final_9 = next((item for item in checks if item.get("item") == "Final 9:16 MV"), {})
    return [
        _check("Render", "Audio source", bool(assets.get("audio_path")), "audio path set" if assets.get("audio_path") else "missing audio", "WARN", 6, "Add audio file in Render Lab"),
        _check("Render", "Final 16:9 render", bool(final_16.get("ok")), final_16.get("path", ""), "WARN", 5, "Render final 16:9 output"),
        _check("Render", "Final 9:16 render", bool(final_9.get("ok")), final_9.get("path", ""), "INFO", 4, "Render 9:16 for Shorts/TikTok"),
    ]


def _asset_checks(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    storyboard = _storyboard(project)
    assets = project.get("assets", {}) or {}
    approved = assets.get("approved_images", {}) or {}
    missing = []
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        if not approved.get(scene_id) and not (assets.get("videos", {}) or {}).get(scene_id):
            missing.append(scene_id)
    return [
        _check("Assets", "Missing asset check", not missing and bool(storyboard), f"missing scenes: {', '.join(missing) if missing else 'none'}", "ERROR" if missing else "INFO", 12, "Approve or reuse images for missing scenes"),
        _check("Assets", "Hero shot selected", bool(assets.get("hero_shot") or approved), "hero/approved image available" if (assets.get("hero_shot") or approved) else "no hero shot", "WARN", 4, "Mark hero shot in Image Review"),
    ]


def _platform_checks(project: Dict[str, Any], render_dir: str | Path | None) -> List[Dict[str, Any]]:
    marketing = build_marketing_package(project).get("data", {})
    package = inspect_final_package_inputs(project, render_dir).get("data", {}).get("checks", []) or []
    by_item = {item.get("item"): item for item in package}
    upload = marketing.get("upload_checklist", []) or []
    youtube = bool(marketing.get("youtube", {}).get("title") and marketing.get("youtube", {}).get("description"))
    tiktok = bool(marketing.get("tiktok", {}).get("caption") and by_item.get("Final 9:16 MV", {}).get("ok"))
    return [
        _check("TikTok", "TikTok package readiness", tiktok, "caption + 9:16 render ready" if tiktok else "needs caption or 9:16 render", "WARN", 7, "Generate clips/9:16 render and TikTok caption"),
        _check("YouTube", "YouTube package readiness", youtube and by_item.get("Final 16:9 MV", {}).get("ok", False), "title/description + 16:9 render", "WARN", 7, "Render 16:9 and review YouTube copy"),
        _check("Marketing", "Upload checklist", bool(upload), f"{len(upload)} checklist items", "INFO", 3, "Build marketing package"),
    ]


def _final_package_checks(project: Dict[str, Any], render_dir: str | Path | None) -> List[Dict[str, Any]]:
    package = inspect_final_package_inputs(project, render_dir).get("data", {}).get("checks", []) or []
    ok_count = sum(1 for item in package if item.get("ok"))
    return [
        _check("Final Package", "Final package checklist", ok_count >= max(3, len(package) // 2), f"{ok_count}/{len(package)} ready", "WARN", 8, "Build final render, clips, captions, and marketing package"),
    ]


def _weighted_score(checks: List[Dict[str, Any]]) -> int:
    total = sum(max(1, int(item.get("weight", 1))) for item in checks)
    earned = sum(max(1, int(item.get("weight", 1))) for item in checks if item.get("ok"))
    return round((earned / total) * 100) if total else 0


def _priorities(checks: List[Dict[str, Any]], limit: int = 7) -> List[Dict[str, Any]]:
    failed = [item for item in checks if not item.get("ok")]
    severity = {"ERROR": 0, "WARN": 1, "INFO": 2}
    return sorted(failed, key=lambda item: (severity.get(item.get("level", "WARN"), 1), -int(item.get("weight", 1))))[:limit]


def _summary(checks: List[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "total": len(checks),
        "passed": sum(1 for item in checks if item.get("ok")),
        "errors": sum(1 for item in checks if item.get("level") == "ERROR" and not item.get("ok")),
        "warnings": sum(1 for item in checks if item.get("level") == "WARN" and not item.get("ok")),
    }


def _verdict(score: int, checks: List[Dict[str, Any]]) -> str:
    has_error = any(item.get("level") == "ERROR" and not item.get("ok") for item in checks)
    if has_error:
        return "Fix critical blockers before final render"
    if score >= 85:
        return "Ready for final render/export"
    if score >= 70:
        return "Good draft, fix priority warnings before final"
    return "Needs producer review before final render"


def _audit_markdown(data: Dict[str, Any]) -> str:
    lines = [
        f"# Production Audit: {data.get('project', 'project')}",
        "",
        f"Created: {data.get('created_at', '')}",
        f"Score: {data.get('score', 0)}/100",
        f"Verdict: {data.get('verdict', '')}",
        "",
        "## Fix First",
    ]
    for item in data.get("fix_first", []) or []:
        lines.append(f"- [{item.get('level')}] {item.get('area')} / {item.get('name')}: {item.get('fix') or item.get('message')}")
    if not data.get("fix_first"):
        lines.append("- No priority fixes.")
    lines += ["", "## Checks"]
    for item in data.get("checks", []) or []:
        mark = "OK" if item.get("ok") else item.get("level", "WARN")
        lines.append(f"- {mark} {item.get('area')} / {item.get('name')}: {item.get('message')}")
    return "\n".join(lines) + "\n"
