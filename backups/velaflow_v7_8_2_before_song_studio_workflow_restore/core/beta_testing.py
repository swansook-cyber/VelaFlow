from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.production_audit import run_full_project_audit
from core.project_io import safe_name
from core.version import identity_payload


ROOT = Path(__file__).resolve().parents[1]
BETA_ROOT = ROOT / "project_data" / "beta_tests"

BETA_RATING_AREAS = ["Song", "Storyboard", "Image", "Motion", "Subtitle", "Render", "Clips", "Marketing"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _project_dir(project: Dict[str, Any]) -> Path:
    return BETA_ROOT / safe_name(project.get("title", "project"))


def _session_path(project: Dict[str, Any], session_id: str) -> Path:
    return _project_dir(project) / f"{session_id}.json"


def new_beta_session(project: Dict[str, Any], template: str = "", render_profile: str = "", notes: str = "") -> Dict[str, Any]:
    session_id = datetime.now().strftime("beta_%Y%m%d_%H%M%S")
    session = {
        **identity_payload(),
        "session_id": session_id,
        "project": project.get("title", "project"),
        "song_title": (project.get("song", {}) or {}).get("title") or project.get("title", "project"),
        "template": template or (project.get("settings", {}) or {}).get("template", ""),
        "render_profile": render_profile or (project.get("settings", {}) or {}).get("render_profile", "Draft"),
        "created_at": _now(),
        "updated_at": _now(),
        "ratings": {area: 0 for area in BETA_RATING_AREAS},
        "issues": [],
        "notes": notes,
        "stable_candidate": False,
        "stable_marked_at": "",
        "audit_score": run_full_project_audit(project).get("data", {}).get("score", 0),
    }
    save_beta_session(project, session)
    return {"ok": True, "message": "Beta test session created", "data": {"session": session, "path": str(_session_path(project, session_id))}, "error": ""}


def save_beta_session(project: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    session_id = session.get("session_id") or datetime.now().strftime("beta_%Y%m%d_%H%M%S")
    session["session_id"] = session_id
    session["updated_at"] = _now()
    folder = _project_dir(project)
    folder.mkdir(parents=True, exist_ok=True)
    path = _session_path(project, session_id)
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "message": "Beta test session saved", "data": {"path": str(path), "session": session}, "error": ""}


def list_beta_sessions(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    folder = _project_dir(project)
    if not folder.exists():
        return []
    rows = []
    for path in folder.glob("beta_*.json"):
        try:
            session = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        rows.append(
            {
                "session_id": session.get("session_id", path.stem),
                "song_title": session.get("song_title", ""),
                "template": session.get("template", ""),
                "render_profile": session.get("render_profile", ""),
                "average_rating": average_beta_rating(session),
                "issues": len(session.get("issues", []) or []),
                "stable_candidate": bool(session.get("stable_candidate")),
                "updated_at": session.get("updated_at", ""),
                "path": str(path),
            }
        )
    return sorted(rows, key=lambda item: item.get("updated_at", ""), reverse=True)


def load_beta_session(project: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    path = _session_path(project, session_id)
    if not path.exists():
        return {"ok": False, "message": "Beta session not found", "data": {}, "error": "missing_session"}
    session = json.loads(path.read_text(encoding="utf-8"))
    return {"ok": True, "message": "Beta session loaded", "data": {"session": session, "path": str(path)}, "error": ""}


def update_beta_ratings(project: Dict[str, Any], session_id: str, ratings: Dict[str, int]) -> Dict[str, Any]:
    loaded = load_beta_session(project, session_id)
    if not loaded.get("ok"):
        return loaded
    session = loaded["data"]["session"]
    current = session.setdefault("ratings", {})
    for area in BETA_RATING_AREAS:
        current[area] = max(0, min(10, int(ratings.get(area, current.get(area, 0)) or 0)))
    return save_beta_session(project, session)


def add_beta_issue(project: Dict[str, Any], session_id: str, area: str, severity: str, description: str, status: str = "OPEN") -> Dict[str, Any]:
    loaded = load_beta_session(project, session_id)
    if not loaded.get("ok"):
        return loaded
    session = loaded["data"]["session"]
    issue = {
        "id": f"ISSUE-{len(session.get('issues', []) or []) + 1:03d}",
        "area": area,
        "severity": severity,
        "description": description,
        "status": status,
        "created_at": _now(),
    }
    session.setdefault("issues", []).append(issue)
    return save_beta_session(project, session)


def average_beta_rating(session: Dict[str, Any]) -> float:
    ratings = session.get("ratings", {}) or {}
    values = [int(ratings.get(area, 0) or 0) for area in BETA_RATING_AREAS]
    return round(sum(values) / len(values), 2) if values else 0.0


def beta_test_checklist(project: Dict[str, Any], session: Dict[str, Any] | None = None) -> Dict[str, Any]:
    audit = run_full_project_audit(project).get("data", {})
    session = session or {}
    ratings = session.get("ratings", {}) or {}
    issues = session.get("issues", []) or []
    checks = [
        {"item": "Song tested", "ok": ratings.get("Song", 0) > 0},
        {"item": "Storyboard tested", "ok": ratings.get("Storyboard", 0) > 0},
        {"item": "Images reviewed", "ok": ratings.get("Image", 0) > 0},
        {"item": "Motion reviewed", "ok": ratings.get("Motion", 0) > 0},
        {"item": "Subtitle reviewed", "ok": ratings.get("Subtitle", 0) > 0},
        {"item": "Render reviewed", "ok": ratings.get("Render", 0) > 0},
        {"item": "Clips reviewed", "ok": ratings.get("Clips", 0) > 0},
        {"item": "Marketing reviewed", "ok": ratings.get("Marketing", 0) > 0},
        {"item": "No critical open issues", "ok": not any(item.get("severity") == "CRITICAL" and item.get("status") != "DONE" for item in issues)},
        {"item": "Production audit acceptable", "ok": audit.get("score", 0) >= 70},
    ]
    return {"ok": True, "message": "Beta checklist created", "data": {"checks": checks, "audit_score": audit.get("score", 0)}, "error": ""}


def compare_render_versions(render_a: str | Path, render_b: str | Path) -> Dict[str, Any]:
    a = Path(render_a)
    b = Path(render_b)
    rows = []
    for filename in ["render_manifest.json", "timeline.json", "final_16x9.mp4", "final_9x16.mp4", "final_1x1.mp4"]:
        pa = a / filename
        pb = b / filename
        rows.append(
            {
                "file": filename,
                "a_exists": pa.exists(),
                "b_exists": pb.exists(),
                "a_size": pa.stat().st_size if pa.exists() else 0,
                "b_size": pb.stat().st_size if pb.exists() else 0,
                "size_delta": (pb.stat().st_size if pb.exists() else 0) - (pa.stat().st_size if pa.exists() else 0),
            }
        )
    return {"ok": True, "message": "Render versions compared", "data": {"render_a": str(a), "render_b": str(b), "rows": rows}, "error": ""}


def mark_stable_candidate(project: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    loaded = load_beta_session(project, session_id)
    if not loaded.get("ok"):
        return loaded
    session = loaded["data"]["session"]
    session["stable_candidate"] = True
    session["stable_marked_at"] = _now()
    project.setdefault("release", {})["stable_candidate_session"] = session_id
    project["release"]["stable_candidate_marked_at"] = session["stable_marked_at"]
    saved = save_beta_session(project, session)
    saved["data"]["project"] = project
    return saved


def export_beta_report(project: Dict[str, Any], session_id: str, output_dir: str | Path | None = None) -> Dict[str, Any]:
    loaded = load_beta_session(project, session_id)
    if not loaded.get("ok"):
        return loaded
    session = loaded["data"]["session"]
    output = Path(output_dir) if output_dir else ROOT / "outputs" / "beta_reports" / safe_name(project.get("title", "project"))
    output.mkdir(parents=True, exist_ok=True)
    base = output / f"{session_id}_beta_report"
    checklist = beta_test_checklist(project, session).get("data", {})
    payload = {"project": project.get("title", "project"), "session": session, "checklist": checklist}
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_beta_markdown(payload), encoding="utf-8")
    return {"ok": True, "message": "Beta report exported", "data": {"json": str(json_path), "markdown": str(md_path), "payload": payload}, "error": ""}


def _beta_markdown(payload: Dict[str, Any]) -> str:
    session = payload.get("session", {})
    lines = [
        f"# Beta Test Report: {payload.get('project', 'project')}",
        "",
        f"Session: {session.get('session_id', '')}",
        f"Song: {session.get('song_title', '')}",
        f"Template: {session.get('template', '')}",
        f"Render Profile: {session.get('render_profile', '')}",
        f"Average Rating: {average_beta_rating(session)}/10",
        f"Stable Candidate: {bool(session.get('stable_candidate'))}",
        "",
        "## Ratings",
    ]
    for area, value in (session.get("ratings", {}) or {}).items():
        lines.append(f"- {area}: {value}/10")
    lines += ["", "## Issues"]
    for issue in session.get("issues", []) or []:
        lines.append(f"- [{issue.get('severity')}] {issue.get('area')} / {issue.get('status')}: {issue.get('description')}")
    if not session.get("issues"):
        lines.append("- No issues logged.")
    lines += ["", "## Checklist"]
    for item in payload.get("checklist", {}).get("checks", []) or []:
        mark = "OK" if item.get("ok") else "TODO"
        lines.append(f"- {mark} {item.get('item')}")
    return "\n".join(lines) + "\n"
