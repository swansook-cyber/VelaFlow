"""Per-scene media production and review; no rendering or automatic provider calls."""
from __future__ import annotations

import json
import hashlib
import io
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from PIL import Image

from providers.image_ai import generate_image_with_diagnostics, validate_image_file
from providers.video_ai import generate_video_shot


IMAGE_PROVIDERS = {"openai_images", "gemini_image"}
VIDEO_PROVIDERS = {"gemini_veo"}
ALLOWED_SUFFIXES = {"image": {".jpg", ".jpeg", ".png", ".webp"}, "video": {".mp4"}}
MAX_RETRIES = 3
MAX_REFERENCE_BYTES = 20 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(path: str | Path) -> str:
    hasher = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(block)
        return hasher.hexdigest()
    except OSError:
        return ""


def load_character_references(record: dict[str, Any], project_folder: str | Path) -> dict[str, Any]:
    """Validate a saved reference version and return its exact image bytes."""
    try:
        root = Path(project_folder).resolve(strict=True)
        if not record or record.get("reference_asset_status") not in {"Imported / Pending Technical Validation", "Validated"}:
            raise ValueError("Select an imported character reference version.")
        if record.get("creative_design_status") != "Approved by User":
            raise ValueError("Character identity is not approved by the user.")
        images = record.get("images") or {}
        if not 1 <= len(images) <= 4:
            raise ValueError("Choose one to four approved master views for this workflow.")
        payload = []
        for name, metadata in images.items():
            path = Path(str(metadata.get("path") or "")).resolve(strict=True)
            if not path.is_relative_to(root) or path.suffix.lower() != ".png" or path.name != name:
                raise ValueError("Reference path is outside this project or has an unexpected type.")
            data = path.read_bytes()
            if not 0 < len(data) <= MAX_REFERENCE_BYTES or len(data) != metadata.get("size_bytes"):
                raise ValueError("Reference size does not match the saved version.")
            if hashlib.sha256(data).hexdigest() != metadata.get("sha256"):
                raise ValueError("Reference SHA-256 does not match the saved version.")
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                if image.format != "PNG" or image.size != (metadata.get("width"), metadata.get("height")):
                    raise ValueError("Reference MIME or dimensions do not match the saved version.")
            payload.append({"filename": name, "mime_type": "image/png", "content": data,
                            "sha256": metadata["sha256"]})
        return {"ok": True, "images": payload, "error": ""}
    except (OSError, ValueError, TypeError) as exc:
        return {"ok": False, "images": [], "error": str(exc) or "Reference validation failed."}


def _find(scenes: list[dict[str, Any]], scene_id: str) -> dict[str, Any] | None:
    return next((scene for scene in scenes if scene.get("scene_id") == scene_id), None)


def _production(scene: dict[str, Any]) -> dict[str, Any]:
    return scene.setdefault("production", {"assets": [], "attempts": [], "active_asset_id": "", "pending_attempt_id": "", "generation_status": "Not Started", "error_history": []})


