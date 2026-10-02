import json
from datetime import datetime, timezone
from pathlib import Path
import typer
from filelock import Timeout
from .config import Settings, redact
from .db import Engines
from .integrity import check_integrity
from .storage import load_run, run_path, write_json, engine_lock
from .reports import export, summary

app = typer.Typer(help="Migración SQL verificable · FactorIT", no_args_is_help=True)


def safe(action):
    try:
        return action()
    except (Exception,) as error:
        if isinstance(error, typer.Exit):
            raise
        typer.echo("Error: " + redact(str(error), Settings()), err=True)
        raise typer.Exit(2) from error


@app.command()
def doctor():
    """Comprobar configuración, integridad y conexiones sin consumir tokens."""
    s = Settings()
    status = {"openai_key_configured": bool(s.api_key), "model": s.model, "token_budget": s.budget}
    try:
        status["benchmark_integrity"] = check_integrity(s.benchmark)
    except Exception as error:
        status["benchmark_integrity"] = "ERROR: " + str(error)
    engines = Engines(s)
    for name, connect in [
        ("sqlserver", lambda: engines.source("master")),
        ("postgres", lambda: engines.target(True, "postgres")),
    ]:
        try:
            conn = connect()
            conn.close()
            status[name] = "available"
        except Exception as error:
            status[name] = "unavailable: " + redact(str(error), s)
    typer.echo(json.dumps(status, ensure_ascii=False, indent=2))
    if any("unavailable" in str(v) or "ERROR:" in str(v) for v in status.values()):
        raise typer.Exit(2)


@app.command("init")
def initialize():
    """Inicializar motores y datos; no modifica archivos de referencia."""

    def action():
        s = Settings()
        with engine_lock(s):
            Engines(s).initialize()
        typer.echo("Motores inicializados; datos idénticos en ambos motores.")

    safe(action)


@app.command()
def benchmark(run_id: str = typer.Option(None, help="Reutiliza el ID para reanudar.")):
    """Generar y verificar ambas técnicas, respetando el presupuesto."""

    def action():
        from .benchmark import run_benchmark

        s = Settings()
        name = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run = run_benchmark(s, name, typer.echo)
        typer.echo(json.dumps(summary(run), ensure_ascii=False, indent=2))
        typer.echo("Evidencia: " + str(run_path(s, name).parent))
        if run["status"] != "completed":
            raise typer.Exit(1)

    safe(action)


@app.command()
def verify(
    run_id: str = typer.Option(None), technique: str = "agent", procedure: str = typer.Option(None)
):
    """Reejecutar código guardado SIN OpenAI; fallo no equivalente => exit 1."""

    def action():
        from .models import Translation
        from .verifier import verify as verify_proposal

        s = Settings()
        if technique not in ["direct", "agent"]:
            raise ValueError("Técnica: direct o agent.")
        run = load_run(s, run_id)
        if run["benchmark_hash"] != check_integrity(s.benchmark):
            raise ValueError("El conjunto de referencia cambió.")
        specs = {p["id"]: p for p in Engines(s).specs()}
        selected = [
            p
            for p in run["procedures"]
            if procedure is None or p["id"] == procedure or p["name"] == procedure
        ]
        if not selected:
            raise ValueError("No se encontraron procedimientos.")
        results = []
        with engine_lock(s):
            for item in selected:
                attempts = item[technique].get("attempts", [])
                result = (
                    verify_proposal(
                        s, specs[item["id"]], Translation.model_validate(attempts[-1]["proposal"])
                    )
                    if attempts
                    else {"status": "incomplete"}
                )
                results.append({"id": item["id"], **result})
                typer.echo(item["id"] + " " + result["status"])
        write_json(s.artifacts / ("verification-" + run["id"] + "-" + technique + ".json"), results)
        if any(r["status"] != "equivalent" for r in results):
            raise typer.Exit(1)

    safe(action)


@app.command()
def report(run_id: str = typer.Option(None), output: Path = typer.Option(None)):
    """Exportar tabla CSV, JSON completo y resumen Markdown."""

    def action():
        s = Settings()
        try:
            with engine_lock(s):
                run = load_run(s, run_id)
                destination = output or run_path(s, run["id"]).parent
                export(run, destination)
        except Timeout as error:
            raise RuntimeError(
                "Hay una evaluación en curso. Espera a que termine para exportar el informe."
            ) from error
        typer.echo(json.dumps(summary(run), ensure_ascii=False, indent=2))
        typer.echo(str(destination))

    safe(action)


@app.command("eval-prompts")
def eval_prompts(detection_only: bool = False):
    """Evaluar prompts con OpenAI y trampas controladas contra el verificador."""

    def action():
        from .evals import evaluate_prompts, evaluate_detection

        s = Settings()
        detection = evaluate_detection(s)
        typer.echo("Detección: " + str(detection["detected"]) + "/" + str(detection["total"]))
        if not detection_only:
            result = evaluate_prompts(s, typer.echo)
            typer.echo("Prompt: " + str(result["passed"]) + "/" + str(result["total"]))
            if not result["complete"] or result["passed"] != result["total"]:
                raise typer.Exit(1)
        if detection["detected"] != detection["total"]:
            raise typer.Exit(1)

    safe(action)


@app.command()
def ask(question: str, run_id: str = typer.Option(None)):
    """Preguntar por resultados con referencias a procedimientos."""

    def action():
        from .assistant import ask as ask_report

        s = Settings()
        run = load_run(s, run_id)
        result = ask_report(s, question, run)
        typer.echo(result["answer"])
        for pid in result["procedure_ids"]:
            typer.echo(f"Evidencia: http://localhost:8000/procedures/{pid}?run_id={run['id']}")

    safe(action)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    """Abrir interfaz local y API de informes."""
    import uvicorn

    uvicorn.run("migrator.web:app", host=host, port=port)
