from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from .config import Settings, redact
from .storage import load_run
from .reports import rows, summary, LABELS
from .db import Engines

HERE = Path(__file__).parent
app = FastAPI(title="FactorIT · Migraciones verificadas", version="1.0.0")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
templates.env.globals["labels"] = LABELS


def get_run(run_id=None):
    try:
        return load_run(Settings(), run_id)
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, run_id: str | None = None, status: str | None = None):
    try:
        run = get_run(run_id)
        records = rows(run)
        if status:
            records = [r for r in records if r["status"] == status]
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"run": run, "records": records, "summary": summary(run), "status": status},
        )
    except HTTPException as error:
        if error.status_code != 404:
            raise
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"run": None, "records": [], "summary": {}, "status": None},
        )


@app.get("/procedures/{procedure_id}", response_class=HTMLResponse)
def detail(request: Request, procedure_id: str, run_id: str | None = None):
    run = get_run(run_id)
    procedure = next((p for p in run["procedures"] if p["id"] == procedure_id), None)
    if not procedure:
        raise HTTPException(404, "Procedimiento no encontrado.")
    spec = next(p for p in Engines(Settings()).specs() if p["id"] == procedure_id)
    source = (Settings().benchmark / spec["source"]).read_text()
    return templates.TemplateResponse(
        request=request,
        name="detail.html",
        context={"run": run, "procedure": procedure, "source": source},
    )


@app.get("/api/runs/latest")
def latest():
    run = get_run()
    return {"id": run["id"], "summary": summary(run), "results": rows(run)}


@app.get("/api/runs/{run_id}")
def api_run(run_id: str):
    return get_run(run_id)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    run_id: str | None = None


@app.post("/api/ask")
def api_ask(body: Question):
    from .assistant import ask
    from .llm import BudgetExceeded, ModelFailure

    try:
        result = ask(Settings(), body.question, get_run(body.run_id))
        run = get_run(body.run_id)
        result["evidence"] = [
            {"id": pid, "url": f"/procedures/{pid}?run_id={run['id']}"}
            for pid in result["procedure_ids"]
        ]
        return result
    except BudgetExceeded as error:
        raise HTTPException(429, str(error)) from error
    except ModelFailure as error:
        raise HTTPException(503, redact(str(error), Settings())) from error
    except ValueError as error:
        raise HTTPException(502, str(error)) from error
