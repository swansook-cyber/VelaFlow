import hashlib
import json
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from core.song_quality_core import production_diagnostic_logger, safe_diagnostic_label, safe_exception_summary
from providers.ai_provider import generate_text as provider_generate_text
from providers.ai_provider import normalize_provider, provider_model


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "outputs" / "cache" / "text"
_EXECUTOR = ThreadPoolExecutor(max_workers=int(os.getenv("AI_QUEUE_WORKERS", "3")))
LOGGER = production_diagnostic_logger("velaflow.provider_manager")


class ProviderError(RuntimeError):
    pass


def _cache_enabled() -> bool:
    return os.getenv("AI_CACHE_ENABLED", "true").strip().lower() not in {"0", "false", "no"}


def _cache_key(provider: str, model_name: str, prompt: str) -> str:
    digest = hashlib.sha256(f"{provider}\n{model_name}\n{prompt}".encode("utf-8")).hexdigest()
    return digest


def _read_cache(provider: str, model_name: str, prompt: str) -> str | None:
    if not _cache_enabled():
        return None
    path = CACHE_DIR / f"{_cache_key(provider, model_name, prompt)}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("text")


def _write_cache(provider: str, model_name: str, prompt: str, text: str) -> None:
    if not _cache_enabled():
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{_cache_key(provider, model_name, prompt)}.json"
    path.write_text(
        json.dumps(
            {"provider": provider, "model": model_name, "created_at": time.time(), "text": text},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _model_candidates(provider: str, primary_model: str | None = None, fallback_model: str | None = None) -> list[str]:
    normalized = normalize_provider(provider)
    if normalized == "openai":
        candidates = [
            primary_model or os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini"),
            fallback_model or os.getenv("OPENAI_FALLBACK_TEXT_MODEL", ""),
            "gpt-4.1-mini",
        ]
        return list(dict.fromkeys(model.strip() for model in candidates if model and model.strip()))
    if normalized == "xai":
        candidates = [
            primary_model or os.getenv("XAI_TEXT_MODEL", "grok-4.3"),
            fallback_model or os.getenv("XAI_FALLBACK_TEXT_MODEL", ""),
            "grok-4.3",
        ]
        return list(dict.fromkeys(model.strip() for model in candidates if model and model.strip()))
    candidates = [
        primary_model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        fallback_model or os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-latest"),
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ]
    return list(dict.fromkeys(model.strip() for model in candidates if model and model.strip()))


def _is_retryable_error(error: Exception) -> bool:
    if isinstance(error, AttributeError):
        return False
    message = str(error).lower()
    retryable = [
        "timeout",
        "deadline",
        "temporarily unavailable",
        "503",
        "500",
        "429",
        "rate",
        "quota",
        "connection",
        "remote end closed",
    ]
    return any(token in message for token in retryable)


def _is_model_error(error: Exception) -> bool:
    message = str(error).lower()
    return "404" in message or "not found" in message or "no longer available" in message or "not supported" in message


def generate_text(
    *,
    provider: str,
    api_key: str,
    prompt: str,
    system_prompt: str | None = None,
    primary_model: str | None = None,
    fallback_model: str | None = None,
    temperature: float = 0.7,
    retries: int | None = None,
    timeout: int | None = None,
    offline_factory: Callable[[], str] | None = None,
    return_metadata: bool = False,
    diagnostic_id: str = "",
) -> str | dict[str, Any]:
    provider = normalize_provider(provider)
    correlation = safe_diagnostic_label(diagnostic_id or "none", limit=24)
    if not str(api_key or "").strip():
        if offline_factory:
            text = offline_factory()
            LOGGER.warning("provider_offline_fixture id=%s provider=%s chars=%s", correlation, provider, len(text))
            if return_metadata:
                return {
                    "text": text,
                    "provenance": {
                        "status": "offline_synthetic",
                        "provider": provider,
                        "model": "",
                        "model_fallback": False,
                        "synthetic": True,
                        "cache_hit": False,
                        "response_character_count": len(text),
                    },
                }
            return text
        LOGGER.error("provider_failed id=%s provider=%s error=ProviderError:_missing_api_key", correlation, provider)
        raise ProviderError("Missing runtime API key")

    retries = max(1, int(retries or os.getenv("AI_RETRY_COUNT", "3")))
    timeout = max(10, int(timeout or os.getenv("AI_REQUEST_TIMEOUT", "60")))
    backoff_base = float(os.getenv("AI_BACKOFF_BASE_SECONDS", "2"))
    last_error: Exception | None = None

    candidates = _model_candidates(provider, primary_model, fallback_model)
    for model_index, model_name in enumerate(candidates):
        LOGGER.info(
            "provider_attempt id=%s provider=%s model=%s fallback=%s",
            correlation,
            provider,
            safe_diagnostic_label(model_name, limit=64),
            bool(model_index),
        )
        cached = _read_cache(provider, model_name, prompt)
        if cached:
            LOGGER.info(
                "provider_success id=%s provider=%s model=%s fallback=%s cache=true chars=%s",
                correlation,
                provider,
                safe_diagnostic_label(model_name, limit=64),
                bool(model_index),
                len(cached),
            )
            if return_metadata:
                return {
                    "text": cached,
                    "provenance": {
                        "status": "model_fallback_success" if model_index else "provider_success",
                        "provider": provider,
                        "model": model_name,
                        "model_fallback": bool(model_index),
                        "synthetic": False,
                        "cache_hit": True,
                        "response_character_count": len(cached),
                    },
                }
            return cached

        for attempt in range(retries):
            try:
                text = provider_generate_text(
                    prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    provider=provider,
                    api_key=api_key,
                    model_name=model_name or provider_model(provider),
                    timeout=timeout,
                )
                _write_cache(provider, model_name, prompt, text)
                LOGGER.info(
                    "provider_success id=%s provider=%s model=%s fallback=%s cache=false chars=%s",
                    correlation,
                    provider,
                    safe_diagnostic_label(model_name, limit=64),
                    bool(model_index),
                    len(text),
                )
                if return_metadata:
                    return {
                        "text": text,
                        "provenance": {
                            "status": "model_fallback_success" if model_index else "provider_success",
                            "provider": provider,
                            "model": model_name,
                            "model_fallback": bool(model_index),
                            "synthetic": False,
                            "cache_hit": False,
                            "response_character_count": len(text),
                        },
                    }
                return text
            except Exception as error:
                last_error = error
                LOGGER.warning(
                    "provider_attempt_failed id=%s provider=%s model=%s attempt=%s error=%s",
                    correlation,
                    provider,
                    safe_diagnostic_label(model_name, limit=64),
                    attempt + 1,
                    safe_exception_summary(error),
                )
                if _is_model_error(error):
                    break
                if attempt >= retries - 1 or not _is_retryable_error(error):
                    break
                time.sleep(backoff_base * (2**attempt))

    if offline_factory:
        text = offline_factory()
        LOGGER.warning("provider_offline_fixture id=%s provider=%s chars=%s", correlation, provider, len(text))
        if return_metadata:
            return {
                "text": text,
                "provenance": {
                    "status": "offline_synthetic",
                    "provider": provider,
                    "model": "",
                    "model_fallback": False,
                    "synthetic": True,
                    "cache_hit": False,
                    "response_character_count": len(text),
                },
            }
        return text
    safe_error = safe_exception_summary(last_error)
    LOGGER.error("provider_failed id=%s provider=%s error=%s", correlation, provider, safe_error)
    raise ProviderError(f"All text providers failed: {safe_error}")


def enqueue_text_generation(**kwargs: Any) -> Future:
    return _EXECUTOR.submit(generate_text, **kwargs)
