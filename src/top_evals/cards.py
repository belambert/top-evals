"""Extract eval names from Hugging Face model cards."""

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

RAW = "https://huggingface.co/{repo}/raw/main/README.md"

EVAL_HEADING = re.compile(
    r"eval|benchmark|performance|result|preparedness|comparison", re.I
)
LABEL_HEADER = re.compile(r"benchmark|^eval|metric|^task", re.I)
# spec and summary rows that pass the "has a number" test but aren't evals
NOT_EVAL = re.compile(
    r"param|architecture|layers|context|^#|^overall|^average|^mean|^model$|^size|,|^[\d.%\s-]*$"
    r"|bpw|footprint|density|^vs\b|^(thinking|benchmark) avg",
    re.I,
)
# tables with one row per model and one column per eval
MODEL_HEADER = re.compile(r"^(model|variant)", re.I)
SUBROW = "\u21b3"  # marks indented rows that belong to the row above

MD_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
MD_SEPARATOR = re.compile(r"^[\s|:-]+$")
HTML_TABLE = re.compile(r"<table.*?</table>", re.I | re.S)
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE = re.compile(r"^\s*```")


@dataclass
class Table:
    heading: str
    rows: list[list[str]]


def fetch_card(client: httpx.Client, repo: str) -> str | None:
    """Return the model card markdown, or None if it can't be read."""
    r = client.get(RAW.format(repo=repo))
    if r.status_code in (401, 403, 404):
        return None
    r.raise_for_status()
    return r.text


def extract_evals(card: str) -> list[str]:
    """Return eval names from the card's benchmark tables, in order of appearance."""
    names = [n for t in tables(card) if is_eval_table(t) for n in labels(t)]
    return list(dict.fromkeys(names))


def is_eval_table(t: Table) -> bool:
    header = [c for row in t.rows[:3] for c in row]
    return bool(EVAL_HEADING.search(t.heading)) or any(
        LABEL_HEADER.search(c) for c in header
    )


def labels(t: Table) -> list[str]:
    """Return the names of evals that have at least one score in the table."""
    if t.rows[0] and MODEL_HEADER.match(t.rows[0][0]):
        return column_labels(t)
    return row_labels(t)


def column_labels(t: Table) -> list[str]:
    """Read eval names from the header of a table with one row per model."""
    header, body = t.rows[0], t.rows[1:]
    scored = [
        h
        for i, h in enumerate(header[1:], 1)
        if any(i < len(r) and re.search(r"\d", r[i]) for r in body)
    ]
    return [h for h in scored if h and not NOT_EVAL.search(h)]


def row_labels(t: Table) -> list[str]:
    """Read eval names from the label column of a table with one row per eval."""
    col = label_column(t.rows)
    out, parent = [], ""
    for row in t.rows[1:]:
        if col is not None and col < len(row):
            label, values = row[col], row[col + 1 :]
        else:
            label, values = split_unlabeled(row)
        if label.startswith(SUBROW):
            label = f"{parent} {label.removeprefix(SUBROW).strip()}"
        else:
            parent = label
        if (
            label
            and not NOT_EVAL.search(label)
            and any(re.search(r"\d", v) for v in values)
        ):
            out.append(label)
    return out


def label_column(rows: list[list[str]]) -> int | None:
    """Return the index of the header column naming the benchmarks, if any."""
    for row in rows[:3]:
        for i, c in enumerate(row):
            if LABEL_HEADER.search(c):
                return i
    return None


def split_unlabeled(row: list[str]) -> tuple[str, list[str]]:
    """Use the last text cell before the first numeric cell as the label."""
    # handles layouts like `| category | benchmark | 81.2 | ...` with no header
    first_num = next(
        (i for i, c in enumerate(row) if re.match(r"[-+]?\d", c)), len(row)
    )
    label = next((c for c in reversed(row[:first_num]) if c), "")
    return label, row[first_num:]


def tables(card: str) -> list[Table]:
    """Return markdown and HTML tables, each tagged with its heading path."""
    out: list[Table] = []
    path: dict[int, str] = {}
    block: list[str] = []
    in_code = False

    def heading() -> str:
        return " / ".join(path.values())

    def flush() -> None:
        rows = [split_md_row(r) for r in block if not MD_SEPARATOR.match(r)]
        if len(rows) > 1:
            out.append(Table(heading(), rows))
        block.clear()

    # mask HTML tables so their lines aren't scanned as markdown
    html = [
        (card.count("\n", 0, m.start()), m.group()) for m in HTML_TABLE.finditer(card)
    ]
    masked = HTML_TABLE.sub(lambda m: "\n" * m.group().count("\n"), card)

    html_iter = iter(html)
    nxt = next(html_iter, None)
    for i, line in enumerate(masked.splitlines()):
        while nxt and nxt[0] <= i:
            out.append(Table(heading(), parse_html_table(nxt[1])))
            nxt = next(html_iter, None)
        if FENCE.match(line):
            in_code = not in_code
        if in_code:
            continue
        if MD_TABLE_ROW.match(line):
            block.append(line)
            continue
        flush()
        if m := HEADING.match(line):
            level = len(m.group(1))
            path = {k: v for k, v in path.items() if k < level} | {
                level: clean(m.group(2))
            }
    flush()
    return [t for t in out if len(t.rows) > 1]


def split_md_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [
        (SUBROW if c.lstrip().startswith("&nbsp;") else "") + clean(c) for c in cells
    ]


def clean(s: str) -> str:
    """Strip markdown, HTML, and footnote markers from a cell."""
    s = re.sub(r"<sup>.*?</sup>", "", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_`†‡§¹²↗]|\\", "", s)
    return " ".join(s.split())


def parse_html_table(src: str) -> list[list[str]]:
    p = _TableParser()
    p.feed(src)
    return p.rows


class _TableParser(HTMLParser):
    """Collect cell text; a cell made of several divs keeps only the last one."""

    # e.g. Qwen cards render `<div>Agentic coding</div><div>SWE-bench Pro</div>`

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.parts: list[str] | None = None
        self.in_sup = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "sup":
            self.in_sup = True
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.parts = [""]
        elif self.parts is not None and tag == "div":
            self.parts.append("")
        elif self.parts is not None and tag == "br":
            self.parts[-1] += " "

    def handle_endtag(self, tag: str) -> None:
        if tag == "sup":
            self.in_sup = False
        elif tag in ("td", "th") and self.parts is not None:
            parts = [p for p in map(clean, self.parts) if p]
            self.row.append(parts[-1] if len(parts) > 1 else " ".join(parts))
            self.parts = None
        elif tag == "tr" and self.row:
            self.rows.append(self.row)

    def handle_data(self, data: str) -> None:
        if self.parts is not None and not self.in_sup:
            self.parts[-1] += data
