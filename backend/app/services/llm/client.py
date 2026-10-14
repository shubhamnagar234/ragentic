import asyncio
import time
from typing import Optional, AsyncGenerator

from litellm import acompletion, RateLimitError
from app.config import settings

def _normalize_model(model: str) -> str:
    """Ensure invalid model strings like gemini-3.6-flash fall back to valid gemini-2.5-flash."""
    if "gemini-3.6" in model:
        return "gemini/gemini-2.5-flash"
    return model


def get_primary_model() -> str:
    return _normalize_model(settings.LLM_PRIMARY_MODEL)


def get_lite_model() -> str:
    return _normalize_model(settings.LLM_LITE_MODEL)


def get_fallback_model() -> str:
    return _normalize_model(settings.LLM_FALLBACK_MODEL)


# Model ladder loaded from .env: primary → lite fallback → Groq
PRIMARY_MODEL = get_primary_model()
LITE_MODEL = get_lite_model()
FALLBACK_MODEL = get_fallback_model()

# Retry config for transient rate limits (per-minute quota)
_MAX_RETRIES = 2
_RETRY_BASE_DELAY = 10  # seconds

# ── Circuit Breaker ──────────────────────────────────────────────────────────
# Tracks models whose quota is exhausted so we skip them immediately.
# Cooldown is long (1 hour) because free-tier daily quota doesn't reset sooner.
_CIRCUIT_COOLDOWN = 3600  # seconds (1 hour)
_circuit_tripped: dict[str, float] = {}  # model → timestamp when tripped


def _is_tripped(model: str) -> bool:
    """Return True if this model's circuit is open (should be skipped)."""
    ts = _circuit_tripped.get(model)
    if ts is None:
        return False
    if time.monotonic() - ts > _CIRCUIT_COOLDOWN:
        # Cooldown expired — reset and allow a retry
        del _circuit_tripped[model]
        return False
    return True


def _trip(model: str) -> None:
    """Open the circuit for this model."""
    _circuit_tripped[model] = time.monotonic()
    print(f"[llm] Circuit tripped for {model} -- skipping for {_CIRCUIT_COOLDOWN // 60}min")


# ── Core call with retry ─────────────────────────────────────────────────────

async def _call_with_retry(model: str, api_key: str, **kwargs) -> str:
    """
    Call acompletion with limited exponential backoff on transient RateLimitError.
    Trips the circuit breaker when the daily quota is confirmed exhausted (limit: 0).
    """
    delay = _RETRY_BASE_DELAY
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            response = await acompletion(model=model, api_key=api_key, **kwargs)
            return response.choices[0].message.content
        except RateLimitError as e:
            err_str = str(e)
            # Daily quota exhausted — no point retrying
            if "limit: 0" in err_str or "GenerateRequestsPerDayPerProject" in err_str:
                _trip(model)
                raise e
            # Transient per-minute limit — back off and retry
            last_exc = e
            if attempt < _MAX_RETRIES - 1:
                print(f"[llm] Rate limited on {model}, retrying in {delay}s (attempt {attempt + 1}/{_MAX_RETRIES})")
                await asyncio.sleep(delay)
                delay *= 2
            else:
                raise e

    raise last_exc  # type: ignore


# ── Public API ───────────────────────────────────────────────────────────────

def _get_key_for_model(model: str) -> str:
    """Helper to pick the right API key based on model prefix."""
    if model.startswith("openrouter/"):
        openrouter_key = getattr(settings, "OPENROUTER_API_KEY", None)
        if not openrouter_key:
            raise ValueError(f"OPENROUTER_API_KEY is not set but model {model} was requested.")
        return openrouter_key
    if model.startswith("groq/"):
        if not settings.GROQ_API_KEY:
            raise ValueError(f"GROQ_API_KEY is not set but model {model} was requested.")
        return settings.GROQ_API_KEY
    return settings.GEMINI_API_KEY

