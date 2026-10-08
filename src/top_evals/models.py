"""Build a ranked list of hot open-weight models."""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import httpx

from top_evals import hf, openrouter

WORKERS = 8


@dataclass
class Model:
    hf_id: str
    name: str
    or_ids: list[str]
    created: datetime
    likes: int
    trending: int
    downloads: int  # base repo, last 30 days
    quant_downloads: int  # quantized derivatives, last 30 days
    params: int | None
    license: str | None
    price_out: float | None  # cheapest USD per 1M output tokens
    aa_index: float | None  # Artificial Analysis intelligence index

    @property
    def total_downloads(self) -> int:
        return self.downloads + self.quant_downloads

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
            "created": self.created.isoformat(),
            "total_downloads": self.total_downloads,
        }


def collect(
    since: datetime, or_client: httpx.Client, hf_client: httpx.Client
) -> list[Model]:
    """Return OpenRouter-hosted open models created since `since`, hottest first."""
    groups = group_by_repo(openrouter.fetch_models(or_client))

    with ThreadPoolExecutor(WORKERS) as pool:
        infos = dict(
            zip(groups, pool.map(lambda r: hf.fetch_info(hf_client, r), groups))
        )
        recent = {r: i for r, i in infos.items() if i and created_at(i) >= since}
        quants = pool.map(lambda r: hf.quantized_downloads(hf_client, r), recent)
        models = [build(groups[r], i, q) for (r, i), q in zip(recent.items(), quants)]

    return sorted(models, key=lambda m: (m.trending, m.likes), reverse=True)


def group_by_repo(or_models: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group OpenRouter variants (e.g. `:free`, `:batch`) by Hugging Face repo."""
    groups = defaultdict(list)
    for m in or_models:
        groups[m["hugging_face_id"]].append(m)
    return dict(groups)


def build(or_models: list[dict[str, Any]], info: dict[str, Any], quant: int) -> Model:
    """Merge OpenRouter entries and Hub metadata for one repo."""
    main = min(or_models, key=lambda m: len(m["id"]))
    aa = (main.get("benchmarks") or {}).get("artificial_analysis") or {}
    return Model(
        hf_id=info["id"],
        name=main["name"].split(": ", 1)[-1],
        or_ids=sorted(m["id"] for m in or_models),
        created=created_at(info),
        likes=info.get("likes", 0),
        trending=info.get("trendingScore", 0),
        downloads=info.get("downloads", 0),
        quant_downloads=quant,
        params=(info.get("safetensors") or {}).get("total"),
        license=(info.get("cardData") or {}).get("license"),
        price_out=cheapest_output_price(or_models),
        aa_index=aa.get("intelligence_index"),
    )


def created_at(info: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(info["createdAt"])


def cheapest_output_price(or_models: list[dict[str, Any]]) -> float | None:
    """Return the lowest paid output price in USD per 1M tokens."""
    # free variants are rate-limited promos, not a real price signal
    prices = [float(m["pricing"]["completion"]) * 1e6 for m in or_models]
    paid = [p for p in prices if p > 0]
    return min(paid) if paid else None
