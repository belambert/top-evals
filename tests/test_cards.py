from top_evals.cards import extract_evals

ROW_PER_EVAL = """
# Model

## Architecture
| Property   | Value |
|------------|-------|
| Parameters | 27B   |
| Layers     | 64    |

## Evaluation
| Benchmark            | Ours | Other |
|----------------------|------|-------|
| **Reasoning**        |      |       |
| GPQA Diamond         | 90.1 | 88.0  |
| HLE<sup>1</sup>      | 40.2 | -     |
| Not run              | -    | -     |
| Average              | 65.0 | 60.0  |

```python
# not a heading
| Fake | 1 |
|------|---|
| Code | 2 |
```
"""

TRANSPOSED = """
## Results
| Model    | Size | AIME25 | SWE-bench Pro |
|----------|------|--------|---------------|
| **Ours** | 27B  | 90%    | 55%           |
| Other    | 30B  | 85%    | -             |
"""

NESTED_HEADINGS = """
## Benchmark Results
### Language
<table>
<tr><th></th><th>Ours</th></tr>
<tr><td><div>Agentic coding</div><div>Terminal Bench 2.1</div></td><td>73.0</td></tr>
<tr><td>BrowseComp<sup><a href="#n6">6</a></sup></td><td>83.4</td></tr>
</table>
"""

SUBROWS = """
## Eval
| Benchmark          | Ours |
|--------------------|------|
| TauBench V3        |      |
| &nbsp;&nbsp;Retail | 70.1 |
"""

UNHEADED = """
## Overview
| | | Ours |
|-|-|------|
| **Coding** | SWE-bench Verified | 77.6% |

| Benchmark | Ours |
|-----------|------|
| IFBench   | 79.8 |
"""


def test_row_per_eval_skips_specs_categories_and_code() -> None:
    assert extract_evals(ROW_PER_EVAL) == ["GPQA Diamond", "HLE"]


def test_transposed_table_reads_header() -> None:
    assert extract_evals(TRANSPOSED) == ["AIME25", "SWE-bench Pro"]


def test_html_table_under_nested_heading() -> None:
    assert extract_evals(NESTED_HEADINGS) == ["Terminal Bench 2.1", "BrowseComp"]


def test_indented_rows_inherit_parent() -> None:
    assert extract_evals(SUBROWS) == ["TauBench V3 Retail"]


def test_benchmark_header_outside_eval_section() -> None:
    # the first table has neither an eval heading nor a benchmark header
    assert extract_evals(UNHEADED) == ["IFBench"]


def test_no_tables() -> None:
    assert extract_evals("# Model\n\n![benchmarks](bench.png)\n") == []
