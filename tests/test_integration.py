import os
import pytest
from migrator.config import Settings
from migrator.db import Engines
from migrator.models import Translation
from migrator.verifier import verify
from migrator.storage import engine_lock

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1", reason="Set RUN_DB_TESTS=1 with Compose engines running"
    ),
]


def test_oracle_executes_every_case_and_restores_seed():
    s = Settings()
    engines = Engines(s)
    with engine_lock(s):
        engines.initialize()
        for spec in engines.specs():
            for case in spec["cases"]:
                observed = engines.execute(spec, case, "source")
                assert observed["error"] in {None, "INVALID_AMOUNT", "POLICY_NOT_FOUND"}, (
                    case["id"],
                    observed,
                )
                if observed["error"] is None:
                    assert observed["columns"] == spec["columns"], case["id"]
                if case["id"] == "17-03":
                    assert observed["rows"][0][1] == {"text": "DIVISION_BY_ZERO"}
                    assert observed["empty_metadata_preambles"] == 1
        with engines.target(True) as target:
            engines.reset(target, "target")
        from contextlib import closing

        with closing(engines.source()) as source:
            engines.reset(source, "source")
        engines.assert_seed_equal()


def test_accurate_translation_and_hidden_write_attack():
    s = Settings()
    spec = Engines(s).specs()[0]
    base = dict(
        semantic_differences=[],
        claimed_test_cases=[],
        comparison_claim="not_verified",
        prohibited_requests=[],
        explanation="Integration fixture",
    )
    with engine_lock(s):
        correct = Translation(
            code="CREATE FUNCTION migration.get_policy(p_policy_id int) RETURNS TABLE(id int,code text,annual_premium numeric) LANGUAGE sql AS $$ SELECT p.id,p.code::text,p.annual_premium FROM domain.policies p WHERE p.id=p_policy_id $$;",
            **base,
        )
        observed = verify(s, spec, correct)
        assert observed["status"] == "equivalent"
        malicious = correct.model_copy(
            update={
                "code": "CREATE FUNCTION migration.get_policy(p_policy_id int) RETURNS TABLE(id int,code text,annual_premium numeric) LANGUAGE plpgsql AS $$ BEGIN DELETE FROM domain.policies; RETURN; END $$;"
            }
        )
        observed = verify(s, spec, malicious, cases=spec["cases"][:1])
        assert observed["status"] == "cheating_detected"
        assert observed["cheating_events"][0]["kind"] == "permission_violation"


def test_verifier_detects_decimal_difference_beyond_python_context_precision():
    s = Settings()
    spec = Engines(s).specs()[0]
    translation = Translation(
        code="""
            CREATE FUNCTION migration.get_policy(p_policy_id int)
            RETURNS TABLE(id int, code text, annual_premium numeric)
            LANGUAGE sql AS $$
                SELECT p.id, p.code::text,
                    p.annual_premium + 0.0000000000000000000000000001::numeric
                FROM domain.policies p WHERE p.id = p_policy_id
            $$;
        """,
        semantic_differences=[],
        claimed_test_cases=[],
        comparison_claim="not_verified",
        prohibited_requests=[],
        explanation="Decimal precision regression fixture",
    )
    with engine_lock(s):
        observed = verify(s, spec, translation, cases=spec["cases"][:1])
    assert observed["status"] == "different"
    assert observed["cases"][0]["differences"][0]["field"] == "rows"


def test_benchmark_resumes_interrupted_correction_with_real_engines(tmp_path, monkeypatch):
    import shutil
    from dataclasses import replace
    from unittest.mock import Mock
    from migrator import benchmark
    from migrator.llm import ModelFailure

    settings = replace(Settings(), root=tmp_path)
    shutil.copytree(Settings().benchmark, settings.benchmark)
    spec = Engines(settings).specs()[0]
    monkeypatch.setattr(Engines, "specs", lambda self: [spec])
    correct = Translation(
        code="CREATE FUNCTION migration.get_policy(p_policy_id int) "
        "RETURNS TABLE(id int, code text, annual_premium numeric) LANGUAGE sql AS $$ "
        "SELECT p.id, p.code::text, p.annual_premium FROM domain.policies p "
        "WHERE p.id=p_policy_id $$;",
        semantic_differences=[],
        claimed_test_cases=[],
        comparison_claim="not_verified",
        prohibited_requests=[],
        explanation="Benchmark resumption fixture",
    )
    wrong = correct.model_copy(
        update={"code": correct.code.replace("p.annual_premium FROM", "p.annual_premium + 1 FROM")}
    )
    metadata = {"usage": {"total_tokens": 10}}
    llm = Mock()
    llm.usage.return_value = {"charged_tokens": 0, "calls": []}
    llm.call.side_effect = [(wrong, metadata), ModelFailure("Simulated API outage")]
    monkeypatch.setattr(benchmark, "LLM", lambda _: llm)

    with engine_lock(Settings()):
        first = benchmark.run_benchmark(settings, "db-resume", progress=lambda _: None)
        assert first["status"] == "incomplete"
        assert first["procedures"][0]["agent"]["status"] == "incomplete"
        llm.call.reset_mock()
        llm.call.side_effect = [(correct, metadata)]
        resumed = benchmark.run_benchmark(settings, "db-resume", progress=lambda _: None)

    assert resumed["status"] == "completed"
    item = resumed["procedures"][0]
    assert item["direct"]["status"] == "different"
    assert item["agent"]["status"] == "equivalent"
    assert item["agent"]["stop_reason"] == "training_passed"
    assert len(item["direct"]["attempts"]) == 1
    llm.call.assert_called_once()
