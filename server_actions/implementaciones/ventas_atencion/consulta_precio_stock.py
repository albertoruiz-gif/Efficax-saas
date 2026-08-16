"""Server Action: ventas_atencion / consulta_precio_stock

Segunda herramienta con lógica real. Solo lectura (product.product): no crea
ni modifica nada, por eso es la más segura para empezar la ronda de
implementación de las 8 restantes de ventas_atencion.

El contenido de CODIGO es exactamente lo que va en el campo `code` del
`ir.actions.server` — corre en el sandbox de Odoo con `env`, `ai`,
`datetime` y `UserError` ya disponibles, y cada propiedad del esquema
saneado llega como variable suelta (`busqueda`, `por_sku`).

Regla "patrón Hasky" (de la descripción del catálogo): si no hay una
coincidencia clara, nunca inventar el producto — se devuelve ok=false y,
si hay varios candidatos, se listan para que el usuario precise, en vez de
adivinar cuál quiso decir.

qty_available es un campo calculado nativo de product.product (agrega
stock.quant por dentro) — se lee ahí en vez de consultar stock.quant a
mano, evita duplicar lógica de Odoo y respeta los permisos reales del
usuario igual que consultar stock.quant directamente.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
termino = (busqueda or '').strip()
usar_sku = bool(por_sku)

if not termino:
    ai['result'] = {'ok': False, 'mensaje': 'Necesito un SKU o nombre de producto para buscar.', 'datos': {}}
else:
    Product = env['product.product']
    if usar_sku:
        candidatos = Product.search([('default_code', '=ilike', termino)], limit=5)
    else:
        candidatos = Product.search(
            ['|', ('name', 'ilike', termino), ('default_code', '=ilike', termino)],
            limit=5,
        )

    if not candidatos:
        ai['result'] = {
            'ok': False,
            'mensaje': 'No encontre ningun producto que coincida con "' + termino + '".',
            'datos': {},
        }
    elif len(candidatos) > 1:
        # Nunca inventar cual quiso decir: se listan los candidatos y se pide precisar.
        nombres = [(p.default_code or 's/SKU') + ' - ' + p.name for p in candidatos]
        ai['result'] = {
            'ok': False,
            'mensaje': 'Hay varios productos que coinciden con "' + termino + '". Precisa cual: ' + '; '.join(nombres),
            'datos': {'candidatos': nombres},
        }
    else:
        p = candidatos[0]
        ai['result'] = {
            'ok': True,
            'mensaje': 'Producto encontrado.',
            'datos': {
                'producto': p.name,
                'sku': p.default_code or '',
                'precio': p.lst_price,
                'moneda': env.company.currency_id.symbol or env.company.currency_id.name,
                'stock_disponible': p.qty_available,
                'unidad_medida': p.uom_id.name,
            },
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
