from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.hook_detector import detect_hook_section
from core.prompt_director import build_prompt_director_package, export_prompt_director_files
from core.project_io import safe_name
from core.real_clip_pipeline import ensure_parent_dir, trim_audio_clip, write_subtitles
from core.paths import workflow_project_root


def extract_full_hook_section(lyrics_text: str, fallback_hook: str = "") -> str:
    text = str(lyrics_text or "").replace("\r\n", "\n").strip()
    if not text:
        return str(fallback_hook or "").strip()
    section_pattern = re.compile(r"(?is)(?:^|\n)\s*\[(?:hook|chorus|pre-chorus|post-chorus)\]\s*\n(.*?)(?=\n\s*\[[^\]]+\]|\Z)")
    matches = [match.group(1).strip() for match in section_pattern.finditer(text) if match.group(1).strip()]
    if matches:
        return "\n".join(matches[:2]).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("[")]
    if len(lines) >= 4:
        start = max(0, min(len(lines) - 4, len(lines) // 2 - 2))
        return "\n".join(lines[start : start + min(8, len(lines) - start)]).strip()
    return "\n".join(lines).strip() or str(fallback_hook or "").strip()


def _caption_from_hook(hook_section: str) -> str:
    lines = [line.strip() for line in str(hook_section or "").splitlines() if line.strip()]
    core = "\n".join(lines[:2]) if lines else "เพลงนี้คือความรู้สึกที่พูดแทนใจ"
    return f"{core}\n\nฟังท่อนฮุกนี้แล้วคิดถึงใคร?"


def _hashtags(mood: str = "") -> str:
    base = ["#เพลงเศร้า", "#เพลงไทย", "#ThaiMusic", "#EmotionalSong", "#เพลงอกหัก", "#VelaFlow"]
    if "pop" in str(mood).lower():
        base.append("#ThaiPop")
    return " ".join(base)


def _upload_checklist() -> str:
    return "\n".join(
        [
            "[ ] Review selected_hook_section.txt",
            "[ ] Preview hook_audio.mp3",
            "[ ] Choose platform prompt: Flow / Veo / Runway / Kling / Pika / CapCut",
            "[ ] Paste prompt into external video tool",
            "[ ] Add subtitle.srt in editor if needed",
            "[ ] Copy TikTok caption and hashtags",
        ]
    )


def _write_text(path: Path, content: str) -> str:
    output = ensure_parent_dir(path)
    output.write_text(str(content or "").strip() + "\n", encoding="utf-8-sig")
    return str(output)


def generate_full_hook_creator_package(
    *,
    project_name: str,
    uploaded_mp3_path: str | Path,
    lyrics_text: str = "",
    fallback_hook: str = "",
    song_title: str = "",
    artist_name: str = "",
    mood: str = "",
    hook_start_time: float | None = None,
    hook_end_time: float | None = None,
    ffmpeg_path: str = "",
) -> dict[str, Any]:
    project_dir = workflow_project_root("song") / safe_name(project_name or song_title or "hook_creator_package")
    exports_dir = project_dir / "exports"
    package_dir = exports_dir / "creator_package"
    debug_dir = exports_dir / "debug"
    package_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    detection = detect_hook_section(
        uploaded_mp3_path,
        output_dir=debug_dir,
        quota_saving_mode=False,
        min_hook_duration=15,
        max_hook_duration=30,
        ffmpeg_path=ffmpeg_path,
    )
    if not detection.get("ok"):
        return {"ok": False, "message": "Hook detection failed", "data": detection.get("data", {}), "error": detection.get("error", "")}
    detected = detection["data"]
    start = float(hook_start_time if hook_start_time is not None else detected["hook_start_time"])
    end = float(hook_end_time if hook_end_time is not None else detected["hook_end_time"])
    if end <= start:
        end = start + float(detected.get("hook_duration") or 15)
    hook_audio_path = package_dir / "hook_audio.mp3"
    audio = trim_audio_clip(uploaded_mp3_path, hook_audio_path, start_time=start, end_time=end, ffmpeg_path=ffmpeg_path)
    if not audio.get("ok"):
        return {"ok": False, "message": "Hook audio export failed", "data": {"detection": detected}, "error": audio.get("error", "")}

    hook_section = extract_full_hook_section(lyrics_text, fallback_hook=fallback_hook)
    prompt_package = build_prompt_director_package(hook_section, song_title=song_title, artist_name=artist_name, mood=mood)
    files = {}
    files["hook_audio.mp3"] = str(hook_audio_path)
    files["selected_hook_section.txt"] = _write_text(package_dir / "selected_hook_section.txt", hook_section)
    files.update(export_prompt_director_files(prompt_package, package_dir))
    subtitle_lines = [line.strip() for line in hook_section.splitlines() if line.strip()]
    subtitle_timing = []
    duration = max(1.0, end - start)
    if subtitle_lines:
        slot = duration / len(subtitle_lines)
        for idx, line in enumerate(subtitle_lines):
            subtitle_timing.append({"start": round(idx * slot, 2), "end": round((idx + 1) * slot, 2), "text": line, "subtitle": line})
    write_subtitles(subtitle_timing, package_dir / "subtitle.srt")
    files["subtitle.srt"] = str(package_dir / "subtitle.srt")
    files["tiktok_caption.txt"] = _write_text(package_dir / "tiktok_caption.txt", _caption_from_hook(hook_section))
    files["youtube_description.txt"] = _write_text(package_dir / "youtube_description.txt", f"{song_title or project_name}\n\n{prompt_package['hook_summary']}\n\nCreated with VelaFlow.")
    files["hashtags.txt"] = _write_text(package_dir / "hashtags.txt", _hashtags(mood))
    files["upload_checklist.txt"] = _write_text(package_dir / "upload_checklist.txt", _upload_checklist())
    warning = ""
    if len(subtitle_lines) <= 1:
        warning = "Only one lyric line available; user should review."
    manifest = {
        "package_version": "full_hook_creator_package_v1",
        "project_name": project_name,
        "song_title": song_title,
        "artist_name": artist_name,
        "hook_start_time": round(start, 2),
        "hook_end_time": round(end, 2),
        "hook_duration": round(end - start, 2),
        "confidence_score": detected.get("confidence_score", detected.get("confidence")),
        "detection_reason": detected.get("detection_reason", detected.get("reason", "")),
        "energy_profile_summary": detected.get("energy_profile_summary", ""),
        "suggested_use": detected.get("suggested_use", ""),
        "hook_summary": prompt_package.get("hook_summary"),
        "emotional_tone": prompt_package.get("hook_emotion", {}).get("emotional_tone"),
        "selected_hook_section_line_count": len(subtitle_lines),
        "hook_section_warning": warning,
        "generated_files": files,
        "target_platforms": ["Flow", "Veo", "Runway", "Kling", "Pika", "CapCut"],
        "detection_report": detected.get("report_path", ""),
        "veo_called": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    manifest_path = package_dir / "creator_package_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    files["creator_package_manifest.json"] = str(manifest_path)
    zip_path = exports_dir / "creator_package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files.values():
            file_path = Path(path)
            if file_path.is_file():
                archive.write(file_path, file_path.name)
    return {
        "ok": True,
        "message": "Creator package generated",
        "data": {
            "package_dir": str(package_dir),
            "zip_path": str(zip_path),
            "manifest_path": str(manifest_path),
            "hook_audio": str(hook_audio_path),
            "selected_hook_section": hook_section,
            "manifest": manifest,
        },
        "error": "",
    }
