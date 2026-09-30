"""Score extraction against the eval cases with a local Ollama model.

Runs every case in evals/cases/ and evals/private/, prints precision / recall
per case and per set, and appends one row per set to evals/results.md.
Ollama must be running locally.

Usage: .venv/bin/python -m evals.run --note "baseline"
Pass --model to evaluate a model other than the default qwen2.5:14b.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import typer
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.table import Table

from src import ollama_client
from src.transcript_cleaner import clean_transcript
from src.transcripts import read_transcript


EVALS_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = EVALS_DIR / "cases"
PRIVATE_DIR = EVALS_DIR / "private"
RESULTS_PATH = EVALS_DIR / "results.md"
FIELDS = {
    "debrief": ["commitments", "questions_asked", "people_mentioned"],
    "meeting": ["action_items", "decisions"],
}
FIELD_LABELS = {
    "commitments": "Commitments",
    "questions_asked": "Questions",
    "people_mentioned": "People",
    "action_items": "Action items",
    "decisions": "Decisions",
}
RESULTS_HEADER = (
    "# Eval Results\n\n"
    "Each cell is precision / recall, summed over cases. Public rows use only "
    "`evals/cases/` and are reproducible from the repo. Private rows use "
    "`evals/private/` and never name cases. Retries counts extractions that "
    "needed the one JSON retry.\n\n"
    "| Date | Commit | Model | Note | Cases | "
    + " | ".join(FIELD_LABELS.values())
    + " | Total recall | Retries | Per case |\n"
    "|" + "---|" * (len(FIELD_LABELS) + 8) + "\n"
)

console = Console()


@dataclass
class FieldScore:
    matched: int
    expected: int
    extracted: int


@dataclass
class CaseResult:
    name: str
    private: bool
    scores: dict[str, FieldScore]
    retried: bool
    failed: bool


def item_text(item: str | BaseModel) -> str:
    """Text that keywords are checked against: every field except owner and evidence."""
    if isinstance(item, str):
        return item
    values = item.model_dump(exclude={"owner", "evidence"}).values()
    return " ".join(value for value in values if value)


def owner_matches(expected_owner: str, extracted_owner: str | None) -> bool:
    """Match when the expected owner equals the extracted one or appears in it as whole words."""
    if not extracted_owner:
        return False
    pattern = rf"\b{re.escape(expected_owner)}\b"
    return re.search(pattern, extracted_owner, re.IGNORECASE) is not None


def item_matches(expected: dict, item: str | BaseModel) -> bool:
    text = item_text(item).lower()
    if not all(keyword.lower() in text for keyword in expected["keywords"]):
        return False
    owner = expected.get("owner")
    return owner is None or owner_matches(owner, getattr(item, "owner", None))


def count_matches(expected_items: list[dict], extracted_items: list) -> int:
    """Pair each expected item with the first unused extracted item that matches it."""
    unused = list(extracted_items)
    matched = 0
    for expected in expected_items:
        for index, item in enumerate(unused):
            if item_matches(expected, item):
                unused.pop(index)
                matched += 1
                break
    return matched


def score_case(expected: dict, extraction: BaseModel | None) -> dict[str, FieldScore]:
    """Score one extraction against an expected.json; a failed extraction extracts nothing."""
    scores = {}
    for field in FIELDS[expected["mode"]]:
        expected_items = expected[field]
        extracted_items = getattr(extraction, field) if extraction else []
        scores[field] = FieldScore(
            count_matches(expected_items, extracted_items),
            len(expected_items),
            len(extracted_items),
        )
    return scores


def load_expected(case_dir: Path) -> dict:
    return json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))


def case_dirs(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        path for path in folder.iterdir() if path.is_dir() and not path.is_symlink()
    )


def run_case(case_dir: Path, model: str, private: bool) -> CaseResult:
    """Run one case through the real extraction, counting Ollama calls to detect a retry."""
    expected = load_expected(case_dir)
    transcript = clean_transcript(read_transcript(case_dir / "transcript.txt"))
    extract = (
        ollama_client.extract_debrief
        if expected["mode"] == "debrief"
        else ollama_client.extract_meeting
    )

    calls = 0
    original_generate = ollama_client._generate

    def counting_generate(*args):
        nonlocal calls
        calls += 1
        return original_generate(*args)

    ollama_client._generate = counting_generate
    try:
        extraction = extract(transcript, model=model)
        failed = False
    except RuntimeError as error:
        if not isinstance(error.__cause__, ValidationError):
            raise
        extraction = None
        failed = True
    finally:
        ollama_client._generate = original_generate

    return CaseResult(
        case_dir.name, private, score_case(expected, extraction), calls > 1, failed
    )


def total_scores(results: list[CaseResult]) -> dict[str, FieldScore]:
    totals = {field: FieldScore(0, 0, 0) for field in FIELD_LABELS}
    for result in results:
        for field, score in result.scores.items():
            totals[field].matched += score.matched
            totals[field].expected += score.expected
            totals[field].extracted += score.extracted
    return totals


def case_score(result: CaseResult) -> FieldScore:
    scores = result.scores.values()
    return FieldScore(
        sum(score.matched for score in scores),
        sum(score.expected for score in scores),
        sum(score.extracted for score in scores),
    )


def ratio(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.2f}" if denominator else "—"


def precision_recall(score: FieldScore) -> str:
    return f"{ratio(score.matched, score.extracted)} / {ratio(score.matched, score.expected)}"


def total_recall(totals: dict[str, FieldScore]) -> str:
    return ratio(
        sum(score.matched for score in totals.values()),
        sum(score.expected for score in totals.values()),
    )


def retries_cell(results: list[CaseResult]) -> str:
    cell = f"{sum(result.retried for result in results)}/{len(results)}"
    failed = sum(result.failed for result in results)
    return f"{cell}, {failed} failed" if failed else cell


def results_row(
    label: str,
    results: list[CaseResult],
    model: str,
    commit: str,
    note: str,
    today: date,
) -> str:
    """One results.md row; private rows never name their cases."""
    totals = total_scores(results)
    per_case = (
        "—"
        if label == "private"
        else "; ".join(
            f"{result.name} {precision_recall(case_score(result))}" for result in results
        )
    )
    cells = [
        today.isoformat(),
        commit,
        model,
        note,
        f"{label} ({len(results)})",
        *(precision_recall(totals[field]) for field in FIELD_LABELS),
        total_recall(totals),
        retries_cell(results),
        per_case,
    ]
    return "| " + " | ".join(cells) + " |\n"


def current_commit() -> str:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=EVALS_DIR, capture_output=True, text=True, check=True
        ).stdout.strip()

    commit = git("rev-parse", "--short", "HEAD")
    return f"{commit}+dirty" if git("status", "--porcelain") else commit


def append_results(results_path: Path, rows: list[str]) -> None:
    if not results_path.exists():
        results_path.write_text(RESULTS_HEADER, encoding="utf-8")
    with results_path.open("a", encoding="utf-8") as results_file:
        results_file.writelines(rows)


def split_results(results: list[CaseResult]) -> list[tuple[str, list[CaseResult]]]:
    """Group results into public and private sets, dropping an empty set."""
    public = [result for result in results if not result.private]
    private = [result for result in results if result.private]
    return [(label, group) for label, group in [("public", public), ("private", private)] if group]


def print_tables(results: list[CaseResult]) -> None:
    cases_table = Table(title="Cases (precision / recall)")
    for column in ["Case", *FIELD_LABELS.values(), "Total", "Retried"]:
        cases_table.add_column(column)
    for result in results:
        name = f"{result.name} (private)" if result.private else result.name
        cases_table.add_row(
            name,
            *(
                precision_recall(result.scores[field]) if field in result.scores else ""
                for field in FIELD_LABELS
            ),
            precision_recall(case_score(result)),
            "failed" if result.failed else "yes" if result.retried else "",
        )
    console.print(cases_table)

    totals_table = Table(title="Totals (precision / recall)")
    for column in ["Set", *FIELD_LABELS.values(), "Total recall", "Retries"]:
        totals_table.add_column(column)
    for label, group in split_results(results):
        totals = total_scores(group)
        totals_table.add_row(
            f"{label} ({len(group)})",
            *(precision_recall(totals[field]) for field in FIELD_LABELS),
            total_recall(totals),
            retries_cell(group),
        )
    console.print(totals_table)


def main(
    model: str = typer.Option(ollama_client.DEFAULT_MODEL, "--model", help="Local Ollama model to evaluate."),
    note: str = typer.Option("", "--note", help="Short label for this run in results.md."),
) -> None:
    """Run every eval case and append the scores to evals/results.md."""
    cases = [(path, False) for path in case_dirs(PUBLIC_DIR)]
    cases += [(path, True) for path in case_dirs(PRIVATE_DIR)]

    results = []
    for case_dir, private in cases:
        with console.status(f"Running {case_dir.name}..."):
            results.append(run_case(case_dir, model, private))

    print_tables(results)

    commit = current_commit()
    today = date.today()
    append_results(
        RESULTS_PATH,
        [
            results_row(label, group, model, commit, note, today)
            for label, group in split_results(results)
        ],
    )
    console.print(f"Appended to {RESULTS_PATH}")


if __name__ == "__main__":
    typer.run(main)