def inspect_media(path: str | Path, kind: str) -> dict[str, Any]:
    source = Path(path)
    if kind not in ALLOWED_SUFFIXES or source.suffix.lower() not in ALLOWED_SUFFIXES[kind]:
        return {"ok": False, "error": "Unsupported image or video file type."}
    try:
        available = source.is_file() and source.stat().st_size > 0
    except OSError:
        available = False
    if not available:
        return {"ok": False, "error": "Media file is missing or empty."}
    if kind == "image":
        result = validate_image_file(source, expected_aspect_ratio="9:16")
        if not result.get("ok"):
            return {"ok": False, "error": "Image file cannot be read."}
        try:
            with Image.open(source) as image:
                actual = image.format
        except OSError:
            return {"ok": False, "error": "Image file cannot be read."}
        expected = "JPEG" if source.suffix.lower() in {".jpg", ".jpeg"} else "PNG" if source.suffix.lower() == ".png" else "WEBP"
        if actual != expected:
            return {"ok": False, "error": "Image content does not match its file type."}
        return {"ok": True, "kind": kind, "path": str(source), "file_type": source.suffix.lower(),
                "width": result["width"], "height": result["height"], "aspect_ratio": result["aspect_ratio"],
                "duration_seconds": 0.0, "size_bytes": result["file_size"]}
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name:stream=codec_type,width,height", "-of", "json", str(source)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        payload = json.loads(probe.stdout) if probe.returncode == 0 else {}
        container = str((payload.get("format") or {}).get("format_name") or "")
        video = next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"), {})
        width, height = int(video.get("width") or 0), int(video.get("height") or 0)
        duration = float((payload.get("format") or {}).get("duration") or 0)
        if "mp4" not in container and "mov" not in container:
            raise ValueError("unsupported container")
        if width < 1 or height < 1 or not 0 < duration < 3600:
            raise ValueError("invalid media metadata")
        return {"ok": True, "kind": kind, "path": str(source), "file_type": ".mp4", "width": width,
                "height": height, "aspect_ratio": round(width / height, 4), "duration_seconds": round(duration, 3),
                "size_bytes": source.stat().st_size}
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return {"ok": False, "error": "Video file cannot be read or FFprobe is unavailable."}


def _ready_scene(scenes: list[dict[str, Any]], scene_id: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str]:
    updated = deepcopy(scenes)
    scene = _find(updated, scene_id)
    if scene is None:
        return updated, None, "Scene was not found."
    if scene.get("approval_status") != "Approved":
        return updated, None, "Approve this storyboard scene before producing media."
    if _production(scene).get("pending_attempt_id"):
        return updated, None, "This scene already has a generation attempt in progress."
    return updated, scene, ""


def _asset_record(scene: dict[str, Any], metadata: dict[str, Any], *, provider: str, model: str = "",
                  prompt: str = "", reference: str = "", job_id: str = "", provider_status: str = "imported",
                  shot_duration: float = 0.0) -> dict[str, Any]:
    now = _now()
    return {
        "asset_id": uuid4().hex, "scene_id": scene["scene_id"], "scene_revision": int(scene["revision"]),
        "approved_storyboard_revision": int(scene["revision"]), "kind": metadata["kind"],
        "provider": provider, "model": model, "prompt_used": prompt, "reference_used": "",
        "reference_selected": reference,
        "reference_sent_to_provider": False, "job_id": job_id, "path": metadata["path"],
        "file_type": metadata["file_type"], "duration_seconds": metadata["duration_seconds"],
        "width": metadata["width"], "height": metadata["height"], "aspect_ratio": metadata["aspect_ratio"],
        "size_bytes": metadata["size_bytes"], "shot_duration_seconds": shot_duration,
        "provider_status": provider_status, "status": "Needs QC", "qc_result": {}, "qc_revision": 0,
        "estimated_cost": None, "actual_cost": None, "created_at": now, "updated_at": now,
    }


def import_scene_media(scenes: list[dict[str, Any]], scene_id: str, filename: str, payload: bytes,
                       output_dir: str | Path) -> dict[str, Any]:
    updated, scene, error = _ready_scene(scenes, scene_id)
    if error:
        return {"ok": False, "error": error}
    suffix = Path(filename).suffix.lower()
    kind = "image" if suffix in ALLOWED_SUFFIXES["image"] else "video" if suffix == ".mp4" else ""
    if not kind or not payload or len(payload) > 250 * 1024 * 1024:
        return {"ok": False, "error": "Choose a supported, nonempty image or MP4 under 250 MB."}
    folder = Path(output_dir) / scene_id
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=folder, suffix=suffix, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
    try:
        inspected = inspect_media(temporary, kind)
        if not inspected.get("ok"):
            return inspected
        destination = folder / f"import_{uuid4().hex}{suffix}"
        with destination.open("xb") as handle:
            handle.write(payload)
        inspected["path"] = str(destination)
        record = _asset_record(scene, inspected, provider="external_import", prompt=str(scene.get("visual_prompt") or ""),
                               reference=str(scene.get("reference_asset") or ""),
                               shot_duration=min(8.0, float(inspected["duration_seconds"])) if kind == "video" else 0.0)
        _production(scene)["assets"].append(record)
        scene["asset_status"] = "Needs QC"
        return {"ok": True, "scenes": updated, "asset_id": record["asset_id"]}
    finally:
        temporary.unlink(missing_ok=True)


