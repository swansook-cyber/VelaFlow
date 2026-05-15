from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from core.paths import resolve_project_folder
from core.project_io import safe_name
from core.ffmpeg_utils import resolve_ffmpeg_path


VOICEOVER_STYLES = [
    "calm narrator",
    "emotional storyteller",
    "tired office worker",
    "sarcastic rant",
    "cozy storytelling",
    "meme voice",
]

OPENAI_TTS_VOICES = {
    "calm narrator": "alloy",
    "emotional storyteller": "coral",
    "tired office worker": "ash",
    "sarcastic rant": "verse",
    "cozy storytelling": "sage",
    "meme voice": "nova",
}


def build_voiceover_plan(script: str | list[str], style: str = "calm narrator") -> dict[str, Any]:
    lines = script if isinstance(script, list) else [line.strip() for line in str(script or "").splitlines() if line.strip()]
    style = style if style in VOICEOVER_STYLES else "calm narrator"
    cues = []
    current = 0.0
    for index, line in enumerate(lines[:20], start=1):
        duration = max(1.2, min(4.0, len(line) / 18))
        cues.append(
            {
                "cue_id": f"vo_{index:02d}",
                "start": round(current, 2),
                "end": round(current + duration, 2),
                "text": line,
                "pause_after": 0.35 if index < len(lines) else 0.0,
                "emphasis": "high" if index == 1 else "medium",
            }
        )
        current += duration + 0.35
    return {
        "generated_by": "VelaFlow",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "style": style,
        "provider_ready": ["OpenAI TTS", "ElevenLabs", "Gemini TTS future-ready"],
        "status": "script_only",
        "message": "TTS provider not called. Voiceover script and timing cues exported only.",
        "cues": cues,
    }


def export_voiceover_plan(project_name: str, plan: dict[str, Any], base_dir: str | Path | None = None) -> dict[str, Any]:
    try:
        folder = (Path(base_dir) / safe_name(project_name or "voiceover")) if base_dir else resolve_project_folder(project_name or "voiceover")
        export_dir = folder / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        json_path = export_dir / "voiceover_plan.json"
        txt_path = export_dir / "voiceover_script.txt"
        json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        txt_path.write_text("\n".join(cue.get("text", "") for cue in plan.get("cues", [])), encoding="utf-8")
        return {"ok": True, "message": "Voiceover plan exported", "data": {"json_path": str(json_path), "txt_path": str(txt_path)}, "error": ""}
    except Exception as exc:
        return {"ok": False, "message": "Voiceover export failed", "data": {}, "error": str(exc)}


def _find_ffmpeg() -> str:
    return resolve_ffmpeg_path("ffmpeg")


def _write_silent_mp3(path: Path, duration_seconds: float = 8.0) -> bool:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t",
        str(max(1.0, duration_seconds)),
        "-q:a",
        "9",
        "-acodec",
        "libmp3lame",
        str(path),
    ]
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    return proc.returncode == 0 and path.exists()


def generate_voiceover_audio(
    project_name: str,
    script: str | list[str],
    *,
    style: str = "calm narrator",
    api_key: str = "",
    provider: str = "openai",
    output_name: str = "hook_voiceover.mp3",
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    plan = build_voiceover_plan(script, style)
    folder = (Path(base_dir) / safe_name(project_name or "voiceover")) if base_dir else resolve_project_folder(project_name or "voiceover", "clips")
    export_dir = folder / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    output_path = export_dir / output_name
    text = "\n".join(cue.get("text", "") for cue in plan.get("cues", []))
    duration = max(3.0, min(30.0, (plan.get("cues", [{}])[-1].get("end", 8.0) if plan.get("cues") else 8.0)))
    if provider == "openai" and api_key and text.strip():
        try:
            response = requests.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini-tts",
                    "voice": OPENAI_TTS_VOICES.get(style, "alloy"),
                    "input": text[:4000],
                    "format": "mp3",
                },
                timeout=60,
            )
            if response.ok and response.content:
                output_path.write_bytes(response.content)
                plan["status"] = "completed"
                plan["provider"] = "openai"
                export_voiceover_plan(project_name, plan, base_dir)
                return {"ok": True, "message": "Voiceover MP3 generated with OpenAI TTS", "data": {"audio_path": str(output_path), "plan": plan}, "error": ""}
            error = response.text[:1000]
        except Exception as exc:
            error = str(exc)
    else:
        error = "missing_openai_key_or_provider_unavailable"
    if _write_silent_mp3(output_path, duration):
        plan["status"] = "fallback_silent_mp3"
        plan["provider"] = "offline_ffmpeg"
        plan["message"] = "OpenAI TTS was unavailable. Exported a silent MP3 placeholder and narration timing plan."
        export_voiceover_plan(project_name, plan, base_dir)
        return {"ok": True, "message": "Voiceover fallback MP3 generated", "data": {"audio_path": str(output_path), "plan": plan, "fallback_reason": error}, "error": ""}
    export_voiceover_plan(project_name, plan, base_dir)
    return {"ok": False, "message": "Voiceover MP3 unavailable. Script-only plan exported.", "data": {"plan": plan}, "error": error}
