from datetime import UTC, datetime

import httpx

from top_evals.models import cheapest_output_price, collect, group_by_repo
from top_evals.openrouter import fetch_models

from .conftest import OR_MODELS, or_model

SINCE = datetime(2026, 1, 1, tzinfo=UTC)


def test_fetch_models_drops_closed(mock_client: httpx.Client) -> None:
    assert "closed/model" not in [m["id"] for m in fetch_models(mock_client)]


def test_group_by_repo_merges_variants() -> None:
    groups = group_by_repo([m for m in OR_MODELS if m["hugging_face_id"]])
    assert [m["id"] for m in groups["acme/Big"]] == ["acme/big", "acme/big:free"]


def test_collect_filters_and_ranks(mock_client: httpx.Client) -> None:
    models = collect(SINCE, mock_client, mock_client)

    # old repo is filtered by date, missing repo is skipped
    assert [m.hf_id for m in models] == ["acme/Small", "acme/Big"]

    big = models[1]
    assert big.name == "big"
    assert big.or_ids == ["acme/big", "acme/big:free"]
    assert big.total_downloads == 112
    assert big.aa_index == 40.0
    assert big.price_out == 1.0
    assert big.license == "mit"


def test_cheapest_output_price_ignores_free() -> None:
    assert cheapest_output_price([or_model("a", "A", price="0")]) is None
    prices = [or_model("a", "A", "0.000003"), or_model("b", "A", "0.000002")]
    assert cheapest_output_price(prices) == 2.0
