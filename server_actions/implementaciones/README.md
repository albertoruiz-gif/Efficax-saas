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

Nota sobre el API key de RPC: venció una vez (16-ago, ~19:00) a mitad de
sesión — se regeneró el 17-ago. Ver el requisito de diseño anotado en
`booster/README.md` (pedir todos los accesos una sola vez en Fase 3, para
no reproducirle esta misma fricción al cliente real).

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
| ventas_atencion | crear_cotizacion | 16-ago-2026, tenant 0 (cotización S00043 en borrador verificada, SKU inexistente → fallo explícito sin cotización parcial, + kill-switch) |
| mentor | resumen_negocio | 17-ago-2026, tenant 0 (ventas/facturado/leads/entregas verificados exacto contra RPC directo, comparación contra período anterior, + kill-switch) |
| mentor | estado_agentes | 17-ago-2026, tenant 0 (lista los 8 agentes reales con última actividad real desde `mail.message`, + kill-switch) |
| mentor | crear_actividad | 17-ago-2026, tenant 0 (tarea creada y verificada en `mail.activity`, aprobacion=confirmar respetada, + kill-switch) |
| mentor | registrar_decision | 17-ago-2026, tenant 0 (app Documentos instalada por decisión explícita de Alberto — `button_immediate_install` sobre `ir.module.module`; carpeta "05_decisiones" creada como `documents.document` tipo folder; decisión registrada con contexto verificada exacta contra `ir.attachment.raw` incluyendo la línea de contexto agregada por el agente, + kill-switch: intento de registrar una segunda decisión con la llave vencida devolvió "Servicio suspendido — contacta a Efficax", conteo de documentos en la carpeta se mantuvo en 1) |
| dashboard_kpis | calcular_kpi | 17-ago-2026, tenant 0 (5 de 5 KPIs verificados exacto contra RPC directo: ventas_totales, ticket_promedio, tasa_conversion, valor_inventario, y margen_bruto tras corregirlo — ver bug abajo; + kill-switch) |
| dashboard_kpis | revision_mensual | 17-ago-2026, tenant 0 (comparación 2025-05 vs 2025-04 correcta tras el mismo fix de margen_bruto, propuesta de candidatos a revisión con el umbral 20% verificada, + kill-switch) |
| dashboard_kpis | construir_dashboard | 17-ago-2026, tenant 0 (dashboard gerencial creado y verificado — ver bug de `dashboard_group_id` abajo, contenido real o-spreadsheet sigue como placeholder honesto, + kill-switch) |
| dashboard_kpis | alerta_umbral | 17-ago-2026, tenant 0 (reescrita de `base.automation` a `ir.cron` — ver bug abajo; alerta creada, disparada a mano con `ir.cron.method_direct_trigger()`, generó la `mail.activity` real con el valor correcto del KPI 47316.85 < 1,000,000, + kill-switch) |

**Ventas & Atención 24/7 completa: 9 de 9.** Mentor: 4 de 6 probadas. dashboard_kpis: 4 de 4 probadas.

**Bug real encontrado y corregido en `margen_bruto` (17-ago-2026):** el código
original usaba `env['sale.report'].search([('order_id', 'in', ...)])` y
`.mapped('margin')` — ninguno de los dos campos existe en este tenant
(`sale.report` no tiene `order_id` ni `margin`; confirmado con `fields_get`,
no asumido — el módulo `sale_margin` no está instalado). Corregido en
`calcular_kpi.py` y `revision_mensual.py` calculando el margen a mano desde
`sale.order.line`: `price_subtotal` menos `product_uom_qty * product_id.standard_price`.
Verificado en vivo contra RPC directo (95913.0 de ventas, 0.0 de costo porque
los productos de este tenant no tienen `standard_price` configurado — dato
real, no bug de la herramienta — margen 100%).

