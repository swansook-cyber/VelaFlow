from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
PRESET_ROOT = ROOT / "config" / "presets"


def export_preset_bundle(output_dir: str | Path | None = None) -> Dict[str, Any]:
    output = Path(output_dir) if output_dir else ROOT / "outputs" / "preset_bundles"
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"velaflow_presets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    manifest = {
        "generated_by": "VelaFlow",
        "bundle_type": "offline_preset_bundle",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "files": [],
    }
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in PRESET_ROOT.glob("*.json"):
            zf.write(path, path.name)
            manifest["files"].append(path.name)
        zf.writestr("preset_bundle_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return {"ok": True, "message": "Offline preset bundle exported", "data": {"path": str(target), "manifest": manifest}, "error": ""}


def import_preset_bundle(bundle_path: str | Path, backup: bool = True) -> Dict[str, Any]:
    source = Path(bundle_path)
    if not source.exists():
        return {"ok": False, "message": "Preset bundle not found", "data": {}, "error": "missing_bundle"}
    PRESET_ROOT.mkdir(parents=True, exist_ok=True)
    if backup:
        backup_dir = ROOT / "outputs" / "preset_bundles" / f"presets_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for path in PRESET_ROOT.glob("*.json"):
            shutil.copy2(path, backup_dir / path.name)
    imported = []
    with zipfile.ZipFile(source, "r") as zf:
        for name in zf.namelist():
            if not name.endswith(".json") or "/" in name or "\\" in name:
                continue
            if name == "preset_bundle_manifest.json":
                continue
            target = PRESET_ROOT / name
            target.write_bytes(zf.read(name))
            imported.append(name)
    return {"ok": True, "message": "Offline preset bundle imported", "data": {"imported": imported}, "error": ""}
