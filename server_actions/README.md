# Server Actions — las 49 herramientas de los agentes

La spec fuente de verdad es `../../Agentes_SAAS/agentes_v2/herramientas/herramientas_esquemas.json`.
`generador.py` produce el esqueleto de cada herramienta (con guarda de llave
obligatoria); la implementación de cada una se hace SOBRE el esqueleto generado
y se registra aquí por agente. Si el catálogo cambia, se regenera — nunca se
deja divergir el código de la spec.
