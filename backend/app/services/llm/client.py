import json
from typing import Optional, AsyncGenerator
from litellm import acompletion
from app.config import settings

# LLM fallback chain
PRIMARY_MODEL = "gemini/gemini-2.5-flash"
FALLBACK_MODEL = "groq/llama3-70b-8192"


async def get_llm_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    json_mode: bool = False,
    max_tokens: int = 1000,
) -> str:
    """
    Sends a prompt to the LLM and returns the response text.
    Tries primary model first, falls back to secondary on failure.
    """
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    import litellm

    litellm.api_key = settings.GEMINI_API_KEY

    kwargs = {
        "model": PRIMARY_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "api_key": settings.GEMINI_API_KEY,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = await acompletion(**kwargs)
        return response.choices[0].message.content

    except Exception as e:
        print(f"[llm] Primary model failed: {e}. Trying fallback...")

        try:
            kwargs["model"] = FALLBACK_MODEL
            kwargs["api_key"] = settings.GROQ_API_KEY
            response = await acompletion(**kwargs)
            return response.choices[0].message.content

        except Exception as e2:
            print(f"[llm] Fallback model also failed: {e2}")
            raise e2


async def stream_llm_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
) -> AsyncGenerator[str, None]:
    """
    Streams LLM response token by token.
    Used for the SSE streaming chat endpoint.
    """
    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    import litellm

    litellm.api_key = settings.GEMINI_API_KEY

    try:
        response = await acompletion(
            model=PRIMARY_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            api_key=settings.GEMINI_API_KEY,
            stream=True,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    except Exception as e:
        print(f"[llm] Streaming failed: {e}")
        yield f"Error: {str(e)}"