def begin_generation(scenes: list[dict[str, Any]], scene_id: str, kind: str, provider: str, *,
                     confirmed: bool, configured: bool, shot_duration: float = 5.0,
                     reference_record: dict[str, Any] | None = None,
                     reference_root: str | Path | None = None) -> dict[str, Any]:
    updated, scene, error = _ready_scene(scenes, scene_id)
    if error:
        return {"ok": False, "error": error}
    if not confirmed or not configured:
        return {"ok": False, "error": "Confirm the possible provider charge and configure its API key first."}
    if provider not in (IMAGE_PROVIDERS if kind == "image" else VIDEO_PROVIDERS if kind == "video" else set()):
        return {"ok": False, "error": "This provider is not supported for scene generation."}
    production = _production(scene)
    if production["attempts"] and production.get("generation_status") != "Retry Requested":
        return {"ok": False, "error": "Choose Retry for this scene before another paid generation attempt."}
    if production.get("retry_count", scene.get("retry_count", 0)) > MAX_RETRIES:
        return {"ok": False, "error": "Retry limit reached for this scene."}
    prompt = str(scene.get("visual_prompt") or "").strip()
    if not prompt:
        return {"ok": False, "error": "Add a visual prompt before generating this scene."}
    if kind == "video" and not 3 <= shot_duration <= 8:
        return {"ok": False, "error": "Veo shots must be 3–8 seconds; a scene may use multiple shots or a hold."}
    previous = production["attempts"][-1] if production["attempts"] else {}
    prior_reference = previous.get("reference_snapshot") or {}
    if prior_reference and reference_record and (
        reference_record.get("source_zip_sha256") != prior_reference.get("source_zip_sha256")
        or reference_record.get("version") != prior_reference.get("version")
        or [item.get("sha256") for item in (reference_record.get("images") or {}).values()]
           != [item.get("sha256") for item in (prior_reference.get("images") or {}).values()]
    ):
        return {"ok": False, "error": "Retry must use the same character reference version."}
    reference_snapshot = deepcopy(prior_reference)
    if reference_record and not reference_snapshot:
        if kind != "image" or provider != "openai_images" or not reference_root:
            return {"ok": False, "error": "This provider cannot send character reference images."}
        checked = load_character_references(reference_record, reference_root)
        if not checked["ok"]:
            return {"ok": False, "error": checked["error"]}
        reference_snapshot = deepcopy(reference_record)
        reference_snapshot["project_folder"] = str(Path(reference_root).resolve())
    if reference_snapshot:
        if kind != "image" or provider != "openai_images":
            return {"ok": False, "error": "Retry must keep the original reference-aware provider."}
        checked = load_character_references(reference_snapshot, reference_snapshot["project_folder"])
        if not checked["ok"]:
            return {"ok": False, "error": checked["error"]}
        prompt += " Use the supplied character reference images to keep the same face, hairstyle, and recognizable identity. Do not invent a different person."
        if scene_id == "scene_010":
            prompt += " Wardrobe Look B: charcoal T-shirt, dark denim jacket, black jeans; intimate band rehearsal. Compose as a 16:9 cinematic frame."
    attempt_id = uuid4().hex
    attempt = {"attempt_id": attempt_id, "scene_id": scene_id, "scene_revision": int(scene["revision"]),
               "kind": kind, "provider": provider, "prompt_used": prompt,
               "reference_used": "", "reference_selected": str(scene.get("reference_asset") or ""),
               "reference_snapshot": reference_snapshot,
               "shot_duration_seconds": shot_duration,
               "status": "Running", "job_id": "", "error": "", "started_at": _now(), "updated_at": _now(),
               "estimated_cost": None, "actual_cost": None}
    production["attempts"].append(attempt)
    production["pending_attempt_id"] = attempt_id
    production["generation_status"] = "Running"
    return {"ok": True, "scenes": updated, "attempt_id": attempt_id}


