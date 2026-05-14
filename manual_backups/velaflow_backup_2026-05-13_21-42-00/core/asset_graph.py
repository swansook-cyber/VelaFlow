from __future__ import annotations

from typing import Any, Dict, List


def build_asset_relationship_graph(project: Dict[str, Any]) -> Dict[str, Any]:
    assets = project.get("assets", {}) or {}
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    nodes: List[Dict[str, Any]] = [{"id": "project", "label": project.get("title", "project"), "type": "project"}]
    edges: List[Dict[str, Any]] = []
    prompt_usage: Dict[str, int] = {}
    motion_usage: Dict[str, int] = {}
    for index, scene in enumerate(storyboard):
        scene_id = str(scene.get("scene") or index + 1)
        scene_node = f"scene:{scene_id}"
        nodes.append({"id": scene_node, "label": f"Scene {scene_id}", "type": "scene"})
        edges.append({"from": "project", "to": scene_node, "relation": "contains"})
        prompt = scene.get("image_prompt") or scene.get("expanded_prompt") or ""
        if prompt:
            prompt_id = f"prompt:{abs(hash(prompt))}"
            prompt_usage[prompt_id] = prompt_usage.get(prompt_id, 0) + 1
            nodes.append({"id": prompt_id, "label": prompt[:80], "type": "prompt"})
            edges.append({"from": prompt_id, "to": scene_node, "relation": "used_by"})
        motion = scene.get("motion_effect") or scene.get("camera") or ""
        if motion:
            motion_id = f"motion:{motion}"
            motion_usage[motion_id] = motion_usage.get(motion_id, 0) + 1
            nodes.append({"id": motion_id, "label": motion, "type": "motion"})
            edges.append({"from": motion_id, "to": scene_node, "relation": "drives"})
        image = (assets.get("approved_images", {}) or {}).get(scene_id) or (assets.get("images", {}) or {}).get(scene_id)
        if image:
            asset_id = f"asset:{image}"
            nodes.append({"id": asset_id, "label": image, "type": "asset"})
            edges.append({"from": asset_id, "to": scene_node, "relation": "visual_for"})
    unique_nodes = {node["id"]: node for node in nodes}
    reuse = [{"id": key, "count": count} for key, count in {**prompt_usage, **motion_usage}.items() if count > 1]
    return {"ok": True, "message": "Asset relationship graph built", "data": {"nodes": list(unique_nodes.values()), "edges": edges, "reuse": reuse}, "error": ""}
