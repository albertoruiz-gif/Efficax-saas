"""Server Action: mentor / resumen_negocio

Décima herramienta con lógica real, primera de Mentor. Solo lectura:
ventas del período, facturación/cobranza, entregas pendientes y leads
nuevos — los insumos crudos para que Mentor arme el "top-3 semanal" en
lenguaje natural (la narrativa la construye el LLM con estos datos; esta
herramienta entrega números exactos, no inventa la síntesis).

`periodo` (objeto en el catálogo) llega aplanado como `periodo_desde` /
`periodo_hasta` (ver esquemas_odoo.py) — ambos obligatorios porque
`periodo` es obligatorio en el esquema original. `comparar_con_anterior`
pierde su `default: true` (Odoo no lo soporta) — se aplica a mano.

"Caja estimada" se interpreta como facturación del período vs. lo que
sigue pendiente de cobro (`payment_state` en `account.move`) — no hay un
modelo de caja/banco en `modelos_odoo`, así que no se inventa acceso a
`account.account`/`account.payment`.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
desde_txt = (periodo_desde or '').strip()
hasta_txt = (periodo_hasta or '').strip()
comparar = True if comparar_con_anterior is None else bool(comparar_con_anterior)

try:
    desde_dt = datetime.datetime.strptime(desde_txt, '%Y-%m-%d').date()
except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
    desde_dt = False
try:
    hasta_dt = datetime.datetime.strptime(hasta_txt, '%Y-%m-%d').date()
except:  # noqa: E722
    hasta_dt = False

if not desde_dt or not hasta_dt:
    ai['result'] = {'ok': False, 'mensaje': 'periodo_desde/periodo_hasta deben ser fechas validas en formato AAAA-MM-DD.', 'datos': {}}
elif desde_dt > hasta_dt:
    ai['result'] = {'ok': False, 'mensaje': 'periodo_desde no puede ser posterior a periodo_hasta.', 'datos': {}}
else:
    def medir_periodo(d_desde, d_hasta):
        Sale = env['sale.order']
        ordenes = Sale.search([
            ('date_order', '>=', str(d_desde)), ('date_order', '<=', str(d_hasta)),
            ('state', 'in', ['sale', 'done']),
        ])
        ventas_total = sum(ordenes.mapped('amount_total'))

        Move = env['account.move']
        facturas = Move.search([
            ('invoice_date', '>=', str(d_desde)), ('invoice_date', '<=', str(d_hasta)),
            ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
        ])
        facturado_total = sum(facturas.mapped('amount_total'))
        pendiente_cobro = sum(facturas.filtered(lambda f: f.payment_state not in ('paid', 'in_payment')).mapped('amount_residual'))

        Lead = env['crm.lead']
        leads_nuevos = Lead.search_count([
            ('create_date', '>=', str(d_desde) + ' 00:00:00'), ('create_date', '<=', str(d_hasta) + ' 23:59:59'),
        ])

        Picking = env['stock.picking']
        entregas_pendientes = Picking.search_count([
            ('scheduled_date', '>=', str(d_desde) + ' 00:00:00'), ('scheduled_date', '<=', str(d_hasta) + ' 23:59:59'),
            ('state', 'not in', ['done', 'cancel']),
        ])

        return {
            'ventas_total': ventas_total,
            'pedidos_confirmados': len(ordenes),
            'facturado_total': facturado_total,
            'pendiente_cobro': pendiente_cobro,
            'leads_nuevos': leads_nuevos,
            'entregas_pendientes': entregas_pendientes,
        }

    actual = medir_periodo(desde_dt, hasta_dt)
    datos = {'periodo': {'desde': str(desde_dt), 'hasta': str(hasta_dt)}, 'actual': actual}

    if comparar:
        dias = (hasta_dt - desde_dt).days + 1
        anterior_hasta = desde_dt - datetime.timedelta(days=1)
        anterior_desde = anterior_hasta - datetime.timedelta(days=dias - 1)
        datos['anterior'] = medir_periodo(anterior_desde, anterior_hasta)
        datos['periodo_anterior'] = {'desde': str(anterior_desde), 'hasta': str(anterior_hasta)}

    ai['result'] = {
        'ok': True,
        'mensaje': (
            'Ventas: ' + str(actual['ventas_total']) + '. Facturado: ' + str(actual['facturado_total']) +
            ' (pendiente de cobro: ' + str(actual['pendiente_cobro']) + '). Leads nuevos: ' +
            str(actual['leads_nuevos']) + '. Entregas pendientes: ' + str(actual['entregas_pendientes']) + '.'
        ),
        'datos': datos,
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
