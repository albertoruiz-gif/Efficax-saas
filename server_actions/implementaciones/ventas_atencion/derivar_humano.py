"""Server Action: ventas_atencion / derivar_humano

Quinta herramienta con lógica real. Notifica al responsable humano y
registra el contexto — "Registra el contexto en el lead" (descripción del
catálogo), pero `lead_id` es OPCIONAL en el esquema (no está en
`required`), así que hay dos caminos reales:

- Con `lead_id`: se postea el resumen en el chatter del lead y se agenda
  un `mail.activity` de seguimiento urgente para el vendedor asignado
  (`lead.user_id`) o, si el lead no tiene vendedor asignado, para quien
  esté hablando con el agente (`env.user`).
- Sin `lead_id` (puede pasar: el cliente pide un humano antes de que se
  haya registrado ningún lead): no existe ningún registro de negocio al
  cual "registrar el contexto", y `mail.activity` en Odoo EXIGE un
  res_model/res_id — no se puede crear una actividad flotante sin dueño.
  Se usa como ancla el `res.partner` de quien está operando la
  conversación (`env.user.partner_id`, que todo usuario tiene y que sí
  soporta chatter/actividades) — es una decisión de diseño real, no un
  mapeo obvio del catálogo, documentada acá por eso.

`activity_schedule()` en vez de `mail.activity.create()` a mano — ver la
lección de `crear_ticket.py` (fallaba en silencio por permisos en
`ir.model`).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
MOTIVOS_TEXTO = {
    'cliente_lo_pide': 'El cliente pidio hablar con una persona',
    'monto_supera_umbral': 'El monto de la operacion supera el umbral automatico',
    'descuento_supera_umbral': 'El descuento pedido supera el umbral automatico',
    'producto_requiere_humano': 'El producto/servicio requiere atencion humana',
    'otro': 'Otro motivo',
}

motivo_val = (motivo or '').strip()
resumen = (resumen_caso or '').strip()
lead_id_val = lead_id or False

errores = []
if motivo_val not in MOTIVOS_TEXTO:
    errores.append('motivo invalido')
if len(resumen) < 20:
    # minLength no lo valida Odoo (ver esquemas_odoo.py) -- se valida acá.
    errores.append('resumen_caso debe tener al menos 20 caracteres de contexto real')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude derivar: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    motivo_texto = MOTIVOS_TEXTO[motivo_val]
    resumen_completo = motivo_texto + '. ' + resumen

    lead = env['crm.lead'].browse(int(lead_id_val)).exists() if lead_id_val else env['crm.lead'].browse()

    if lead:
        objetivo = lead
        responsable_id = lead.user_id.id or env.user.id
        etiqueta_objetivo = 'lead #' + str(lead.id)
    else:
        # Sin lead: se ancla al partner del usuario real de la conversacion,
        # unico registro garantizado que soporta chatter/actividades.
        objetivo = env.user.partner_id
        responsable_id = env.user.id
        etiqueta_objetivo = 'sin lead asociado'

    objetivo.message_post(body='Derivacion a humano solicitada. ' + resumen_completo)
    objetivo.activity_schedule(
        'mail.mail_activity_data_todo',
        summary='Atencion humana requerida: ' + motivo_texto,
        note=resumen_completo,
        user_id=responsable_id,
    )

    ai['result'] = {
        'ok': True,
        'mensaje': 'Derivado a un responsable humano (' + etiqueta_objetivo + ').',
        'datos': {'motivo': motivo_val, 'lead_id': lead.id if lead else False, 'responsable_id': responsable_id},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
