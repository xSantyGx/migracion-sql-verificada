# Resultados de la migración

Ejecución: `verificacion-final` · Modelo: `gpt-5-mini`

Equivalencia sobre casos ejecutados. Diferencias declaradas se muestran por separado.

| ID | Procedimiento | Técnica | Estado | Casos | Intentos | Tokens | Diferencias declaradas |
|---|---|---|---|---|---|---|---|
| 01 | get_policy | direct | Equivalente | 8/8 | 1 | 2118 |  |
| 01 | get_policy | agent | Equivalente | 8/8 | 1 | 2118 |  |
| 02 | client_policies | direct | Equivalente | 8/8 | 1 | 2377 |  |
| 02 | client_policies | agent | Equivalente | 8/8 | 1 | 2377 |  |
| 03 | premium_total | direct | Equivalente | 8/8 | 1 | 2474 | Rounding: The original T-SQL casts to decimal(19,4). PostgreSQL casting to numeric(19,4) may have different midpoint (.5) rounding behavior than SQL Server's ROUND/CAST semantics (SQL Server rounds halves away from zero in some contexts). If exact tie-breaking for .00005 fractions matters, review results.; Collation: The source used Latin1_General_100_CI_AS collation in SQL Server. This routine does not perform string comparisons or ordering, so no collation behaviour is required here. If callers rely on collation elsewhere, that remains a platform difference.; Aggregate NULL handling: SUM over all-NULL yields NULL in both engines; this function preserves the original ISNULL(...,0) behavior by using COALESCE(SUM(amount),0). |
| 03 | premium_total | agent | Equivalente | 8/8 | 1 | 2474 | Rounding: The original T-SQL casts to decimal(19,4). PostgreSQL casting to numeric(19,4) may have different midpoint (.5) rounding behavior than SQL Server's ROUND/CAST semantics (SQL Server rounds halves away from zero in some contexts). If exact tie-breaking for .00005 fractions matters, review results.; Collation: The source used Latin1_General_100_CI_AS collation in SQL Server. This routine does not perform string comparisons or ordering, so no collation behaviour is required here. If callers rely on collation elsewhere, that remains a platform difference.; Aggregate NULL handling: SUM over all-NULL yields NULL in both engines; this function preserves the original ISNULL(...,0) behavior by using COALESCE(SUM(amount),0). |
| 04 | payment_summary | direct | Equivalente | 8/8 | 1 | 2429 |  |
| 04 | payment_summary | agent | Equivalente | 8/8 | 1 | 2429 |  |
| 05 | outstanding_balance | direct | Equivalente | 8/8 | 1 | 2387 |  |
| 05 | outstanding_balance | agent | Equivalente | 8/8 | 1 | 2387 |  |
| 06 | due_premiums | direct | Equivalente | 8/8 | 1 | 2343 |  |
| 06 | due_premiums | agent | Equivalente | 8/8 | 1 | 2343 |  |
| 07 | expiry_window | direct | Equivalente | 8/8 | 1 | 2393 |  |
| 07 | expiry_window | agent | Equivalente | 8/8 | 1 | 2393 |  |
| 08 | date_boundaries | direct | Equivalente | 8/8 | 1 | 2677 | PostgreSQL does not support SQL Server collations; if calling code relies on Latin1_General_100_CI_AS ordering or comparisons of text within this routine, results may differ. This routine does not perform any string comparison or ordering, so no practical collation impact is present here.; SQL Server DATEDIFF counts boundary crossings for the specified datepart. The implementation reproduces that semantics: days as (to_date - from_date) and months computed by year/month difference. Edge cases involving end-of-month behave like DATEDIFF(month) because we compute month boundaries via year/month arithmetic.; No differences for NULL handling: T-SQL DATEDIFF with NULL yields NULL and the PostgreSQL expressions also yield NULL when any input is NULL.; Rounding and numeric differences are not applicable (no floating types used); monetary types avoided as required. |
| 08 | date_boundaries | agent | Equivalente | 8/8 | 1 | 2677 | PostgreSQL does not support SQL Server collations; if calling code relies on Latin1_General_100_CI_AS ordering or comparisons of text within this routine, results may differ. This routine does not perform any string comparison or ordering, so no practical collation impact is present here.; SQL Server DATEDIFF counts boundary crossings for the specified datepart. The implementation reproduces that semantics: days as (to_date - from_date) and months computed by year/month difference. Edge cases involving end-of-month behave like DATEDIFF(month) because we compute month boundaries via year/month arithmetic.; No differences for NULL handling: T-SQL DATEDIFF with NULL yields NULL and the PostgreSQL expressions also yield NULL when any input is NULL.; Rounding and numeric differences are not applicable (no floating types used); monetary types avoided as required. |
| 09 | prorated_premium | direct | Equivalente | 8/8 | 1 | 2846 |  |
| 09 | prorated_premium | agent | Equivalente | 8/8 | 1 | 2846 |  |
| 10 | round_amount | direct | Equivalente | 8/8 | 1 | 2945 |  |
| 10 | round_amount | agent | Equivalente | 8/8 | 1 | 2945 |  |
| 11 | null_and_concat | direct | Equivalente | 8/8 | 1 | 2144 |  |
| 11 | null_and_concat | agent | Equivalente | 8/8 | 1 | 2144 |  |
| 12 | search_code | direct | Equivalente | 8/8 | 1 | 2411 | Collation: SQL Server used Latin1_General_100_CI_AS for the equality comparison. PostgreSQL does not reproduce that collation here. The function implements case-insensitive comparison via lower(code) = lower(p_code). This differs from Latin1_General_100_CI_AS in at least the following concrete ways: accent sensitivity/insensitivity and Unicode case-folding rules may differ, and sort ordering for strings may differ. If exact Latin1_General_100_CI_AS semantics are required, a database collation or ICU-based collation configured to match must be used externally.; Ordering: ORDER BY id is preserved exactly. If original ordering depended on a string collation it would need explicit specification; here ordering is only by id so unaffected.; NULL handling: The WHERE includes code IS NOT NULL to avoid lower(NULL) semantics; this preserves that rows with NULL code are excluded as in the original equality comparison. (Behavior for comparisons with NULL is otherwise the same.) |
| 12 | search_code | agent | Equivalente | 8/8 | 1 | 2411 | Collation: SQL Server used Latin1_General_100_CI_AS for the equality comparison. PostgreSQL does not reproduce that collation here. The function implements case-insensitive comparison via lower(code) = lower(p_code). This differs from Latin1_General_100_CI_AS in at least the following concrete ways: accent sensitivity/insensitivity and Unicode case-folding rules may differ, and sort ordering for strings may differ. If exact Latin1_General_100_CI_AS semantics are required, a database collation or ICU-based collation configured to match must be used externally.; Ordering: ORDER BY id is preserved exactly. If original ordering depended on a string collation it would need explicit specification; here ordering is only by id so unaffected.; NULL handling: The WHERE includes code IS NOT NULL to avoid lower(NULL) semantics; this preserves that rows with NULL code are excluded as in the original equality comparison. (Behavior for comparisons with NULL is otherwise the same.) |
| 13 | top_policies | direct | Equivalente | 8/8 | 1 | 2241 |  |
| 13 | top_policies | agent | Equivalente | 8/8 | 1 | 2241 |  |
| 14 | temp_balances | direct | Equivalente | 8/8 | 1 | 2393 |  |
| 14 | temp_balances | agent | Equivalente | 8/8 | 1 | 2393 |  |
| 15 | cursor_total | direct | No compila | 0/0 | 1 | 2857 | Collation: the original procedure did not perform string comparison or ordering that depends on SQL Server collation; therefore no collation-related semantic difference applies here.; Rounding: SQL Server ROUND(val,2) rounds halves away from zero. The function includes an explicit implementation (round_sqlserver) to reproduce that behavior. If PostgreSQL's built-in round() differs in edge cases, this implementation is used to preserve SQL Server semantics.; Types: monetary fields are handled as numeric(19,4) and the running total as numeric(19,2) to match the original precision/scale. PostgreSQL's numeric may behave differently in internal representation but preserves numeric semantics.; Control-flow adaptation: the T-SQL cursor is replaced by a FOR ... LOOP over an ordered SELECT. This preserves row order, NULL handling and per-row rounding. This is an adaptation, not a semantic mismatch, but noted for review. |
| 15 | cursor_total | agent | Equivalente | 8/8 | 2 | 6459 | Collation: the original procedure did not perform string comparison or ordering that depends on SQL Server collation; therefore no collation-related semantic difference applies here.; Rounding: SQL Server ROUND(val,2) rounds halves away from zero. The translation implements that behavior explicitly per row using floor(abs(val)*100 + 0.5)/100 with sign handling. This reproduces the SQL Server half-away-from-zero rounding rule. Edge cases tied to different numeric precisions are handled by casting to numeric(19,2).; Types: monetary fields are handled as numeric(19,4) for source amounts and numeric(19,2) for the running total to match the original precision/scale. PostgreSQL numeric preserves arithmetic semantics but may differ in internal representation.; Control-flow adaptation: the T-SQL cursor is replaced by a FOR ... LOOP over an ORDER BY id SELECT. This preserves row order, per-row rounding, NULL handling and accumulation semantics. The procedural cursor semantics are preserved functionally. |
| 16 | dynamic_filter | direct | Compila pero difiere | 7/8 | 1 | 2361 | Collation: SQL Server original usa Latin1_General_100_CI_AS. PostgreSQL no aplica esa collation por defecto; comparaciones de cadenas (por ejemplo status) pueden comportarse diferente en cuanto a mayúsculas/minúsculas y ordenamiento. Si la semántica depende de esa collation (sensibilidad a mayúsculas o reglas de ordenamiento), se requiere revisión humana.; Execution model: la implementación T-SQL invoca sp_executesql con un parámetro nombrado. En PostgreSQL se usa RETURN QUERY EXECUTE con USING; funcionalmente equivalente para estos casos, pero la adaptación se realiza explícitamente y no reproduce otros efectos de sp_executesql (por ejemplo, persistencia de variables de sesión). |
| 16 | dynamic_filter | agent | Compila pero difiere | 7/8 | 1 | 2361 | Collation: SQL Server original usa Latin1_General_100_CI_AS. PostgreSQL no aplica esa collation por defecto; comparaciones de cadenas (por ejemplo status) pueden comportarse diferente en cuanto a mayúsculas/minúsculas y ordenamiento. Si la semántica depende de esa collation (sensibilidad a mayúsculas o reglas de ordenamiento), se requiere revisión humana.; Execution model: la implementación T-SQL invoca sp_executesql con un parámetro nombrado. En PostgreSQL se usa RETURN QUERY EXECUTE con USING; funcionalmente equivalente para estos casos, pero la adaptación se realiza explícitamente y no reproduce otros efectos de sp_executesql (por ejemplo, persistencia de variables de sesión). |
| 17 | safe_ratio | direct | Equivalente | 8/8 | 1 | 2817 | Redondeo: el CAST a numeric(19,4) en PostgreSQL puede aplicar reglas de redondeo distintas a las de SQL Server (SQL Server aleja mitades de cero). Esto puede producir diferencias en resultados cuando el valor termina exactamente en un 0.00005 respecto de 4 decimales.; Código de error/excepciones: SQL Server emplea TRY/CATCH con errores de motor T-SQL; en PostgreSQL se captura la condición SQLSTATE 'division_by_zero' y se convierte al literal 'DIVISION_BY_ZERO' para conservar el contrato. El SQLSTATE interno y los números de error difieren entre motores.; Collation: SQL Server original usa Latin1_General_100_CI_AS. Si se realizaran comparaciones u ordenamientos de texto aquí podrían comportar diferencias de collation en PostgreSQL; en este procedimiento específico no hay ordenamiento ni comparación de texto que dependa de collation.; Transaccionalidad: el comportamiento de manejo de transacciones en presencia de errores difiere entre motores; la función en PostgreSQL captura la excepción y devuelve el resultado sin abortar la transacción de llamada, que intenta reproducir la intención del PROCEDURE original, pero los detalles de anidamiento de transacciones/errores pueden variar. |
| 17 | safe_ratio | agent | Equivalente | 8/8 | 1 | 2817 | Redondeo: el CAST a numeric(19,4) en PostgreSQL puede aplicar reglas de redondeo distintas a las de SQL Server (SQL Server aleja mitades de cero). Esto puede producir diferencias en resultados cuando el valor termina exactamente en un 0.00005 respecto de 4 decimales.; Código de error/excepciones: SQL Server emplea TRY/CATCH con errores de motor T-SQL; en PostgreSQL se captura la condición SQLSTATE 'division_by_zero' y se convierte al literal 'DIVISION_BY_ZERO' para conservar el contrato. El SQLSTATE interno y los números de error difieren entre motores.; Collation: SQL Server original usa Latin1_General_100_CI_AS. Si se realizaran comparaciones u ordenamientos de texto aquí podrían comportar diferencias de collation en PostgreSQL; en este procedimiento específico no hay ordenamiento ni comparación de texto que dependa de collation.; Transaccionalidad: el comportamiento de manejo de transacciones en presencia de errores difiere entre motores; la función en PostgreSQL captura la excepción y devuelve el resultado sin abortar la transacción de llamada, que intenta reproducir la intención del PROCEDURE original, pero los detalles de anidamiento de transacciones/errores pueden variar. |
| 18 | monthly_collections | direct | Equivalente | 8/8 | 1 | 2725 |  |
| 18 | monthly_collections | agent | Equivalente | 8/8 | 1 | 2725 |  |
| 19 | register_payment | direct | Equivalente | 8/8 | 1 | 3031 |  |
| 19 | register_payment | agent | Equivalente | 8/8 | 1 | 3031 |  |
| 20 | cancel_policy | direct | Equivalente | 8/8 | 1 | 3584 |  |
| 20 | cancel_policy | agent | Equivalente | 8/8 | 1 | 3584 |  |

## Resumen

```json
{
  "direct": {
    "counts": {
      "equivalent": 18,
      "compile_error": 1,
      "different": 1
    },
    "equivalent": 18,
    "total": 20,
    "equivalence_rate": 0.9,
    "tokens": 51553,
    "compiled_but_not_equivalent": 1
  },
  "agent": {
    "counts": {
      "equivalent": 19,
      "different": 1
    },
    "equivalent": 19,
    "total": 20,
    "equivalence_rate": 0.95,
    "tokens": 55155,
    "compiled_but_not_equivalent": 1
  }
}
```

Tokens por técnica incluyen la primera llamada compartida. El gasto real se encuentra en usage_ledger; también incluye evaluaciones de prompts y consultas.
