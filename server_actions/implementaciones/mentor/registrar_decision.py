"""Server Action: mentor / registrar_decision

Duodécima herramienta con lógica real. Escribe una decisión/acuerdo del
dueño en el expediente del negocio (carpeta "05_decisiones" en la app
Documentos) con fecha, contexto y una etiqueta de visibilidad.

**PENDIENTE DE VERIFICAR EN LA PRUEBA EN VIVO** (a diferencia del resto de
implementaciones de esta noche, `documents.document` — app Enterprise —
todavía no se tocó en esta sesión, así que los nombres de campo de abajo
son la mejor estimación con el conocimiento general de Odoo 19, NO
confirmados con `fields_get` como el resto). Concretamente a confirmar:
  - Si las carpetas son `documents.document` con `type='folder'`, o un
    modelo separado (`documents.folder`, según versión).
  - Si el contenido de texto va en `ir.attachment.raw` (attachment
    separado, enlazado via `attachment_id`) o hay un campo más directo.
Si algo de esto falla, es exactamente el tipo de bug que la prueba en
vivo está diseñada para encontrar y corregir (como pasó esta noche con
`partner.mobile` y `activity_schedule`) — no es un motivo para no
escribir el código, es lo que falta ajustar antes de poder marcarla
"implementada" según la regla de `implementaciones/README.md`.

La carpeta del expediente ("05_decisiones") la crea Booster en su Fase 4
("construir el expediente del negocio", 5 docs — ver
01-booster-implementador.md) — esa fase todavía no está construida, así
que en este tenant es probable que la carpeta no exista todavía. El
código falla explícito en ese caso, no la crea por su cuenta (no le
corresponde a esta herramienta decidir la estructura del expediente).

`visibilidad` pierde su `default: "solo_dueno"` (Odoo no soporta
`default`) — se aplica a mano, conservador por diseño: si no se
especifica, nunca se asume la visibilidad más amplia.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
CATEGORIAS_VALIDAS = ('kpi', 'campana', 'politica', 'credito', 'otro')
VISIBILIDADES_VALIDAS = ('solo_dueno', 'gerencia', 'todo_equipo')
NOMBRE_CARPETA_DECISIONES = '05_decisiones'

decision_txt = (decision or '').strip()
contexto_txt = (contexto or '').strip()
categoria_txt = (categoria or '').strip()
visibilidad_txt = (visibilidad or 'solo_dueno').strip()

errores = []
if len(decision_txt) < 10:
    # minLength no lo valida Odoo (ver esquemas_odoo.py) -- se valida acá.
    errores.append('la decision debe tener al menos 10 caracteres de detalle real')
if categoria_txt not in CATEGORIAS_VALIDAS:
    errores.append('categoria invalida')
if visibilidad_txt not in VISIBILIDADES_VALIDAS:
    errores.append('visibilidad invalida')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude registrar la decision: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Doc = env['documents.document']
    carpeta = Doc.search([('name', '=', NOMBRE_CARPETA_DECISIONES), ('type', '=', 'folder')], limit=1)

    if not carpeta:
        ai['result'] = {
            'ok': False,
            'mensaje': 'No encontre la carpeta "' + NOMBRE_CARPETA_DECISIONES + '" en Documentos. Hay que crear el expediente del negocio antes de poder registrar decisiones.',
            'datos': {},
        }
    else:
        ahora = datetime.datetime.now()
        contenido = (
            'Decision: ' + decision_txt + '\\n\\n' +
            'Contexto: ' + (contexto_txt or '(sin contexto adicional)') + '\\n' +
            'Categoria: ' + categoria_txt + '\\n' +
            'Visibilidad: ' + visibilidad_txt + '\\n' +
            'Registrado: ' + str(ahora)
        )
        adjunto = env['ir.attachment'].create({
            'name': 'Decision ' + str(ahora.date()) + ' - ' + categoria_txt + '.txt',
            'raw': contenido,
            'mimetype': 'text/plain',
        })
        registro = Doc.create({
            'name': 'Decision ' + str(ahora.date()) + ' - ' + categoria_txt,
            'folder_id': carpeta.id,
            'attachment_id': adjunto.id,
        })

        ai['result'] = {
            'ok': True,
            'mensaje': 'Decision registrada en el expediente (categoria: ' + categoria_txt + ', visibilidad: ' + visibilidad_txt + ').',
            'datos': {'documento_id': registro.id, 'categoria': categoria_txt, 'visibilidad': visibilidad_txt},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
