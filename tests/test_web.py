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
