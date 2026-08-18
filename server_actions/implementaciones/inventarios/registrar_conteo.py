"""Server Action: inventarios / registrar_conteo

`aprobacion: "ninguna"`. Registra lo contado por SKU usando el
mecanismo NATIVO real de Odoo para conteos físicos:
`stock.quant.inventory_quantity` (campo "Contado") -- al escribirlo,
Odoo calcula solo `inventory_diff_quantity` ("Diferencia"), confirmado
en vivo que existe y se comporta así. **No llama `action_apply_inventory()`
-- eso es trabajo de `ajustar_inventario.py`**, tal cual pide el
catálogo ("No ajusta stock por si sola").

`conteos` es un array de objetos en el catálogo -- Odoo no soporta
arrays de objetos en `ai_tool_schema` (ver `esquemas_odoo.py`), así que
llega saneado como `conteos_json` (string JSON, se parsea con el módulo
`json`, disponible en el sandbox).

**Tolerancia dentro/fuera:** no hay ningún parámetro de Fase 4 real para
esto en este tenant -- se usa un default explícito de ±2% de la
cantidad teórica (o ±1 unidad si la cantidad teórica es 0), declarado en
la respuesta, no oculto.

**Simplificación declarada:** si un producto tiene más de una ubicación
interna con stock (multi-almacén), o ninguna, esta herramienta NO
adivina cuál corregir -- lo reporta como "ambiguo" para resolución
manual, en vez de aplicar un conteo al lugar equivocado.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
TOLERANCIA_PCT = 0.02

fecha_txt = (fecha or '').strip()

try:
    fecha_dt = datetime.datetime.strptime(fecha_txt, '%Y-%m-%d').date() if fecha_txt else False
except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
    fecha_dt = False

lista_conteos = []
if conteos_json:
    try:
        lista_conteos = json.loads(conteos_json)
    except:  # noqa: E722
        lista_conteos = []

if not fecha_dt:
    ai['result'] = {'ok': False, 'mensaje': 'fecha debe ser una fecha valida en formato AAAA-MM-DD.', 'datos': {}}
elif not lista_conteos:
    ai['result'] = {'ok': False, 'mensaje': 'conteos no puede estar vacio o no se pudo interpretar como lista.', 'datos': {}}
else:
    Producto = env['product.template']
    Quant = env['stock.quant']
    registrados = []
    ambiguos = []
    no_encontrados = []

    for item in lista_conteos:
        codigo_txt = str(item.get('codigo_producto', '')).strip()
        cantidad_val = item.get('cantidad_contada')

        producto = Producto.search([('default_code', '=', codigo_txt)], limit=1)
        if not producto:
            no_encontrados.append(codigo_txt)
            continue

        # stock.quant.product_id es product.product, producto.id es
        # product.template -- puentear con product_tmpl_id (mismo bug
        # evitado que en clasificar_abc.py).
        quants = Quant.search([('product_id.product_tmpl_id', '=', producto.id), ('location_id.usage', '=', 'internal')])
        if len(quants) != 1:
            ambiguos.append({'sku': codigo_txt, 'motivo': str(len(quants)) + ' ubicacion(es) interna(s) con stock -- no se puede aplicar un conteo unico sin ambiguedad'})
            continue

        quant = quants
        cantidad_teorica = quant.quantity
        quant.write({'inventory_quantity': cantidad_val})
        diferencia = quant.inventory_diff_quantity

        umbral = max(abs(cantidad_teorica) * TOLERANCIA_PCT, 1.0)
        dentro_tolerancia = abs(diferencia) <= umbral

        registrados.append({
            'sku': codigo_txt, 'producto_id': producto.id, 'cantidad_teorica': cantidad_teorica,
            'cantidad_contada': cantidad_val, 'diferencia': diferencia,
            'dentro_tolerancia': dentro_tolerancia, 'quant_id': quant.id,
        })

    ai['result'] = {
        'ok': True,
        'mensaje': (
            str(len(registrados)) + ' conteo(s) registrado(s) del ' + str(fecha_dt) + '. ' +
            str(len([r for r in registrados if not r['dentro_tolerancia']])) + ' fuera de tolerancia (+/-2%% o 1 unidad). ' +
            (str(len(ambiguos)) + ' ambiguo(s) (multi-ubicacion). ' if ambiguos else '') +
            (str(len(no_encontrados)) + ' SKU no encontrado(s): ' + ', '.join(no_encontrados) + '. ' if no_encontrados else '') +
            'NO se aplico ningun ajuste de stock todavia -- eso lo hace ajustar_inventario.'
        ),
        'datos': {'fecha': str(fecha_dt), 'registrados': registrados, 'ambiguos': ambiguos, 'no_encontrados': no_encontrados},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
