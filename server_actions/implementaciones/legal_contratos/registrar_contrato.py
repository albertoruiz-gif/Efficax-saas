"""Server Action: legal_contratos / registrar_contrato

`aprobacion: "confirmar"`. Archiva un contrato ya firmado/vigente en la
carpeta "Legal" de Documentos (ya existe en este tenant --
`documents.document` id de la carpeta "Contracts" dentro de "Legal",
confirmado con `search`, no creada por esta herramienta) con sus
metadatos: contraparte, vigencia, renovación automática, días de aviso
previo, semáforo.

**Campos custom necesarios:** `documents.document` no tiene ninguno de
estos metadatos de forma nativa -- creados por
`instalar_campos_legal.py` (mismo patrón que
`instalar_campos_inventarios.py`). Sin ellos, `alerta_vencimiento`
(que solo recibe `contrato_id` + `dias_antes`, sin la vigencia como
parámetro) no tendría de dónde leer la fecha de vencimiento.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
SEMAFOROS_VALIDOS = ('verde', 'amarillo', 'rojo')

nombre_txt = (nombre or '').strip()
contraparte_txt = (contraparte or '').strip()
vigencia_desde_txt = (vigencia_desde or '').strip()
vigencia_hasta_txt = (vigencia_hasta or '').strip()
renovacion_val = bool(renovacion_automatica) if renovacion_automatica is not None else False
dias_aviso_val = dias_aviso_previo if dias_aviso_previo is not None else 30
semaforo_txt = (semaforo or '').strip()

errores = []
if not nombre_txt:
    errores.append('falta el nombre del contrato')
if not contraparte_txt:
    errores.append('falta la contraparte')
if not vigencia_desde_txt:
    errores.append('falta vigencia_desde')
if semaforo_txt not in SEMAFOROS_VALIDOS:
    errores.append('semaforo debe ser verde, amarillo o rojo')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude registrar el contrato: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Doc = env['documents.document']
    carpeta_legal = Doc.search([('name', '=', 'Legal'), ('type', '=', 'folder'), ('folder_id', '=', False)], limit=1)
    if not carpeta_legal:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre la carpeta "Legal" en Documentos.', 'datos': {}}
    else:
        carpeta_contratos = Doc.search([('name', '=', 'Contracts'), ('type', '=', 'folder'), ('folder_id', '=', carpeta_legal.id)], limit=1)
        if not carpeta_contratos:
            carpeta_contratos = Doc.create({'name': 'Contracts', 'type': 'folder', 'folder_id': carpeta_legal.id})

        ahora = datetime.datetime.now()
        contenido = (
            'Contrato: ' + nombre_txt + '\\n' +
            'Contraparte: ' + contraparte_txt + '\\n' +
            'Vigencia: ' + vigencia_desde_txt + ' a ' + (vigencia_hasta_txt or '(sin fecha de termino)') + '\\n' +
            'Renovacion automatica: ' + ('si' if renovacion_val else 'no') + '\\n' +
            'Dias de aviso previo: ' + str(dias_aviso_val) + '\\n' +
            'Semaforo: ' + semaforo_txt + '\\n' +
            'Registrado: ' + str(ahora)
        )
        adjunto = env['ir.attachment'].create({
            'name': nombre_txt + ' - ' + str(ahora.date()) + '.txt',
            'raw': contenido,
            'mimetype': 'text/plain',
        })

        valores = {
            'name': nombre_txt,
            'folder_id': carpeta_contratos.id,
            'attachment_id': adjunto.id,
            'x_contrato_contraparte': contraparte_txt,
            'x_contrato_vigencia_desde': vigencia_desde_txt,
            'x_contrato_renovacion_automatica': renovacion_val,
            'x_contrato_dias_aviso_previo': dias_aviso_val,
            'x_contrato_semaforo': semaforo_txt,
        }
        if vigencia_hasta_txt:
            valores['x_contrato_vigencia_hasta'] = vigencia_hasta_txt

        registro = Doc.create(valores)

        ai['result'] = {
            'ok': True,
            'mensaje': 'Contrato "' + nombre_txt + '" registrado en Legal/Contracts (semaforo: ' + semaforo_txt + ').',
            'datos': {'documento_id': registro.id, 'nombre': nombre_txt, 'semaforo': semaforo_txt},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
