from src.client import get_json
from src.config import BASE_TEST_URL, AZDO_API_VERSION

def list_results(run_id: int, top: int = 100):
    url = f"{BASE_TEST_URL}/Runs/{run_id}/results"
    data = get_json(url, params={
        "api-version": AZDO_API_VERSION,
        "$top": top
    })
    return data.get("value", [])

if __name__ == "__main__":
    run_id = int(input("Digite o run_id: "))
    results = list_results(run_id)
    print(f"\nResultados encontrados: {len(results)}\n")

    for result in results[:10]:
        print({
            "id": result.get("id"),
            "testCaseTitle": result.get("testCaseTitle"),
            "state": result.get("state"),
            "outcome": result.get("outcome"),
            "completedDate": result.get("completedDate"),
            "runBy": (result.get("runBy") or {}).get("displayName"),
            "lastUpdatedBy": (result.get("lastUpdatedBy") or {}).get("displayName"),
        })