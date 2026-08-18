"""Server Action: legal_contratos / preparar_firma

`aprobacion: "dueno"`. Arma el circuito en Firma electrónica de Odoo
(`sign.request`) a partir de un documento ya archivado
(`documents.document`). **El catálogo es explícito: "El ENVÍO lo
dispara el dueño"** -- esta herramienta NUNCA envía nada, solo prepara
el circuito para que el dueño lo revise y lo mande él mismo desde la
app Firmar.

**Incertidumbre real declarada (no probada en profundidad):**
`sign.request` necesita un `sign.template` (un documento con los campos
de firma YA COLOCADOS en coordenadas x/y de página -- confirmado con
`fields_get`: `sign.item.page/posX/posY/width/height` son todos
obligatorios). Colocar esos campos con precisión normalmente se hace a
mano en el editor visual de Firma, viendo el documento real -- este
código NO puede ver el PDF (no hay librería de render en el sandbox),
así que coloca un campo de firma por firmante en una posición
FIJA/genérica de la página 1 (franjas horizontales), pensada como punto
de partida, no como colocación definitiva. El dueño debe revisar la
posición en el editor de Firma antes de enviar -- lo cual de todos
modos tiene que hacer, porque esta herramienta nunca envía sola.

**Corrección (confirmada con `fields_get` contra el Odoo 19 real, no
supuesta):** `sign.template` NO tiene un campo `attachment_id` propio
-- el adjunto se cuelga de un registro intermedio `sign.document`
(`attachment_id` + `template_id`, ambos obligatorios en ese modelo), y
`sign.item.document_id` (obligatorio) apunta a ese `sign.document`, no
directo al `sign.template`.

**Segunda corrección (encontrada probando en vivo con un PDF real):**
una plantilla con `nombre_plantilla` puede existir pero estar
INCOMPLETA -- por ejemplo si un intento anterior falló al procesar el
PDF (adjunto cifrado o corrupto) despues de crear el `sign.template`
pero antes de crear su `sign.document`/`sign.item`. Tratar
"la plantilla ya existe" como "ya está armada" deja una plantilla
huérfana sin firmantes cubiertos, y Odoo rechaza el `sign.request`
resultante ("Debe especificar un firmante para cada rol de su
plantilla").

**Tercera corrección (mismo problema, un nivel más abajo):** ni
siquiera "la plantilla ya tiene `document_ids`" es suficiente --
un intento anterior puede haber creado el `sign.document` (adjunto
enlazado) y fallar ANTES de crear el `sign.item` (ej. por un
`AccessError` real de permisos, visto en la prueba en vivo del
18-ago-2026: faltaba el grupo de seguridad de Firma electrónica).
El criterio correcto es si el `sign.document` YA TIENE
`sign_item_ids` -- eso es lo que de verdad determina si los campos de
firma están armados. Si el documento existe pero sin items, se
reutiliza el documento y se arman los items sobre él (no se crea un
segundo `sign.document` duplicado).

**Precaución tomada para la prueba en vivo:** para no arriesgar un
envío real no autorizado a un tercero si la suposición de que
`sign.request.create()` no dispara correo por sí solo resultara
incorrecta, la prueba en vivo de esta herramienta usa como firmante de
prueba el correo del propio Alberto, nunca un tercero real.

`firmantes` es un array de objetos -- `esquemas_odoo.py` lo sanea a un
único parámetro string `firmantes_json` (ver convención ya usada en
`inventarios/registrar_conteo.py` y `ventas_atencion/crear_cotizacion.py`),
así que llega serializado y se parsea con `json.loads` (el sandbox trae
el módulo `json`).

**Estado de la prueba en vivo (18-ago-2026): código validado, pero NO
confirmado de punta a punta por el chat.** Cada operación de este
código (crear `sign.document`, `sign.item`, `sign.item.role`,
`res.partner`, `sign.request`) se probó exitosamente UNA POR UNA
llamándola directo por RPC con exactamente los mismos valores -- todas
funcionan. Pero al invocar la herramienta completa a través del chat
del agente de IA, la ejecución termina en un error genérico de Odoo
("¡Uy! Se ha producido un error...") sin que se escriba nada en la
base de datos (confirmado por RPC después de cada intento). El
traceback de ese error muestra que la falla ocurre DESPUÉS de que el
agente ya generó su respuesta, al intentar publicarla en el canal
(`ai/models/ai_agent.py:_post_ai_response -> message_post`), con
`psycopg2.errors.InFailedSqlTransaction: current transaction is
aborted` -- es decir, algo ANTES en esa misma transacción ya había
fallado a nivel SQL, y Odoo no hizo `rollback` antes de seguir. Ese
código anterior es interno del módulo `ai` de Odoo Enterprise (no es
parte de este repo), así que no es algo que se pueda corregir desde
acá. Reproducible de forma consistente (no es una condición de
carrera de reintentos). Pendiente: reportarlo a soporte de Odoo o
revisar los logs del servidor con acceso de administrador.

**Precondición del tenant (no es un bug de código, encontrado probando
en vivo el 18-ago-2026):** crear un `sign.item` requiere el grupo de
seguridad "Sign / User: Own Templates" (o "Sign / Administrator") --
sin él, Odoo devuelve un `AccessError` real. La convención del
catálogo es explícita: nunca `sudo()` fuera del guard, así que esta
herramienta corre con los permisos reales del usuario que la invoca --
si ese usuario no tiene el grupo de Firma electrónica asignado en
Ajustes > Usuarios, la herramienta falla (correctamente: no debe
saltarse el control de acceso real del tenant).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
Doc = env['documents.document']
documento = Doc.browse(documento_id) if documento_id else Doc.browse()

lista_firmantes = []
if firmantes_json:
    try:
        lista_firmantes = json.loads(firmantes_json)
    except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
        lista_firmantes = []
if not isinstance(lista_firmantes, list):
    lista_firmantes = []

errores = []
if not documento.exists():
    errores.append('no encontre ningun documento con id ' + str(documento_id))
elif not documento.attachment_id:
    errores.append('el documento "' + documento.name + '" no tiene un archivo adjunto para firmar')
if not lista_firmantes:
    errores.append('firmantes no puede estar vacio')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude preparar la firma: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Role = env['sign.item.role']
    TipoFirma = env['sign.item.type'].search([('name', '=', 'Signature')], limit=1)

    nombre_plantilla = 'Firma -- ' + documento.name
    Plantilla = env['sign.template']
    plantilla_existente = Plantilla.search([('name', '=', nombre_plantilla)], limit=1)
    plantilla = plantilla_existente if plantilla_existente else Plantilla.create({'name': nombre_plantilla})

    # "ya existe la plantilla" y "ya existe el sign.document" no son lo
    # mismo que "ya estan armados los campos de firma" -- un intento
    # anterior puede haber fallado a medio camino (PDF corrupto, permiso
    # faltante) dejando piezas sueltas. Lo unico que de verdad indica que
    # ya esta armado es que el sign.document tenga sign_item_ids (ver
    # docstring).
    documentos_existentes = plantilla.document_ids
    if documentos_existentes:
        doc_firma = documentos_existentes[:1]
    else:
        doc_firma = env['sign.document'].create({
            'attachment_id': documento.attachment_id.id,
            'template_id': plantilla.id,
        })
    plantilla_necesita_armado = not doc_firma.sign_item_ids

    firmantes_armados = []
    errores_firmantes = []
    altura_franja = 0.06
    for i, f in enumerate(lista_firmantes):
        nombre_f = (f.get('nombre') or '').strip()
        email_f = (f.get('email') or '').strip()
        orden_f = f.get('orden') or (i + 1)
        if not nombre_f or not email_f:
            errores_firmantes.append('firmante en posicion ' + str(i + 1) + ' sin nombre o email')
            continue

        nombre_rol = 'Firmante ' + str(i + 1)
        rol = Role.search([('name', '=', nombre_rol)], limit=1)
        if not rol:
            rol = Role.create({'name': nombre_rol})

        # campo de firma en una franja horizontal generica de la pagina 1
        # -- punto de partida, no colocacion definitiva (ver docstring).
        if plantilla_necesita_armado:
            env['sign.item'].create({
                'document_id': doc_firma.id,
                'type_id': TipoFirma.id,
                'responsible_id': rol.id,
                'page': 1,
                'posX': 0.1,
                'posY': 0.80 + (i * altura_franja),
                'width': 0.3,
                'height': altura_franja * 0.8,
                'alignment': 'left',
            })

        Partner = env['res.partner'].search(['|', ('email', '=ilike', email_f), ('name', 'ilike', nombre_f)], limit=1)
        if not Partner:
            Partner = env['res.partner'].create({'name': nombre_f, 'email': email_f})

        firmantes_armados.append({'role_id': rol.id, 'partner_id': Partner.id, 'orden': orden_f, 'nombre': nombre_f, 'email': email_f})

    if errores_firmantes:
        ai['result'] = {'ok': False, 'mensaje': 'No pude armar todos los firmantes: ' + '; '.join(errores_firmantes) + '.', 'datos': {}}
    else:
        SignRequest = env['sign.request']
        solicitud = SignRequest.create({
            'reference': documento.name,
            'template_id': plantilla.id,
            'request_item_ids': [(0, 0, {'role_id': fa['role_id'], 'partner_id': fa['partner_id']}) for fa in firmantes_armados],
        })

        ai['result'] = {
            'ok': True,
            'mensaje': (
                'Circuito de firma preparado para "' + documento.name + '" con ' + str(len(firmantes_armados)) + ' firmante(s). ' +
                'NO se envio -- revisa la posicion de los campos de firma en la app Firmar antes de mandarlo.'
            ),
            'datos': {'sign_request_id': solicitud.id, 'sign_template_id': plantilla.id, 'firmantes': firmantes_armados},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
