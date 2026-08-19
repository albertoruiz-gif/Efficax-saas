"""Server Action: booster / killswitch_inventario

Kill-switch capa 2 de Booster (spec §Regla de cancelacion): archiva
(`active=False`) TODO lo inventariado como 'creado_por_booster' y
NUNCA toca lo 'preexistente'. Es la materializacion de "lo nuestro se
apaga; lo suyo jamas". 'reactivar' lo revierte (reconexion tras pago).
'listar' es solo lectura, para el reporte al dueno.

## Invariantes (las que importan de verdad)

1. Lo 'preexistente' NO se toca jamas -- ni en apagar ni en reactivar.
   Se filtra por etiqueta ANTES de cualquier write. Es la linea de
   negocio completa: si un dia el filtro fallara, Booster estaria
   tocando el Odoo que el cliente tenia antes de conocernos.
2. 'apagar' y 'reactivar' exigen `confirmar=True` explicito. Sin eso
   devuelven que falta confirmacion y no hacen nada. El LLM no puede
   poner confirmar=true por su cuenta: el topic se lo prohibe salvo
   confirmacion explicita de la persona -- y aunque lo hiciera, la
   guarda de licencia sigue siendo la capa 1 independiente.
3. Lo no archivable (x_archivable=False) se salta y se REPORTA, no se
   finge que se apago.
4. Cada fila actualiza su x_estado, asi 'listar' despues del apagado
   dice la verdad de lo que paso.

## Por que `with_context(active_test=False)` en reactivar

Al reactivar, los registros estan archivados: sin active_test=False,
`browse().exists()` los ve pero un `search` no -- se usa browse directo
por id (que es lo que guarda el inventario) asi que no hay problema,
pero se deja explicito para quien lo lea.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
ACCIONES_VALIDAS = ('listar', 'apagar', 'reactivar')
accion_txt = (accion or '').strip().lower()
confirmado = bool(confirmar)

Inv = env['x_booster_inventario']

if accion_txt not in ACCIONES_VALIDAS:
    ai['result'] = {'ok': False, 'mensaje': 'accion debe ser listar, apagar o reactivar.', 'datos': {}}

elif accion_txt == 'listar':
    filas = Inv.search([], order='x_etiqueta, x_modelo, x_res_id')
    creados = [f for f in filas if f.x_etiqueta == 'creado_por_booster']
    preexist = [f for f in filas if f.x_etiqueta == 'preexistente']
    def _fila(f):
        return {'modelo': f.x_modelo, 'res_id': f.x_res_id, 'nombre': f.x_nombre or '', 'receta': f.x_receta or '', 'estado': f.x_estado or '', 'archivable': bool(f.x_archivable)}
    ai['result'] = {
        'ok': True,
        'mensaje': str(len(creados)) + ' registro(s) creados por Booster y ' + str(len(preexist)) + ' preexistente(s) (prohibido tocar).',
        'datos': {'creados_por_booster': [_fila(f) for f in creados], 'preexistentes': [_fila(f) for f in preexist]},
    }

elif not confirmado:
    ai['result'] = {
        'ok': False,
        'mensaje': 'La accion "' + accion_txt + '" requiere confirmacion explicita (confirmar=true). No se hizo nada. Confirma con la persona antes de reintentar.',
        'datos': {'accion': accion_txt, 'confirmado': False},
    }

else:
    # INVARIANTE 1: solo lo creado por Booster. Lo preexistente ni se carga.
    objetivo = Inv.search([('x_etiqueta', '=', 'creado_por_booster')])
    nuevo_active = (accion_txt == 'reactivar')
    nuevo_estado = 'activo' if nuevo_active else 'archivado'

    hechos = []
    saltados = []
    fantasmas = []
    for f in objetivo:
        if not f.x_archivable:
            saltados.append({'modelo': f.x_modelo, 'res_id': f.x_res_id, 'nombre': f.x_nombre or '', 'motivo': 'el modelo no soporta archivar'})
            continue
        if f.x_modelo not in env:
            fantasmas.append({'modelo': f.x_modelo, 'res_id': f.x_res_id, 'motivo': 'modelo ya no existe'})
            continue
        rec = env[f.x_modelo].with_context(active_test=False).browse(f.x_res_id)
        if not rec.exists():
            fantasmas.append({'modelo': f.x_modelo, 'res_id': f.x_res_id, 'motivo': 'registro ya no existe'})
            continue
        if rec.active != nuevo_active:
            rec.write({'active': nuevo_active})
        f.write({'x_estado': nuevo_estado})
        hechos.append({'modelo': f.x_modelo, 'res_id': f.x_res_id, 'nombre': f.x_nombre or ''})

    preexist_n = Inv.search_count([('x_etiqueta', '=', 'preexistente')])
    verbo = 'reactivado(s)' if nuevo_active else 'archivado(s)'
    ai['result'] = {
        'ok': True,
        'mensaje': (
            str(len(hechos)) + ' registro(s) ' + verbo + '. ' +
            (str(len(saltados)) + ' saltado(s) por no ser archivables. ' if saltados else '') +
            (str(len(fantasmas)) + ' ya no existian. ' if fantasmas else '') +
            str(preexist_n) + ' preexistente(s) NO tocado(s), como corresponde.'
        ),
        'datos': {'accion': accion_txt, 'hechos': hechos, 'saltados': saltados, 'fantasmas': fantasmas, 'preexistentes_intactos': preexist_n},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
