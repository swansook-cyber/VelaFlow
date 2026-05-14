from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.marketing_package import build_marketing_package, export_marketing_package
from core.project_io import safe_name
from core.project_workflow import build_project_status
from core.quality_control import build_quality_checklist
from core.branding import PROGRAM_NAME
from core.version import identity_payload
from core.export_policy import load_export_policy
from core.artist_presets import get_artist_preset
from core.instrument_tag_normalizer import normalize_lyrics_tags, validate_english_only_tags


ROOT = Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _latest_render_dir(project: Dict[str, Any]) -> Path | None:
    render_root = ROOT / "outputs" / "renders" / safe_name(project.get("title", "project"))
    if not render_root.exists():
        return None
    render_dirs = [path for path in render_root.iterdir() if path.is_dir()]
    if not render_dirs:
        return None
    return sorted(render_dirs, key=lambda path: path.stat().st_mtime, reverse=True)[0]


def _copy_file(src: Path, dst: Path, copied: List[Dict[str, str]], missing: List[str], label: str) -> bool:
    if not src.is_file():
        missing.append(label)
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append({"label": label, "source": str(src), "target": str(dst)})
    return True


def _write(path: Path, text: str, copied: List[Dict[str, str]], label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or "", encoding="utf-8")
    copied.append({"label": label, "source": "generated", "target": str(path)})


def _zip_folder(folder: Path) -> Path:
    zip_path = folder.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in folder.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(folder.parent))
    return zip_path


def _project_report_markdown(project: Dict[str, Any], missing: List[str]) -> str:
    status = build_project_status(project)
    quality = build_quality_checklist(project)
    lines = [
        f"# Final Release Report: {project.get('title', 'project')}",
        "",
        f"Created: {_now()}",
        "",
        "## Project Status",
    ]
    for stage in status.get("data", {}).get("stages", []) or []:
        mark = "OK" if stage.get("ok") else "MISSING"
        lines.append(f"- {mark} {stage.get('name')}: {stage.get('detail')}")
    lines += ["", "## Quality Checks"]
    for check in quality.get("data", {}).get("checks", []) or []:
        mark = "OK" if check.get("ok") else check.get("level", "WARN")
        lines.append(f"- {mark} {check.get('name')}: {check.get('message')}")
    lines += ["", "## Missing Files"]
    if missing:
        lines.extend(f"- {item}" for item in missing)
    else:
        lines.append("- No critical package files missing.")
    lines += ["", "## Upload Safety", "- No auto upload was performed.", "- Review every file before publishing."]
    return "\n".join(lines) + "\n"


def _upload_checklist_markdown(package_checks: List[Dict[str, Any]]) -> str:
    lines = ["# Final Upload Checklist", ""]
    for item in package_checks:
        mark = "x" if item.get("ok") else " "
        lines.append(f"- [{mark}] {item.get('item')}")
    lines.append("")
    lines.append(f"No auto upload is performed by {PROGRAM_NAME}.")
    return "\n".join(lines) + "\n"


def inspect_final_package_inputs(project: Dict[str, Any], render_dir: str | Path | None = None) -> Dict[str, Any]:
    render_path = Path(render_dir) if render_dir else _latest_render_dir(project)
    clips_dir = render_path / "clips" if render_path else None
    marketing = build_marketing_package(project).get("data", {})
    checks = [
        {"item": "Render folder found", "ok": bool(render_path and render_path.exists()), "path": str(render_path or "")},
        {"item": "Final 16:9 MV", "ok": bool(render_path and (render_path / "final_16x9.mp4").is_file()), "path": str((render_path / "final_16x9.mp4") if render_path else "")},
        {"item": "Final 9:16 MV", "ok": bool(render_path and (render_path / "final_9x16.mp4").is_file()), "path": str((render_path / "final_9x16.mp4") if render_path else "")},
        {"item": "Subtitle SRT", "ok": bool(render_path and (render_path / "subtitle.srt").is_file()), "path": str((render_path / "subtitle.srt") if render_path else "")},
        {"item": "Subtitle ASS", "ok": bool(render_path and (render_path / "subtitle.ass").is_file()), "path": str((render_path / "subtitle.ass") if render_path else "")},
        {"item": "Clips folder", "ok": bool(clips_dir and clips_dir.exists()), "path": str(clips_dir or "")},
        {"item": "Clip MP4 files", "ok": bool(clips_dir and list(clips_dir.glob("*.mp4"))), "path": str(clips_dir or "")},
        {"item": "Marketing copy ready", "ok": bool(marketing.get("youtube") and marketing.get("tiktok")), "path": ""},
        {"item": "Thumbnail prompt ready", "ok": bool(marketing.get("thumbnail_prompt")), "path": ""},
    ]
    return {"ok": True, "message": "Final package inputs inspected", "data": {"render_dir": str(render_path or ""), "checks": checks}, "error": ""}


