# Diseño validado: migración con evidencia

Crear un laboratorio local de SQL Server 2022 y PostgreSQL 16, con veinte procedimientos propios sobre pólizas/primas/pagos porque solo se recibió la guía y una clave. Exponer CLI y web, seleccionadas para reproducir resultados en CI y revisar evidencia visualmente.

Usar Python 3.12, Responses API y salidas estructuradas. Mantener un modelo idéntico entre técnicas. Compartir el primer intento; directa se detiene y agente dispone de hasta dos correcciones con feedback ejecutado. Límite autorizado: 500.000 tokens globales, incluyendo calibración, prompts y consultas. El driver SQL Server final es pymssql para evitar una instalación ODBC adicional.

Proteger fuentes, datos y casos por hashes y permisos. Restaurar tablas de trabajo antes de cada caso. Comparar una relación tabular, errores de negocio declarados y efectos persistentes; dinero exacto, nulos, duplicados y orden contractual. Registrar todos los conjuntos TDS y adaptar solamente preámbulos vacíos de igual forma. Abortar ante resultados múltiples con filas o columnas diferentes. Congelar este contrato antes del experimento final.

Seis casos de corrección y dos reservados por procedimiento; nunca revelar reservados como feedback. Separar éxito de instalación, ejecución y equivalencia. Declaraciones semánticas no convierten diferencias en éxito. Detectar solicitudes prohibidas, SQL fuera de contrato, alteración de fixtures, violaciones de permisos y afirmaciones de pruebas inventadas.

Versionar prompts y evaluar rechazo exacto fuera de dominio, trampas, honestidad y semántica no traducible con OpenAI real. Complementar con ataques controlados al verificador. Conservar resultados fallidos y calibraciones. Informes por procedimiento/técnica y trazas completas alimentan CLI, web y consultas explicativas.

Entrega: código y configuración reproducible, manifiesto, README, C4, resultados y hallazgos. Git privado con acceso de jaimeguzman y Fit-Latam al contar con autenticación del dueño; nunca publicar la guía ni .env.
