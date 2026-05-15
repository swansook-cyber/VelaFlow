import shutil
import subprocess
import os
from pathlib import Path
from typing import Any, Dict, List


ASPECT_RATIOS: Dict[str, Dict[str, Any]] = {
    "16:9": {"width": 1920, "height": 1080, "filename": "final_16x9.mp4"},
    "9:16": {"width": 1080, "height": 1920, "filename": "final_9x16.mp4"},
    "1:1": {"width": 1080, "height": 1080, "filename": "final_1x1.mp4"},
}


ROOT = Path(__file__).resolve().parents[1]


def resolve_ffmpeg_path(ffmpeg_path: str = "ffmpeg") -> str:
    configured = str(ffmpeg_path or "").strip() or os.getenv("FFMPEG_PATH", "ffmpeg")
    candidates: list[str | Path] = []
    if configured:
        candidates.append(configured)
    env_path = os.getenv("FFMPEG_PATH", "").strip()
    if env_path and env_path not in candidates:
        candidates.append(env_path)
    candidates.extend(
        [
            "ffmpeg",
            ROOT / "ffmpeg-2026-05-06-git-f2e5eff3ff-full_build" / "bin" / "ffmpeg.exe",
            ROOT / "ffmpeg" / "bin" / "ffmpeg.exe",
            ROOT / "bin" / "ffmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ]
    )
    for candidate in candidates:
        value = str(candidate)
        found = shutil.which(value)
        if found:
            return found
        path = Path(value)
        if path.exists():
            return str(path)
    return ""


def ffmpeg_available(ffmpeg_path: str = "ffmpeg") -> bool:
    return bool(resolve_ffmpeg_path(ffmpeg_path))


def ffmpeg_version(ffmpeg_path: str = "ffmpeg") -> Dict[str, Any]:
    resolved = resolve_ffmpeg_path(ffmpeg_path)
    if not resolved:
        return {"ok": False, "path": "", "version": "", "error": "missing_ffmpeg"}
    try:
        process = subprocess.run(
            [resolved, "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        first_line = (process.stdout or process.stderr or "").splitlines()[0] if (process.stdout or process.stderr) else ""
        return {
            "ok": process.returncode == 0,
            "path": resolved,
            "version": first_line,
            "error": "" if process.returncode == 0 else (process.stderr or process.stdout or "ffmpeg version check failed"),
        }
    except Exception as exc:
        return {"ok": False, "path": resolved, "version": "", "error": str(exc)}


def configure_moviepy_ffmpeg(ffmpeg_path: str = "ffmpeg") -> Dict[str, Any]:
    resolved = resolve_ffmpeg_path(ffmpeg_path)
    if resolved:
        os.environ["IMAGEIO_FFMPEG_EXE"] = resolved
        os.environ["FFMPEG_BINARY"] = resolved
        return {"ok": True, "path": resolved, "error": ""}
    return {"ok": False, "path": "", "error": "missing_ffmpeg"}


def append_log(log_path: str | Path, text: str) -> None:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def run_ffmpeg(command: List[str], log_path: str | Path, cwd: str | Path | None = None) -> Dict[str, Any]:
    append_log(log_path, "$ " + " ".join(f'"{part}"' if " " in str(part) else str(part) for part in command))
    try:
        process = subprocess.run(
            [str(part) for part in command],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (process.stdout or "") + ("\n" if process.stdout and process.stderr else "") + (process.stderr or "")
        if output.strip():
            append_log(log_path, output[-8000:])
        return {
            "ok": process.returncode == 0,
            "command": [str(part) for part in command],
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "error": "" if process.returncode == 0 else (process.stderr or process.stdout or "ffmpeg failed"),
        }
    except Exception as error:
        append_log(log_path, f"[ERROR] {error}")
        return {
            "ok": False,
            "command": [str(part) for part in command],
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "error": str(error),
        }


def normalize_scene_filter(width: int, height: int, fps: int = 30) -> str:
    return (
        f"fps={fps},"
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        "setsar=1,format=yuv420p"
    )


def safe_concat_line(path: str | Path) -> str:
    value = str(Path(path).resolve()).replace("\\", "/").replace("'", "'\\''")
    return f"file '{value}'"
