from dataclasses import replace
from migrator.config import Settings
from migrator.storage import load_run, write_json
import pytest


def test_shipped_evidence_can_be_opened_by_id_without_local_artifacts(tmp_path):
    settings = replace(Settings(), root=tmp_path)
    write_json(tmp_path / "reports" / "saved" / "run.json", {"id": "saved"})
    assert load_run(settings)["id"] == "saved"
    assert load_run(settings, "saved")["id"] == "saved"
    with pytest.raises(ValueError):
        load_run(settings, "../secret")
