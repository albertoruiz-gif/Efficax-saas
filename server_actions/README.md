# Server Actions — las 58 herramientas de los agentes

La spec fuente de verdad es un catálogo JSON que vive **fuera de este repo**,
en `Agentes_SAAS/agentes_v2/herramientas/herramientas_esquemas.json` dentro
de `EFFICAX_IA` (documentación de agentes en markdown). Es una dependencia
cross-repo real, no un descuido — `generador.py` la ubica con una ruta
relativa por defecto (`CATALOGO_DEFAULT`), sobreescribible con la variable
de entorno `EFFICAX_CATALOGO`. **Pendiente de decisión con Alberto:** si
conviene mover el catálogo (o todo `agentes_v2/`) a vivir dentro de este
repo, para que la spec y el código que la implementa queden en el mismo
árbol de control de versiones — hoy están separados por un genuino salto de
carpetas (`Desktop/Efficax-saas` vs `Desktop/Efficax 2026 - 2027/EFFICAX_IA`).

`generador.py` produce, por herramienta:

- **`ejecuta: "server_action"`** → un `.json` con el payload completo y
  listo para crear/actualizar un `ir.actions.server` en Odoo 19 como
  herramienta de IA (`name`, `modelo_tecnico`, `state`, `code` con la
  guarda embebida, `use_in_ai`, `ai_tool_description`, `ai_tool_schema`).
  Mapeo de campos validado en vivo en el Odoo de Efficax el 15-ago-2026
  (ver receta 7 de `01-booster-implementador.md`).
- **`ejecuta: "servidor_control"`** → un esqueleto `.py` (no es un Server
  Action de Odoo — es un endpoint a implementar en `servidor_control/app/`).

La implementación real de cada `TODO` se hace sobre el artefacto generado.
Si el catálogo cambia, se regenera — nunca se deja divergir el código de
la spec.

## Deuda técnica conocida

Las 3 herramientas de Hasky ya en producción (company_id=2, misma base que
Efficax) fueron construidas antes de esta convención: usan `env.sudo()` y no
tienen guarda de licencia. No pasan por este generador. Quedan marcadas para
reemplazarse cuando se instale la versión endurecida.
