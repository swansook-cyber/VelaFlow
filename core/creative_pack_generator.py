from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from core.file_naming import build_export_filename, ensure_unique_path, sanitize_filename
from core.paths import workflow_project_root
from core.song_title_engine import generate_song_title_from_idea


CREATIVE_PACK_PRESETS: dict[str, dict[str, str]] = {
    "Thai Sad Pop": {
        "mood": "เศร้า ละมุน คิดถึง",
        "style": "cinematic emotional Thai pop, warm piano, soft drums, intimate vocal, memorable chorus",
        "visual": "rainy apartment window, warm shadows, lonely realistic character, premium Thai pop cover",
    },
    "Office Burnout": {
        "mood": "เหนื่อยล้าในออฟฟิศ แต่ยังอยากมีแรงไปต่อ",
        "style": "dark office pop, soft synth pulse, low piano, tired spoken verse, emotional chorus lift",
        "visual": "late night office, monitor glow, empty desk, city lights, cinematic burnout mood",
    },
    "Lonely Night Drive": {
        "mood": "ขับรถกลางคืน เหงา คิดถึงคนเก่า",
        "style": "night drive synth pop, mellow bass, airy pads, emotional male vocal, late-night hook",
        "visual": "car interior at night, blurred city lights, wet windshield, cinematic neon realism",
    },
    "Broken Relationship": {
        "mood": "รักพัง ยังลืมไม่ได้",
        "style": "modern heartbreak ballad, acoustic guitar, emotional strings, layered chorus harmony",
        "visual": "quiet bedroom after breakup, soft morning light, empty side of bed, realistic emotion",
    },
    "TikTok Emotional Hook": {
        "mood": "ฮุกสั้น จำง่าย เจ็บเร็ว",
        "style": "TikTok emotional hook, instant chorus intro, strong vocal phrase, punchy modern pop drums",
        "visual": "close-up emotional face, vertical cinematic frame, strong first-second visual hook",
    },
    "Indie Acoustic": {
        "mood": "อบอุ่น จริงใจ เหงาแบบเรียบง่าย",
        "style": "indie acoustic pop, fingerpicked guitar, soft vocal, organic room tone, gentle chorus",
        "visual": "small room with guitar, natural window light, film grain, cozy indie album cover",
    },
    "Dark Podcast Intro": {
        "mood": "ดาร์ก ออฟฟิศ เหนื่อยกับชีวิตเมือง",
        "style": "dark podcast intro music, low pulse, cinematic drone, intimate narration bed",
        "visual": "dark desk setup, microphone silhouette, city night, dramatic office storytelling",
    },
}


RELEASE_PACK_FILES = {
    "song_concept.txt": "Song concept",
    "suggested_title.txt": "Suggested title",
    "hook.txt": "Hook",
    "full_lyrics.txt": "Full lyrics",
    "music_style_prompt.txt": "Music style prompt for Suno/Udio",
    "cover_prompt.txt": "Cover prompt",
    "mv_storyboard_prompt.txt": "MV storyboard prompt",
    "shorts_tiktok_ideas.txt": "Shorts/TikTok ideas",
    "caption.txt": "Caption",
    "hashtags.txt": "Hashtags",
    "youtube_description.txt": "YouTube description",
    "release_notes.txt": "Release notes",
}


def _lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _seed_title(idea: str, preset_name: str) -> str:
    title = generate_song_title_from_idea(idea, "")
    title = str(title or "").strip()
    if title and title.lower() not in {"demo song", "untitled song", "new song"}:
        return title
    words = str(idea or preset_name).replace("\n", " ").split()
    return " ".join(words[:5]) or preset_name