def build_final_release_package(
    project: Dict[str, Any],
    output_dir: str | Path | None = None,
    render_dir: str | Path | None = None,
    zip_package: bool = True,
) -> Dict[str, Any]:
    title = safe_name(project.get("title", "project"))
    root = Path(output_dir) if output_dir else ROOT / "outputs" / "final_packages" / title
    package_dir = root / "final_package"
    if package_dir.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = root / f"final_package_backup_{stamp}"
        counter = 1
        while backup.exists():
            counter += 1
            backup = root / f"final_package_backup_{stamp}_{counter}"
        package_dir.replace(backup)
    for sub in ["song", "mv", "clips", "captions", "marketing_package", "thumbnails", "prompts"]:
        (package_dir / sub).mkdir(parents=True, exist_ok=True)

    copied: List[Dict[str, str]] = []
    missing: List[str] = []
    render_path = Path(render_dir) if render_dir else _latest_render_dir(project)
    song = project.get("song", {}) or {}
    mv = project.get("mv", {}) or {}
    storyboard = mv.get("storyboard", []) or []
    marketing_result = export_marketing_package(project, package_dir)
    marketing_folder = Path(marketing_result.get("data", {}).get("folder", ""))
    if marketing_folder.exists() and marketing_folder != package_dir / "marketing_package":
        for file in marketing_folder.rglob("*"):
            if file.is_file():
                rel = file.relative_to(marketing_folder)
                _copy_file(file, package_dir / "marketing_package" / rel, copied, missing, f"marketing/{rel}")

    artist_preset = get_artist_preset(song.get("artist_preset", "vela_moon"))
    normalized_lyrics = song.get("normalized_song_output") or normalize_lyrics_tags(song.get("complete_lyrics", ""), artist_preset)
    _write(package_dir / "song" / "song.json", json.dumps(song, ensure_ascii=False, indent=2), copied, "song/song.json")
    _write(package_dir / "song" / "lyrics.txt", normalized_lyrics, copied, "song/lyrics.txt")
    _write(package_dir / "song" / "suno_style_prompt.txt", song.get("music_style_prompt", ""), copied, "song/suno_style_prompt.txt")
    _write(package_dir / "song" / "artist_preset.json", json.dumps(song.get("artist_preset_data") or artist_preset, ensure_ascii=False, indent=2), copied, "song/artist_preset.json")
    _write(package_dir / "song" / "instrument_tag_validation.json", json.dumps(validate_english_only_tags(normalized_lyrics), ensure_ascii=False, indent=2), copied, "song/instrument_tag_validation.json")

    _write(package_dir / "prompts" / "storyboard.json", json.dumps(storyboard, ensure_ascii=False, indent=2), copied, "prompts/storyboard.json")
    _write(package_dir / "prompts" / "mv.json", json.dumps(mv, ensure_ascii=False, indent=2), copied, "prompts/mv.json")
    prompt_lines = []
    for scene in storyboard:
        scene_id = scene.get("scene", "")
        prompt_lines += [
            f"Scene {scene_id}",
            scene.get("image_prompt_with_character") or scene.get("expanded_prompt") or scene.get("image_prompt", ""),
            f"Video: {scene.get('video_prompt', '')}",
            "",
        ]
    _write(package_dir / "prompts" / "scene_prompts.txt", "\n".join(prompt_lines), copied, "prompts/scene_prompts.txt")

    if render_path and render_path.exists():
        for filename in ["final_16x9.mp4", "final_9x16.mp4", "final_1x1.mp4", "render_manifest.json", "timeline.json", "assets_used.json"]:
            src = render_path / filename
            if src.exists():
                _copy_file(src, package_dir / "mv" / filename, copied, missing, f"mv/{filename}")
            elif filename.startswith("final_"):
                missing.append(f"mv/{filename}")
        for filename in ["subtitle.srt", "subtitle.ass"]:
            _copy_file(render_path / filename, package_dir / "captions" / filename, copied, missing, f"captions/{filename}")
        clips_dir = render_path / "clips"
        if clips_dir.exists():
            for file in clips_dir.rglob("*"):
                if file.is_file():
                    target_root = package_dir / ("captions" if "caption" in file.stem else "clips")
                    _copy_file(file, target_root / file.name, copied, missing, f"{target_root.name}/{file.name}")
        else:
            missing.append("clips folder")
    else:
        missing.append("render folder")

    marketing = build_marketing_package(project).get("data", {})
    _write(package_dir / "thumbnails" / "thumbnail_prompt.txt", marketing.get("thumbnail_prompt", ""), copied, "thumbnails/thumbnail_prompt.txt")
    _write(package_dir / "thumbnails" / "spotify_canvas_prompt.txt", marketing.get("spotify_canvas_prompt", ""), copied, "thumbnails/spotify_canvas_prompt.txt")

    package_checks = inspect_final_package_inputs(project, render_path).get("data", {}).get("checks", [])
    _write(package_dir / "project_report.md", _project_report_markdown(project, missing), copied, "project_report.md")
    _write(package_dir / "upload_checklist.md", _upload_checklist_markdown(package_checks), copied, "upload_checklist.md")
    manifest = {
        **identity_payload(),
        "project": project.get("title", "project"),
        "created_at": _now(),
        "render_dir": str(render_path or ""),
        "missing": missing,
        "copied": copied,
        "auto_upload": False,
        "export_policy": load_export_policy(),
    }
    _write(package_dir / "final_package_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2), copied, "final_package_manifest.json")
    zip_path = str(_zip_folder(package_dir)) if zip_package else ""
    ok = bool(package_dir.exists())
    return {
        "ok": ok,
        "message": "Final release package built",
        "data": {"folder": str(package_dir), "zip": zip_path, "missing": missing, "copied": copied, "checks": package_checks},
        "error": "",
    }