async def get_llm_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    json_mode: bool = False,
    max_tokens: int = 1000,
) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs = {"messages": messages, "max_tokens": max_tokens, "temperature": 0.0}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    primary = get_primary_model()
    lite = get_lite_model()
    fallback = get_fallback_model()

    # 1. Primary Gemini model
    if not _is_tripped(primary):
        try:
            return await _call_with_retry(primary, _get_key_for_model(primary), **kwargs)
        except RateLimitError as e:
            print(f"[llm] Primary model unavailable, trying lite: {e}")
        except Exception as e:
            print(f"[llm] Primary model failed: {e}")
    else:
        print(f"[llm] Skipping {primary} (circuit open)")

    # 2. Lite Gemini model (higher free-tier RPM)
    if lite != primary and not _is_tripped(lite):
        try:
            return await _call_with_retry(lite, _get_key_for_model(lite), **kwargs)
        except RateLimitError as e:
            print(f"[llm] Lite model unavailable, trying OpenRouter: {e}")
        except Exception as e:
            print(f"[llm] Lite model failed: {e}")
    else:
        print(f"[llm] Skipping {lite} (circuit open or duplicate)")

    # 3. OpenRouter fallback
    openrouter_key = getattr(settings, "OPENROUTER_API_KEY", None)
    if openrouter_key:
        openrouter_model = "openrouter/google/gemini-2.5-flash"
        if not _is_tripped(openrouter_model):
            try:
                return await _call_with_retry(openrouter_model, openrouter_key, **kwargs)
            except Exception as e:
                print(f"[llm] OpenRouter fallback failed: {e}")

    # 4. Groq fallback
    if settings.GROQ_API_KEY and fallback.startswith("groq/"):
        if not _is_tripped(fallback):
            try:
                return await _call_with_retry(fallback, _get_key_for_model(fallback), **kwargs)
            except Exception as e:
                print(f"[llm] Groq fallback failed: {e}")
                raise e
        else:
            print(f"[llm] Skipping {fallback} (circuit open)")

    raise RuntimeError(
        "All LLM providers are unavailable or rate-limited. "
        "Please check your GEMINI_API_KEY or OPENROUTER_API_KEY in .env."
    )


async def stream_llm_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
) -> AsyncGenerator[str, None]:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    async def _stream(model: str, api_key: str):
        response = await acompletion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.0,
            api_key=api_key,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    primary = get_primary_model()
    lite = get_lite_model()
    fallback = get_fallback_model()

    # Try each model in order, skipping tripped ones
    candidates = []
    try:
        candidates.append((primary, _get_key_for_model(primary)))
    except ValueError:
        pass
        
    if lite != primary:
        try:
            candidates.append((lite, _get_key_for_model(lite)))
        except ValueError:
            pass

    # OpenRouter fallback
    openrouter_key = getattr(settings, "OPENROUTER_API_KEY", None)
    if openrouter_key:
        candidates.append(("openrouter/google/gemini-2.5-flash", openrouter_key))

    # Groq fallback
    if settings.GROQ_API_KEY and fallback.startswith("groq/"):
        try:
            candidates.append((fallback, _get_key_for_model(fallback)))
        except ValueError:
            pass

    for model, api_key in candidates:
        if _is_tripped(model):
            print(f"[llm] Skipping {model} for streaming (circuit open)")
            continue
        try:
            async for token in _stream(model, api_key):
                yield token
            return  # success — stop after first working model
        except RateLimitError as e:
            if "limit: 0" in str(e):
                _trip(model)
            print(f"[llm] Streaming rate-limited on {model}, trying next")
        except Exception as e:
            print(f"[llm] Streaming failed on {model}: {e}")
            with open("llm_error.txt", "a") as f:
                f.write(f"Streaming failed on {model}: {repr(e)}\n")

    yield "Error: All LLM providers are unavailable. Please try again later."
