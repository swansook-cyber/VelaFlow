from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


AGENT_EXPORT_ROOT = Path("exports") / "agent_studio"


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _clean_text(value: Any, fallback: str = "agent_package") -> str:
    text = str(value or "").strip()
    return text or fallback


def generate_filename(title: str) -> str:
    text = _clean_text(title, "agent_package")
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._ ")
    return text[:80] or "agent_package"


def _unique_path(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return path
    return path.with_name(f"{path.stem}_{_now_stamp()}{path.suffix}")


def create_project_folder(project_name: str) -> Path:
    safe_name = generate_filename(project_name)
    folder = AGENT_EXPORT_ROOT / safe_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def export_txt(output: str, filename: str) -> Path:
    safe_name = generate_filename(Path(filename).stem)
    suffix = Path(filename).suffix or ".txt"
    path = _unique_path(AGENT_EXPORT_ROOT / f"{safe_name}{suffix}")
    path.write_text(_clean_text(output, "-"), encoding="utf-8-sig")
    return path


def _package_to_text(output: dict[str, str]) -> str:
    blocks: list[str] = []
    for key, value in output.items():
        blocks.append(str(key))
        blocks.append("=" * len(str(key)))
        blocks.append(_clean_text(value, "-"))
        blocks.append("")
    return "\n".join(blocks).strip() + "\n"


def save_project_package(output: dict[str, str], project_name: str) -> Path:
    folder = create_project_folder(project_name)
    path = _unique_path(folder / "agent_package.txt")
    path.write_text(_package_to_text(output), encoding="utf-8-sig")
    return path


def generate_release_checklist(project_type: str) -> str:
    base = [
        "[ ] Review the generated title ideas",
        "[ ] Copy the main creative direction",
        "[ ] Prepare the script, lyrics, or talking points",
        "[ ] Copy the caption and hashtags",
        "[ ] Save final files before publishing",
    ]
    if project_type == "Spotify Song Release":
        base[2:2] = ["[ ] Copy the Suno / music style prompt", "[ ] Generate cover artwork"]
    elif project_type == "Podcast Episode Idea":
        base[2:2] = ["[ ] Record the intro", "[ ] Mark short-clip extraction moments"]
    elif project_type == "AI Music Video Prompt":
        base[2:2] = ["[ ] Copy the video prompt", "[ ] Build the storyboard in your AI video tool"]
    elif project_type == "TikTok Affiliate Clip":
        base[2:2] = ["[ ] Film product proof shots", "[ ] Choose the strongest CTA"]
    return "\n".join(base)


def summarize_memory(memory: dict[str, Any]) -> str:
    if not isinstance(memory, dict) or not memory:
        return "No Agent Studio memory yet."
    ideas = memory.get("last_user_ideas") or []
    titles = memory.get("last_generated_titles") or []
    return "\n".join(
        [
            f"Recent project type: {memory.get('recent_project_type') or '-'}",
            f"Recent tone: {memory.get('recent_tone') or '-'}",
            f"Recent language: {memory.get('recent_language') or '-'}",
            f"Recent ideas: {', '.join(ideas[-3:]) if ideas else '-'}",
            f"Recent titles: {', '.join(titles[-3:]) if titles else '-'}",
            f"Creative direction: {memory.get('preferred_creative_direction_summary') or '-'}",
        ]
    )


def build_release_package(output: dict[str, str]) -> dict[str, Any]:
    title_block = _clean_text(output.get("Best Title Ideas"), "agent_package")
    first_title = next((line.strip("- ").strip() for line in title_block.splitlines() if line.strip()), "agent_package")
    folder = create_project_folder(first_title)
    generated_files: list[str] = []
    for section, content in output.items():
        filename = generate_filename(section.lower().replace("/", " ")) + ".txt"
        path = _unique_path(folder / filename)
        path.write_text(_clean_text(content, "-"), encoding="utf-8-sig")
        generated_files.append(str(path))
    manifest_path = _unique_path(folder / "agent_manifest.json")
    manifest = {
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "section_count": len(output),
        "generated_files": generated_files,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    generated_files.append(str(manifest_path))
    zip_path = _unique_path(folder / "agent_release_package.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_name in generated_files:
            path = Path(file_name)
            if path.is_file():
                archive.write(path, arcname=path.name)
    generated_files.append(str(zip_path))
    return {"folder": str(folder), "zip_path": str(zip_path), "files": generated_files}
