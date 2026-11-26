"""Human review controls for full-song MV planning inside MV Director."""
from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import streamlit as st

from app.full_song_mv_production_ui import render_scene_production
from core.full_song_mv import create_full_song_storyboard, edit_scene, move_scene, probe_song_audio, validate_storyboard


def render_full_song_planner(
    project: dict[str, Any],
    save_project: Callable[[], dict[str, Any]],
    save_audio: Callable[..., dict[str, Any]],
    provider_key: Callable[[str], str] | None = None,
) -> None:
    mv = project.setdefault("mv", {})
    plan = mv.get("full_song") or {}
    scenes = plan.get("scenes") or []
    st.subheader("Full-Song MV Plan")
    st.caption("Import the finished song, approve each scene, then produce and review one shot at a time.")

    def commit(new_plan: dict[str, Any]) -> bool:
        previous = deepcopy(mv.get("full_song"))
        mv["full_song"] = new_plan
        result = save_project()
        if not result.get("ok"):
            if previous is None:
                mv.pop("full_song", None)
            else:
                mv["full_song"] = previous
            st.error(f"Project could not be saved: {result.get('error') or 'check storage permissions'}")
            return False
        return True

    if not plan:
        upload = st.file_uploader("Import finished song audio", type=["mp3", "wav", "m4a"], key="mv_full_audio_upload")
        if st.button("Import audio", disabled=upload is None, key="mv_full_import_audio") and upload is not None:
            digest = hashlib.sha256(upload.getvalue()).hexdigest()[:20]
            saved = save_audio(
                project.get("title") or "mv_project", upload, project.get("workflow_type") or "song",
                upload_state_key=f"mv_full_audio::{digest}", storage_stem=f"full_song_mv_{digest}",
            )
            if not saved.get("ok"):
                st.error(saved.get("error") or "Audio could not be saved.")
            else:
                metadata = probe_song_audio(saved["data"]["path"])
                if not metadata.get("ok"):
                    st.error(metadata["error"])
                elif commit({"audio": {**metadata, "upload_id": saved["data"].get("upload_id", "")}, "scenes": []}):
                    st.rerun()
        return

    audio = plan.get("audio") or {}
    metadata = probe_song_audio(audio.get("path") or "")
    if not metadata.get("ok"):
        st.error(metadata["error"])
        return
    duration = float(metadata["duration_seconds"])
    if abs(duration - float(audio.get("duration_seconds") or 0)) > 0.05:
        st.error("The audio duration changed after import. Restore the original file before editing this plan.")
        return
    st.audio(audio["path"])
    st.caption(f"Audio duration: {duration:.1f}s ({duration / 60:.2f} min). Song sections are estimated from lyric headings and can be edited below.")
    if not scenes:
        suggested = max(12, min(80, round(duration / 6)))
        scene_count = st.number_input("Number of scenes", min_value=2, max_value=120, value=suggested, step=1, key="mv_full_count")
        if st.button("Create full-song storyboard", type="primary", key="mv_full_create"):
            result = create_full_song_storyboard(project.get("song") or {}, project, duration, int(scene_count))
            if not result.get("ok"):
                st.error(result["error"])
            elif commit({**plan, "scenes": result["scenes"], "section_source": result["section_source"]}):
                st.rerun()
        return

    validation = validate_storyboard(scenes, duration)
    if not validation.get("ok"):
        st.error(validation["error"])
        return
    if validation.get("missing_assets"):
        st.warning(f"{len(validation['missing_assets'])} previous asset file(s) are missing. The timeline remains editable; review or replace these files per scene.")
    approved_count = sum(scene.get("approval_status") == "Approved" for scene in scenes)
    st.caption(f"{len(scenes)} scenes · {approved_count} approved · timeline covers {duration:.1f}s")
    st.dataframe(
        [{"Order": scene["scene_order"], "Start": scene["start_seconds"], "End": scene["end_seconds"],
          "Duration": scene["duration_seconds"], "Section": scene.get("song_section", ""),
          "Scene": scene.get("scene_description", ""), "Approval": scene.get("approval_status", "Planned")}
         for scene in scenes],
        use_container_width=True, hide_index=True, height=320,
    )
    options = [scene["scene_id"] for scene in scenes]
    selected = st.selectbox("Review scene", options, format_func=lambda key: next(
        (f"{item['scene_order']}. {item.get('song_section', '')} · {item.get('scene_description', '')}" for item in scenes if item["scene_id"] == key), key),
        key="mv_full_selected_scene")
    scene = next(item for item in scenes if item["scene_id"] == selected)
    prefix = f"mv_full_{selected}"
    st.caption(f"{scene['start_seconds']:.1f}s – {scene['end_seconds']:.1f}s · ID {selected} · revision {scene.get('revision', 1)}")
    col_a, col_b = st.columns(2)
    section = col_a.text_input("Song section", value=scene.get("song_section", ""), key=f"{prefix}_section")
    shot_strategy = col_b.selectbox("Shot strategy", ["New shot", "Reuse approved asset", "Hold shot"],
                                   index=["New shot", "Reuse approved asset", "Hold shot"].index(scene.get("shot_strategy", "New shot"))
                                   if scene.get("shot_strategy") in {"New shot", "Reuse approved asset", "Hold shot"} else 0,
                                   key=f"{prefix}_strategy")
    description = st.text_input("Scene description", value=scene.get("scene_description", ""), key=f"{prefix}_description")
    prompt = st.text_area("Visual prompt", value=scene.get("visual_prompt", ""), height=130, key=f"{prefix}_prompt")
    col_c, col_d = st.columns(2)
    character = col_c.text_input("Character", value=scene.get("character", ""), key=f"{prefix}_character")
    costume = col_d.text_input("Costume", value=scene.get("costume", ""), key=f"{prefix}_costume")
    col_e, col_f = st.columns(2)
    location = col_e.text_input("Location", value=scene.get("location", ""), key=f"{prefix}_location")
    visual_style = col_f.text_input("Visual style", value=scene.get("visual_style", ""), key=f"{prefix}_style")
    references = sorted({str(path) for path in (project.get("assets") or {}).get("approved_images", {}).values() if path and Path(str(path)).is_file()})
    current_reference = str(scene.get("reference_asset") or "")
    choices = [""] + references
    if current_reference and current_reference not in choices:
        choices.append(current_reference)
    reference = st.selectbox("Reference asset", choices, index=choices.index(current_reference),
                             format_func=lambda path: Path(path).name if path else "None", key=f"{prefix}_reference")
    if reference and not Path(reference).is_file():
        st.warning("Reference asset is missing on disk. Choose another before approving.")
    scene_duration = st.number_input("Duration (seconds)", min_value=1.0, max_value=duration,
                                     value=float(scene["duration_seconds"]), step=0.5, key=f"{prefix}_duration",
                                     help="The neighboring scene absorbs the difference so the timeline stays continuous.")

    changes = {"song_section": section, "scene_description": description, "visual_prompt": prompt,
               "character": character, "costume": costume, "location": location, "visual_style": visual_style,
               "reference_asset": reference, "shot_strategy": shot_strategy, "duration_seconds": scene_duration}

    def save_scene(status: str | None = None, direction: int = 0) -> None:
        requested = {**changes, **({"approval_status": status} if status else {})}
        if status == "Approved" and reference and not Path(reference).is_file():
            st.error("Choose a reference file that exists before approving.")
            return
        edited = edit_scene(scenes, selected, requested, duration)
        if not edited.get("ok"):
            st.error(edited["error"])
            return
        updated = edited["scenes"]
        if direction:
            moved = move_scene(updated, selected, direction, duration)
            if not moved.get("ok"):
                st.error(moved["error"])
                return
            updated = moved["scenes"]
        if commit({**plan, "scenes": updated}):
            st.rerun()

    actions = st.columns(3)
    if actions[0].button("Save scene", key=f"{prefix}_save"):
        save_scene()
    if actions[1].button("Approve", key=f"{prefix}_approve"):
        save_scene("Approved")
    if actions[2].button("Needs revision", key=f"{prefix}_revise"):
        save_scene("Needs Revision")
    order_actions = st.columns(2)
    if order_actions[0].button("Move up", disabled=scene["scene_order"] == 1, key=f"{prefix}_up"):
        save_scene(direction=-1)
    if order_actions[1].button("Move down", disabled=scene["scene_order"] == len(scenes), key=f"{prefix}_down"):
        save_scene(direction=1)
    st.caption(f"Asset: {scene.get('asset_status', 'Planned')} · QC: {scene.get('qc_status', 'Pending')} · retries: {scene.get('retry_count', 0)}")
    render_scene_production(project, plan, scenes, scene, commit, provider_key)
