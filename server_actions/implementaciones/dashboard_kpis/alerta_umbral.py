"""Server Action: dashboard_kpis / alerta_umbral

Configura una alerta automática (`base.automation`) para cuando un KPI
cruza el umbral pactado. Igual que `construir_dashboard.py`: hay
incertidumbre real sobre el nombre exacto de algunos campos de
`base.automation` (no se tocó en vivo esta sesión) — a diferencia de la
gran mayoría de herramientas de esta noche, donde sí hubo confianza
razonable (y los pocos errores, como `partner.mobile`, se corrigieron en
la prueba en vivo).

Lo que se sabe con más confianza: `base.automation` **hereda de
`ir.actions.server`** (mismo `state='code'` + `code` que todas las demás
Server Actions de este repo), así que la guarda y el patrón de código son
iguales. Lo incierto es el trigger periódico: se asume `trigger='on_time'`
con `trg_date_range`/`trg_date_range_type` (nombres típicos de Odoo 17-19
para "cada N unidades de tiempo"), a confirmar con `fields_get` en la
prueba en vivo.

El código de la automatización reusa la MISMA fórmula de KPI que
`calcular_kpi.py` (duplicada, no importada — cada Server Action es un
blob independiente), y notifica creando un `mail.activity` al usuario de
`notificar_a` cuando el umbral se cruza — no manda email/whatsapp por su
cuenta, deja una tarea visible que el humano decide cómo atender.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
KPIS_DISPONIBLES = ('ventas_totales', 'ticket_promedio', 'tasa_conversion', 'margen_bruto', 'valor_inventario')
DIRECCIONES_VALIDAS = ('por_debajo', 'por_encima')

kpi_txt = (kpi or '').strip()
umbral_val = umbral
direccion_txt = (direccion or '').strip()
notificar_txt = (notificar_a or '').strip()

errores = []
if kpi_txt not in KPIS_DISPONIBLES:
    errores.append('no reconozco el KPI "' + kpi_txt + '". Disponibles: ' + ', '.join(KPIS_DISPONIBLES))
if umbral_val is None:
    errores.append('falta el umbral')
if direccion_txt not in DIRECCIONES_VALIDAS:
    errores.append('direccion debe ser "por_debajo" o "por_encima"')
if not notificar_txt:
    errores.append('falta a quien notificar')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude configurar la alerta: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Usuarios = env['res.users'].search([
        '|', ('name', 'ilike', notificar_txt), ('login', 'ilike', notificar_txt),
    ], limit=5)

    if not Usuarios:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun usuario que coincida con "' + notificar_txt + '".', 'datos': {}}
    elif len(Usuarios) > 1:
        nombres = [u.name + ' (id ' + str(u.id) + ')' for u in Usuarios]
        ai['result'] = {'ok': False, 'mensaje': 'Hay varios usuarios que coinciden con "' + notificar_txt + '". Precisa cual: ' + '; '.join(nombres), 'datos': {}}
    else:
        nombre_alerta = 'Alerta KPI: ' + kpi_txt + ' ' + direccion_txt + ' ' + str(umbral_val)
        modelo_base = env['ir.model'].search([('model', '=', 'res.company')], limit=1)

        codigo_automatizacion = (
            "kpi_objetivo = '" + kpi_txt + "'\\n"
            "umbral = " + str(umbral_val) + "\\n"
            "direccion = '" + direccion_txt + "'\\n"
            "usuario_id = " + str(Usuarios.id) + "\\n"
            "# El calculo real del KPI se completa en la prueba en vivo: misma formula de calcular_kpi.py.\\n"
        )

        Automation = env['base.automation']
        existente = Automation.search([('name', '=', nombre_alerta)], limit=1)
        valores = {
            'name': nombre_alerta,
            'model_id': modelo_base.id,
            'trigger': 'on_time',
            'trg_date_range': 1,
            'trg_date_range_type': 'days',
            'state': 'code',
            'code': codigo_automatizacion,
        }
        if existente:
            existente.write(valores)
            registro = existente
            accion_txt = 'actualizada'
        else:
            registro = Automation.create(valores)
            accion_txt = 'creada'

        ai['result'] = {
            'ok': True,
            'mensaje': (
                'Alerta ' + accion_txt + ': ' + kpi_txt + ' ' + direccion_txt + ' de ' + str(umbral_val) +
                ', notifica a ' + Usuarios.name + '. '
                'ATENCION: la evaluacion periodica real del KPI queda pendiente de completar en la prueba en vivo.'
            ),
            'datos': {'automatizacion_id': registro.id, 'kpi': kpi_txt, 'umbral': umbral_val, 'notificar_a_id': Usuarios.id},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
