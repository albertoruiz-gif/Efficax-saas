Implementaciones reales
=======================

Acá vive el cuerpo Python REAL de cada herramienta, a diferencia de
`generadas/`, que sólo produce esqueletos con `TODO` a partir del catálogo.

Regla: una herramienta sólo se considera implementada cuando fue instalada y
probada EN VIVO en un Odoo real — con la llave vigente (camino feliz) y con
la llave vencida (kill-switch). Mientras no tenga esa doble prueba, no entra
acá.

Estado
------

| Agente | Herramienta | Probada en vivo |
|---|---|---|
| ventas_atencion | crear_actualizar_lead | 15-ago-2026, tenant 0 (crea/actualiza + kill-switch) |
| ventas_atencion | consulta_precio_stock | 15-ago-2026, tenant 0 (precio+stock exacto, ambiguo con 2 candidatos + kill-switch) |
| ventas_atencion | estado_pedido | 15-ago-2026, tenant 0 (verificado ok, verificación incorrecta → mensaje genérico sin revelar el pedido, + kill-switch) |

Las otras 55 herramientas del catálogo siguen como esqueletos. Ya no hay
incógnita de arquitectura: el patrón agente → tema → Server Action, la
guarda de llave, el esquema saneado y el ciclo de aprobación están
verificados de punta a punta. Lo que falta es escribir la lógica de negocio
de cada una y pasarle la misma doble prueba.

Contexto imprescindible antes de escribir una nueva
---------------------------------------------------

- `guarda_llave.py` — la guarda va SIEMPRE primero; ojo con
  `datetime.datetime.now()` (no `datetime.now()`).
- `esquemas_odoo.py` — qué acepta Odoo en `ai_tool_schema` y en qué se
  traduce lo que no acepta. Los nombres de las variables que recibe el
  código son los del esquema SANEADO (ej. `periodo_desde`, no `periodo`;
  `lineas_json`, no `lineas`).
- Nunca `sudo()` fuera de la guarda: la herramienta corre con los permisos
  reales de quien le habla al agente.
- `res.partner` en este tenant **no tiene campo `mobile`** (solo `phone`,
  `phone_sanitized`, `email`, `email_normalized` — verificado con
  `fields_get`, no asumido). Usar `partner.mobile` revienta con un error
  técnico genérico en el chat (Odoo no expone el traceback real al agente
  de IA) — detectado y corregido en `estado_pedido.py`. Antes de asumir que
  un campo existe en un modelo estándar, verificar con `fields_get`.

Cómo se prueba en vivo (patrón establecido 15-ago-2026)
--------------------------------------------------------

- `scripts/booster_rpc.py` — helper RPC reusable: instala/actualiza el
  `ir.actions.server` desde el catálogo + la implementación real, crea/
  ajusta un tema de prueba, y prende/apaga la licencia para el kill-switch.
  Lee credenciales de `scripts/credenciales_booster.env` (gitignored).
- Las herramientas nuevas se cablean a un tema en el agente **"Mentor
  Efficax (piloto)"** (tema "Ventas — Piloto herramientas nuevas"), nunca
  directo al agente de cara al cliente ("Hasky") — así una herramienta a
  medio probar no puede responderle a un visitante real.
- La conversación de prueba se hace por el chat del agente en el backend de
  Odoo (Ajustes > IA > Agentes > abrir el agente), no llamando `run()` por
  RPC: Odoo inyecta las variables del esquema como parte del pipeline de
  tool-calling de la IA, no como contexto de `ir.actions.server.run()`
  (confirmado con un `NameError` al intentarlo directo).
