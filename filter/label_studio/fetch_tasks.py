import json
import requests
# from config import LABEL_STUDIO_BASE_URL, LABEL_STUDIO_API_KEY   
from config import PROJECT_IDS as project_id
from config import LABEL_STUDIO_BASE_URL
from config import LABEL_STUDIO_API_KEY

PAGE_SIZE = 50

def _get_tasks_from_label_studio(project_id):
    all_tasks = []
    page = 1
    tasks_url = f"{LABEL_STUDIO_BASE_URL}/api/tasks/"
    headers = {
        "Authorization": f"Token {LABEL_STUDIO_API_KEY}",
        "Content-Type": "application/json"
    }

    while True:
        # Paginated request
        request_url = (
            f"{tasks_url}?page={page}"
            f"&project={project_id}"
            f"&page_size={PAGE_SIZE}"
            "&fields=all"
        )
        
        response = requests.get(request_url, headers=headers, verify=False)
        if response.status_code != 200:
            break

        response_data = response.json()
        tasks = response_data.get("tasks", [])
        if not tasks:
            break

        all_tasks.extend(tasks)
        page += 1

    with open(f"filter/label_studio/data/tasks_projectId_{project_id}.json", "w") as f:
        json.dump(all_tasks, f)

    return all_tasks

if __name__ == "__main__":
    tasks = _get_tasks_from_label_studio(project_id)
    print(f"Fetched {len(tasks)} tasks from Label Studio for project ID {project_id}.")