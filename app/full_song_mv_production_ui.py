"""Explicit, one-scene-at-a-time production controls for the existing planner."""
from __future__ import annotations

import os
import importlib.util
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import streamlit as st

from core.full_song_mv_production import (
    MAX_RETRIES, accept_scene_asset, begin_generation, import_scene_media, qc_scene_asset,
    release_stalled_attempt, request_scene_retry, run_generation, load_character_references,
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
    target_aspect = plan.get("target_aspect_ratio", "9:16")
    prefix = f"mv_prod_{scene_id}"
    production = scene.get("production") or {}
    assets = production.get("assets") or []
    attempts = production.get("attempts") or []
    project_folder = resolve_project_folder(project.get("title") or "mv_project", project.get("workflow_type") or "song")
    folder = project_folder / "assets" / "full_song_mv"
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
            result = qc_scene_asset(scenes, scene_id, asset_id, target_aspect)
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

    accepted = [row for row in assets if row.get("status") == "Accepted" and
                row.get("scene_revision") == scene.get("revision") and
                (row.get("qc_result") or {}).get("target_aspect_ratio", "9:16") == target_aspect]
    if approved and accepted:
        st.caption("Choose accepted shots in playback order. A still image can fill the remaining scene time.")
        available = [row["asset_id"] for row in accepted]
        selected_ids = [key for key in (production.get("render_asset_ids") or [production.get("active_asset_id")]) if key in available]
        shot_ids = st.multiselect("Shots for render (in order)", available, default=selected_ids,
                                  format_func=lambda key: next((f"{row['kind'].title()} · {Path(row['path']).name}" for row in accepted if row["asset_id"] == key), key),
                                  key=f"{prefix}_render_shots")
        policy_options = ["Require full shot coverage", "Hold last video frame", "Loop last video"]
        current_policy = 2 if production.get("allow_video_loop") else 1 if production.get("hold_last_frame") else 0
        policy = st.selectbox("If the last video is short", policy_options, index=current_policy, key=f"{prefix}_video_fill")
        if st.button("Save shot assembly", disabled=not shot_ids, key=f"{prefix}_save_shots"):
            updated = deepcopy(scenes)
            changed = next(row for row in updated if row["scene_id"] == scene_id)
            settings = changed.setdefault("production", {})
            settings["render_asset_ids"] = shot_ids
            settings["hold_last_frame"] = policy == policy_options[1]
            settings["allow_video_loop"] = policy == policy_options[2]
            if commit({**plan, "scenes": updated}):
                st.rerun()

    if approved and (assets or attempts) and not production.get("pending_attempt_id") and int(scene.get("retry_count") or 0) < MAX_RETRIES:
        st.caption(f"Retries used: {scene.get('retry_count', 0)}/{MAX_RETRIES}. A new provider request may incur another charge.")
        if st.button("Retry this scene", key=f"{prefix}_retry"):
            result = request_scene_retry(scenes, scene_id)
            if not result.get("ok"):
                st.error(result["error"])
            elif commit({**plan, "scenes": result["scenes"]}):
                st.rerun()

    with st.expander("Generate this scene", expanded=False):
        choices = {"Image · OpenAI": ("image", "openai_images", "openai")}
        if target_aspect == "9:16":
            st.caption("The Gemini image and Veo connectors need a verified current model before paid generation is offered here. Import their finished assets for QC instead.")
        else:
            st.caption("16:9: OpenAI image edits can use the selected character views. The landscape provider output is cropped to 16:9 after generation.")
        chosen = st.selectbox("Provider", list(choices), key=f"{prefix}_provider")
        kind, provider, key_name = choices[chosen]
        references = (project.get("assets") or {}).get("character_references") or {}
        prior_reference = (attempts[-1].get("reference_snapshot") or {}) if attempts else {}
        options = ["None", *references.keys()]
        default_reference = next((name for name, item in references.items() if item.get("character_name") == "Vela Moon"), "None") if scene_id == "scene_010" else "None"
        selected_name = st.selectbox("Character reference", options,
                                     index=options.index(default_reference), key=f"{prefix}_character_reference")
        reference_record = references.get(selected_name)
        active_reference = prior_reference or reference_record
        retry_reference_mismatch = bool(prior_reference and reference_record and (
            reference_record.get("source_zip_sha256") != prior_reference.get("source_zip_sha256")
            or reference_record.get("version") != prior_reference.get("version")
            or [item.get("sha256") for item in (reference_record.get("images") or {}).values()]
               != [item.get("sha256") for item in (prior_reference.get("images") or {}).values()]))
        reference_check = load_character_references(active_reference, project_folder) if active_reference else {"ok": False, "error": "Select an imported character reference."}
        if active_reference:
            st.write(f"**{active_reference.get('character_name', 'Character')} · Master V{active_reference.get('version', '?')} · {len(active_reference.get('images') or {})} views** · {active_reference.get('reference_asset_status', 'Pending validation')}")
            st.caption("Reference images are sent only to the chosen OpenAI image edits request. Identity similarity is not guaranteed.")
            if prior_reference:
                st.info("Retry is pinned to the reference version used by the previous attempt.")
            if retry_reference_mismatch:
                st.error("Select the same reference version for this retry.")
            if not reference_check["ok"]:
                st.error(reference_check["error"])
        if scene_id == "scene_010":
            st.info("Scene 010 plan: band performance · Wardrobe Look B · 16:9 · same face and hairstyle as Master Character V1.0. Storyboard approval remains required.")
        if target_aspect == "16:9" and not active_reference:
            st.info("Select the imported Master Character reference to enable 16:9 generation.")
        key = (provider_key(key_name) if provider_key else "") or ""
        configured = _locally_available(provider, key)
        model = (get_settings().openai_image_model if provider == "openai_images" else
                 "provider selects from configured image models" if provider == "gemini_image" else
                 os.getenv("VEO_MODEL", DEFAULT_VEO_MODEL))
        st.write(f"Model: {model}")
        if model == "gpt-image-1.5":
            st.caption("GPT Image 1.5 is deprecated and scheduled to shut down on 1 December 2026. Reference edits request high input fidelity.")
        model_supported = model in {"gpt-image-1.5", "gpt-image-1-mini", "gpt-image-2"}
        if not model_supported:
            st.info("This image model has not been verified for the selected output format. Choose a supported model in Settings or import an existing asset.")
        if not configured:
            st.info("OpenAI API key missing. Check Settings / API Key before generating.")
        else:
            st.caption("Provider is locally configured; live access is checked when you request generation.")
        st.caption("Output: 1536×1024 from OpenAI, then cropped locally to 1536×864 (16:9). One image per request.")
        quality = os.getenv("OPENAI_IMAGE_QUALITY", "medium")
        output_price = {"low": 0.013, "medium": 0.05, "high": 0.20}.get(quality.lower()) if model == "gpt-image-1.5" else None
        if output_price is not None:
            st.warning(f"Published output-image price at {quality} quality: about ${output_price:.3f} USD. Four reference images and prompt add variable input-token charges; total cost cannot be known before the request. Check current provider pricing before confirming.")
        else:
            st.warning("Estimated cost is unavailable for this model/quality. Your provider may charge your account for each request; actual cost is not tracked here.")
        if kind == "video":
            shot_duration = st.number_input("Shot length (seconds)", min_value=3.0, max_value=8.0,
                                            value=min(8.0, max(3.0, float(scene.get("duration_seconds") or 5))), step=1.0,
                                            key=f"{prefix}_shot_length")
            st.caption("Veo generates a 3–8 second shot. Longer scenes need another shot, a reused asset, or a held shot.")
        else:
            shot_duration = 0.0
        if scene.get("reference_asset") and not active_reference:
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
        can_generate = (approved and configured and model_supported and confirm and bool(str(scene.get("visual_prompt") or "").strip())
                        and (not active_reference or reference_check["ok"]) and not retry_reference_mismatch
                        and (target_aspect != "16:9" or bool(active_reference))
                        and not production.get("pending_attempt_id") and
                        (not attempts or production.get("generation_status") == "Retry Requested"))
        if st.button("Generate this shot", type="primary", disabled=not can_generate, key=f"{prefix}_generate"):
            begun = begin_generation(scenes, scene_id, kind, provider, confirmed=confirm,
                                     configured=configured, shot_duration=shot_duration,
                                     reference_record=reference_record, reference_root=project_folder)
            if not begun.get("ok"):
                st.error(begun["error"])
            elif commit({**plan, "scenes": begun["scenes"]}):
                settings = {"gemini_api_key": key if key_name == "gemini" else "",
                            "openai_api_key": key if key_name == "openai" else "",
                            "openai_image_model": model if provider == "openai_images" else "",
                            "model": model if kind == "video" else "",
                            "size": "1536x1024" if target_aspect == "16:9" else "1024x1536",
                            "target_aspect_ratio": target_aspect,
                            "strict_image_model": True, "cache_enabled": False}
                with st.spinner("Generating only this shot…"):
                    result = run_generation(begun["scenes"], scene_id, begun["attempt_id"], folder, settings)
                if result.get("scenes") and commit({**plan, "scenes": result["scenes"]}):
                    if result.get("ok"):
                        st.rerun()
                    else:
                        st.error(f"Generation stopped: {result.get('error') or 'provider_failed_or_invalid_media'}. Existing accepted assets remain unchanged.")
