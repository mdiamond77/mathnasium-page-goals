import json
import os
from datetime import datetime, timezone

RUN_LOG_PATH = "run_log.json"


def read_log() -> list[dict]:
    if not os.path.exists(RUN_LOG_PATH):
        return []
    with open(RUN_LOG_PATH) as f:
        return json.load(f)


def append_run(
    trigger: str,
    month: str,
    status: str,
    output_file: str = None,
    drive_link: str = None,
    error: str = None,
) -> None:
    log = read_log()
    log.append({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trigger": trigger,
        "month": month,
        "status": status,
        "output_file": output_file,
        "drive_link": drive_link,
        "error": error,
    })
    with open(RUN_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def get_last_run(trigger: str = None) -> dict | None:
    log = read_log()
    if trigger:
        log = [r for r in log if r.get("trigger") == trigger]
    return log[-1] if log else None
