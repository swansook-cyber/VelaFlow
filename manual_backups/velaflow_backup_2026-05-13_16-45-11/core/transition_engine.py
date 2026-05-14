from typing import Dict


TRANSITIONS: Dict[str, str] = {
    "none": "",
    "fade": "soft fade in/out per scene",
    "blur dissolve": "fade plus soft blur at scene edges",
    "whip pan": "fast horizontal pan feel",
    "film burn": "warm bright flash at cut",
    "flash cut": "short brightness flash",
    "emotional dip to black": "fade through black",
}


def scene_transition_filter(transition: str, duration: float) -> str:
    transition = (transition or "none").lower()
    duration = max(0.5, float(duration or 1))
    fade_duration = min(0.45, duration / 5)
    out_start = max(0, duration - fade_duration)
    if transition in {"none", ""}:
        return ""
    if transition == "fade":
        return f"fade=t=in:st=0:d={fade_duration:.3f},fade=t=out:st={out_start:.3f}:d={fade_duration:.3f}"
    if transition == "blur dissolve":
        return f"boxblur=luma_radius=1:luma_power=1,fade=t=in:st=0:d={fade_duration:.3f},fade=t=out:st={out_start:.3f}:d={fade_duration:.3f}"
    if transition == "flash cut":
        return "eq=brightness='if(lt(t,0.10),0.22,if(gt(t,{:.3f}),0.18,0))'".format(max(0, duration - 0.10))
    if transition == "film burn":
        return "colorbalance=rs=.12:gs=.04:bs=-.08,eq=brightness='if(lt(t,0.18),0.18,0)'"
    if transition == "whip pan":
        return "minterpolate=fps=30:mi_mode=mci"
    if transition == "emotional dip to black":
        dip = min(0.65, duration / 4)
        return f"fade=t=in:st=0:d={dip:.3f},fade=t=out:st={max(0, duration-dip):.3f}:d={dip:.3f}"
    return ""


def transition_options() -> list[str]:
    return list(TRANSITIONS.keys())
