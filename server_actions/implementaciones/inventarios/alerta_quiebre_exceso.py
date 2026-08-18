"""Server Action: inventarios / alerta_quiebre_exceso

Solo lectura (`aprobacion: "ninguna"`). Proyecta quiebre o exceso
comparando la velocidad de consumo real (salidas de los últimos 30 días,
`stock.move` `state='done'`) contra el stock actual (`qty_available`,
nativo de `product.template`).

`horizonte_dias` pierde su `default: 14` (Odoo no soporta `default`, se
aplica a mano). Si se omite `codigo_producto`, evalúa el catálogo clase
A/B (`x_clase_abc`, custom -- corre `clasificar_abc` primero si está
vacío para todos).

**Umbral de exceso declarado, no parametrizado:** se avisa exceso
cuando el stock actual representa más de 5x el horizonte pedido (ej.
horizonte 14 dias -> exceso si hay mas de 70 dias de stock). Es un
default razonable, no una configuración real de Fase 4 que no existe
todavía.

**Bug real evitado antes de probar en vivo:** `stock.move.product_id` es
`product.product`, no `product.template` -- puenteado con
`product_tmpl_id` (mismo bug evitado en `clasificar_abc.py` e
`indicadores_confiabilidad.py`).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
MULTIPLICADOR_EXCESO = 5
VENTANA_VELOCIDAD_DIAS = 30

horizonte_val = horizonte_dias if horizonte_dias else 14
codigo_txt = (codigo_producto or '').strip()

Producto = env['product.template']
if codigo_txt:
    productos = Producto.search([('default_code', '=', codigo_txt)], limit=1)
    if not productos:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun producto con codigo "' + codigo_txt + '".', 'datos': {}}
        productos = Producto.browse()
else:
    productos = Producto.search([('x_clase_abc', 'in', ('A', 'B')), ('active', '=', True)])

if not codigo_txt and not productos:
    ai['result'] = {'ok': True, 'mensaje': 'No hay productos con clase ABC A/B todavia -- corre clasificar_abc primero.', 'datos': {'quiebres': [], 'excesos': []}}
elif productos:
    hoy = datetime.date.today()
    desde_velocidad = hoy - datetime.timedelta(days=VENTANA_VELOCIDAD_DIAS)
    Move = env['stock.move']

    quiebres = []
    excesos = []
    sin_movimiento = []
    for producto in productos:
        # stock.move.product_id es product.product, producto.id es
        # product.template -- puentear con product_tmpl_id.
        salidas = Move.search([
            ('product_id.product_tmpl_id', '=', producto.id), ('state', '=', 'done'),
            ('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'customer'),
            ('date', '>=', str(desde_velocidad) + ' 00:00:00'),
        ])
        qty_salida = sum(salidas.mapped('product_qty'))
        velocidad_diaria = qty_salida / VENTANA_VELOCIDAD_DIAS

        if velocidad_diaria <= 0:
            sin_movimiento.append({'producto_id': producto.id, 'sku': producto.default_code or False})
            continue

        dias_de_stock = producto.qty_available / velocidad_diaria
        fila = {'producto_id': producto.id, 'sku': producto.default_code or False, 'nombre': producto.name, 'stock_actual': producto.qty_available, 'velocidad_diaria': round(velocidad_diaria, 2), 'dias_de_stock_proyectados': round(dias_de_stock, 1)}

        if dias_de_stock < horizonte_val:
            quiebres.append(fila)
        elif dias_de_stock > horizonte_val * MULTIPLICADOR_EXCESO:
            excesos.append(fila)

    ai['result'] = {
        'ok': True,
        'mensaje': (
            'Proyeccion a ' + str(horizonte_val) + ' dias sobre ' + str(len(productos)) + ' producto(s): ' +
            str(len(quiebres)) + ' en riesgo de quiebre, ' + str(len(excesos)) + ' en exceso. ' +
            (str(len(sin_movimiento)) + ' sin salidas en los ultimos ' + str(VENTANA_VELOCIDAD_DIAS) + ' dias (no se puede proyectar velocidad). ' if sin_movimiento else '')
        ),
        'datos': {'horizonte_dias': horizonte_val, 'quiebres': quiebres, 'excesos': excesos, 'sin_movimiento_reciente': sin_movimiento},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
