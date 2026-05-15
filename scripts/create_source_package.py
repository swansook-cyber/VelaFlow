from __future__ import annotations

import argparse
import fnmatch
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "source_packages"
INCLUDE_PATHS = [
    "app",
    "core",
    "providers",
    "config",
    "docs",
    "tests",
    "README.md",
    "MASTER_CONTEXT.md",
    "CHANGELOG.md",
    "TODO_NEXT.md",
    "requirements.txt",
    ".env.example",
    "Procfile",
    "railway.json",
    "nixpacks.toml",
    "runtime.txt",
    "run_velaflow.bat",
]
FORBIDDEN_PATTERNS = [
    ".env",
    ".env.*",
    ".venv/*",
    "venv/*",
    "*/__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "outputs/cache/*",
    "outputs/renders/_scene_cache/*",
    "outputs/renders/*/_scene_cache/*",
    "outputs/renders/*/temp/*",
    "outputs/renders/*.mp4",
    "outputs/renders/*.mov",
    "outputs/renders/*.mkv",
    "outputs/renders/*.avi",
    "outputs/renders/*.wav",
    "outputs/renders/*.mp3",
]


def _as_posix(path: Path) -> str:
    return path.as_posix()


def is_forbidden(relative_path: str) -> bool:
    value = relative_path.replace("\\", "/")
    if value == ".env.example":
        return False
    parts = value.split("/")
    if ".venv" in parts or "venv" in parts or "__pycache__" in parts:
        return True
    if value == ".env" or (value.startswith(".env.") and value != ".env.example"):
        return True
    if value.endswith((".pyc", ".pyo", ".pyd")):
        return True
    if value.startswith("outputs/cache/") or "/_scene_cache/" in value or "/temp/" in value:
        return True
    if value.startswith("outputs/renders/") and value.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".wav", ".mp3")):
        return True
    return any(fnmatch.fnmatch(value, pattern) for pattern in FORBIDDEN_PATTERNS)


def iter_source_files(root: Path = ROOT) -> Iterable[Path]:
    for include in INCLUDE_PATHS:
        path = root / include
        if not path.exists():
            continue
        if path.is_file():
            relative = _as_posix(path.relative_to(root))
            if not is_forbidden(relative):
                yield path
            continue
        for file_path in path.rglob("*"):
            if file_path.is_file():
                relative = _as_posix(file_path.relative_to(root))
                if not is_forbidden(relative):
                    yield file_path


def create_source_package(output_dir: str | Path | None = None, root: Path = ROOT) -> dict:
    output = Path(output_dir) if output_dir else DEFAULT_OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = output / f"velaflow_source_v7_8_2_{stamp}.zip"
    files = sorted(set(iter_source_files(root)), key=lambda item: _as_posix(item.relative_to(root)))
    forbidden = [_as_posix(path.relative_to(root)) for path in files if is_forbidden(_as_posix(path.relative_to(root)))]
    if forbidden:
        raise RuntimeError(f"Forbidden files selected for package: {forbidden}")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            zf.write(file_path, _as_posix(file_path.relative_to(root)))
    manifest = {
        "package": str(zip_path),
        "file_count": len(files),
        "included_roots": INCLUDE_PATHS,
        "forbidden_patterns": FORBIDDEN_PATTERNS,
    }
    manifest_path = zip_path.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "package": str(zip_path), "manifest": str(manifest_path), "file_count": len(files)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a VelaFlow source-only package.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT), help="Folder for the source package zip.")
    args = parser.parse_args()
    result = create_source_package(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
