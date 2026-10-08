# Top Evals

**Live pages:** [models](https://belambert.github.io/top-evals/) ·
[evals](https://belambert.github.io/top-evals/evals.html) ·
[models.json](https://belambert.github.io/top-evals/models.json) ·
[evals.json](https://belambert.github.io/top-evals/evals.json)

Track the hottest open-weight models and the evals they report. A daily
GitHub Actions job builds two static pages, one listing the models and one
ranking the evals their model cards use, and publishes them to GitHub Pages.

## How Models Are Chosen

1. **Candidates** come from the [OpenRouter model catalog](https://openrouter.ai/api/v1/models).
   Only models with a `hugging_face_id` (i.e. open weights) are kept. Being
   served on OpenRouter is the bar for "notable", which filters out the
   fine-tunes and re-uploads that dominate raw Hugging Face listings.
   Variants such as `:free` and `:batch` are merged by Hugging Face repo.
2. **Stats** for each repo come from the Hugging Face Hub API: creation date,
   likes, trending score, parameter count, license, and 30-day downloads.
   Downloads include the top 100 quantized derivatives (GGUF, MLX, FP8, ...),
   since most local usage goes through those.
3. **Ranking** keeps models created in the last `--days` days and sorts by
   Hugging Face trending score (recent likes). The page's columns can be
   re-sorted in the browser.

The page also shows the Artificial Analysis intelligence index and the
cheapest output price, both taken from OpenRouter.

## How Evals Are Counted

For each listed model, `top-evals evals` downloads the Hugging Face model card
and reads the benchmark tables in it, both Markdown and HTML.

- **Which tables:** tables under a heading mentioning evaluation, benchmarks,
  performance, or results, plus any table with a "Benchmark" or "Eval"
  column. Spec tables (layers, parameters, ...) are skipped.
- **Which names:** the label of each row with at least one score. Tables with
  one row per model and one column per eval (a `Model` header) are read
  from the header instead.
- **Normalization:** names are merged across spelling variants, so
  `Terminal-Bench 2.1 (Pass@1)` and `TerminalBench 2.1 (with terminus2)`
  count as one eval. Tool settings, shot counts, and metrics are ignored,
  but versions are kept, so Terminal-Bench 2.0 and 2.1 stay separate.
- **Counting:** each model counts once per eval. That includes evals the card
  reports only for comparison models, since the question is which evals the
  card presents.

Cards that publish results only as images can't be read. The evals page lists
them separately.

## Usage

Install dependencies and build the site into `site/`:

    uv sync
    uv run top-evals build
    uv run top-evals evals

`build` options:

| Option    | Default | Description                                     |
|-----------|---------|-------------------------------------------------|
| `--out`   | `site`  | Output directory.                               |
| `--days`  | `365`   | Only include models created in the last N days. |
| `--limit` | `50`    | Maximum number of models to list.               |

`build` writes `index.html` plus `models.json` with the same data. `evals`
reads `models.json` and writes `evals.html` plus `evals.json`, which also
records the evals found on each card.

`evals` options:

| Option         | Default | Description                                    |
|----------------|---------|------------------------------------------------|
| `--site`       | `site`  | Site directory containing `models.json`.       |
| `--min-models` | `2`     | Only show evals reported by at least N models. |

Set `HF_TOKEN` to raise Hugging Face rate limits. It is optional.

## Deployment

`.github/workflows/pages.yml` runs `build` then `evals` and deploys the site
on pushes to `main`,
daily at 06:00 UTC, and on manual dispatch. To enable it, set
**Settings → Pages → Source** to **GitHub Actions**. Optionally add an
`HF_TOKEN` repository secret.

## Development

    uv run pytest
    uv run black src tests
    uv run isort src tests
    uv run mypy src tests

Tests use mocked HTTP and need no network access.
