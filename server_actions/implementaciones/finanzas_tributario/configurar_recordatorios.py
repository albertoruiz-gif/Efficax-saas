"""Server Action: finanzas_tributario / configurar_recordatorios

`aprobacion: "dueno"`. Crea/edita un nivel de "Seguimientos de pago"
nativo de Odoo (`account_followup.followup.line`) por tramo -- mapeo
directo de `Playbook_Creditos_Cobranzas.md` §5 ("Tramos de cobranza y
recordatorios | Niveles de seguimiento (follow-up) de Contabilidad").

Campos reales confirmados con `fields_get`: `delay` (Due Days, entero,
mapea a `dias_offset`), `send_email`/`send_whatsapp`/`send_letter`
(booleanos por canal -- el modelo SÍ distingue canal, a diferencia de lo
que sugiere el nombre "email" en el catálogo), `auto_execute` (mapea a
`auto_envio`).

**Sin equivalente nativo:** `frecuencia_dias` (cada cuánto se repite el
recordatorio DENTRO del tramo) no tiene campo propio en
`account_followup.followup.line` -- cada nivel es un disparo único a
`delay` días del vencimiento, no una cadencia repetitiva. Se guarda como
texto en la descripción del nivel (`name`), declarado honesto en vez de
inventar un campo que no existe.

`auto_envio=true` **solo se permite en tramos "suaves"** -- el catálogo
dice "pre-aprobados por el dueño (decisión de Fase 4)", que no existe
todavía en este tenant. Hasta que exista esa configuración real, se
restringe de forma conservadora a `preventiva`/`temprana` (los únicos
con tono "Servicio"/"Cordial" en el playbook) -- cualquier otro tramo
con `auto_envio=true` se rechaza explícito.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
TRAMOS_VALIDOS = ('preventiva', 'temprana', 'intermedia_1', 'intermedia_2', 'tardia', 'prejudicial', 'judicial')
TRAMOS_SUAVES = ('preventiva', 'temprana')

tramo_txt = (tramo or '').strip()
offset_val = dias_offset
frecuencia_val = frecuencia_dias
plantilla_txt = (plantilla or '').strip()
auto_envio_val = bool(auto_envio) if auto_envio is not None else False

errores = []
if tramo_txt not in TRAMOS_VALIDOS:
    errores.append('tramo debe ser una de: ' + ', '.join(TRAMOS_VALIDOS))
if offset_val is None:
    errores.append('falta dias_offset')
if frecuencia_val is None or frecuencia_val < 1:
    errores.append('frecuencia_dias debe ser al menos 1')
if auto_envio_val and tramo_txt not in TRAMOS_SUAVES:
    errores.append('auto_envio=true solo esta permitido en tramos suaves (' + ', '.join(TRAMOS_SUAVES) + ') hasta que exista una configuracion de Fase 4 que lo autorice para otros tramos')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude configurar el recordatorio: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    nombre_nivel = 'Cobranza -- ' + tramo_txt
    descripcion = nombre_nivel + ' (repite cada ' + str(frecuencia_val) + ' dia(s) dentro del tramo -- sin campo nativo para la cadencia, ver docstring)'

    Followup = env['account_followup.followup.line']
    existente = Followup.search([('name', '=', nombre_nivel)], limit=1)
    valores = {
        'name': descripcion,
        'delay': offset_val,
        'send_email': True,
        'auto_execute': auto_envio_val,
        'company_id': env.company.id,
    }
    if existente:
        existente.write(valores)
        registro = existente
        accion_txt = 'actualizado'
    else:
        registro = Followup.create(valores)
        accion_txt = 'creado'

    aviso_plantilla = ''
    if plantilla_txt:
        aviso_plantilla = ' (la plantilla de texto entregada queda en el registro de esta conversacion -- vincularla a un mail.template real es un paso manual pendiente, no se crea uno automaticamente)'

    ai['result'] = {
        'ok': True,
        'mensaje': (
            'Nivel de seguimiento ' + accion_txt + ' para el tramo "' + tramo_txt + '": ' + str(offset_val) + ' dias respecto al vencimiento, ' +
            'auto-envio ' + ('activado' if auto_envio_val else 'desactivado') + '.' + aviso_plantilla
        ),
        'datos': {'followup_line_id': registro.id, 'tramo': tramo_txt, 'dias_offset': offset_val, 'frecuencia_dias': frecuencia_val, 'auto_envio': auto_envio_val},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
