import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from top_evals import cli, hf, openrouter
from top_evals.models import Model
from top_evals.render import compact, render

from .conftest import handler

NOW = datetime(2026, 10, 7, tzinfo=UTC)


def model(**kw: object) -> Model:
    fields: dict[str, object] = dict(
        hf_id="acme/Big",
        name="Big",
        or_ids=["acme/big"],
        created=NOW,
        likes=1500,
        trending=42,
        downloads=1_000_000,
        quant_downloads=250_000,
        params=27_000_000_000,
        license="mit",
        price_out=None,
        aa_index=None,
    )
    return Model(**(fields | kw))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "n, want",
    [
        (None, "–"),
        (999, "999"),
        (1500, "1.5K"),
        (2_000_000, "2M"),
        (27e9, "27B"),
        (2.8e12, "2.8T"),
    ],
)
def test_compact(n: float | None, want: str) -> None:
    assert compact(n) == want


def test_render_escapes_and_formats() -> None:
    html = render([model(name="<script>x</script>")], generated=NOW, days=30)
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "<script>x</script>" not in html
    assert "1.2M" in html and "27B" in html


def test_build_writes_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # fresh clients, since the CLI opens and closes each one
    def mock() -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(openrouter, "client", mock)
    monkeypatch.setattr(hf, "client", mock)

    res = CliRunner().invoke(cli.app, ["build", "--out", str(tmp_path), "--limit", "1"])

    assert res.exit_code == 0, res.output
    assert "acme/Small" in (tmp_path / "index.html").read_text()
    assert [m["hf_id"] for m in json.loads((tmp_path / "models.json").read_text())] == [
        "acme/Small"
    ]
