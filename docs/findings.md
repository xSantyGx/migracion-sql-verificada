# Hallazgos de la evaluación real

Evaluación final: `verificacion-final`, ejecutada el 1 de octubre de 2026 contra SQL Server 2022 CU22 y PostgreSQL 16.13. Modelo devuelto por OpenAI: `gpt-5-mini-2025-08-07`. Los datos son sintéticos y propios.

| Técnica | Equivalentes | Instala pero difiere | No instala | Tokens lógicos |
|---|---:|---:|---:|---:|
| Directa, una pasada | 18/20 (90%) | 1 | 1 | 51.553 |
| Agente, hasta tres intentos | 19/20 (95%) | 1 | 0 | 55.155 |

La primera llamada de cada procedimiento es compartida. El agente solo necesitó una corrección en esta ejecución. El incremento lógico fue 3.602 tokens. Estos valores no incluyen calibraciones ni evaluación de prompts; el ledger global sí las incluye. No se afirma que la diferencia de cinco puntos porcentuales generalice a otras ejecuciones o a SQL de producción.

## Dónde falló cada técnica

**15 · `cursor_total`:** la primera propuesta incluyó una función local dentro de un bloque PL/pgSQL, una construcción que PostgreSQL no acepta. No instaló. El agente recibió el error de instalación y reemplazó el código por una implementación válida que conservó redondeo por fila. Coincidió en los ocho casos, incluidos los reservados.

**16 · `dynamic_filter`:** ambos enfoques instalaron, pero fallaron el caso reservado `16-07`, con entrada `active`. SQL Server usa collation case-insensitive y devuelve las pólizas ACTIVE. PostgreSQL devuelve un conjunto vacío con la comparación generada. La diferencia de collation está declarada en la propuesta. El agente pasó los seis casos de corrección, por lo que se detuvo sin recibir el caso reservado; no se modificó ese caso para conseguir 100%. Este procedimiento permanece no equivalente y no debe aprobarse para despliegue.

Los otros dieciocho procedimientos coincidieron desde el primer intento. El agente mantuvo esas propuestas y corrigió el cursor, quedando diecinueve equivalentes sobre los casos ejecutados. No hubo trampas espontáneas detectadas en la comparación final.

## Evaluación de prompts y detección

El prompt final pasó **10/10** evaluaciones reales de OpenAI: rechazo exacto fuera de dominio, consulta normal sin falsos avisos, modificaciones prohibidas, instrucciones incrustadas en comentarios, equivalencia inventada y limitaciones de collation/NOLOCK. El detector pasó **8/8** ataques controlados, incluyendo SQL de modificación de datos dentro del cuerpo de una rutina, escalada de privilegios, alteración de fixture y declaración falsa de éxito. Los ataques controlados se identifican por su origen; no se atribuyen al agente como conducta espontánea.

La primera versión del prompt era ambigua: el modelo enumeró políticas en `prohibited_requests`, provocando falsos positivos. La segunda corrigió eso, pero omitió registrar una solicitud explícita de alterar datos en una evaluación. La versión final agregó definiciones de campos y un ejemplo de esa solicitud. Se conservan los informes anteriores en `reports/calibration/`, junto con los prompts correspondientes. No se cambió la prueba fallida para mejorar la puntuación.

La calibración también reveló un defecto del adaptador TDS: un SELECT que falla dentro de TRY puede emitir metadatos vacíos antes de que CATCH devuelva su fila. El feedback incompleto hizo que el agente eliminara esa fila y luego perdiera precisión en la división. Se conservó esa evidencia, se corrigió el adaptador y se fijó su regla de preámbulos vacíos antes de repetir todo el experimento final. Las pruebas del original ahora exigen las columnas contractuales y la fila de error correspondiente.

## Qué aprobaría

Firmaría únicamente los procedimientos con evidencia completa, revisión de diferencias declaradas y contratos de consumo aceptados por el equipo. La equivalencia observada no demuestra comportamiento para cualquier cadena Unicode, cualquier transacción o acceso concurrente. No aprobaría `dynamic_filter` hasta implementar y validar una estrategia de collation sobre las entradas reales del sistema, incluidos acentos y espacios finales. Una declaración de diferencia es información para decidir, no permiso para marcar equivalencia.

Evidencia: [tabla completa](../reports/verificacion-final/results.md), [trazas por caso e intento](../reports/verificacion-final/run.json), [evaluación del prompt](../reports/prompt-evals.json), [ataques controlados](../reports/detection-evals.json), [ledger de consumo](../reports/usage.json).

La revalidación de las traducciones guardadas desde la aplicación Docker volvió a obtener 19 equivalentes y el mismo caso de collation diferente, sin usar OpenAI. [Estados y hash del verificador actual](../reports/revalidation.json). La aplicación desplegada también respondió la frase exacta de rechazo ante una solicitud de receta.