def _hook_from_idea(idea: str, title: str, preset: dict[str, str]) -> str:
    lowered = str(idea or "").strip()
    if "ออฟฟิศ" in lowered or "office" in lowered.lower():
        return "\n".join(["ทำไมใจยังติดอยู่ที่โต๊ะเดิม", "ทั้งที่ไฟในตึกดับไปนานแล้ว", "ฉันแค่เหนื่อย หรือฉันไม่เหลือใคร"])
    if "แฟน" in lowered or "เลิก" in lowered or "relationship" in lowered.lower():
        return "\n".join(["ลืมเธอไม่ได้สักที", "แม้รู้ว่าเธอไม่กลับมา", "ใจยังเรียกชื่อเดิมทุกคืน"])
    if "drive" in lowered.lower() or "ขับรถ" in lowered:
        return "\n".join(["ถนนคืนนี้ยาวเกินไป", "ไฟเมืองยังพาใจกลับไปหาเธอ", "ยิ่งขับไกล ยิ่งลืมไม่ลง"])
    return "\n".join([title, "ท่อนนี้ต้องจำได้ตั้งแต่ครั้งแรก", f"อารมณ์หลัก: {preset['mood']}"])


def _lyrics(title: str, hook: str, idea: str, preset: dict[str, str]) -> str:
    hook_lines = _lines(hook)
    hook_block = "\n".join(hook_lines)
    first_hook = hook_lines[0] if hook_lines else title
    return "\n".join(
        [
            "[Intro]",
            f"(soft cinematic intro, {preset['style']})",
            f"คืนหนึ่งที่ใจยังไม่ยอมพักจากเรื่อง {idea}",
            "",
            "[Verse 1]",
            "ฉันเดินผ่านที่เดิมเหมือนไม่มีอะไรเปลี่ยน",
            "แต่ข้างในกลับเงียบจนได้ยินเสียงใจ",
            "ทุกข้อความเก่าเหมือนแสงที่ยังไม่ดับไป",
            "ยิ่งพยายามลืมเท่าไร ยิ่งชัดขึ้นมา",
            "",
            "[Pre-Chorus]",
            "ถ้าความทรงจำมีประตูให้ปิด",
            "ฉันคงไม่ติดอยู่ตรงนี้ซ้ำ ๆ",
            "",
            "[Chorus]",
            hook_block,
            first_hook,
            "ให้ท่อนนี้วนอยู่ในใจคนฟัง",
            "",
            "[Verse 2]",
            "เสียงเมืองยังดัง แต่ฉันกลับได้ยินแค่เธอ",
            "ทุกความเงียบทำให้คำลาเหมือนเพิ่งเกิดเมื่อวาน",
            "ฉันไม่รู้ว่าควรปล่อย หรือควรรอให้นาน",
            "เพราะหัวใจยังจำว่าเคยรักแค่ไหน",
            "",
            "[Bridge]",
            "ถ้าวันหนึ่งฉันยอมวางทุกอย่างลง",
            "ขอให้เพลงนี้เป็นคำสุดท้ายที่ยังอ่อนโยน",
            "",
            "[Final Chorus]",
            hook_block,
            "คราวนี้ร้องให้สุด เหมือนคืนสุดท้ายที่ยังคิดถึง",
            "",
            "[Outro]",
            "(emotional fade out, warm reverb tail, soft vocal ad-lib)",
            "ปล่อยให้ชื่อเธอค่อย ๆ จางไปกับเพลงนี้",
        ]
    )


