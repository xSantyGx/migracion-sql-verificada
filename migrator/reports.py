import csv
import json
from collections import Counter
from .storage import write_json

LABELS = {
    "equivalent": "Equivalente",
    "different": "Compila pero difiere",
    "compile_error": "No compila",
    "runtime_error": "Falla al ejecutar",
    "cheating_detected": "Trampa detectada",
    "incomplete": "Incompleto",
}


def rows(run):
    result = []
    for procedure in sorted(run["procedures"], key=lambda p: p["id"]):
        for technique in ["direct", "agent"]:
            data = procedure[technique]
            attempts = data.get("attempts", [])
            last = attempts[-1] if attempts else {}
            verification = last.get("verification", {})
            cases = verification.get("cases", [])
            result.append(
                {
                    "id": procedure["id"],
                    "procedure": procedure["name"],
                    "technique": technique,
                    "status": data.get("status", "incomplete"),
                    "compiled": verification.get("compiled", False),
                    "passed_cases": sum(c["equal"] for c in cases),
                    "total_cases": len(cases),
                    "attempts": len(attempts),
                    "tokens": sum(
                        a.get("api", {}).get("usage", {}).get("total_tokens", 0) for a in attempts
                    ),
                    "declared_differences": last.get("proposal", {}).get(
                        "semantic_differences", []
                    ),
                    "cheating_events": verification.get("cheating_events", []),
                }
            )
    return result


def summary(run):
    result = {}
    for technique in ["direct", "agent"]:
        selected = [r for r in rows(run) if r["technique"] == technique]
        counts = dict(Counter(r["status"] for r in selected))
        result[technique] = {
            "counts": counts,
            "equivalent": counts.get("equivalent", 0),
            "total": len(selected),
            "equivalence_rate": counts.get("equivalent", 0) / len(selected) if selected else 0,
            "tokens": sum(r["tokens"] for r in selected),
            "compiled_but_not_equivalent": sum(
                r["compiled"] and r["status"] != "equivalent" for r in selected
            ),
        }
    return result


def export(run, destination):
    destination.mkdir(parents=True, exist_ok=True)
    write_json(destination / "run.json", run)
    records = rows(run)
    with (destination / "results.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]) if records else [])
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
                    for k, v in row.items()
                }
            )
    lines = [
        "# Resultados de la migración",
        "",
        f"Ejecución: `{run['id']}` · Modelo: `{run['model']}`",
        "",
        "Equivalencia sobre casos ejecutados. Diferencias declaradas se muestran por separado.",
        "",
        "| ID | Procedimiento | Técnica | Estado | Casos | Intentos | Tokens | Diferencias declaradas |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in records:
        differences = "; ".join(row["declared_differences"]).replace("|", "/").replace("\n", " ")
        lines.append(
            f"| {row['id']} | {row['procedure']} | {row['technique']} | {LABELS[row['status']]} | {row['passed_cases']}/{row['total_cases']} | {row['attempts']} | {row['tokens']} | {differences} |"
        )
    lines += [
        "",
        "## Resumen",
        "",
        "```json",
        json.dumps(summary(run), ensure_ascii=False, indent=2),
        "```",
        "",
        "Tokens por técnica incluyen la primera llamada compartida. El gasto real se encuentra en usage_ledger; también incluye evaluaciones de prompts y consultas.",
    ]
    (destination / "results.md").write_text("\n".join(lines) + "\n")
    return records
