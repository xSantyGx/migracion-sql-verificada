import copy
import json
import platform
from datetime import datetime, timezone
import importlib.metadata
from .db import Engines, DDL_CONTEXT
from .llm import LLM, prompt, BudgetExceeded, ModelFailure
from .models import Translation
from .verifier import verify, training_feedback, training_passed
from .integrity import check_integrity, trust_fingerprint
from .storage import run_path, write_json, engine_lock
from .reports import export


def translation_input(settings, spec):
    contract = {k: v for k, v in spec.items() if k not in ["cases", "source"]}
    return json.dumps(
        {
            "task": "Traduce preservando semántica; aún no has ejecutado pruebas.",
            "contract": contract,
            "target_schema": DDL_CONTEXT,
            "source_sql": (settings.benchmark / spec["source"]).read_text(),
        },
        ensure_ascii=False,
    )


def run_benchmark(settings, run_id, progress=print):
    path = run_path(settings, run_id)
    with engine_lock(settings):
        fingerprint = check_integrity(settings.benchmark)
        trusted = trust_fingerprint(settings)
        engines = Engines(settings)
        specs = engines.specs()
        llm = LLM(settings)
        if path.exists():
            run = json.loads(path.read_text())
            if (
                run["benchmark_hash"] != fingerprint
                or run["trusted_code_hash"] != trusted
                or run["model"] != settings.model
                or run["max_attempts"] != settings.max_attempts
            ):
                raise RuntimeError(
                    "No se puede reanudar: cambió el benchmark, el código, el modelo o los intentos."
                )
        else:
            run = {
                "id": run_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": settings.model,
                "benchmark_hash": fingerprint,
                "trusted_code_hash": trusted,
                "max_attempts": settings.max_attempts,
                "python": platform.python_version(),
                "packages": {
                    p: importlib.metadata.version(p) for p in ["openai", "pymssql", "psycopg"]
                },
                "status": "running",
                "comparison_contract": "Single tabular relation; same-shape empty TDS metadata preambles are recorded and ignored. Nonempty or differently shaped multiple results are unsupported and abort verification.",
                "procedures": [],
            }
            write_json(path, run)

        def save():
            if trust_fingerprint(settings) != trusted:
                raise RuntimeError("El código o prompt cambió durante la evaluación.")
            run["usage_ledger"] = llm.usage()
            write_json(path, run)

        run["status"] = "running"
        run.pop("finished_at", None)
        save()
        entries = {p["id"]: p for p in run["procedures"]}
        # Allocate a first pass to every procedure before spending on corrections.
        for spec in specs:
            if spec["id"] in entries and entries[spec["id"]]["direct"].get("attempts"):
                continue
            entry = entries.get(spec["id"]) or {
                "id": spec["id"],
                "name": spec["name"],
                "description": spec["description"],
                "direct": {"attempts": []},
                "agent": {"attempts": []},
            }
            if spec["id"] not in entries:
                run["procedures"].append(entry)
                entries[spec["id"]] = entry
            progress("Traducción directa " + spec["id"] + " " + spec["name"])
            try:
                proposal, metadata = llm.call(
                    prompt("migration"),
                    translation_input(settings, spec),
                    Translation,
                    run_id + ":direct:" + spec["id"],
                )
                attempt = {"number": 1, "proposal": proposal.model_dump(), "api": metadata}
                # Checkpoint the API output before any engine action.
                entry["direct"]["attempts"].append(attempt)
                entry["direct"].pop("stop_reason", None)
                entry["agent"].pop("stop_reason", None)
                save()
            except (BudgetExceeded, ModelFailure) as error:
                entry["direct"].setdefault("api_failures", []).append(str(error))
                entry["direct"].update(status="incomplete", stop_reason=str(error))
                entry["agent"].update(status="incomplete", stop_reason=str(error))
                save()
                if isinstance(error, BudgetExceeded):
                    break
        # Resume verification of all saved drafts (even after interruption).
        for spec in specs:
            entry = entries.get(spec["id"])
            if not entry or not entry["direct"]["attempts"]:
                continue
            attempt = entry["direct"]["attempts"][0]
            if "verification" not in attempt:
                progress("Verificación inicial " + spec["id"])
                attempt["verification"] = verify(
                    settings, spec, Translation.model_validate(attempt["proposal"])
                )
                save()
            entry["direct"]["status"] = attempt["verification"]["status"]
            if not entry["agent"]["attempts"]:
                entry["agent"]["attempts"] = [copy.deepcopy(attempt)]
                entry["agent"]["attempts"][0]["shared_initial_call"] = True
                save()
        for spec in specs:
            entry = entries.get(spec["id"])
            if not entry or not entry["agent"]["attempts"]:
                continue
            technique = entry["agent"]
            correction_failed = False
            while len(technique["attempts"]) < settings.max_attempts:
                last = technique["attempts"][-1]
                if "verification" not in last:
                    last["verification"] = verify(
                        settings, spec, Translation.model_validate(last["proposal"])
                    )
                    save()
                if training_passed(last["verification"]) or last["verification"]["cheating_events"]:
                    break
                number = len(technique["attempts"]) + 1
                progress("Corrección " + spec["id"] + " intento " + str(number))
                content = (
                    translation_input(settings, spec)
                    + "\n"
                    + json.dumps(
                        {
                            "task": "Corrige solo la traducción usando evidencia del ejecutor.",
                            "previous_translation": last["proposal"],
                            "verification": training_feedback(last["verification"]),
                        },
                        ensure_ascii=False,
                    )
                )
                try:
                    proposal, metadata = llm.call(
                        prompt("migration"),
                        content,
                        Translation,
                        run_id + ":agent:" + spec["id"] + ":" + str(number),
                    )
                    attempt = {"number": number, "proposal": proposal.model_dump(), "api": metadata}
                    technique["attempts"].append(attempt)
                    technique["status"] = "incomplete"
                    save()
                    attempt["verification"] = verify(settings, spec, proposal)
                    save()
                except (BudgetExceeded, ModelFailure) as error:
                    correction_failed = True
                    technique.setdefault("api_failures", []).append(str(error))
                    technique.update(status="incomplete", stop_reason=str(error))
                    save()
                    break
            last = technique["attempts"][-1]
            if "verification" not in last:
                last["verification"] = verify(
                    settings, spec, Translation.model_validate(last["proposal"])
                )
            technique["status"] = (
                "incomplete" if correction_failed else last["verification"]["status"]
            )
            if not correction_failed:
                technique["stop_reason"] = (
                    "training_passed"
                    if training_passed(last["verification"])
                    else "cheating_detected"
                    if last["verification"]["cheating_events"]
                    else "max_attempts"
                )
            save()
        for spec in specs:
            if spec["id"] not in entries:
                run["procedures"].append(
                    {
                        "id": spec["id"],
                        "name": spec["name"],
                        "description": spec["description"],
                        "direct": {"attempts": [], "status": "incomplete"},
                        "agent": {"attempts": [], "status": "incomplete"},
                    }
                )
        run["status"] = (
            "completed"
            if all(
                p[t].get("status") != "incomplete"
                for p in run["procedures"]
                for t in ["direct", "agent"]
            )
            else "incomplete"
        )
        run["finished_at"] = datetime.now(timezone.utc).isoformat()
        save()
        # Exports also write run.json: keep them inside the checkpoint lock.
        export(run, path.parent)
        return run
