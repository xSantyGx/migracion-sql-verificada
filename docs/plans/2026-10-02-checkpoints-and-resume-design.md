# Protección de checkpoints y correcciones interrumpidas

## Pérdida de evidencia al exportar

`report` leía `run.json` y lo reescribía mediante `export` sin adquirir el lock
del benchmark. Una propuesta recibida después de esa lectura podía perderse
cuando la exportación guardaba su snapshot anterior. Reanudar podía entonces
volver a generar una traducción ya pagada. La exportación final de la CLI también
ocurría después de liberar el lock del benchmark.

Se protege la lectura y exportación de `report` con el lock compartido. Si existe
una evaluación activa, el comando devuelve un error claro sin escribir archivos.
La exportación final del benchmark se realiza dentro de su lock, antes de retornar
a la CLI. La web continúa leyendo checkpoints atómicos durante la evaluación.
Usar un lock exclusivo de exportaciones no protegería frente al escritor del
benchmark; omitir solamente el JSON dejaría los informes derivados expuestos.

## Falsa finalización después de un fallo de API

Cuando una corrección fallaba por transporte o presupuesto, el agente conservaba
el estado de la última traducción y la ejecución se marcaba `completed`. La CLI
devolvía exit 0 aunque quedaran intentos pendientes. Al reanudar, el motivo del
fallo podía permanecer incluso después de obtener una traducción equivalente.

Una corrección interrumpida produce `incomplete`, conserva la propuesta y su
verificación e incluye el error en `api_failures`. La reanudación marca la ejecución
como `running`, elimina la fecha de cierre anterior y recalcula el motivo de parada
al terminar. Pasar los casos de entrenamiento o agotar los intentos sigue siendo
una evaluación completada, aunque la traducción no resulte equivalente.

## Validación

Pruebas deterministas reproducen la sobrescritura de un checkpoint y el exit 0
incorrecto antes de corregirlos. Cubren fallo de transporte, límite de presupuesto,
reanudación sin repetir la llamada inicial, historial y motivos de parada, casos
reservados y agotamiento de intentos. Una prueba de integración ejecuta traducciones
en SQL Server y PostgreSQL y simula únicamente la interrupción de la API.

Se ejecutan la suite, Ruff y comprobaciones de la aplicación reconstruida en Docker.
No se generan traducciones con OpenAI ni se modifican los materiales de referencia.
