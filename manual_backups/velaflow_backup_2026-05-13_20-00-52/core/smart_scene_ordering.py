from __future__ import annotations

from typing import Any, Dict, List

from core.emotional_arc import analyze_emotional_arc


def analyze_scene_order(project: Dict[str, Any]) -> Dict[str, Any]:
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    arc = {item["scene_id"]: item for item in analyze_emotional_arc(project)["data"]["points"]}
    rows: List[Dict[str, Any]] = []
    warnings: List[Dict[str, str]] = []
    previous_energy = None
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        energy = arc.get(scene_id, {}).get("energy", 50)
        if previous_energy is not None and abs(energy - previous_energy) > 45:
            warnings.append({"scene_id": scene_id, "message": "Energy jump may feel too abrupt"})
        rows.append({"scene_id": scene_id, "current_index": index, "energy": energy, "section": arc.get(scene_id, {}).get("section", "scene")})
        previous_energy = energy
    suggested = sorted(rows, key=lambda item: _order_weight(item["section"], item["energy"]))
    return {"ok": True, "message": "Scene ordering analyzed", "data": {"current": rows, "suggested": suggested, "warnings": warnings, "smooth": not warnings}, "error": ""}


def apply_suggested_scene_order(project: Dict[str, Any]) -> Dict[str, Any]:
    analysis = analyze_scene_order(project)
    order = [item["scene_id"] for item in analysis["data"]["suggested"]]
    storyboard = project.setdefault("mv", {}).setdefault("storyboard", [])
    by_id = {str(scene.get("scene") or index + 1): scene for index, scene in enumerate(storyboard)}
    reordered = [by_id[scene_id] for scene_id in order if scene_id in by_id]
    if len(reordered) == len(storyboard):
        project["mv"]["storyboard"] = reordered
    return {"ok": True, "message": "Applied suggested scene order", "data": {"project": project, "order": order}, "error": ""}


def _order_weight(section: str, energy: int) -> tuple[int, int]:
    section_order = {"intro": 0, "verse": 1, "scene": 2, "rise": 3, "bridge": 4, "hook": 5, "final_chorus": 6, "outro": 7}
    return (section_order.get(section, 2), energy)
