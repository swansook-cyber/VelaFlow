from __future__ import annotations

import json
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.beta_testing import export_beta_report, load_beta_session
from core.production_audit import export_project_audit, run_full_project_audit
from core.project_io import safe_name
from core.render_recovery import export_diagnostic_bundle
from core.version import identity_payload


ROOT = Path(__file__).resolve().parents[1]
STABLE_FREEZE_NAME = "VelaFlow V7.7 Stable Candidate 1"
STABLE_POLICY = "Core pipeline is frozen after this snapshot except for bug fixes."


READY_FEATURES = [
    "Song Studio and MV Director workflow",
    "Character Studio and character lock prompt injection",
    "Image Lab, Image Review, approval/reject/regenerate/version flow",
    "Video Lab with manual/offline placeholder providers",
    "Queue Monitor and persistent job state",
    "Render Lab with FFmpeg render pipeline, subtitles, motion, profiles, and recovery tools",
    "Clip Factory, Marketing Package, and Final Package exports",
    "Asset Manager, System Logs, System Health, Safe Mode, and diagnostics",
    "Beta Test Mode with ratings, issue log, reports, and stable candidate marker",
]

NOT_DONE = [
    "No online license activation, payment, or subscription system",
    "No cloud sync, team accounts, or collaborative editing",
    "No full AI video generation pipeline by default",
    "No auto upload to social platforms",
    "No installer, EXE launcher, or hidden CMD packaging yet",
]


def stable_build_summary(project: Dict[str, Any], beta_session_id: str = "") -> Dict[str, Any]:
    audit = run_full_project_audit(project).get("data", {})
    issues = _known_issues(project, beta_session_id, audit)
    return {
        **identity_payload(),
        "freeze_name": STABLE_FREEZE_NAME,
        "freeze_policy": STABLE_POLICY,
        "project": project.get("title", "project"),
        "audit_score": audit.get("score", 0),
        "audit_verdict": audit.get("verdict", ""),
        "features_ready": READY_FEATURES,
        "known_issues": issues,
        "not_done": NOT_DONE,
    }


