import asyncio
import time
from typing import Optional, AsyncGenerator

from litellm import acompletion, RateLimitError
from app.config import settings

# Model ladder loaded from .env: primary → lite fallback → Groq
PRIMARY_MODEL = settings.LLM_PRIMARY_MODEL
LITE_MODEL = settings.LLM_LITE_MODEL
FALLBACK_MODEL = settings.LLM_FALLBACK_MODEL

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
    print(f"[llm] Circuit tripped for {model} — skipping for {_CIRCUIT_COOLDOWN // 60}min")


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

    kwargs = {"messages": messages, "max_tokens": max_tokens}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    # 1. Primary Gemini model
    if not _is_tripped(PRIMARY_MODEL):
        try:
            return await _call_with_retry(PRIMARY_MODEL, _get_key_for_model(PRIMARY_MODEL), **kwargs)
        except RateLimitError as e:
            print(f"[llm] Primary model unavailable, trying lite: {e}")
        except Exception as e:
            print(f"[llm] Primary model failed: {e}")
    else:
        print(f"[llm] Skipping {PRIMARY_MODEL} (circuit open)")

    # 2. Lite Gemini model (higher free-tier RPM)
    if not _is_tripped(LITE_MODEL):
        try:
            return await _call_with_retry(LITE_MODEL, _get_key_for_model(LITE_MODEL), **kwargs)
        except RateLimitError as e:
            print(f"[llm] Lite model unavailable, trying Groq: {e}")
        except Exception as e:
            print(f"[llm] Lite model failed: {e}")
    else:
        print(f"[llm] Skipping {LITE_MODEL} (circuit open)")

    # 3. Groq fallback
    if settings.GROQ_API_KEY:
        if not _is_tripped(FALLBACK_MODEL):
            try:
                return await _call_with_retry(FALLBACK_MODEL, _get_key_for_model(FALLBACK_MODEL), **kwargs)
            except Exception as e:
                print(f"[llm] Groq fallback failed: {e}")
                raise e
        else:
            print(f"[llm] Skipping {FALLBACK_MODEL} (circuit open)")

    raise RuntimeError(
        "All LLM providers are unavailable or rate-limited. "
        "Please add a GROQ_API_KEY to .env or wait for quota to reset."
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
            api_key=api_key,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    # Try each model in order, skipping tripped ones
    candidates = []
    try:
        candidates.append((PRIMARY_MODEL, _get_key_for_model(PRIMARY_MODEL)))
    except ValueError:
        pass
        
    try:
        candidates.append((LITE_MODEL, _get_key_for_model(LITE_MODEL)))
    except ValueError:
        pass

    if settings.GROQ_API_KEY:
        try:
            candidates.append((FALLBACK_MODEL, _get_key_for_model(FALLBACK_MODEL)))
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

    yield "Error: All LLM providers are unavailable. Please try again later."
