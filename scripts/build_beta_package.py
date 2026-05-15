from __future__ import annotations

import fnmatch
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "beta_packages"
INCLUDE_PATHS = [
    "app",
    "core",
    "providers",
    "tests",
    "docs",
    "assets",
    ".gitignore",
    "CHANGELOG.md",
    "README.md",
    "requirements.txt",
    ".env.example",
    "Procfile",
    "railway.json",
    "runtime.txt",
    "run_velaflow.bat",
]
EXCLUDE_PATTERNS = [
    ".env",
    ".env.*",
    ".venv/*",
    "venv/*",
    "temp/*",
    "runtime/*",
    "project_data/*",
    "outputs/*",
    "exports/*",
    "logs/*",
    "cache/*",
    "*/cache/*",
    "*/__pycache__/*",
    "__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*.tmp",
    "*.log",
    "*.mp4",
    "*.mov",
    "*.mkv",
    "*.avi",
    "*.wav",
    "*.mp3",
]


def _as_posix(path: Path) -> str:
    return path.as_posix()


def _version() -> str:
    try:
        version_file = ROOT / "core" / "version.py"
        match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', version_file.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            return match.group(1).replace(".", "_")
    except Exception:
        pass
    return "beta"


def is_excluded(relative_path: str) -> bool:
    value = relative_path.replace("\\", "/")
    if value == ".env.example":
        return False
    parts = value.split("/")
    if ".venv" in parts or "venv" in parts or "__pycache__" in parts:
        return True
    if value == ".env" or (value.startswith(".env.") and value != ".env.example"):
        return True
    if value.startswith(("project_data/", "outputs/", "exports/", "logs/", "cache/", "temp/", "runtime/")):
        return True
    return any(fnmatch.fnmatch(value, pattern) for pattern in EXCLUDE_PATTERNS)


def iter_beta_files(root: Path = ROOT) -> Iterable[Path]:
    for include in INCLUDE_PATHS:
        path = root / include
        if not path.exists():
            continue
        if path.is_file():
            relative = _as_posix(path.relative_to(root))
            if not is_excluded(relative):
                yield path
            continue
        for file_path in path.rglob("*"):
            if file_path.is_file():
                relative = _as_posix(file_path.relative_to(root))
                if not is_excluded(relative):
                    yield file_path


def build_beta_package(output_dir: str | Path | None = None, root: Path = ROOT) -> dict:
    output = Path(output_dir) if output_dir else OUTPUT_DIR
    output.mkdir(parents=True, exist_ok=True)
    version = _version()
    zip_path = output / f"velaflow_closed_beta_{version}.zip"
    files = sorted(set(iter_beta_files(root)), key=lambda item: _as_posix(item.relative_to(root)))
    forbidden = [_as_posix(path.relative_to(root)) for path in files if is_excluded(_as_posix(path.relative_to(root)))]
    if forbidden:
        raise RuntimeError(f"Excluded files selected for beta package: {forbidden}")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            zf.write(file_path, _as_posix(file_path.relative_to(root)))
    manifest = {
        "package": str(zip_path),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "file_count": len(files),
        "include_paths": INCLUDE_PATHS,
        "exclude_patterns": EXCLUDE_PATTERNS,
        "contains_project_data": any(_as_posix(path.relative_to(root)).startswith("project_data/") for path in files),
        "contains_env": any(_as_posix(path.relative_to(root)) == ".env" for path in files),
        "contains_venv": any(".venv" in _as_posix(path.relative_to(root)).split("/") for path in files),
    }
    manifest_path = zip_path.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "package": str(zip_path), "manifest": str(manifest_path), "file_count": len(files)}


if __name__ == "__main__":
    print(json.dumps(build_beta_package(), ensure_ascii=False, indent=2))
