"""Server Action: inventarios / ajustar_inventario

`aprobacion: "dueno"` (el catálogo aclara que es dinámica según el
umbral de valor -- "confirmar" para diferencias chicas, "dueño" para
las grandes; el campo `aprobacion` refleja el techo. La decisión de
CUÁNDO pedir cada nivel es del agente en la conversación, no de este
código).

Aplica el ajuste con el mecanismo NATIVO real de Odoo: escribe
`stock.quant.inventory_quantity` (cantidad teorica + diferencia) y llama
`action_apply_inventory()` -- confirmado en vivo que el método existe y
ejecuta sin error. Deja constancia de `causa_probable` en el chatter del
producto (`message_post` -- `product.template` hereda `mail.thread`).

Mismo criterio de `registrar_conteo.py`: si hay más de una ubicación
interna con stock para el SKU, no adivina cuál ajustar -- lo rechaza
explícito.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
CAUSAS_VALIDAS = ('rotura', 'merma', 'error_recepcion', 'error_conteo', 'posible_perdida', 'otro')

codigo_txt = (codigo_producto or '').strip()
diferencia_val = diferencia
causa_txt = (causa_probable or '').strip()

errores = []
if not codigo_txt:
    errores.append('falta codigo_producto')
if diferencia_val is None:
    errores.append('falta diferencia')
if causa_txt not in CAUSAS_VALIDAS:
    errores.append('causa_probable debe ser una de: ' + ', '.join(CAUSAS_VALIDAS))

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude ajustar el inventario: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Producto = env['product.template'].search([('default_code', '=', codigo_txt)], limit=1)
    if not Producto:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun producto con codigo "' + codigo_txt + '".', 'datos': {}}
    else:
        # stock.quant.product_id es product.product, Producto.id es
        # product.template -- puentear con product_tmpl_id.
        Quant = env['stock.quant'].search([('product_id.product_tmpl_id', '=', Producto.id), ('location_id.usage', '=', 'internal')])
        if len(Quant) != 1:
            ai['result'] = {
                'ok': False,
                'mensaje': 'El SKU "' + codigo_txt + '" tiene ' + str(len(Quant)) + ' ubicacion(es) interna(s) con stock -- no puedo aplicar un ajuste unico sin ambiguedad. Resuelvelo a mano en Inventario.',
                'datos': {},
            }
        else:
            quant = Quant
            cantidad_teorica_previa = quant.quantity
            nueva_cantidad = cantidad_teorica_previa + diferencia_val
            quant.write({'inventory_quantity': nueva_cantidad})
            quant.action_apply_inventory()

            nota = (
                'Ajuste de inventario aplicado: ' + str(cantidad_teorica_previa) + ' -> ' + str(nueva_cantidad) +
                ' (diferencia ' + str(diferencia_val) + '). Causa probable: ' + causa_txt + '.'
            )
            Producto.message_post(body=nota)

            ai['result'] = {
                'ok': True,
                'mensaje': (
                    'Ajuste aplicado para ' + codigo_txt + ': ' + str(cantidad_teorica_previa) + ' -> ' + str(nueva_cantidad) +
                    ' (' + causa_txt + '). Constancia dejada en el chatter del producto.'
                ),
                'datos': {'producto_id': Producto.id, 'sku': codigo_txt, 'cantidad_anterior': cantidad_teorica_previa, 'cantidad_nueva': nueva_cantidad, 'diferencia': diferencia_val, 'causa_probable': causa_txt},
            }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
