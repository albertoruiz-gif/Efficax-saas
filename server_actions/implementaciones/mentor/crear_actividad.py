"""Server Action: mentor / crear_actividad

Decimotercera herramienta con lógica real. Agenda una tarea/recordatorio
(`mail.activity`) a un usuario interno, opcionalmente sobre un registro
específico (`modelo_ref` + `id_ref` — ninguno de los dos es obligatorio
en el esquema).

Sin registro relacionado, igual que en `derivar_humano.py`: no existe
forma de crear un `mail.activity` sin `res_model`/`res_id` (Odoo lo
exige), así que se ancla al `res.partner` del usuario asignado — la
actividad queda como un recordatorio personal en vez de fallar o
inventar un registro relacionado que nadie pidió.

`modelo_ref` es texto libre del catálogo — antes de hacer `env[modelo_ref]`
se valida que el modelo exista de verdad (`ir.model.search`), para no
reventar con un modelo inventado o mal escrito.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
usuario_txt = (usuario_asignado or '').strip()
titulo_txt = (titulo or '').strip()
fecha_txt = (fecha_limite or '').strip()
modelo_ref_txt = (modelo_ref or '').strip()
id_ref_val = id_ref or False

errores = []
if not usuario_txt:
    errores.append('falta el usuario asignado')
if not titulo_txt:
    errores.append('falta el titulo de la actividad')

fecha_dt = False
if fecha_txt:
    try:
        fecha_dt = datetime.datetime.strptime(fecha_txt, '%Y-%m-%d').date()
    except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
        fecha_dt = False
if not fecha_dt:
    errores.append('fecha_limite invalida, usa AAAA-MM-DD')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude agendar la actividad: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Usuarios = env['res.users'].search([
        '|', ('name', 'ilike', usuario_txt), ('login', 'ilike', usuario_txt),
    ], limit=5)

    if not Usuarios:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun usuario interno que coincida con "' + usuario_txt + '".', 'datos': {}}
    elif len(Usuarios) > 1:
        nombres = [u.name + ' (id ' + str(u.id) + ')' for u in Usuarios]
        ai['result'] = {'ok': False, 'mensaje': 'Hay varios usuarios que coinciden con "' + usuario_txt + '". Precisa cual: ' + '; '.join(nombres), 'datos': {}}
    else:
        objetivo = False
        if modelo_ref_txt and id_ref_val:
            existe_modelo = env['ir.model'].search([('model', '=', modelo_ref_txt)], limit=1)
            if not existe_modelo:
                ai['result'] = {'ok': False, 'mensaje': 'El modelo "' + modelo_ref_txt + '" no existe.', 'datos': {}}
            else:
                registro = env[modelo_ref_txt].browse(int(id_ref_val)).exists()
                if not registro:
                    ai['result'] = {'ok': False, 'mensaje': 'No encontre el registro ' + modelo_ref_txt + ' #' + str(id_ref_val) + '.', 'datos': {}}
                else:
                    objetivo = registro
        else:
            objetivo = Usuarios.partner_id

        if objetivo:
            objetivo.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fecha_dt,
                summary=titulo_txt,
                user_id=Usuarios.id,
            )
            etiqueta = (modelo_ref_txt + ' #' + str(id_ref_val)) if (modelo_ref_txt and id_ref_val) else ('recordatorio personal de ' + Usuarios.name)
            ai['result'] = {
                'ok': True,
                'mensaje': 'Actividad agendada para ' + Usuarios.name + ' (' + etiqueta + '), vence el ' + str(fecha_dt) + '.',
                'datos': {'usuario_id': Usuarios.id, 'fecha_limite': str(fecha_dt)},
            }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
