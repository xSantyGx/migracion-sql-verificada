"""Fixed comparison rules. Never use an LLM to decide equality."""

from collections import Counter
from datetime import date, datetime
from decimal import Decimal
import json


def normalize(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return {"boolean": value}
    if isinstance(value, (Decimal, int)):
        number = Decimal(value)
        return {"number": format(number.normalize(), "f") if number else "0"}
    if isinstance(value, float):
        # Financial fixtures use DECIMAL; float coercion is deliberately not accepted.
        return {"float": repr(value)}
    if isinstance(value, datetime):
        return {"datetime": value.isoformat()}
    if isinstance(value, date):
        return {"date": value.isoformat()}
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    return {"text": str(value)}


def encoded(rows):
    return [json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows]


def compare(source, target, ordered=False):
    differences = []
    if source["error"] != target["error"]:
        differences.append({"field": "error", "source": source["error"], "target": target["error"]})
    if source["columns"] != target["columns"]:
        differences.append(
            {"field": "columns", "source": source["columns"], "target": target["columns"]}
        )
    a, b = encoded(source["rows"]), encoded(target["rows"])
    equal = a == b if ordered else Counter(a) == Counter(b)
    if not equal:
        differences.append({"field": "rows", "source": source["rows"], "target": target["rows"]})
    if source["state"] != target["state"]:
        for table in source["state"]:
            if source["state"][table] != target["state"].get(table):
                differences.append(
                    {
                        "field": "state." + table,
                        "source": source["state"][table],
                        "target": target["state"].get(table),
                    }
                )
    return differences
