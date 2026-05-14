import shutil
import subprocess
from pathlib import Path
from typing import Optional


def ffmpeg_available(ffmpeg_path: str = "ffmpeg") -> bool:
    return shutil.which(ffmpeg_path) is not None or Path(ffmpeg_path).exists()


def build_concat_command(folder: str, output_name: str = "mv_16x9.mp4", audio_path: Optional[str] = None, ffmpeg_path: str = "ffmpeg") -> list[str]:
    base = Path(folder)
    concat_file = base / "render_scripts" / "ffmpeg_concat_list.txt"
    output = base / output_name
    cmd = [ffmpeg_path, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file)]
    if audio_path:
        cmd += ["-i", audio_path, "-map", "0:v:0", "-map", "1:a:0", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(output)]
    return cmd


def render_concat(folder: str, output_name: str = "mv_16x9.mp4", audio_path: Optional[str] = None, ffmpeg_path: str = "ffmpeg") -> tuple[bool, str]:
    cmd = build_concat_command(folder, output_name, audio_path, ffmpeg_path)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(folder)))
        if p.returncode == 0:
            return True, str(Path(folder) / output_name)
        return False, p.stderr[-3000:]
    except Exception as e:
        return False, str(e)
