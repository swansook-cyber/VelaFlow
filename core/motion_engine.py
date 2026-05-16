from typing import Any, Dict


MOTION_PRESETS = [
    "still",
    "slow_zoom_in",
    "slow_zoom_out",
    "pan_left",
    "pan_right",
    "handheld_soft",
    "cinematic_drift",
    "emotional_push_in",
    "hook_energy_zoom",
    "slow_zoom",
    "slow_cinematic",
    "minimal_pan",
    "product_focus",
    "shake",
    "shake_zoom",
    "bounce",
    "cinematic_fade",
    "film_fade",
]


def select_motion(scene: Dict[str, Any], motion_style: str = "auto") -> str:
    if motion_style and motion_style != "auto":
        return motion_style if motion_style in MOTION_PRESETS else "cinematic_drift"

    text = " ".join(
        str(scene.get(key, "") or "").lower()
        for key in ["emotion", "camera", "camera_motion", "pacing_note", "lyric_part", "section", "transition"]
    )
    if any(word in text for word in ["hook", "chorus", "final chorus", "drop", "energy"]):
        return "hook_energy_zoom"
    if any(word in text for word in ["close", "push", "dolly in", "cry", "sad", "lonely", "miss", "emotional"]):
        return "emotional_push_in"
    if any(word in text for word in ["handheld", "shaky", "raw"]):
        return "handheld_soft"
    if "pan left" in text:
        return "pan_left"
    if "pan right" in text:
        return "pan_right"
    if any(word in text for word in ["wide", "slow", "verse", "soft"]):
        return "slow_zoom_in"
    if any(word in text for word in ["outro", "fade", "ending"]):
        return "slow_zoom_out"
    return "cinematic_drift"


def image_motion_filter(motion: str, width: int, height: int, duration_seconds: float, fps: int = 30) -> str:
    frames = max(1, int(float(duration_seconds or 1) * fps))
    motion = (motion or "cinematic_drift").strip()
    aliases = {
        "slow_zoom": "slow_zoom_in",
        "slow_cinematic": "emotional_push_in",
        "cinematic_mv": "emotional_push_in",
        "cinematic_fade": "slow_zoom_out",
        "film_fade": "slow_zoom_out",
        "minimal_pan": "cinematic_drift",
        "product_focus": "slow_zoom_in",
        "shake": "handheld_soft",
        "shake_zoom": "hook_energy_zoom",
        "bounce": "hook_energy_zoom",
    }
    motion = aliases.get(motion, motion)
    zoom_in = "min(zoom+0.0008,1.12)"
    zoom_out = "max(1.12-on*0.0008,1.0)"

    if motion == "still":
        z_expr = "1.0"
        x_expr = "(iw-iw/zoom)/2"
        y_expr = "(ih-ih/zoom)/2-18"
    elif motion == "slow_zoom_out":
        z_expr = zoom_out
        x_expr = "(iw-iw/zoom)/2"
        y_expr = "(ih-ih/zoom)/2-18"
    elif motion == "pan_left":
        z_expr = "1.08"
        x_expr = "(iw-iw/zoom)*(1-on/max(1,({frames}-1)))"
        y_expr = "(ih-ih/zoom)/2-18"
    elif motion == "pan_right":
        z_expr = "1.08"
        x_expr = "(iw-iw/zoom)*(on/max(1,({frames}-1)))"
        y_expr = "(ih-ih/zoom)/2"
    elif motion == "handheld_soft":
        z_expr = "1.04"
        x_expr = "(iw-iw/zoom)/2+sin(on/9)*6"
        y_expr = "(ih-ih/zoom)/2-18+cos(on/11)*5"
    elif motion == "hook_energy_zoom":
        z_expr = "min(zoom+0.0014,1.18)"
        x_expr = "(iw-iw/zoom)/2+sin(on/8)*5"
        y_expr = "(ih-ih/zoom)/2-18"
    elif motion == "emotional_push_in":
        z_expr = "min(zoom+0.0010,1.15)"
        x_expr = "(iw-iw/zoom)/2"
        y_expr = "(ih-ih/zoom)/2-18"
    elif motion == "cinematic_drift":
        z_expr = "min(zoom+0.0006,1.10)"
        x_expr = "(iw-iw/zoom)/2+sin(on/18)*8"
        y_expr = "(ih-ih/zoom)/2-18+cos(on/24)*6"
    else:
        z_expr = zoom_in
        x_expr = "(iw-iw/zoom)/2"
        y_expr = "(ih-ih/zoom)/2"

    x_expr = x_expr.format(frames=frames)
    y_expr = y_expr.format(frames=frames)
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={width}x{height}:fps={fps},"
        f"trim=duration={float(duration_seconds or 1):.3f},setpts=PTS-STARTPTS,setsar=1,format=yuv420p"
    )
