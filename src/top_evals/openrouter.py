"""OpenRouter model catalog."""

from typing import Any

import httpx

URL = "https://openrouter.ai/api/v1/models"


def client() -> httpx.Client:
    return httpx.Client(timeout=30)


def fetch_models(client: httpx.Client) -> list[dict[str, Any]]:
    """Return OpenRouter models that link to Hugging Face weights."""
    r = client.get(URL)
    r.raise_for_status()
    return [m for m in r.json()["data"] if m.get("hugging_face_id")]