def finish_generation(scenes: list[dict[str, Any]], scene_id: str, attempt_id: str, result: dict[str, Any],
                      output_dir: str | Path) -> dict[str, Any]:
    updated = deepcopy(scenes)
    scene = _find(updated, scene_id)
    if scene is None:
        return {"ok": False, "error": "Scene was not found."}
    production = _production(scene)
    attempt = next((row for row in production["attempts"] if row["attempt_id"] == attempt_id), None)
    if attempt is None or production.get("pending_attempt_id") != attempt_id:
        return {"ok": False, "error": "Generation attempt is no longer active."}
    data = result.get("data") or {}
    provider_ok = bool(result.get("ok")) and not data.get("fallback_used")
    if attempt["kind"] == "video":
        provider_ok = provider_ok and bool(data.get("real_ai_video_used")) and data.get("provider_status") == "complete"
    else:
        provider_ok = provider_ok and data.get("provider_used") == attempt["provider"]
    reference_snapshot = attempt.get("reference_snapshot") or {}
    if reference_snapshot:
        expected_hashes = [item["sha256"] for item in reference_snapshot["images"].values()]
        provider_ok = provider_ok and data.get("reference_sent_to_provider") is True and data.get("reference_sha256s") == expected_hashes
    path = Path(str(data.get("path") or ""))
    in_folder = path.is_file() and path.resolve().parent == (Path(output_dir) / scene_id).resolve()
    inspected = inspect_media(path, attempt["kind"]) if provider_ok and in_folder else {"ok": False}
    current_revision = int(scene["revision"]) == attempt["scene_revision"] and scene.get("approval_status") == "Approved"
    production["pending_attempt_id"] = ""
    attempt["job_id"] = str(data.get("job_id") or "")
    attempt["updated_at"] = _now()
    if not provider_ok or not in_folder or not inspected.get("ok") or not current_revision:
        attempt["status"] = "Failed"
        attempt["error"] = "scene_revision_changed" if not current_revision else (
            str(result.get("error") or "provider_failed_or_invalid_media")
            if str(result.get("error") or "") in {"reference_validation_failed", "reference_unsupported", "validation_failed"}
            else "provider_failed_or_invalid_media")
        production["generation_status"] = "Failed"
        production["error_history"].append({"attempt_id": attempt_id, "error": attempt["error"], "at": _now()})
        return {"ok": False, "error": attempt["error"], "scenes": updated}
    attempt["status"] = "Succeeded"
    production["generation_status"] = "Asset Ready"
    actual_prompt = str(data.get("prompt") or (data.get("payload") or {}).get("prompt") or attempt["prompt_used"])
    record = _asset_record(scene, inspected, provider=attempt["provider"],
                           model=str(data.get("actual_model") or data.get("model") or (data.get("payload") or {}).get("model") or ""),
                           prompt=actual_prompt, reference=attempt["reference_selected"], job_id=attempt["job_id"],
                           provider_status="complete", shot_duration=attempt["shot_duration_seconds"])
    if reference_snapshot:
        record.update({"reference_used": reference_snapshot.get("character_name", ""),
                       "reference_selected": reference_snapshot.get("version", ""),
                       "reference_version": reference_snapshot.get("version", ""),
                       "reference_sha256s": data["reference_sha256s"],
                       "reference_sent_to_provider": True})
    production["assets"].append(record)
    scene["asset_status"] = "Needs QC"
    return {"ok": True, "scenes": updated, "asset_id": record["asset_id"]}


