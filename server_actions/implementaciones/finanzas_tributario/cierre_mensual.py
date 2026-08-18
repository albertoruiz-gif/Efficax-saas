"""Server Action: finanzas_tributario / cierre_mensual

Solo lectura + reporte (`aprobacion: "ninguna"`). Diagnóstico de cierre
usando campos reales de `account.move`/`account.move.line`/`account.account`
(confirmados con `fields_get`: `account_type` tiene los valores reales
de Odoo 19 -- `income`/`income_other`/`expense`/`expense_other`/
`expense_direct_cost`/`expense_depreciation`, no adivinados).

Tres chequeos + narrativa:
1. **Transacciones sin categorizar** = asientos (`account.move`) del mes
   todavía en `state='draft'` -- no pueden cerrar el mes hasta postearse
   o descartarse.
2. **Duplicados sospechosos** = facturas con el mismo cliente + mismo
   monto total + misma fecha dentro del mes (heurística razonable, no
   una detección perfecta -- se declara como sospecha, no como hecho).
3. **Cuadre** = suma de debe vs haber de todas las líneas posteadas del
   mes -- en Odoo esto SIEMPRE cuadra por partida doble (no es un chequeo
   que pueda fallar salvo corrupción de datos), se reporta igual como
   confirmación explícita, no se asume sin verificar.

La narrativa del P&L usa `account_type` para separar ingresos
(`income`/`income_other`) de gastos (`expense`/`expense_other`/
`expense_direct_cost`/`expense_depreciation`).
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
mes_txt = (mes or '').strip()

anio = False
mes_num = False
if len(mes_txt) == 7 and mes_txt[4] == '-':
    try:
        anio = int(mes_txt[0:4])
        mes_num = int(mes_txt[5:7])
    except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
        anio = False
        mes_num = False

if not anio or not mes_num or mes_num < 1 or mes_num > 12:
    ai['result'] = {'ok': False, 'mensaje': 'mes debe tener formato AAAA-MM valido.', 'datos': {}}
else:
    desde_dt = datetime.date(anio, mes_num, 1)
    if mes_num == 12:
        hasta_dt = datetime.date(anio, 12, 31)
    else:
        hasta_dt = datetime.date(anio, mes_num + 1, 1) - datetime.timedelta(days=1)

    Move = env['account.move']

    # 1) sin categorizar: asientos del mes que siguen en borrador.
    sin_categorizar = Move.search([
        ('state', '=', 'draft'),
        ('date', '>=', str(desde_dt)), ('date', '<=', str(hasta_dt)),
    ])

    # 2) duplicados sospechosos: mismo cliente + mismo monto + misma fecha.
    facturas_mes = Move.search([
        ('move_type', 'in', ('out_invoice', 'in_invoice')),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', str(desde_dt)), ('invoice_date', '<=', str(hasta_dt)),
    ])
    vistos = {}
    duplicados = []
    for f in facturas_mes:
        clave = (f.partner_id.id if f.partner_id else False, f.amount_total, str(f.invoice_date))
        if clave in vistos:
            duplicados.append({'factura_a': vistos[clave], 'factura_b': f.name, 'cliente': f.partner_id.name if f.partner_id else False, 'monto': f.amount_total, 'fecha': str(f.invoice_date)})
        else:
            vistos[clave] = f.name

    # 3) cuadre: debe vs haber de lineas posteadas del mes.
    Linea = env['account.move.line']
    lineas_mes = Linea.search([
        ('parent_state', '=', 'posted'),
        ('date', '>=', str(desde_dt)), ('date', '<=', str(hasta_dt)),
    ])
    total_debe = sum(lineas_mes.mapped('debit'))
    total_haber = sum(lineas_mes.mapped('credit'))
    cuadra = abs(total_debe - total_haber) < 0.01

    # narrativa P&L
    CUENTAS_INGRESO = ('income', 'income_other')
    CUENTAS_GASTO = ('expense', 'expense_other', 'expense_direct_cost', 'expense_depreciation')
    lineas_ingreso = lineas_mes.filtered(lambda l_: l_.account_id.account_type in CUENTAS_INGRESO)
    lineas_gasto = lineas_mes.filtered(lambda l_: l_.account_id.account_type in CUENTAS_GASTO)
    ingresos = sum(lineas_ingreso.mapped('credit')) - sum(lineas_ingreso.mapped('debit'))
    gastos = sum(lineas_gasto.mapped('debit')) - sum(lineas_gasto.mapped('credit'))
    utilidad = ingresos - gastos

    narrativa = (
        'En ' + mes_txt + ' entraron ' + str(round(ingresos, 2)) + ' de ingresos y salieron ' + str(round(gastos, 2)) + ' en gastos, ' +
        'dejando una utilidad de ' + str(round(utilidad, 2)) + '.'
    )

    ai['result'] = {
        'ok': True,
        'mensaje': (
            'Cierre de ' + mes_txt + ': ' + str(len(sin_categorizar)) + ' asiento(s) sin categorizar (en borrador), ' +
            str(len(duplicados)) + ' posible(s) duplicado(s), cuadre ' + ('OK' if cuadra else 'DESCUADRADO -- revisar urgente') + '. ' +
            narrativa
        ),
        'datos': {
            'mes': mes_txt, 'sin_categorizar': sin_categorizar.ids, 'duplicados_sospechosos': duplicados,
            'total_debe': total_debe, 'total_haber': total_haber, 'cuadra': cuadra,
            'ingresos': round(ingresos, 2), 'gastos': round(gastos, 2), 'utilidad': round(utilidad, 2),
            'narrativa': narrativa,
        },
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
