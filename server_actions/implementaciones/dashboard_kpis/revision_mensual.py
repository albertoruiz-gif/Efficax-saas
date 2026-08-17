"""Server Action: dashboard_kpis / revision_mensual

Solo lectura + propuesta — el catálogo lo dice explícito, así que a
diferencia de `construir_dashboard`/`alerta_umbral` esta NO escribe nada
en `spreadsheet.dashboard` (que aparece en `modelos_odoo` como el área de
negocio del agente, no como algo que esta herramienta puntual deba tocar
— mismo criterio ya aplicado en `nota_vendedor.py` para `calendar.event`).

Compara el mes pedido contra el anterior usando el mismo catálogo fijo de
KPIs de `calcular_kpi.py` (duplicado acá a propósito: cada Server Action
es un blob de código independiente, no hay import entre ellas dentro del
sandbox de Odoo) y arma una propuesta simple: cualquier KPI que se movió
más de 20% entre meses queda marcado como candidato a revisar el umbral
del contrato — regla honesta y explicable, no una IA prediciendo metas
que nadie definió.

`mes` usa `pattern: "^[0-9]{4}-[0-9]{2}$"` — es una de las pocas
restricciones de propiedad que Odoo SÍ preserva en el esquema (ver
esquemas_odoo.py: `pattern` está en `CLAVES_PERMITIDAS_PROPIEDAD`), así
que llega ya validado por formato la mayoría de las veces — igual se
revalida acá por si acaso.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
KPIS_DISPONIBLES = ('ventas_totales', 'ticket_promedio', 'tasa_conversion', 'margen_bruto', 'valor_inventario')
UMBRAL_CAMBIO_RELEVANTE_PCT = 20.0

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
        anio_ant, mes_ant = anio, 11
    else:
        siguiente = datetime.date(anio, mes_num + 1, 1)
        hasta_dt = siguiente - datetime.timedelta(days=1)
        anio_ant, mes_ant = (anio, mes_num - 1) if mes_num > 1 else (anio - 1, 12)

    desde_ant = datetime.date(anio_ant, mes_ant, 1)
    if mes_ant == 12:
        hasta_ant = datetime.date(anio_ant, 12, 31)
    else:
        hasta_ant = datetime.date(anio_ant, mes_ant + 1, 1) - datetime.timedelta(days=1)

    def calcular(nombre, d_desde, d_hasta):
        Sale = env['sale.order']
        ordenes = Sale.search([
            ('date_order', '>=', str(d_desde)), ('date_order', '<=', str(d_hasta)),
            ('state', 'in', ['sale', 'done']),
        ])
        if nombre == 'ventas_totales':
            return sum(ordenes.mapped('amount_total'))
        if nombre == 'ticket_promedio':
            total = sum(ordenes.mapped('amount_total'))
            n = len(ordenes)
            return (total / n) if n else 0.0
        if nombre == 'tasa_conversion':
            Lead = env['crm.lead']
            leads_periodo = Lead.search([
                ('create_date', '>=', str(d_desde) + ' 00:00:00'), ('create_date', '<=', str(d_hasta) + ' 23:59:59'),
            ])
            total_leads = len(leads_periodo)
            ganados = len(leads_periodo.filtered(lambda l_: l_.stage_id.is_won))
            return (ganados / total_leads * 100) if total_leads else 0.0
        if nombre == 'margen_bruto':
            # sale.report no tiene 'margin' ni 'order_id' en este tenant (modulo
            # sale_margin no instalado, confirmado con fields_get) -- se calcula
            # a mano: subtotal de linea menos costo estandar del producto x cantidad.
            Linea = env['sale.order.line']
            lineas = Linea.search([('order_id', 'in', ordenes.ids)])
            ventas = sum(lineas.mapped('price_subtotal'))
            costo = sum(l.product_uom_qty * l.product_id.standard_price for l in lineas)
            margen = ventas - costo
            return (margen / ventas * 100) if ventas else 0.0
        Quant = env['stock.quant']
        quants = Quant.search([('location_id.usage', '=', 'internal')])
        return sum(q.quantity * q.product_id.standard_price for q in quants)

    comparacion = []
    candidatos_revision = []
    for nombre_kpi in KPIS_DISPONIBLES:
        actual = calcular(nombre_kpi, desde_dt, hasta_dt)
        anterior = calcular(nombre_kpi, desde_ant, hasta_ant)
        cambio_pct = ((actual - anterior) / anterior * 100) if anterior else (100.0 if actual else 0.0)
        fila = {'kpi': nombre_kpi, 'mes_actual': actual, 'mes_anterior': anterior, 'cambio_pct': cambio_pct}
        comparacion.append(fila)
        if abs(cambio_pct) >= UMBRAL_CAMBIO_RELEVANTE_PCT:
            candidatos_revision.append(nombre_kpi + ' (' + ('%.1f' % cambio_pct) + '%)')

    propuesta = (
        'Sin cambios relevantes (todos los KPIs dentro de +/-' + str(UMBRAL_CAMBIO_RELEVANTE_PCT) + '%).'
        if not candidatos_revision else
        'Candidatos a revisar el umbral del contrato: ' + ', '.join(candidatos_revision) + '.'
    )

    ai['result'] = {
        'ok': True,
        'mensaje': 'Revision de ' + mes_txt + ' vs ' + desde_ant.strftime('%Y-%m') + '. ' + propuesta,
        'datos': {'mes': mes_txt, 'mes_anterior': desde_ant.strftime('%Y-%m'), 'comparacion': comparacion, 'propuesta': propuesta},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
