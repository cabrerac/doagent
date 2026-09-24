"""Optional provider clients shared by repository examples and experiments.

Provider SDKs are imported only when a client is created.
They are not DOAgent dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Callable, Dict, Optional

from .env_file import load_dotenv

PROXY_BASE_URL = "https://llm.hpc.cam.ac.uk"
PROXY_MODEL = "moonshotai/Kimi-K3"
PROXY_API_KEY_ENV = "LITE_LLM_API_KEY"


def proxy_api_key() -> str:
    """Return the university proxy key from the process environment.

    A .env file at the repository root is loaded first if it exists.
    A key already set in the environment is left unchanged.

    Returns:
        The value of LITE_LLM_API_KEY.

    Raises:
        RuntimeError:
            If that variable is not set.
    """
    load_dotenv()
    key = os.environ.get(PROXY_API_KEY_ENV)
    if not key:
        raise RuntimeError(
            f"No university API key found. Set {PROXY_API_KEY_ENV}."
        )
    return key


@dataclass(frozen=True)
class LLMResponse:
    """Normalized model response with reproducibility and usage metadata."""

    text: str
    provider: str
    requested_model: str
    response_model: str
    usage: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "text": self.text,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "response_model": self.response_model,
            "usage": dict(self.usage),
        }


LLMClient = Callable[..., LLMResponse]


def create_llm_client(
    *,
    api_key: Optional[str] = None,
    provider: str = "openai",
    timeout: float = 60.0,
) -> LLMClient:
    """Create a provider client returning text, model identity, and token usage.

    The OpenAI-compatible provider talks to the university proxy.
    The key is taken from the api_key argument, then from LITE_LLM_API_KEY.
    A .env file at the repository root is loaded first if it exists.
    Variables already set in the environment are left unchanged.

    Args:
        api_key:
            Provider key. When omitted, the matching environment variable is used.
        provider:
            openai for the university proxy, or gemini.
        timeout:
            Request timeout in seconds.

    Returns:
        A callable that takes model, messages, and temperature.
        The callable returns text, model identity, and token usage.
    """
    load_dotenv()
    normalized_provider = provider.lower()
    if normalized_provider == "openai":
        key = api_key or proxy_api_key()
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The OpenAI SDK is required. Install it with: pip install openai"
            ) from exc

        sdk_client = OpenAI(
            api_key=key,
            base_url=PROXY_BASE_URL,
            timeout=timeout,
        )

        def _openai_call(
            *,
            model: str,
            messages: list,
            temperature: float = 0.0,
        ) -> LLMResponse:
            response = sdk_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            usage = response.usage
            return LLMResponse(
                text=response.choices[0].message.content or "",
                provider="openai",
                requested_model=model,
                response_model=getattr(response, "model", model),
                usage={
                    "input_tokens": int(
                        getattr(usage, "prompt_tokens", 0) or 0
                    ),
                    "output_tokens": int(
                        getattr(usage, "completion_tokens", 0) or 0
                    ),
                    "total_tokens": int(
                        getattr(usage, "total_tokens", 0) or 0
                    ),
                },
            )

        return _openai_call

    if normalized_provider == "gemini":
        key = (
            api_key
            or os.environ.get("DOAGENT_GEMINI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        if not key:
            raise RuntimeError(
                "No Gemini API key found. Set GEMINI_API_KEY or "
                "DOAGENT_GEMINI_API_KEY."
            )
        try:
            from google import genai  # type: ignore[import-untyped]
            from google.genai import types  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The google-genai SDK is required. Install it with: "
                "pip install google-genai"
            ) from exc

        sdk_client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(timeout=int(timeout * 1000)),
        )

        def _gemini_call(
            *,
            model: str,
            messages: list,
            temperature: float = 0.0,
        ) -> LLMResponse:
            system_parts = [
                message["content"]
                for message in messages
                if message["role"] == "system"
            ]
            user_parts = [
                message["content"]
                for message in messages
                if message["role"] != "system"
            ]
            config = types.GenerateContentConfig(
                system_instruction=(
                    "\n".join(system_parts) if system_parts else None
                ),
                temperature=temperature,
            )
            response = sdk_client.models.generate_content(
                model=model,
                contents="\n".join(user_parts),
                config=config,
            )
            usage = getattr(response, "usage_metadata", None)
            input_tokens = int(
                getattr(usage, "prompt_token_count", 0) or 0
            )
            output_tokens = int(
                getattr(usage, "candidates_token_count", 0) or 0
            )
            total_tokens = int(
                getattr(usage, "total_token_count", 0)
                or input_tokens + output_tokens
            )
            return LLMResponse(
                text=response.text or "",
                provider="gemini",
                requested_model=model,
                response_model=getattr(response, "model_version", model)
                or model,
                usage={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                },
            )

        return _gemini_call

    raise ValueError(f"Unsupported LLM provider: {provider!r}")


def create_llm_tool(
    *,
    api_key: Optional[str] = None,
    provider: str = "openai",
    timeout: float = 60.0,
    temperature: float = 0.0,
) -> Callable[..., str]:
    """Create the text-only callable expected by existing agent policies."""
    client = create_llm_client(
        api_key=api_key,
        provider=provider,
        timeout=timeout,
    )

    def _tool(*, model: str, messages: list) -> str:
        return client(
            model=model,
            messages=messages,
            temperature=temperature,
        ).text

    return _tool
