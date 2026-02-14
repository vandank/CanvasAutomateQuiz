"""
Suggest or update quiz_id -> gradebook column name mapping from an exported Canvas Grades CSV
and cse412_quiz_metadata.json (or any quiz metadata with quiz_id and quiz_title).

Run after exporting the gradebook. Use the output to add entries to quiz_gradebook_columns.json
if a quiz is not yet mapped.

Usage:
  python build_gradebook_mapping.py path/to/Grades-....csv [--metadata cse412_quiz_metadata.json] [--course-id 249800] [--write]
  --write: merge suggestions into quiz_gradebook_columns.json (backup is created)
"""
import argparse
import csv
import json
import re
from pathlib import Path

METADATA_DEFAULT = "cse412_quiz_metadata.json"
MAPPING_FILE = "quiz_gradebook_columns.json"


def normalize(s: str) -> str:
    """Lowercase, collapse spaces, remove punctuation for fuzzy match."""
    s = s.lower().strip()
    s = re.sub(r"[\s\-_]+", "", s)
    s = re.sub(r"[^\w]", "", s)
    return s


def assignment_columns_from_csv(csv_path: Path) -> list[tuple[int, str]]:
    """Return list of (column_index, header) for columns that look like assignment columns (Name (id))."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        row = next(csv.reader(f))
    out = []
    for i, cell in enumerate(row):
        cell = (cell or "").strip()
        if not cell:
            continue
        if re.search(r"\(\d{5,}\)$", cell):
            out.append((i, cell))
    return out


def load_metadata(metadata_path: Path, course_id: str) -> list[dict]:
    """Load quiz metadata and return list of {quiz_id, quiz_title, ...} for the course."""
    with open(metadata_path, encoding="utf-8") as f:
        data = json.load(f)
    return [q for q in data if str(q.get("course_id")) == str(course_id)]


def suggest_mapping(
    assignment_headers: list[tuple[int, str]],
    quizzes: list[dict],
) -> dict[str, str]:
    """Suggest quiz_id -> column name by matching quiz_title to header (fuzzy)."""
    suggestions = {}
    for q in quizzes:
        qid = str(q["quiz_id"])
        title = (q.get("quiz_title") or "").strip()
        norm_title = normalize(title)
        best = None
        best_len = 0
        for _, header in assignment_headers:
            norm_header = normalize(header)
            if norm_title in norm_header or norm_header in norm_title:
                if len(header) > best_len:
                    best = header
                    best_len = len(header)
            elif norm_title and norm_header and (norm_title[:10] in norm_header or norm_header[:10] in norm_title):
                if len(header) > best_len:
                    best = header
                    best_len = len(header)
        if best:
            suggestions[qid] = best
    return suggestions


def main():
    parser = argparse.ArgumentParser(description="Suggest quiz_id -> gradebook column mapping from export + metadata.")
    parser.add_argument("csv_path", type=Path, help="Path to exported Grades CSV")
    parser.add_argument("--metadata", type=Path, default=Path(METADATA_DEFAULT), help="Quiz metadata JSON")
    parser.add_argument("--course-id", default="249800", help="Course ID to filter metadata")
    parser.add_argument("--write", action="store_true", help="Merge into quiz_gradebook_columns.json (creates backup)")
    args = parser.parse_args()

    if not args.csv_path.exists():
        raise SystemExit(f"CSV not found: {args.csv_path}")
    if not args.metadata.exists():
        raise SystemExit(f"Metadata not found: {args.metadata}")

    assignment_headers = assignment_columns_from_csv(args.csv_path)
    quizzes = load_metadata(args.metadata, args.course_id)
    suggestions = suggest_mapping(assignment_headers, quizzes)

    print("Suggested quiz_id -> assignment column (add missing ones to quiz_gradebook_columns.json):")
    for q in quizzes:
        qid = str(q["quiz_id"])
        title = q.get("quiz_title", "")
        col = suggestions.get(qid, "(no match)")
        print(f"  {qid}  {title!r}  ->  {col}")

    if args.write and suggestions:
        path = Path(MAPPING_FILE)
        existing = {}
        if path.exists():
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
            backup = path.parent / f"{path.stem}.backup.json"
            with open(backup, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            print(f"Backup written to {backup}")
        by_course = existing.get(args.course_id, {})
        for qid, col in suggestions.items():
            by_course[qid] = col
        existing[args.course_id] = by_course
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        print(f"Updated {path}")


if __name__ == "__main__":
    main()
