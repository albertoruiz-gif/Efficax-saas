"""Server Action: finanzas_tributario / proyeccion_caja

Solo lectura (`aprobacion: "ninguna"`). El catálogo pide "flujo de caja
proyectado ... desde facturas reales y su historial de cobro, con
supuestos explícitos" -- esta herramienta hace la primera parte con
confianza (facturas reales) y es honesta sobre la segunda: NO existe
todavía ningún modelo de "historial de cobro por cliente" (días
promedio de atraso, etc.) construido en este repo, así que no se
inventa un ajuste algorítmico -- se proyecta el flujo bruto (cobros
esperados de `out_invoice`/`out_refund` menos pagos esperados de
`in_invoice`/`in_refund`, ambos `state='posted'` y no pagados/reversados,
agrupados por vencimiento dentro del horizonte) y se declara el supuesto
explícito: "asume pago en la fecha de vencimiento, sin ajuste por
historial de mora".

Tampoco se reporta un "saldo de caja actual" -- calcular el saldo real
de bancos/caja requiere sumar `account.move.line` de las cuentas de los
diarios de tesorería, que no es confiable de inferir sin verificarlo
en vivo con datos reales (a diferencia de `account.journal.current_statement_balance`,
que solo refleja el último extracto importado, no el saldo contable
real). Se prefiere reportar el FLUJO (delta), no inventar un saldo
absoluto que podría estar mal.

`moneda` (PEN/USD, `$ref` a `$defs/moneda`) filtra por `currency_id` de
la factura -- no hay conversión de tipo de cambio, cada factura se
cuenta en su propia moneda y el resultado se separa por moneda
explícitamente (nunca se suman PEN y USD como si fueran lo mismo).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
HORIZONTES_VALIDOS = (30, 60, 90)

horizonte_val = horizonte_dias if horizonte_dias in HORIZONTES_VALIDOS else 30
moneda_txt = (moneda or 'PEN').strip()

if moneda_txt not in ('PEN', 'USD'):
    ai['result'] = {'ok': False, 'mensaje': 'moneda debe ser PEN o USD.', 'datos': {}}
else:
    Moneda = env['res.currency'].search([('name', '=', moneda_txt)], limit=1)
    if not Moneda:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre la moneda ' + moneda_txt + ' configurada en Odoo.', 'datos': {}}
    else:
        hoy = datetime.date.today()
        limite = hoy + datetime.timedelta(days=horizonte_val)

        def facturas_abiertas(tipos):
            Move = env['account.move']
            return Move.search([
                ('move_type', 'in', tipos),
                ('state', '=', 'posted'),
                ('payment_state', 'not in', ('paid', 'reversed')),
                ('currency_id', '=', Moneda.id),
                ('invoice_date_due', '!=', False),
                ('invoice_date_due', '<=', str(limite)),
            ])

        cobros = facturas_abiertas(['out_invoice', 'out_refund'])
        pagos = facturas_abiertas(['in_invoice', 'in_refund'])

        total_cobros = sum(cobros.mapped('amount_residual'))
        total_pagos = sum(pagos.mapped('amount_residual'))
        flujo_neto = total_cobros - total_pagos

        vencidas_cobros = cobros.filtered(lambda m: m.invoice_date_due and m.invoice_date_due < hoy)
        vencidas_pagos = pagos.filtered(lambda m: m.invoice_date_due and m.invoice_date_due < hoy)

        ai['result'] = {
            'ok': True,
            'mensaje': (
                'Proyeccion a ' + str(horizonte_val) + ' dias (' + moneda_txt + '): cobros esperados ' +
                str(total_cobros) + ' (' + str(len(cobros)) + ' factura(s), ' + str(len(vencidas_cobros)) + ' ya vencida(s)), ' +
                'pagos esperados ' + str(total_pagos) + ' (' + str(len(pagos)) + ' factura(s), ' + str(len(vencidas_pagos)) + ' ya vencida(s)). ' +
                'Flujo neto proyectado: ' + str(flujo_neto) + '. ' +
                'Supuesto: se asume cobro/pago en la fecha de vencimiento, sin ajuste por historial de mora (no hay ese modelo construido todavia). ' +
                'No se reporta saldo de caja actual -- solo el flujo esperado.'
            ),
            'datos': {
                'horizonte_dias': horizonte_val, 'moneda': moneda_txt,
                'cobros_esperados': total_cobros, 'pagos_esperados': total_pagos, 'flujo_neto': flujo_neto,
                'cantidad_facturas_cobro': len(cobros), 'cantidad_facturas_pago': len(pagos),
                'cobros_ya_vencidos': len(vencidas_cobros), 'pagos_ya_vencidos': len(vencidas_pagos),
            },
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