def create_stable_candidate_snapshot(
    project: Dict[str, Any],
    beta_session_id: str = "",
    stable_name: str = STABLE_FREEZE_NAME,
    output_dir: str | Path | None = None,
    include_smoke_test: bool = False,
    python_executable: str | None = None,
) -> Dict[str, Any]:
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = safe_name(project.get("title", "project"))
        root = Path(output_dir) if output_dir else ROOT / "outputs" / "stable_candidates" / project_name
        snapshot_dir = root / f"stable_candidate_{stamp}"
        evidence_dir = snapshot_dir / "release_evidence"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        evidence_dir.mkdir(parents=True, exist_ok=True)

        audit_export = export_project_audit(project, evidence_dir / "audit")
        diagnostic = export_diagnostic_bundle(project, evidence_dir / "diagnostics")
        beta_report = _export_beta_evidence(project, beta_session_id, evidence_dir / "beta_report")
        smoke = _run_smoke_test(evidence_dir / "smoke_test", python_executable) if include_smoke_test else _smoke_not_run()
        audit_data = audit_export.get("data", {}).get("audit", {})

        manifest = {
            **identity_payload(),
            "freeze_name": stable_name,
            "freeze_policy": STABLE_POLICY,
            "project": project.get("title", "project"),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "snapshot_dir": str(snapshot_dir),
            "features_ready": READY_FEATURES,
            "known_issues": _known_issues(project, beta_session_id, audit_data),
            "not_done": NOT_DONE,
            "evidence": {
                "diagnostic_bundle": diagnostic.get("data", {}).get("path", ""),
                "audit_json": audit_export.get("data", {}).get("json", ""),
                "audit_markdown": audit_export.get("data", {}).get("markdown", ""),
                "beta_report_json": beta_report.get("data", {}).get("json", ""),
                "beta_report_markdown": beta_report.get("data", {}).get("markdown", ""),
                "smoke_test_json": smoke.get("data", {}).get("path", ""),
                "smoke_test_ok": smoke.get("ok", False),
            },
        }

        (snapshot_dir / "project_snapshot.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
        (snapshot_dir / "stable_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (snapshot_dir / "STABLE_BUILD.md").write_text(_stable_markdown(manifest), encoding="utf-8")
        zip_path = _zip_snapshot(snapshot_dir)

        project.setdefault("release", {})["stable_candidate_snapshot"] = str(snapshot_dir)
        project["release"]["stable_candidate_name"] = stable_name
        project["release"]["stable_candidate_zip"] = str(zip_path)
        project["release"]["freeze_policy"] = STABLE_POLICY
        return {
            "ok": True,
            "message": "Stable candidate snapshot created",
            "data": {"snapshot_dir": str(snapshot_dir), "zip": str(zip_path), "manifest": manifest, "project": project},
            "error": "",
        }
    except Exception as exc:
        return {"ok": False, "message": "Stable candidate snapshot failed", "data": {}, "error": str(exc)}


def _known_issues(project: Dict[str, Any], beta_session_id: str, audit_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for item in audit_data.get("fix_first", []) or []:
        issues.append(
            {
                "source": "production_audit",
                "area": item.get("area", ""),
                "severity": item.get("level", "WARN"),
                "description": item.get("fix") or item.get("message", ""),
                "status": "OPEN",
            }
        )
    if beta_session_id:
        loaded = load_beta_session(project, beta_session_id)
        session = loaded.get("data", {}).get("session", {}) if loaded.get("ok") else {}
        for issue in session.get("issues", []) or []:
            if issue.get("status") != "DONE":
                issues.append({"source": "beta_test", **issue})
    if not issues:
        issues.append({"source": "release", "area": "General", "severity": "INFO", "description": "No open known issues recorded.", "status": "INFO"})
    return issues


def _export_beta_evidence(project: Dict[str, Any], beta_session_id: str, output_dir: Path) -> Dict[str, Any]:
    if not beta_session_id:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "beta_report_not_selected.json"
        path.write_text(json.dumps({"ok": False, "message": "No beta session selected"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": False, "message": "No beta session selected", "data": {"json": str(path), "markdown": ""}, "error": "missing_beta_session"}
    return export_beta_report(project, beta_session_id, output_dir)


def _run_smoke_test(output_dir: Path, python_executable: str | None = None) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    exe = python_executable or sys.executable
    completed = subprocess.run(
        [exe, str(ROOT / "tests" / "smoke_test.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    payload = {
        "ok": completed.returncode == 0,
        "command": [exe, str(ROOT / "tests" / "smoke_test.py")],
        "returncode": completed.returncode,
        "duration_seconds": round(time.time() - started, 2),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    path = output_dir / "smoke_test_result.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": payload["ok"], "message": "Smoke test completed", "data": {"path": str(path), "result": payload}, "error": "" if payload["ok"] else "smoke_test_failed"}


def _smoke_not_run() -> Dict[str, Any]:
    return {"ok": True, "message": "Smoke test not run in snapshot request", "data": {"path": "", "result": {"ok": None, "status": "not_run"}}, "error": ""}


def _zip_snapshot(snapshot_dir: Path) -> Path:
    zip_path = snapshot_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in snapshot_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(snapshot_dir))
    return zip_path


def _stable_markdown(manifest: Dict[str, Any]) -> str:
    lines = [
        f"# {manifest.get('freeze_name', STABLE_FREEZE_NAME)}",
        "",
        f"Generated by: {manifest.get('generated_by', 'VelaFlow')}",
        f"App version: {manifest.get('app_version', '')}",
        f"Build version: {manifest.get('build_version', '')}",
        f"Created: {manifest.get('created_at', '')}",
        f"Project: {manifest.get('project', '')}",
        "",
        "## Freeze Policy",
        "",
        manifest.get("freeze_policy", STABLE_POLICY),
        "",
        "## Features Ready",
    ]
    lines.extend(f"- {item}" for item in manifest.get("features_ready", []) or [])
    lines += ["", "## Known Issues"]
    lines.extend(f"- [{item.get('severity')}] {item.get('area')}: {item.get('description')}" for item in manifest.get("known_issues", []) or [])
    lines += ["", "## Not Done"]
    lines.extend(f"- {item}" for item in manifest.get("not_done", []) or [])
    lines += ["", "## Release Evidence"]
    for key, value in (manifest.get("evidence", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"
