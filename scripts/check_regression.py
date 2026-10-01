"""CI gate: previously equivalent procedures must remain equivalent.

The all-procedure CLI still exits 1 for any non-equivalent migration. This gate
also makes testing the checker possible when the benchmark has a known failure.
"""

import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
baseline = json.loads((root / "reports/verificacion-final/run.json").read_text())
observed = json.loads(
    (root / "artifacts" / f"verification-{baseline['id']}-agent.json").read_text()
)
by_id = {row["id"]: row["status"] for row in observed}
regressions = [
    p["id"]
    for p in baseline["procedures"]
    if p["agent"]["status"] == "equivalent" and by_id.get(p["id"]) != "equivalent"
]
if set(by_id) != {p["id"] for p in baseline["procedures"]}:
    print("Incomplete verification evidence", file=sys.stderr)
    sys.exit(1)
if regressions:
    print("Equivalent migrations regressed: " + ", ".join(regressions), file=sys.stderr)
    sys.exit(1)
print(
    "Previously equivalent procedures still pass; non-equivalent migrations remain flagged by the CLI."
)
