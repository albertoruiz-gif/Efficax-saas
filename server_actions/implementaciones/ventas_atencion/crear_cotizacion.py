"""Server Action: ventas_atencion / crear_cotizacion

Novena y última herramienta con lógica real de ventas_atencion. Crea una
cotización EN BORRADOR (`sale.order`, sin confirmar) desde los productos
conversados. Nunca llama `action_confirm()`: la descripción del catálogo
es explícita — "el pedido final lo confirma el humano o el flujo de
pago", así que confirmar la orden queda fuera del alcance de esta
herramienta a propósito, no es un olvido.

`lineas` es un array de objetos en el catálogo → llega aplanado como
`lineas_json` (string), según `esquemas_odoo.py`. Se parsea con
`json.loads` (disponible en el sandbox — es la razón de ser de ese campo,
ver la docstring de `esquemas_odoo.py`).

Regla explícita del catálogo: "Los SKU deben existir (fallo explícito si
no)" — por eso se validan TODOS los SKU antes de crear nada; si falta
alguno, no se crea una cotización parcial, se informa exactamente cuáles
SKU no existen.

`cliente` es "Nombre o ID del contacto" (texto libre): si es puramente
numérico se trata como id; si no, se busca por nombre — mismo patrón
"nunca inventar" del resto de herramientas.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
cliente_txt = (cliente or '').strip()
lineas_txt = (lineas_json or '').strip()

if not cliente_txt or not lineas_txt:
    ai['result'] = {'ok': False, 'mensaje': 'Necesito el cliente y al menos una linea de productos.', 'datos': {}}
else:
    lineas_data = None
    try:
        lineas_data = json.loads(lineas_txt)
    except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
        lineas_data = None

    if not isinstance(lineas_data, list) or not lineas_data:
        ai['result'] = {'ok': False, 'mensaje': 'lineas_json debe ser una lista con al menos un producto (sku, cantidad).', 'datos': {}}
    else:
        errores_lineas = []
        for i, linea in enumerate(lineas_data):
            if not isinstance(linea, dict) or not linea.get('sku') or linea.get('cantidad') is None:
                errores_lineas.append('linea ' + str(i + 1) + ': falta sku o cantidad')
            elif not (isinstance(linea['cantidad'], (int, float)) and linea['cantidad'] > 0):
                errores_lineas.append('linea ' + str(i + 1) + ' (' + str(linea.get('sku')) + '): cantidad debe ser mayor que 0')

        if errores_lineas:
            ai['result'] = {'ok': False, 'mensaje': 'Lineas invalidas: ' + '; '.join(errores_lineas) + '.', 'datos': {}}
        else:
            # Cliente: id directo si es numerico, si no busqueda por nombre/email.
            Partner = env['res.partner']
            if cliente_txt.isdigit():
                partner = Partner.browse(int(cliente_txt)).exists()
                candidatos_cliente = partner if partner else Partner.browse()
            else:
                candidatos_cliente = Partner.search(
                    ['|', ('name', 'ilike', cliente_txt), ('email', 'ilike', cliente_txt)], limit=5,
                )

            if not candidatos_cliente:
                ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun cliente que coincida con "' + cliente_txt + '".', 'datos': {}}
            elif len(candidatos_cliente) > 1:
                nombres_cli = [c.name + ' (id ' + str(c.id) + ')' for c in candidatos_cliente]
                ai['result'] = {'ok': False, 'mensaje': 'Hay varios clientes que coinciden con "' + cliente_txt + '". Precisa cual: ' + '; '.join(nombres_cli), 'datos': {}}
            else:
                # Los SKU deben existir -- se validan TODOS antes de crear nada
                # (regla explicita del catalogo: fallo explicito, no cotizacion parcial).
                Product = env['product.product']
                lineas_orden = []
                skus_faltantes = []
                for linea in lineas_data:
                    prod = Product.search([('default_code', '=ilike', linea['sku'])], limit=1)
                    if not prod:
                        skus_faltantes.append(str(linea['sku']))
                    else:
                        lineas_orden.append((0, 0, {'product_id': prod.id, 'product_uom_qty': linea['cantidad']}))

                if skus_faltantes:
                    ai['result'] = {
                        'ok': False,
                        'mensaje': 'Estos SKU no existen, no se creo ninguna cotizacion: ' + ', '.join(skus_faltantes) + '.',
                        'datos': {'skus_faltantes': skus_faltantes},
                    }
                else:
                    orden = env['sale.order'].create({
                        'partner_id': candidatos_cliente.id,
                        'order_line': lineas_orden,
                    })
                    ai['result'] = {
                        'ok': True,
                        'mensaje': 'Cotizacion ' + orden.name + ' creada en borrador para ' + candidatos_cliente.name + '. Falta que un humano o el flujo de pago la confirme.',
                        'datos': {'sale_order_id': orden.id, 'numero': orden.name, 'total': orden.amount_total},
                    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
