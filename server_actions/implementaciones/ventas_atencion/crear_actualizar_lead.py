"""Server Action: ventas_atencion / crear_actualizar_lead

PRIMERA HERRAMIENTA CON LÓGICA REAL PROBADA EN PRODUCCIÓN.
Instalada y verificada en el Odoo de Efficax (tenant 0) el 15-ago-2026:

  1. Llave vigente  -> el agente creó el lead 1004 (Rosa Quispe) y el registro
     existe de verdad en `crm.lead`, con su email y su descripción.
  2. Llave con 3 días de antigüedad (> 48h) -> la herramienta se negó a
     ejecutar, el agente le explicó al usuario que el servicio estaba
     suspendido, y NO se creó ningún registro (verificado: 0 leads).

El contenido de CODIGO es exactamente lo que va en el campo `code` del
`ir.actions.server`. No es un módulo Python ejecutable acá: es el cuerpo que
corre dentro del sandbox de Odoo, donde `env`, `ai`, `datetime` y `UserError`
ya existen, y donde cada parámetro del esquema llega como variable suelta.

Restricciones del sandbox que condicionan este código (verificadas, no
supuestas): no existe `type`, `datetime` es un wrap_module (hay que usar
`datetime.datetime.now()`), y el esquema no admite `format`/`default`
(por eso la validación de "email o teléfono" se hace acá abajo y no en el
esquema — ver esquemas_odoo.py).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
nombre = (nombre_contacto or '').strip()
tel = (telefono or '').strip()
mail = (email or '').strip()
detalle = (interes or '').strip()
canal = (origen or 'livechat')

if not nombre or not detalle:
    ai['result'] = {'ok': False, 'mensaje': 'Falta el nombre del contacto o el interes.', 'datos': {}}
elif not tel and not mail:
    # La regla "telefono O email" vive acá porque el esquema de Odoo no
    # soporta anyOf (ver esquemas_odoo.py).
    ai['result'] = {'ok': False, 'mensaje': 'Necesito telefono o email para registrar el lead.', 'datos': {}}
else:
    Lead = env['crm.lead']
    existente = Lead.browse()
    if mail:
        existente = Lead.search([('email_from', '=ilike', mail)], limit=1)
    if not existente and tel:
        existente = Lead.search([('phone', '=', tel)], limit=1)
    if existente:
        # No duplicar: se acumula el nuevo interes en el historial.
        nuevo_desc = (existente.description or '') + '\\n[' + canal + '] ' + detalle
        existente.write({'description': nuevo_desc})
        lead = existente
        accion = 'actualizado'
    else:
        valores = {'contact_name': nombre, 'name': detalle[:120], 'description': '[' + canal + '] ' + detalle}
        if tel:
            valores['phone'] = tel
        if mail:
            valores['email_from'] = mail
        lead = Lead.create(valores)
        accion = 'creado'
    ai['result'] = {
        'ok': True,
        'mensaje': 'Lead ' + accion + ' correctamente.',
        'datos': {'lead_id': lead.id, 'nombre': lead.contact_name or nombre, 'accion': accion},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
