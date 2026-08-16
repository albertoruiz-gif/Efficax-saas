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
| ventas_atencion | crear_ticket | 15-ago-2026, tenant 0 (ticket de soporte, reclamo con Libro de Reclamaciones + recordatorio de plazo legal agendado, + kill-switch) |
| ventas_atencion | derivar_humano | 15/16-ago-2026, tenant 0 (con lead_id: nota+actividad en el lead; sin lead_id: nota+actividad en el partner del usuario real; + kill-switch) |
| ventas_atencion | resumen_conversacion | 16-ago-2026, tenant 0 (chatter del lead 1004 verificado, lead inexistente → mensaje correcto, + kill-switch) |
| ventas_atencion | nota_vendedor | 16-ago-2026, tenant 0 (nota interna + actividad de seguimiento con fecha verificadas, cliente inexistente → mensaje correcto, aprobacion=confirmar respetada por el agente, + kill-switch) |
| ventas_atencion | agendar_reunion | 16-ago-2026, tenant 0 (evento_directo con hora Lima→UTC verificada en el registro real, enlace_citas sin tipo configurado → mensaje honesto, + kill-switch) |

Las otras 50 herramientas del catálogo siguen como esqueletos. Ya no hay
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
- Para crear un `mail.activity` sobre un registro, usar el método del mixin
  `registro.activity_schedule(xmlid, ...)` (ej. `'mail.mail_activity_data_todo'`)
  en vez de buscar `ir.model`/`mail.activity.type` a mano y hacer
  `env['mail.activity'].create(...)`: ese camino manual falló EN SILENCIO
  en `crear_ticket.py` (el ticket se creaba bien, pero la actividad nunca
  aparecía y no había ningún error visible en el chat — el usuario real que
  ejecuta la herramienta probablemente no tiene acceso de lectura a
  `ir.model`, que es un modelo técnico oculto por defecto). Con
  `activity_schedule` (que resuelve el tipo vía `env.ref`, de uso general)
  funcionó a la primera.

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
- Al escribir en el cuadro de chat por automatización de navegador: una vez
  que la conversación acumula historial, el cuadro de texto se corre de
  posición y clickear por coordenadas fijas puede fallar en silencio (el
  texto no se escribe donde se cree). Más confiable: leer la página
  (`read_page`, filtro `interactive`) y clickear por `ref` del textbox, no
  por coordenadas.
- `except ValueError:` (o cualquier otra clase de excepción nombrada:
  `TypeError`, `KeyError`, etc.) revienta con `NameError` real en el
  sandbox de Odoo — esas clases no están expuestas ahí, ni siquiera para
  capturarlas. Usar `except:` desnudo. Cubierto ahora por un test
  automático (`test_sin_clases_de_excepcion_no_disponibles`) que revisa
  toda implementación real.
- Cualquier campo `Datetime` con hora (no solo fecha) que reciba un valor
  en hora local (ej. "15:00 hora Lima") hay que convertirlo a UTC A MANO
  antes de guardarlo: `create()` no hace conversión de zona horaria por sí
  solo. Perú es UTC-5 fijo (sin horario de verano) — confirmado en vivo en
  `agendar_reunion.py`: sin el offset, un evento pedido a las 15:00 Lima
  quedaba guardado (y mostrado) a las 10:00 Lima, 5 horas antes.
