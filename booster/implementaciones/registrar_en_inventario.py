"""Server Action: booster / registrar_en_inventario

Registra en `x_booster_inventario` un registro que Booster acaba de crear
(o que detecto como preexistente en el camino C). Es la pieza que hace
posible la invariante "lo nuestro se apaga; lo suyo jamas": sin este
registro, el kill-switch no sabe que apagar.

Idempotente por (modelo, res_id): si ya esta inventariado, actualiza la
etiqueta/receta/nombre pero no duplica la fila. Esto importa porque las
recetas pueden reintentarse (smoke test en rojo -> reintento automatico
segun el spec) y no deben dejar filas repetidas.

`x_archivable` se calcula aca, una vez, leyendo si el modelo tiene campo
`active`: el kill-switch despues no tiene que adivinarlo. Verificado en
vivo que `'active' in env[modelo]._fields` funciona en el sandbox (es
acceso a atributo + `in`, no getattr -- ver BUILTINS_NO_DISPONIBLES).

Si el registro referido no existe (id equivocado), se rechaza: el
inventario no puede apuntar a fantasmas.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
ETIQUETAS_VALIDAS = ('creado_por_booster', 'preexistente')

modelo_txt = (modelo or '').strip()
etiqueta_txt = (etiqueta or '').strip()
nombre_txt = (nombre or '').strip()
receta_txt = (receta or '').strip()

errores = []
if not modelo_txt:
    errores.append('falta el modelo')
elif modelo_txt not in env:
    errores.append('el modelo "' + modelo_txt + '" no existe en este Odoo')
if not res_id:
    errores.append('falta res_id')
if etiqueta_txt not in ETIQUETAS_VALIDAS:
    errores.append('etiqueta debe ser creado_por_booster o preexistente')

registro_ref = None
if not errores:
    registro_ref = env[modelo_txt].browse(res_id)
    if not registro_ref.exists():
        errores.append('no existe ningun registro id ' + str(res_id) + ' en ' + modelo_txt)

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude registrar en el inventario: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Inv = env['x_booster_inventario']
    archivable = 'active' in env[modelo_txt]._fields
    if not nombre_txt:
        nombre_txt = registro_ref.display_name if 'display_name' in registro_ref._fields else (modelo_txt + ' #' + str(res_id))

    existente = Inv.search([('x_modelo', '=', modelo_txt), ('x_res_id', '=', res_id)], limit=1)
    valores = {
        'x_name': nombre_txt,
        'x_modelo': modelo_txt,
        'x_res_id': res_id,
        'x_nombre': nombre_txt,
        'x_etiqueta': etiqueta_txt,
        'x_receta': receta_txt,
        'x_archivable': archivable,
    }
    if existente:
        existente.write(valores)
        fila = existente
        accion = 'actualizado'
    else:
        valores['x_fecha'] = datetime.datetime.now()
        valores['x_estado'] = 'activo'
        fila = Inv.create(valores)
        accion = 'registrado'

    ai['result'] = {
        'ok': True,
        'mensaje': nombre_txt + ' (' + modelo_txt + ' #' + str(res_id) + ') ' + accion + ' en el inventario como ' + etiqueta_txt + '.' + ('' if archivable else ' Nota: este modelo no soporta archivar, el kill-switch lo reportara pero no podra apagarlo.'),
        'datos': {'inventario_id': fila.id, 'modelo': modelo_txt, 'res_id': res_id, 'etiqueta': etiqueta_txt, 'archivable': archivable, 'accion': accion},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
