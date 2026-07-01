"""
Minimal client for a locally running Ollama instance.

Assumes Ollama is already installed and running (default: localhost:11434),
with the desired model already pulled (e.g. `ollama pull llama3.1`).
"""

from __future__ import annotations
import requests

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1"


class OllamaError(Exception):
    pass


def generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 300,
) -> str:
    """
    Send a prompt to Ollama and return the full generated text.
    Uses stream=False for simplicity -- waits for the complete response
    rather than streaming tokens.
    """
    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
    except requests.exceptions.ConnectionError as e:
        raise OllamaError(
            f"Could not connect to Ollama at {base_url}. "
            f"Is it running? Try 'ollama serve' or check 'ollama list'."
        ) from e
    except requests.exceptions.Timeout as e:
        raise OllamaError(
            f"Ollama did not respond within {timeout}s. The model may be "
            f"slow to load on first use, or the prompt may be very long."
        ) from e

    if response.status_code == 404:
        raise OllamaError(
            f"Model '{model}' not found. Try 'ollama pull {model}' first."
        )
    if response.status_code != 200:
        raise OllamaError(
            f"Ollama returned status {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    if "response" not in data:
        raise OllamaError(f"Unexpected response shape from Ollama: {data}")

    return data["response"]
