"""Server Action: inventarios / clasificar_abc

`aprobacion: "confirmar"`. Calcula la clasificación ABC (Pareto
80/15/5 sobre valor de consumo -- convención estándar de gestión de
inventarios, no inventada) de los SKU con movimiento de salida en el
período, y la persiste en el campo custom `x_clase_abc` de
`product.template` (creado por `instalar_campos_inventarios.py` -- no
existe de forma nativa en Odoo, confirmado con `fields_get`).

`periodo` (`$ref` a `$defs/periodo`, objeto `{desde, hasta}`) llega
saneado como `periodo_desde`/`periodo_hasta` (Odoo no soporta objetos
anidados en `ai_tool_schema`, ver `esquemas_odoo.py`).

`forzar_recalculo` (default false, Odoo no soporta `default`): por
default, un producto que YA tiene `x_clase_abc` fijado no se toca --
solo se clasifican los que todavía no tienen clase. Con
`forzar_recalculo=true`, se reclasifica TODO el catálogo con movimiento
en el período, sin importar si ya tenía una clase.

Valor de consumo = suma de `product_qty * standard_price` de los
`stock.move` de salida (`location_id.usage='internal'`,
`location_dest_id.usage='customer'`, `state='done'`) en el período.

**Bug real evitado antes de probar en vivo:** `stock.move.product_id` es
`product.product` (variante), NO `product.template` (donde vive
`x_clase_abc`) -- confirmado con `fields_get`, no asumido. Agrupar por
`m.product_id.id` directo compararía ids de dos modelos distintos (casi
nunca coinciden) y el `Producto.browse(pid)` posterior habría fallado en
silencio o tocado el producto equivocado. Se puentea con
`product_id.product_tmpl_id.id`.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
desde_txt = (periodo_desde or '').strip()
hasta_txt = (periodo_hasta or '').strip()
forzar_val = bool(forzar_recalculo) if forzar_recalculo is not None else False

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
elif desde_dt > hasta_dt:
    ai['result'] = {'ok': False, 'mensaje': 'periodo.desde no puede ser posterior a periodo.hasta.', 'datos': {}}
else:
    Move = env['stock.move']
    salidas = Move.search([
        ('state', '=', 'done'),
        ('location_id.usage', '=', 'internal'),
        ('location_dest_id.usage', '=', 'customer'),
        ('date', '>=', str(desde_dt) + ' 00:00:00'), ('date', '<=', str(hasta_dt) + ' 23:59:59'),
    ])

    valor_por_producto = {}
    for m in salidas:
        # stock.move.product_id es product.product (variante) -- los campos
        # custom (x_clase_abc) viven en product.template, hay que puentear
        # con product_tmpl_id o se estaria comparando ids de modelos distintos.
        pid = m.product_id.product_tmpl_id.id
        valor = m.product_qty * m.product_id.standard_price
        valor_por_producto[pid] = valor_por_producto.get(pid, 0.0) + valor

    if not valor_por_producto:
        ai['result'] = {'ok': True, 'mensaje': 'No hubo salidas de stock en ese periodo -- nada que clasificar.', 'datos': {'clasificados': [], 'sin_cambios': []}}
    else:
        ranking = sorted(valor_por_producto.items(), key=lambda kv: -kv[1])
        valor_total = sum(v for _, v in ranking)

        Producto = env['product.template']
        clasificados = []
        sin_cambios = []
        acumulado = 0.0
        for pid, valor in ranking:
            acumulado += valor
            pct_acumulado = (acumulado / valor_total * 100) if valor_total else 0.0
            if pct_acumulado <= 80:
                clase = 'A'
            elif pct_acumulado <= 95:
                clase = 'B'
            else:
                clase = 'C'

            producto = Producto.browse(pid)
            if not forzar_val and producto.x_clase_abc:
                sin_cambios.append({'producto_id': pid, 'sku': producto.default_code or False, 'clase_existente': producto.x_clase_abc})
                continue

            producto.write({'x_clase_abc': clase})
            clasificados.append({'producto_id': pid, 'sku': producto.default_code or False, 'nombre': producto.name, 'valor_consumo': round(valor, 2), 'clase': clase})

        conteo_clases = {}
        for c in clasificados:
            conteo_clases[c['clase']] = conteo_clases.get(c['clase'], 0) + 1

        ai['result'] = {
            'ok': True,
            'mensaje': (
                str(len(clasificados)) + ' producto(s) clasificado(s) (' +
                ', '.join(k + '=' + str(v) for k, v in sorted(conteo_clases.items())) + '). ' +
                str(len(sin_cambios)) + ' se dejaron sin tocar por ya tener clase (usa forzar_recalculo=true para reclasificarlos).'
            ),
            'datos': {'clasificados': clasificados, 'sin_cambios': sin_cambios, 'periodo': {'desde': str(desde_dt), 'hasta': str(hasta_dt)}},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
