from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.project_io import safe_name
from core.project_workflow import build_project_status
from core.quality_control import build_quality_checklist
from core.scene_scoring import smart_tiktok_recommendations
from core.branding import BRAND_NAME, PROGRAM_NAME, PRODUCT_TAGLINE
from core.version import identity_payload
from core.export_policy import load_export_policy


ROOT = Path(__file__).resolve().parents[1]


def _first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _song_title(project: Dict[str, Any]) -> str:
    song = project.get("song", {}) or {}
    return _first_text(song.get("title"), project.get("title"), f"{PROGRAM_NAME} Release")


def _artist(project: Dict[str, Any]) -> str:
    return _first_text(project.get("artist"), BRAND_NAME)


def _selected_hook(project: Dict[str, Any]) -> str:
    song = project.get("song", {}) or {}
    selected_hook = song.get("selected_hook")
    selected_hook_text = selected_hook.get("hook_text", "") if isinstance(selected_hook, dict) else selected_hook
    storyboard = ((project.get("mv", {}) or {}).get("storyboard", []) or [])
    for scene in storyboard:
        text = " ".join(str(scene.get(key, "") or "").lower() for key in ["emotion", "pacing_note", "section"])
        if "hook" in text or "chorus" in text:
            return _first_text(scene.get("subtitle_text"), scene.get("lyric_part"), song.get("selected_hook_text"), selected_hook_text)
    return _first_text(song.get("selected_hook_text"), selected_hook_text, song.get("complete_lyrics", "").splitlines()[0] if song.get("complete_lyrics") else "")


def _hashtags(project: Dict[str, Any]) -> List[str]:
    mv = project.get("mv", {}) or {}
    caps = mv.get("captions", {}) or {}
    tags = caps.get("hashtags", []) or []
    if isinstance(tags, str):
        tags = [part for part in tags.split() if part.startswith("#")]
    base = ["#เพลงไทย", "#เพลงใหม่", "#MV", "#VelaFlow", "#VelaLab"]
    style = str((project.get("song", {}) or {}).get("music_style_prompt", "")).lower()
    if "rock" in style:
        base.append("#PopRock")
    if "ballad" in style:
        base.append("#เพลงเศร้า")
    merged = []
    for tag in list(tags) + base:
        clean = str(tag).strip()
        if clean and clean not in merged:
            merged.append(clean if clean.startswith("#") else f"#{clean}")
    return merged[:18]


def _youtube_titles(project: Dict[str, Any]) -> List[str]:
    title = _song_title(project)
    artist = _artist(project)
    hook = _selected_hook(project)
    mv = project.get("mv", {}) or {}
    caps = mv.get("captions", {}) or {}
    existing = caps.get("youtube_title_options", []) or []
    if isinstance(existing, str):
        existing = [existing]
    generated = [
        f"{title} - {artist} | Official AI Music Video",
        f"{title} | {hook[:42]} | {PROGRAM_NAME}",
        f"{artist} - {title} (Cinematic MV)",
    ]
    return [item for item in list(existing) + generated if item][:5]


def _thumbnail_prompt(project: Dict[str, Any]) -> str:
    mv = project.get("mv", {}) or {}
    covers = mv.get("cover_prompts", {}) or {}
    existing = _first_text(covers.get("youtube_thumbnail_16x9"), covers.get("thumbnail_prompt"))
    if existing:
        return existing
    hook = _selected_hook(project)
    return (
        "cinematic YouTube thumbnail, Thai music video emotional moment, expressive singer, "
        "strong readable Thai title area, dramatic lighting, high contrast, premium pop music campaign, "
        f"visual mood inspired by lyric: {hook}"
    )


def _spotify_canvas_prompt(project: Dict[str, Any]) -> str:
    mv = project.get("mv", {}) or {}
    covers = mv.get("cover_prompts", {}) or {}
    existing = _first_text(covers.get("spotify_1x1"), covers.get("spotify_canvas_prompt"))
    if existing:
        return existing
    return (
        "8 second seamless vertical Spotify Canvas loop, cinematic close-up motion, emotional Thai singer, "
        "soft film grain, subtle camera drift, no text, loopable ending, premium music release visual"
    )


