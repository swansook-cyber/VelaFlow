from __future__ import annotations

from pathlib import Path
from typing import Any

from core import agent_tools
from core.agent_memory import load_agent_memory
from core.agent_studio import PROJECT_TYPES, generate_agent_package
from core.agent_workflows import WORKFLOW_MODES


def _infer_project_type(user_input: str, workflow_mode: str, project_type: str | None) -> str:
    if project_type in PROJECT_TYPES:
        return str(project_type)
    lowered = str(user_input or "").lower()
    if workflow_mode == "Spotify Commercial Mode" or any(word in lowered for word in ["song", "lyrics", "suno", "เพลง"]):
        return "Spotify Song Release"
    if workflow_mode == "Podcast Episode Mode" or any(word in lowered for word in ["podcast", "episode", "พอดแคสต์"]):
        return "Podcast Episode Idea"
    if workflow_mode == "MV Director Mode" or any(word in lowered for word in ["mv", "music video", "video prompt"]):
        return "AI Music Video Prompt"
    if workflow_mode == "TikTok Viral Mode" or any(word in lowered for word in ["affiliate", "product", "สินค้า"]):
        return "TikTok Affiliate Clip"
    return "General Creative Package"


def _workflow_export_text(output: dict[str, str], workflow_mode: str) -> tuple[str, str]:
    if workflow_mode == "Spotify Commercial Mode":
        return "spotify_release_package.txt", "\n\n".join(
            [
                output.get("Best Title Ideas", ""),
                output.get("Lyrics or Script", ""),
                output.get("Suno / Music Style Prompt", ""),
                output.get("Cover Image Prompt", ""),
                output.get("Next Action Checklist", ""),
            ]
        )
    if workflow_mode == "Podcast Episode Mode":
        return "podcast_episode_structure.txt", "\n\n".join(
            [
                output.get("Project Summary", ""),
                output.get("Lyrics or Script", ""),
                output.get("TikTok Hook Ideas", ""),
                output.get("Next Action Checklist", ""),
            ]
        )
    if workflow_mode == "MV Director Mode":
        return "mv_storyboard.txt", "\n\n".join(
            [
                output.get("Main Creative Direction", ""),
                output.get("Lyrics or Script", ""),
                output.get("Video Prompt", ""),
                output.get("Cover Image Prompt", ""),
            ]
        )
    if workflow_mode == "TikTok Viral Mode":
        return "tiktok_hooks.txt", "\n\n".join(
            [
                output.get("TikTok Hook Ideas", ""),
                output.get("Caption", ""),
                output.get("Hashtags", ""),
            ]
        )
    return "agent_package.txt", "\n\n".join(f"{key}\n{value}" for key, value in output.items())


def run_agent_workflow(
    user_input: str,
    workflow_mode: str,
    use_memory: bool = True,
    project_type: str | None = None,
    language: str = "Thai",
    tone: str = "Emotional",
) -> dict[str, Any]:
    actions: list[str] = []
    generated_files: list[str] = []
    errors: list[str] = []
    workflow_mode = workflow_mode if workflow_mode in WORKFLOW_MODES else "Quick Generate"
    selected_project_type = _infer_project_type(user_input, workflow_mode, project_type)
    actions.append("analyzing idea")
    actions.append(f"selecting workflow: {workflow_mode}")

    output = generate_agent_package(
        user_input,
        selected_project_type,
        language,
        tone,
        workflow_mode,
        use_memory=use_memory,
    )
    actions.append("generating package")

    try:
        title = output.get("Best Title Ideas", "agent_package").splitlines()[0].strip("- ").strip()
        folder = agent_tools.create_project_folder(title or selected_project_type)
        actions.append(f"created project folder: {folder}")
    except Exception as exc:
        folder = None
        errors.append(f"Could not create project folder: {exc}")

    try:
        package_file = agent_tools.save_project_package(output, selected_project_type)
        generated_files.append(str(package_file))
        actions.append("saved complete agent package")
    except Exception as exc:
        errors.append(f"Could not save package TXT: {exc}")

    try:
        filename, text_payload = _workflow_export_text(output, workflow_mode)
        workflow_file = agent_tools.export_txt(text_payload, filename)
        generated_files.append(str(workflow_file))
        actions.append(f"exported workflow file: {filename}")
    except Exception as exc:
        errors.append(f"Could not export workflow TXT: {exc}")

    try:
        checklist = agent_tools.generate_release_checklist(selected_project_type)
        checklist_file = agent_tools.export_txt(checklist, "release_checklist.txt")
        generated_files.append(str(checklist_file))
        actions.append("generated release checklist")
    except Exception as exc:
        errors.append(f"Could not export checklist: {exc}")

    try:
        release_package = agent_tools.build_release_package(output)
        generated_files.extend(release_package.get("files", []))
        actions.append("built downloadable release package")
    except Exception as exc:
        errors.append(f"Could not build release package: {exc}")

    memory_summary = agent_tools.summarize_memory(load_agent_memory() if use_memory else {})
    actions.append("finalizing project")
    unique_files = []
    for file_name in generated_files:
        if file_name not in unique_files and Path(file_name).exists():
            unique_files.append(file_name)
    return {
        "output_package": output,
        "actions_performed": actions,
        "generated_files": unique_files,
        "workflow_summary": (
            f"VelaFlow Agent ran {workflow_mode} for {selected_project_type}. "
            f"Generated {len(unique_files)} file(s)."
        ),
        "memory_summary": memory_summary,
        "errors": errors,
        "success": not errors,
    }
