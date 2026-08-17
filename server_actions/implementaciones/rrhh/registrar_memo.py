"""Server Action: rrhh / registrar_memo

Registra un memo o amonestación en el file del empleado
(`aprobacion: "dueno"` -- SIEMPRE un borrador ya aprobado por el dueño
antes de llegar acá, mismo patrón que `crear_puesto.py`/`registrar_decision.py`:
el código no vuelve a pedir confirmación, eso lo hace el agente en la
conversación). El catálogo es explícito: **sin acuse no tiene valor
legal** -- esta herramienta NO decide si un `via_acuse` es válido para el
país (eso requiere al asesor legal, fuera de alcance de código), solo dos
cosas honestas: (1) archiva el documento con `estado='pendiente_acuse'`
por defecto (el `default` del esquema no lo soporta Odoo, se aplica a
mano), y (2) deja UN recordatorio agendado a 7 días para que el dueño
revise si ya hay acuse -- no es un sistema de escalamiento completo, es
lo mínimo verificable en esta sesión; documentado así a propósito.

Se guarda en la MISMA estructura de carpetas que Odoo ya usa para
legajos de empleado (`Employees - <compañía>` / `<nombre empleado>` /
`Memos`, confirmado que existe con `search_read` -- Odoo la crea sola
cuando el módulo de Documentos + RRHH están instalados). No se inventa
una carpeta nueva paralela.

`estado` (pendiente_acuse/acusado) y el `via_acuse` NO son campos nativos
de `documents.document` -- Odoo no tiene ese concepto. Se guardan como
texto dentro del propio documento (nombre + contenido), honestamente
declarado, no como un campo estructurado que no existe.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
TIPOS_VALIDOS = ('memo', 'amonestacion_verbal', 'amonestacion_escrita')
VIAS_VALIDAS = ('firma_odoo', 'firma_fisica_escaneada', 'entrega_con_testigo', 'carta_notarial', 'correo_con_acuse')

tipo_txt = (tipo or '').strip()
sustento_txt = (sustento or '').strip()
texto_txt = (texto or '').strip()
via_txt = (via_acuse or '').strip()
estado_txt = (estado or 'pendiente_acuse').strip()

Empleado = env['hr.employee']
empleado = Empleado.browse(empleado_id) if empleado_id else Empleado.browse()

errores = []
if not empleado.exists():
    errores.append('no encontre ningun empleado con id ' + str(empleado_id))
if tipo_txt not in TIPOS_VALIDOS:
    errores.append('tipo debe ser una de: ' + ', '.join(TIPOS_VALIDOS))
if len(sustento_txt) < 20:
    # minLength no lo valida Odoo -- se valida acá.
    errores.append('sustento debe tener al menos 20 caracteres de detalle real (llego con ' + str(len(sustento_txt)) + ')')
if not texto_txt:
    errores.append('falta texto (el borrador ya aprobado por el dueno)')
if via_txt and via_txt not in VIAS_VALIDAS:
    errores.append('via_acuse invalida')
if estado_txt not in ('pendiente_acuse', 'acusado'):
    errores.append('estado invalido')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude registrar el memo: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Doc = env['documents.document']
    nombre_raiz = 'Employees - ' + empleado.company_id.name if empleado.company_id else 'Employees'
    carpeta_raiz = Doc.search([('name', '=', nombre_raiz), ('type', '=', 'folder')], limit=1)
    if not carpeta_raiz:
        carpeta_raiz = Doc.create({'name': nombre_raiz, 'type': 'folder'})

    carpeta_empleado = Doc.search([('name', '=', empleado.name), ('type', '=', 'folder'), ('folder_id', '=', carpeta_raiz.id)], limit=1)
    if not carpeta_empleado:
        carpeta_empleado = Doc.create({'name': empleado.name, 'type': 'folder', 'folder_id': carpeta_raiz.id})

    carpeta_memos = Doc.search([('name', '=', 'Memos'), ('type', '=', 'folder'), ('folder_id', '=', carpeta_empleado.id)], limit=1)
    if not carpeta_memos:
        carpeta_memos = Doc.create({'name': 'Memos', 'type': 'folder', 'folder_id': carpeta_empleado.id})

    ahora = datetime.datetime.now()
    contenido = (
        'Tipo: ' + tipo_txt + '\\n' +
        'Sustento: ' + sustento_txt + '\\n\\n' +
        texto_txt + '\\n\\n' +
        'Via de acuse: ' + (via_txt or '(no especificada -- requiere confirmar con asesor legal antes de notificar)') + '\\n' +
        'Estado: ' + estado_txt + '\\n' +
        'Registrado: ' + str(ahora)
    )
    nombre_doc = tipo_txt + ' - ' + str(ahora.date()) + ' [' + estado_txt + ']'
    adjunto = env['ir.attachment'].create({
        'name': nombre_doc + '.txt',
        'raw': contenido,
        'mimetype': 'text/plain',
    })
    registro = Doc.create({
        'name': nombre_doc,
        'folder_id': carpeta_memos.id,
        'attachment_id': adjunto.id,
    })

    aviso_recordatorio = ''
    if estado_txt == 'pendiente_acuse':
        fecha_recordatorio = (ahora + datetime.timedelta(days=7)).date()
        empleado.activity_schedule(
            'mail.mail_activity_data_todo',
            date_deadline=fecha_recordatorio,
            summary='Revisar acuse del ' + tipo_txt + ' de ' + empleado.name,
            note='Documento ' + nombre_doc + ' sigue pendiente_acuse -- confirmar si ya hay firma/constancia de entrega.',
        )
        aviso_recordatorio = ' Recordatorio agendado para el ' + str(fecha_recordatorio) + ' si sigue sin acuse.'

    ai['result'] = {
        'ok': True,
        'mensaje': (
            tipo_txt.capitalize() + ' registrado en el file de ' + empleado.name + ' (estado: ' + estado_txt + ').' +
            (' Sin acuse todavia no tiene valor legal.' if estado_txt == 'pendiente_acuse' else '') +
            aviso_recordatorio
        ),
        'datos': {'documento_id': registro.id, 'empleado_id': empleado.id, 'tipo': tipo_txt, 'estado': estado_txt},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
