"""Server Action: rrhh / file_contratacion

Guarda una pieza del proceso (CV, filtro, cuadro de méritos, resultado
de entrevista, evaluación, puntaje final, oferta, respuesta, onboarding)
en el expediente del candidato -- app Documentos (`aprobacion: "ninguna"`,
es solo archivar, no decide nada). Mismo mecanismo verificado en vivo con
`registrar_decision.py` de Mentor: carpeta (`documents.document`,
`type='folder'`) + `ir.attachment` con el contenido + `documents.document`
que lo referencia via `attachment_id`.

A diferencia de `registrar_decision.py` (una sola carpeta fija ya creada
por Booster), acá no existe todavía ninguna carpeta de reclutamiento --
la crea esta misma herramienta la primera vez que se usa (carpeta raíz
"Reclutamiento" + una subcarpeta por candidato), porque el expediente por
candidato es responsabilidad de esta herramienta, no de una fase de
Booster que ya lo haya dejado listo.

`adjunto_id` (opcional): si ya existe un `ir.attachment` real (ej. el CV
subido por el candidato), se referencia directo en vez de crear uno
nuevo desde `contenido` -- así no se duplica el archivo original.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
TIPOS_VALIDOS = ('cv', 'filtro', 'cuadro_meritos', 'resultado_entrevista', 'evaluacion', 'puntaje_final', 'oferta', 'respuesta_oferta', 'onboarding')
NOMBRE_CARPETA_RAIZ = 'Reclutamiento'

tipo_txt = (tipo_pieza or '').strip()
contenido_txt = (contenido or '').strip()

Applicant = env['hr.applicant']
candidato = Applicant.browse(candidato_id) if candidato_id else Applicant.browse()

errores = []
if not candidato.exists():
    errores.append('no encontre ningun candidato con id ' + str(candidato_id))
if tipo_txt not in TIPOS_VALIDOS:
    errores.append('tipo_pieza debe ser una de: ' + ', '.join(TIPOS_VALIDOS))
if not contenido_txt and not adjunto_id:
    errores.append('falta contenido (o un adjunto_id existente)')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude archivar la pieza: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Doc = env['documents.document']
    carpeta_raiz = Doc.search([('name', '=', NOMBRE_CARPETA_RAIZ), ('type', '=', 'folder'), ('folder_id', '=', False)], limit=1)
    if not carpeta_raiz:
        carpeta_raiz = Doc.create({'name': NOMBRE_CARPETA_RAIZ, 'type': 'folder'})

    nombre_candidato = candidato.partner_name or ('Candidato ' + str(candidato.id))
    carpeta_candidato = Doc.search([('name', '=', nombre_candidato), ('type', '=', 'folder'), ('folder_id', '=', carpeta_raiz.id)], limit=1)
    if not carpeta_candidato:
        carpeta_candidato = Doc.create({'name': nombre_candidato, 'type': 'folder', 'folder_id': carpeta_raiz.id})

    ahora = datetime.datetime.now()
    nombre_pieza = tipo_txt + ' - ' + str(ahora.date())

    if adjunto_id:
        Attachment = env['ir.attachment']
        adjunto = Attachment.browse(adjunto_id)
        if not adjunto.exists():
            ai['result'] = {'ok': False, 'mensaje': 'adjunto_id ' + str(adjunto_id) + ' no corresponde a ningun archivo existente.', 'datos': {}}
            adjunto = False
    else:
        adjunto = env['ir.attachment'].create({
            'name': nombre_pieza + '.txt',
            'raw': contenido_txt,
            'mimetype': 'text/plain',
        })

    if adjunto:
        registro = Doc.create({
            'name': nombre_pieza,
            'folder_id': carpeta_candidato.id,
            'attachment_id': adjunto.id,
        })
        ai['result'] = {
            'ok': True,
            'mensaje': 'Pieza "' + tipo_txt + '" archivada en el expediente de ' + nombre_candidato + '.',
            'datos': {'documento_id': registro.id, 'candidato_id': candidato.id, 'tipo_pieza': tipo_txt},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
