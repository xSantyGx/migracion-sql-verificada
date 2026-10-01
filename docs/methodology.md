# Metodología y contexto de dominio

## Material recibido y conjunto construido

Solo se recibieron la guía Word y una clave OpenAI. Los veinte procedimientos, el Compose y los datos anunciados en el Word no estaban adjuntos. Este repositorio contiene un benchmark propio, no una reproducción atribuida a FactorIT. `scripts/create_benchmark.py` documenta cómo se construyó. No se ejecuta durante una evaluación. Cambiar el benchmark requiere una revisión humana explícita y una nueva ejecución; reanudar con otro hash se rechaza.

El modelo representa pólizas con fecha inicial/final, primas exigibles y pagos. Un saldo correcto suma primas y resta pagos por separado: unir ambas tablas antes de sumar puede multiplicar importes. Dinero usa DECIMAL(19,4); montos calculados con dos decimales conservan el redondeo en el punto del cálculo original.

## Diseño experimental

Hay 20 procedimientos × 8 entradas = 160 casos por técnica. Seis entradas son visibles para corregir y dos son reservadas. Los originales se ejecutan en SQL Server, no se reemplazan con respuestas Python. La primera propuesta es compartida: directa se detiene y agente puede corregirla hasta tres intentos totales. Ambas técnicas usan el mismo prompt, modelo y contratos, aislando el efecto del feedback ejecutado. Se generan primero todos los intentos directos para que las correcciones no consuman el presupuesto antes de cubrir el conjunto.

El resultado es una comparación emparejada de una ejecución; no una estimación estadística de superioridad universal. El snapshot exacto del modelo devuelto, los paquetes, los hashes y los IDs de respuesta se registran. OpenAI puede generar resultados diferentes en otra ejecución. Reejecutar las traducciones guardadas no consume API y sí comprueba regresiones.

El denominador de equivalencia incluye todos los procedimientos, también los incompletos. "Compila" significa que CREATE FUNCTION/PROCEDURE fue aceptado; PostgreSQL puede diferir validación de ciertas referencias al primer uso. Por ello se distingue error de instalación de error en ejecución. Diferencias semánticas declaradas son un atributo independiente: no excusan un resultado distinto, y pasar casos con advertencias exige revisión humana.

## Comparación y equivalencia

Se comparan columnas, filas, errores y el estado completo de tablas. Sin ORDER BY contractual se compara un multiconjunto, preservando duplicados. Con orden contractual, se compara posición. Decimal e integer se normalizan a valor numérico exacto, sin tolerancia; no se convierten floats a dinero. Fechas date se normalizan a ISO. Las cadenas no se recortan, no se convierten a minúsculas ni se normalizan Unicode. NULL no equivale a cadena vacía ni a texto "NULL".

`INVALID_AMOUNT` y `POLICY_NOT_FOUND` son errores de negocio declarados en el benchmark. Se comparan esos identificadores, pues SQL Server THROW y PostgreSQL RAISE usan códigos y envoltorios de driver distintos. Otros errores técnicos no se consideran equivalentes por compartir un mensaje. Se mantienen los errores crudos como evidencia. Este mapeo no cubre equivalencia completa de SQLSTATE, severidad o protocolo de errores de aplicaciones externas.

Los cambios válidos de datos ocurren en tablas de trabajo, restauradas en cada caso. No son cambios a fixtures. Se comprueba también el estado después de errores. Para operaciones transaccionales se usa CALL en autocommit, ya que los procedimientos PostgreSQL tienen reglas distintas de las funciones para control de transacciones.

## Diferencias que rompen migraciones

- `DATEDIFF(month)` cuenta fronteras de calendario, no meses completos; días y años bisiestos requieren casos explícitos.
- `ROUND` debe operar sobre numeric para conservar mitades alejadas de cero. Redondear cada fila y sumar no equivale a redondear la suma.
- `SUM` ignora NULL, pero devuelve NULL sobre cero filas. COUNT(*) tiene otro comportamiento. CONCAT e ISNULL no deben sustituirse sin revisar tipos y NULL.
- SQL Server configura collation case-insensitive. PostgreSQL no aplica esa collation automáticamente. LOWER puede cubrir el conjunto ASCII, pero no garantiza equivalencia general para Unicode, acentos o espacios finales.
- TOP requiere un orden y desempate definido. SQL dinámico requiere parámetros; interpolar cadenas cambia semántica y expone inyección.
- Cursores y temporales pueden reescribirse, pero hay que conservar el punto del redondeo y el orden cuando altera cálculos.
- Transacciones, concurrencia y lecturas NOLOCK no se reducen a igualar una consulta aislada. Las pruebas presentes no prueban equivalencia bajo concurrencia.

## Agentes que se engañan

Declarar "equivalent" sin ejecutar, excluir casos difíciles, aumentar tolerancias, editar datos o hardcodear salidas son atajos que ocultan el fallo. El sistema audita afirmaciones, controla permisos, fija comparación y aplica casos reservados. La evaluación de detección inyecta ataques deliberados; no presenta esos ataques como trampas espontáneamente cometidas por OpenAI. Tampoco interpreta una declaración honesta de limitaciones como trampa.

Antes de firmar una migración exigiría todos los casos de aceptación, revisión de diferencias declaradas, evidencia de efectos transaccionales, pruebas con datos de producción anonimizados y pruebas específicas de concurrencia/collation para el entorno objetivo. Esta prueba demuestra equivalencia finita sobre su benchmark, no una prueba formal para toda entrada posible.

## Adaptación del protocolo de resultados

El contrato público compara una relación tabular, además de errores y estado. SQL Server puede anunciar un conjunto vacío con columnas antes de que un SELECT falle dentro de TRY y CATCH devuelva una fila. El adaptador conserva TODOS los conjuntos crudos en `result_sets`, y solo omite preámbulos vacíos con exactamente las mismas columnas que el resultado final. No descarta filas ni conjuntos con otra forma; esas situaciones abortan la evaluación como contrato no soportado. Esta adaptación del protocolo TDS está fijada antes de la evaluación final y no es una tolerancia numérica ni un cambio solicitado por el agente. Si un consumidor depende de observar ese preámbulo en el protocolo, debe revisarse esa diferencia de interfaz antes de migrar.

La calibración encontró este problema en el procedimiento `safe_ratio`. Con feedback incompleto, el agente trató de imitar una ausencia de filas que era un error del adaptador, y empeoró su traducción. Es evidencia de que un verificador mal implementado también puede inducir un agente a una solución incorrecta. Se corrigió el adaptador, se reforzaron pruebas del original y se repitió el experimento desde cero; las entradas, originales y dinero de referencia se mantuvieron intactos.
