"""Render the model list as a static HTML page."""

from datetime import datetime

from jinja2 import Environment, PackageLoader

from top_evals.evals import Report
from top_evals.models import Model

env = Environment(loader=PackageLoader("top_evals"), autoescape=True)


def render_models(models: list[Model], generated: datetime, days: int) -> str:
    """Return the index page listing `models`."""
    tmpl = env.get_template("index.html.j2")
    return tmpl.render(page="models", models=models, generated=generated, days=days)


def render_evals(
    report: Report, names: dict[str, str], generated: datetime, min_models: int
) -> str:
    """Return the page of evals reported by at least `min_models` models."""
    evals = [e for e in report.evals if e.count >= min_models]
    return env.get_template("evals.html.j2").render(
        page="evals",
        evals=evals,
        max_count=max((e.count for e in evals), default=1),
        names=names,
        n_models=len(report.by_model),
        missing=report.missing,
        generated=generated,
        min_models=min_models,
    )


def compact(n: float | None) -> str:
    """Format a count like 1.2M or 27B."""
    if n is None:
        return "–"
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= div:
            return f"{n / div:.1f}".removesuffix(".0") + unit
    return str(int(n))


env.filters["compact"] = compact
