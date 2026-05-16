import json
import re
from pathlib import Path
from typing import Any, Dict, List


SUBTITLE_MODES = [
    "none",
    "simple",
    "karaoke",
    "tiktok_bold",
    "cinematic",
    "word_by_word",
    "bounce",
    "punch",
    "emoji_pop",
    "dramatic",
    "meme_caption",
    "caption_heavy",
    "colorful",
    "soft_fade",
]


PRESET_SUBTITLE_MODE = {
    "viral_meme": "punch",
    "cute_character": "bounce",
    "emotional_story": "karaoke",
    "podcast_drama": "caption_heavy",
    "affiliate_sell": "meme_caption",
    "cinematic_mv": "cinematic",
}


SUBTITLE_STYLE_CONFIG = {
    "word_by_word": {"font_size": 64, "highlight_color": "&H0000FFFF", "animation_speed": "fast", "emoji_support": True, "outline_size": 4, "caption_position": "center"},
    "bounce": {"font_size": 68, "highlight_color": "&H0000FFAA", "animation_speed": "fun", "emoji_support": True, "outline_size": 5, "caption_position": "lower_center"},
    "punch": {"font_size": 76, "highlight_color": "&H0000FFFF", "animation_speed": "fast", "emoji_support": True, "outline_size": 6, "caption_position": "center"},
    "emoji_pop": {"font_size": 70, "highlight_color": "&H0000AAFF", "animation_speed": "fast", "emoji_support": True, "outline_size": 5, "caption_position": "center"},
    "karaoke": {"font_size": 54, "highlight_color": "&H0000FFFF", "animation_speed": "medium", "emoji_support": False, "outline_size": 3, "caption_position": "bottom"},
    "dramatic": {"font_size": 58, "highlight_color": "&H00FFFFFF", "animation_speed": "slow", "emoji_support": False, "outline_size": 3, "caption_position": "bottom"},
    "meme_caption": {"font_size": 72, "highlight_color": "&H0000FFFF", "animation_speed": "fast", "emoji_support": True, "outline_size": 6, "caption_position": "upper_center"},
    "caption_heavy": {"font_size": 52, "highlight_color": "&H00FFFFFF", "animation_speed": "medium", "emoji_support": False, "outline_size": 4, "caption_position": "lower_center"},
    "colorful": {"font_size": 68, "highlight_color": "&H0000FFAA", "animation_speed": "fun", "emoji_support": True, "outline_size": 5, "caption_position": "lower_center"},
    "soft_fade": {"font_size": 52, "highlight_color": "&H00F8F1E8", "animation_speed": "slow", "emoji_support": False, "outline_size": 2, "caption_position": "bottom"},
}


VIRAL_SUBTITLE_PRESETS = {
    "Thai Meme": {
        "mode": "punch",
        "font_size": 78,
        "emphasis_words": ["เดี๋ยวก่อน", "จริง", "พอ", "หยุด", "ทำไม"],
        "caption_position": "center",
        "emoji_highlight": True,
        "timing": "fast first line, punchy cuts",
    },
    "Emotional Karaoke": {
        "mode": "karaoke",
        "font_size": 56,
        "emphasis_words": ["ใจ", "รัก", "เจ็บ", "คิดถึง", "ลืม"],
        "caption_position": "bottom",
        "emoji_highlight": False,
        "timing": "lyric-following emotional pacing",
    },
    "Podcast Caption": {
        "mode": "caption_heavy",
        "font_size": 52,
        "emphasis_words": ["เรื่องนี้", "ฟังนะ", "จริง ๆ", "ชีวิต"],
        "caption_position": "lower_center",
        "emoji_highlight": False,
        "timing": "readable spoken caption pacing",
    },
    "Fast Viral Caption": {
        "mode": "meme_caption",
        "font_size": 74,
        "emphasis_words": ["อย่าเพิ่ง", "ต้องดู", "พลาดไม่ได้", "โคตร"],
        "caption_position": "upper_center",
        "emoji_highlight": True,
        "timing": "short dense subtitle bursts",
    },
    "Cute Character Pop": {
        "mode": "bounce",
        "font_size": 68,
        "emphasis_words": ["น่ารัก", "งง", "แง", "เอ๊ะ"],
        "caption_position": "lower_center",
        "emoji_highlight": True,
        "timing": "bouncy character beats",
    },
    "Affiliate CTA": {
        "mode": "meme_caption",
        "font_size": 70,
        "emphasis_words": ["ลด", "คุ้ม", "ต้องมี", "กด", "โปร"],
        "caption_position": "center",
        "emoji_highlight": True,
        "timing": "benefit then CTA",
    },
}


