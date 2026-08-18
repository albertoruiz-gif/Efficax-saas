"""Server Action: finanzas_tributario / conciliar_movimientos

`aprobacion: "confirmar"`. Corre los modelos de conciliación sobre un
`account.bank.statement`: aplica AUTOMÁTICO solo los emparejamientos
inequívocos (nº de operación o RUC+monto exacto contra una factura
abierta), presenta el resto como propuesta con evidencia, y lista los no
identificados. **Nunca aplica un match dudoso sin confirmación** -- tal
cual pide el catálogo.

**Incertidumbre real, declarada:** la API de conciliación bancaria
"correcta" de Odoo 19 es el widget de Conciliación Bancaria (JS,
`account.bank.statement.line._reconcile_bank_lines` internamente), que
no está pensada para invocarse línea por línea desde un Server Action
simple. Esta implementación usa el camino de más bajo nivel que SÍ es
ORM puro (`account.move.line.reconcile()` sobre la línea contable de la
`statement.line` y la línea por cobrar de la factura) -- funciona para
el caso exacto, pero **no fue probado en vivo con reconciliaciones
reales todavía** (a diferencia del resto del catálogo de esta noche). Si
`reconcile()` falla por cualquier razón, esta herramienta NO revienta:
degrada ese movimiento a "propuesta" en vez de aplicar nada a la fuerza.

`solo_proponer=True` desactiva CUALQUIER escritura -- devuelve solo
propuestas, ni siquiera aplica los exactos.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
Statement = env['account.bank.statement']
statement = Statement.browse(statement_id) if statement_id else Statement.browse()

if not statement.exists():
    ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun extracto con id ' + str(statement_id) + '.', 'datos': {}}
else:
    solo_proponer_val = bool(solo_proponer) if solo_proponer is not None else False

    lineas_sin_conciliar = statement.line_ids.filtered(lambda l_: not l_.is_reconciled)

    aplicados = []
    propuestas = []
    no_identificados = []

    Move = env['account.move']

    for linea in lineas_sin_conciliar:
        monto_abs = abs(linea.amount)
        candidatos = Move.search([
            ('move_type', 'in', ('out_invoice', 'in_invoice')),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ('paid', 'reversed')),
            ('amount_residual', '=', monto_abs),
        ])

        # match exacto: numero de operacion (payment_ref) contiene el nombre
        # de la factura, o el RUC del partner coincide con un candidato de
        # monto igual.
        match_exacto = candidatos.filtered(lambda f_: f_.name and linea.payment_ref and f_.name in linea.payment_ref)
        if not match_exacto and linea.partner_id:
            match_exacto = candidatos.filtered(lambda f_: f_.partner_id.id == linea.partner_id.id)

        if len(match_exacto) == 1 and not solo_proponer_val:
            factura = match_exacto
            linea_bancaria = linea.move_id.line_ids.filtered(lambda l_: l_.account_id.account_type not in ('asset_cash', 'asset_current') and not l_.reconciled)
            linea_factura = factura.line_ids.filtered(lambda l_: l_.account_id.account_type in ('asset_receivable', 'liability_payable') and not l_.reconciled)
            aplicado_ok = False
            try:
                if linea_bancaria and linea_factura:
                    (linea_bancaria[:1] + linea_factura[:1]).reconcile()
                    aplicado_ok = True
            except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox; degrada a propuesta
                aplicado_ok = False

            if aplicado_ok:
                aplicados.append({'linea_id': linea.id, 'factura': factura.name, 'monto': monto_abs, 'evidencia': 'match exacto (numero de operacion o cliente unico con mismo monto)'})
            else:
                propuestas.append({'linea_id': linea.id, 'factura_candidata': factura.name, 'monto': monto_abs, 'evidencia': 'match exacto pero no se pudo aplicar automaticamente -- confirma a mano', 'descripcion_movimiento': linea.payment_ref})
        elif len(match_exacto) == 1 and solo_proponer_val:
            propuestas.append({'linea_id': linea.id, 'factura_candidata': match_exacto.name, 'monto': monto_abs, 'evidencia': 'match exacto (solo_proponer=true, no se aplico nada)', 'descripcion_movimiento': linea.payment_ref})
        elif candidatos:
            nombres = [c.name for c in candidatos]
            propuestas.append({'linea_id': linea.id, 'facturas_candidatas': nombres, 'monto': monto_abs, 'evidencia': 'mismo monto, ' + str(len(candidatos)) + ' factura(s) posibles -- ambiguo, requiere confirmacion', 'descripcion_movimiento': linea.payment_ref})
        else:
            no_identificados.append({'linea_id': linea.id, 'monto': linea.amount, 'descripcion_movimiento': linea.payment_ref, 'fecha': str(linea.date)})

    ai['result'] = {
        'ok': True,
        'mensaje': (
            'Extracto "' + statement.name + '": ' + str(len(aplicados)) + ' aplicado(s) automatico, ' +
            str(len(propuestas)) + ' propuesta(s) pendiente de confirmacion, ' + str(len(no_identificados)) + ' sin identificar.' +
            (' (solo_proponer=true -- nada se aplico)' if solo_proponer_val else '')
        ),
        'datos': {'statement_id': statement.id, 'aplicados': aplicados, 'propuestas': propuestas, 'no_identificados': no_identificados},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
