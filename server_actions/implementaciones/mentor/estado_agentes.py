"""Server Action: mentor / estado_agentes

Undécima herramienta con lógica real. Solo lectura: lista los agentes de
IA del tenant, si están activos (el kill-switch de un agente puntual es
archivarlo — `active=False` — no solo la guarda de licencia global) y su
última actividad real.

"Última actividad" NO es `write_date` (que solo marca la última vez que
se editó la CONFIGURACIÓN del agente, no que respondió a alguien) — se
mide buscando el último `mail.message` cuyo autor es el `partner_id` del
agente (cada `ai.agent` tiene un partner que firma sus respuestas en el
chat). Es una aproximación honesta a "cuándo habló por última vez", no
un invento.

Sin parámetros de entrada — el esquema del catálogo no declara ninguno.

Ya existía una versión de esta herramienta del piloto original (15-ago-2026,
`ir.actions.server` id 1446, antes de que esta convención de doble prueba
existiera formalmente) — esta reemplaza esa implementación con la lógica
real de "última actividad" y el resto de las convenciones vigentes.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
Agente = env['ai.agent']
Mensaje = env['mail.message']

agentes = Agente.with_context(active_test=False).search([])
filas = []
for a in agentes:
    ultima = ''
    if a.partner_id:
        msg = Mensaje.search([('author_id', '=', a.partner_id.id)], order='create_date desc', limit=1)
        if msg:
            ultima = str(msg.create_date)
    filas.append({
        'nombre': a.name,
        'activo': a.active,
        'ultima_actividad': ultima or 'sin actividad registrada',
    })

activos = [f for f in filas if f['activo']]
inactivos = [f for f in filas if not f['activo']]

ai['result'] = {
    'ok': True,
    'mensaje': str(len(activos)) + ' agente(s) activo(s), ' + str(len(inactivos)) + ' archivado(s) de ' + str(len(filas)) + ' en total.',
    'datos': {'agentes': filas, 'total': len(filas), 'activos': len(activos), 'archivados': len(inactivos)},
}
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
