"""Server Action: dashboard_kpis / calcular_kpi

Solo lectura. Calcula un KPI y devuelve también la fórmula en texto
("este 23% sale de X entre Y") — es un requisito explícito del catálogo,
no cosmético: el dueño tiene que poder verificar el número, no solo
confiar en él.

`kpi` dice "Nombre del KPI del **contrato vigente**" — el contrato (qué
KPIs sigue cada negocio) lo define Booster en su Fase 4 ("criterios...
qué cuenta como 'conversión' para sus reportes", ver
01-booster-implementador.md), que todavía no está construida. Sin esa
fuente de verdad, esta herramienta NO inventa el contrato de nadie: ofrece
un catálogo fijo de KPIs de negocio estándar (ventas, ticket promedio,
conversión, margen, valor de inventario) y si piden uno que no reconoce,
lo dice explícito con la lista de los disponibles — mismo patrón "nunca
inventar" del resto del catálogo. Cuando exista el contrato real de Fase
4, este catálogo fijo se reemplaza por esa fuente, no antes.

`comparar_con: "meta"` tiene el mismo problema: no existe ningún lugar
donde el negocio registre sus metas todavía. Si piden comparar contra
meta, se calcula igual el valor pero se avisa honesto que no hay meta
configurada — no se inventa un objetivo.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
KPIS_DISPONIBLES = ('ventas_totales', 'ticket_promedio', 'tasa_conversion', 'margen_bruto', 'valor_inventario')
COMPARACIONES_VALIDAS = ('periodo_anterior', 'meta', 'ambos')

kpi_txt = (kpi or '').strip()
desde_txt = (periodo_desde or '').strip()
hasta_txt = (periodo_hasta or '').strip()
comparar_txt = (comparar_con or 'ambos').strip()

try:
    desde_dt = datetime.datetime.strptime(desde_txt, '%Y-%m-%d').date()
except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
    desde_dt = False
try:
    hasta_dt = datetime.datetime.strptime(hasta_txt, '%Y-%m-%d').date()
except:  # noqa: E722
    hasta_dt = False

errores = []
if kpi_txt not in KPIS_DISPONIBLES:
    errores.append('no reconozco el KPI "' + kpi_txt + '". Disponibles: ' + ', '.join(KPIS_DISPONIBLES))
if not desde_dt or not hasta_dt:
    errores.append('periodo_desde/periodo_hasta deben ser fechas validas en formato AAAA-MM-DD')
elif desde_dt > hasta_dt:
    errores.append('periodo_desde no puede ser posterior a periodo_hasta')
if comparar_txt not in COMPARACIONES_VALIDAS:
    errores.append('comparar_con invalido')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude calcular el KPI: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    def calcular(nombre, d_desde, d_hasta):
        Sale = env['sale.order']
        ordenes = Sale.search([
            ('date_order', '>=', str(d_desde)), ('date_order', '<=', str(d_hasta)),
            ('state', 'in', ['sale', 'done']),
        ])
        if nombre == 'ventas_totales':
            total = sum(ordenes.mapped('amount_total'))
            return total, str(len(ordenes)) + ' pedido(s) confirmado(s), suma de amount_total = ' + str(total)

        if nombre == 'ticket_promedio':
            total = sum(ordenes.mapped('amount_total'))
            n = len(ordenes)
            valor = (total / n) if n else 0.0
            return valor, str(total) + ' entre ' + str(n) + ' pedido(s) = ' + str(valor)

        if nombre == 'tasa_conversion':
            Lead = env['crm.lead']
            leads_periodo = Lead.search([
                ('create_date', '>=', str(d_desde) + ' 00:00:00'), ('create_date', '<=', str(d_hasta) + ' 23:59:59'),
            ])
            total_leads = len(leads_periodo)
            ganados = len(leads_periodo.filtered(lambda l_: l_.stage_id.is_won))
            valor = (ganados / total_leads * 100) if total_leads else 0.0
            return valor, str(ganados) + ' ganado(s) entre ' + str(total_leads) + ' lead(s) x 100 = ' + str(valor) + '%'

        if nombre == 'margen_bruto':
            Report = env['sale.report']
            lineas = Report.search([
                ('order_id', 'in', ordenes.ids),
            ])
            margen = sum(lineas.mapped('margin')) if lineas else 0.0
            ventas = sum(ordenes.mapped('amount_total'))
            valor = (margen / ventas * 100) if ventas else 0.0
            return valor, 'margen total ' + str(margen) + ' entre ventas totales ' + str(ventas) + ' x 100 = ' + str(valor) + '%'

        # valor_inventario: no depende del periodo, es una foto del momento actual.
        Quant = env['stock.quant']
        quants = Quant.search([('location_id.usage', '=', 'internal')])
        valor = sum(q.quantity * q.product_id.standard_price for q in quants)
        return valor, 'suma de (cantidad x costo estandar) sobre ' + str(len(quants)) + ' registro(s) de stock interno'

    valor_actual, formula = calcular(kpi_txt, desde_dt, hasta_dt)
    datos = {'kpi': kpi_txt, 'valor': valor_actual, 'formula': formula, 'periodo': {'desde': str(desde_dt), 'hasta': str(hasta_dt)}}
    avisos = []

    if comparar_txt in ('periodo_anterior', 'ambos'):
        dias = (hasta_dt - desde_dt).days + 1
        anterior_hasta = desde_dt - datetime.timedelta(days=1)
        anterior_desde = anterior_hasta - datetime.timedelta(days=dias - 1)
        valor_anterior, formula_anterior = calcular(kpi_txt, anterior_desde, anterior_hasta)
        datos['periodo_anterior'] = {
            'desde': str(anterior_desde), 'hasta': str(anterior_hasta),
            'valor': valor_anterior, 'formula': formula_anterior,
        }

    if comparar_txt in ('meta', 'ambos'):
        avisos.append('no hay ninguna meta configurada todavia para este negocio (Fase 4 de Booster no construida) -- no se inventa un objetivo')

    ai['result'] = {
        'ok': True,
        'mensaje': kpi_txt + ' = ' + str(valor_actual) + ' (' + formula + ')' + (' | ' + '; '.join(avisos) if avisos else ''),
        'datos': datos,
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
