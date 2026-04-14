from src.client import get_json_with_headers
from src.config import BASE_TEST_URL, AZDO_API_VERSION

def list_all_runs(page_size: int = 200):
    url = f"{BASE_TEST_URL}/runs"
    all_runs = []
    continuation_token = None

    while True:
        params = {
            "api-version": AZDO_API_VERSION,
            "$top": page_size
        }

        if continuation_token:
            params["continuationToken"] = continuation_token

        data, headers = get_json_with_headers(url, params=params)
        runs = data.get("value", [])
        all_runs.extend(runs)

        continuation_token = headers.get("x-ms-continuationtoken")
        if not continuation_token:
            break

    return all_runs

if __name__ == "__main__":
    runs = list_all_runs()
    print(f"Runs encontrados: {len(runs)}\n")

    # Ordena pelos maiores IDs primeiro, só para facilitar inspeção
    runs = sorted(runs, key=lambda x: x.get("id", 0), reverse=True)

    for run in runs[:20]:
        print({
            "id": run.get("id"),
            "name": run.get("name"),
            "completedDate": run.get("completedDate"),
            "state": run.get("state"),
            "totalTests": run.get("totalTests"),
            "passedTests": run.get("passedTests"),
            "plan": (run.get("plan") or {}).get("name"),
            "owner": (run.get("owner") or {}).get("displayName"),
        })