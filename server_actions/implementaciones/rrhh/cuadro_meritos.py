"""Server Action: rrhh / cuadro_meritos

Solo lectura y cálculo (`aprobacion: "ninguna"`) -- la decisión es del
dueño/gerente, esta herramienta arma el ranking a partir de datos reales,
no decide. Ordena los candidatos de un puesto por `matching_score`
(entero, 0-100) y `priority` ("Evaluation", estrellas 0-3) -- ambos
campos reales confirmados con `fields_get`, no un puntaje propio
inventado.

"Descartados" en Odoo Recruitment = candidatos archivados (`active =
False`, con o sin `refuse_reason_id`) -- confirmado como el patrón
estándar del módulo (no hay un campo `descartado` explícito). Por
default una búsqueda normal ya excluye los archivados; para
`incluir_descartados=True` hay que forzar `context={'active_test': False}`
o no aparecen.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
Job = env['hr.job']
puesto = Job.browse(puesto_id) if puesto_id else Job.browse()

if not puesto.exists():
    ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun puesto con id ' + str(puesto_id) + '.', 'datos': {}}
else:
    incluir_desc = bool(incluir_descartados)
    Applicant = env['hr.applicant']
    if incluir_desc:
        candidatos = Applicant.with_context(active_test=False).search([('job_id', '=', puesto.id)])
    else:
        candidatos = Applicant.search([('job_id', '=', puesto.id)])

    filas = []
    for c in candidatos:
        filas.append({
            'candidato_id': c.id,
            'nombre': c.partner_name or ('candidato ' + str(c.id)),
            'etapa': c.stage_id.name if c.stage_id else False,
            'puntaje_matching': c.matching_score,
            'evaluacion_estrellas': c.priority or '0',
            'descartado': not c.active,
            'motivo_descarte': c.refuse_reason_id.name if (not c.active and c.refuse_reason_id) else False,
        })

    # Ranking: puntaje de matching primero, estrellas de evaluacion como desempate.
    filas.sort(key=lambda f: (f['puntaje_matching'] or 0, int(f['evaluacion_estrellas'] or '0')), reverse=True)
    for i, f in enumerate(filas, start=1):
        f['posicion'] = i

    ai['result'] = {
        'ok': True,
        'mensaje': 'Cuadro de meritos de "' + puesto.name + '": ' + str(len(filas)) + ' candidato(s)' + (' (incluye descartados)' if incluir_desc else '') + '.',
        'datos': {'puesto_id': puesto.id, 'incluir_descartados': incluir_desc, 'candidatos': filas},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
