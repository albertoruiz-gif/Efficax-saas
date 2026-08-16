"""Server Action: ventas_atencion / estado_pedido

Tercera herramienta con lógica real. Solo lectura (sale.order +
stock.picking), pero con una regla de seguridad explícita del catálogo:
"nunca revelar datos de terceros".

Por eso la verificación de identidad (teléfono o email del comprador) no
es opcional ni cosmética: si el pedido existe pero el dato de verificación
no coincide con el partner del pedido, la respuesta es EXACTAMENTE la
misma que si el pedido no existiera. Distinguir "pedido no existe" de
"pedido existe pero verificación incorrecta" dejaría enumerar números de
pedido válidos por fuerza bruta — no se hace.

El contenido de CODIGO es lo que va en el campo `code` del
`ir.actions.server`; corre en el sandbox de Odoo con `env`, `ai`,
`datetime` y `UserError` ya disponibles, y cada propiedad del esquema
saneado llega como variable suelta (`numero_pedido`, `verificacion_cliente`).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
MENSAJE_NO_ENCONTRADO = 'No encontre ningun pedido con ese numero y esos datos de verificacion.'

pedido_num = (numero_pedido or '').strip()
verificacion = (verificacion_cliente or '').strip().lower()

if not pedido_num or not verificacion:
    ai['result'] = {
        'ok': False,
        'mensaje': 'Necesito el numero de pedido y un telefono o email para verificar tu identidad.',
        'datos': {},
    }
else:
    Order = env['sale.order']
    orden = Order.search([('name', '=ilike', pedido_num)], limit=1)

    verificado = False
    if orden:
        # Esta base no tiene un campo 'mobile' separado (fue verificado con
        # fields_get: solo existen phone / phone_sanitized / email). Se usa
        # phone_sanitized ademas de phone porque normaliza formato (espacios,
        # guiones, codigo de pais) y hace la comparacion mas tolerante.
        partner = orden.partner_id
        datos_partner = [
            (partner.email or '').strip().lower(),
            (partner.phone or '').strip().lower(),
            (partner.phone_sanitized or '').strip().lower(),
        ]
        verificado = verificacion in datos_partner and verificacion != ''

    if not orden or not verificado:
        # Misma respuesta para "no existe" y "existe pero no coincide la verificacion":
        # no se revela si el numero de pedido es valido.
        ai['result'] = {'ok': False, 'mensaje': MENSAJE_NO_ENCONTRADO, 'datos': {}}
    else:
        ESTADOS_COMERCIALES = {
            'draft': 'cotizacion',
            'sent': 'cotizacion enviada',
            'sale': 'confirmado',
            'done': 'bloqueado',
            'cancel': 'cancelado',
        }
        ESTADOS_ENTREGA = {
            'draft': 'entrega en preparacion',
            'waiting': 'esperando disponibilidad de stock',
            'confirmed': 'esperando disponibilidad de stock',
            'assigned': 'listo para enviar',
            'done': 'entregado',
            'cancel': 'cancelado',
        }
        entrega = orden.picking_ids.filtered(lambda p: p.state != 'cancel')[:1]
        if entrega:
            estado_entrega = ESTADOS_ENTREGA.get(entrega.state, entrega.state)
            fecha_entrega = entrega.date_done or entrega.scheduled_date
        else:
            estado_entrega = 'sin envio asociado todavia'
            fecha_entrega = False

        ai['result'] = {
            'ok': True,
            'mensaje': 'Pedido encontrado.',
            'datos': {
                'numero_pedido': orden.name,
                'estado_comercial': ESTADOS_COMERCIALES.get(orden.state, orden.state),
                'total': orden.amount_total,
                'moneda': orden.currency_id.symbol or orden.currency_id.name,
                'estado_entrega': estado_entrega,
                'fecha_entrega': str(fecha_entrega) if fecha_entrega else '',
            },
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