**Bug real en `construir_dashboard` (17-ago-2026):** `spreadsheet.dashboard`
tiene `dashboard_group_id` como campo **obligatorio** (`fields_get`,
`required: True`) — la primera versión del código no lo incluía y hubiera
fallado el `create()`. Corregido buscando/creando un grupo propio
"Efficax — KPIs" (no se reutiliza un grupo estándar de Odoo como
Sales/Finance). El contenido real del dashboard (formato o-spreadsheet,
~56 KB de JSON en uno existente, revisado en vivo) sigue como placeholder
honesto — confirmado que reconstruirlo a mano no es viable en el tiempo
de esta sesión.

**Bug real en `alerta_umbral` (17-ago-2026) — el enfoque original estaba
mal elegido, no solo mal tipeado:** la primera versión usaba
`base.automation` con `trigger='on_time'`, que evalúa un campo Fecha/
Datetime PROPIO DE CADA REGISTRO (ej. actividades que vencen X días
después de su `date_deadline`) — no sirve para "revisa este KPI de
negocio cada N días", que no depende de ningún campo fecha de un
registro puntual. Reescrita para usar `ir.cron` (Acciones Planificadas),
el mecanismo correcto de Odoo para jobs periódicos con `code` propio
(también hereda de `ir.actions.server`, mismo patrón). De paso se
completó la lógica real de cálculo de KPI + notificación (antes era un
placeholder comentado) y se probó disparando el cron a mano con
`ir.cron.method_direct_trigger()` — no hace falta esperar al `nextcall`
real para probarlo en vivo. El cron de prueba se dejó **desactivado**
(`active=False`) después de confirmar que funciona, para no generarle a
Alberto una tarea diaria real con un umbral que era solo de prueba.

Código listo, pendiente de prueba en vivo
------------------------------------------

**dashboard_kpis completo: 4 de 4 probadas en vivo.** No queda ninguna
herramienta de este agente en la tabla de "código listo, pendiente".

`calcular_kpi`/`revision_mensual` comparten un catálogo fijo de 5 KPIs
(ventas_totales, ticket_promedio, tasa_conversion, margen_bruto,
valor_inventario) — el "contrato de KPIs" real que Booster define en su
Fase 4 todavía no existe, así que no se inventa; cuando exista, este
catálogo fijo se reemplaza por esa fuente.

Quedan 2 de las 6 de Mentor sin tocar: `actualizar_perfil_acceso` y
`abrir_ticket_efficax` — ambas `ejecuta: "servidor_control"`, no Server
Action. Su lógica de decisión (validación + armado del payload, sin red)
ya está en `servidor_control/app/mentor/` con tests propios — ver el
README de `servidor_control/` para el detalle de qué falta para que sean
invocables de verdad (integración XML-RPC + registro de tenants, ninguno
existe todavía).

Las otras 39 herramientas del catálogo (de 58 en total: 15 probadas en
vivo + 2 con código listo pendiente de prueba + 2 con lógica pura de
servidor_control ya testeada) siguen como esqueletos. Ya no hay
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
- `registrar_decision` necesitaba la app **Documentos** (`documents.document`),
  que estaba `state='uninstalled'` en este tenant. Se instaló con
  `ir.module.module.button_immediate_install` por decisión explícita de
  Alberto (17-ago-2026) — confirmado el schema real con `fields_get` antes
  de dar por buenos los nombres de campo que ya estaban en el código
  (`type`, `folder_id`, `attachment_id`, `name`: coincidieron).
- Este tenant tiene productos con `company_id` fijado a una compañía
  específica (ej. los SKU `HSK-*` pertenecen a "Haskell_Distribuidor").
  Un `sale.order` creado sin pasar `company_id` toma la compañía del
  usuario actual ("Efficax Solutions SA") — si se le agregan líneas con
  productos de otra compañía, Odoo rechaza la creación con un error claro
  ("no company crossover is allowed"), sin dejar nada a medias. No es un
  bug de las herramientas: es una regla real de este tenant que cualquier
  prueba en vivo con productos `HSK-*` tiene que tener en cuenta (usar un
  cliente/producto de la misma compañía, o un producto sin `company_id`).
