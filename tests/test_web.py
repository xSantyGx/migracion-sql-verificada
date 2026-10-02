from fastapi.testclient import TestClient
from migrator.web import app

client = TestClient(app)


def test_usable_empty_state_and_health():
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/")
    assert response.status_code == 200
    assert "FactorIT" in response.text
    assert client.get("/static/style.css").status_code == 200


def test_unknown_id_and_invalid_question():
    assert client.get("/procedures/not-found").status_code == 404
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert client.get("/api/runs/..").status_code in [400, 404]


def test_report_text_is_escaped_not_executed(monkeypatch):
    from migrator import web

    run = {
        "id": "xss-check",
        "model": "test",
        "status": "completed",
        "usage_ledger": {"charged_tokens": 0},
        "procedures": [
            {
                "id": "01",
                "name": "<script>alert(1)</script>",
                "description": "test",
                "direct": {"status": "incomplete", "attempts": []},
                "agent": {"status": "incomplete", "attempts": []},
            }
        ],
    }
    monkeypatch.setattr(web, "get_run", lambda run_id=None: run)
    response = client.get("/")
    assert response.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
    assert "<script>alert(1)</script>" not in response.text


def test_ask_evidence_stays_with_run_used_to_generate_answer(tmp_path, monkeypatch):
    from dataclasses import replace
    from migrator import assistant, web
    from migrator.config import Settings
    from migrator.storage import write_json

    settings = replace(Settings(), root=tmp_path)
    old_path = settings.artifacts / "original" / "run.json"
    write_json(old_path, {"id": "original", "procedures": [{"id": "01"}]})
    monkeypatch.setattr(web, "Settings", lambda: settings)

    def answer_while_new_run_finishes(settings, question, run):
        assert run["id"] == "original"
        new_path = settings.artifacts / "newest" / "run.json"
        write_json(new_path, {"id": "newest", "procedures": [{"id": "02"}]})
        # Force ordering regardless of filesystem timestamp resolution.
        import os

        newer = old_path.stat().st_mtime + 10
        os.utime(new_path, (newer, newer))
        return {"answer": "Evidencia original", "procedure_ids": ["01"]}

    monkeypatch.setattr(assistant, "ask", answer_while_new_run_finishes)
    response = client.post("/api/ask", json={"question": "¿Qué quedó equivalente?"})
    assert response.status_code == 200
    assert response.json()["evidence"] == [
        {"id": "01", "url": "/procedures/01?run_id=original"}
    ]
