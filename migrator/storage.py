import json
import os
import re
from pathlib import Path
from filelock import FileLock


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    temp.replace(path)


def run_path(settings, run_id):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", run_id):
        raise ValueError("Identificador de ejecución inválido.")
    return settings.artifacts / run_id / "run.json"


def load_run(settings, run_id=None):
    if run_id:
        path = run_path(settings, run_id)
        if not path.exists():
            path = settings.root / "reports" / run_id / "run.json"
    else:
        paths = sorted(settings.artifacts.glob("*/run.json"), key=lambda p: p.stat().st_mtime)
        if not paths:
            paths = sorted((settings.root / "reports").glob("*/run.json"))
        if not paths:
            raise FileNotFoundError("Aún no hay evaluaciones. Ejecuta migrator benchmark.")
        path = paths[-1]
    return json.loads(path.read_text())


def engine_lock(settings):
    settings.artifacts.mkdir(parents=True, exist_ok=True)
    return FileLock(str(settings.artifacts / "engines.lock"), timeout=1)
