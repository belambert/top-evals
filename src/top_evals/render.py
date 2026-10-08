"""Render the model list as a static HTML page."""

from datetime import datetime

from jinja2 import Environment, PackageLoader

from top_evals.models import Model

env = Environment(loader=PackageLoader("top_evals"), autoescape=True)


def render(models: list[Model], generated: datetime, days: int) -> str:
    """Return the index page for `models`."""
    tmpl = env.get_template("index.html.j2")
    return tmpl.render(models=models, generated=generated, days=days)


def compact(n: float | None) -> str:
    """Format a count like 1.2M or 27B."""
    if n is None:
        return "–"
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= div:
            return f"{n / div:.1f}".removesuffix(".0") + unit
    return str(int(n))


env.filters["compact"] = compact
