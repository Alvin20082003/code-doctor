"""
backend/agents/llm.py

Thin LLM adapter.  Reads LLM_PROVIDER from the environment (default "ollama").

Supported providers:
  ollama   – local Ollama server via httpx (default)
  watsonx  – IBM watsonx.ai ModelInference (imported lazily; needs ibm-watsonx-ai)

Environment variables
---------------------
LLM_PROVIDER        "ollama" | "watsonx"  (default "ollama")

Ollama
  OLLAMA_URL        Base URL of the Ollama server  (default http://127.0.0.1:11434)
  OLLAMA_MODEL      Model tag                       (default granite3.3:8b)

watsonx
  WATSONX_APIKEY
  WATSONX_PROJECT_ID
  WATSONX_URL
  WATSONX_MODEL
"""
from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"),
            override=False)

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def generate(prompt: str) -> str:
    """
    Send *prompt* to the configured LLM and return the response text.

    Raises RuntimeError if the provider is unreachable or returns an error.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "watsonx":
        return await _watsonx(prompt)
    return await _ollama(prompt)


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

async def _ollama(prompt: str) -> str:
    url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "granite3.3:8b")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
        },
    }

    async with httpx.AsyncClient(timeout=170.0) as client:
        try:
            resp = await client.post(f"{url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            text: str = data.get("response", "")
            if not text:
                raise RuntimeError("Ollama returned an empty response")
            return text
        except httpx.ConnectError as exc:
            raise RuntimeError(f"Ollama unreachable at {url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Ollama request timed out: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Ollama HTTP error {exc.response.status_code}: {exc}") from exc


# ---------------------------------------------------------------------------
# watsonx (lazy import — not required unless LLM_PROVIDER=watsonx)
# ---------------------------------------------------------------------------

async def _watsonx(prompt: str) -> str:
    """
    Stub watsonx branch.  Only imports ibm-watsonx-ai when this branch is
    actually executed, so a missing package does not break the ollama path.
    """
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
    except ImportError as exc:
        raise RuntimeError(
            "ibm-watsonx-ai is not installed. "
            "Run: pip install ibm-watsonx-ai"
        ) from exc

    api_key    = os.environ["WATSONX_APIKEY"]
    project_id = os.environ["WATSONX_PROJECT_ID"]
    url        = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    model_id   = os.environ.get("WATSONX_MODEL", "ibm/granite-3-3-8b-instruct")

    credentials = Credentials(url=url, api_key=api_key)
    model = ModelInference(
        model_id=model_id,
        credentials=credentials,
        project_id=project_id,
        params={"temperature": 0.1, "max_new_tokens": 2048},
    )

    import asyncio
    response = await asyncio.to_thread(model.generate_text, prompt)
    if not response:
        raise RuntimeError("watsonx returned an empty response")
    return response
