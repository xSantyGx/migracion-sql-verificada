import json
from dataclasses import replace
from unittest.mock import Mock

from typer.testing import CliRunner

from migrator import cli
from migrator.config import Settings
from migrator.storage import engine_lock, load_run, run_path, write_json


def test_report_cannot_overwrite_checkpoint_during_active_benchmark(tmp_path, monkeypatch):
    settings = replace(Settings(), root=tmp_path)
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    latest = {"id": "active", "model": "test", "procedures": [], "checkpoint": 1}
    path = run_path(settings, "active")
    write_json(path, latest)

    def load_then_benchmark_advances(settings, run_id):
        nonlocal latest
        snapshot = load_run(settings, run_id)
        # Simulate a new checkpoint being saved after the report's read.
        latest = {**snapshot, "checkpoint": 2, "saved_api_response": "new-response"}
        write_json(path, latest)
        return snapshot

    reader = Mock(side_effect=load_then_benchmark_advances)
    monkeypatch.setattr(cli, "load_run", reader)
    with engine_lock(settings):
        result = CliRunner().invoke(cli.app, ["report", "--run-id", "active"])

    assert json.loads(path.read_text()) == latest
    assert result.exit_code == 2
    reader.assert_not_called()


def test_report_exports_normally_after_benchmark_releases_lock(tmp_path, monkeypatch):
    settings = replace(Settings(), root=tmp_path)
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    run = {"id": "saved", "model": "test", "procedures": []}
    path = run_path(settings, "saved")
    with engine_lock(settings):
        write_json(path, run)

    result = CliRunner().invoke(cli.app, ["report", "--run-id", "saved"])
    assert result.exit_code == 0, result.output
    assert json.loads(path.read_text()) == run
    assert (path.parent / "results.csv").is_file()
    assert (path.parent / "results.md").is_file()
