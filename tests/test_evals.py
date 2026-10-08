import httpx
import pytest

from top_evals.evals import aggregate, collect, key


@pytest.mark.parametrize(
    "a, b",
    [
        ("Terminal-Bench 2.1 (Pass@1)", "TerminalBench 2.1 (with terminus2)"),
        ("GPQA-Diamond", "GPQA Diamond (AA)"),
        ("HLE w/ Tools", "Humanity's Last Exam"),
        ("SWEBench Pro (Public)", "SWE-Bench Pro"),
        ("τ³-Banking", "Tau 3 Banking"),
        ("𝛕3-Banking", "τ³-Bench Banking"),
        ("HMMT Feb. 2026", "HMMT 2026 Feb"),
        ("BFCLv4", "BFCL (v4)"),
        ("MMLU Redux 5-shot", "MMLU-Redux (EM)"),
        ("DeepSWE v1.1", "DeepSWE (v1.1)"),
        ("OSWorld 2.0", "OSWorld-2"),
    ],
)
def test_key_merges_variants(a: str, b: str) -> None:
    assert key(a) == key(b)


@pytest.mark.parametrize(
    "a, b",
    [
        ("Terminal Bench 2.0", "Terminal Bench 2.1"),
        ("AIME 2025", "AIME 2026"),
        ("SWE-bench Pro", "SWE-bench Verified"),
    ],
)
def test_key_keeps_distinct_evals(a: str, b: str) -> None:
    assert key(a) != key(b)


def test_aggregate_counts_each_model_once() -> None:
    report = aggregate(
        {
            "a/One": ["HLE", "HLE (w/ tools)", "GPQA Diamond"],
            "b/Two": ["Humanity's Last Exam"],
            "c/Three": [],
        }
    )
    assert [(e.name, e.models) for e in report.evals] == [
        ("HLE", ["a/One", "b/Two"]),
        ("GPQA Diamond", ["a/One"]),
    ]
    assert report.by_model["a/One"] == ["hle", "gpqadiamond"]
    assert report.missing == ["c/Three"]


def test_collect_treats_unreadable_cards_as_missing() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/a/One/raw/main/README.md":
            return httpx.Response(
                200, text="## Eval\n| Benchmark | X |\n|-|-|\n| HLE | 1 |\n"
            )
        return httpx.Response(404)

    report = collect(
        ["a/One", "b/Gated"], httpx.Client(transport=httpx.MockTransport(handler))
    )

    assert [e.key for e in report.evals] == ["hle"]
    assert report.missing == ["b/Gated"]
