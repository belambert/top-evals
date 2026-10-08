"""Command-line interface."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import typer

from top_evals import evals, hf, models, openrouter
from top_evals.render import render_evals, render_models

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
        found = models.collect(now - timedelta(days=days), or_client, hf_client)[:limit]

    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(render_models(found, generated=now, days=days))
    (out / "models.json").write_text(json.dumps([m.to_dict() for m in found], indent=2))
    typer.echo(f"wrote {len(found)} models to {out}")


@app.command("evals")
def evals_cmd(
    site: Path = typer.Option(
        Path("site"), help="Site directory containing models.json."
    ),
    min_models: int = typer.Option(
        2, help="Only show evals reported by at least N models."
    ),
) -> None:
    """Find which evals the listed models' cards report and write the evals page."""
    listed = json.loads((site / "models.json").read_text())
    with hf.client() as client:
        report = evals.collect([m["hf_id"] for m in listed], client)

    names = {m["hf_id"]: m["name"] for m in listed}
    now = datetime.now(UTC)
    (site / "evals.html").write_text(render_evals(report, names, now, min_models))
    (site / "evals.json").write_text(json.dumps(report.to_dict(), indent=2))
    typer.echo(
        f"wrote {len(report.evals)} evals from {len(listed)} model cards to {site}"
    )
