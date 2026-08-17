"""Server Action: rrhh / avanzar_etapa

Mueve un candidato a la siguiente etapa SOLO si los requisitos de la
etapa ACTUAL están cumplidos (`aprobacion: "confirmar"`). `hr.recruitment.stage`
tiene un campo real `requirements` (texto, confirmado con `fields_get`) --
si la etapa actual del candidato tiene ese texto lleno, hace falta que
venga `verificacion` (qué se comprobó) para poder avanzar; si
`requirements` está vacío, no hay nada que exigir y se avanza igual,
pero SIEMPRE queda constancia en el chatter del candidato
(`message_post`, `hr.applicant` hereda `mail.thread` -- confirmado con
`fields_get`) de qué se verificó y quién lo hizo, sea el requisito
explícito o no ("deja constancia de que se verifico", texto del
catálogo).

Si falta el requisito, `ok: false` con el detalle -- NO avanza (ni
siquiera parcialmente).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
etapa_destino_txt = (etapa_destino or '').strip()
verificacion_txt = (verificacion or '').strip()

Applicant = env['hr.applicant']
candidato = Applicant.browse(candidato_id) if candidato_id else Applicant.browse()

if not candidato.exists():
    ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun candidato con id ' + str(candidato_id) + '.', 'datos': {}}
elif not etapa_destino_txt:
    ai['result'] = {'ok': False, 'mensaje': 'Falta etapa_destino.', 'datos': {}}
else:
    Etapa = env['hr.recruitment.stage']
    destino = Etapa.search([('name', 'ilike', etapa_destino_txt)], limit=5)

    if not destino:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ninguna etapa que coincida con "' + etapa_destino_txt + '".', 'datos': {}}
    elif len(destino) > 1:
        nombres = [e.name + ' (id ' + str(e.id) + ')' for e in destino]
        ai['result'] = {'ok': False, 'mensaje': 'Hay varias etapas que coinciden con "' + etapa_destino_txt + '". Precisa cual: ' + '; '.join(nombres), 'datos': {}}
    else:
        etapa_actual = candidato.stage_id
        requisito_txt = (etapa_actual.requirements or '').strip() if etapa_actual else ''

        if requisito_txt and not verificacion_txt:
            ai['result'] = {
                'ok': False,
                'mensaje': 'No puedo avanzar a "' + destino.name + '": la etapa actual ("' + (etapa_actual.name if etapa_actual else 'sin etapa') + '") exige verificar "' + requisito_txt + '" antes de avanzar, y no llego el parametro verificacion.',
                'datos': {'requisito_pendiente': requisito_txt},
            }
        else:
            candidato.write({'stage_id': destino.id})
            nota = (
                'Avance de etapa: "' + (etapa_actual.name if etapa_actual else 'sin etapa') + '" -> "' + destino.name + '". ' +
                ('Verificacion: ' + verificacion_txt if verificacion_txt else 'Sin requisito explicito en la etapa anterior.')
            )
            candidato.message_post(body=nota)

            ai['result'] = {
                'ok': True,
                'mensaje': 'Candidato "' + (candidato.partner_name or str(candidato.id)) + '" avanzado a "' + destino.name + '". Constancia dejada en el expediente.',
                'datos': {'candidato_id': candidato.id, 'etapa_anterior': etapa_actual.name if etapa_actual else False, 'etapa_nueva': destino.name},
            }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
