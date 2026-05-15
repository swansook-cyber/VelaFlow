from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def combine_scene_clips(
    scene_clips: list[str | Path],
    output_path: str | Path,
    *,
    subtitle_timing: list[dict[str, Any]] | None = None,
    voiceover_path: str | Path | None = None,
) -> dict[str, Any]:
    """Lightweight combine foundation.

    If moviepy is unavailable or real scene clips do not exist, this exports a
    combine manifest instead of crashing. No GPU or real render API is used.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = [Path(path) for path in scene_clips if Path(path).is_file()]
    manifest = {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "requested_output": str(output),
        "scene_clips": [str(path) for path in scene_clips],
        "existing_scene_clips": [str(path) for path in existing],
        "subtitle_timing": subtitle_timing or [],
        "voiceover_path": str(voiceover_path or ""),
        "status": "scene_package_only",
        "message": "Scene clips are not available yet. Exported combine manifest only.",
    }
    manifest_path = output.with_suffix(".combine_manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": manifest["message"], "data": {"manifest_path": str(manifest_path), "output_path": str(output)}, "error": ""}
