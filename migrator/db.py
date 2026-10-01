"""Trusted DB adapter: credentials and fixture resets never enter model context."""

from contextlib import closing
from decimal import Decimal
from datetime import date
import json
import pymssql
import psycopg
from psycopg import sql
from .compare import normalize
from .integrity import check_integrity

TABLES = {
    "clients": "id int PRIMARY KEY, name {text}(100) NOT NULL",
    "policies": "id int PRIMARY KEY, client_id int NOT NULL, code {text}(100) NOT NULL, start_date date NOT NULL, end_date date NULL, status {text}(100) NOT NULL, annual_premium decimal(19,4) NULL, notes {text}(100) NULL",
    "premiums": "id int PRIMARY KEY, policy_id int NOT NULL, due_date date NOT NULL, amount decimal(19,4) NULL",
    "payments": "id int PRIMARY KEY, policy_id int NOT NULL, paid_date date NOT NULL, amount decimal(19,4) NULL, reference {text}(100) NULL",
    "movements": "id int PRIMARY KEY, policy_id int NOT NULL, kind {text}(100) NOT NULL, amount decimal(19,4) NOT NULL",
}
DDL_CONTEXT = "\n".join(
    "CREATE TABLE domain." + t + " (" + ddl.format(text="varchar") + ");"
    for t, ddl in TABLES.items()
)


def tabular_result(sets):
    """Ignore only empty same-shape TDS preambles; retain all sets as evidence."""
    if not sets:
        return None
    last = sets[-1]
    if any(item["rows"] or item["columns"] != last["columns"] for item in sets[:-1]):
        return None
    return last


