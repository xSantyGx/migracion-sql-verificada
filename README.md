# FactorIT · Migration Lab

Sistema funcional para migrar veinte procedimientos T-SQL a PostgreSQL y comparar **traducción directa** con **agente que verifica y corrige**. La equivalencia la decide un verificador determinista ejecutando ambos motores, incluyendo efectos sobre datos. OpenAI propone código y explica evidencia.

> Se recibieron únicamente la guía y la clave. El Compose, los veinte procedimientos y el conjunto de pólizas/primas/pagos fueron creados para este desafío. No se presentan como materiales entregados por FactorIT. El repositorio debe permanecer **privado**.

## Inicio rápido con Docker

Requisitos: Docker Engine/Desktop activo, Compose, equipo x86-64, al menos 4 GB de RAM disponibles para Docker y 8 GB libres **en el disco interno de Docker**. SQL Server usa la edición Developer para desarrollo/pruebas. Los motores siempre son locales; OpenAI es el único servicio externo necesario para generar traducciones.

```bash
# Conservar tu .env si ya existe; no sobrescribir la clave.
[ -f .env ] || cp .env.example .env
# Editar .env y establecer OPENAI_API_KEY.
mkdir -p artifacts
# Linux: permite escribir artifacts con el usuario del equipo.
export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)
docker compose up -d --build
```

La inicialización espera ambos motores, instala originales y comprueba igualdad de datos. Abre **http://localhost:8000**. Antes de evaluar verás una pantalla de inicio; si hay evidencia incluida en `reports/`, podrás consultarla inmediatamente.

```bash
docker compose exec app migrator doctor
docker compose exec app migrator eval-prompts
docker compose exec app migrator benchmark --run-id entrega
```

El benchmark registra una primera traducción por procedimiento y permite hasta dos correcciones. Tiene un presupuesto global conservador de **500.000 tokens**. Puede tardar varios minutos. La web lee los resultados guardados: recarga para ver avances. No se iniciará consumo de API por abrir una página.

## Reproducir evidencia sin consumir OpenAI

```bash
# Reejecutar todas las traducciones finales del agente.
# Devuelve exit 1 si alguna no es equivalente, incompleta o tiene trampa detectada.
docker compose exec app migrator verify
# Comparar también el primer intento:
docker compose exec app migrator verify --technique direct
# Consultar/exportar la tabla completa:
docker compose exec app migrator report
# Verificar solamente un procedimiento:
docker compose exec app migrator verify --procedure 08
# Ataques controlados del detector, sin OpenAI:
docker compose exec app migrator eval-prompts --detection-only
```

Los estados son: `equivalent`, `different` (instala pero difiere), `compile_error`, `runtime_error`, `cheating_detected` e `incomplete`. Las diferencias semánticas declaradas aparecen en otra columna y requieren revisión aunque los casos coincidan. Un benchmark con traducciones fallidas sigue siendo una evaluación válida: el comando `benchmark` termina correctamente si completó la comparación; `verify` exige equivalencia.

## Consultas con evidencia

Usa el formulario de la web o:

```bash
docker compose exec app migrator ask '¿Qué procedimientos quedaron equivalentes y cuáles declaran diferencias?'
```

Las respuestas enlazan a la evidencia por procedimiento. Una consulta fuera del dominio responde exactamente:

```text
No estoy habilitado para responder ese tipo de preguntas.
```

Las consultas también consumen el presupuesto global. La web y la CLI comparten el ledger y su lock.

## Desarrollo local y pruebas

