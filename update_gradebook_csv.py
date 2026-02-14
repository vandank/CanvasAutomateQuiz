"""
Update a Canvas gradebook export CSV with quiz attempt grades (1 = on-time, 0 = late or not attempted).
Uses Option B: read the exported CSV, fill only the chosen assignment column, preserve everything else.

Usage:
  set CANVAS_API_TOKEN=your_token
  python update_gradebook_csv.py path/to/Grades-....csv --quiz-id 1938135 [--course-id 249800]
  python update_gradebook_csv.py path/to/Grades-....csv --quiz-id 1938135 --assignment-column "ERDiagram Quizz (7176714)"

Output: writes path/to/Grades-....-updated.csv (or -out path for custom output).
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def log(msg: str) -> None:
    """Print and flush so output appears immediately (e.g. before slow API calls)."""
    print(msg)
    sys.stdout.flush()

from canvas_paginated_fetch import fetch_all_pages
from fetch_enrollments import fetch_all_enrollments
from fetch_quiz_metadata import fetch_quiz_due_at

BASE_URL_DEFAULT = "https://canvas.asu.edu/api/v1"
METADATA_FILE = "cse412_quiz_metadata.json"
MAPPING_FILE = "quiz_gradebook_columns.json"
ID_HEADER = "ID"
GRADE_ON_TIME = "1.00"
GRADE_LATE_OR_NOT = "0.00"


def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def get_assignment_column(course_id: str, quiz_id: str, assignment_column_arg: Optional[str]) -> str:
    """Resolve gradebook assignment column name: --assignment-column, then metadata file, then mapping file."""
    if assignment_column_arg:
        return assignment_column_arg
    qid = str(quiz_id)
    cid = str(course_id)
    # 1) Try quiz metadata (built by build_quiz_metadata_index.py from API)
    meta_path = Path(METADATA_FILE)
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            quiz_list = json.load(f)
        for q in quiz_list:
            if str(q.get("course_id")) == cid and str(q.get("quiz_id")) == qid:
                col = q.get("gradebook_column")
                if col:
                    return col
                break
    # 2) Fall back to manual mapping file
    path = Path(MAPPING_FILE)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            mapping = json.load(f)
        by_course = mapping.get(cid)
        if by_course:
            col = by_course.get(qid)
            if col:
                return col
    raise SystemExit(
        f"Assignment column for quiz_id {qid} not found. Run build_quiz_metadata_index.py to refresh "
        f"{METADATA_FILE}, or add an entry to {MAPPING_FILE}, or pass --assignment-column 'Exact Name (id)'."
    )


def build_user_grades(base_url: str, token: str, course_id: str, quiz_id: str) -> dict[int, str]:
    """Return dict: user_id -> '1.00' (on-time) or '0.00' (late or not attempted)."""
    quiz_due_at = fetch_quiz_due_at(base_url, token, course_id, quiz_id)
    due_dt = parse_ts(quiz_due_at)

    quiz_url = f"{base_url}/courses/{course_id}/quizzes/{quiz_id}/submissions"
    quiz_subs, _ = fetch_all_pages(
        quiz_url,
        token,
        params={"include[]": "user", "per_page": 100},
    )
    enrollments = fetch_all_enrollments(base_url, token, course_id)

    attempt_map = {s["user_id"]: s for s in quiz_subs}
    user_ids = {e.get("user", {}).get("id") for e in enrollments if e.get("user")}

    grades = {}
    for uid in user_ids:
        if uid is None:
            continue
        sub = attempt_map.get(uid)
        if not sub:
            grades[uid] = GRADE_LATE_OR_NOT
            continue
        finished_at_raw = sub.get("finished_at")
        if finished_at_raw is None:
            grades[uid] = GRADE_LATE_OR_NOT
            continue
        finished_at = parse_ts(finished_at_raw)
        grades[uid] = GRADE_ON_TIME if finished_at <= due_dt else GRADE_LATE_OR_NOT
    return grades


def update_csv(
    csv_path: Path,
    assignment_column: str,
    user_grades: dict[int, str],
    out_path: Optional[Path],
) -> Path:
    """Read CSV, set assignment column from user_grades (keyed by ID), write to out_path. Returns output path."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        raise SystemExit("CSV is empty.")

    header = rows[0]
    try:
        id_col = header.index(ID_HEADER)
    except ValueError:
        raise SystemExit(f"CSV header must contain '{ID_HEADER}'.")

    try:
        assign_col = header.index(assignment_column)
    except ValueError:
        raise SystemExit(
            f"Assignment column '{assignment_column}' not found in CSV header. "
            "Check spelling and parentheses (e.g. 'ERDiagram Quizz (7176714)')."
        )

    # Preserve rows 1–3 (header + metadata); update data rows from row index 3 onward
    for i in range(3, len(rows)):
        row = rows[i]
        if len(row) <= max(id_col, assign_col):
            continue
        try:
            raw_id = row[id_col].strip()
            uid = int(raw_id) if raw_id else None
        except ValueError:
            continue
        if uid is not None and uid in user_grades:
            row[assign_col] = user_grades[uid]

    if out_path is None:
        stem = csv_path.stem
        out_path = csv_path.parent / f"{stem}-updated.csv"

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Update Canvas gradebook CSV with quiz attempt grades (on-time=1, late/not attempted=0)."
    )
    parser.add_argument("csv_path", type=Path, help="Path to exported Grades CSV")
    parser.add_argument("--quiz-id", required=True, help="Canvas quiz ID (e.g. 1938135)")
    parser.add_argument("--assignment-column", help="Exact assignment column name as in CSV (e.g. 'ERDiagram Quizz (7176714)')")
    parser.add_argument("--course-id", default=os.environ.get("CANVAS_COURSE_ID", "249800"), help="Canvas course ID")
    parser.add_argument("--base-url", default=os.environ.get("CANVAS_BASE_URL", BASE_URL_DEFAULT), help="Canvas API base URL")
    parser.add_argument("--out", type=Path, help="Output CSV path (default: <csv_path>-updated.csv)")
    args = parser.parse_args()

    log("update_gradebook_csv: starting...")

    token = os.environ.get("CANVAS_API_TOKEN")
    if not token:
        raise SystemExit("Set CANVAS_API_TOKEN in the environment.")

    assignment_column = get_assignment_column(args.course_id, args.quiz_id, args.assignment_column)
    log(f"Assignment column: {assignment_column}")

    log("Fetching quiz due date, submissions, and enrollments...")
    try:
        user_grades = build_user_grades(args.base_url, token, args.course_id, args.quiz_id)
    except Exception as e:
        log(f"Error fetching from Canvas API: {e}")
        raise
    log(f"Computed grades for {len(user_grades)} students.")

    out_path = update_csv(args.csv_path, assignment_column, user_grades, args.out)
    log(f"Wrote {out_path}")
    log("Import this file in Canvas: Grades → Actions → Import.")


if __name__ == "__main__":
    main()
