# Top Evals

**Live page:** <https://belambert.github.io/top-evals/> ·
[models.json](https://belambert.github.io/top-evals/models.json)

Track the hottest open-weight models and, eventually, their evals. A daily
GitHub Actions job builds a static page listing the models and publishes it
to GitHub Pages.

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

## Usage

Install dependencies and build the site into `site/`:

    uv sync
    uv run top-evals build

Options:

| Option    | Default | Description                                     |
|-----------|---------|-------------------------------------------------|
| `--out`   | `site`  | Output directory.                               |
| `--days`  | `365`   | Only include models created in the last N days. |
| `--limit` | `50`    | Maximum number of models to list.               |

The output is `index.html` plus `models.json` with the same data.

Set `HF_TOKEN` to raise Hugging Face rate limits. It is optional.

## Deployment

`.github/workflows/pages.yml` builds and deploys the site on pushes to `main`,
daily at 06:00 UTC, and on manual dispatch. To enable it, set
**Settings → Pages → Source** to **GitHub Actions**. Optionally add an
`HF_TOKEN` repository secret.

## Development

    uv run pytest
    uv run black src tests
    uv run isort src tests
    uv run mypy src tests

Tests use mocked HTTP and need no network access.
