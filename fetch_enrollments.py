import requests

def fetch_all_enrollments(base_url, token, course_id):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = f"{base_url}/courses/{course_id}/enrollments"
    params = {
        "type[]": "StudentEnrollment",
        "per_page": 100
    }

    all_enrollments = []

    while url:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()
        all_enrollments.extend(data)

        # pagination
        url = None
        link = r.headers.get("Link")
        if link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part[part.find("<") + 1 : part.find(">")]

        params = None

    return all_enrollments
