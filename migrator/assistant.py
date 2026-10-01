import json
from .llm import LLM, prompt
from .models import DomainDecision, Explanation, REFUSAL
from .reports import rows


def ask(settings, question, run):
    llm = LLM(settings)
    decision, _ = llm.call(
        prompt("domain"), question, DomainDecision, "domain-classification", max_output=256
    )
    if not decision.in_domain:
        return {"answer": REFUSAL, "procedure_ids": []}
    evidence = rows(run)
    response, _ = llm.call(
        prompt("explain"),
        json.dumps({"question": question, "results": evidence}, ensure_ascii=False),
        Explanation,
        "explain-results",
        max_output=2048,
    )
    valid = {p["id"] for p in run["procedures"]}
    if not set(response.procedure_ids) <= valid:
        raise ValueError("La respuesta citó procedimientos que no existen en la evidencia.")
    return response.model_dump()
