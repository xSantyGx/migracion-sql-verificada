import json
import shutil
from dataclasses import replace
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from migrator import benchmark, cli
from migrator.config import Settings
from migrator.db import Engines
from migrator.llm import BudgetExceeded, ModelFailure
from migrator.models import Translation
from migrator.storage import run_path


@pytest.fixture
def benchmark_environment(tmp_path, monkeypatch):
    settings = replace(Settings(), root=tmp_path, api_key="test-only")
    shutil.copytree(Settings().benchmark, settings.benchmark)
    spec = Engines(settings).specs()[0]
    engines = Mock()
    engines.specs.return_value = [spec]
    monkeypatch.setattr(benchmark, "Engines", lambda _: engines)
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    llm = Mock()
    llm.usage.return_value = {"charged_tokens": 0, "calls": []}
    monkeypatch.setattr(benchmark, "LLM", lambda _: llm)
    proposal = Translation(
        code="CREATE FUNCTION migration.get_policy(p_policy_id int) RETURNS int "
        "LANGUAGE sql AS $$ SELECT p_policy_id $$;",
        semantic_differences=[],
        claimed_test_cases=[],
        comparison_claim="not_verified",
        prohibited_requests=[],
        explanation="Test fixture",
    )
    reply = (proposal, {"usage": {"total_tokens": 10}})
    return settings, llm, reply


def verification(equal=False, reserved_failure=False):
    cases = [
        {
            "id": "01-01",
            "args": [1],
            "reserved": False,
            "equal": equal,
            "differences": [] if equal else [{"field": "rows"}],
            "source": {"raw_error": None},
            "target": {"raw_error": None},
        }
    ]
    if reserved_failure:
        cases.append({**cases[0], "id": "01-07", "reserved": True, "equal": False})
    return {
        "compiled": True,
        "status": "equivalent" if equal and not reserved_failure else "different",
        "cases": cases,
        "cheating_events": [],
        "installation_error": None,
        "semantic_differences": [],
    }


@pytest.mark.parametrize("error_type", [ModelFailure, BudgetExceeded])
def test_failed_correction_is_incomplete_and_resume_keeps_saved_draft(
    benchmark_environment, monkeypatch, error_type
):
    settings, llm, reply = benchmark_environment
    error = error_type("Correction interrupted")
    llm.call.side_effect = [reply, error]
    checker = Mock(side_effect=[verification(), verification(equal=True)])
    monkeypatch.setattr(benchmark, "verify", checker)

    first = benchmark.run_benchmark(settings, "resume", progress=lambda _: None)
    assert first["status"] == "incomplete"
    agent = first["procedures"][0]["agent"]
    assert agent["status"] == "incomplete"
    assert agent["attempts"][-1]["verification"]["status"] == "different"
    assert agent["api_failures"] == [str(error)]
    assert agent["stop_reason"] == str(error)
    assert json.loads(run_path(settings, "resume").read_text()) == first

    llm.call.reset_mock()
    def reply_during_resume(*args, **kwargs):
        checkpoint = json.loads(run_path(settings, "resume").read_text())
        assert checkpoint["status"] == "running"
        assert "finished_at" not in checkpoint
        return reply

    llm.call.side_effect = reply_during_resume
    resumed = benchmark.run_benchmark(settings, "resume", progress=lambda _: None)
    agent = resumed["procedures"][0]["agent"]
    assert resumed["status"] == "completed"
    assert agent["status"] == "equivalent"
    assert agent["stop_reason"] == "training_passed"
    assert agent["api_failures"] == [str(error)]
    assert len(resumed["procedures"][0]["direct"]["attempts"]) == 1
    assert len(agent["attempts"]) == 2
    llm.call.assert_called_once()
    assert llm.call.call_args.args[3] == "resume:agent:01:2"
    assert checker.call_count == 2


def test_cli_benchmark_returns_failure_if_correction_could_not_finish(
    benchmark_environment, monkeypatch
):
    settings, llm, reply = benchmark_environment
    llm.call.side_effect = [reply, ModelFailure("API unavailable")]
    monkeypatch.setattr(benchmark, "verify", Mock(return_value=verification()))
    result = CliRunner().invoke(cli.app, ["benchmark", "--run-id", "interrupted"])
    assert result.exit_code == 1, result.output
    path = run_path(settings, "interrupted")
    assert json.loads(path.read_text())["status"] == "incomplete"
    assert "Incompleto" in (path.parent / "results.md").read_text()


@pytest.mark.parametrize("reserved_failure", [False, True])
def test_training_pass_remains_completed_without_corrections(
    benchmark_environment, monkeypatch, reserved_failure
):
    settings, llm, reply = benchmark_environment
    llm.call.return_value = reply
    monkeypatch.setattr(
        benchmark, "verify", Mock(return_value=verification(True, reserved_failure))
    )
    run = benchmark.run_benchmark(settings, "training-pass", progress=lambda _: None)
    assert run["status"] == "completed"
    assert run["procedures"][0]["agent"]["stop_reason"] == "training_passed"
    llm.call.assert_called_once()


def test_exhausting_attempts_with_differences_is_still_completed(
    benchmark_environment, monkeypatch
):
    settings, llm, reply = benchmark_environment
    llm.call.return_value = reply
    monkeypatch.setattr(benchmark, "verify", Mock(return_value=verification()))
    run = benchmark.run_benchmark(settings, "exhausted", progress=lambda _: None)
    assert run["status"] == "completed"
    agent = run["procedures"][0]["agent"]
    assert agent["status"] == "different"
    assert agent["stop_reason"] == "max_attempts"
    assert len(agent["attempts"]) == settings.max_attempts