El adaptador SQL Server usa `pymssql`/FreeTDS, sin instalar ODBC en el host.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
pip install --no-deps -e .
docker compose up -d --wait sqlserver postgres
migrator init
ruff check migrator tests scripts
pytest -q -m 'not integration'
RUN_DB_TESTS=1 pytest -q -m integration
migrator eval-prompts --detection-only
migrator serve
```

Las pruebas de integración verifican que los 160 casos ejecutan en SQL Server, restauración entre pruebas, una traducción correcta y un ataque dentro del cuerpo PL/pgSQL. Las pruebas unitarias cubren dinero exacto, duplicados, orden, nulos, efectos persistentes, integridad, presupuesto y límites de entrada web. No requieren una clave real. GitHub Actions reejecuta la evidencia sin OpenAI; el workflow manual `live_openai` consume API usando el secreto `OPENAI_API_KEY`.

## Configuración, recuperación y evidencia

`.env.example` enumera las variables. Solo `OPENAI_API_KEY` es obligatorio para traducciones. Los valores locales predeterminados de contraseñas sirven para este laboratorio. Nunca usar estas credenciales para producción. La clave no entra en imágenes, Git, prompts ni informes.

- `OPENAI_MODEL=gpt-5-mini`: configurable; se conserva igual en las dos técnicas de una ejecución.
- `TOKEN_BUDGET=500000`: máximo para el ledger compartido, incluye consultas y evaluaciones.
- `MAX_ATTEMPTS=3`: incluye el primer intento.
- `MAX_OUTPUT_TOKENS=8192`: reserva por llamada, incluye razonamiento y salida.
- Puertos host: SQL Server `14330`, PostgreSQL `54330`, web `8000`. Las URLs dentro de Compose usan nombres de servicio.

`artifacts/usage.json` es el registro de gasto. Antes de llamar a OpenAI se cuenta la entrada y se reserva entrada + salida máxima. Si una respuesta entrega uso real, se libera el remanente. Si una llamada termina con resultado de transporte desconocido, se conserva su reserva: evita volver a gastar tokens potencialmente cobrados. No se reintenta automáticamente una llamada de generación. No borres el ledger durante una evaluación para eludir el presupuesto. Aumentar el límite en `.env` es una decisión explícita del operador.

```bash
# Reanudar el mismo ID: conserva traducciones ya recibidas y verificaciones terminadas.
docker compose exec app migrator benchmark --run-id entrega
# Exportar una ejecución concreta:
docker compose exec app migrator report --run-id entrega
```

Cada ejecución genera `run.json`, `results.csv` y `results.md`. Contiene código por intento, evidencia por caso, estados, diferencias semánticas, llamadas, tokens, tiempos, hashes y motivos de parada. La primera llamada compartida se cuenta en cada técnica para comparar coste lógico; el ledger cuenta el gasto real una sola vez. Los archivos de evidencia curados para entregar viven en `reports/` y sí se versionan; `artifacts/` es trabajo local excluido de Git.

Cambiar contratos, fuentes, código o prompts impide reanudar una ejecución anterior. Para comparar el nuevo sistema inicia otro ID y conserva la evidencia anterior. Los casos reservados nunca se envían como feedback de corrección.

## Arquitectura y hallazgos

- [Arquitectura C4 y límites de confianza](docs/architecture.md).
- [Metodología, semántica SQL y criterios para firmar una migración](docs/methodology.md).
- [Hallazgos y resultados de la ejecución real](docs/findings.md).
- [Prompts versionados](migrator/prompts/).
- [Procedimientos y contratos de referencia](benchmark/).

El dataset tiene veinte procedimientos con consultas, cálculos, temporales, cursores, SQL dinámico, validación y transacciones. Cada uno tiene seis casos de corrección y dos reservados. Equivalencia sobre estos casos no demuestra equivalencia para toda entrada, para concurrencia, ni para collations arbitrarias. Esos límites forman parte de los hallazgos, no se ocultan mediante tolerancias.

## Diagnóstico y cierre

Si Docker no responde, inicia Docker Desktop/Engine y ejecuta `docker info`. Si el host tiene espacio pero aparece `no space left on device`, comprueba el disco de la VM de Docker; no elimines volúmenes de otros proyectos. Si SQL Server no inicia, revisa `docker compose logs sqlserver`; necesita arquitectura x86-64 y suficiente memoria. Los errores de API quedan registrados como incompletos y nunca como equivalentes.

```bash
# Detener conservando datos:
docker compose down
# Reinicializar exclusivamente este laboratorio (elimina sus dos volúmenes):
docker compose down -v
docker compose up -d --build
```

## Entrega privada en GitHub

Este proyecto ya está en [`xSantyGx/migracion-sql-verificada`](https://github.com/xSantyGx/migracion-sql-verificada). No ejecutes `gh repo create`: crearía un repositorio duplicado. Mantén este repositorio privado y comprueba que `.env` no esté incluido.

La guía de entrega solicita compartirlo con `jaimeguzman` y `Fit-Latam`. **Importante:** al ser un repositorio privado de una cuenta personal, GitHub solo permite dar a sus colaboradores acceso de lectura y escritura; no hay un rol de solo lectura. Si necesitas limitar el acceso a lectura, el repositorio debe pertenecer a una organización que permita asignar el rol `Read`.

Si aceptas darles acceso de lectura y escritura, y aún no los has invitado, puedes ejecutar con GitHub CLI autenticado:

```bash
gh api --method PUT repos/xSantyGx/migracion-sql-verificada/collaborators/jaimeguzman
gh api --method PUT repos/xSantyGx/migracion-sql-verificada/collaborators/Fit-Latam
gh repo view xSantyGx/migracion-sql-verificada --json visibility,url
```

Comprueba que la visibilidad sea `PRIVATE` y que las invitaciones estén pendientes o aceptadas. No hagas público el repositorio después de la entrega. La clave de OpenAI no permite administrar permisos de GitHub.

La evidencia incluida conserva un caso no equivalente (`dynamic_filter`). Por diseño, `migrator verify` devuelve **1** al verificar el conjunto completo; `migrator verify --procedure 15` devuelve **0** para el cursor corregido. CI además comprueba que los diecinueve procedimientos previamente equivalentes no regresen, sin aprobar el caso conocido como diferente.
