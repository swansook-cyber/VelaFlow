"""Explicit, one-scene-at-a-time production controls for the existing planner."""
from __future__ import annotations

import os
import importlib.util
from pathlib import Path
from typing import Any, Callable

import streamlit as st

from core.full_song_mv_production import (
    MAX_RETRIES, accept_scene_asset, begin_generation, import_scene_media, qc_scene_asset,
    release_stalled_attempt, request_scene_retry, run_generation,
)
from core.paths import resolve_project_folder
from core.settings import get_settings
from providers.veo_provider import DEFAULT_VEO_MODEL


def _locally_available(provider: str, key: str) -> bool:
    if not key:
        return False
    if provider == "openai_images":
        return True
    try:
        return importlib.util.find_spec("google.genai") is not None
    except ModuleNotFoundError:
        return False


def render_scene_production(project: dict[str, Any], plan: dict[str, Any], scenes: list[dict[str, Any]],
                            scene: dict[str, Any], commit: Callable[[dict[str, Any]], bool],
                            provider_key: Callable[[str], str] | None = None) -> None:
    scene_id = scene["scene_id"]
    prefix = f"mv_prod_{scene_id}"
    production = scene.get("production") or {}
    assets = production.get("assets") or []
    attempts = production.get("attempts") or []
    folder = resolve_project_folder(project.get("title") or "mv_project", project.get("workflow_type") or "song") / "assets" / "full_song_mv"
    approved = scene.get("approval_status") == "Approved"
    st.subheader("Scene production")
    st.caption("Produce or import one shot, preview it, run file checks, then accept it. Existing accepted files are kept.")
    if not approved:
        st.info("Approve this storyboard scene before importing or generating media. Previous assets remain available for review.")
    if scene.get("asset_path") and scene.get("qc_status") == "Needs Revision":
        st.warning("The storyboard changed. The previous accepted file is preserved, but its QC does not cover this scene revision.")

    with st.expander("Import image or MP4", expanded=approved and not assets):
        upload = st.file_uploader("Media for this scene", type=["jpg", "jpeg", "png", "webp", "mp4"],
                                  key=f"{prefix}_upload", disabled=not approved)
        if st.button("Import this asset", disabled=not approved or upload is None, key=f"{prefix}_import") and upload is not None:
            result = import_scene_media(scenes, scene_id, upload.name, upload.getvalue(), folder)
            if not result.get("ok"):
                st.error(result.get("error") or "The media file could not be imported.")
            elif commit({**plan, "scenes": result["scenes"]}):
                st.rerun()
        reusable = str(scene.get("reference_asset") or scene.get("asset_path") or "")
        if approved and reusable and Path(reusable).is_file():
            st.caption(f"Existing file: {Path(reusable).name}. A separate copy will be created for QC; the original stays untouched.")
            if st.button("Use existing file for this scene", key=f"{prefix}_reuse"):
                result = import_scene_media(scenes, scene_id, Path(reusable).name, Path(reusable).read_bytes(), folder)
                if not result.get("ok"):
                    st.error(result.get("error") or "The existing file could not be imported.")
                elif commit({**plan, "scenes": result["scenes"]}):
                    st.rerun()

    if assets:
        asset_ids = [row["asset_id"] for row in reversed(assets)]
        asset_id = st.selectbox("Review asset", asset_ids,
                                format_func=lambda key: next((f"{row['kind'].title()} · {row['status']} · rev {row['scene_revision']} · {Path(row['path']).name}"
                                                               for row in assets if row["asset_id"] == key), key),
                                key=f"{prefix}_review_asset")
        record = next(row for row in assets if row["asset_id"] == asset_id)
        media = Path(record["path"])
        if media.is_file():
            if record["kind"] == "image":
                st.image(str(media), caption=media.name, use_container_width=True)
            else:
                st.video(str(media))
        else:
            st.error("This asset file is missing. Its history is preserved; import or generate a replacement.")
        st.caption(f"Scene rev {record['scene_revision']} · {record['width']}×{record['height']} · "
                   f"{record['duration_seconds']:.1f}s · provider {record['provider']} · job {record.get('job_id') or 'none'}")
        st.caption("Visual review guide: " + ", ".join(f"{label}: {scene.get(field) or 'unspecified'}" for label, field in
                                                  (("character", "character"), ("costume", "costume"),
                                                   ("location", "location"), ("style", "visual_style"))))
        st.caption("Character and visual match require your review; file QC cannot inspect image content.")
        qc = record.get("qc_result") or {}
        if qc:
            st.write("File QC:", "Passed" if qc.get("passed") else "Needs attention")
            st.dataframe([{"Check": name.replace("_", " "), "Result": "Pass" if passed else "Fail"}
                          for name, passed in (qc.get("checks") or {}).items()], hide_index=True, use_container_width=True)
        current_revision = record["scene_revision"] == scene.get("revision")
        if not current_revision:
            st.info("This file was reviewed for an older scene revision. Use the existing file as a new candidate above if it still fits.")
        reviewed = st.checkbox("I reviewed this shot against the scene description and references",
                               key=f"{prefix}_{asset_id}_{qc.get('file_sha256', 'unchecked')}_human_review")
        actions = st.columns(2)
        if actions[0].button("Run file QC", disabled=not current_revision, key=f"{prefix}_qc"):
            result = qc_scene_asset(scenes, scene_id, asset_id)
            if commit({**plan, "scenes": result["scenes"]}):
                if not result["ok"]:
                    st.error(result["error"])
                else:
                    st.rerun()
        current_qc = approved and record.get("status") == "QC Passed" and record.get("qc_revision") == scene.get("revision")
        if actions[1].button("Accept this asset", disabled=not current_qc or not reviewed, key=f"{prefix}_accept"):
            result = accept_scene_asset(scenes, scene_id, asset_id)
            if not result.get("ok"):
                st.error(result["error"])
            elif commit({**plan, "scenes": result["scenes"]}):
                st.rerun()

    with st.expander("Generate this scene", expanded=False):
        choices = {"Image · OpenAI": ("image", "openai_images", "openai"),
                   "Image · Gemini": ("image", "gemini_image", "gemini"),
                   "Video shot · Veo": ("video", "gemini_veo", "gemini")}
        chosen = st.selectbox("Provider", list(choices), key=f"{prefix}_provider")
        kind, provider, key_name = choices[chosen]
        key = (provider_key(key_name) if provider_key else "") or ""
        configured = _locally_available(provider, key)
        model = (get_settings().openai_image_model if provider == "openai_images" else
                 "provider selects from configured image models" if provider == "gemini_image" else
                 os.getenv("VEO_MODEL", DEFAULT_VEO_MODEL))
        st.write(f"Model: {model}")
        if not configured:
            st.info("API key or provider SDK missing. Check Settings / API Key before generating.")
        else:
            st.caption("Provider is locally configured; live access is checked when you request generation.")
        st.warning("Estimated cost is unavailable for this model. Your provider may charge your account for each request; actual cost is not tracked here.")
        if kind == "video":
            shot_duration = st.number_input("Shot length (seconds)", min_value=3.0, max_value=8.0,
                                            value=min(8.0, max(3.0, float(scene.get("duration_seconds") or 5))), step=1.0,
                                            key=f"{prefix}_shot_length")
            st.caption("Veo generates a 3–8 second shot. Longer scenes need another shot, a reused asset, or a held shot.")
        else:
            shot_duration = 0.0
        if scene.get("reference_asset"):
            st.caption("Reference selected: " + Path(scene["reference_asset"]).name +
                       ". This provider connector uses text prompts only; the reference file is shown for manual review and is not uploaded to the provider.")
        if production.get("pending_attempt_id"):
            st.warning("A generation attempt is recorded as running. No automatic resubmission occurs on reload.")
            if st.button("Mark stalled attempt failed", key=f"{prefix}_release"):
                released = release_stalled_attempt(scenes, scene_id)
                if released.get("scenes") and commit({**plan, "scenes": released["scenes"]}):
                    st.rerun()
        elif attempts and production.get("generation_status") != "Retry Requested":
            st.caption("Choose Retry below before making another paid request for this scene.")
        confirm = st.checkbox("I confirm one provider request for this scene and accept possible charges",
                              key=f"{prefix}_{provider}_{len(attempts)}_paid_confirm")
        can_generate = (approved and configured and confirm and bool(str(scene.get("visual_prompt") or "").strip())
                        and not production.get("pending_attempt_id") and
                        (not attempts or production.get("generation_status") == "Retry Requested"))
        if st.button("Generate this shot", type="primary", disabled=not can_generate, key=f"{prefix}_generate"):
            begun = begin_generation(scenes, scene_id, kind, provider, confirmed=confirm,
                                     configured=configured, shot_duration=shot_duration)
            if not begun.get("ok"):
                st.error(begun["error"])
            elif commit({**plan, "scenes": begun["scenes"]}):
                settings = {"gemini_api_key": key if key_name == "gemini" else "",
                            "openai_api_key": key if key_name == "openai" else "",
                            "openai_image_model": model if provider == "openai_images" else "",
                            "model": model if kind == "video" else "",
                            "size": "1024x1536", "cache_enabled": False}
                with st.spinner("Generating only this shot…"):
                    result = run_generation(begun["scenes"], scene_id, begun["attempt_id"], folder, settings)
                if result.get("scenes") and commit({**plan, "scenes": result["scenes"]}):
                    if result.get("ok"):
                        st.rerun()
                    else:
                        st.error("Provider attempt failed or returned invalid media. Existing accepted assets remain unchanged.")

    if approved and (assets or attempts) and not production.get("pending_attempt_id") and int(scene.get("retry_count") or 0) < MAX_RETRIES:
        st.caption(f"Retries used: {scene.get('retry_count', 0)}/{MAX_RETRIES}. A new provider request may incur another charge.")
        if st.button("Retry this scene", key=f"{prefix}_retry"):
            result = request_scene_retry(scenes, scene_id)
            if not result.get("ok"):
                st.error(result["error"])
            elif commit({**plan, "scenes": result["scenes"]}):
                st.rerun()
