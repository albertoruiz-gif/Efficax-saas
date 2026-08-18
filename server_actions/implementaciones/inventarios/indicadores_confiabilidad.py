"""Server Action: inventarios / indicadores_confiabilidad

Solo lectura (`aprobacion: "ninguna"`). Cuatro indicadores del período:
cobertura, valor de ajustes, quiebres/excesos -- calculados de datos
reales -- y **exactitud declarada como NO calculable todavía**, honesto
en vez de inventado.

**Por qué exactitud queda pendiente:** cuando se aplica un ajuste
(`action_apply_inventory()`), Odoo limpia `inventory_quantity`/
`inventory_diff_quantity` del quant -- no queda ningún registro
persistente de "cuántos conteos cayeron dentro de tolerancia" una vez
aplicados. `registrar_conteo.py` devuelve esa info en el momento pero no
la guarda en ningún lado (no existe un modelo de "log de conteos" en
este tenant). Sin ese registro, calcular exactitud histórica sería
inventar un número -- se declara explícito como pendiente en vez de
simularlo.

**Cobertura y valor de ajustes** SÍ son calculables con datos reales:
Odoo enruta el contrapartida de cualquier ajuste aplicado a través de la
ubicación `usage='inventory'` ("Inventory Loss"/"Inventory adjustment")
-- son `stock.move` reales, fechables, confirmados con `fields_get`.
**Aviso verificado en vivo (18-ago-2026):** ese mismo mecanismo es el
que usa Odoo para la carga INICIAL de stock de un catálogo nuevo -- en
este tenant, "valor de ajustes" incluye tanto la carga inicial masiva
del catálogo HSK (37 productos, ago-2026) como un ajuste real de
cobranza de conteo (-5 unidades de HSK-0039). El número es correcto para
la definición técnica de "ajuste" de Odoo, pero NO distingue "carga
inicial" de "corrección de conteo cíclico" -- si eso importa, hay que
acotar el período a después de la puesta en marcha del inventario.

**Quiebres/excesos** son una FOTO del momento actual (no puede ser
histórica del período sin el mismo problema del log que no existe):
quiebre = catálogo con `qty_available <= 0` y con movimiento de salida
en el período (hubo demanda real, no es solo un SKU descontinuado);
exceso = stock actual que representa más de 90 días de consumo a la
velocidad del período (umbral declarado, no parametrizado en ningún
lado todavía).

**Bug real evitado antes de probar en vivo:** `stock.move.product_id` es
`product.product`, no `product.template` -- mismo puente con
`product_tmpl_id` que en `clasificar_abc.py`, necesario para comparar
contra el catálogo (`product.template`) sin mezclar ids de modelos
distintos.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
desde_txt = (periodo_desde or '').strip()
hasta_txt = (periodo_hasta or '').strip()

try:
    desde_dt = datetime.datetime.strptime(desde_txt, '%Y-%m-%d').date() if desde_txt else False
except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
    desde_dt = False
try:
    hasta_dt = datetime.datetime.strptime(hasta_txt, '%Y-%m-%d').date() if hasta_txt else False
except:  # noqa: E722
    hasta_dt = False

if not desde_dt or not hasta_dt:
    ai['result'] = {'ok': False, 'mensaje': 'periodo.desde y periodo.hasta deben ser fechas validas en formato AAAA-MM-DD.', 'datos': {}}
else:
    dias_periodo = max((hasta_dt - desde_dt).days + 1, 1)
    Move = env['stock.move']

    ajustes = Move.search([
        ('state', '=', 'done'),
        '|', ('location_id.usage', '=', 'inventory'), ('location_dest_id.usage', '=', 'inventory'),
        ('date', '>=', str(desde_dt) + ' 00:00:00'), ('date', '<=', str(hasta_dt) + ' 23:59:59'),
    ])
    # ajustes.product_id es product.product -- puentear con product_tmpl_id
    # para comparar contra el catalogo de product.template.
    productos_ajustados = set(ajustes.mapped('product_id.product_tmpl_id.id'))
    valor_ajustes = sum(abs(m.product_qty * m.product_id.standard_price) for m in ajustes)

    Producto = env['product.template']
    total_activos = Producto.search_count([('active', '=', True)])
    cobertura_pct = (len(productos_ajustados) / total_activos * 100) if total_activos else 0.0

    salidas = Move.search([
        ('state', '=', 'done'), ('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'customer'),
        ('date', '>=', str(desde_dt) + ' 00:00:00'), ('date', '<=', str(hasta_dt) + ' 23:59:59'),
    ])
    salida_por_producto = {}
    for m in salidas:
        pid = m.product_id.product_tmpl_id.id
        salida_por_producto[pid] = salida_por_producto.get(pid, 0.0) + m.product_qty

    quiebres = []
    excesos = []
    for pid, qty_salida in salida_por_producto.items():
        producto = Producto.browse(pid)
        velocidad_diaria = qty_salida / dias_periodo
        if producto.qty_available <= 0:
            quiebres.append({'producto_id': pid, 'sku': producto.default_code or False, 'nombre': producto.name})
        elif velocidad_diaria > 0 and (producto.qty_available / velocidad_diaria) > 90:
            excesos.append({'producto_id': pid, 'sku': producto.default_code or False, 'nombre': producto.name, 'dias_de_stock': round(producto.qty_available / velocidad_diaria, 1)})

    ai['result'] = {
        'ok': True,
        'mensaje': (
            'Periodo ' + str(desde_dt) + ' a ' + str(hasta_dt) + ': cobertura ' + str(round(cobertura_pct, 1)) + '% del catalogo activo (' +
            str(len(productos_ajustados)) + ' de ' + str(total_activos) + '), valor de ajustes S/' + str(round(valor_ajustes, 2)) + ', ' +
            str(len(quiebres)) + ' quiebre(s), ' + str(len(excesos)) + ' exceso(s). ' +
            'Exactitud: NO calculable todavia (no hay un log persistente de conteos aplicados en este tenant, ver docstring).'
        ),
        'datos': {
            'periodo': {'desde': str(desde_dt), 'hasta': str(hasta_dt)},
            'cobertura_pct': round(cobertura_pct, 1), 'productos_ajustados': len(productos_ajustados), 'total_catalogo_activo': total_activos,
            'valor_ajustes': round(valor_ajustes, 2), 'quiebres': quiebres, 'excesos': excesos,
            'exactitud': None,
        },
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
