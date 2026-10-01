import hashlib
import json
from pathlib import Path
from pglast import ast, parse_sql
from pglast.parser import ParseError


class IntegrityViolation(RuntimeError):
    pass


class UnsafeProposal(RuntimeError):
    pass


def check_integrity(benchmark: Path):
    manifest = json.loads((benchmark / "manifest.json").read_text())
    for name, digest in manifest.items():
        path = benchmark / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise IntegrityViolation("Alteración de material protegido: " + name)
    return hashlib.sha256((benchmark / "manifest.json").read_bytes()).hexdigest()


def trust_fingerprint(settings):
    files = [
        settings.benchmark / "manifest.json",
        *sorted((settings.root / "migrator").glob("*.py")),
        *sorted((settings.root / "migrator/prompts").glob("*.txt")),
    ]
    return hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()


def validate_proposal(code, spec):
    try:
        statements = parse_sql(code)
    except ParseError:
        # Syntax errors belong to compilation results, not accusations of cheating.
        return
    if len(statements) != 1 or not isinstance(statements[0].stmt, ast.CreateFunctionStmt):
        raise UnsafeProposal(
            "Solo se permite una definición de rutina; instrucciones externas detectadas."
        )
    node = statements[0].stmt
    name = [part.sval for part in node.funcname]
    if name != ["migration", spec["name"]]:
        raise UnsafeProposal("Intento de definir objetos fuera de la rutina autorizada.")
    if node.is_procedure != (spec["target_kind"] == "procedure"):
        raise ValueError("El tipo de rutina no corresponde al contrato.")
    language = None
    for option in node.options or ():
        if option.defname == "language":
            language = option.arg.sval
        if option.defname == "security" and option.arg.boolval:
            raise UnsafeProposal("SECURITY DEFINER está prohibido.")
        if option.defname == "set":
            raise UnsafeProposal("La rutina no puede modificar configuración del ejecutor.")
    if language not in ["plpgsql", "sql"]:
        raise UnsafeProposal("Solo se permiten lenguajes SQL y PL/pgSQL.")
