"""Synthetic fixtures and a disposable app tree; never copy credentials/user projects."""
import math
import os
import shutil
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def stage_app(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('app', 'core', 'providers', 'config', 'assets', 'static', 'data', '.streamlit'):
        shutil.copytree(ROOT / name, destination / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'secrets.toml'), dirs_exist_ok=True)
    return destination


def offline_env():
    return {k: v for k, v in os.environ.items()
            if not any(s in k.upper() for s in ('API_KEY', 'ACCESS_PASSWORD', 'RAILWAY', 'VELAFLOW_MODE'))}


def tone(path, *, duration=2, frequency=440, silent=False):
    path = Path(path)
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(48000)
        out.writeframes(b''.join(struct.pack('<h', 0 if silent else int(4000 * math.sin(2*math.pi*frequency*n/48000)))
                                 for n in range(int(duration * 48000))))
    return path
