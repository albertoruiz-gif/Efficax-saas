"""Server Action: rrhh / resumen_candidato

Solo lectura (`aprobacion: "ninguna"`). El catálogo dice "resume un CV
contra los requisitos del puesto: fortalezas, brechas y preguntas
sugeridas" -- pero esta Server Action NO puede leer el contenido de un
PDF/Word adjunto (`hr.applicant.attachment_ids` son `ir.attachment`
binarios; el sandbox de IA no tiene `open()` ni ninguna librería de
parseo de documentos, confirmado en `guarda_llave.py`: solo
`env`/`ai`/`datetime`/`UserError` están disponibles). Por eso esta
herramienta hace lo que SÍ puede hacer honestamente: junta los datos
estructurados reales (notas del reclutador, descripción/requisitos del
puesto, puntaje de matching, evaluación) y se los entrega al agente de
IA -- es el agente (no este código determinista) quien redacta
fortalezas/brechas/preguntas a partir de esos datos, igual que
`calcular_kpi.py` entrega el número + fórmula y deja que el agente arme
el mensaje final. Inventar un resumen de un CV que nunca se leyó
rompería la regla "nunca inventar" del resto del catálogo.

Campos reales verificados con `fields_get`: `partner_name`, `email_from`,
`applicant_notes` (html), `matching_score` (integer), `priority`
(selection, "Evaluation" -- estrellas), `availability` (date),
`job_id` (m2o a `hr.job`).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
Applicant = env['hr.applicant']
candidato = Applicant.browse(candidato_id) if candidato_id else Applicant.browse()

if not candidato.exists():
    ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun candidato con id ' + str(candidato_id) + '.', 'datos': {}}
else:
    Job = env['hr.job']
    puesto = Job.browse(puesto_id) if puesto_id else Job.browse()

    if not puesto.exists():
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun puesto con id ' + str(puesto_id) + '.', 'datos': {}}
    else:
        avisos = []
        if candidato.job_id and candidato.job_id.id != puesto.id:
            avisos.append('el candidato esta postulando a "' + candidato.job_id.name + '", no a "' + puesto.name + '" -- verifica que sea el puesto correcto')

        cant_adjuntos = len(candidato.attachment_ids)
        if cant_adjuntos:
            avisos.append(str(cant_adjuntos) + ' archivo(s) adjunto(s) (posible CV) -- esta herramienta NO puede leer su contenido, solo confirma que existen')

        ai['result'] = {
            'ok': True,
            'mensaje': 'Datos del candidato y del puesto listos -- redacta el resumen (fortalezas/brechas/preguntas) a partir de esto, no inventes datos que no esten aca.',
            'datos': {
                'candidato': {
                    'id': candidato.id,
                    'nombre': candidato.partner_name or False,
                    'email': candidato.email_from or False,
                    'notas_reclutador': candidato.applicant_notes or False,
                    'puntaje_matching': candidato.matching_score,
                    'evaluacion_estrellas': candidato.priority or False,
                    'disponibilidad': str(candidato.availability) if candidato.availability else False,
                    'cantidad_adjuntos': cant_adjuntos,
                },
                'puesto': {
                    'id': puesto.id,
                    'titulo': puesto.name,
                    'requisitos_descripcion': puesto.description or False,
                },
                'avisos': avisos,
            },
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
