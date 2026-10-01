from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock
import json
import pytest
from openai import APIConnectionError
import httpx
from migrator.config import Settings
from migrator.llm import LLM, BudgetExceeded, ModelFailure
from migrator.models import DomainDecision


def fake_llm(tmp_path, budget=1000):
    settings = replace(Settings(), root=tmp_path, api_key="test-only", budget=budget)
    llm = LLM(settings)
    llm.client = Mock()
    llm.client.responses.input_tokens.count.return_value = SimpleNamespace(input_tokens=10)
    return llm


def test_call_is_not_sent_when_worst_case_exceeds_budget(tmp_path):
    llm = fake_llm(tmp_path, budget=100)
    with pytest.raises(BudgetExceeded):
        llm.call("system", "input", DomainDecision, "test", max_output=100)
    llm.client.responses.create.assert_not_called()


def test_transport_failure_keeps_reservation_across_restart(tmp_path):
    llm = fake_llm(tmp_path, budget=150)
    llm.client.responses.create.side_effect = APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com")
    )
    with pytest.raises(ModelFailure):
        llm.call("system", "input", DomainDecision, "test", max_output=100)
    assert json.loads(llm.path.read_text())["charged_tokens"] == 110
    restarted = fake_llm(tmp_path, budget=150)
    with pytest.raises(BudgetExceeded):
        restarted.call("system", "input", DomainDecision, "test", max_output=100)


def test_known_usage_releases_only_unused_reservation(tmp_path):
    llm = fake_llm(tmp_path)
    usage = Mock()
    usage.model_dump.return_value = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    llm.client.responses.create.return_value = SimpleNamespace(
        status="completed",
        usage=usage,
        id="response-test",
        model="gpt-5-mini",
        output_text='{"in_domain":true}',
    )
    result, metadata = llm.call("system", "input", DomainDecision, "test", max_output=100)
    assert result.in_domain
    assert llm.usage()["charged_tokens"] == 15


def test_read_only_count_retry_does_not_duplicate_generation(tmp_path, monkeypatch):
    llm = fake_llm(tmp_path)
    monkeypatch.setattr("migrator.llm.time.sleep", lambda _: None)
    llm.client.responses.input_tokens.count.side_effect = [
        APIConnectionError(request=httpx.Request("POST", "https://api.openai.com")),
        SimpleNamespace(input_tokens=10),
    ]
    usage = Mock()
    usage.model_dump.return_value = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    llm.client.responses.create.return_value = SimpleNamespace(
        status="completed",
        usage=usage,
        id="response-test",
        model="gpt-5-mini",
        output_text='{"in_domain":true}',
    )
    output, _ = llm.call("system", "input", DomainDecision, "test", max_output=100)
    assert output.in_domain
    assert llm.client.responses.input_tokens.count.call_count == 2
    llm.client.responses.create.assert_called_once()