def build_marketing_package(project: Dict[str, Any]) -> Dict[str, Any]:
    title = _song_title(project)
    artist = _artist(project)
    hook = _selected_hook(project)
    mv = project.get("mv", {}) or {}
    caps = mv.get("captions", {}) or {}
    tags = _hashtags(project)
    tiktok = smart_tiktok_recommendations(project).get("data", {}).get("recommended_scenes", []) or []
    status = build_project_status(project)
    quality = build_quality_checklist(project)
    next_step = status.get("next_step", {})
    youtube_title = _youtube_titles(project)[0]
    youtube_description = _first_text(
        caps.get("youtube_description"),
        f"{title} by {artist}\n\n{hook}\n\nCreated with {PROGRAM_NAME}, {PRODUCT_TAGLINE}.",
    )
    tiktok_caption = _first_text(
        caps.get("tiktok_caption"),
        f"{hook}\n\n{title} - {artist}\n{' '.join(tags[:8])}",
    )
    facebook_caption = _first_text(
        caps.get("facebook_caption"),
        f"{title} - {artist}\n\n{hook}\n\nชม MV และบอกเราว่าท่อนไหนโดนใจที่สุด",
    )
    pinned_comment = _first_text(
        caps.get("pinned_comment"),
        f"ท่อนไหนของเพลง {title} ที่คุณชอบที่สุด? คอมเมนต์ไว้ได้เลย",
    )
    upload_checklist = [
        {"item": "Final render exported", "ok": "Render" not in status.get("data", {}).get("missing", [])},
        {"item": "9:16 short clips generated", "ok": bool(tiktok)},
        {"item": "Thumbnail prompt ready", "ok": bool(_thumbnail_prompt(project))},
        {"item": "Captions ready", "ok": bool(tiktok_caption and facebook_caption and youtube_description)},
        {"item": "Hashtags ready", "ok": bool(tags)},
        {"item": "Quality checklist reviewed", "ok": quality.get("ok", False)},
    ]
    release_note = (
        f"Release: {title}\n"
        f"Artist: {artist}\n"
        f"Hook: {hook}\n"
        f"Next operational step: {next_step.get('label', 'Review export package')}\n"
    )
    post_plan = [
        "Day 0: Publish YouTube MV and pin comment.",
        "Day 0: Post 15s TikTok teaser using the strongest hook scene.",
        "Day 1: Post Emotional Quote Clip with lyric caption.",
        "Day 2: Post 30s promo clip and link back to full MV.",
        "Day 3: Repost Spotify Canvas / short loop as story content.",
    ]
    package = {
        **identity_payload(),
        "project": title,
        "artist": artist,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "youtube": {"title": youtube_title, "title_options": _youtube_titles(project), "description": youtube_description},
        "tiktok": {"caption": tiktok_caption, "recommended_scenes": tiktok},
        "facebook": {"caption": facebook_caption},
        "hashtags": tags,
        "pinned_comment": pinned_comment,
        "thumbnail_prompt": _thumbnail_prompt(project),
        "spotify_canvas_prompt": _spotify_canvas_prompt(project),
        "upload_checklist": upload_checklist,
        "release_note": release_note,
        "post_plan": post_plan,
        "status": status,
        "export_policy": load_export_policy(),
    }
    return {"ok": True, "message": "Marketing package built", "data": package, "error": ""}


def _checklist_markdown(items: List[Dict[str, Any]]) -> str:
    lines = ["# Upload Checklist", ""]
    for item in items:
        mark = "x" if item.get("ok") else " "
        lines.append(f"- [{mark}] {item.get('item', '')}")
    return "\n".join(lines) + "\n"


def export_marketing_package(project: Dict[str, Any], output_dir: str | Path | None = None) -> Dict[str, Any]:
    package_result = build_marketing_package(project)
    package = package_result["data"]
    root = Path(output_dir) if output_dir else ROOT / "outputs" / "marketing_packages" / safe_name(package["project"])
    folder = root / "marketing_package"
    folder.mkdir(parents=True, exist_ok=True)

    files = {
        "youtube.txt": f"{package['youtube']['title']}\n\n{package['youtube']['description']}\n",
        "tiktok.txt": package["tiktok"]["caption"] + "\n",
        "facebook.txt": package["facebook"]["caption"] + "\n",
        "hashtags.txt": " ".join(package["hashtags"]) + "\n",
        "pinned_comment.txt": package["pinned_comment"] + "\n",
        "thumbnail_prompt.txt": package["thumbnail_prompt"] + "\n",
        "spotify_canvas_prompt.txt": package["spotify_canvas_prompt"] + "\n",
        "upload_checklist.md": _checklist_markdown(package["upload_checklist"]),
        "release_note.md": "# Release Note / Post Plan\n\n" + package["release_note"] + "\n## Post Plan\n" + "\n".join(f"- {item}" for item in package["post_plan"]) + "\n",
        "marketing_package.json": json.dumps(package, ensure_ascii=False, indent=2),
    }
    written = {}
    for name, text in files.items():
        path = folder / name
        path.write_text(text, encoding="utf-8")
        written[name] = str(path)
    return {"ok": True, "message": "Marketing package exported", "data": {"folder": str(folder), "files": written, "package": package}, "error": ""}
