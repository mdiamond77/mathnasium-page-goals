import json
import os
import pytest
import tempfile
import run_log


@pytest.fixture(autouse=True)
def tmp_log(monkeypatch, tmp_path):
    log_path = str(tmp_path / "run_log.json")
    monkeypatch.setattr(run_log, "RUN_LOG_PATH", log_path)
    return log_path


def test_append_creates_file(tmp_log):
    run_log.append_run("manual", "2026-04", "success", "April Page Goals.xlsx", "https://drive.google.com/x", None)
    assert os.path.exists(tmp_log)


def test_append_stores_fields(tmp_log):
    run_log.append_run("auto", "2026-04", "success", "April Page Goals.xlsx", "https://drive.google.com/x", None)
    with open(tmp_log) as f:
        log = json.load(f)
    assert len(log) == 1
    entry = log[0]
    assert entry["trigger"] == "auto"
    assert entry["month"] == "2026-04"
    assert entry["status"] == "success"
    assert entry["output_file"] == "April Page Goals.xlsx"
    assert entry["drive_link"] == "https://drive.google.com/x"
    assert entry["error"] is None
    assert "timestamp" in entry


def test_append_multiple_runs(tmp_log):
    run_log.append_run("auto", "2026-03", "success", "March Page Goals.xlsx", None, None)
    run_log.append_run("manual", "2026-04", "error", None, None, "Download failed")
    with open(tmp_log) as f:
        log = json.load(f)
    assert len(log) == 2
    assert log[1]["status"] == "error"
    assert log[1]["error"] == "Download failed"


def test_read_log_empty_when_no_file(tmp_log):
    result = run_log.read_log()
    assert result == []


def test_get_last_run_by_trigger(tmp_log):
    run_log.append_run("auto", "2026-03", "success", "March Page Goals.xlsx", None, None)
    run_log.append_run("manual", "2026-04", "success", "April Page Goals.xlsx", None, None)
    last_auto = run_log.get_last_run("auto")
    assert last_auto["month"] == "2026-03"
    last_manual = run_log.get_last_run("manual")
    assert last_manual["month"] == "2026-04"


def test_get_last_run_returns_none_when_empty(tmp_log):
    assert run_log.get_last_run("auto") is None
