"""Human review controls for full-song MV planning inside MV Director."""
from __future__ import annotations

import hashlib
from html import escape
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import streamlit as st

from app.full_song_mv_production_ui import render_scene_production
from core.full_song_mv import create_full_song_storyboard, edit_scene, move_scene, probe_song_audio, validate_storyboard
from core.full_song_mv_render import prepare_full_song_render, render_full_song


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
                elif commit({"audio": {**metadata, "upload_id": saved["data"].get("upload_id", "")}, "scenes": [], "target_aspect_ratio": "16:9"}):
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
    target_aspect = plan.get("target_aspect_ratio", "9:16")
    selected_aspect = st.selectbox("MV format", ["16:9", "9:16"],
                                   index=0 if target_aspect == "16:9" else 1,
                                   help="16:9 for a full music video; 9:16 for vertical clips.",
                                   key="mv_full_target_aspect")
    if selected_aspect != target_aspect:
        if commit({**plan, "target_aspect_ratio": selected_aspect}):
            st.rerun()
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
    approved_count = sum(item.get("approval_status") == "Approved" for item in scenes)
    options = [item["scene_id"] for item in scenes]
    identity = (str(audio.get("path")), tuple(options))
    if st.session_state.get("mv_full_plan_identity") != identity:
        for item_id in options:
            for suffix in ("section", "strategy", "description", "prompt", "character", "costume", "location", "style", "reference", "duration"):
                st.session_state.pop(f"mv_full_{item_id}_{suffix}", None)
        st.session_state.pop("mv_full_jump_target", None)
        st.session_state["mv_full_plan_identity"] = identity
        st.session_state["mv_full_active_scene"] = options[0]
        st.session_state.pop("mv_full_pending_scene", None)
    selected = st.session_state.get("mv_full_active_scene")
    if selected not in options:
        selected = options[0]
        st.session_state["mv_full_active_scene"] = selected
    scene = next(item for item in scenes if item["scene_id"] == selected)
    prefix = f"mv_full_{selected}"
    field_keys = {
        "song_section": "section", "shot_strategy": "strategy", "scene_description": "description",
        "visual_prompt": "prompt", "character": "character", "costume": "costume",
        "location": "location", "visual_style": "style", "reference_asset": "reference",
        "duration_seconds": "duration",
    }

    def staged_changes() -> dict[str, Any]:
        return {field: st.session_state.get(f"{prefix}_{suffix}", scene.get(field, ""))
                for field, suffix in field_keys.items()}

    def has_unsaved_changes() -> bool:
        return any(
            abs(float(value) - float(scene.get(field, 0))) > 0.0001 if field == "duration_seconds"
            else value != (scene.get(field) or ("New shot" if field == "shot_strategy" else ""))
            for field, value in staged_changes().items()
        )

    def clear_scene_widgets() -> None:
        for suffix in field_keys.values():
            st.session_state.pop(f"{prefix}_{suffix}", None)

    def switch_scene(target: str) -> None:
        clear_scene_widgets()
        st.session_state["mv_full_active_scene"] = target
        st.session_state.pop("mv_full_jump_target", None)
        st.session_state.pop("mv_full_pending_scene", None)
        st.rerun()

    def request_scene(target: str) -> None:
        if target == selected:
            return
        if has_unsaved_changes():
            st.session_state["mv_full_pending_scene"] = target
        else:
            switch_scene(target)

    def save_scene(status: str | None = None, direction: int = 0, target: str | None = None) -> None:
        changes = staged_changes()
        reference = str(changes["reference_asset"] or "")
        if status == "Approved" and reference and not Path(reference).is_file():
            st.error("Choose a reference file that exists before approving.")
            return
        requested = {**changes, **({"approval_status": status} if status else {})}
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
            if target:
                switch_scene(target)
            else:
                clear_scene_widgets()
                st.rerun()

    def timecode(seconds: float) -> str:
        whole = round(float(seconds))
        return f"{whole // 60}:{whole % 60:02d}"

    st.markdown("""<style>
    .st-key-mv_full_review_nav button { min-height: 44px; }
    .mv-scene-card { background: rgba(127,127,127,.08); border-radius: 12px; padding: 1rem 1.1rem; margin: .75rem 0 1rem; overflow-wrap: anywhere; }
    .mv-scene-card h3 { margin: .2rem 0 .55rem; font-size: 1.3rem; line-height: 1.35; }
    .mv-scene-card p { margin: .35rem 0; }
    .mv-scene-card .mv-timing { font-variant-numeric: tabular-nums; font-weight: 650; }
    @media (max-width: 640px) {
      .mv-scene-card { padding: .9rem; }
      .st-key-mv_full_scene_step [data-testid="stHorizontalBlock"],
      .st-key-mv_full_jump_row [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; gap: .5rem; }
      .st-key-mv_full_scene_step [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }
      .st-key-mv_full_jump_row [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }
      .st-key-mv_full_jump_row [data-testid="stColumn"]:last-child { flex: 0 0 72px !important; }
      .st-key-mv_full_jump_row [data-baseweb="select"] { min-height: 44px; }
      .st-key-mv_full_scene_step [data-testid="stVerticalBlock"],
      .st-key-mv_full_scene_step [data-testid="stElementContainer"],
      .st-key-mv_full_scene_step [data-testid="stButton"],
      .st-key-mv_full_jump_row [data-testid="stVerticalBlock"],
      .st-key-mv_full_jump_row [data-testid="stElementContainer"],
      .st-key-mv_full_jump_row [data-testid="stSelectbox"],
      .st-key-mv_full_jump_row [data-testid="stButton"] { width: 100% !important; }
    }
    @media (max-width: 350px) {
      .st-key-mv_full_jump_row [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
      .st-key-mv_full_jump_row [data-testid="stColumn"],
      .st-key-mv_full_jump_row [data-testid="stColumn"]:last-child { flex: 1 1 100% !important; }
    }
    </style>""", unsafe_allow_html=True)
    with st.container(key="mv_full_review_nav"):
        position = options.index(selected)
        st.markdown(f"**Scene {position + 1} / {len(scenes)}** · {approved_count} approved")
        with st.container(key="mv_full_scene_step"):
            nav = st.columns(2, gap="small")
            if nav[0].button("Previous scene", disabled=position == 0, key="mv_full_previous", use_container_width=True):
                request_scene(options[position - 1])
            if nav[1].button("Next scene", type="primary", disabled=position == len(options) - 1,
                             key="mv_full_next", use_container_width=True):
                request_scene(options[position + 1])
        if st.session_state.get("mv_full_jump_target") not in options:
            st.session_state["mv_full_jump_target"] = selected
        with st.container(key="mv_full_jump_row"):
            jump_cols = st.columns([5, 1], gap="small", vertical_alignment="bottom")
            jump = jump_cols[0].selectbox("Jump to scene", options, format_func=lambda key: next(
                (f"{item['scene_order']}. {item.get('song_section', '')} · {item.get('scene_description', '')}" for item in scenes if item["scene_id"] == key), key),
                key="mv_full_jump_target")
            if jump_cols[1].button("Go", help="Go to selected scene", key="mv_full_jump", use_container_width=True):
                request_scene(jump)
        pending = st.session_state.get("mv_full_pending_scene")
        if pending in options:
            st.warning("This scene has unsaved changes. Save or discard them before switching scenes.")
            pending_actions = st.columns(3)
            if pending_actions[0].button("Save and switch", key="mv_full_save_switch", use_container_width=True):
                save_scene(target=pending)
            if pending_actions[1].button("Discard and switch", key="mv_full_discard_switch", use_container_width=True):
                switch_scene(pending)
            if pending_actions[2].button("Stay here", key="mv_full_stay", use_container_width=True):
                st.session_state.pop("mv_full_pending_scene", None)
    st.markdown(
        f'<div class="mv-scene-card"><div class="mv-timing">{timecode(scene["start_seconds"])}–{timecode(scene["end_seconds"])}'
        f' · {escape(scene.get("song_section", ""))}</div>'
        f'<h3>{escape(scene.get("scene_description", ""))}</h3>'
        f'<p>{escape(scene.get("shot_strategy", "New shot"))} · {escape(scene.get("approval_status", "Planned"))}</p></div>',
        unsafe_allow_html=True,
    )
    st.caption(f"ID {selected} · revision {scene.get('revision', 1)} · exact timing {scene['start_seconds']:.2f}–{scene['end_seconds']:.2f}s")
    with st.expander("Scene details"):
        section = st.text_input("Song section", value=scene.get("song_section", ""), key=f"{prefix}_section")
        shot_strategy = st.selectbox("Shot strategy", ["New shot", "Reuse approved asset", "Hold shot"],
                                     index=["New shot", "Reuse approved asset", "Hold shot"].index(scene.get("shot_strategy", "New shot"))
                                     if scene.get("shot_strategy") in {"New shot", "Reuse approved asset", "Hold shot"} else 0,
                                     key=f"{prefix}_strategy")
        description = st.text_input("Scene description", value=scene.get("scene_description", ""), key=f"{prefix}_description")
        scene_duration = st.number_input("Duration (seconds)", min_value=1.0, max_value=duration,
                                         value=float(scene["duration_seconds"]), step=0.5, key=f"{prefix}_duration",
                                         help="The neighboring scene absorbs the difference so the timeline stays continuous.")
    with st.expander("Visual prompt and identity"):
        prompt = st.text_area("Visual prompt", value=scene.get("visual_prompt", ""), height=130, key=f"{prefix}_prompt")
        character = st.text_input("Character", value=scene.get("character", ""), key=f"{prefix}_character")
        costume = st.text_input("Costume", value=scene.get("costume", ""), key=f"{prefix}_costume")
        location = st.text_input("Location", value=scene.get("location", ""), key=f"{prefix}_location")
        visual_style = st.text_input("Visual style", value=scene.get("visual_style", ""), key=f"{prefix}_style")
    with st.expander("Reference asset"):
        references = sorted({str(path) for path in (project.get("assets") or {}).get("approved_images", {}).values() if path and Path(str(path)).is_file()})
        current_reference = str(scene.get("reference_asset") or "")
        choices = [""] + references
        if current_reference and current_reference not in choices:
            choices.append(current_reference)
        reference = st.selectbox("Reference asset", choices, index=choices.index(current_reference),
                                 format_func=lambda path: Path(path).name if path else "None", key=f"{prefix}_reference")
        if reference and not Path(reference).is_file():
            st.warning("Reference asset is missing on disk. Choose another before approving.")
    with st.expander("Scene actions", expanded=True):
        if st.button("Save scene", key=f"{prefix}_save", use_container_width=True):
            save_scene()
        actions = st.columns(2)
        if actions[0].button("Approve", key=f"{prefix}_approve", use_container_width=True):
            save_scene("Approved")
        if actions[1].button("Needs revision", key=f"{prefix}_revise", use_container_width=True):
            save_scene("Needs Revision")
        order_actions = st.columns(2)
        if order_actions[0].button("Move up", disabled=scene["scene_order"] == 1, key=f"{prefix}_up", use_container_width=True):
            save_scene(direction=-1)
        if order_actions[1].button("Move down", disabled=scene["scene_order"] == len(scenes), key=f"{prefix}_down", use_container_width=True):
            save_scene(direction=1)
    st.caption(f"Asset: {scene.get('asset_status', 'Planned')} · QC: {scene.get('qc_status', 'Pending')} · retries: {scene.get('retry_count', 0)}")
    render_scene_production(project, plan, scenes, scene, commit, provider_key)
    with st.expander("View all scenes"):
        st.caption(f"{len(scenes)} scenes · {approved_count} approved · timeline covers {duration:.1f}s")
        st.dataframe(
            [{"Order": item["scene_order"], "Start": item["start_seconds"], "End": item["end_seconds"],
              "Duration": item["duration_seconds"], "Section": item.get("song_section", ""),
              "Scene": item.get("scene_description", ""), "Approval": item.get("approval_status", "Planned")}
             for item in scenes],
            use_container_width=True, hide_index=True, height=320,
        )
    st.subheader("Full-song render")
    readiness = prepare_full_song_render(project, selected_aspect)
    if not readiness.get("ok"):
        st.info(readiness.get("error") or "Finish scene review before rendering.")
        if readiness.get("missing_scenes"):
            st.dataframe(readiness["missing_scenes"], hide_index=True, use_container_width=True)
    else:
        st.caption(f"Ready: {readiness['scene_count']} approved scenes, {len(readiness['timeline'])} shots, {duration:.1f}s of audio.")
    if st.button("Render full-song MV", disabled=not readiness.get("ok"), key="mv_full_render"):
        progress = st.progress(0, text="Preparing render")
        def on_progress(percent: int, message: str) -> None:
            progress.progress(percent, text=message)
        with st.spinner("Rendering approved scenes locally with FFmpeg…"):
            result = render_full_song(project, selected_aspect, progress_callback=on_progress)
        if result.get("ok"):
            if commit({**plan, "last_render": {"render_id": result["data"]["render_id"],
                                                  "path": result["data"]["outputs"][selected_aspect],
                                                  "final_qc": result["final_qc"]}}):
                st.success("Full-song MP4 passed FFprobe QC.")
                st.video(result["data"]["outputs"][selected_aspect])
        else:
            st.error(result.get("error") or "Render failed. Review the scene list and render log.")
    last_render = plan.get("last_render") or {}
    if last_render.get("path") and Path(last_render["path"]).is_file():
        st.caption(f"Last verified render: {last_render['path']}")
