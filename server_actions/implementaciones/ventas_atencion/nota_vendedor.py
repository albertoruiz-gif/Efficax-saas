"""Server Action: ventas_atencion / nota_vendedor

Séptima herramienta con lógica real. Canal INTERNO: el vendedor dicta una
nota de visita/llamada, se registra en el CRM como nota interna (no un
mensaje de cara al cliente) y, opcionalmente, agenda un seguimiento.

Decisiones de implementación:

- `cliente_o_lead` es texto libre (nombre), no un id — se busca por
  `name`/`contact_name` con el mismo patrón "nunca inventar" que
  `consulta_precio_stock`: 0 coincidencias o más de 1 → se pide precisar,
  nunca se adivina cuál.
- La nota se postea con `subtype_xmlid='mail.mt_note'` explícitamente
  (nota interna, no mensaje) — es justo la distinción que pide la
  descripción del catálogo ("Canal interno").
- `seguimiento` (objeto anidado en el catálogo) llega aplanado como
  `seguimiento_tipo` / `seguimiento_fecha` (ver esquemas_odoo.py).
- El seguimiento se agenda SIEMPRE como `mail.activity` (vía
  `activity_schedule`), no como `calendar.event`: crear eventos de
  calendario reales es responsabilidad de `agendar_reunion.py`, que existe
  específicamente para eso — evita que dos herramientas compitan por la
  misma responsabilidad. `calendar.event` aparece en `modelos_odoo` del
  catálogo porque describe al AGENTE en conjunto, no que cada herramienta
  suya deba tocar ese modelo.
- No hay tipo de actividad nativo de Odoo para "visita" — se usa el
  genérico "To-Do", dejando "Visita:" explícito en el resumen para que no
  se confunda con una llamada o reunión real.
- Si se pide seguimiento pero no llega `seguimiento_fecha` (o llega en un
  formato no parseable — Odoo ya no valida `format: date`, ver
  esquemas_odoo.py), se agenda para mañana por defecto y se avisa en el
  mensaje de respuesta — nunca se falla en silencio ni se inventa una
  fecha sin decirlo.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
MAPA_ACTIVIDAD = {
    'llamada': 'mail.mail_activity_data_call',
    'reunion': 'mail.mail_activity_data_meeting',
    'visita': 'mail.mail_activity_data_todo',
}
ETIQUETA_TIPO = {'llamada': 'Llamada', 'reunion': 'Reunion', 'visita': 'Visita'}

nombre_buscado = (cliente_o_lead or '').strip()
nota_txt = (nota or '').strip()
tipo_seg = (seguimiento_tipo or 'ninguno').strip()
fecha_seg_txt = (seguimiento_fecha or '').strip()

errores = []
if not nombre_buscado:
    errores.append('falta el nombre del cliente o lead')
if len(nota_txt) < 10:
    errores.append('la nota debe tener al menos 10 caracteres')
if tipo_seg not in ('llamada', 'visita', 'reunion', 'ninguno'):
    errores.append('seguimiento_tipo invalido')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude grabar la nota: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Lead = env['crm.lead']
    candidatos = Lead.search(
        ['|', ('name', 'ilike', nombre_buscado), ('contact_name', 'ilike', nombre_buscado)],
        limit=5,
    )

    if not candidatos:
        ai['result'] = {
            'ok': False,
            'mensaje': 'No encontre ningun cliente o lead que coincida con "' + nombre_buscado + '".',
            'datos': {},
        }
    elif len(candidatos) > 1:
        nombres = [(c.contact_name or c.name) + ' (id ' + str(c.id) + ')' for c in candidatos]
        ai['result'] = {
            'ok': False,
            'mensaje': 'Hay varios que coinciden con "' + nombre_buscado + '". Precisa cual: ' + '; '.join(nombres),
            'datos': {'candidatos': nombres},
        }
    else:
        lead = candidatos[0]
        lead.message_post(body='Nota de vendedor: ' + nota_txt, subtype_xmlid='mail.mt_note')

        aviso_fecha = ''
        if tipo_seg != 'ninguno':
            fecha_dt = False
            if fecha_seg_txt:
                try:
                    fecha_dt = datetime.datetime.strptime(fecha_seg_txt, '%Y-%m-%d').date()
                except:  # noqa: E722 -- ValueError no esta expuesto en el sandbox de Odoo (ver README)
                    fecha_dt = False
            if not fecha_dt:
                fecha_dt = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
                aviso_fecha = ' (sin fecha valida indicada, se agendo para manana)'

            lead.activity_schedule(
                MAPA_ACTIVIDAD[tipo_seg],
                date_deadline=fecha_dt,
                summary=ETIQUETA_TIPO[tipo_seg] + ' de seguimiento (nota de vendedor)',
                note=nota_txt,
                user_id=lead.user_id.id or env.user.id,
            )

        ai['result'] = {
            'ok': True,
            'mensaje': 'Nota registrada en ' + (lead.contact_name or lead.name) + '.' + (
                ' Seguimiento (' + tipo_seg + ') agendado' + aviso_fecha + '.' if tipo_seg != 'ninguno' else ''
            ),
            'datos': {'lead_id': lead.id, 'seguimiento_tipo': tipo_seg},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
