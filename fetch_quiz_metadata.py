import requests
from typing import Optional

def fetch_quiz_due_at(base_url, token, course_id, quiz_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{base_url}/courses/{course_id}/quizzes/{quiz_id}"

    r = requests.get(url, headers=headers)
    r.raise_for_status()

    quiz = r.json()
    return quiz.get("due_at")


def fetch_course_quiz_assignments(base_url: str, token: str, course_id: str) -> dict:
    """
    List all assignments for the course and return a mapping of quiz_id -> assignment info
    for assignments that are quizzes (submission_types includes 'online_quiz').
    Canvas includes quiz_id on such assignments.
    Returns: { quiz_id: {"assignment_id": int, "assignment_name": str, "gradebook_column": str}, ... }
    """
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{base_url}/courses/{course_id}/assignments"
    params = {"per_page": 100}
    result = {}

    while url:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        for a in data:
            if "online_quiz" not in (a.get("submission_types") or []):
                continue
            qid = a.get("quiz_id")
            if qid is None:
                continue
            aid = a.get("id")
            name = (a.get("name") or "").strip()
            result[qid] = {
                "assignment_id": aid,
                "assignment_name": name,
                "gradebook_column": f"{name} ({aid})",
            }
        url = None
        link = r.headers.get("Link")
        if link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part[part.find("<") + 1 : part.find(">")]
        params = None

    return result


def fetch_quiz_assignment_info(
    base_url: str, token: str, course_id: str, quiz_id: str
) -> Optional[dict]:
    """
    Return assignment info for a single quiz: assignment_id, assignment_name, gradebook_column.
    Returns None if this quiz has no associated assignment (e.g. not linked to gradebook).
    """
    mapping = fetch_course_quiz_assignments(base_url, token, course_id)
    return mapping.get(quiz_id)
