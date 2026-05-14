from typing import Dict


COLOR_GRADES: Dict[str, str] = {
    "none": "",
    "warm": "eq=contrast=1.05:saturation=1.08:gamma_r=1.04:gamma_b=0.96",
    "cold": "eq=contrast=1.07:saturation=0.95:gamma_b=1.08:gamma_r=0.96",
    "moody": "eq=contrast=1.18:brightness=-0.035:saturation=0.88",
    "neon": "eq=contrast=1.13:saturation=1.35:gamma=0.96",
    "film_look": "eq=contrast=1.10:saturation=0.92:gamma=1.03,curves=preset=medium_contrast",
}


def color_grade_filter(name: str = "none") -> str:
    return COLOR_GRADES.get(name or "none", "")


def color_grade_options() -> list[str]:
    return list(COLOR_GRADES.keys())
