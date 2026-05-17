#!/usr/bin/env python3
"""Verify manuscript prose numbers against empirical logs and tables."""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from pathlib import Path


NUMBER_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?%?")
SKIP_COMMAND_RE = re.compile(
    r"\\(?:label|ref|input|includegraphics|cite[tp]?|citealp|hypersetup|bibliographystyle|bibliography)\{[^}]*\}"
)


def numeric_value(raw: str) -> float | None:
    clean = raw.replace(",", "").rstrip("%")
    try:
        return float(clean)
    except ValueError:
        return None


def should_skip(raw: str, value: float) -> bool:
    if re.match(r"^(19|20)\d{2}$", raw):
        return True
    if value == 0:
        return True
    if value == int(value) and 1 <= value <= 20 and "." not in raw and "," not in raw:
        return True
    return False


def strip_markup(text: str) -> str:
    doc_start = text.find(r"\begin{document}")
    if doc_start >= 0:
        text = text[doc_start:]
    text = SKIP_COMMAND_RE.sub("", text)
    text = re.sub(r"\\(?:begin|end)\{[^}]*\}", "", text)
    text = re.sub(r"\\begin\{tabular\}.*?\\end\{tabular\}", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return text


def extract_prose_numbers(path: Path) -> list[dict[str, object]]:
    text = strip_markup(path.read_text(errors="ignore"))
    results: list[dict[str, object]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        if re.match(r"^\s*\\(setcounter|renewcommand|newcommand|def\\)", line):
            continue
        for match in NUMBER_RE.finditer(line):
            raw = match.group()
            value = numeric_value(raw)
            if value is None or should_skip(raw, value):
                continue
            start = max(0, match.start() - 50)
            end = min(len(line), match.end() + 50)
            results.append(
                {
                    "number": raw,
                    "value": value,
                    "line": line_no,
                    "context": line[start:end].strip(),
                }
            )
    return results


def extract_reference_numbers(project: Path) -> set[float]:
    patterns = [
        "logs/*.log",
        "tables/*.tex",
        "tables/*.csv",
        "analysis/output/logs/*.log",
        "analysis/output/tables/*.tex",
        "analysis/output/tables/*.csv",
        "analysis/output/*.md",
    ]
    numbers: set[float] = set()
    for pattern in patterns:
        for raw_path in glob.glob(str(project / pattern)):
            path = Path(raw_path)
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            for match in re.finditer(r"-?\d[\d,]*(?:\.\d+)?", text):
                value = numeric_value(match.group())
                if value is not None and value != 0:
                    numbers.add(value)
    return numbers


def number_matches(value: float, references: set[float], tolerance: float) -> bool:
    if value in references:
        return True
    for ref in references:
        if ref == 0:
            continue
        candidates = (ref, ref * 100, ref / 100, ref * 1000, ref / 1000)
        for candidate in candidates:
            denom = abs(candidate) if candidate else 1.0
            if abs(value - candidate) / denom <= tolerance:
                return True
    return False


def build_report(
    paper: Path,
    project: Path,
    paper_numbers: list[dict[str, object]],
    references: set[float],
    tolerance: float,
) -> tuple[str, int]:
    matched = []
    unmatched = []
    for entry in paper_numbers:
        if number_matches(float(entry["value"]), references, tolerance):
            matched.append(entry)
        else:
            unmatched.append(entry)

    lines = [
        "# Business Number Audit",
        "",
        "## Automated Number Check",
        "",
        f"- Paper: `{paper}`",
        f"- Project: `{project}`",
        f"- Reference numbers found: {len(references)}",
        f"- Prose numbers found: {len(paper_numbers)}",
        f"- Matched: {len(matched)}",
        f"- Unmatched: {len(unmatched)}",
        "",
        "## Unmatched Numbers",
        "",
    ]
    if unmatched:
        lines.append("| Number | Line | Context |")
        lines.append("|--------|------|---------|")
        for entry in unmatched:
            context = str(entry["context"]).replace("|", "\\|")
            lines.append(f"| {entry['number']} | {entry['line']} | {context} |")
    else:
        lines.append("None.")

    lines.extend(["", "## Matched Numbers", ""])
    if matched:
        lines.append("| Number | Line | Context |")
        lines.append("|--------|------|---------|")
        for entry in matched:
            context = str(entry["context"]).replace("|", "\\|")
            lines.append(f"| {entry['number']} | {entry['line']} | {context} |")
    else:
        lines.append("None.")

    return "\n".join(lines) + "\n", len(unmatched)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="Project directory containing logs and tables")
    parser.add_argument("--paper", required=True, help="Manuscript file: .tex, .md, or .qmd")
    parser.add_argument("--output", help="Optional markdown report path")
    parser.add_argument("--tolerance", type=float, default=0.02, help="Relative numeric tolerance")
    parser.add_argument("--allow-unmatched", action="store_true", help="Exit 0 even with unmatched numbers")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = Path(args.project).resolve()
    paper = Path(args.paper).resolve()
    if not paper.exists():
        print(f"ERROR: paper file not found: {paper}", file=sys.stderr)
        return 2
    if not project.exists():
        print(f"ERROR: project directory not found: {project}", file=sys.stderr)
        return 2

    paper_numbers = extract_prose_numbers(paper)
    references = extract_reference_numbers(project)
    report, unmatched_count = build_report(paper, project, paper_numbers, references, args.tolerance)

    if args.output:
        output = Path(args.output)
        output.write_text(report)
    else:
        sys.stdout.write(report)

    if unmatched_count and not args.allow_unmatched:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
