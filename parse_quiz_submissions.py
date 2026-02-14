import json
import sys
from datetime import datetime

if len(sys.argv) != 2:
    print("Usage: python parse_quiz_submissions.py quiz_submissions_raw.json")
    sys.exit(1)

input_file = sys.argv[1]

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

quiz_submissions = data.get("quiz_submissions", [])
users = data.get("users", [])

# Build lookup: user_id -> user info
user_map = {u["id"]: u for u in users}

summary = []

for s in quiz_submissions:
    user = user_map.get(s["user_id"], {})
    summary.append({
        "name": user.get("name", "UNKNOWN"),
        "login_id": user.get("login_id", "UNKNOWN"),
        "user_id": s["user_id"],
        "attempt": s.get("attempt"),
        "score": s.get("score"),
        "points_possible": s.get("quiz_points_possible"),
        "started_at": s.get("started_at"),
        "finished_at": s.get("finished_at"),
        "time_spent_seconds": s.get("time_spent"),
        "workflow_state": s.get("workflow_state")
    })

# ---- OUTPUT FILES ----

# 1) Human-readable TXT
with open("quiz_attempts_summary.txt", "w", encoding="utf-8") as f:
    for r in summary:
        f.write(
            f"{r['name']} ({r['login_id']}) | "
            f"score={r['score']}/{r['points_possible']} | "
            f"attempt={r['attempt']} | "
            f"finished={r['finished_at']}\n"
        )

# 2) Machine-readable JSON
with open("quiz_attempts_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print("✅ Generated:")
print(" - quiz_attempts_summary.txt")
print(" - quiz_attempts_summary.json")
