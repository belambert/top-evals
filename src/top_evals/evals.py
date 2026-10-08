"""Count which evals model cards report."""

import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

from top_evals import cards

WORKERS = 8

# names that normalize differently but mean the same eval
ALIASES = {
    "humanityslastexam": "hle",
    "hlefull": "hle",
    "hletext": "hle",
    "hletextonly": "hle",
    "gpqa": "gpqadiamond",
    "sweverified": "swebenchverified",
    "swepro": "swebenchpro",
    "swemultilingual": "swebenchmultilingual",
    "mcpatlaspublic": "mcpatlas",
    "lcb6": "livecodebench6",
    "automationbenchpublic": "automationbench",
    "charxiv": "charxivrq",
    "charxivreasoning": "charxivrq",
    "nl2repobench": "nl2repo",
}


@dataclass
class EvalUsage:
    key: str
    name: str
    models: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.models)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"count": self.count}


@dataclass
class Report:
    evals: list[EvalUsage]
    by_model: dict[str, list[str]]  # hf id -> eval keys found on its card
    missing: list[str]  # cards with no readable eval tables

    def to_dict(self) -> dict[str, Any]:
        return {
            "evals": [e.to_dict() for e in self.evals],
            "by_model": self.by_model,
            "missing": self.missing,
        }


def collect(repos: list[str], client: httpx.Client) -> Report:
    """Fetch each repo's card and count the evals it reports, most used first."""
    with ThreadPoolExecutor(WORKERS) as pool:
        texts = list(pool.map(lambda r: cards.fetch_card(client, r), repos))
    found = {r: cards.extract_evals(t) if t else [] for r, t in zip(repos, texts)}
    return aggregate(found)


def aggregate(found: dict[str, list[str]]) -> Report:
    """Group raw eval names by normalized key, counting each model once per eval."""
    models: dict[str, list[str]] = defaultdict(list)
    names: dict[str, Counter[str]] = defaultdict(Counter)
    by_model = {}

    for repo, labels in found.items():
        keyed = [(k, label) for label in labels if (k := key(label))]
        for k, label in keyed:
            names[k][display(label)] += 1
        by_model[repo] = list(dict.fromkeys(k for k, _ in keyed))
        for k in by_model[repo]:
            models[k].append(repo)

    evals = [
        EvalUsage(k, names[k].most_common(1)[0][0], ms) for k, ms in models.items()
    ]
    evals.sort(key=lambda e: (-e.count, e.name.lower()))
    return Report(evals, by_model, [r for r, labels in found.items() if not labels])


def key(label: str) -> str:
    """Normalize an eval name so spelling variants compare equal."""
    s = unwrap_version(label.lower())
    for a, b in (("𝛕", "tau"), ("τ", "tau"), ("³", "3"), ("²", "2")):
        s = s.replace(a, b)
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)

    # tool settings, shots, metrics, and averages are variants of the same eval
    s = re.sub(r"\b(w/o?|with|without|no|wo)\.?\s*(tools?|python|search|ci)\b.*", "", s)
    s = re.sub(r"\b(\d+-shot|pass@\d+|avg@?\d*|average|em|acc|elo|rating)\b", "", s)

    s = re.sub(r"[^a-z0-9.]", "", s)
    s = re.sub(r"(?<=[a-z])v(?=\d)", "", s)  # v1.1 -> 1.1
    s = re.sub(r"20(\d\d)", r"\1", s)  # 2026 -> 26
    s = re.sub(r"(\d)\.0(?!\d)", r"\1", s)  # 2.0 -> 2
    s = re.sub(r"(?<!\d)\.|\.(?!\d)", "", s)  # keep dots only inside versions
    s = re.sub(r"tau(?:bench)?(\d?)(?:bench)?", r"tau\1", s)
    s = re.sub(r"hmmt(\d\d)(feb|nov)", r"hmmt\2\1", s)
    return ALIASES.get(s, s)


def display(label: str) -> str:
    """Return a readable name without parenthetical details."""
    return " ".join(re.sub(r"\(.*?\)", "", unwrap_version(label)).split()) or label


def unwrap_version(s: str) -> str:
    """Turn `DeepSWE (v1.1)` into `DeepSWE v1.1` so the version survives."""
    return re.sub(r"\(\s*([vV]?\d[\d.]*)\s*\)", r" \1", s)