def run_generation(scenes: list[dict[str, Any]], scene_id: str, attempt_id: str, output_dir: str | Path,
                   settings: dict[str, Any], *, image_generator: Callable[..., dict[str, Any]] = generate_image_with_diagnostics,
                   video_generator: Callable[..., dict[str, Any]] = generate_video_shot) -> dict[str, Any]:
    scene = _find(scenes, scene_id)
    attempt = next((row for row in _production(scene)["attempts"] if row["attempt_id"] == attempt_id), None) if scene else None
    if attempt is None or _production(scene).get("pending_attempt_id") != attempt_id:
        return {"ok": False, "error": "Generation attempt is no longer active."}
    if attempt["kind"] == "image" and not settings.get("openai_api_key" if attempt["provider"] == "openai_images" else "gemini_api_key"):
        return finish_generation(scenes, scene_id, attempt_id, {"ok": False}, output_dir)
    if attempt["kind"] == "video" and not settings.get("gemini_api_key"):
        return finish_generation(scenes, scene_id, attempt_id, {"ok": False}, output_dir)
    reference_snapshot = attempt.get("reference_snapshot") or {}
    reference_images = []
    if reference_snapshot:
        checked = load_character_references(reference_snapshot, reference_snapshot.get("project_folder", ""))
        if not checked["ok"]:
            return finish_generation(scenes, scene_id, attempt_id, {"ok": False, "error": "reference_validation_failed"}, output_dir)
        reference_images = checked["images"]
    folder = Path(output_dir) / scene_id
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"generated_{attempt_id}{'.jpg' if attempt['kind'] == 'image' else '.mp4'}"
    try:
        if attempt["kind"] == "image":
            result = image_generator(attempt["provider"], attempt["prompt_used"], str(destination),
                                     {**settings, "cache_enabled": False, "allow_env_key": False,
                                      "reference_images": reference_images,
                                      "target_aspect_ratio": settings.get("target_aspect_ratio", "9:16")})
        else:
            prompt = (f"{attempt['prompt_used']}. single continuous cinematic video shot, ultra realistic live-action, "
                      "vertical 9:16, natural human motion, cinematic camera movement, no text, no subtitles")
            result = video_generator(prompt, attempt["shot_duration_seconds"], destination, provider="gemini_veo",
                                     aspect_ratio="9:16", settings=settings)
    except Exception:
        result = {"ok": False, "error": "provider_exception"}
    return finish_generation(scenes, scene_id, attempt_id, result, output_dir)


def qc_scene_asset(scenes: list[dict[str, Any]], scene_id: str, asset_id: str,
                   target_aspect_ratio: str = "9:16") -> dict[str, Any]:
    updated = deepcopy(scenes)
    scene = _find(updated, scene_id)
    if scene is None:
        return {"ok": False, "error": "Scene was not found."}
    record = next((row for row in _production(scene)["assets"] if row["asset_id"] == asset_id), None)
    if record is None:
        return {"ok": False, "error": "Asset was not found for this scene."}
    media = inspect_media(record["path"], record["kind"])
    if target_aspect_ratio not in {"16:9", "9:16"}:
        return {"ok": False, "scenes": updated, "error": "Unsupported target aspect ratio."}
    revision_ok = record["scene_revision"] == int(scene["revision"]) and scene.get("approval_status") == "Approved"
    provider_ok = record["provider_status"] in {"complete", "imported"}
    if record["kind"] == "video":
        requested = float(record.get("shot_duration_seconds") or min(8, scene.get("duration_seconds") or 5))
        duration_ok = bool(media.get("ok")) and max(1, requested - 1.5) <= media["duration_seconds"] <= requested + 1.5
        resolution_ok = bool(media.get("ok")) and (media["width"] >= 720 and media["height"] >= 480 if target_aspect_ratio == "16:9" else media["width"] >= 480 and media["height"] >= 720)
    else:
        duration_ok = True
        resolution_ok = bool(media.get("ok")) and media["width"] >= 512 and media["height"] >= 512
    aspect_ok = bool(media.get("ok")) and abs(media["aspect_ratio"] - (16 / 9 if target_aspect_ratio == "16:9" else 9 / 16)) <= 0.09
    checks = {"readable_file": bool(media.get("ok")), "supported_type": bool(media.get("ok")),
              "duration": duration_ok, "resolution": resolution_ok, "aspect_ratio_9_16" if target_aspect_ratio == "9:16" else "aspect_ratio_16_9": aspect_ok,
              "provider_job": provider_ok, "current_scene_revision": revision_ok}
    passed = all(checks.values())
    if not revision_ok:
        return {"ok": False, "scenes": updated, "qc_result": {"passed": False, "checks": checks},
                "error": "This asset belongs to an older storyboard revision. Import it as a new candidate to review it again."}
    digest = _digest(record["path"]) if media.get("ok") else ""
    if not digest:
        checks["readable_file"] = False
        passed = False
    if record.get("status") == "Accepted":
        if passed and digest == record.get("qc_result", {}).get("file_sha256") and record.get("qc_result", {}).get("target_aspect_ratio", "9:16") == target_aspect_ratio:
            return {"ok": True, "scenes": updated, "qc_result": record["qc_result"], "error": ""}
        scene["qc_status"] = "Missing Asset" if not media.get("ok") else "Needs Review"
        scene["asset_status"] = "Missing" if not media.get("ok") else "Needs Review"
        return {"ok": False, "scenes": updated, "qc_result": {"passed": False, "checks": checks},
                "error": "The accepted file no longer passes QC. Its previous approval history was preserved."}
    record["qc_result"] = {"passed": passed, "checks": checks, "human_accepted": False,
                           "target_aspect_ratio": target_aspect_ratio,
                           "file_sha256": digest,
                           "review_notes": {"character": scene.get("character", ""), "costume": scene.get("costume", ""),
                                            "location": scene.get("location", ""), "visual_style": scene.get("visual_style", ""),
                                            "visual_match_automated": False}, "checked_at": _now()}
    record["qc_revision"] = int(scene["revision"]) if revision_ok else 0
    record["status"] = "QC Passed" if passed else "QC Failed"
    record["updated_at"] = _now()
    return {"ok": passed, "scenes": updated, "qc_result": record["qc_result"],
            "error": "Asset did not pass scene QC." if not passed else ""}


