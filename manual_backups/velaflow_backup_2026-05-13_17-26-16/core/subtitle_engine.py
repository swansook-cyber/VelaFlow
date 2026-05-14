import re
from pathlib import Path
from typing import Any, Dict, List


SUBTITLE_MODES = ["none", "simple", "karaoke", "tiktok_bold", "cinematic"]


ASS_STYLES = {
    "simple": "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H7F000000,&H7F000000,0,0,0,0,100,100,0,0,1,2,1,2,80,80,80,1",
    "karaoke": "Style: Default,Arial,52,&H00FFFFFF,&H0000FFFF,&H7F000000,&H7F000000,1,0,0,0,100,100,0,0,1,2,1,2,80,80,90,1",
    "tiktok_bold": "Style: Default,Arial,72,&H0000FFFF,&H000000FF,&H00000000,&H7F000000,1,0,0,0,100,100,0,0,1,5,1,2,60,60,120,1",
    "cinematic": "Style: Default,Arial,46,&H00F8F1E8,&H000000FF,&H66000000,&H99000000,0,0,0,0,100,100,0,0,1,1,1,2,120,120,100,1",
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
