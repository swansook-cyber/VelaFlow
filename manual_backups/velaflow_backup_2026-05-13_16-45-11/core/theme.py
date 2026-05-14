from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
THEME_CONFIG_PATH = ROOT / "config" / "theme.json"


DEFAULT_THEME = {
    "active_theme": "Cinematic Dark",
    "themes": {
        "Dark": {"background": "#111318", "surface": "#1b1f27", "text": "#f4f7fb", "accent": "#4ea1ff"},
        "Cinematic Dark": {"background": "#0b0d12", "surface": "#171a22", "text": "#f6f1e8", "accent": "#d6a85a"},
        "Light": {"background": "#ffffff", "surface": "#f5f7fa", "text": "#1b2430", "accent": "#276ef1"},
    },
}


def load_theme_config(path: str | Path | None = None) -> Dict[str, Any]:
    source = Path(path) if path else THEME_CONFIG_PATH
    if not source.exists():
        return DEFAULT_THEME.copy()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        data.setdefault("active_theme", DEFAULT_THEME["active_theme"])
        data.setdefault("themes", DEFAULT_THEME["themes"])
        return data
    except Exception:
        return DEFAULT_THEME.copy()


def active_theme_name(path: str | Path | None = None) -> str:
    return str(load_theme_config(path).get("active_theme", "Cinematic Dark"))
