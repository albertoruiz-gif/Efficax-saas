"""Server Action: rrhh / checklist_onboarding

Genera el plan 1 día / 1 semana / 1 mes del puesto como actividades
asignadas al empleado (`aprobacion: "confirmar"`). `hr.employee` tiene el
mixin de actividades (`activity_ids` presente en `fields_get`), así que
usa `empleado.activity_schedule(...)` -- el método que ya demostró
funcionar en vivo esta sesión (`crear_actividad.py` de Mentor,
`crear_ticket.py`), a diferencia del camino manual
`ir.model.search()` + `mail.activity.create()` que falló en silencio.

`empleado`/`puesto` llegan como texto libre (no ids) -- se busca el
empleado por nombre con el mismo patrón "nunca inventar, ambiguo se
pregunta" del resto del catálogo (`nota_vendedor.py`,
`agendar_reunion.py`). `puesto` es solo texto descriptivo para el
contenido de las actividades, no se valida contra `hr.job` porque el
catálogo no lo declara como id.

Las 3 actividades quedan con `date_deadline` = `fecha_inicio` + 0/7/30
días -- son fechas (no horas), así que no aplica el offset de zona
horaria que sí necesitan los `Datetime` (ver `agendar_reunion.py`).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
empleado_txt = (empleado or '').strip()
puesto_txt = (puesto or '').strip()
fecha_inicio_txt = (fecha_inicio or '').strip()

fecha_dt = False
try:
    fecha_dt = datetime.datetime.strptime(fecha_inicio_txt, '%Y-%m-%d').date()
except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
    fecha_dt = False

errores = []
if not empleado_txt:
    errores.append('falta el nombre del empleado')
if not puesto_txt:
    errores.append('falta el puesto')
if not fecha_dt:
    errores.append('fecha_inicio debe ser una fecha valida en formato AAAA-MM-DD')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude generar el onboarding: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Empleados = env['hr.employee'].search([('name', 'ilike', empleado_txt)], limit=5)

    if not Empleados:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun empleado que coincida con "' + empleado_txt + '".', 'datos': {}}
    elif len(Empleados) > 1:
        nombres = [e.name + ' (id ' + str(e.id) + ')' for e in Empleados]
        ai['result'] = {'ok': False, 'mensaje': 'Hay varios empleados que coinciden con "' + empleado_txt + '". Precisa cual: ' + '; '.join(nombres), 'datos': {}}
    else:
        HITOS = (
            (0, 'Dia 1', 'Bienvenida, accesos y presentacion del equipo'),
            (7, 'Semana 1', 'Primeras tareas del puesto de ' + puesto_txt + ' y seguimiento con el responsable'),
            (30, 'Mes 1', 'Evaluacion de avance del primer mes en ' + puesto_txt),
        )
        actividades_creadas = []
        for dias, etiqueta, detalle in HITOS:
            fecha_hito = fecha_dt + datetime.timedelta(days=dias)
            actividad = Empleados.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fecha_hito,
                summary='Onboarding ' + etiqueta + ' -- ' + Empleados.name,
                note=detalle,
            )
            actividades_creadas.append({'hito': etiqueta, 'fecha': str(fecha_hito), 'actividad_id': actividad.id})

        ai['result'] = {
            'ok': True,
            'mensaje': 'Plan de onboarding creado para ' + Empleados.name + ' (' + puesto_txt + '): 3 actividades (dia 1, semana 1, mes 1) desde ' + str(fecha_dt) + '.',
            'datos': {'empleado_id': Empleados.id, 'actividades': actividades_creadas},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