ASS_STYLES = {
    "simple": "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H7F000000,&H7F000000,0,0,0,0,100,100,0,0,1,2,1,2,80,80,80,1",
    "karaoke": "Style: Default,Arial,52,&H00FFFFFF,&H0000FFFF,&H7F000000,&H7F000000,1,0,0,0,100,100,0,0,1,2,1,2,80,80,90,1",
    "tiktok_bold": "Style: Default,Arial,72,&H0000FFFF,&H000000FF,&H00000000,&H7F000000,1,0,0,0,100,100,0,0,1,5,1,2,60,60,120,1",
    "cinematic": "Style: Default,Arial,46,&H00F8F1E8,&H000000FF,&H66000000,&H99000000,0,0,0,0,100,100,0,0,1,1,1,2,120,120,100,1",
    "word_by_word": "Style: Default,Arial,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H7F000000,1,0,0,0,100,100,0,0,1,4,1,5,50,50,120,1",
    "bounce": "Style: Default,Arial,68,&H00FFFFFF,&H0000FFAA,&H00000000,&H7F000000,1,0,0,0,100,100,0,0,1,5,1,2,50,50,150,1",
    "punch": "Style: Default,Arial,76,&H0000FFFF,&H000000FF,&H00000000,&H7F000000,1,0,0,0,104,104,0,0,1,6,1,5,40,40,110,1",
    "emoji_pop": "Style: Default,Arial,70,&H0000AAFF,&H000000FF,&H00000000,&H7F000000,1,0,0,0,104,104,0,0,1,5,1,5,40,40,110,1",
    "dramatic": "Style: Default,Arial,58,&H00FFFFFF,&H000000FF,&H88000000,&H99000000,1,0,0,0,100,100,0,0,1,3,1,2,90,90,120,1",
    "meme_caption": "Style: Default,Arial,72,&H0000FFFF,&H000000FF,&H00000000,&H7F000000,1,0,0,0,100,100,0,0,1,6,1,8,40,40,80,1",
    "caption_heavy": "Style: Default,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H7F000000,1,0,0,0,100,100,0,0,1,4,1,2,60,60,120,1",
    "colorful": "Style: Default,Arial,68,&H0000FFAA,&H0000FFFF,&H00000000,&H7F000000,1,0,0,0,104,104,0,0,1,5,1,2,50,50,145,1",
    "soft_fade": "Style: Default,Arial,52,&H00F8F1E8,&H000000FF,&H66000000,&H99000000,0,0,0,0,100,100,0,0,1,2,1,2,100,100,130,1",
}


def _format_srt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds or 0))
    ms = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds or 0))
    cs = int(round((seconds - int(seconds)) * 100))
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_animated_text(text: str, mode: str, duration: float) -> str:
    safe = str(text).replace("\n", r"\N").replace(",", "،")
    if mode == "karaoke":
        words = [word for word in safe.split(" ") if word]
        if not words:
            return safe
        centiseconds = max(8, int(duration * 100 / len(words)))
        return "".join(f"{{\\k{centiseconds}}}{word} " for word in words).strip()
    if mode == "tiktok_bold":
        return r"{\fad(60,80)\fscx108\fscy108\t(0,120,\fscx100\fscy100)}" + safe
    if mode == "cinematic":
        return r"{\fad(320,520)\blur0.6}" + safe
    if mode in {"word_by_word"}:
        words = [word for word in safe.split(" ") if word]
        centiseconds = max(6, int(duration * 100 / max(1, len(words))))
        return "".join(f"{{\\k{centiseconds}}}{word} " for word in words).strip()
    if mode in {"bounce", "colorful"}:
        return r"{\fad(40,80)\fscx84\fscy84\t(0,120,\fscx112\fscy112)\t(120,240,\fscx100\fscy100)}" + safe
    if mode in {"punch", "meme_caption"}:
        return r"{\fad(30,60)\fscx125\fscy125\t(0,90,\fscx100\fscy100)}" + safe
    if mode == "emoji_pop":
        return r"{\fad(30,80)\fscx118\fscy118\t(0,120,\fscx100\fscy100)}🔥 " + safe
    if mode in {"dramatic", "caption_heavy", "soft_fade"}:
        return r"{\fad(260,420)\blur0.3}" + safe
    return r"{\fad(120,160)}" + safe


def split_subtitle_text(text: str, max_chars: int = 42) -> List[str]:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return []
    chunks: List[str] = []
    current = ""
    for part in re.split(r"([,，ๆ.!?]|/)", cleaned):
        if not part:
            continue
        candidate = (current + part).strip()
        if len(candidate) > max_chars and current:
            chunks.append(current.strip())
            current = part.strip()
        else:
            current = candidate
    if current:
        chunks.append(current.strip())
    if len(chunks) == 1 and len(chunks[0]) > max_chars:
        text_value = chunks.pop()
        chunks.extend(text_value[i : i + max_chars] for i in range(0, len(text_value), max_chars))
    return [chunk for chunk in chunks if chunk]


