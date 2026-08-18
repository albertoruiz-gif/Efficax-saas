"""Server Action: inventarios / entregar_conteo_dia

`aprobacion: "ninguna"`. Entrega los SKU programados para contar en
`fecha` (via `x_proximo_conteo_ciclico`, fijado por `generar_plan_conteo`).

**Política de conteo ciego -- no hay una configuración real de esto
todavía** (ningún parámetro de Fase 4 existe en este tenant para esa
política): se asume conteo CIEGO por default (no se muestra la cantidad
esperada del sistema) porque es la mejor práctica estándar -- mostrar la
cantidad esperada sesga a quien cuenta a confirmar el número en vez de
contar de verdad. Declarado explícito, no una decisión oculta.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
fecha_txt = (fecha or '').strip()
responsable_txt = (responsable or '').strip()

try:
    fecha_dt = datetime.datetime.strptime(fecha_txt, '%Y-%m-%d').date() if fecha_txt else False
except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
    fecha_dt = False

if not fecha_dt:
    ai['result'] = {'ok': False, 'mensaje': 'fecha debe ser una fecha valida en formato AAAA-MM-DD.', 'datos': {}}
elif not responsable_txt:
    ai['result'] = {'ok': False, 'mensaje': 'falta el responsable del conteo.', 'datos': {}}
else:
    Producto = env['product.template']
    programados = Producto.search([('x_proximo_conteo_ciclico', '=', str(fecha_dt))])

    if not programados:
        ai['result'] = {'ok': True, 'mensaje': 'No hay ningun SKU programado para contar el ' + str(fecha_dt) + '.', 'datos': {'skus': []}}
    else:
        skus = [{'producto_id': p.id, 'sku': p.default_code or False, 'nombre': p.name, 'clase': p.x_clase_abc or False} for p in programados]
        ai['result'] = {
            'ok': True,
            'mensaje': (
                'Conteo del ' + str(fecha_dt) + ' para ' + responsable_txt + ': ' + str(len(skus)) + ' SKU. ' +
                'Conteo CIEGO (no se muestra la cantidad esperada del sistema -- no hay una politica configurada distinta todavia).'
            ),
            'datos': {'fecha': str(fecha_dt), 'responsable': responsable_txt, 'skus': skus, 'conteo_ciego': True},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