def generate_creative_release_pack(
    idea: str,
    preset_name: str = "Thai Sad Pop",
    artist_name: str = "Vela Moon",
) -> dict[str, Any]:
    preset = CREATIVE_PACK_PRESETS.get(preset_name, CREATIVE_PACK_PRESETS["Thai Sad Pop"])
    concept = str(idea or "").strip() or preset["mood"]
    title = _seed_title(concept, preset_name)
    hook = _hook_from_idea(concept, title, preset)
    lyrics = _lyrics(title, hook, concept, preset)
    hashtags = ["#เพลงไทย", "#เพลงเศร้า", "#ThaiPop", "#VelaFlow", "#TikTokMusic", "#SunoAI", "#เพลงใหม่"]
    pack = {
        "Song concept": f"{concept}\nPreset: {preset_name}\nMood: {preset['mood']}",
        "Suggested title": title,
        "Hook": hook,
        "Full lyrics": lyrics,
        "Music style prompt for Suno/Udio": preset["style"],
        "Cover prompt": f"premium cover artwork for '{title}', {preset['visual']}, cinematic realism, no watermark",
        "MV storyboard prompt": (
            f"Vertical 9:16 emotional MV storyboard for '{title}'. Scene 1: wide atmosphere. "
            "Scene 2: medium emotional action. Scene 3: close-up hook moment. Scene 4: soft release ending. "
            f"Keep continuity: {preset['visual']}."
        ),
        "Shorts/TikTok ideas": "\n".join(
            [
                "1. เปิดด้วยท่อนฮุกที่เจ็บที่สุดใน 2 วินาทีแรก",
                "2. ทำ lyric visualizer แนว cinematic vertical",
                "3. ใช้ฉาก close-up อารมณ์กับ caption สั้น",
                "4. ตัด 15s hook สำหรับ Reels/Shorts",
            ]
        ),
        "Caption": f"{_lines(hook)[0] if _lines(hook) else title}\n\nเพลงนี้สำหรับคนที่ยังยิ้มได้ แต่ข้างในยังไม่หายดี",
        "Hashtags": " ".join(hashtags),
        "YouTube description": (
            f"{title} - {artist_name}\n\n"
            f"เพลงใหม่จาก VelaFlow concept: {concept}\n"
            "อารมณ์เพลงเน้นฮุกจำง่าย เนื้อหาเล่าเรื่องชัด และพร้อมนำไปต่อยอดใน Suno/Udio, Whisk, Flow, Veo, Runway หรือ Kling.\n\n"
            + " ".join(hashtags[:5])
        ),
        "Release notes": "\n".join(
            [
                "Release Pack generated locally by VelaFlow V1.",
                "No video rendering, lip sync, cloud render, or encoding was used.",
                "Review lyrics and prompts before publishing.",
                f"Created at: {datetime.now().isoformat(timespec='seconds')}",
            ]
        ),
    }
    return {
        "ok": True,
        "preset": preset_name,
        "artist_name": artist_name,
        "pack": pack,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def creative_release_pack_to_text(result: dict[str, Any]) -> str:
    pack = result.get("pack") or {}
    return "\n\n".join(
        [
            "VELAFLOW AI CREATIVE RELEASE PACK",
            f"Preset: {result.get('preset', '')}",
            f"Generated: {result.get('generated_at', '')}",
            *[f"====================\n{label}\n====================\n{pack.get(label, '')}" for label in RELEASE_PACK_FILES.values()],
        ]
    )


def export_creative_release_pack(
    project_name: str,
    result: dict[str, Any],
    artist_name: str = "Vela Moon",
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    try:
        pack = result.get("pack") or {}
        title = str(pack.get("Suggested title") or project_name or "VelaFlow Release")
        root = Path(base_dir) if base_dir else workflow_project_root("song") / sanitize_filename(project_name or title)
        export_dir = root / "exports" / "release_pack"
        export_dir.mkdir(parents=True, exist_ok=True)
        written: dict[str, str] = {}
        for filename, label in RELEASE_PACK_FILES.items():
            path = export_dir / filename
            path.write_text(str(pack.get(label, "")).strip() + "\n", encoding="utf-8-sig")
            written[filename] = str(path)
        txt_path = ensure_unique_path(export_dir / build_export_filename(title, artist_name, "Release_Pack", "txt"))
        txt_path.write_text(creative_release_pack_to_text(result), encoding="utf-8-sig")
        manifest = {
            "package_type": "ai_creative_release_pack",
            "render_features_used": False,
            "project_name": project_name,
            "song_title": title,
            "preset": result.get("preset"),
            "generated_files": written,
            "txt_export": str(txt_path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        manifest_path = export_dir / "release_pack_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        zip_path = ensure_unique_path(export_dir / build_export_filename(title, artist_name, "Release_Pack", "zip"))
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in [Path(item) for item in written.values()] + [txt_path, manifest_path]:
                archive.write(path, path.name)
        return {
            "ok": True,
            "data": {
                "export_dir": str(export_dir),
                "txt_path": str(txt_path),
                "zip_path": str(zip_path),
                "manifest_path": str(manifest_path),
                "files": written,
            },
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "data": {}, "error": str(exc)}