def accept_scene_asset(scenes: list[dict[str, Any]], scene_id: str, asset_id: str) -> dict[str, Any]:
    updated = deepcopy(scenes)
    scene = _find(updated, scene_id)
    if scene is None or scene.get("approval_status") != "Approved":
        return {"ok": False, "error": "Approve the current storyboard scene first."}
    production = _production(scene)
    record = next((row for row in production["assets"] if row["asset_id"] == asset_id), None)
    if not record or record.get("status") != "QC Passed" or record.get("qc_revision") != int(scene["revision"]):
        return {"ok": False, "error": "Run QC for the current scene revision before accepting this asset."}
    if not inspect_media(record["path"], record["kind"]).get("ok"):
        return {"ok": False, "error": "Asset is missing or unreadable."}
    if not record.get("qc_result", {}).get("file_sha256") or _digest(record["path"]) != record["qc_result"]["file_sha256"]:
        return {"ok": False, "error": "Asset changed after QC. Run file QC again."}
    record["status"] = "Accepted"
    record["qc_result"]["human_accepted"] = True
    record["updated_at"] = _now()
    production["active_asset_id"] = asset_id
    scene["asset_path"] = record["path"]
    scene["asset_status"] = "Asset Ready"
    scene["qc_status"] = "QC Passed"
    return {"ok": True, "scenes": updated}


def request_scene_retry(scenes: list[dict[str, Any]], scene_id: str) -> dict[str, Any]:
    updated, scene, error = _ready_scene(scenes, scene_id)
    if error:
        return {"ok": False, "error": error}
    if int(scene.get("retry_count") or 0) >= MAX_RETRIES:
        return {"ok": False, "error": "Retry limit reached for this scene."}
    scene["retry_count"] = int(scene.get("retry_count") or 0) + 1
    _production(scene)["generation_status"] = "Retry Requested"
    return {"ok": True, "scenes": updated}


def release_stalled_attempt(scenes: list[dict[str, Any]], scene_id: str) -> dict[str, Any]:
    updated = deepcopy(scenes)
    scene = _find(updated, scene_id)
    if scene is None:
        return {"ok": False, "error": "Scene was not found."}
    production = _production(scene)
    attempt_id = production.get("pending_attempt_id")
    if not attempt_id:
        return {"ok": False, "error": "No pending attempt exists."}
    return finish_generation(updated, scene_id, attempt_id, {"ok": False}, Path("."))
