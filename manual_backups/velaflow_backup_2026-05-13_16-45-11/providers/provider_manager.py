import hashlib
import json
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

import google.generativeai as genai


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "outputs" / "cache" / "text"
_EXECUTOR = ThreadPoolExecutor(max_workers=int(os.getenv("AI_QUEUE_WORKERS", "3")))


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


def _model_candidates(primary_model: str | None = None, fallback_model: str | None = None) -> list[str]:
    candidates = [
        primary_model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        fallback_model or os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-latest"),
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ]
    return list(dict.fromkeys(model.strip() for model in candidates if model and model.strip()))


def _is_retryable_error(error: Exception) -> bool:
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


def _gemini_generate_once(api_key: str, model_name: str, prompt: str, timeout: int) -> str:
    if not api_key:
        raise ProviderError("Missing GEMINI_API_KEY in .env")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt, request_options={"timeout": timeout})
    return (response.text or "").strip()


def generate_text(
    *,
    provider: str,
    api_key: str,
    prompt: str,
    primary_model: str | None = None,
    fallback_model: str | None = None,
    retries: int | None = None,
    timeout: int | None = None,
    offline_factory: Callable[[], str] | None = None,
) -> str:
    provider = (provider or "gemini").lower()
    if provider != "gemini":
        raise ProviderError(f"Unsupported text provider: {provider}")

    retries = max(1, int(retries or os.getenv("AI_RETRY_COUNT", "3")))
    timeout = max(10, int(timeout or os.getenv("AI_REQUEST_TIMEOUT", "60")))
    backoff_base = float(os.getenv("AI_BACKOFF_BASE_SECONDS", "2"))
    last_error: Exception | None = None

    for model_name in _model_candidates(primary_model, fallback_model):
        cached = _read_cache(provider, model_name, prompt)
        if cached:
            return cached

        for attempt in range(retries):
            try:
                text = _gemini_generate_once(api_key, model_name, prompt, timeout)
                _write_cache(provider, model_name, prompt, text)
                return text
            except Exception as error:
                last_error = error
                if _is_model_error(error):
                    break
                if attempt >= retries - 1 or not _is_retryable_error(error):
                    break
                time.sleep(backoff_base * (2**attempt))

    if offline_factory:
        return offline_factory()
    raise ProviderError(f"All text providers failed: {last_error}")


def enqueue_text_generation(**kwargs: Any) -> Future:
    return _EXECUTOR.submit(generate_text, **kwargs)
