# Correcciones de precisión y referencias de evidencia

Objetivo: corregir dos fallos reproducibles sin generar traducciones ni consumir API.

## Comparación decimal exacta

`Decimal.normalize()` aplica la precisión del contexto de Python y puede redondear
un valor PostgreSQL antes de compararlo con SQL Server. Por ejemplo, `1000` y
`1000.0000000000000000000000000001` se consideraban iguales.

Se formatea directamente el decimal y se eliminan únicamente los ceros finales
de la fracción. Esto conserva todos los dígitos, mantiene la igualdad entre `1`,
`1.00` y `1E+0`, y unifica los ceros con signo. Aumentar la precisión global o
elegir otra precisión fija seguiría imponiendo un límite innecesario.

Las pruebas cubren diferencias después del dígito 28, enteros largos, un contexto
de precisión reducida y una traducción ejecutada en ambos motores que introduce
una diferencia decimal diminuta.

## Referencias consistentes en consultas

`POST /api/ask` cargaba el informe dos veces. Sin `run_id`, una ejecución nueva
podía aparecer mientras se generaba la respuesta y cambiar el destino de los
enlaces de evidencia.

Se carga el informe una sola vez y se usa el mismo objeto para responder y crear
los enlaces. No requiere bloquear el benchmark ni alterar el formato de la API.
Una prueba simula la aparición de una ejecución nueva durante la consulta y
comprueba que los enlaces conservan el identificador del informe original.

## Validación y ejecución

Ejecutar pruebas unitarias, integración con los motores existentes, Ruff y la
verificación de las traducciones guardadas. Reconstruir la aplicación Docker con
las correcciones y dejarla disponible en `http://localhost:8000`. Conservar los
volúmenes y la evidencia existente. El caso conocido `dynamic_filter` debe seguir
informándose como diferente.
