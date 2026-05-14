from __future__ import annotations

from typing import Any, Dict

from core.emotional_arc import analyze_emotional_arc
from core.hook_intelligence import analyze_hooks


def recommend_render_profile(project: Dict[str, Any]) -> Dict[str, Any]:
    song_text = " ".join(str(value or "") for value in (project.get("song", {}) or {}).values()).lower()
    arc = analyze_emotional_arc(project)["data"]
    hooks = analyze_hooks(project)["data"]["candidates"]
    top_hook = hooks[0]["hook_score"] if hooks else 0
    if any(word in song_text for word in ["viral", "tiktok", "dance", "beat", "fast"]) or top_hook >= 78:
        profile = "TikTok Fast"
        reason = "hook-first or viral/beat language detected"
    elif arc.get("climax_energy", 0) >= 80 and any(word in song_text for word in ["rock", "epic", "power"]):
        profile = "Standard"
        reason = "strong full-song energy detected"
    elif any(word in song_text for word in ["sad", "heartbreak", "lonely", "cinematic", "ballad", "miss"]) or arc.get("emotional_rise") in {"rising then release", "low restrained arc"}:
        profile = "Cinematic"
        reason = "emotional or cinematic song language detected"
    else:
        profile = "Standard"
        reason = "balanced project profile"
    return {"ok": True, "message": "Adaptive render profile recommended", "data": {"profile": profile, "reason": reason, "top_hook_score": top_hook, "arc": arc}, "error": ""}


def apply_adaptive_profile(project: Dict[str, Any]) -> Dict[str, Any]:
    recommendation = recommend_render_profile(project)
    profile = recommendation["data"]["profile"]
    project.setdefault("settings", {})["render_profile"] = profile
    project["settings"]["adaptive_profile_reason"] = recommendation["data"]["reason"]
    return {"ok": True, "message": f"Applied adaptive render profile: {profile}", "data": {"project": project, "profile": profile}, "error": ""}
