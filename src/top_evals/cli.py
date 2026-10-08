"""Command-line interface."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import typer

from top_evals import hf, openrouter
from top_evals.models import collect
from top_evals.render import render

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Track the hottest open-weight models and their evals."""


@app.command()
def build(
    out: Path = typer.Option(Path("site"), help="Output directory."),
    days: int = typer.Option(
        365, help="Only include models created in the last N days."
    ),
    limit: int = typer.Option(50, help="Maximum number of models to list."),
) -> None:
    """Fetch hot open-weight models and write the static site."""
    now = datetime.now(UTC)
    with openrouter.client() as or_client, hf.client() as hf_client:
        models = collect(now - timedelta(days=days), or_client, hf_client)[:limit]

    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render(models, generated=now, days=days))
    (out / "models.json").write_text(
        json.dumps([m.to_dict() for m in models], indent=2)
    )
    typer.echo(f"wrote {len(models)} models to {out}")
