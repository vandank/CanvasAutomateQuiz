import os
from datetime import datetime, timezone
from canvas_paginated_fetch import fetch_all_pages
from fetch_enrollments import fetch_all_enrollments
from fetch_quiz_metadata import fetch_quiz_due_at

BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://canvas.asu.edu/api/v1")
TOKEN = os.environ["CANVAS_API_TOKEN"]
COURSE_ID = os.environ.get("CANVAS_COURSE_ID", "249800")
QUIZ_ID = os.environ.get("CANVAS_QUIZ_ID")  # e.g. 1938135 for ER diagram, 1938812 for ER diagram (2)

# ---- helpers ----
def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

# ---- fetch data ----
quiz_due_at = fetch_quiz_due_at(BASE_URL, TOKEN, COURSE_ID, QUIZ_ID)
due_dt = parse_ts(quiz_due_at)

quiz_url = f"{BASE_URL}/courses/{COURSE_ID}/quizzes/{QUIZ_ID}/submissions"
quiz_subs, quiz_users = fetch_all_pages(
    quiz_url,
    TOKEN,
    params={"include[]": "user", "per_page": 100}
)

enrollments = fetch_all_enrollments(BASE_URL, TOKEN, COURSE_ID)

# ---- build lookup tables ----
attempt_map = {s["user_id"]: s for s in quiz_subs}
user_map = {u["id"]: u for u in quiz_users}

students = []
for e in enrollments:
    u = e.get("user", {})
    students.append({
        "user_id": u.get("id"),
        "name": u.get("name"),
        "login_id": u.get("login_id")
    })

# ---- classify ----
on_time = []
late = []
not_attempted = []

for s in students:
    sub = attempt_map.get(s["user_id"])

    if not sub:
        not_attempted.append(s)
        continue

    finished_at = parse_ts(sub["finished_at"])

    record = {
        **s,
        "score": sub.get("score"),
        "finished_at": sub.get("finished_at")
    }

    if finished_at > due_dt:
        late.append(record)
    else:
        on_time.append(record)

# ---- write reports ----
with open("quiz_on_time.txt", "w") as f:
    for s in on_time:
        f.write(f"{s['name']} ({s['login_id']}) | score={s['score']}\n")

with open("quiz_late.txt", "w") as f:
    for s in late:
        f.write(
            f"{s['name']} ({s['login_id']}) | "
            f"score={s['score']} | finished={s['finished_at']}\n"
        )

with open("quiz_not_attempted.txt", "w") as f:
    for s in not_attempted:
        f.write(f"{s['name']} ({s['login_id']})\n")

print("✅ Report generated:")
print(f"   On-time       : {len(on_time)}")
print(f"   Late          : {len(late)}")
print(f"   Not attempted : {len(not_attempted)}")