class Engines:
    def __init__(self, settings):
        self.s = settings

    def source(self, database="migration_source"):
        return pymssql.connect(
            server=self.s.sql_host,
            port=self.s.sql_port,
            user="sa",
            password=self.s.sql_password,
            database=database,
            autocommit=True,
            login_timeout=10,
            timeout=10,
            charset="UTF-8",
        )

    def target(self, admin=False, database="migration_target"):
        return psycopg.connect(
            host=self.s.pg_host,
            port=self.s.pg_port,
            user="postgres" if admin else "candidate",
            password=self.s.pg_password if admin else self.s.runner_password,
            dbname=database,
            autocommit=True,
            connect_timeout=10,
            options="-c statement_timeout=10000 -c lock_timeout=3000 -c search_path=pg_catalog,domain,migration",
        )

    def initialize(self):
        check_integrity(self.s.benchmark)
        with closing(self.source("master")) as conn:
            conn.cursor().execute(
                "IF DB_ID('migration_source') IS NULL CREATE DATABASE migration_source COLLATE Latin1_General_100_CI_AS;"
            )
        with self.target(True, "postgres") as conn:
            if not conn.execute(
                "SELECT 1 FROM pg_database WHERE datname='migration_target'"
            ).fetchone():
                conn.execute("CREATE DATABASE migration_target")
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='candidate'").fetchone():
                conn.execute(
                    sql.SQL(
                        "CREATE ROLE candidate LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
                    ).format(sql.Literal(self.s.runner_password))
                )
            else:
                conn.execute(
                    sql.SQL("ALTER ROLE candidate PASSWORD {}").format(
                        sql.Literal(self.s.runner_password)
                    )
                )
        with closing(self.source()) as conn:
            cur = conn.cursor()
            for table, ddl in TABLES.items():
                cur.execute(
                    f"IF OBJECT_ID('dbo.{table}') IS NULL CREATE TABLE dbo.{table} ({ddl.format(text='nvarchar')});"
                )
            for spec in self.specs():
                cur.execute((self.s.benchmark / spec["source"]).read_text())
            self.reset(conn, "source")
        with self.target(True) as conn:
            conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            conn.execute("CREATE SCHEMA IF NOT EXISTS domain AUTHORIZATION postgres")
            conn.execute("CREATE SCHEMA IF NOT EXISTS migration AUTHORIZATION candidate")
            conn.execute("GRANT USAGE ON SCHEMA domain TO candidate")
            for table, ddl in TABLES.items():
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS domain.{table} ({ddl.format(text='varchar')})"
                )
            conn.execute("GRANT SELECT ON ALL TABLES IN SCHEMA domain TO candidate")
            self.reset(conn, "target")
        self.assert_seed_equal()

    def specs(self):
        check_integrity(self.s.benchmark)
        return json.loads((self.s.benchmark / "procedures.json").read_text())

    def reset(self, conn, engine):
        # Immutable fixtures become mutable *working* tables; originals stay on disk.
        seed = json.loads((self.s.benchmark / "seed.json").read_text())
        schema = "dbo" if engine == "source" else "domain"
        cur = conn.cursor()
        for table in reversed(TABLES):
            cur.execute(f"DELETE FROM {schema}.{table}")
        for table, data in seed.items():
            if data["rows"]:
                placeholders = ",".join(["%s"] * len(data["columns"]))
                cur.executemany(
                    f"INSERT INTO {schema}.{table} ({','.join(data['columns'])}) VALUES ({placeholders})",
                    data["rows"],
                )
        cur.close()

    def snapshot(self, conn, engine):
        result = {}
        schema = "dbo" if engine == "source" else "domain"
        cur = conn.cursor()
        for table in TABLES:
            cur.execute(f"SELECT * FROM {schema}.{table} ORDER BY id")
            result[table] = [[normalize(v) for v in row] for row in cur.fetchall()]
        cur.close()
        return result

    def assert_seed_equal(self):
        with closing(self.source()) as source, self.target(True) as target:
            if self.snapshot(source, "source") != self.snapshot(target, "target"):
                raise RuntimeError("Los datos iniciales difieren entre motores.")

    def install(self, code, spec):
        with self.target(True) as admin:
            admin.execute(
                "REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA domain FROM candidate"
            )
            for table in spec["write_tables"]:
                admin.execute(
                    sql.SQL("GRANT INSERT, UPDATE, DELETE ON domain.{} TO candidate").format(
                        sql.Identifier(table)
                    )
                )
            # Clean owned migration routines/temp artifacts between proposals.
            admin.execute("DROP SCHEMA migration CASCADE")
            admin.execute("CREATE SCHEMA migration AUTHORIZATION candidate")
        with self.target() as conn:
            conn.execute(code)

    def execute(self, spec, case, engine):
        args = []
        for param, value in zip(spec["params"], case["args"], strict=True):
            if value is not None:
                if param["pg"] == "numeric":
                    value = Decimal(value)
                if param["pg"] == "date":
                    value = date.fromisoformat(value)
            args.append(value)
        result = {
            "columns": [],
            "rows": [],
            "error": None,
            "raw_error": None,
            "state": {},
            "result_sets": [],
            "empty_metadata_preambles": 0,
        }
        conn = self.source() if engine == "source" else self.target()
        with closing(conn):
            if engine == "source":
                self.reset(conn, engine)
            else:
                with self.target(True) as admin:
                    self.reset(admin, engine)
            cur = conn.cursor()
            try:
                if engine == "source":
                    cur.execute(
                        "EXEC dbo." + spec["name"] + " " + ",".join(["%s"] * len(args)), tuple(args)
                    )
                else:
                    casts = ",".join("%s::" + p["pg"] for p in spec["params"])
                    query = (
                        ("CALL migration." + spec["name"] + "(" + casts + ",NULL::text)")
                        if spec["target_kind"] == "procedure"
                        else "SELECT * FROM migration." + spec["name"] + "(" + casts + ")"
                    )
                    cur.execute(query, tuple(args))
                sets = []
                while True:
                    if cur.description:
                        sets.append(
                            {
                                "columns": [c[0] for c in cur.description],
                                "rows": [[normalize(v) for v in row] for row in cur.fetchall()],
                            }
                        )
                    if engine != "source" or not cur.nextset():
                        break
                result["result_sets"] = sets
                relation = tabular_result(sets)
                if relation is None:
                    result["error"] = "RESULT_SET_CONTRACT"
                else:
                    result.update(relation)
                    result["empty_metadata_preambles"] = len(sets) - 1
            except (pymssql.Error, psycopg.Error) as error:
                message = str(error)
                result["raw_error"] = message
                # Only predeclared tagged business errors have cross-engine identity.
                if engine == "source":
                    tag = {50001: "INVALID_AMOUNT", 50002: "POLICY_NOT_FOUND"}.get(
                        error.args[0] if error.args else None
                    )
                else:
                    primary = error.diag.message_primary
                    tag = primary if primary in {"INVALID_AMOUNT", "POLICY_NOT_FOUND"} else None
                result["error"] = tag or ("SOURCE_ERROR" if engine == "source" else "TARGET_ERROR")
                if engine == "source":
                    conn.cursor().execute("IF @@TRANCOUNT>0 ROLLBACK TRANSACTION")
            finally:
                cur.close()
            result["state"] = self.snapshot(conn, engine)
        return result
