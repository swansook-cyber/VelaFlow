import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


ROOT = Path(__file__).resolve().parents[1]


def _detect_ffmpeg_path() -> str:
    configured = os.getenv("FFMPEG_PATH", "ffmpeg")
    if configured and configured != "ffmpeg":
        return configured
    candidates = [
        ROOT / "ffmpeg-2026-05-06-git-f2e5eff3ff-full_build" / "bin" / "ffmpeg.exe",
        ROOT / "ffmpeg" / "bin" / "ffmpeg.exe",
        ROOT / "bin" / "ffmpeg.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return configured


@dataclass
class AppSettings:
    velaflow_mode: str = os.getenv("VELAFLOW_MODE", "LOCAL")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_fallback_model: str = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-latest")
    default_ai_provider: str = os.getenv("DEFAULT_AI_PROVIDER", os.getenv("TEXT_AI", "gemini"))
    ai_retry_count: int = int(os.getenv("AI_RETRY_COUNT", "3"))
    ai_request_timeout: int = int(os.getenv("AI_REQUEST_TIMEOUT", "60"))
    ai_cache_enabled: str = os.getenv("AI_CACHE_ENABLED", "true")
    text_ai: str = os.getenv("TEXT_AI", "gemini")
    image_ai: str = os.getenv("IMAGE_AI", "manual")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_text_model: str = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    openai_fallback_text_model: str = os.getenv("OPENAI_FALLBACK_TEXT_MODEL", "")
    xai_api_key: str = os.getenv("XAI_API_KEY", "")
    xai_text_model: str = os.getenv("XAI_TEXT_MODEL", "grok-4.3")
    xai_fallback_text_model: str = os.getenv("XAI_FALLBACK_TEXT_MODEL", "")
    openai_image_model: str = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1.5")
    openai_image_size: str = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")
    openai_image_quality: str = os.getenv("OPENAI_IMAGE_QUALITY", "medium")
    flux_api_url: str = os.getenv("FLUX_API_URL", "")
    flux_api_key: str = os.getenv("FLUX_API_KEY", "")
    sdxl_api_url: str = os.getenv("SDXL_API_URL", "")
    sdxl_api_key: str = os.getenv("SDXL_API_KEY", "")
    image_request_timeout: int = int(os.getenv("IMAGE_REQUEST_TIMEOUT", "180"))
    image_cache_enabled: str = os.getenv("IMAGE_CACHE_ENABLED", "true")
    video_ai: str = os.getenv("VIDEO_AI", "manual")
    video_request_timeout: int = int(os.getenv("VIDEO_REQUEST_TIMEOUT", "300"))
    kling_api_url: str = os.getenv("KLING_API_URL", "")
    kling_api_key: str = os.getenv("KLING_API_KEY", "")
    runway_api_url: str = os.getenv("RUNWAY_API_URL", "")
    runway_api_key: str = os.getenv("RUNWAY_API_KEY", "")
    google_flow_api_url: str = os.getenv("GOOGLE_FLOW_API_URL", "")
    google_flow_api_key: str = os.getenv("GOOGLE_FLOW_API_KEY", "")
    luma_api_url: str = os.getenv("LUMA_API_URL", "")
    luma_api_key: str = os.getenv("LUMA_API_KEY", "")
    pixverse_api_url: str = os.getenv("PIXVERSE_API_URL", "")
    pixverse_api_key: str = os.getenv("PIXVERSE_API_KEY", "")
    veo_api_url: str = os.getenv("VEO_API_URL", "")
    veo_api_key: str = os.getenv("VEO_API_KEY", "")
    quality_mode: str = os.getenv("QUALITY_MODE", "balanced")
    ffmpeg_path: str = _detect_ffmpeg_path()

def get_settings() -> AppSettings:
    return AppSettings(velaflow_mode=os.getenv("VELAFLOW_MODE", "LOCAL"))
