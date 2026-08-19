# Reporte de bug a soporte de Odoo — transacción SQL abortada al ejecutar AI tool que crea registros de Sign

**Tenant:** efficaxba-online.odoo.com (Odoo 19 Online / Enterprise)
**Fecha del incidente:** 18-ago-2026, reproducido de forma consistente entre ~18:09 y ~20:28 GMT
**Usuario afectado:** Alberto Ruiz (uid 2, admin), con grupos "Sign / Administrator" y "Sign / User: Own Templates" confirmados

## Resumen

Una Server Action (`state='code'`, `use_in_ai=True`) usada como herramienta de un agente de IA (`ai.agent` → `ai.topic` → tool) falla SIEMPRE cuando su código crea registros del módulo Firma electrónica (`sign.document`, `sign.item`, `sign.request`) — pero **las mismas operaciones, con los mismos valores y el mismo usuario, funcionan perfectamente vía XML-RPC directo**. El fallo solo ocurre dentro del pipeline del chat del agente de IA.

## Síntoma visible

El usuario del chat ve el diálogo genérico "¡Uy! Se ha producido un error…" con `RPC_ERROR / Odoo Server Error`. No se escribe nada en la base de datos (verificado por RPC después de cada intento).

## Traceback (extracto del diálogo de detalles técnicos)

La excepción final visible es un error *secundario*: la publicación de la respuesta del agente muere porque la transacción ya estaba abortada por un fallo *anterior* dentro de la misma request:

```
File ".../enterprise/19.0/ai/controllers/main.py", line 19, in generate_response
    channel.sudo().ai_agent_id.with_context(...)._generate_response_for_channel(message, channel)
File ".../enterprise/19.0/ai/models/ai_agent.py", line 417, in _generate_response_for_channel
    self._post_ai_response(channel, message)
File ".../enterprise/19.0/ai/models/ai_agent.py", line 501, in _post_ai_response
    channel.sudo().message_post(
...
File ".../addons/mail/models/discuss/discuss_channel.py", line 333, in _compute_member_count
    read_group_res = self.env['discuss.channel.member']._read_group(...)
...
psycopg2.errors.InFailedSqlTransaction: current transaction is aborted,
commands ignored until end of transaction block
```

Es decir: algo falló a nivel SQL durante la ejecución de la herramienta, la transacción quedó abortada, **no se hizo rollback**, y el propio flujo de `_post_ai_response` revienta después al intentar seguir usando el cursor.

## Código de la herramienta (reproducible)

Server Action sobre `documents.document`, invocada como AI tool con params `documento_id` (integer) y `firmantes_json` (string JSON). Secuencia de operaciones del código:

1. `env['sign.template'].create({'name': ...})` (o search de una existente)
2. `env['sign.document'].create({'attachment_id': X, 'template_id': Y})`
3. `env['sign.item'].create({...})` (Signature, page/posX/posY/width/height/alignment)
4. `env['sign.item.role'].search/create`, `env['res.partner'].search/create`
5. `env['sign.request'].create({'reference': ..., 'template_id': ..., 'request_item_ids': [(0,0,{...})]})`

## Evidencia de que el código es correcto

Cada una de esas operaciones, ejecutada individualmente vía XML-RPC (`execute_kw`) con el mismo usuario (uid 2) y exactamente los mismos valores, **funciona sin error** y crea los registros esperados. Verificado el 18-ago-2026:

- `sign.document.create({'attachment_id': 2887, 'template_id': 2})` → id 4 ✔
- `sign.item.create({...})` sobre ese document → id 5 y luego id 7 ✔ (creados y limpiados)
- El adjunto es un PDF válido generado con reportlab (`num_pages` computa 1 correctamente)

## Efectos colaterales observados (escrituras parciales pese al error)

En intentos previos, la transacción fallida dejó registros **parciales** persistidos pese a que el chat reportó error y "no se creó la solicitud":

- Un `sign.template` (id 2) creado sin su `sign.document` correspondiente
- Dos `sign.request` (ids 1 y 2, estado 'sent') colgando de esa plantilla vacía — tuvimos que cancelarlos/eliminarlos manualmente para desbloquear la regla `ir.rule` `[('template_id.has_sign_requests','=',False)]` de `sign.item`

Esto sugiere que dentro del pipeline del agente hay commits/savepoints parciales que persisten estado intermedio aun cuando la request termina en error.

## Qué pedimos

1. Revisar los logs del servidor de efficaxba-online.odoo.com alrededor de 2026-08-18 20:23:34 GMT y 20:28:10 GMT para identificar la excepción SQL *original* (la que aborta la transacción antes del `InFailedSqlTransaction`).
2. Confirmar si existe una incompatibilidad conocida entre AI tools (Server Actions con `use_in_ai`) y la creación de registros de `sign.*` dentro de la misma transacción del chat.
3. Si es un bug del módulo `ai` de Enterprise, registrarlo para corrección.

## Datos de contacto

Alberto Ruiz — alberto.ruiz@efficaxba.com — Efficax Solutions SA
