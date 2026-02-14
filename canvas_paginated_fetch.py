import requests
import json

def fetch_all_pages(url, token, params=None):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    all_data = []
    all_users = {}

    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()

        data = resp.json()

        # Handle quiz submissions shape
        if isinstance(data, dict) and "quiz_submissions" in data:
            all_data.extend(data["quiz_submissions"])
            for u in data.get("users", []):
                all_users[u["id"]] = u
        # Handle plain list shape
        elif isinstance(data, list):
            all_data.extend(data)
        else:
            raise ValueError("Unexpected response shape")

        # Find next page
        url = None
        link_header = resp.headers.get("Link")
        if link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url = part[part.find("<") + 1 : part.find(">")]

        params = None  # params only on first request

    return all_data, list(all_users.values())
