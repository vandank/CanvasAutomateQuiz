import requests
import json
import os

from fetch_quiz_metadata import fetch_course_quiz_assignments

BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://canvas.asu.edu/api/v1")
TOKEN = os.environ["CANVAS_API_TOKEN"]
COURSE_ID = os.environ.get("CANVAS_COURSE_ID", "249800")

headers = {"Authorization": f"Bearer {TOKEN}"}

# Fetch quiz->assignment mapping so we can store assignment_id and gradebook column name
print("Fetching assignments (quiz -> gradebook column)...")
quiz_assignments = fetch_course_quiz_assignments(BASE_URL, TOKEN, COURSE_ID)
print(f"  Found {len(quiz_assignments)} quiz-linked assignments")

quiz_index = []
url = f"{BASE_URL}/courses/{COURSE_ID}/quizzes"
params = {"per_page": 100}

while url:
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()

    quizzes = r.json()
    for q in quizzes:
        entry = {
            "course_id": COURSE_ID,
            "quiz_id": q["id"],
            "quiz_title": q["title"],
            "due_at": q.get("due_at"),
            "unlock_at": q.get("unlock_at"),
            "lock_at": q.get("lock_at"),
            "published": q.get("published"),
            "points_possible": q.get("points_possible"),
        }
        info = quiz_assignments.get(q["id"])
        if info:
            entry["assignment_id"] = info["assignment_id"]
            entry["assignment_name"] = info["assignment_name"]
            entry["gradebook_column"] = info["gradebook_column"]
        quiz_index.append(entry)

    url = None
    link = r.headers.get("Link")
    if link:
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part[part.find("<") + 1 : part.find(">")]

    params = None

# write metadata
with open("cse412_quiz_metadata.json", "w", encoding="utf-8") as f:
    json.dump(quiz_index, f, indent=2)

print(f"✅ Found {len(quiz_index)} quizzes for course {COURSE_ID}")
