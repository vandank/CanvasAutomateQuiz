from canvas_paginated_fetch import fetch_all_pages

BASE_URL = "https://canvas.asu.edu/api/v1"
TOKEN = "<YOUR TOKEN HERE>"
COURSE_ID = "249800"
QUIZ_ID = "1941218" #1938135 for ER diagram and 1938812 for ER diagram (2)

url = f"{BASE_URL}/courses/{COURSE_ID}/quizzes/{QUIZ_ID}/submissions"

subs, users = fetch_all_pages(
    url,
    TOKEN,
    params={"include[]": "user", "per_page": 100}
)

print(f"Total quiz submissions fetched: {len(subs)}")