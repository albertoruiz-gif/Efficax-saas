"""Server Action: legal_contratos / alerta_vencimiento

`aprobacion: "confirmar"`. Programa recordatorios de renovación/aviso
previo de un contrato YA REGISTRADO (`registrar_contrato.py`). Lee la
vigencia desde los campos custom del propio registro
(`x_contrato_vigencia_hasta`) -- el catálogo no manda esa fecha como
parámetro, así que si el contrato no tiene vigencia_hasta registrada
(ej. renovación automática indefinida), no hay nada que alertar y se
dice explícito, no se inventa una fecha.

`dias_antes` es un array de enteros -- Odoo SÍ soporta arrays de
escalares en `ai_tool_schema` (a diferencia de arrays de objetos, ver
`esquemas_odoo.py`), así que llega directo, sin sanear a `_json`.
Pierde su `default: [60, 30, 7]` (Odoo no soporta `default`), se aplica
a mano.

`documents.document` tiene el mixin de actividades (`activity_ids`
confirmado con `fields_get`) -- usa `activity_schedule`, igual que el
resto del catálogo.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
Doc = env['documents.document']
contrato = Doc.browse(contrato_id) if contrato_id else Doc.browse()

if not contrato.exists():
    ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun contrato con id ' + str(contrato_id) + '.', 'datos': {}}
elif not contrato.x_contrato_vigencia_hasta:
    ai['result'] = {
        'ok': False,
        'mensaje': 'El contrato "' + contrato.name + '" no tiene vigencia_hasta registrada (puede ser indefinido) -- no hay fecha de vencimiento sobre la que agendar recordatorios.',
        'datos': {},
    }
else:
    lista_dias = dias_antes if isinstance(dias_antes, list) and dias_antes else [60, 30, 7]
    vigencia_hasta = contrato.x_contrato_vigencia_hasta

    creadas = []
    ya_pasadas = []
    for dias in lista_dias:
        fecha_recordatorio = vigencia_hasta - datetime.timedelta(days=dias)
        if fecha_recordatorio < datetime.date.today():
            ya_pasadas.append({'dias_antes': dias, 'fecha': str(fecha_recordatorio)})
            continue
        actividad = contrato.activity_schedule(
            'mail.mail_activity_data_todo',
            date_deadline=fecha_recordatorio,
            summary='Vencimiento en ' + str(dias) + ' dias: ' + contrato.name,
            note='El contrato "' + contrato.name + '" (contraparte: ' + (contrato.x_contrato_contraparte or 'sin registrar') + ') vence el ' + str(vigencia_hasta) + '.',
        )
        creadas.append({'dias_antes': dias, 'fecha': str(fecha_recordatorio), 'actividad_id': actividad.id})

    ai['result'] = {
        'ok': True,
        'mensaje': (
            str(len(creadas)) + ' recordatorio(s) agendado(s) para "' + contrato.name + '" (vence ' + str(vigencia_hasta) + ').' +
            (' ' + str(len(ya_pasadas)) + ' quedaron en el pasado y no se agendaron.' if ya_pasadas else '')
        ),
        'datos': {'contrato_id': contrato.id, 'vigencia_hasta': str(vigencia_hasta), 'recordatorios_creados': creadas, 'fechas_ya_pasadas': ya_pasadas},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
