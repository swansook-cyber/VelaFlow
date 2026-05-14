from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

from core.project_io import safe_name


ROOT = Path(__file__).resolve().parents[1]
APP_FOLDER_SLUG = "velaflow"
PROJECT_DATA_ROOT = ROOT / "project_data"
LEGACY_PROJECTS_ROOT = PROJECT_DATA_ROOT / "projects"

WORKFLOW_PROJECT_ROOTS: Dict[str, Path] = {
    "song": PROJECT_DATA_ROOT / "music",
    "music_pipeline": PROJECT_DATA_ROOT / "music",
    "seller": PROJECT_DATA_ROOT / "seller",
    "podcast": PROJECT_DATA_ROOT / "podcast",
    "clips": PROJECT_DATA_ROOT / "clips",
    "mv": PROJECT_DATA_ROOT / "mv",
    "legacy": LEGACY_PROJECTS_ROOT,
}


def workflow_project_root(workflow_type: str | None = None) -> Path:
    return WORKFLOW_PROJECT_ROOTS.get(str(workflow_type or "").strip(), LEGACY_PROJECTS_ROOT)


def project_folder(project_name: str, workflow_type: str | None = None) -> Path:
    return workflow_project_root(workflow_type) / safe_name(project_name or "project")


def project_search_roots() -> List[Path]:
    roots: List[Path] = []
    for root in list(WORKFLOW_PROJECT_ROOTS.values()) + [LEGACY_PROJECTS_ROOT]:
        if root not in roots:
            roots.append(root)
    return roots


def candidate_project_folders(project_name: str) -> List[Path]:
    name = safe_name(project_name or "project")
    return [root / name for root in project_search_roots()]


def resolve_project_folder(project_name: str, workflow_type: str | None = None) -> Path:
    preferred = project_folder(project_name, workflow_type)
    if preferred.exists():
        return preferred
    for candidate in candidate_project_folders(project_name):
        if candidate.exists():
            return candidate
    return preferred


def iter_project_folders() -> Iterable[Path]:
    seen = set()
    for root in project_search_roots():
        root.mkdir(parents=True, exist_ok=True)
        for folder in root.iterdir():
            if not folder.is_dir():
                continue
            resolved = folder.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield folder


def is_project_data_child(path: Path) -> bool:
    try:
        resolved = path.resolve()
        return any(resolved.parent == root.resolve() for root in project_search_roots())
    except Exception:
        return False