def subtitle_events(timeline: List[Dict[str, Any]], mode: str = "simple") -> List[Dict[str, Any]]:
    if mode == "none":
        return []
    events: List[Dict[str, Any]] = []
    for item in timeline or []:
        text = item.get("subtitle_text") or item.get("lyric_part") or ""
        chunks = split_subtitle_text(text)
        if not chunks:
            continue
        start = float(item.get("start_time", 0) or 0)
        duration = max(0.8, float(item.get("duration_seconds", 1) or 1))
        chunk_duration = duration / len(chunks)
        for index, chunk in enumerate(chunks):
            events.append(
                {
                    "index": len(events) + 1,
                    "start": start + index * chunk_duration,
                    "end": start + (index + 1) * chunk_duration,
                    "text": chunk,
                    "scene_id": item.get("scene_id", ""),
                }
            )
    return events


def write_srt(timeline: List[Dict[str, Any]], output_path: str | Path, mode: str = "simple") -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    for event in subtitle_events(timeline, mode):
        lines.extend(
            [
                str(event["index"]),
                f"{_format_srt_time(event['start'])} --> {_format_srt_time(event['end'])}",
                event["text"],
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_ass(timeline: List[Dict[str, Any]], output_path: str | Path, mode: str = "simple") -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    style = ASS_STYLES.get(mode, ASS_STYLES["simple"])
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        style,
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    events = []
    for event in subtitle_events(timeline, mode):
        text = _ass_animated_text(event["text"], mode, max(0.1, float(event["end"]) - float(event["start"])))
        events.append(f"Dialogue: 0,{_format_ass_time(event['start'])},{_format_ass_time(event['end'])},Default,,0,0,0,,{text}")
    path.write_text("\n".join(header + events), encoding="utf-8")
    return path


def generate_subtitles(timeline: List[Dict[str, Any]], render_dir: str | Path, mode: str = "simple") -> Dict[str, Any]:
    render_dir = Path(render_dir)
    if mode == "none":
        return {"ok": True, "message": "Subtitles disabled", "data": {"srt": "", "ass": ""}, "error": ""}
    try:
        srt = write_srt(timeline, render_dir / "subtitle.srt", mode)
        ass = write_ass(timeline, render_dir / "subtitle.ass", mode)
        return {"ok": True, "message": "Subtitles generated", "data": {"srt": str(srt), "ass": str(ass)}, "error": ""}
    except Exception as error:
        return {"ok": False, "message": "Subtitle generation failed", "data": {}, "error": str(error)}


def mode_for_preset(preset_id: str | None, subtitle_style: str | None = None) -> str:
    style = str(subtitle_style or "").strip()
    if style in VIRAL_SUBTITLE_PRESETS:
        return VIRAL_SUBTITLE_PRESETS[style]["mode"]
    style_map = {
        "bold_fast": "punch",
        "cute_pop": "bounce",
        "soft_fade": "soft_fade",
        "caption_heavy": "caption_heavy",
        "cta_bold": "meme_caption",
        "minimal": "cinematic",
    }
    return style_map.get(style) or PRESET_SUBTITLE_MODE.get(str(preset_id or ""), "punch")


def list_viral_subtitle_presets() -> list[str]:
    return list(VIRAL_SUBTITLE_PRESETS)


def get_viral_subtitle_preset(name: str) -> Dict[str, Any]:
    return dict(VIRAL_SUBTITLE_PRESETS.get(name) or VIRAL_SUBTITLE_PRESETS["Fast Viral Caption"])


def subtitle_timing_to_timeline(subtitle_timing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    timeline: List[Dict[str, Any]] = []
    for item in subtitle_timing or []:
        start = float(item.get("start", 0) or 0)
        end = float(item.get("end", start + 1) or start + 1)
        timeline.append(
            {
                "scene_id": item.get("scene_id", ""),
                "start_time": start,
                "duration_seconds": max(0.5, end - start),
                "subtitle_text": item.get("subtitle") or item.get("text") or "",
            }
        )
    return timeline


def generate_styled_subtitles(subtitle_timing: List[Dict[str, Any]], export_dir: str | Path, *, preset_id: str = "", subtitle_style: str = "") -> Dict[str, Any]:
    try:
        mode = mode_for_preset(preset_id, subtitle_style)
        export_dir = Path(export_dir)
        timeline = subtitle_timing_to_timeline(subtitle_timing)
        srt = write_srt(timeline, export_dir / "subtitles.srt", mode)
        ass = write_ass(timeline, export_dir / "styled_subtitles.ass", mode)
        manifest_path = export_dir / "subtitle_manifest.json"
        config = SUBTITLE_STYLE_CONFIG.get(mode, SUBTITLE_STYLE_CONFIG["punch"])
        manifest_path.write_text(
            json.dumps(
                {
                    "mode": mode,
                    "preset_name": subtitle_style if subtitle_style in VIRAL_SUBTITLE_PRESETS else "",
                    "preset": VIRAL_SUBTITLE_PRESETS.get(subtitle_style, {}),
                    "style": config,
                    "srt": str(srt),
                    "ass": str(ass),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"ok": True, "message": "Styled subtitles generated", "data": {"mode": mode, "style": config, "srt": str(srt), "ass": str(ass), "manifest_path": str(manifest_path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Styled subtitle generation failed", "data": {}, "error": str(exc)}
