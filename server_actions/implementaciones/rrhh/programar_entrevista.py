"""Server Action: rrhh / programar_entrevista

Agenda la entrevista entre candidato y dueño en el Calendario
(`aprobacion: "confirmar"`). Crea un `calendar.event` enlazado al
candidato via `res_model`/`res_id` (así aparece en el `meeting_ids` del
`hr.applicant`, confirmado con `fields_get`) -- mismo mecanismo que usa
Odoo internamente para el botón "Meetings" del kanban de reclutamiento.

`fecha_hora` llega en hora local de Lima -- mismo offset fijo +5h a UTC
que `agendar_reunion.py` (ver esa herramienta y `implementaciones/README.md`
sobre por qué el offset es fijo y seguro para Perú, sin horario de
verano). `duracion_min` pierde su `default: 45` (Odoo no soporta
`default`, se aplica a mano). `modo` pierde su `default: "video"`, misma
razón.

El organizador es quien le habla al agente (`env.user`, sin `sudo()`) --
si el candidato tiene un `partner_id` (contacto) ya vinculado, se agrega
como asistente; si no, el nombre/email del candidato queda solo en la
descripción (no se inventa un contacto que no existe, mismo criterio que
`agendar_reunion.py` con `contacto`).

**Riesgo real confirmado en la prueba en vivo (17-ago-2026), NO resuelto
del todo:** pedí "20 de agosto de 2026 a las 15:00 hora Lima" y el evento
quedó guardado a las 20:00 UTC del 21-ago (5 horas tarde -- el doble del
offset esperado). Causa: el catálogo no le dice al modelo de IA en qué
convención debe entregar `fecha_hora` (ver `input_schema.fecha_hora` en
el catálogo, sin `description`) -- esta vez el agente parece haber
convertido "15:00 Lima" a UTC (20:00) POR SU CUENTA antes de llamar la
herramienta, y el código sumó +5h otra vez sobre ese valor ya convertido,
duplicando el corrimiento. En la prueba de `agendar_reunion.py` (misma
lógica de +5h) el agente NO había pre-convertido y el resultado fue
correcto -- el comportamiento del modelo no es consistente entre
llamadas. Corregido el dato de esta prueba a mano. Arreglar esto de raíz
requiere agregar una `description` explícita al campo `fecha_hora` en el
catálogo (fuera de este repo, ver `server_actions/README.md` sobre esa
dependencia cross-repo) indicando "hora LOCAL de Lima, no conviertas a
UTC" -- documentado como pendiente, no inventado un arreglo a medias
acá.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
MODOS_VALIDOS = ('presencial', 'video')

fecha_hora_txt = (fecha_hora or '').strip()
duracion_val = duracion_min or 45
modo_txt = (modo or 'video').strip()

errores = []
if modo_txt not in MODOS_VALIDOS:
    errores.append('modo debe ser "presencial" o "video"')
if duracion_val < 1:
    errores.append('duracion_min debe ser mayor a 0')

fecha_dt = False
for patron in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'):
    try:
        fecha_dt = datetime.datetime.strptime(fecha_hora_txt, patron)
        break
    except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
        continue
if not fecha_dt:
    errores.append('no entendi fecha_hora "' + fecha_hora_txt + '" -- usa AAAA-MM-DD HH:MM')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude agendar la entrevista: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Applicant = env['hr.applicant']
    candidato = Applicant.browse(candidato_id) if candidato_id else Applicant.browse()

    if not candidato.exists():
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun candidato con id ' + str(candidato_id) + '.', 'datos': {}}
    else:
        # hora local Lima -> UTC (Peru es UTC-5 fijo, ver README).
        fecha_utc = fecha_dt + datetime.timedelta(hours=5)
        modelo_applicant = env['ir.model'].search([('model', '=', 'hr.applicant')], limit=1)

        valores = {
            'name': 'Entrevista: ' + (candidato.partner_name or 'candidato ' + str(candidato.id)),
            'start': fecha_utc,
            'stop': fecha_utc + datetime.timedelta(minutes=duracion_val),
            'user_id': env.user.id,
            'description': 'Modalidad: ' + modo_txt + '. Candidato: ' + (candidato.partner_name or '') + ' (' + (candidato.email_from or 'sin email') + ')',
            'res_model': 'hr.applicant',
            'res_id': candidato.id,
            'res_model_id': modelo_applicant.id,
        }
        asistentes = [env.user.partner_id.id]
        aviso_contacto = ''
        if candidato.partner_id:
            asistentes.append(candidato.partner_id.id)
        else:
            aviso_contacto = ' (el candidato no tiene un contacto vinculado todavia, no se invito por email automaticamente)'
        valores['partner_ids'] = [(6, 0, asistentes)]

        evento = env['calendar.event'].create(valores)

        ai['result'] = {
            'ok': True,
            'mensaje': 'Entrevista agendada para el ' + str(fecha_dt) + ' hora Lima (' + modo_txt + ', ' + str(duracion_val) + ' min).' + aviso_contacto,
            'datos': {'evento_id': evento.id, 'candidato_id': candidato.id},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
