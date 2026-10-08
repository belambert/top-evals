from typing import Any

import httpx
import pytest


def or_model(id: str, hf_id: str, price: str = "0.000001", **kw: Any) -> dict[str, Any]:
    return {
        "id": id,
        "name": f"Org: {id.split('/')[-1]}",
        "hugging_face_id": hf_id,
        "pricing": {"prompt": "0", "completion": price},
        **kw,
    }


def hf_info(id: str, created: str, trending: int = 0, **kw: Any) -> dict[str, Any]:
    return {
        "id": id,
        "createdAt": created,
        "likes": 10,
        "trendingScore": trending,
        "downloads": 100,
        "safetensors": {"total": 27_000_000_000},
        "cardData": {"license": "mit"},
        **kw,
    }


OR_MODELS = [
    or_model(
        "acme/big",
        "acme/Big",
        benchmarks={"artificial_analysis": {"intelligence_index": 40.0}},
    ),
    or_model("acme/big:free", "acme/Big", price="0"),
    or_model("acme/small", "acme/Small", price="0.0000002"),
    or_model("acme/old", "acme/Old"),
    or_model("acme/gone", "acme/Gone"),
    {"id": "closed/model", "name": "Closed", "hugging_face_id": "", "pricing": {}},
]

HF_INFOS = {
    "acme/Big": hf_info("acme/Big", "2026-09-01T00:00:00.000Z", trending=50),
    "acme/Small": hf_info("acme/Small", "2026-08-01T00:00:00.000Z", trending=80),
    "acme/Old": hf_info("acme/Old", "2024-01-01T00:00:00.000Z", trending=999),
}

QUANTS = {"acme/Big": [{"downloads": 5}, {"downloads": 7}], "acme/Small": []}


def handler(req: httpx.Request) -> httpx.Response:
    if req.url.host == "openrouter.ai":
        return httpx.Response(200, json={"data": OR_MODELS})
    if f := req.url.params.get("filter"):
        return httpx.Response(200, json=QUANTS[f.removeprefix("base_model:quantized:")])
    repo = req.url.path.removeprefix("/api/models/")
    if repo in HF_INFOS:
        return httpx.Response(200, json=HF_INFOS[repo])
    return httpx.Response(404)


@pytest.fixture
def mock_client() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))
