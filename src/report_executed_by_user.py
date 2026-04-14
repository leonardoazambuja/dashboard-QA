from collections import defaultdict
from datetime import datetime, timedelta, timezone
import sys
import csv
import json
from pathlib import Path

from src.config import BASE_TEST_URL, AZDO_API_VERSION, DEFAULT_DAYS_BACK
from src.client import get_json, get_json_with_headers

def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def format_azdo_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def list_runs_in_window(start_dt: datetime, end_dt: datetime, page_size: int = 100):
    url = f"{BASE_TEST_URL}/runs"
    all_runs = []
    continuation_token = None

    while True:
        params = {
            "api-version": AZDO_API_VERSION,
            "minLastUpdatedDate": format_azdo_dt(start_dt),
            "maxLastUpdatedDate": format_azdo_dt(end_dt),
            "$top": page_size,
        }

        if continuation_token:
            params["continuationToken"] = continuation_token

        data, headers = get_json_with_headers(url, params=params)
        runs = data if isinstance(data, list) else data.get("value", [])
        all_runs.extend(runs)

        continuation_token = headers.get("x-ms-continuationtoken")
        if not continuation_token:
            break

    return all_runs

def list_all_runs_for_period(days_back: int):
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days_back)

    all_runs = []
    cursor = start_dt

    while cursor < end_dt:
        window_end = min(cursor + timedelta(days=7), end_dt)
        runs = list_runs_in_window(cursor, window_end)
        all_runs.extend(runs)
        cursor = window_end

    dedup = {}
    for run in all_runs:
        dedup[run["id"]] = run

    return list(dedup.values())

def list_results(run_id: int, top: int = 1000):
    url = f"{BASE_TEST_URL}/Runs/{run_id}/results"
    data = get_json(url, params={
        "api-version": AZDO_API_VERSION,
        "$top": top
    })
    return data.get("value", [])

def generate_html_report(days_back: int, rows: list[dict], output_html_path: Path):
    template_path = Path("templates/report_template.html")
    template = template_path.read_text(encoding="utf-8")

    total_executed = sum(r["executados"] for r in rows)
    total_passed = sum(r["passed"] for r in rows)
    avg_pass_rate = round((total_passed / total_executed * 100), 1) if total_executed else 0

    labels = [r["colaborador"] for r in rows]
    executed = [r["executados"] for r in rows]
    passed = [r["passed"] for r in rows]
    failed = [r["failed"] for r in rows]
    pass_rate = [r["pass_rate"] for r in rows]

    table_rows = "\n".join(
        f"""
        <tr>
          <td>{r['colaborador']}</td>
          <td>{r['executados']}</td>
          <td>{r['passed']}</td>
          <td>{r['failed']}</td>
          <td>{r['blocked']}</td>
          <td>{r['pass_rate']}%</td>
        </tr>
        """
        for r in rows
    )

    html = (
        template
        .replace("{{DAYS_BACK}}", str(days_back))
        .replace("{{COLLABORATORS}}", str(len(rows)))
        .replace("{{TOTAL_EXECUTED}}", str(total_executed))
        .replace("{{TOTAL_PASSED}}", str(total_passed))
        .replace("{{AVG_PASS_RATE}}", str(avg_pass_rate))
        .replace("{{TABLE_ROWS}}", table_rows)
        .replace("{{LABELS}}", json.dumps(labels, ensure_ascii=False))
        .replace("{{EXECUTED}}", json.dumps(executed))
        .replace("{{PASSED}}", json.dumps(passed))
        .replace("{{FAILED}}", json.dumps(failed))
        .replace("{{PASS_RATE}}", json.dumps(pass_rate))
    )

    output_html_path.write_text(html, encoding="utf-8")

def main(days_back: int = DEFAULT_DAYS_BACK):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    runs = list_all_runs_for_period(days_back)

    executed_by = defaultdict(int)
    passed_by = defaultdict(int)
    failed_by = defaultdict(int)
    blocked_by = defaultdict(int)
    total_results = 0

    for run in runs:
        run_id = run["id"]
        results = list_results(run_id)

        for result in results:
            completed_dt = parse_dt(result.get("completedDate"))
            if not completed_dt or completed_dt < cutoff:
                continue

            state = result.get("state")
            outcome = result.get("outcome")

            runner = (
                (result.get("runBy") or {}).get("displayName")
                or (result.get("lastUpdatedBy") or {}).get("displayName")
                or "Sem executor"
            )

            if state == "Completed" and outcome != "NotExecuted":
                total_results += 1
                executed_by[runner] += 1

                if outcome == "Passed":
                    passed_by[runner] += 1
                elif outcome == "Failed":
                    failed_by[runner] += 1
                elif outcome == "Blocked":
                    blocked_by[runner] += 1

    print(f"\nCenários executados por colaborador - últimos {days_back} dias\n")
    print(f"Runs analisados: {len(runs)}")
    print(f"Total de cenários executados no período: {total_results}\n")

    rows = []
    for person, total in sorted(executed_by.items(), key=lambda x: x[1], reverse=True):
        passed = passed_by.get(person, 0)
        failed = failed_by.get(person, 0)
        blocked = blocked_by.get(person, 0)
        pass_rate = round((passed / total * 100), 1) if total else 0

        print(
            f"{person}: "
            f"executados={total}, "
            f"passed={passed}, "
            f"failed={failed}, "
            f"blocked={blocked}, "
            f"pass_rate={pass_rate:.1f}%"
        )

        rows.append({
            "colaborador": person,
            "executados": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "pass_rate": pass_rate,
        })

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / f"executados_por_colaborador_{days_back}d.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["colaborador", "executados", "passed", "failed", "blocked", "pass_rate"]
        )
        writer.writeheader()
        writer.writerows(rows)

    html_path = output_dir / f"executados_por_colaborador_{days_back}d.html"
    generate_html_report(days_back, rows, html_path)

    print(f"\nCSV gerado em: {csv_path.resolve()}")
    print(f"HTML gerado em: {html_path.resolve()}")

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DAYS_BACK
    main(days)