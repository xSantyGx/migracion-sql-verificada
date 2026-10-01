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
