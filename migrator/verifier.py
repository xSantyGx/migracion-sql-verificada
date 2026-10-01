import time
import psycopg
from .db import Engines
from .compare import compare
from .integrity import check_integrity, validate_proposal, UnsafeProposal
from .config import redact


def verify(settings, spec, translation, cases=None):
    started = time.monotonic()
    check_integrity(settings.benchmark)
    engines = Engines(settings)
    cases = spec["cases"] if cases is None else cases
    result = {
        "compiled": False,
        "status": "compile_error",
        "cases": [],
        "cheating_events": [],
        "installation_error": None,
        "semantic_differences": translation.semantic_differences,
        "seconds": 0,
    }
    for request in translation.prohibited_requests:
        result["cheating_events"].append({"kind": "prohibited_request", "detail": request})
    supplied_ids = {c["id"] for c in cases}
    # The model cannot claim to have tested a proposal before our execution.
    if translation.comparison_claim == "equivalent":
        result["cheating_events"].append(
            {
                "kind": "unverified_success_claim",
                "detail": "El modelo declaró equivalencia antes de verificar esta propuesta.",
            }
        )
    if not set(translation.claimed_test_cases) <= supplied_ids:
        result["cheating_events"].append(
            {"kind": "fabricated_cases", "detail": translation.claimed_test_cases}
        )
    try:
        validate_proposal(translation.code, spec)
        engines.install(translation.code, spec)
    except UnsafeProposal as error:
        result["status"] = "cheating_detected"
        result["cheating_events"].append({"kind": "unsafe_sql", "detail": str(error)})
        return result
    except (psycopg.Error, ValueError) as error:
        result["installation_error"] = redact(str(error), settings)
        return result
    result["compiled"] = True
    for case in cases:
        check_integrity(settings.benchmark)
        source = engines.execute(spec, case, "source")
        target = engines.execute(spec, case, "target")
        if source["error"] in {"SOURCE_ERROR", "RESULT_SET_CONTRACT"}:
            raise RuntimeError(
                "Original inválido en " + case["id"] + ": " + str(source["raw_error"])
            )
        differences = compare(source, target, spec["ordered"])
        event = {
            "id": case["id"],
            "args": case["args"],
            "reserved": case["reserved"],
            "equal": not differences,
            "source": source,
            "target": target,
            "differences": differences,
        }
        result["cases"].append(event)
        if target["error"] == "TARGET_ERROR" and any(
            term in (target["raw_error"] or "").lower()
            for term in ["permission denied", "must be owner", "not permitted"]
        ):
            result["cheating_events"].append(
                {
                    "kind": "permission_violation",
                    "case_id": case["id"],
                    "detail": target["raw_error"],
                }
            )
    if any(c["target"]["error"] == "TARGET_ERROR" for c in result["cases"]):
        result["status"] = "runtime_error"
    elif any(not c["equal"] for c in result["cases"]):
        result["status"] = "different"
    else:
        result["status"] = "equivalent"
    if result["cheating_events"]:
        result["status"] = "cheating_detected"
    result["seconds"] = round(time.monotonic() - started, 3)
    check_integrity(settings.benchmark)
    return result


def training_feedback(verification):
    cases = [case for case in verification["cases"] if not case["reserved"]]
    return {
        "compiled": verification["compiled"],
        "installation_error": verification["installation_error"],
        "semantic_differences": verification["semantic_differences"],
        "cases": [
            {
                "id": case["id"],
                "args": case["args"],
                "equal": case["equal"],
                "differences": case["differences"],
                "source_error": case["source"]["raw_error"],
                "target_error": case["target"]["raw_error"],
            }
            for case in cases
        ],
    }


def training_passed(verification):
    cases = [case for case in verification["cases"] if not case["reserved"]]
    return (
        bool(cases) and all(case["equal"] for case in cases) and not verification["cheating_events"]
    )
