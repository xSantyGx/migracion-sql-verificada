"""Build the authored, deterministic benchmark. Never run this during agent evaluation."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "benchmark"
ROOT.mkdir(exist_ok=True)
(ROOT / "source").mkdir(exist_ok=True)
seed = {
    "clients": {
        "columns": ["id", "name"],
        "rows": [[1, "Ana"], [2, "José"], [3, "JOSE"], [4, "Sin pólizas"]],
    },
    "policies": {
        "columns": [
            "id",
            "client_id",
            "code",
            "start_date",
            "end_date",
            "status",
            "annual_premium",
            "notes",
        ],
        "rows": [
            [1, 1, "POL-A", "2024-01-01", "2024-12-31", "ACTIVE", "1000.0050", None],
            [2, 1, "pol-b", "2024-02-29", "2025-02-28", "ACTIVE", "1200.0000", ""],
            [3, 2, "POL-C", "2023-12-31", "2024-01-01", "EXPIRED", "0.0000", "áé"],
            [4, 3, "POL-D", "2024-06-01", None, "ACTIVE", "99.9950", "NULL"],
            [5, 2, "POL-E", "2024-01-01", "2024-01-01", "CANCELLED", "-10.0050", "prueba"],
            [6, 3, "POL-F", "2024-12-31", "2025-01-01", "ACTIVE", None, "redondeo"],
        ],
    },
    "premiums": {
        "columns": ["id", "policy_id", "due_date", "amount"],
        "rows": [
            [1, 1, "2024-01-01", "100.0050"],
            [2, 1, "2024-02-29", "200.0050"],
            [3, 1, "2024-12-31", None],
            [4, 2, "2024-02-29", "400.0000"],
            [5, 2, "2025-02-28", "400.0000"],
            [6, 3, "2024-01-01", "0.0000"],
            [7, 4, "2024-06-01", "-10.0050"],
            [8, 4, "2024-06-01", "10.0050"],
            [9, 6, "2024-12-31", "0.0050"],
        ],
    },
    "payments": {
        "columns": ["id", "policy_id", "paid_date", "amount", "reference"],
        "rows": [
            [1, 1, "2024-01-01", "100.0000", "ABC"],
            [2, 1, "2024-03-01", "50.0050", "abc"],
            [3, 2, "2024-02-29", "400.0000", None],
            [4, 4, "2024-06-01", "0.0000", ""],
            [5, 6, "2025-01-01", "0.0050", "X "],
        ],
    },
    "movements": {"columns": ["id", "policy_id", "kind", "amount"], "rows": []},
}
(ROOT / "seed.json").write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n")
specs = []


def add(
    n, name, description, params, columns, body, cases, ordered=False, writes=None, kind="function"
):
    source = (
        f"CREATE OR ALTER PROCEDURE dbo.{name}\n"
        + (", ".join("@" + p["name"] + " " + p["tsql"] for p in params))
        + "\nAS\nBEGIN\n SET NOCOUNT ON;\n "
        + body
        + "\nEND;\n"
    )
    path = f"source/{n:02d}_{name}.sql"
    (ROOT / path).write_text(source)
    specs.append(
        {
            "id": f"{n:02d}",
            "name": name,
            "description": description,
            "source": path,
            "params": params,
            "columns": columns,
            "ordered": ordered,
            "write_tables": writes or [],
            "target_kind": kind,
            "cases": [
                {"id": f"{n:02d}-{i + 1:02d}", "args": args, "reserved": i >= 6}
                for i, args in enumerate(cases)
            ],
        }
    )


def p(name, tsql, pg):
    return {"name": name, "tsql": tsql, "pg": pg}


def integer_param(name):
    return p(name, "int", "integer")


def D(name):
    return p(name, "date", "date")


def N(name):
    return p(name, "decimal(19,4)", "numeric")


def S(name):
    return p(name, "nvarchar(100)", "text")


ids = [[1], [2], [3], [4], [999], [None], [5], [6]]
add(
    1,
    "get_policy",
    "Consulta simple y ausencia de fila",
    [integer_param("policy_id")],
    ["id", "code", "annual_premium"],
    "SELECT id,code,annual_premium FROM dbo.policies WHERE id=@policy_id;",
    ids,
)
add(
    2,
    "client_policies",
    "Filtro opcional y orden",
    [integer_param("client_id")],
    ["id", "code", "status"],
    "SELECT id,code,status FROM dbo.policies WHERE @client_id IS NULL OR client_id=@client_id ORDER BY id;",
    [[1], [2], [3], [4], [None], [999], [0], [-1]],
    True,
)
add(
    3,
    "premium_total",
    "SUM vacío y NULL",
    [integer_param("policy_id")],
    ["total"],
    "SELECT CAST(ISNULL(SUM(amount),0) AS decimal(19,4)) AS total FROM dbo.premiums WHERE policy_id=@policy_id;",
    ids,
)
add(
    4,
    "payment_summary",
    "COUNT y SUM tienen distintas reglas para NULL",
    [integer_param("policy_id")],
    ["payment_count", "total"],
    "SELECT COUNT(*) AS payment_count, CAST(ISNULL(SUM(amount),0) AS decimal(19,4)) AS total FROM dbo.payments WHERE policy_id=@policy_id;",
    ids,
)
add(
    5,
    "outstanding_balance",
    "Evitar multiplicación de filas al unir pagos y primas",
    [integer_param("policy_id")],
    ["balance"],
    "SELECT CAST((SELECT ISNULL(SUM(amount),0) FROM dbo.premiums WHERE policy_id=@policy_id)-(SELECT ISNULL(SUM(amount),0) FROM dbo.payments WHERE policy_id=@policy_id) AS decimal(19,4)) AS balance;",
    ids,
)
add(
    6,
    "due_premiums",
    "Límite de fecha inclusivo",
    [D("as_of")],
    ["id", "policy_id", "amount"],
    "SELECT id,policy_id,amount FROM dbo.premiums WHERE due_date<=@as_of ORDER BY due_date,id;",
    [
        [d]
        for d in [
            "2024-01-01",
            "2024-02-28",
            "2024-02-29",
            "2024-06-01",
            "1900-01-01",
            None,
            "2024-12-31",
            "2025-02-28",
        ]
    ],
    True,
)
add(
    7,
    "expiry_window",
    "BETWEEN inclusivo y extremos invertidos",
    [D("from_date"), D("to_date")],
    ["id", "end_date"],
    "SELECT id,end_date FROM dbo.policies WHERE end_date BETWEEN @from_date AND @to_date ORDER BY id;",
    [
        ["2024-01-01", "2024-12-31"],
        ["2024-01-01", "2024-01-01"],
        ["2024-02-28", "2024-02-29"],
        ["2025-01-01", "2024-01-01"],
        [None, "2024-12-31"],
        ["1900-01-01", "1900-01-02"],
        ["2025-01-01", "2025-02-28"],
        ["2024-12-31", None],
    ],
    True,
)
add(
    8,
    "date_boundaries",
    "DATEDIFF cuenta fronteras de día y mes",
    [D("from_date"), D("to_date")],
    ["days", "months"],
    "SELECT DATEDIFF(day,@from_date,@to_date) AS days,DATEDIFF(month,@from_date,@to_date) AS months;",
    [
        ["2024-01-31", "2024-02-01"],
        ["2024-02-28", "2024-03-01"],
        ["2024-03-01", "2024-02-28"],
        ["2024-01-01", "2024-01-01"],
        [None, "2024-01-01"],
        ["2023-12-31", "2024-01-01"],
        ["2024-02-29", "2025-02-28"],
        ["2025-01-01", "2024-12-31"],
    ],
)
add(
    9,
    "prorated_premium",
    "Prorrateo decimal con año bisiesto",
    [integer_param("policy_id"), integer_param("days")],
    ["premium"],
    "SELECT CAST(ROUND(annual_premium * CAST(@days AS decimal(19,4)) / 365,2) AS decimal(19,2)) AS premium FROM dbo.policies WHERE id=@policy_id;",
    [[1, 1], [2, 366], [4, 0], [5, 1], [999, 10], [1, None], [6, 365], [1, -30]],
)
add(
    10,
    "round_amount",
    "ROUND mitades alejadas de cero",
    [N("amount"), integer_param("digits")],
    ["rounded"],
    "SELECT CAST(ROUND(@amount,@digits) AS decimal(19,4)) AS rounded;",
    [
        [str(a), d]
        for a, d in [
            ("1.005", 2),
            ("-1.005", 2),
            ("99.995", 2),
            ("0.0049", 2),
            ("125", -1),
            ("0", 0),
            ("2.675", 2),
            ("-125", -1),
        ]
    ],
)
add(
    11,
    "null_and_concat",
    "ISNULL y CONCAT con NULL",
    [integer_param("policy_id")],
    ["label", "notes"],
    "SELECT CONCAT(code,':',notes) AS label,ISNULL(notes,N'(sin nota)') AS notes FROM dbo.policies WHERE id=@policy_id;",
    ids,
)
add(
    12,
    "search_code",
    "Collation explícita case-insensitive sin normalizar resultados",
    [S("code")],
    ["id", "code"],
    "SELECT id,code FROM dbo.policies WHERE code COLLATE Latin1_General_100_CI_AS=@code ORDER BY id;",
    [[x] for x in ["POL-A", "pol-a", "POL-B", "pol-b", "no-existe", None, "POL-C", "pol-f"]],
    True,
)
add(
    13,
    "top_policies",
    "TOP con orden y desempate fijo",
    [integer_param("limit_count")],
    ["id", "annual_premium"],
    "SELECT TOP (@limit_count) id,annual_premium FROM dbo.policies WHERE annual_premium IS NOT NULL ORDER BY annual_premium DESC,id;",
    [[1], [2], [0], [10], [3], [4], [5], [6]],
    True,
)
add(
    14,
    "temp_balances",
    "Tabla temporal y agregaciones",
    [integer_param("client_id")],
    ["id", "balance"],
    "CREATE TABLE #balances(id int,balance decimal(19,4)); INSERT INTO #balances SELECT p.id,ISNULL((SELECT SUM(amount) FROM dbo.premiums WHERE policy_id=p.id),0)-ISNULL((SELECT SUM(amount) FROM dbo.payments WHERE policy_id=p.id),0) FROM dbo.policies p WHERE p.client_id=@client_id; SELECT id,balance FROM #balances ORDER BY id; DROP TABLE #balances;",
    [[1], [2], [3], [4], [999], [None], [0], [-1]],
    True,
)
add(
    15,
    "cursor_total",
    "Cursor con redondeo por fila, no sobre la suma",
    [integer_param("policy_id")],
    ["total"],
    "DECLARE @amount decimal(19,4),@total decimal(19,2)=0; DECLARE premium_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT amount FROM dbo.premiums WHERE policy_id=@policy_id ORDER BY id; OPEN premium_cursor; FETCH NEXT FROM premium_cursor INTO @amount; WHILE @@FETCH_STATUS=0 BEGIN SET @total=@total+ISNULL(ROUND(@amount,2),0); FETCH NEXT FROM premium_cursor INTO @amount; END; CLOSE premium_cursor; DEALLOCATE premium_cursor; SELECT @total AS total;",
    ids,
)
add(
    16,
    "dynamic_filter",
    "SQL dinámico parametrizado",
    [S("status")],
    ["id", "code"],
    "DECLARE @sql nvarchar(max)=N'SELECT id,code FROM dbo.policies WHERE status=@s ORDER BY id'; EXEC sp_executesql @sql,N'@s nvarchar(100)',@s=@status;",
    [
        [x]
        for x in [
            "ACTIVE",
            "EXPIRED",
            "CANCELLED",
            "MISSING",
            None,
            "ACTIVE' OR 1=1 --",
            "active",
            "",
        ]
    ],
    True,
)
add(
    17,
    "safe_ratio",
    "TRY/CATCH con división por cero",
    [N("numerator"), N("denominator")],
    ["ratio", "error_code"],
    "BEGIN TRY SELECT CAST(@numerator/@denominator AS decimal(19,4)) AS ratio,CAST(NULL AS nvarchar(30)) AS error_code; END TRY BEGIN CATCH SELECT CAST(NULL AS decimal(19,4)) AS ratio,N'DIVISION_BY_ZERO' AS error_code; END CATCH;",
    [
        ["10", "2"],
        ["1", "3"],
        ["1", "0"],
        ["-1", "2"],
        [None, "1"],
        ["1", None],
        ["0", "0"],
        ["0.0001", "2"],
    ],
)
add(
    18,
    "monthly_collections",
    "SQL Server fin de mes y agregación",
    [D("month_date")],
    ["month_end", "total"],
    "SELECT EOMONTH(@month_date) AS month_end,CAST(ISNULL(SUM(amount),0) AS decimal(19,4)) AS total FROM dbo.payments WHERE paid_date>=DATEFROMPARTS(YEAR(@month_date),MONTH(@month_date),1) AND paid_date<=EOMONTH(@month_date);",
    [
        [d]
        for d in [
            "2024-02-01",
            "2024-02-29",
            "2024-01-31",
            "2024-03-01",
            "1900-01-01",
            None,
            "2024-06-30",
            "2025-01-01",
        ]
    ],
)
add(
    19,
    "register_payment",
    "Validación, THROW y efecto persistente",
    [integer_param("policy_id"), N("amount")],
    ["payment_id", "total_paid"],
    "IF @amount IS NULL OR @amount<=0 THROW 50001,'INVALID_AMOUNT',1; IF NOT EXISTS(SELECT 1 FROM dbo.policies WHERE id=@policy_id) THROW 50002,'POLICY_NOT_FOUND',1; DECLARE @new_id int=(SELECT ISNULL(MAX(id),0)+1 FROM dbo.payments); INSERT INTO dbo.payments(id,policy_id,paid_date,amount,reference) VALUES(@new_id,@policy_id,'2024-07-01',@amount,'NEW'); SELECT @new_id AS payment_id,CAST(SUM(amount) AS decimal(19,4)) AS total_paid FROM dbo.payments WHERE policy_id=@policy_id;",
    [
        [1, "10.005"],
        [2, "1"],
        [1, "0"],
        [1, "-1"],
        [999, "10"],
        [1, None],
        [4, "0.005"],
        [None, "10"],
    ],
    writes=["payments"],
)
add(
    20,
    "cancel_policy",
    "Transacción atómica con salida y bitácora",
    [integer_param("policy_id")],
    ["result"],
    "IF NOT EXISTS(SELECT 1 FROM dbo.policies WHERE id=@policy_id) THROW 50002,'POLICY_NOT_FOUND',1; BEGIN TRY BEGIN TRANSACTION; UPDATE dbo.policies SET status='CANCELLED' WHERE id=@policy_id; INSERT INTO dbo.movements(id,policy_id,kind,amount) SELECT ISNULL(MAX(id),0)+1,@policy_id,'CANCEL',0 FROM dbo.movements; COMMIT TRANSACTION; SELECT CAST('CANCELLED' AS nvarchar(30)) AS result; END TRY BEGIN CATCH IF @@TRANCOUNT>0 ROLLBACK TRANSACTION; THROW; END CATCH;",
    ids,
    writes=["policies", "movements"],
    kind="procedure",
)
(ROOT / "procedures.json").write_text(json.dumps(specs, ensure_ascii=False, indent=2) + "\n")
protected = ["seed.json", "procedures.json"] + [s["source"] for s in specs]
manifest = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in protected}
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(
    "Authored benchmark:", len(specs), "procedures;", sum(len(s["cases"]) for s in specs), "cases"
)
