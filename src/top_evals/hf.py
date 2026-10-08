"""Hugging Face Hub model stats."""

import os
from typing import Any

import httpx

API = "https://huggingface.co/api/models"
EXPAND = ["createdAt", "downloads", "likes", "trendingScore", "safetensors", "cardData"]


def client() -> httpx.Client:
    """Return a Hub client, authenticated if `HF_TOKEN` is set."""
    token = os.environ.get("HF_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(headers=headers, timeout=30, follow_redirects=True)


def fetch_info(client: httpx.Client, repo: str) -> dict[str, Any] | None:
    """Return repo metadata, or None if the repo is missing or private."""
    r = client.get(f"{API}/{repo}", params=[("expand[]", e) for e in EXPAND])
    if r.status_code in (401, 403, 404):
        return None
    r.raise_for_status()
    return r.json()  # type: ignore[no-any-return]


def quantized_downloads(client: httpx.Client, repo: str) -> int:
    """Sum 30-day downloads of the repo's top 100 quantized derivatives."""
    params: dict[str, str | int] = {
        "filter": f"base_model:quantized:{repo}",
        "sort": "downloads",
        "limit": 100,
        "expand[]": "downloads",
    }
    r = client.get(API, params=params)
    r.raise_for_status()
    return sum(m.get("downloads", 0) for m in r.json())
